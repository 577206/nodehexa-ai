"""Render revisioned CAD tessellation, without changing its geometric design.

Run in an isolated Blender process:
  Blender -b --factory-startup --python-exit-code 1 -P render_R04_blender.py
  Blender -b --factory-startup --python-exit-code 1 -P render_R04_blender.py -- --qa-only
Source coordinates: millimetres, front +Y, left -X, up +Z.
No CAD part moves, no bevel/modifier/kitbash geometry is added. The studio floor,
lights and cameras are presentation-only. Same-coordinate vertex indexing is
welded exactly, without a merge-distance threshold or position changes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SKILLS = Path('/Users/dyke_4/.codex/skills')
EXCLUDED = ('REF_FIXED_BOWL', 'REF_BOARDS', 'REF_SOFT_PAD')


def dump(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4


def rgba(hex_color):
    code = hex_color.lstrip('#')
    if len(code) == 6:
        code += 'FF'
    if len(code) != 8:
        raise ValueError('Expected #RRGGBBAA: ' + hex_color)
    vals = [int(code[i:i + 2], 16) / 255 for i in (0, 2, 4, 6)]
    return (*[linear(v) for v in vals[:3]], vals[3])


def input_value(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def material_for(source):
    name = source['name']
    color = source.get('color', '#58616CFF')
    upper = name.upper()
    if 'CLEAR_VISOR' in upper:
        kind = 'ClearVisor'
    elif 'OLED_PIXELS' in upper:
        kind = 'OLED_AmberPixels'
    elif 'REF_CAMERA_LENS_GLASS' in upper:
        kind = 'CameraOpticalGlass'
    elif 'REF_CAMERA_LENS_HOUSING' in upper:
        kind = 'CameraBlackHousing'
    elif 'REF_DISPLAY' in upper:
        kind = 'OLED_BlackDisplay'
    elif 'REF_OLED_' in upper:
        kind = 'OLED_PCB'
    elif 'REF_EDGE_MASK' in upper:
        kind = 'OLED_BlackMask'
    elif 'REF_PHONE' in upper:
        kind = 'PhoneReference'
    else:
        kind = 'Plastic_' + color.lstrip('#')[:6]
    key = 'M_' + kind
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
    base = rgba(color)
    input_value(bsdf, 'Base Color', (*base[:3], 1))
    input_value(bsdf, 'Metallic', 0)
    input_value(bsdf, 'Roughness', .37)
    input_value(bsdf, 'IOR', 1.49)
    input_value(bsdf, 'Specular IOR Level', .5)
    input_value(bsdf, 'Coat Weight', .05)
    input_value(bsdf, 'Coat Roughness', .24)
    mat.diffuse_color = (*base[:3], 1)
    if kind == 'ClearVisor':
        # Transmission uses the *same CAD cover solid*, not a hidden replacement.
        # Clear optical material is illustrative; print transparency remains process-dependent.
        tint = rgba('#EAF5FAFF')
        input_value(bsdf, 'Base Color', tint)
        input_value(bsdf, 'Transmission Weight', 1)
        input_value(bsdf, 'Roughness', .075)
        input_value(bsdf, 'Coat Weight', .12)
        input_value(bsdf, 'Coat Roughness', .08)
        input_value(bsdf, 'Alpha', 1)
        absorb = nodes.new('ShaderNodeVolumeAbsorption')
        absorb.inputs['Color'].default_value = rgba('#CFE8F2FF')
        absorb.inputs['Density'].default_value = 1
        links.new(absorb.outputs['Volume'], output.inputs['Volume'])
        mat.diffuse_color = (*tint[:3], .30)
    elif kind == 'CameraOpticalGlass':
        input_value(bsdf, 'Base Color', rgba('#81758FFF'))
        input_value(bsdf, 'Transmission Weight', .96)
        input_value(bsdf, 'Roughness', .055)
        input_value(bsdf, 'IOR', 1.52)
        input_value(bsdf, 'Coat Weight', .16)
    elif kind == 'CameraBlackHousing':
        input_value(bsdf, 'Base Color', rgba('#1C2025FF'))
        input_value(bsdf, 'Roughness', .27)
    elif kind == 'OLED_AmberPixels':
        amber = rgba('#FFAC36FF')
        input_value(bsdf, 'Base Color', amber)
        input_value(bsdf, 'Emission Color', amber)
        input_value(bsdf, 'Emission Strength', 3.5)
        input_value(bsdf, 'Roughness', .25)
    elif kind in ('OLED_BlackDisplay', 'OLED_BlackMask'):
        input_value(bsdf, 'Base Color', rgba('#0E1419FF'))
        input_value(bsdf, 'Roughness', .23 if kind == 'OLED_BlackDisplay' else .5)
    elif kind == 'PhoneReference':
        input_value(bsdf, 'Roughness', .21)
    elif kind.startswith('Plastic_'):
        # Micro-roughness changes only shading. No bump, bevel or displacement.
        texcoord = nodes.new('ShaderNodeTexCoord')
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 180
        noise.inputs['Detail'].default_value = 2
        ramp = nodes.new('ShaderNodeMapRange')
        ramp.inputs['From Min'].default_value = 0
        ramp.inputs['From Max'].default_value = 1
        ramp.inputs['To Min'].default_value = .31
        ramp.inputs['To Max'].default_value = .42
        links.new(texcoord.outputs['Generated'], noise.inputs['Vector'])
        links.new(noise.outputs['Fac'], ramp.inputs['Value'])
        links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
    return mat


def import_cad(data, asset_col, refs_col, core_only=False):
    objects, source_stats, excluded, phone = [], [], [], []
    for source in data['objects']:
        name = source['name']
        if core_only and bool(source.get('reference', name.startswith('REF_'))):
            excluded.append(name)
            continue
        if any(name.startswith(prefix) for prefix in EXCLUDED):
            excluded.append(name)
            continue
        original = source['vertices']
        vertices, mapping, seen = [], [], {}
        for xyz in original:
            key = tuple(float(v) for v in xyz)
            if key not in seen:
                seen[key] = len(vertices)
                vertices.append(tuple(v * .001 for v in key))
            mapping.append(seen[key])
        faces = [tuple(mapping[int(i)] for i in face) for face in source['faces']]
        if not vertices or not faces:
            raise ValueError('Empty CAD mesh: ' + name)
        if any(len(face) != 3 for face in faces):
            raise ValueError('Expected true CAD triangle tessellation: ' + name)
        mesh = bpy.data.meshes.new('CAD_' + name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        ob = bpy.data.objects.new('SM_' + name, mesh)
        is_ref = bool(source.get('reference', name.startswith('REF_')))
        (refs_col if is_ref else asset_col).objects.link(ob)
        ob['cad_name'] = name
        ob['cad_part_id'] = str(source.get('part_id', name))
        ob['cad_reference_only'] = is_ref
        ob['cad_geometric_transform'] = 'source mm × 0.001; no rotation/translation'
        ob['cad_source_triangle_count'] = len(faces)
        ob.data.materials.append(material_for(
            source))
        # Keep source tessellation normals/flat face orientation; no modifiers.
        for polygon in mesh.polygons:
            polygon.use_smooth = False
        if name.startswith('REF_PHONE'):
            ob.hide_render = True
            phone.append(ob)
        else:
            objects.append(ob)
        source_stats.append({'name': ob.name, 'source_name': name,
                             'reference': is_ref, 'part_id': ob['cad_part_id'],
                             'input_vertices': len(original),
                             'exact_coordinate_vertices': len(vertices),
                             'triangles': len(faces),
                             'unchanged_faces': True,
                             'geometry_modifiers': 0})
    bpy.context.view_layer.update()
    for stat in source_stats:
        stat['size_mm'] = [round(v * 1000, 5) for v in bpy.data.objects[stat['name']].dimensions]
    return objects, phone, source_stats, excluded


def bounds(objects):
    bpy.context.view_layer.update()
    pts = [ob.matrix_world @ Vector(corner) for ob in objects for corner in ob.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return pts, lo, hi


def point_at(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def area(col, name, loc, target, power, size, shape='DISK', size_y=None):
    light = bpy.data.lights.new(name, 'AREA')
    light.energy, light.shape, light.size = power, shape, size
    if size_y is not None and hasattr(light, 'size_y'):
        light.size_y = size_y
    ob = bpy.data.objects.new(name, light)
    col.objects.link(ob)
    ob.location = loc
    point_at(ob, target)
    return ob


def studio(objects, col):
    scene = bpy.context.scene
    pts, lo, hi = bounds(objects)
    center = (lo + hi) / 2
    span = max(hi - lo)
    world = bpy.data.worlds.new('World_NeutralStudio')
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (.23, .245, .27, 1)
    bg.inputs['Strength'].default_value = .35
    scene.world = world
    size = span * 100
    z = lo.z - .00005
    floor_mesh = bpy.data.meshes.new('StudioGroundMesh')
    floor_mesh.from_pydata([(-size, -size, z), (size, -size, z),
                           (size, size, z), (-size, size, z)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new('STUDIO_Ground', floor_mesh)
    col.objects.link(floor)
    floor.data.materials.append(material_for({'name': 'StudioFloor', 'color': '#B3B5B9FF'}))
    power_scale = .16 * (span / .18) ** 2
    area(col, 'LIGHT_Key', center + Vector((-1.65, 2, 2.5)) * span,
         center, 30 * power_scale, span * 1.8, 'RECTANGLE', span * 1.15)
    area(col, 'LIGHT_Fill', center + Vector((2.2, 1.25, 1.1)) * span,
         center, 10 * power_scale, span * 1.65)
    area(col, 'LIGHT_Rim', center + Vector((.65, -1.9, 2.15)) * span,
         center, 36 * power_scale, span * 1.3, 'RECTANGLE', span * 2)
    area(col, 'LIGHT_TopSoft', center + Vector((-.2, .1, 3.1)) * span,
         center, 6 * power_scale, span * 2.2)
    under = area(col, 'LIGHT_Underside', center + Vector((-.7, 1.25, -2)) * span,
                 center, 19 * power_scale, span * 1.75)
    under.hide_render = True
    return floor, under, center, pts, lo, hi


def make_camera(col, name, direction, points, center, perspective=False):
    cam_data = bpy.data.cameras.new(name)
    ob = bpy.data.objects.new(name, cam_data)
    col.objects.link(ob)
    direction = Vector(direction).normalized()
    rotation = (-direction).to_track_quat('-Z', 'Y')
    right, up = rotation @ Vector((1, 0, 0)), rotation @ Vector((0, 1, 0))
    x = [(p - center).dot(right) for p in points]
    y = [(p - center).dot(up) for p in points]
    depth = [(p - center).dot(direction) for p in points]
    width, height = max(x) - min(x), max(y) - min(y)
    frame_center = center + right * ((max(x) + min(x)) / 2) + up * ((max(y) + min(y)) / 2)
    if perspective:
        cam_data.type, cam_data.lens = 'PERSP', 85
        half_fov = math.atan(cam_data.sensor_width / (2 * cam_data.lens))
        distance = max(width, height) / (2 * math.tan(half_fov)) * 1.14 + max(depth)
    else:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = max(width, height) * 1.18
        distance = max(width, height) * 4
    cam_data.clip_start, cam_data.clip_end = .0001, distance + 4
    cam_data.dof.use_dof = False
    ob.location = frame_center + direction * distance
    point_at(ob, frame_center)
    return ob


def configure_cycles(samples):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .035
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 12
    scene.cycles.transparent_max_bounces = 12
    scene.cycles.sample_clamp_indirect = 8
    scene.render.use_persistent_data = True
    device = 'CPU'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.refresh_devices()
        for d in prefs.devices:
            d.use = d.type == 'METAL'
        if any(d.type == 'METAL' for d in prefs.devices):
            scene.cycles.device = 'GPU'
            device = 'METAL'
    except Exception as exc:
        print('CYCLES_CPU_FALLBACK', str(exc), flush=True)
        scene.cycles.device = 'CPU'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.threads_mode = 'AUTO'
    return device


def run_qa(objects, stats, excluded, source_path, output, revision, core_only, source_hash):
    sys.path.insert(0, str(SKILLS / 'blender-asset-qa' / 'scripts'))
    import qa_check
    real = [ob.name for ob in objects if not ob['cad_reference_only']]
    refs = [ob.name for ob in objects if ob['cad_reference_only']]
    # qa_check has absolute area/point-in-triangle epsilons. CAD tessellation
    # contains legitimate tiny triangles; audit exact source coordinates in mm
    # instead of meter-render coordinates so those tests measure zero geometry,
    # not a0.0001mm² render-detail threshold. No render/export vertex is changed.
    copies = []
    source_objects = {d['name']: d for d in json.loads(source_path.read_text())['objects']}
    name_map = {}
    for ob in objects:
        key = ob.name.removeprefix('SM_')
        if key not in source_objects:
            continue
        d = source_objects[key]
        mesh = bpy.data.meshes.new('QA_MM_' + key)
        mesh.from_pydata(d['vertices'], [], d['faces']); mesh.update()
        cp = bpy.data.objects.new('QA_MM_' + key, mesh)
        bpy.context.scene.collection.objects.link(cp)
        for mat in ob.data.materials: mesh.materials.append(mat)
        copies.append(cp); name_map[ob.name] = cp.name
    real = [name_map[n] for n in real]; refs = [name_map[n] for n in refs]
    # 20 microns is a CAD coplanarity audit, not a contact or print-fit test.
    # Contact tolerance accommodates deliberate sub-millimetre assembly gaps.
    actual = qa_check.run(objects=real, profile='render', eps=.02, tol=.75,
                          max_tris=500000, no_modifiers=True, uv=False)
    reference_reports = {name: qa_check.run(objects=[name], profile='render',
                          eps=.02, tol=.75, max_tris=500000,
                          no_modifiers=True, uv=False) for name in refs}
    qa = {'schema': 'lingxi.cad_render_qa.v1', 'revision': revision,
          'source_file': str(source_path), 'source_sha256': source_hash,
          'blender_version': bpy.app.version_string,
          'units': {'source': 'mm', 'blender': 'm', 'scale_factor': .001},
          'axis_convention': {'front': '+Y', 'left': '-X', 'up': '+Z'},
          'geometry_policy': 'Exact coordinate deduplication only; source positions and triangles unchanged; no modifiers.',
          'qa_coordinate_unit': 'millimeter, exact source coordinates in temporary copies',
          'qa_parameters_mm': {'coplanarity_eps': .02, 'assembly_contact_tol': .75},
          'asset': actual, 'hardware_reference_topology': reference_reports,
          'core_only': core_only,
          'scope_note': ('First-batch body, deep base and any included clear visor/retainer; second-batch screw-on decorative parts are not included in this source scene.'
                         if core_only else 'Full source CAD assembly for visual review.'),
          'objects': stats, 'excluded_reference_objects': excluded,
          'total_triangles': sum(s['triangles'] for s in stats),
          'materials': len(bpy.data.materials),
          'accepted_scope_notes': [
              'UV audit omitted: only procedural/solid materials, no texture delivery.',
              'Reference OLED boards, displays, mask and pixels are illustrative hardware envelopes; individual topology is audited separately.',
              'This rendering report is not CAD collision, dimensional fit or manufacturing approval.'
          ], 'visual_review_status': 'PENDING_IMAGE_INSPECTION'}
    if core_only:
        if revision == 'R06':
            qa['scope_note'] = 'Actual R05A first-batch core plus R06 separate decorative/phone parts. Hardware envelopes excluded; no reference device is printed.'
        qa['individual_print_mesh_checks'] = {
            name: qa_check.run(objects=[name], profile='print', eps=.02, tol=.75,
                               max_tris=500000, no_modifiers=True, uv=False)
            for name in real}
    for cp in copies:
        mesh = cp.data; bpy.data.objects.remove(cp, do_unlink=True); bpy.data.meshes.remove(mesh)
    dump(output, qa)
    return qa


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', '--scene', dest='source', type=Path, default=ROOT / 'review/cache/R04_scene.json')
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--revision', default=None)
    parser.add_argument('--core-only', action='store_true', help='Render printable parts only; exclude reference hardware; run per-part print QA.')
    parser.add_argument('--samples', type=int, default=48)
    parser.add_argument('--qa-only', action='store_true')
    parser.add_argument('--with-phone', action='store_true')
    parser.add_argument('--skip-qa-sheets', action='store_true')
    parser.add_argument('--views', nargs='+', default=None)
    args = parser.parse_args(argv)
    match = re.search(r'R[0-9]+[A-Z]?', args.source.stem)
    revision = args.revision or (match.group(0) if match else 'R04')
    if not re.fullmatch(r'R[0-9]+[A-Z]?', revision):
        raise ValueError('Revision must use R plus digits')
    core_only = args.core_only or revision == 'R05'
    args.output = args.output or ROOT / ('outputs/renders/' + revision)
    args.views = args.views or (['hero', 'bottom'] if core_only else ['hero', 'front', 'left', 'rear', 'bottom'])
    if not args.source.is_file():
        raise FileNotFoundError('CAD geometry has not been generated yet: ' + str(args.source))
    source_bytes = args.source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    data = json.loads(source_bytes)
    if not data.get('objects'):
        raise ValueError('No CAD objects in scene JSON')
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for col in list(bpy.data.collections):
        if col.users == 0:
            bpy.data.collections.remove(col)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    scene.unit_settings.length_unit = 'METERS'
    scene['source_cad_json'] = str(args.source)
    scene['source_cad_sha256'] = source_hash
    scene['review_notice'] = ('Real CAD tessellation. ' + revision + ' first-batch separate parts review; second-batch screw-on decorations not included.'
                              if core_only else 'Real CAD tessellation. ' + revision + ' draft; dimensions and assembly fit unverified.')
    scene['front_axis'] = '+Y'
    asset_col = collection('ASSET_Lingxi_' + revision + '_CAD')
    refs_col = collection('REFERENCE_Hardware_Approximate')
    studio_col = collection('STUDIO_Lookdev')
    objects, phone, stats, excluded = import_cad(data, asset_col, refs_col, core_only=core_only)
    floor, underlight, center, points, lo, hi = studio(objects, studio_col)
    cameras = {}
    directions = {'hero': (-1.15, 1.8, .95), 'front': (0, 1, .015),
                  'left': (-1, 0, .015), 'rear': (0, -1, .04), 'bottom': (0, .001, -1)}
    for key, direction in directions.items():
        cameras[key] = make_camera(studio_col, 'CAM_' + key, direction, points,
                                   center, perspective=(key == 'hero'))
    scene.camera = cameras['hero']
    device = configure_cycles(args.samples)
    args.output.mkdir(parents=True, exist_ok=True)
    qa_path = ROOT / ('validation/' + revision + '_blender_qa.json')
    qa = run_qa(objects, stats, excluded, args.source, qa_path, revision, core_only, source_hash)
    print('CAD_QA', qa['asset']['pass'], len(qa['asset']['errors']), 'errors', flush=True)
    blend = args.output / ('Lingxi_Head_' + revision + '_Actual_CAD.blend')
    scene.render.resolution_x = scene.render.resolution_y = 1400
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    if args.qa_only:
        print('QA_ONLY_COMPLETE', str(qa_path), flush=True)
        return
    renders = []
    for key in args.views:
        if key not in cameras:
            raise ValueError('Unknown camera view: ' + key)
        scene.camera = cameras[key]
        floor.hide_render = key == 'bottom'
        underlight.hide_render = key != 'bottom'
        scene.render.resolution_x = scene.render.resolution_y = 1400 if key == 'hero' else 1000
        target = args.output / (revision + '_' + key + '.png')
        scene.render.filepath = str(target)
        start = time.time()
        bpy.ops.render.render(write_still=True)
        renders.append({'view': key, 'path': str(target), 'size_bytes': target.stat().st_size,
                        'resolution': scene.render.resolution_x, 'seconds': round(time.time() - start, 1)})
        print('RENDER_COMPLETE', key, str(target), flush=True)
    if args.with_phone and phone:
        for ob in phone:
            ob.hide_render = False
        pts, phone_lo, phone_hi = bounds(objects + phone)
        phone_center = (phone_lo + phone_hi) / 2
        cam = make_camera(studio_col, 'CAM_phone_reference', directions['hero'], pts, phone_center, True)
        scene.camera = cam
        floor.hide_render = underlight.hide_render = False
        underlight.hide_render = True
        scene.render.resolution_x = scene.render.resolution_y = 1000
        target = args.output / (revision + '_phone_reference.png')
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        renders.append({'view': 'phone_reference', 'path': str(target),
                        'size_bytes': target.stat().st_size, 'resolution': 1000})
        for ob in phone:
            ob.hide_render = True
    sheets = []
    if not args.skip_qa_sheets:
        sys.path.insert(0, str(SKILLS / 'blender-asset-qa' / 'scripts'))
        sys.path.insert(0, str(ROOT / "source"))
        import cad_review_shots as review_shots
        # Skill default front is -Y; override direction table for this CAD frame.
        review_shots.DIRS.update(front=(0, 1, .15), left=(-1, 0, .15),
                                 back=(0, -1, .15), three_quarter=(-1, 1, .6))
        names = [ob.name for ob in objects if not ob['cad_reference_only']]
        for mode in ('random', 'wire'):
            path = args.output / (revision + '_QA_' + mode + '.png')
            result = review_shots.run(objects=names, out=str(path),
                                      views=(['three_quarter', 'bottom'] if core_only else ['front', 'left', 'back', 'three_quarter']),
                                      mode=mode, res=384 if core_only else 512)
            sheets.append(result)
    floor.hide_render, underlight.hide_render = False, True
    scene.camera = cameras['hero']
    scene.render.resolution_x = scene.render.resolution_y = 1400
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    qa['visual_review_images'] = renders
    qa['topology_review_sheets'] = sheets
    dump(qa_path, qa)
    manifest = {'revision': revision, 'source_sha256': source_hash,
                'source_unchanged_during_render': sha256(args.source) == source_hash,
                'core_only': core_only, 'scope_note': qa['scope_note'],
                'blend': str(blend), 'device': device, 'samples': args.samples,
                'asset_size_mm': [round(v * 1000, 4) for v in (hi - lo)],
                'objects': len(stats), 'triangles': qa['total_triangles'],
                'materials': len(bpy.data.materials), 'renders': renders,
                'qa_report': str(qa_path), 'qa_asset_pass': qa['asset']['pass'],
                'status': 'DRAFT_RENDER_REQUIRES_VISUAL_REVIEW_NOT_PRINT_RELEASE'}
    dump(ROOT / ('validation/' + revision + '_render_manifest.json'), manifest)
    print('ALL_RENDER_COMPLETE', json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
