"""R06 bolt-on orange vent frames and separate gray louvers.

Millimeters, +X robot right, +Y camera/front, +Z up. The R05A four core
solids are immutable. Each vent sandwiches its gray grille against the
existing two side bosses; the orange rim is the outer clamping piece.
No glue, decorative screw imitations, blind plastic threads or core edits.
"""
from pathlib import Path
import importlib.util
import json
import math
from build123d import *

ROOT = Path(__file__).resolve().parents[1]
_sp = importlib.util.spec_from_file_location('vent_r05a', ROOT / 'source/model_R05A_archive.py')
r05 = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(r05)
r04 = r05.r04
single, volume, mirror, through_x = r04.single, r04.volume, r04.mirror, r04.through_x
ORANGE, GRAY = '#F37824FF', '#7C8388FF'

# Angular silhouette and visible open aperture in side YZ view.
OUTLINE = [(9, 28), (18, 20), (42, 23), (54, 35), (50, 58), (38, 74), (18, 76), (8, 67)]
APERTURE = [(15, 36), (21, 31), (39, 33), (46, 40), (42, 57), (33, 64), (17, 63), (14, 57)]
AXES = [('UPPER', 22.0, 68.0, 58.44615384615385, 51.84615384615385, 25),
        ('LOWER', 23.0, 29.0, 62.6, 56.0, 20)]
MOUNTS = []


def _face(points, x):
    return Plane(origin=(x, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)) * r04.poly(points)


def _scaled(points, scale):
    cy, cz = 30, 48
    return [(cy + (y-cy)*scale, cz+(z-cz)*scale) for y, z in points]


def _right_parts():
    # Broad 1.5mm angled edge breaks are modeled into both exterior and opening.
    rim = loft([_face(OUTLINE, 65.4), _face(OUTLINE, 70.8),
                _face(_scaled(OUTLINE, .94), 72.8)], ruled=True)
    opening = loft([_face(APERTURE, 65.3), _face(APERTURE, 70.3),
                    _face(_scaled(APERTURE, 1.08), 72.9)], ruled=True)
    rim = rim - opening
    # Continuous gray perimeter. Five angled slats meet it at both ends.
    grille = r04.yz(OUTLINE, 63.0, 2.4) - r04.yz(APERTURE, 62.9, 2.6)
    for z in (36, 42, 48, 54, 60):
        blade = r04.xz([(63.5, z-1.35), (70.0, z-.1),
                        (70.0, z+1.9), (63.5, z+.65)], 54, 46)
        grille = grille + blade.intersect(r04.yz(OUTLINE, 62.9, 8))
    # Gray columns contact the frozen bosses after a 0.2mm clamp take-up.
    for tag, y, z, outer_x, inner_x, length in AXES:
        grille = grille + through_x(outer_x+.2, y, z, 3.8, 65.4-(outer_x+.2))
        rim = rim + through_x(65.4, y, z, 4.5, 7.4)
        grille = grille - through_x(50, y, z, 1.2, 26)
        rim = rim - through_x(64, y, z, 1.2, 10)
        # Ø4.6 pan-head recess; 2mm-deep cylindrical seat, not a countersink.
        rim = rim - through_x(70.8, y, z, 2.3, 4)
    # Upper boss sits on a sloping cheek. Relieve the surrounding column to the
    # original analytic exterior plus 0.2mm; the boss's flat seat stays intact.
    grille = grille - Pos(.2, 0, 0)*r04.envelope()
    grille = grille - rim
    return single(rim).clean(), single(grille).clean()


def build_parts(p):
    """Return genuinely separate colored solids; no main-model import cycle."""
    MOUNTS.clear()
    rim_r, grille_r = _right_parts()
    out = []
    for side, suffix in [(-1, 'L'), (1, 'R')]:
        frame_name = 'D01_VENT_FRAME_L' if side < 0 else 'D02_VENT_FRAME_R'
        grille_name = 'D03_VENT_GRILLE_L' if side < 0 else 'D04_VENT_GRILLE_R'
        for shape, name, color, label in [
            (rim_r, frame_name, ORANGE, ('左' if side < 0 else '右')+'橙色通风口外框'),
            (grille_r, grille_name, GRAY, ('左' if side < 0 else '右')+'灰色独立百叶')]:
            sh = mirror(shape, side)
            sh.label = name
            out.append({'shape': sh, 'name': name, 'color': color, 'label': label,
                        'hardware': '每侧共用上下两颗M2盘头螺丝；灰百叶夹在橙框与主体之间'})
        for tag, y, z, outer_x, inner_x, length in AXES:
            MOUNTS.append({'id': 'VENT_'+tag+'_'+suffix,
                'parts': [frame_name, grille_name],
                'centers_mm': [[side*outer_x, y, z]], 'axis': [side, 0, 0],
                'screw': f'M2x{length} pan head, head diameter<=4.4mm', 'quantity': 1,
                'nut': 'M2 AF4mm x 1.6mm, inside shell',
                'head_bearing_mm': [side*70.8, y, z],
                'nut_bearing_mm': [side*inner_x, y, z],
                'grille_bearing_mm': [side*(outer_x+.2), y, z],
                'through_diameter_mm': 2.4, 'head_recess_diameter_mm': 4.6,
                'head_recess_depth_mm': 2.0,
                'nominal_tip_past_nut_mm': length-(70.8-inner_x)-1.6,
                'note': '先装侧装饰，再装深腔底座。0.2mm装配间隙由紧固收拢；上M2x25，下M2x20。不能用锥形沉头螺丝。'})
    return out


