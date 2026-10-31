"""Read-only original mesh audit and unsimplified planar section references.

Profiles retain faceted source boundaries; they are not nominal fits or an
automatic reverse-engineering claim. Each reconstruction is validated separately.
"""
from pathlib import Path
import json
import hashlib
from collections import defaultdict
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]


def signed_area(points):
    p = np.asarray(points)
    return float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - p[:, 1] * np.roll(p[:, 0], -1)) / 2)


def section_loops(mesh, axis, height):
    origin = np.zeros(3)
    origin[axis] = height
    segments = trimesh.intersections.mesh_plane(mesh, np.eye(3)[axis], origin)
    edges, coordinates = defaultdict(set), {}
    for a, b in segments:
        ka, kb = tuple(np.round(a, 6)), tuple(np.round(b, 6))
        if ka == kb:
            continue
        coordinates[ka], coordinates[kb] = a, b
        edges[ka].add(kb)
        edges[kb].add(ka)
    if any(len(v) != 2 for v in edges.values()):
        raise ValueError('Section has branches/open edges; requires manual review')
    unused = set(edges)
    loops = []
    plane_axes = [i for i in range(3) if i != axis]
    while unused:
        start = min(unused)
        previous, current = None, start
        chain = []
        while True:
            chain.append(coordinates[current][plane_axes].tolist())
            unused.discard(current)
            following = sorted(edges[current] - ({previous} if previous else set()))[0]
            previous, current = current, following
            if current == start:
                break
        # Only remove numerically collinear split points, never round an interface.
        cleaned = []
        for i, point in enumerate(chain):
            a, b, c = np.array(chain[i-1]), np.array(point), np.array(chain[(i+1) % len(chain)])
            ab, bc = b-a, c-b
            cross = abs(ab[0]*bc[1]-ab[1]*bc[0])
            if cross > 1e-7 * max(np.linalg.norm(ab)+np.linalg.norm(bc), 1e-9):
                cleaned.append(point)
        loops.append(cleaned)
    return sorted(loops, key=lambda p: abs(signed_area(p)), reverse=True)


def main():
    report = []
    for path in sorted((ROOT/'inputs/original_chassis').glob('*.STL')):
        mesh = trimesh.load(path, force='mesh')
        report.append({'id':path.stem, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                       'watertight':bool(mesh.is_watertight), 'winding_consistent':bool(mesh.is_winding_consistent),
                       'volume_mm3':float(mesh.volume), 'bounds_xyz_mm':mesh.bounds.tolist(),
                       'triangles':len(mesh.faces), 'physical_fit_verified':False})
    (ROOT/'validation/original_mesh_audit.json').write_text(json.dumps(report,indent=2))
    for name, axis in [('FootGround',2),('BodyTop',1)]:
        path=ROOT/'inputs/original_chassis'/f'TKRC-{name}.STL'
        mesh=trimesh.load(path,force='mesh')
        limits=mesh.bounds[:,axis]
        # FootGround has two transverse screw bores at mid-thickness. The
        # near-bottom footprint is a separate reference from those bores.
        height=float(limits[0]+0.05 if name=='FootGround' else limits.mean())
        loops=section_loops(mesh,axis,height)
        plane_axes=[i for i in range(3) if i!=axis]
        offset=mesh.bounds[0,plane_axes]
        loops=[(np.array(loop)-offset).tolist() for loop in loops]
        thickness=float(limits[1]-limits[0])
        area=abs(signed_area(loops[0]))-sum(abs(signed_area(loop)) for loop in loops[1:])
        result={'source':str(path.relative_to(ROOT)), 'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'local_axes':['XYZ'[i] for i in plane_axes]+['XYZ'[axis]],
                'source_offset_xyz_mm':mesh.bounds[0].tolist(), 'section_height_mm':height,
                'thickness_mm':thickness,'loops_uv_mm':loops,
                'mesh_volume_mm3':float(mesh.volume),'prismatic_volume_mm3':area*thickness,
                'volume_difference_fraction':abs(area*thickness-mesh.volume)/mesh.volume,
                'status':'source-derived polygonal sections; non-prismatic details require explicit reconstruction'}
        if name=='FootGround':
            bores=[]
            for y in [30.04775,60.04775]:
                vertices=mesh.vertices
                section=vertices[(abs(vertices[:,1]-y)<1.1)&(vertices[:,2]>.05)&(vertices[:,2]<2.95)]
                yz=np.unique(np.round(section[:,1:3],6),axis=0)
                fit=np.linalg.lstsq(np.column_stack([2*yz[:,0],2*yz[:,1],np.ones(len(yz))]),np.sum(yz**2,axis=1),rcond=None)[0]
                radius=float(np.sqrt(fit[2]+fit[0]**2+fit[1]**2))
                error=float(np.max(abs(np.linalg.norm(yz-fit[:2],axis=1)-radius)))
                bores.append({'axis':'local u / original X','center_vw_mm':fit[:2].tolist(),
                              'radius_mm':radius,'fit_max_vertex_residual_mm':error,
                              'meaning':'original pilot bore, do not enlarge to nominal screw diameter'})
            result['transverse_bores']=bores
        (ROOT/'validation/interfaces'/f'{name}_section.json').write_text(json.dumps(result,indent=2))
        print(name, {'loops':len(loops),'points':[len(x) for x in loops],
                     'volume_difference_fraction':result['volume_difference_fraction']})


if __name__=='__main__':
    main()
