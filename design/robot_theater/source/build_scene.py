"""Blender scene: existing visual cockpit + analytic six-leg rig, offline only."""
import bpy
from mathutils import Vector, Matrix
import math
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from timeline import OUT, ROOT, FPS, DURATION, geometry, pose

G = geometry()
HEIGHT = G["standby_height_mm"] + 2.2
L0, L1, L2, L3 = [G[k] for k in ["kLegRootToJoint1", "kLegJoint1ToJoint2", "kLegJoint2ToJoint3", "kLegJoint3ToTip"]]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def mat(name, color, metallic=0.0, roughness=0.4):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Metallic"].default_value = metallic
    bs.inputs["Roughness"].default_value = roughness
    return m


armor = mat("Study | graphite", (.13, .155, .18), .55)
orange = mat("Study | orange", (.95, .18, .025), .15)
black = mat("Study | servo", (.022, .032, .043), .3)
silver = mat("Study | hinge", (.36, .4, .43), .7, .28)
rubber = mat("Study | sole", (.045, .055, .065), 0, .8)
floor_mat = mat("Study | warm studio", (.75, .74, .70), 0, .9)


def cube(name, size, material, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    bevel = o.modifiers.new("Rounded manufactured edges", "BEVEL")
    bevel.width = 1.0
    bevel.segments = 2
    o.modifiers.new("Normals", "WEIGHTED_NORMAL")
    return o


def bar(name, width, depth, material):
    return cube(name, (width, depth, 1), material)


def set_bar(obj, a, b):
    a, b = Vector(a), Vector(b)
    delta = b - a
    obj.location = (a + b) / 2
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    obj.scale.z = delta.length


def sphere(name, radius, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


root = bpy.data.objects.new("PERFORMANCE_ROOT__not_a_neck", None)
bpy.context.collection.objects.link(root)
for z, w, d in [(-9, 70, 124), (3, 76, 132)]:
    o = cube("Simplified chassis plate", (w, d, 4), armor, root)
    o.location = (0, 0, z)
o = cube("Low battery volume (schematic)", (42, 70, 18), black, root)
o.location = (0, 0, -5)

# Copy only the visual cockpit. Original source is never saved or modified.
src = ROOT / "design/cockpit_cad/output/Lingxi-Mecha-Cockpit-Visual-v2.blend"
exclude = ["desk", "foot", "phone", "magnet", "contact", "eye", "studio floor", "underside docking"]
with bpy.data.libraries.load(str(src), link=False) as (data_from, data_to):
    data_to.objects = [n for n in data_from.objects if not any(k in n.lower() for k in exclude)]
for o in data_to.objects:
    if o is None:
        continue
    if o.type != "MESH":
        bpy.data.objects.remove(o)
        continue
    bpy.context.collection.objects.link(o)
    o.parent = root
    o.location.z += 10

# Display has the planned 29.4 x 14.7 mm active area, 128 x 64 single-bit pixels.
# Surface basis: right +X, up (0,.6,.8), normal (0,-.8,.6).
screen = bpy.data.meshes.new("OLED active rectangle")
center = Vector((0, -39.1, 55.0))
up = Vector((0, .6, .8))
verts = [center + Vector((x, 0, 0)) + up * z
         for x, z in [(-14.7, -7.35), (14.7, -7.35), (14.7, 7.35), (-14.7, 7.35)]]
screen.from_pydata(verts, [], [(0, 1, 2, 3)])
screen.uv_layers.new(name="UVMap")
for loop, uv in zip(screen.uv_layers.active.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
    loop.uv = uv
display = bpy.data.objects.new("Single monochrome OLED (planned)", screen)
bpy.context.collection.objects.link(display)
display.parent = root
display_mat = bpy.data.materials.new("128x64 single-bit animation")
display_mat.use_nodes = True
nodes = display_mat.node_tree.nodes
nodes.clear()
tex = nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(str(OUT / "textures/oled_0001.png"))
tex.image.source = "SEQUENCE"
tex.image_user.frame_duration = round(FPS * DURATION)
tex.image_user.frame_start = 1
tex.image_user.use_auto_refresh = True
tex.interpolation = "Closest"
emission = nodes.new("ShaderNodeEmission")
emission.inputs["Strength"].default_value = 1.3
output = nodes.new("ShaderNodeOutputMaterial")
display_mat.node_tree.links.new(tex.outputs["Color"], emission.inputs["Color"])
display_mat.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
screen.materials.append(display_mat)

mx, my, sx = G["kLegMountOtherX"], G["kLegMountOtherY"], G["kLegMountLeftRightX"]
mounts = [(mx, my, 0), (sx, 0, 0), (mx, -my, 0), (-mx, -my, 0), (-sx, 0, 0), (-mx, my, 0)]
angles = [45, 0, -45, -135, 180, 135]
radial = L0 + L1 + L2 * .866 + L3 * .2588
feet = [Vector((m[0] + radial * math.cos(math.radians(a)),
                m[1] + radial * math.sin(math.radians(a)), 2.2)) for m, a in zip(mounts, angles)]
rigs = []
for i in range(6):
    bars = [bar(f"L{i+1} hip offset", 13, 12, black),
            bar(f"L{i+1} coxa", 13, 10, orange),
            bar(f"L{i+1} femur", 12, 9, orange),
            bar(f"L{i+1} tibia", 9, 7, armor)]
    joints = [sphere(f"L{i+1} joint {j}", 6 if j != 0 else 7, silver if j == 2 else black) for j in range(4)]
    foot = sphere(f"L{i+1} fixed contact", 3.5, rubber)
    foot.scale.z = .63
    foot.location = feet[i]
    rigs.append((bars, joints))


def rotation(p):
    return (Matrix.Rotation(math.radians(p["rz_deg"]), 3, "Z") @
            Matrix.Rotation(math.radians(p["ry_deg"]), 3, "Y") @
            Matrix.Rotation(math.radians(p["rx_deg"]), 3, "X"))


def solve_leg(i, R, T):
    mount = Vector(mounts[i])
    C = Matrix.Rotation(math.radians(angles[i]), 3, "Z")
    target = C.transposed() @ (R.transposed() @ (feet[i] - T) - mount)
    x, y, z = target
    q0 = math.atan2(y, x - L0)
    planar = math.hypot(x - L0, y) - L1
    dist = math.hypot(planar, z)
    c = (dist * dist + L2 * L2 - L3 * L3) / (2 * L2 * dist)
    c2 = (dist * dist - L2 * L2 + L3 * L3) / (2 * L3 * dist)
    if not (-1 <= c <= 1 and -1 <= c2 <= 1):
        raise ValueError(f"Unreachable leg {i}: {target}")
    alpha, beta = math.acos(c), math.acos(c2)
    q1 = math.atan2(z, planar) + alpha
    q2 = math.pi / 2 - alpha - beta
    d = Vector((math.cos(q0), math.sin(q0), 0))
    p0 = Vector((0, 0, 0))
    p1 = Vector((L0, 0, 0))
    p2 = p1 + d * L1
    p3 = p2 + d * (L2 * math.cos(q1)) + Vector((0, 0, L2 * math.sin(q1)))
    end = p3 + d * (L3 * math.cos(q1 + q2 - math.pi / 2)) + Vector((0, 0, L3 * math.sin(q1 + q2 - math.pi / 2)))
    points = [R @ (mount + C @ p) + T for p in [p0, p1, p2, p3, end]]
    return points, [math.degrees(q) for q in [q0, q1, q2]], (points[-1] - feet[i]).length


# Validate at the firmware's nominal 20 ms tick, independent of render sampling.
mins, maxs = [999] * 3, [-999] * 3
max_error = 0.0
violations = []
for step in range(601):
    t = step / 50
    p = pose(t)
    R = rotation(p)
    T = Vector((p["x_mm"], p["y_mm"], HEIGHT + p["z_mm"]))
    for i in range(6):
        points, qs, error = solve_leg(i, R, T)
        max_error = max(max_error, error)
        for j, q in enumerate(qs):
            mins[j], maxs[j] = min(mins[j], q), max(maxs[j], q)
            lo, hi = [(-45, 45), (-45, 75), (-60, 60)][j]
            if q < lo or q > hi:
                violations.append([step, i, j, q])
if violations:
    raise ValueError(f"Servo limits violated: {violations[:3]}")

for frame in range(1, round(FPS * DURATION) + 1):
    p = pose((frame - 1) / FPS)
    R = rotation(p)
    T = Vector((p["x_mm"], p["y_mm"], HEIGHT + p["z_mm"]))
    root.location = T
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = R.to_quaternion()
    root.keyframe_insert("location", frame=frame)
    root.keyframe_insert("rotation_quaternion", frame=frame)
    for i, (bars, joints) in enumerate(rigs):
        points, _, _ = solve_leg(i, R, T)
        for o, a, b in zip(bars, points, points[1:]):
            set_bar(o, a, b)
            for prop in ["location", "rotation_quaternion", "scale"]:
                o.keyframe_insert(prop, frame=frame)
        for o, pos in zip(joints, points):
            o.location = pos
            o.keyframe_insert("location", frame=frame)

o = cube("Studio floor", (2000, 2000, 2), floor_mat)
o.location.z = -1.8


def area(name, loc, power, size):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = power
    light.shape = "DISK"
    light.size = size
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((0, 0, 65)) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("Key softbox", (180, -260, 450), 4000000, 360)
area("Fill softbox", (-260, -140, 230), 2500000, 300)
area("Rim softbox", (60, 200, 310), 3500000, 230)
camera_data = bpy.data.cameras.new("Fixed audience camera")
camera = bpy.data.objects.new("Fixed audience camera", camera_data)
bpy.context.collection.objects.link(camera)
camera.location = (235, -590, 340)
camera.rotation_euler = (Vector((0, -4, 58)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 440
camera_data.lens = 48
camera_data.clip_end = 3000
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
scene.world.color = (.32, .32, .32)
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.65
scene.render.resolution_x = 1040
scene.render.resolution_y = 830
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = round(FPS * DURATION)
scene.render.filepath = str(OUT / "renders/pose_")
scene.frame_set(1)
report = {"status": "OFFLINE_PREVIEW_ONLY", "sample_interval_seconds": .02,
          "samples": 601, "legs": 6, "joint_angle_min_deg": mins, "joint_angle_max_deg": maxs,
          "servo_limit_violations": violations, "max_fk_foot_error_mm": max_error,
          "all_six_foot_targets_fixed": True,
          "not_validated": ["actual center of mass / stability", "body and leg collision", "loaded servo torque and speed", "electrical power", "OLED driver", "real speech / body / OLED synchronization"],
          "geometry": G, "cockpit_source": str(src.relative_to(ROOT))}
(OUT / "kinematic_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "theater_preview.blend"))
__result__ = {"blend": str(OUT / "theater_preview.blend"), "checks": report}
