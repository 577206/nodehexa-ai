"""Real nominal clearances for R06 upper-shell rear receiving pockets.

The validated U-frame / L-cradle design envelopes include the existing concave
edge breaks. Offset the simple 2D source outlines before extrusion, instead of
3D-offsetting the heavily trimmed final inserts (which OCCT cannot do reliably).
Only P02 is cut. P48 and P49 remain intact. No document is saved by this module.
This 0.20 mm review gap is not a qualified printing tolerance or retention check.
"""
import math
import FreeCAD as App
import Part

def _v(*p):return App.Vector(*p)
def _offset_polygon(points,inset):
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1]))
    sign=1 if area>0 else -1
    lines=[]
    for a,b in zip(points,points[1:]+points[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
        if length<1e-8:raise ValueError('Degenerate source outline edge')
        lines.append(((a[0]-sign*dy*inset/length,a[1]+sign*dx*inset/length),(dx,dy)))
    result=[]
    for i,(b,s) in enumerate(lines):
        a,r=lines[i-1];den=r[0]*s[1]-r[1]*s[0]
        if abs(den)<1e-10:raise ValueError('Parallel consecutive outline edges')
        t=((b[0]-a[0])*s[1]-(b[1]-a[1])*s[0])/den
        result.append((a[0]+t*r[0],a[1]+t*r[1]))
    return result

def _extrude(points,axis_start,length,axis):
    vv=[_v(x,axis_start,z) if axis=='y' else _v(axis_start,x,z) for x,z in points]
    face=Part.Face(Part.makePolygon(vv+[vv[0]]))
    return face.extrude(_v(0,length,0) if axis=='y' else _v(length,0,0))

def _state(shape):
    return {'valid':bool(shape.isValid()),'solids':len(shape.Solids),
            'volume_mm3':float(shape.Volume),'null':bool(shape.isNull())}

def _valid(state):
    return state['valid'] and not state['null'] and state['solids']==1 and state['volume_mm3']>0

def _tools(gap,bevel_frame,bevel_shelf):
    # R06 rear frame: outer contour, bottom-open central 36 x 22 cutout,
    # existing 45-degree concave edge break.  The concave break fills material
    # into the otherwise rectangular cutout, so it must be part of the envelope.
    b=bevel_frame
    rear=[(-32,8),(-18,8),(-18,30-b),(-18+b,30),(18-b,30),(18,30-b),
          (18,8),(32,8),(38,20),(35,35),(27,41),(-27,41),(-35,35),(-38,20)]
    if b<=1e-8:
        rear=[(-32,8),(-18,8),(-18,30),(18,30),(18,8),(32,8),
              (38,20),(35,35),(27,41),(-27,41),(-35,35),(-38,20)]
    rear_tool=_extrude(_offset_polygon(rear,-gap),41-gap,4+2*gap,'y')
    # R06 lower phone cradle: 66 x 12 x 4 shelf and 66 x 3 x 6 lip,
    # with the filled concave corner between the shelf top and the lip.
    b=bevel_shelf
    shelf=[(45,35),(57,35),(57,39),(48+b,39),(48,39+b),(48,42),(45,42)]
    if b<=1e-8:shelf=[(45,35),(57,35),(57,39),(48,39),(48,42),(45,42)]
    shelf_tool=_extrude(_offset_polygon(shelf,-gap),-33-gap,66+2*gap,'x')
    shelf_tool.rotate(_v(0,52,38),_v(1,0,0),-10)
    shelf_tool.translate(_v(0,-8,0))
    return [('P49',rear_tool),('P48',shelf_tool)]

def apply_rear_interface_clearance(doc,manifest,gap_mm=.20):
    """Return (report, changed_ids) after checked, in-memory P02 pocket cuts.

    Call after resolve_interfaces and re-export P02 when it appears in changed
    IDs. The tool validates containment of the current inserts, making changed
    source dimensions fail explicitly instead of silently using a stale pocket.
    """
    if not 0<gap_mm<=.35:raise ValueError('R06 review gap must be >0 and <=0.35 mm')
    entries=manifest.get('parts',[]) if isinstance(manifest,dict) else manifest
    by_id={entry['id']:entry for entry in entries}
    bevel_frame=float(by_id.get('P49',{}).get('edge_break_mm',.45))
    bevel_shelf=float(by_id.get('P48',{}).get('edge_break_mm',.45))
    report={'operation':'R06_rear_source_envelope_clearance','receiver':'P02',
            'nominal_review_gap_mm':float(gap_mm),'insert_parts':['P49','P48'],
            'existing_concave_edge_break_mm':{'P49':bevel_frame,'P48':bevel_shelf},
            'actions':[],'changed_ids':[],
            'limitations':['Nominal clearance is not print-fit or fastening approval.',
                           'Minimum wall thickness and insertion path need separate validation.']}
    receiver=doc.getObject('P02')
    if receiver is None:
        report['status']='rejected_missing_receiver';return report,[]
    changed=False
    for pid,tool in _tools(gap_mm,bevel_frame,bevel_shelf):
        action={'receiver':'P02','insert':pid};report['actions'].append(action)
        insert=doc.getObject(pid)
        if insert is None:
            action['status']='rejected_missing_insert';continue
        before=receiver.Shape.copy();ins=insert.Shape.copy()
        action.update(before=_state(before),insert_state=_state(ins),tool_state=_state(tool))
        if not all(_valid(action[key]) for key in ('before','insert_state','tool_state')):
            action['status']='rejected_invalid_input_or_envelope';continue
        try:
            outside=float(ins.cut(tool).Volume)
            action['insert_outside_envelope_mm3']=outside
            if outside>1e-5:
                action['status']='rejected_source_envelope_no_longer_contains_insert';continue
            candidate=before.cut(tool).removeSplitter();state=_state(candidate)
            action['candidate']=state
            if not _valid(state):
                action['candidate_fragment_volumes_mm3']=[float(s.Volume) for s in candidate.Solids]
                action['status']='rejected_invalid_or_split_receiver';continue
            distance=float(candidate.distToShape(ins)[0])
            common=float(candidate.common(ins).Volume)
            action.update(measured_min_gap_mm=distance,remaining_overlap_mm3=common,
                          removed_volume_mm3=action['before']['volume_mm3']-state['volume_mm3'])
            if (distance<gap_mm-1e-5 or common>1e-6
                    or state['volume_mm3']>action['before']['volume_mm3']+1e-6):
                action['status']='rejected_gap_or_volume_check';continue
            receiver.Shape=candidate;changed=True
            action.update(status='applied',after=state,insert_unchanged=True)
        except Exception as ex:
            action.update(status='rejected_exception',error=str(ex))
    if changed:
        doc.recompute();report['changed_ids']=['P02']
    report['final_measured_gaps_mm']={pid:float(receiver.Shape.distToShape(doc.getObject(pid).Shape)[0])
                                    for pid in ('P49','P48') if doc.getObject(pid) is not None}
    report['status']='NOMINAL_GAP_VERIFIED_FIT_UNVERIFIED' if all(a['status']=='applied' for a in report['actions']) else 'REQUIRES_REVIEW'
    return report,list(report['changed_ids'])
