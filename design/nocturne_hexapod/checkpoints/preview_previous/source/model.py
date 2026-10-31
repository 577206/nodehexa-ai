"""NOCTURNE first engineering draft: widened top frame and shin plate.

Only completed CAD parts are returned. This is deliberately not a placeholder
full-robot assembly. Other parts remain pending in spec/part_register.json.
Original reference contours are used without dimensional scaling; explicit
transverse pilot bores are reconstructed separately. All fits remain provisional.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from lower_frame import widened_bottom
import json
import yaml
from build123d import Face, Wire, Solid, Compound, Color, Pos, Rot, Cylinder, Box, Align, Kind, export_step

ROOT = Path(__file__).resolve().parents[1]


def load_parameters(path):
    return yaml.safe_load(Path(path).read_text())


def value(params, key):
    return float(params['parameters'][key]['value'])


def profile(name):
    return json.loads((ROOT/'validation/interfaces'/f'{name}_section.json').read_text())


def polygon(points, z=0):
    return Face(Wire.make_polygon([(x,y,z) for x,y in points], close=True))


def prism(points, z, thickness):
    return Solid.extrude(polygon(points,z), (0,0,thickness))


def plate(loops, thickness):
    outer=Wire.make_polygon([(x,y,0) for x,y in loops[0]],close=True)
    holes=[Wire.make_polygon([(x,y,0) for x,y in loop],close=True) for loop in loops[1:]]
    return Solid.extrude(Face(outer,holes),(0,0,thickness))


def reference_ground():
    data=profile('FootGround')
    shape=plate(data['loops_uv_mm'],data['thickness_mm'])
    for bore in data['transverse_bores']:
        y,z=bore['center_vw_mm']
        # Analytic pilot hole from measured original faceted cylinder vertices.
        tool=Pos(19.75,y,z)*Rot(0,90,0)*Cylinder(bore['radius_mm'],42)
        shape=shape-tool
    return shape


def widen_loop(loop, center, increase):
    """Translate the two sides rigidly and bridge only centerline crossings."""
    result=[]
    for i,a in enumerate(loop):
        b=loop[(i+1)%len(loop)]
        sign=1 if a[1]>=center else -1
        result.append([a[0],a[1]+sign*increase/2])
        if (a[1]-center)*(b[1]-center)<0:
            t=(center-a[1])/(b[1]-a[1])
            x=a[0]+t*(b[0]-a[0])
            result.extend([[x,center+sign*increase/2],[x,center-sign*increase/2]])
    return result


def widened_top(params):
    data=profile('BodyTop')
    ys=[point[1] for point in data['loops_uv_mm'][0]]
    center=(min(ys)+max(ys))/2
    increase=value(params,'body_width_increase')
    loops=[widen_loop(loop,center,increase) for loop in data['loops_uv_mm']]
    return plate(loops,data['thickness_mm'])


# Relief stays inside the original planar envelope and away from all outer
# connector islands. Its outward height still requires assembly sweep checking.
ARMOR_RAIL=[(6,50),(10,54),(18.2,43),(18.2,20),(15,7),(10,15),(6,24),(10.5,29),(10.5,38),(6,44)]
RED_RECESS=[(8.5,47),(15.5,37.5),(15.5,23),(12.8,17),(13.3,13.5),(17,22.7),(17,38),(9.2,49)]


def mirrored(points):
    return [(39.5-x,y) for x,y in points]


def ground_parts(params):
    base=reference_ground()
    t=value(params,'ground_plate_thickness')
    h=value(params,'armor_raise')
    depth=value(params,'inlay_depth')
    gap=value(params,'inlay_clearance')
    inserts=[]
    for suffix, rail, recess in [('L',ARMOR_RAIL,RED_RECESS),('R',mirrored(ARMOR_RAIL),mirrored(RED_RECESS))]:
        # New relief is bonded into the base geometry, not a separate spacer
        # under any original screw head. Original interfaces remain at 3 mm.
        bottom_wire=polygon(rail,t).outer_wire()
        middle_wire=polygon(rail,t+h-.4).outer_wire()
        top_wire=polygon(rail).outer_wire().offset_2d(-.35,kind=Kind.INTERSECTION)
        top_wire=Pos(0,0,t+h)*top_wire
        blade=Solid.make_loft([bottom_wire,middle_wire,top_wire],ruled=True)
        base=base+blade
        base=base-prism(recess,t+h-depth,depth+0.05)
        wire=polygon(recess).outer_wire().offset_2d(-gap,kind=Kind.INTERSECTION)
        insert=Solid.extrude(Face(wire),(0,0,depth-gap))
        insert=Pos(0,0,t+h-depth)*insert
        insert.label=f'N112_{suffix}_red_insert_DRAFT'
        insert.color=Color(0.65,0.025,0.045)
        inserts.append(insert)
    base.label='N111_shin_face_DRAFT'
    base.color=Color(0.13,0.14,0.16)
    return [base,*inserts]


def local_parts(params):
    top=widened_top(params)
    top.label='N001_upper_frame_W30_DRAFT'
    top.color=Color(0.18,0.19,0.21)
    return [top,*ground_parts(params), widened_bottom("BodyButtom",value(params,"body_width_increase")), widened_bottom("BodyButtom-18650-2S",value(params,"body_width_increase"))]


def build_model(params):
    parts=local_parts(params)
    # Inspection layout only, not a claimed assembled-robot transform.
    laid_out=[parts[0]]
    for p in parts[1:]:
        offset=(0,140,0) if p.label.startswith("N002") else (0,280,0) if p.label.startswith("N003") else (155,12,0)
        placed=Pos(*offset)*p
        placed.label=p.label
        placed.color=p.color
        laid_out.append(placed)
    return Compound(label='NOCTURNE_partial_inspection_layout_NOT_FULL_ASSEMBLY',children=laid_out)


def write_step(model,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    export_step(model,str(path))
    # Export each manufacturing part in its own unshifted local coordinates.
    for part in local_parts(load_parameters(ROOT/'parameters.yaml')):
        export_step(part,str(path.parent/(part.label+'.step')))


if __name__=='__main__':
    model=build_model(load_parameters(ROOT/'parameters.yaml'))
    print({'parts':len(model.children),'valid':model.is_valid,'volume_mm3':model.volume})
