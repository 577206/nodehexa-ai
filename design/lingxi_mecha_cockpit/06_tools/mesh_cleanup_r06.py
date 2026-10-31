"""Guarded review-mesh symmetry repair for R06 P63.

P62/P63 are explicitly mirrored CAD parts in build_r06.py. Their independent
OCC tessellations can triangulate small trimmed faces differently. This reuses
the right part's verified review tessellation for the left part; it does not
alter CAD solids or merge nearby vertices. Call after all STL imports and the
existing conservative per-part cleanup, before saving/rendering the scene.
"""
import sys
import bmesh
from mathutils import Matrix
from mathutils.bvhtree import BVHTree


def _sampled_deviation_mm(a, b):
    """Bidirectional vertex/triangle-centroid distance, not exact Hausdorff."""
    def points_and_tree(mesh):
        mesh.calc_loop_triangles()
        verts = [v.co.copy() for v in mesh.vertices]
        tris = [tuple(t.vertices) for t in mesh.loop_triangles]
        points = verts + [(verts[t[0]] + verts[t[1]] + verts[t[2]]) / 3 for t in tris]
        return points, BVHTree.FromPolygons(verts, tris, all_triangles=True)
    pa, ta = points_and_tree(a)
    pb, tb = points_and_tree(b)
    return 1000 * max(max(tb.find_nearest(p)[3] for p in pa),
                      max(ta.find_nearest(p)[3] for p in pb))


def _signed_volume(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    value = bm.calc_volume(signed=True)
    bm.free()
    return value


def repair_nominal_mirror(items, maximum_deviation_mm=.065):
    """Apply only P62 -> P63 reflection, restoring the original on failed QA."""
    import bpy
    sys.path.insert(0, '/Users/dyke_4/.codex/skills/blender-asset-qa/scripts')
    import qa_check

    source, target = items['P62'], items['P63']
    identity = Matrix.Identity(4)
    for ob in (source, target):
        if any(abs(ob.matrix_world[r][c] - identity[r][c]) > 1e-9
               for r in range(4) for c in range(4)):
            raise ValueError('R06 mirror cleanup expects assembly-coordinate meshes')
    original = target.data
    candidate = source.data.copy()
    candidate.name = original.name + '_symmetric_tessellation'
    candidate.transform(Matrix.Diagonal((-1, 1, 1, 1)))
    candidate.materials.clear()
    for mat in original.materials:
        candidate.materials.append(mat)
    bm = bmesh.new()
    bm.from_mesh(candidate)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(candidate)
    bm.free()
    try:
        deviation = _sampled_deviation_mm(original, candidate)
        if deviation > maximum_deviation_mm:
            raise ValueError(f'P63 mirror surface difference {deviation:.6f} mm exceeds tolerance')
        target.data = candidate
        qa = qa_check.run(objects=[target.name], profile='print', eps=.000005,
                          tol=.0003, no_modifiers=True, uv=False)
        if not qa['pass']:
            raise ValueError('P63 mirrored tessellation failed QA: ' + repr(qa['errors']))
        original_volume = _signed_volume(original)
        return {'part': 'P63', 'source': 'P62', 'method': 'nominal_CAD_mirror_tessellation',
                'sampled_surface_difference_mm': deviation,
                'volume_change_percent': 100 * (_signed_volume(candidate) - original_volume) / original_volume,
                'qa': qa}
    except Exception:
        target.data = original
        bpy.data.meshes.remove(candidate)
        raise
