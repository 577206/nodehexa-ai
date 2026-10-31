"""Selective real-solid chamfers for the R06 review armor.

Only the explicit R06 armor IDs below are eligible.  Selection is geometrical:
straight edge > 4 mm, outward-facing adjacent face, convex corner > 12 degrees.
Hole circles, small engraved edges and rear mounting edges are left intact.
No stable Edge numbers are assumed; the current shape is examined each time.
"""
import math

# P25/P27/P68/P69 retain their undressed solid: valid OCCT chamfers on those
# thin multi-facet skins tessellated with self-overlaps.  Do not hide that
# defect with coarse mesh welding; their original boundary is retained.
TARGET_PARTS=frozenset(('P20','P21','P22','P23','P24','P26',
                        'P38','P39','P60','P61'))

def _valid(candidate,source_volume):
    return (not candidate.isNull() and candidate.isValid()
            and len(candidate.Solids)==1 and candidate.Volume>0
            and candidate.Volume<=source_volume*(1+1e-8))

def _edge_candidates(shape):
    """Return straight edges plus their measured local face classification."""
    side=1 if shape.BoundBox.Center.x>=0 else -1
    result=[]
    for index,edge in enumerate(shape.Edges):
        if edge.Length<=4.0 or len(edge.Vertexes)!=2:
            continue
        chord=(edge.Vertexes[0].Point-edge.Vertexes[1].Point).Length
        # The chord check also accepts straight OCCT B-spline representations,
        # while excluding circular hole arcs and curved panel outlines.
        if abs(edge.Length-chord)>1e-5:
            continue
        midpoint=edge.valueAt((edge.FirstParameter+edge.LastParameter)*.5)
        normals=[]
        for face in shape.Faces:
            if not any(edge.isSame(fe) for fe in face.Edges):
                continue
            try:
                u,v=face.Surface.parameter(midpoint)
                n=face.normalAt(u,v)
                if n.Length>1e-8:
                    n.normalize();normals.append(n)
            except Exception:
                continue
        outward=any(n.x*side>.45 for n in normals)
        angle=0.0;convex=False
        if len(normals)==2:
            angle=math.degrees(math.acos(max(-1.0,min(1.0,normals[0].dot(normals[1])))))
            inward=normals[0]+normals[1]
            if inward.Length>1e-4:
                inward.normalize()
                convex=shape.isInside(midpoint-inward*.05,1e-5,True)
        result.append({'index':index,'length_mm':float(edge.Length),
                       'midpoint_mm':[float(midpoint.x),float(midpoint.y),float(midpoint.z)],
                       'outward':outward,'convex':convex,'angle_deg':angle})
    return result

def apply_edge_break(shape,pid):
    """Return (shape, metadata), falling back unchanged after checked failure.

    Try the complete set of visible convex outline edges at 0.35 and 0.25 mm.
    If OCCT cannot dress the full set, add up to six longest eligible edges,
    checking each proposed combination against the ORIGINAL shape.  Both sizes
    are attempted, then the combination with greatest treated edge length wins.
    This avoids cumulative topology-dependent Edge renumbering.
    """
    metadata={'eligible':pid in TARGET_PARTS,'applied':False,'partial':False,
              'size_mm':0.0,'strategy':'not_requested','selected_edge_count':0,
              'eligible_edge_count':0,'attempt_count':0,'selected_edges':[]}
    if pid not in TARGET_PARTS:
        return shape,metadata
    source_volume=shape.Volume
    if not _valid(shape,source_volume):
        metadata['strategy']='invalid_input_unchanged'
        return shape,metadata
    candidates=_edge_candidates(shape)
    selected_pool=[c for c in candidates if c['outward'] and c['convex'] and c['angle_deg']>12.0]
    metadata['eligible_edge_count']=len(selected_pool)
    metadata['straight_edge_count']=len(candidates)
    metadata['source_volume_mm3']=float(source_volume)
    if not selected_pool:
        metadata['strategy']='no_eligible_outer_edges'
        return shape,metadata
    def attempt(entries,size):
        metadata['attempt_count']+=1
        try:
            candidate=shape.makeChamfer(size,[shape.Edges[e['index']] for e in entries])
            if _valid(candidate,source_volume):
                return candidate
        except Exception:
            pass
        return None
    def finish(candidate,entries,size,strategy):
        metadata.update({'applied':True,'partial':len(entries)<len(selected_pool),
                         'size_mm':float(size),'strategy':strategy,
                         'selected_edge_count':len(entries),'selected_edges':entries,
                         'result_volume_mm3':float(candidate.Volume),
                         'removed_volume_mm3':float(source_volume-candidate.Volume),
                         'valid':True,'solids':1})
        return candidate,metadata
    for size in (.35,.25):
        candidate=attempt(selected_pool,size)
        if candidate is not None:
            return finish(candidate,selected_pool,size,'all_outward_convex_long_edges')
    preferred=sorted(selected_pool,key=lambda c:c['length_mm'],reverse=True)
    best=None;best_score=(-1,-1,-1)
    for size in (.35,.25):
        chosen=[];last=None
        for item in preferred:
            if len(chosen)>=6:
                break
            candidate=attempt(chosen+[item],size)
            if candidate is not None:
                chosen.append(item);last=candidate
        if last is not None:
            score=(sum(e['length_mm'] for e in chosen),len(chosen),size)
            if score>best_score:
                best_score=score;best=(last,chosen,size)
    if best is not None:
        return finish(*best,'partial_greedy_outer_edges')
    metadata['strategy']='no_valid_chamfer_unchanged'
    metadata['partial']=True
    metadata['valid']=True;metadata['solids']=1
    return shape,metadata
