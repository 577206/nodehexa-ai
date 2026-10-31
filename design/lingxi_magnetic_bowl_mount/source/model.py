"""R02 bottom-insert fixed hollow docking hood; source/spec/parameters are authoring truth.
No normal build writes STEP. Use the skill export tool after preview acceptance.
"""
from pathlib import Path
import yaml
from build123d import RectangleRounded,Plane,Pos,Box,Cylinder,Align,loft,extrude,Color
ROOT=Path(__file__).resolve().parents[1]

def load_parameters(path):
    return yaml.safe_load(Path(path).read_text())

def value(params,name):
    return float(params['parameters'][name]['value'])

def rr(w,r,z=0):
    return Plane.XY.offset(z)*RectangleRounded(w,w,r)

def fixed_hood(params):
    p=lambda n:value(params,n)
    roof=p('ceiling_height')+p('roof_thickness')
    outside=loft([rr(p('base_outer'),p('outer_corner_radius')),rr(p('roof_outer'),p('outer_corner_radius'),roof)])
    cavity=loft([rr(p('inner_bottom'),p('inner_corner_radius'),-.1),rr(p('inner_top'),p('inner_corner_radius'),p('ceiling_height'))])
    return outside-cavity

def screw_centers(params):
    h=value(params,'cover_hole_pitch')/2
    return [(-h,0),(h,0)]

def two_recessed_screw_wells(params,body):
    p=lambda n:value(params,n)
    roof=p('ceiling_height')+p('roof_thickness')
    for x,y in screw_centers(params):
        body=body+Pos(x,y,0)*Cylinder(p('well_outer_diameter')/2,roof,align=(Align.CENTER,Align.CENTER,Align.MIN))
    for x,y in screw_centers(params):
        shaft=Pos(x,y,-.1)*Cylinder(p('screw_clearance_diameter')/2,roof+2,align=(Align.CENTER,Align.CENTER,Align.MIN))
        access=Pos(x,y,p('screw_seat_thickness'))*Cylinder(p('well_access_diameter')/2,roof+2,align=(Align.CENTER,Align.CENTER,Align.MIN))
        body=body-shaft-access
    return body

def connector_pocket(params,body):
    # R02: connector enters from -Z, front housing passes through collar.
    # End flange remains below collar; no narrow solder passage or pocket floor.
    p=lambda n:value(params,n)
    roof=p('ceiling_height')+p('roof_thickness')
    boss=Pos(0,0,roof-.2)*extrude(RectangleRounded(p('boss_length'),p('boss_width'),2),amount=p('collar_top_z')-roof+.2)
    body=body+boss
    throat=Pos(0,0,p('ceiling_height')-1)*extrude(RectangleRounded(p('throat_length'),p('throat_width'),p('throat_width')/2-.02),amount=p('collar_top_z')-p('ceiling_height')+2)
    return wire_exit(params,body-throat)

def wire_exit(params,body):
    p=lambda n:value(params,n)
    # Broad below-roof relief ends at flange support plane, open to interior.
    relief=Pos(0,0,p('ceiling_height')-1)*extrude(RectangleRounded(p('relief_length'),p('relief_width'),2),amount=p('flange_stop_z')-p('ceiling_height')+1)
    return body-relief

def head_keyed_nest(params,body):
    p=lambda n:value(params,n)
    roof=p('ceiling_height')+p('roof_thickness')
    rim=extrude(RectangleRounded(p('guide_outer'),p('guide_outer'),5)-RectangleRounded(p('guide_inner'),p('guide_inner'),3),amount=p('guide_height')+.1)
    body=body+Pos(0,0,roof-.1)*rim
    # Asymmetric key, to be inherited by the future head counterpart.
    body=body+Pos(11,p('guide_outer')/2,roof+p('guide_height')/2)*Box(6,4,p('guide_height'))
    return body

def build_model(params):
    model=fixed_hood(params)
    model=two_recessed_screw_wells(params,model)
    model=connector_pocket(params,model)
    model=head_keyed_nest(params,model).clean()
    model.label='B001_FIXED_MAGNETIC_HOOD_R02'
    model.color=Color(.12,.14,.17)
    return model

def write_step(model,path):
    from build123d import export_step
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    export_step(model,str(path))

def main():
    model=build_model(load_parameters(ROOT/'parameters.yaml'))
    print({'valid':model.is_valid,'solids':len(model.solids()),'bbox_mm':list(model.bounding_box().size),'volume_mm3':model.volume})

if __name__=='__main__':main()
