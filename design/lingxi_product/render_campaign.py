"""Derivative lighting renders from the approved frozen R02 mesh. No CAD edits."""
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent / 'assets/v2'
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.hide_render:
        bpy.data.objects.remove(o, do_unlink=True)
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)

def light(name, loc, energy, size, color):
    d = bpy.data.lights.new(name, 'AREA')
    d.energy, d.size, d.color = energy, size, color
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 12, 70))-o.location).to_track_quat('-Z','Y').to_euler()

light('large silver key', (180,310,400), 4200000, 230, (1,.94,.88))
light('quiet front fill', (-280,250,130), 1200000, 250, (.8,.84,.9))
light('crimson rim', (220,-220,190), 2800000, 150, (1,.035,.025))
# Reuse the previously disclosed 18 mm concept eye planes; no active-area claim.
normal=Vector((0,1,.5385)).normalized()
up=Vector((0,-normal.z,normal.y))
for side,name in [('left','REF_OLED_L'),('right','REF_OLED_R')]:
    board=bpy.data.objects[name]
    bs=board.data.materials[0].node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(.004,.005,.006,1)
    vertices=[v.co for v in board.data.vertices]
    center=Vector(tuple((min(v[k] for v in vertices)+max(v[k] for v in vertices))/2 for k in range(3)))
    center+=normal*(max(v.dot(normal) for v in vertices)-center.dot(normal)+.25)
    verts=[center+Vector((x,0,0))+up*y for x,y in [(-9,-9),(9,-9),(9,9),(-9,9)]]
    mesh=bpy.data.meshes.new('Concept eye '+side)
    mesh.from_pydata(verts,[],[(0,3,2,1)])
    mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        mesh.uv_layers.active.data[loop.index].uv=[(1,0),(0,0),(0,1),(1,1)][loop.vertex_index]
    eye=bpy.data.objects.new('Concept smile '+side,mesh)
    scene.collection.objects.link(eye)
    m=bpy.data.materials.new('Concept OLED '+side);m.use_nodes=True
    nodes=m.node_tree.nodes;nodes.clear()
    tex=nodes.new('ShaderNodeTexImage');tex.interpolation='Closest'
    tex.image=bpy.data.images.load(str(OUT.parents[2]/'robot_theater/actions_r03/hold_that_compliment/textures'/f'{side}_0055.png'))
    em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=3
    output=nodes.new('ShaderNodeOutputMaterial')
    m.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
    m.node_tree.links.new(em.outputs[0],output.inputs['Surface'])
    mesh.materials.append(m)
scene.render.engine='BLENDER_EEVEE'
scene.eevee.taa_render_samples=128
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.resolution_x=1400
scene.render.resolution_y=1400
scene.view_settings.exposure=-.8
scene.world.color=(.07,.07,.07)
camera=scene.camera
camera.data.type='ORTHO'
camera.data.ortho_scale=215
target=Vector((0,12,70))
for name, direction in [('head-hero',(1,1.8,.75)),('head-front',(0,1,.12)),('head-side',(-1,.25,.25)),('head-detail',(.65,1.9,.5))]:
    camera.location=target+Vector(direction).normalized()*650
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
