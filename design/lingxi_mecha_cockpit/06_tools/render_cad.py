"""Render the actual CAD exports; never substitutes cosmetic geometry for them."""
import bpy
import json
import os
import sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
iteration=args[0] if args else 'iteration_01'
OUT=ROOT/'04_review'/iteration
OUT.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'03_assembly/manifest.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def material(name,color,metallic=.2,rough=.42):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=rough
    return m

mats={
    'gray':material('graphite armor',(.19,.205,.22),.25,.42),
    'dark':material('dark graphite',(.065,.075,.085),.22,.42),
    'black':material('black recess',(.012,.015,.019),.15,.48),
    'orange':material('safety orange',(.98,.16,.008),.1,.32),
    'glass':material('smoked bronze glazing',(.16,.115,.075),.02,.12),
    'light':material('amber light guides',(1,.3,.008),.05,.22),
    'metal':material('nickel metal',(.55,.57,.59),.8,.27),
    'gold':material('gold contacts',(.85,.55,.15),.8,.25)
}
g=mats['glass'].node_tree.nodes.get('Principled BSDF')
g.inputs['Transmission Weight'].default_value=.88;g.inputs['IOR'].default_value=1.45
l=mats['light'].node_tree.nodes.get('Principled BSDF')
l.inputs['Emission Color'].default_value=(1,.23,.004,1);l.inputs['Emission Strength'].default_value=9

items={}
for p in manifest['parts']:
    bpy.ops.wm.stl_import(filepath=str(ROOT/p['stl']))
    ob=bpy.context.object;ob.name=p['id']+'_'+p['slug']
    ob.data.materials.append(mats[p['material']]);ob['part_id']=p['id']
    ob['source_step']=p['folder']+'/'+p['id']+'.step'
    if p['category']=='fdm':
        bevel=ob.modifiers.new('Render edge highlights (0.22 mm)','BEVEL')
        bevel.width=.22;bevel.segments=2
        ob.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    items[p['id']]=ob

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

floor_mat=material('matte neutral stage',(.67,.69,.72),0,.7)
bpy.ops.mesh.primitive_plane_add(size=1800,location=(0,0,-14.3))
floor=bpy.context.object;floor.name='STUDIO_floor';floor.data.materials.append(floor_mat)
for pos,energy,size in [((-160,-190,240),220000,190),((150,-40,170),130000,160),((40,160,220),230000,170)]:
    bpy.ops.object.light_add(type='AREA',location=pos)
    ob=bpy.context.object;ob.data.energy=energy;ob.data.size=size;aim(ob,(0,0,38))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.8,.85,.95,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.resolution_x=1500;scene.render.resolution_y=1300;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
bpy.ops.object.camera_add(location=(140,-200,130))
cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam

def render(name,position,target,scale):
    cam.location=position;cam.data.ortho_scale=scale;aim(cam,target)
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)

render('01_assembled',(140,-200,135),(0,0,45),172)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'03_assembly/Lingxi_Cockpit_R03_review.blend'))
render('02_front',(0,-260,49),(0,0,49),150)
render('03_right',(250,-5,70),(0,0,45),165)
if '--all' in args:
    render('04_rear',(0,260,70),(0,0,45),160)
    render('05_top',(0,0,270),(0,0,25),155)
    floor.hide_render=True
    render('06_underside',(135,-175,-175),(0,0,20),178)
    floor.hide_render=False

# Exploded display transforms only; the CAD assembly remains unchanged.
for pid,ob in items.items():
    if pid=='P02':ob.location.z+=55
    elif pid in ['P03','P04','P05','P06','P07','P08']:
        ob.location.y-=48;ob.location.z+=38
    elif pid in ['P09','P11','P21','P23','P24']:
        ob.location.x+=43;ob.location.z+=35
    elif pid in ['P10','P12','P22','P25','P26']:
        ob.location.x-=43;ob.location.z+=35
    elif pid in ['P13','P14','P15','P16','P17','P18','P19','P20','H01']:
        ob.location.y-=37
    elif pid in ['P27','P28']:ob.location.z+=85
    elif pid in ['P29','P30','P31','P32','P33']:ob.location.y+=36;ob.location.z+=20
    elif pid in ['P34','H06','H07','H08','H09']:ob.location.y+=40;ob.location.z-=10
render('07_exploded',(205,-275,210),(0,0,70),310)
print('RENDER_COMPLETE',iteration)
