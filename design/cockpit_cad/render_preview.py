"""Optional Blender preview of the FreeCAD-generated STL parts."""

import math
import os

import bpy
from mathutils import Vector


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, metallic=0, roughness=0.5, emission=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 3.0
    return mat


dark = material("Graphite printed shell", (0.19, 0.21, 0.24), 0.1)
gray = material("Light gray roof", (0.48, 0.50, 0.52), 0.1)
orange = material("Orange accent", (0.95, 0.26, 0.025), 0.1)
base_mat = material("Desk base", (0.26, 0.28, 0.31), 0.1)
glass = material("Smoked visor", (0.015, 0.019, 0.023), 0.2, 0.2)
eye_mat = material("Amber eyes", (1.0, 0.3, 0.015), 0, 0.35, (1.0, 0.18, 0.005))
floor_mat = material("Backdrop", (0.87, 0.88, 0.89))


def import_stl(name, mat):
    bpy.ops.wm.stl_import(filepath=os.path.join(OUT, name + ".stl"))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


for name, mat in (("BatteryTray", dark), ("UpperHull", dark),
                  ("RoofLid", gray), ("DesktopBase", base_mat),
                  ("PhoneRest", dark), ("CameraBezel", orange),
                  ("LeftAccent", orange), ("RightAccent", orange)):
    import_stl(name, mat)


def quad(name, points, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    solid = obj.modifiers.new("Thin sheet", "SOLIDIFY")
    solid.thickness = 1.0
    return obj


quad("Smoked window", [(-33, -35.3, 40), (33, -35.3, 40),
                        (33, -30.5, 62), (-33, -30.5, 62)], glass)

# Eyes are preview graphics. Their placement and PCB mounting remain provisional.
quad("Left expressive eye", [(-24, -36.1, 52), (-10, -36.1, 47),
                              (-9, -35.2, 50), (-23, -35.2, 56)], eye_mat)
quad("Right expressive eye", [(10, -36.1, 47), (24, -36.1, 52),
                               (23, -35.2, 56), (9, -35.2, 50)], eye_mat)


def cube(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=4.4, depth=1.0,
                                    location=(0, -37.2, 31),
                                    rotation=(math.pi / 2, 0, 0))
bpy.context.object.name = "Camera lens placeholder"
bpy.context.object.data.materials.append(glass)

cube("Ground", (0, 0, -13.8), (400, 400, 3), floor_mat)


def aim(obj, point):
    direction = Vector(point) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.light_add(type="AREA", location=(-110, -140, 180))
bpy.context.object.data.energy = 850
bpy.context.object.data.shape = "DISK"
bpy.context.object.data.size = 190
aim(bpy.context.object, (0, 0, 25))
bpy.ops.object.light_add(type="AREA", location=(100, 70, 120))
bpy.context.object.data.energy = 450
bpy.context.object.data.size = 130
aim(bpy.context.object, (0, 0, 20))

bpy.ops.object.camera_add(location=(170, -210, 135))
camera = bpy.context.object
aim(camera, (0, 0, 27))
camera.data.type = "ORTHO"
camera.data.ortho_scale = 200
bpy.context.scene.camera = camera

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.5
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.84, 0.9, 1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.45
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(OUT, "cockpit-preview.png")
bpy.ops.render.render(write_still=True)
print("Saved", scene.render.filepath)
