"""NOCTURNE first engineering draft: widened top frame and shin plate.

Only completed CAD parts are returned. This is deliberately not a placeholder
full-robot assembly. Other parts remain pending in spec/part_register.json.
Original reference contours are used without dimensional scaling; explicit
transverse pilot bores are reconstructed separately. All fits remain provisional.
"""
from pathlib import Path
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
ARMOR_RAIL=[(3.4,36.2),(6.5,35.2),(17.6,41.1),(17.6,44.6),(8.4,53.8),(4.7,53.8),(13.3,43.5)]
RED_RECESS=[(6.8,36.0),(15.3,41.8),(15.3,43.6),(9.1,49.8),(8.0,49.0),(13.7,43.1),(6.4,37.3)]


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
        base=base+prism(rail,0,t+h)
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
    return [top,*ground_parts(params)]


def build_model(params):
    parts=local_parts(params)
    # Inspection layout only, not a claimed assembled-robot transform.
    laid_out=[parts[0]]
    for p in parts[1:]:
        placed=Pos(155,12,0)*p
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