def _nut(y, z, x):
    sk = Plane(origin=(x-1.6, y, z), x_dir=(0,1,0), z_dir=(1,0,0))*RegularPolygon(4/math.sqrt(3), 6)
    return extrude(sk, amount=1.6)-through_x(x-1.7,y,z,1.0,1.8)


def validate_and_cache():
    import trimesh
    cache = ROOT/'review/cache'
    core_names = ['H01_MAIN_SHELL','H02_DOCK_RECEIVER','H03_CLEAR_VISOR','H04_VISOR_FRAME']
    core = [(n, import_brep(cache/f'R05A_{n}.brep')) for n in core_names]
    parts = build_parts({})
    report = {'revision': 'R06', 'scope': 'separate side vents only',
              'coordinate_system': 'mm; +X right +Y front +Z up', 'parts': [],
              'pair_intersections_mm3': [], 'core_intersections_mm3': [],
              'extraction': [], 'fasteners': [], 'nut_access_without_base': [],
              'mounts': MOUNTS}
    for item in parts:
        sh = item['shape']; verts, faces = sh.tessellate(.04, .12)
        tm = trimesh.Trimesh(vertices=[tuple(v) for v in verts],faces=faces,process=True)
        record = {'name': item['name'], 'is_valid': sh.is_valid,'solids':len(sh.solids()),
                  'volume_mm3': sh.volume,'bbox_mm':list(sh.bounding_box().size),
                  'mesh_watertight':tm.is_watertight,'mesh_volume':tm.is_volume,
                  'mesh_components':len(tm.split(only_watertight=False))}
        report['parts'].append(record)
        assert sh.is_valid and len(sh.solids())==1 and tm.is_watertight and tm.is_volume
        export_brep(sh, cache/f"vent_R06_{item['name']}.brep")
        for name, c in core:
            v = volume(sh.intersect(c)); report['core_intersections_mm3'].append([item['name'],name,v]); print('intersection',item['name'],name,v,flush=True); assert v<1e-5
        side = -1 if item['name'].endswith('_L') else 1
        for d in (.1, .2, 1, 5, 20, 75):
            v=sum(volume((Pos(side*d,0,0)*sh).intersect(c)) for _,c in core)
            report['extraction'].append([item['name'],d,v]);assert v<1e-5
    for i,a in enumerate(parts):
        for b in parts[i+1:]:
            v=volume(a['shape'].intersect(b['shape']));report['pair_intersections_mm3'].append([a['name'],b['name'],v]); print('pair',a['name'],b['name'],v,flush=True);assert v<1e-5
    for side in (-1,1):
        for tag,y,z,outer_x,inner_x,length in AXES:
            nut=mirror(_nut(y,z,inner_x),side)
            tip=mirror(through_x(70.8-length,y,z,1.0,length),side)
            collisions={name:volume(nut.intersect(c)) for name,c in core}
            shaft_collisions={name:volume(tip.intersect(c)) for name,c in core}
            report['fasteners'].append({'side':side,'tag':tag,'nut_intersection_mm3':collisions,'shaft_intersection_mm3':shaft_collisions})
            print('fastener', side, tag, collisions, shaft_collisions, flush=True)
            assert max(collisions.values())<1e-5 and max(shaft_collisions.values())<1e-5
            # The detachable lower receiver is intentionally removed to fit nuts.
            # Approach radially from the open internal cavity, not through the
            # printed shell. Actual tool shape must be chosen for the open cavity.
            for d in (0, .2, 1, 3, 5, 10, 20):
                v = volume((Pos(-side*d,0,0)*nut).intersect(core[0][1]))
                report['nut_access_without_base'].append([side, tag, d, v])
                assert v < 1e-5
    report['assembly_order'] = ['移开H02下方深腔底座，从主体内放入M2螺母',
        '左右各先装灰色百叶，再套橙色外框',
        '每侧上孔M2x25、下孔M2x20盘头螺丝，轻轻拧紧',
        '确认透明盖和左侧USB线仍可拆装，再装回H02底座']
    report['limitations'] = ['螺钉/螺母为标称M2尺寸；实物打印装配尚未验证',
        '完整移除通风组件时先拆外框、再取灰色百叶；灰色百叶不应强行穿过橙框',
        '0.2mm初始轴向间隙用于装配，紧固时需轻压贴合，不可过紧']
    (ROOT/'validation/vent_R06_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    validate_and_cache()
