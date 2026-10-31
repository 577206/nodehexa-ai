"""Isolated QA experiment. Reads R04 review; never overwrites the review scene.

Tolerance trials operate on copies of the original mesh data. Reports both
topology and the unchanged assembly contacts; none are hidden or relabeled.
"""
import bpy, bmesh, json, sys, math
from pathlib import Path
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'04_review/qa_r04_mesh_experiment'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'03_assembly/Lingxi_Cockpit_R04_review.blend'))
sys.path.insert(0,'/Users/dyke_4/.codex/skills/blender-asset-qa/scripts')
import qa_check

def serial(v):
    if isinstance(v,(int,float,str,bool)) or v is None:return v
    try:return list(v)
    except:return repr(v)

diag={'blender':bpy.app.version_string,'materials':{},'objects':{},'lights':{},'trials':{}}
for name,mat in bpy.data.materials.items():
    diag['materials'][name]={'use_nodes':mat.use_nodes,'diffuse_color':list(mat.diffuse_color),'nodes':[], 'links':[]}
    if mat.node_tree:
        diag['materials'][name]['nodes']=[{'name':n.name,'type':n.type,'is_active_output':getattr(n,'is_active_output',None),'inputs':{s.name:serial(s.default_value) for s in n.inputs if hasattr(s,'default_value')}} for n in mat.node_tree.nodes]
        diag['materials'][name]['links']=[{'from_node':l.from_node.name,'from_socket':l.from_socket.name,'to_node':l.to_node.name,'to_socket':l.to_socket.name} for l in mat.node_tree.links]
for ob in bpy.data.objects:
    if ob.type=='MESH' and (ob.get('part_id') in ['P01','P14','P16','P38']):
        diag['objects'][ob.name]={'materials':[s.material.name if s.material else None for s in ob.material_slots], 'polygon_slots':sorted(set(p.material_index for p in ob.data.polygons)), 'modifiers':[(m.name,m.type) for m in ob.modifiers]}
    if ob.type=='LIGHT':diag['lights'][ob.name]={'energy':ob.data.energy,'location':list(ob.location),'type':ob.data.type}
diag['view']={k:serial(getattr(bpy.context.scene.view_settings,k)) for k in ['view_transform','look','exposure','gamma']}
print('MATERIALS_DIAGNOSTIC',json.dumps({k:diag[k] for k in ['materials','objects','lights','view']}), flush=True)

targets=[o for o in bpy.data.objects if o.type=='MESH' and o.get('part_id') in ['P01','H29','H30','H31','H32']]
orig={ob.name:ob.data.copy() for ob in targets}

def volume(ob):
    bm=bmesh.new();bm.from_mesh(ob.data)
    result=bm.calc_volume(signed=True);bm.free();return result

def sampled_surface_change(a,b):
    """Bidirectional vertex + triangle-centroid distances; not exact Hausdorff."""
    def points_tree(me):
        me.calc_loop_triangles()
        verts=[v.co.copy() for v in me.vertices]
        tris=[tuple(t.vertices) for t in me.loop_triangles]
        points=verts+[(verts[t[0]]+verts[t[1]]+verts[t[2]])/3 for t in tris]
        return points,BVHTree.FromPolygons(verts,tris,all_triangles=True)
    pa,ta=points_tree(a);pb,tb=points_tree(b)
    return max(max(tb.find_nearest(p)[3] for p in pa),max(ta.find_nearest(p)[3] for p in pb))*1000

for ob in targets:
    diag['trials'][ob.name]=[]
    original_volume=volume(ob)
    for tol in [0,1e-7,1e-6,5e-6,1e-5]:
        ob.data=orig[ob.name].copy()
        if tol:
            bm=bmesh.new();bm.from_mesh(ob.data)
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=tol)
            bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=tol)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            bm.to_mesh(ob.data);bm.free()
        q=qa_check.run(objects=[ob.name],profile='print',eps=5e-6,tol=.0003,no_modifiers=True,uv=False)
        v=volume(ob)
        trial={'distance_m':tol,'volume_m3':v,'volume_change_percent':100*(v-original_volume)/original_volume,'qa':q}
        diag['trials'][ob.name].append(trial)
        print('TRIAL',ob.name,tol,'errors',q['errors'],'volume_change_percent',trial['volume_change_percent'],flush=True)
    for angle in [1e-4,.001,.01]:
        ob.data=orig[ob.name].copy()
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.dissolve_limit(bm,angle_limit=angle,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
        q=qa_check.run(objects=[ob.name],profile='print',eps=5e-6,tol=.0003,no_modifiers=True,uv=False)
        v=volume(ob)
        trial={'method':'limited_dissolve','angle_radians':angle,'sampled_surface_change_mm':sampled_surface_change(orig[ob.name],ob.data),'volume_m3':v,'volume_change_percent':100*(v-original_volume)/original_volume,'qa':q}
        diag['trials'][ob.name].append(trial)
        print('PLANAR_TRIAL',ob.name,angle,'errors',q['errors'],'volume_change_percent',trial['volume_change_percent'],flush=True)
    if ob.get('part_id','').startswith('H'):
        ob.data=orig[ob.name].copy()
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.dissolve_limit(bm,angle_limit=.001,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
        bmesh.ops.poke(bm,faces=[f for f in bm.faces if len(f.verts)>4],offset=0,center_mode='MEAN_WEIGHTED')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
        q=qa_check.run(objects=[ob.name],profile='print',eps=5e-6,tol=.0003,no_modifiers=True,uv=False)
        v=volume(ob)
        trial={'method':'planar_caps_centroid_fan','sampled_surface_change_mm':sampled_surface_change(orig[ob.name],ob.data),'volume_m3':v,'volume_change_percent':100*(v-original_volume)/original_volume,'qa':q}
        diag['trials'][ob.name].append(trial)
        print('CAP_FAN_TRIAL',ob.name,'errors',q['errors'],'volume_change_percent',trial['volume_change_percent'],flush=True)
    # Keep the topology-preserving best trial in the separate experiment scene.
    # All other assembly contacts remain unchanged and are reported below.
    ob.data=orig[ob.name].copy()
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm,angle_limit=.01 if ob.get('part_id')=='P01' else .001,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
    if ob.get('part_id','').startswith('H'):
        bmesh.ops.poke(bm,faces=[f for f in bm.faces if len(f.verts)>4],offset=0,center_mode='MEAN_WEIGHTED')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()

diag['assembly_after_cleaned_targets']=qa_check.run(objects=[o.name for o in bpy.data.objects if o.type=='MESH' and o.get('part_id')],profile='render',eps=5e-6,tol=.0003,no_modifiers=True,uv=False)
(OUT/'report.json').write_text(json.dumps(diag,indent=2,ensure_ascii=False))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'R04_mesh_cleanup_EXPERIMENT.blend'))
scene=bpy.context.scene
scene.render.resolution_x=600;scene.render.resolution_y=550
scene.cycles.samples=16
scene.view_settings.exposure=-3
scene.render.filepath=str(OUT/'exposure_minus3.png')
bpy.ops.render.render(write_still=True)
print('EXPERIMENT_COMPLETE',str(OUT),flush=True)
