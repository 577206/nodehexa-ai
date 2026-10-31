"""Render frozen current CAD meshes and release STLs, without CAD regeneration."""
from pathlib import Path
import bpy
from mathutils import Vector
import json
import hashlib
import math

OUT = Path(__file__).resolve().parents[1]
REPO = OUT.parents[2]
lock = json.loads((OUT / "sources.lock.json").read_text())
for record in lock["sources"]:
    path = REPO / record["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise ValueError(f"Source changed after collection: {path}")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, transparent=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    c = tuple(int(color[k:k+2], 16) / 255 for k in [1, 3, 5])
    bs = m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value = (*c, 1)
    bs.inputs["Metallic"].default_value = .18
    bs.inputs["Roughness"].default_value = .38
    if transparent:
        bs.inputs["Transmission Weight"].default_value = .7
        bs.inputs["Alpha"].default_value = .25
        bs.inputs["Roughness"].default_value = .16
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "DITHERED"
    return m


materials = {}
head_data = json.loads((REPO / lock["head_mesh"]).read_text())
head_manifest = json.loads((REPO / "design/lingxi_head_simplified/review/manifest.json").read_text())
parts = {p["id"]: p for p in head_manifest["parts"]}
groups = {}
for f in head_data["faces"]:
    groups.setdefault(f["part_id"], []).append(f["indices"])
head_objects = []
head_bounds = {}
for name, faces in groups.items():
    part = parts[name]
    # Show the two explicitly modeled board envelopes, but no invented active area.
    if part["reference"] and name not in ["REF_OLED_L", "REF_OLED_R"]:
        continue
    used = sorted({i for f in faces for i in f})
    indices = {n: i for i, n in enumerate(used)}
    vertices = [head_data["vertices"][i] for i in used]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], [[indices[i] for i in f] for f in faces])
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    color = part["color"]
    m = material(name, color, name == "H03_CLEAR_VISOR")
    mesh.materials.append(m)
    if name.startswith("REF_"):
        m.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .75
    head_objects.append(o)
    mins = [min(v[k] for v in vertices) for k in range(3)]
    maxs = [max(v[k] for v in vertices) for k in range(3)]
    head_bounds[name] = {"min": mins, "max": maxs, "label": part["label"], "reference": part["reference"]}

camera_data = bpy.data.cameras.new("source render camera")
camera = bpy.data.objects.new("source render camera", camera_data)
bpy.context.collection.objects.link(camera)
camera_data.type = "ORTHO"
camera_data.clip_end = 10000
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 32
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.world.color = (.3, .3, .3)
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.7


def area(name, loc, energy, size):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    o = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector((0, 0, 60)) - o.location).to_track_quat("-Z", "Y").to_euler()


area("key", (280, 350, 470), 3500000, 300)
area("fill", (-300, 150, 200), 2200000, 330)
area("rim", (30, -250, 250), 2400000, 240)


def render(name, target, direction, scale, resolution=1000):
    target = Vector(target)
    camera.location = target + Vector(direction).normalized() * 650
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.ortho_scale = scale
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.filepath = str(OUT / "renders" / (name + ".png"))
    bpy.ops.render.render(write_still=True)


render("head_hero", (0, 12, 70), (1, 1.8, 1.0), 230)
render("head_front", (0, 12, 70), (0, 1, 0), 205)
render("head_left", (0, 12, 70), (-1, 0, 0), 215)
for o in head_objects:
    o.hide_render = True

release_root = REPO / "design/red_black_print_release_20261031"
release = json.loads((release_root / "manifest.json").read_text())
items = release["parts"] + release["optional"]
black = material("printed black", "#242A30")
red = material("printed red", "#BA2639")
atlas = []
for i, item in enumerate(items):
    path = release_root / item["file"]
    bpy.ops.wm.stl_import(filepath=str(path))
    o = bpy.context.object
    o.name = path.stem
    o.data.materials.clear()
    color = item.get("color", "BLACK")
    o.data.materials.append(red if color == "RED" else black)
    bbox = [o.matrix_world @ Vector(v) for v in o.bound_box]
    mins = Vector(tuple(min(v[k] for v in bbox) for k in range(3)))
    maxs = Vector(tuple(max(v[k] for v in bbox) for k in range(3)))
    center = (mins + maxs) / 2
    # Move the object only in the derivative render scene; original STL untouched.
    o.location -= center
    dimensions = maxs - mins
    smallest = min(range(3), key=lambda k: dimensions[k])
    direction = [(1, -2, 1), (1, -3, 1.8), (1, -1.6, 3)][smallest]
    image_name = f"part_{i:02d}"
    render(image_name, (0, 0, 0), direction, max(dimensions) * 1.48, 480)
    atlas.append({"image": "renders/" + image_name + ".png", "file": item["file"],
                  "source": item.get("source", "optional original part"),
                  "name": path.name, "quantity": item["quantity"], "color": color,
                  "optional": i >= len(release["parts"]), "dimensions_mm": list(dimensions),
                  "sha256": item["sha256"]})
    o.hide_render = True

for o in head_objects:
    o.hide_render = False
render("head_hero", (0, 12, 70), (1, 1.8, 1.0), 230)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "current_sources_preview.blend"))
(OUT / "render_manifest.json").write_text(json.dumps({"status": "CURRENT_SOURCE_MESHES_RENDERED",
    "head_geometry_source": lock["head_mesh"], "head_parts": head_bounds,
    "head_print_parts": sum(not p["reference"] for p in head_bounds.values()),
    "oled_envelopes_shown": 2, "body_parts": atlas,
    "head_native_coordinate_system": "+X right, +Y front, +Z up; millimeters",
    "assembly_claim": "No full robot assembly is shown or inferred",
    "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, ensure_ascii=False, indent=2) + "\n")
__result__ = {"head_print_parts": 20, "rendered_stl_types": len(atlas), "out": str(OUT)}
