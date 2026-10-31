"""Animate accepted R06 CAD orientation + conceptual dual OLED overlays.

Loads the already accepted derivative scene; does not regenerate or edit CAD.
There is no inferred head-to-leg assembly placement in this scene.
"""
from pathlib import Path
import sys
import json
import hashlib
import bpy
from mathutils import Vector, Euler

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from actions import OUT,R02,REPO,FPS,ACTIONS,pose,verify_inputs

verify_inputs()
bpy.ops.wm.open_mainfile(filepath=str(R02/"current_sources_preview.blend"))
accepted=json.loads((R02/"render_manifest.json").read_text())
names=set(accepted["head_parts"])
for o in list(bpy.data.objects):
    if o.type=="MESH" and o.name not in names:
        bpy.data.objects.remove(o,do_unlink=True)
head=[bpy.data.objects[n] for n in names]
root=bpy.data.objects.new("Whole-body target orientation (not a neck)",None)
bpy.context.collection.objects.link(root)
for o in head:
    o.hide_render=False
    o.parent=root

textures={}
n=Vector((0,1,.5385)).normalized()
up=Vector((0,-n.z,n.y))
for side,name in [("left","REF_OLED_L"),("right","REF_OLED_R")]:
    board=bpy.data.objects[name]
    board_material=board.data.materials[0].copy()
    bs=board_material.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(.006,.008,.012,1)
    board.data.materials.clear();board.data.materials.append(board_material)
    vertices=[v.co for v in board.data.vertices]
    center=Vector(tuple((min(v[k] for v in vertices)+max(v[k] for v in vertices))/2 for k in range(3)))
    center+=n*(max(v.dot(n) for v in vertices)-center.dot(n)+.25)
    # An 18 mm concept overlay fits inside the reference envelope; this is NOT
    # an assertion about the real OLED active area. It is labeled in every video.
    verts=[center+Vector((x,0,0))+up*y for x,y in [(-9,-9),(9,-9),(9,9),(-9,9)]]
    mesh=bpy.data.meshes.new("Concept 8x8 eye overlay / "+side)
    mesh.from_pydata(verts,[],[(0,3,2,1)])
    mesh.uv_layers.new(name="UVMap")
    uvs=[(1,0),(0,0),(0,1),(1,1)]
    for loop in mesh.loops:
        mesh.uv_layers.active.data[loop.index].uv=uvs[loop.vertex_index]
    eye=bpy.data.objects.new("Concept expression, active area unmeasured / "+side,mesh)
    bpy.context.collection.objects.link(eye);eye.parent=root
    m=bpy.data.materials.new("Concept OLED "+side);m.use_nodes=True
    nodes=m.node_tree.nodes;nodes.clear()
    tex=nodes.new("ShaderNodeTexImage");tex.interpolation="Closest"
    em=nodes.new("ShaderNodeEmission");em.inputs["Strength"].default_value=1.8
    output=nodes.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(tex.outputs["Color"],em.inputs["Color"])
    m.node_tree.links.new(em.outputs[0],output.inputs["Surface"])
    mesh.materials.append(m);textures[side]=tex

scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE"
scene.eevee.taa_render_samples=16
scene.render.resolution_x=720;scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.fps=FPS
scene.render.film_transparent=True
scene.camera.data.ortho_scale=236
root.rotation_mode="QUATERNION"
results=[]
for action in ACTIONS:
    folder=OUT/action["id"]
    count=round(action["seconds"]*FPS)
    root.animation_data_clear()
    for side,tex in textures.items():
        tex.image=bpy.data.images.load(str(folder/"textures"/f"{side}_0001.png"),check_existing=False)
        tex.image.source="SEQUENCE"
        tex.image_user.frame_duration=count;tex.image_user.frame_start=1
        tex.image_user.frame_offset=0;tex.image_user.use_auto_refresh=True
    for i in range(count):
        p=pose(action,i/FPS)
        root.location=(p["x_mm"],p["y_mm"],p["z_mm"])
        root.rotation_quaternion=Euler(tuple(__import__('math').radians(p[k]) for k in ["rx_deg","ry_deg","rz_deg"]),"XYZ").to_quaternion()
        root.keyframe_insert("location",frame=i+1)
        root.keyframe_insert("rotation_quaternion",frame=i+1)
    scene.frame_start=1;scene.frame_end=count;scene.frame_set(1)
    scene.render.filepath=str(folder/"renders/head_")
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/"performance.blend"))
    bpy.ops.render.render(animation=True)
    results.append({"id":action["id"],"frames":count,"head_cad_parts":20,"concept_eyes":2})
(OUT/"render_checks.json").write_text(json.dumps({"status":"RENDERED_ACCEPTED_R06_CAD_ORIENTATION_STUDIES",
    "actions":results,"source_scene_sha256":hashlib.sha256((R02/"current_sources_preview.blend").read_bytes()).hexdigest(),
    "renderer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "geometry_modified":False,"neck_joint_added":False,"full_body_assembly_simulated":False,
    "concept_overlay_size_mm":18,"overlay_size_is_not_a_hardware_active_area_claim":True},ensure_ascii=False,indent=2)+"\n")
__result__={"actions":len(results),"frames":sum(r["frames"] for r in results)}
