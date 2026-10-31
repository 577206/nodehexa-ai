"""Review the identical R06 CAD tessellation in Blender. Separate scene from R03."""
import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'04_review/iteration_06c';OUT.mkdir(parents=True,exist_ok=True)
M=json.loads((ROOT/'03_assembly/manifest_R06.json').read_text())
# This script runs in an isolated background scene only.
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
asset=bpy.data.collections.new('ASSET_Cockpit_R06');scene.collection.children.link(asset)
desktop=bpy.data.collections.new('ASSET_Desktop_Base');scene.collection.children.link(desktop)
studio=bpy.data.collections.new('STUDIO');scene.collection.children.link(studio)
def relink(ob,col):
    for c in list(ob.users_collection):c.objects.unlink(ob)
    col.objects.link(ob)
def mat(name,color,rough=.4,metal=0):
    m=bpy.data.materials.new('M_'+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    return m,p
mats={}
for name,color in [('gray',(.15,.16,.175)),('dark',(.045,.05,.06)),('black',(.014,.017,.021)),('orange',(.95,.16,.008)),('glass',(.42,.32,.22)),('light',(1,.28,.006)),('metal',(.6,.62,.65)),('gold',(.83,.53,.17))]:
    m,p=mat(name,color,.39 if name not in ['glass','light'] else .13,1 if name in ['metal','gold'] else 0)
    if name=='glass':p.inputs['Transmission Weight'].default_value=.98;p.inputs['IOR'].default_value=1.45
    if name=='light':p.inputs['Emission Color'].default_value=(1,.23,.004,1);p.inputs['Emission Strength'].default_value=12
    mats[name]=m
lens_mat,lens_bsdf=mat('optical_coating',(.065,.025,.12),.11,.15)
lens_bsdf.inputs['Transmission Weight'].default_value=.7
lens_bsdf.inputs['IOR'].default_value=1.5
items={}
for p in M['parts']:
    bpy.ops.wm.stl_import(filepath=str(ROOT/p['stl']))
    ob=bpy.context.object;ob.name='SM_'+p['id']+'_'+p['slug'];ob.data.transform(Matrix.Scale(.001,4))
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    if p['id'] in ['P01','P21','P23','P32','P35','P62','P63']:bmesh.ops.dissolve_limit(bm,angle_limit=.01,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
    elif p['id'] in ['H29','H30','H31','H32']:
        bmesh.ops.dissolve_limit(bm,angle_limit=.001,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
        bmesh.ops.poke(bm,faces=[f for f in bm.faces if len(f.verts)>4],offset=0,center_mode='MEAN_WEIGHTED')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    ob.data.materials.clear();ob.data.materials.append(lens_mat if p['id']=='H02' else mats[p['material']]);ob['part_id']=p['id'];ob['CAD_source']=p['folder']+'/'+p['id']+'.FCStd'
    relink(ob,desktop if p['group']=='desktop_base' else asset)
    if p['group']=='desktop_base':ob.hide_render=True;ob.hide_set(True)
    # Edge lighting only, final geometry remains authored in CAD; no silhouette-changing mesh mods.
    items[p['id']]=ob
sys.path.insert(0,str(ROOT/'06_tools'))
from mesh_cleanup_r06 import repair_nominal_mirror
mirror_report=repair_nominal_mirror(items)
(OUT/'mirror_tessellation_qa.json').write_text(json.dumps(mirror_report,ensure_ascii=False,indent=2)+'\n')
floor_mat,_=mat('floor',(.65,.67,.7),.7)
bpy.ops.mesh.primitive_plane_add(size=2,location=(0,0,.003));floor=bpy.context.object;floor.name='STUDIO_Floor';floor.data.materials.append(floor_mat);relink(floor,studio)
def aim(ob,p):ob.rotation_euler=(Vector(p)-ob.location).to_track_quat('-Z','Y').to_euler()
for i,(pos,w,sz) in enumerate([((-.18,-.22,.30),8,.20),((.18,-.10,.16),4,.16),((.06,.19,.24),10,.17)]):
    bpy.ops.object.light_add(type='AREA',location=pos);ob=bpy.context.object;ob.name='STUDIO_Area_'+str(i);ob.data.energy=w/12;ob.data.size=sz;aim(ob,(0,0,.05));relink(ob,studio)
scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.8,.85,.95,1);bg.inputs['Strength'].default_value=.12
scene.render.engine='CYCLES';scene.cycles.samples=24 if '--quick' in sys.argv else 48;scene.cycles.use_denoising=True;scene.cycles.transmission_bounces=10
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=70 if '--quick' in sys.argv else 100
scene.render.image_settings.file_format='PNG'
bpy.ops.object.camera_add(location=(.16,-.22,.13));cam=bpy.context.object;cam.name='CAM_Review';cam.data.type='ORTHO';cam.data.clip_start=.001;cam.data.clip_end=10;scene.camera=cam;relink(cam,studio)
def pose(pos,scale=.17,target=(0,0,.053)):
    cam.location=pos;cam.data.ortho_scale=scale;aim(cam,target)
def render(name,pos,scale=.17,target=(0,0,.053)):
    pose(pos,scale,target);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
pose((.16,-.22,.125),.165)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active;s.clip_start=.0005;s.clip_end=10;s.region_3d.view_perspective='CAMERA';s.shading.type='MATERIAL';s.overlay.show_overlays=False
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'03_assembly/Lingxi_Cockpit_R06_review.blend'))
render('01_assembled',(.16,-.22,.125),.165)
render('02_front',(0,-.3,.06),.15)
render('03_right',(.3,-.001,.065),.155)
if '--all' in sys.argv:
    render('04_rear',(0,.3,.07),.15)
    render('05_top',(0,0,.3),.15,target=(0,0,.045))
    floor.hide_render=True;render('06_bottom',(.15,-.2,-.16),.16,target=(0,0,.045));floor.hide_render=False
if '--quick' in sys.argv:
    print('QUICK_RENDER_COMPLETE',flush=True)
    raise SystemExit(0)
# Explicit inspection cutaway, separate from all exterior comparison views.
# Only the glazing is temporarily hidden to show the real CAD ribs and clips.
for p in M['parts']:
    if p['category']=='clear_sheet':items[p['id']].hide_render=True
render('07_canopy_structure',(.10,-.18,.11),.11,target=(0,-.025,.057))
for p in M['parts']:
    if p['category']=='clear_sheet':items[p['id']].hide_render=False
# Numerical QA is saved as raw evidence. Assembly warnings are not suppressed.
sys.path.insert(0,'/Users/dyke_4/.codex/skills/blender-asset-qa/scripts')
import qa_check
qa=qa_check.run(objects=[ob.name for ob in items.values()],profile='render',eps=.000005,tol=.0003,no_modifiers=True,uv=False)
(OUT/'blender_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print('QA',len(qa['errors']),'errors',len(qa['warnings']),'warnings',flush=True)
sys.path.insert(0,str(ROOT/"06_tools"))
import review_shots_local as review_shots
visible_parts=[o.name for o in asset.objects]
review_shots.run(objects=visible_parts,out=str(OUT/'review_random.png'),mode='random',res=480)
review_shots.run(objects=visible_parts,out=str(OUT/'review_wire.png'),mode='wire',res=480)
print('RENDER_COMPLETE',flush=True)
