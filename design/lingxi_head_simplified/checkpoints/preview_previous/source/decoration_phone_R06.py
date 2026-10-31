"""R06 independent upright phone cradle, dimensions in mm.

X right, Y forward, Z up. R05A first-batch parts are immutable.
The phone slides down from +Z into a 76 x 13 mm channel on the rear (-Y).
75 mm cased phone width and approximately 10-12 mm thickness are confirmed.
Use thin soft pads at contact edges. This is a dimensioned fit prototype,
not a load test; the dimensions are read from project parameters.
"""
from pathlib import Path
import importlib.util
import json
import math
from build123d import *

ROOT=Path(__file__).resolve().parents[1]
_sp=importlib.util.spec_from_file_location('phone_r04',ROOT/'source/model_R04_archive.py')
r04=importlib.util.module_from_spec(_sp);_sp.loader.exec_module(r04)
box=r04.box;single=r04.single;volume=r04.volume;through_y=r04.through_y
GRAY='#7C8388FF';ORANGE='#F37824FF'
MOUNTS=[]

def _rounded(s,r=.55):
    """Fillet contact edges before holes; fail if the specified edge break fails."""
    return single(fillet(s.edges(),radius=r)).clean()

def _nut(x,y,z,af=4.0,t=1.6):
    return extrude(Plane(origin=(x,y,z),x_dir=(1,0,0),z_dir=(0,1,0))*RegularPolygon(af/math.sqrt(3),6,rotation=30),amount=t)

def build_parts(p):
    MOUNTS.clear()
    gap=r04.val(p,'phone_clear_width');depth=r04.val(p,'phone_clear_depth');top=r04.val(p,'phone_support_top')
    back=-74.0;foot=46.0;outer=gap/2+8
    # Rear plate sits 3 mm off the helmet except for the two measured mounting pads.
    outline=[(-outer+5,42),(outer-5,42),(outer,47),(outer,top-5),(outer-5,top),(-outer+5,top),(-outer,top-5),(-outer,47)]
    tray=r04.xz(outline,-70,4)
    window=[(-gap/2+8,64),(gap/2-8,64),(gap/2-8,top-11),(-gap/2+8,top-11)]
    tray=tray-r04.xz(window,-69,6)
    tray=tray+Pos(0,back-depth/2-.5,42)*extrude(RectangleRounded(gap+16,depth+9,1.5),amount=4)
    for x in [-25,25]:
        # Recess pan heads below the phone-contact plane. Seat Y=-72,
        # head top Y=-73.6, phone channel starts behind Y=-74.
        tray=tray+box(10,3,12,(x,-68.5,50))
        tray=tray-through_y(x,-80,50,1.2,20)
        tray=tray-through_y(x,-80,50,2.4,8)
    # Independent orange jaws; four real bolts along +Y, nuts on exposed front.
    parts=[]
    for side,tag in [(-1,'L'),(1,'R')]:
        jaw_profile=[(back,46.2),(back-depth-3,46.2),(back-depth-3,124),(back-depth,132),(back-4,136),(back,132)]
        # XY radii round the two inner longitudinal contact corners; straight
        # extrusions avoid tiny spherical slivers at joined lip intersections.
        guide=Pos(gap/2+4,back-depth/2-1.5,46.2)*extrude(RectangleRounded(8,depth+3,.7),amount=90)
        jaw=single(guide.intersect(r04.yz(jaw_profile,gap/2-.1,8.2)))
        jaw=jaw+Pos(gap/2-1,back-depth-1.5,46.2)*extrude(RectangleRounded(4,3,.6),amount=77.8)
        for z in [78,120]:
            jaw=jaw-through_y(gap/2+4,back-depth-8,z,1.2,depth+12)
            # Long recess leaves a Y=-80 screw bearing regardless of thickness.
            jaw=jaw-through_y(gap/2+4,back-depth-8,z,2.4,depth+2)
            tray=tray-through_y(side*(gap/2+4),back-1,z,1.2,7)
        jaw=r04.mirror(jaw,side)
        parts.append({'shape':single(jaw).clean(),'name':f'D15_PHONE_JAW_L' if side<0 else 'D16_PHONE_JAW_R','color':ORANGE,'label':f'手机支架橙色侧夹{tag} / 1件','hardware':f'每侧2×M2×12盘头螺丝＋2×M2螺母；手机净厚空间{depth:g}mm，适配用户约10–12mm带壳厚度'})
    tray=single(tray).clean()
    MOUNTS.extend([
        {'id':'PHONE_TO_BODY','parts':['D14_PHONE_BACK','H01_MAIN_SHELL'],'centers_mm':[[-25,-67,50],[25,-67,50]],'axis':[0,1,0],'screw':'M2x12 pan','quantity':2,'nut':'M2 AF4.0 x1.6; internal accessible loose nut','head_bearing_y_mm':-72.0,'nut_bearing_y_mm':-62.0,'note':'Install body nuts with docking base removed, before electronics. Pan heads recessed 2mm into rearplate to avoid phone contact. Two flat pads seat at Y=-67; do not use bracket as a lifting handle.'},
        {'id':'PHONE_JAWS','parts':['D14_PHONE_BACK','D15_PHONE_JAW_L','D16_PHONE_JAW_R'],'centers_mm':[[s*(gap/2+4),-74,z] for s in [-1,1] for z in [78,120]],'axis':[0,1,0],'screw':'M2x12 pan','quantity':4,'nut':'M2 AF4.0 x1.6; exposed loose nut','head_bearing_y_mm':-80.0,'nut_bearing_y_mm':-70.0,'note':'Orange jaw recess Ø4.8; all shafts Ø2.4. Fit jaws to backplate before mounting cradle. Phone enters from +Z; soft contact pads user fitted.'},
    ])
    return [{'shape':tray,'name':'D14_PHONE_BACK','color':GRAY,'label':'直立手机背托 / 灰色1件','hardware':'2×M2×12盘头螺丝＋2×M2螺母连接主体'}]+parts

def audit(parts,p):
    import trimesh
    core={n:import_brep(str(ROOT/f'review/cache/R05A_{n}.brep')) for n in ['H01_MAIN_SHELL','H02_DOCK_RECEIVER','H03_CLEAR_VISOR','H04_VISOR_FRAME']}
    checks={'parts':[],'intersections':[],'hardware':[],'mounts':MOUNTS,'phone':{'nominal_cased_width_mm':75,'user_cased_thickness_range_mm':[10,12],'clear_width_mm':r04.val(p,'phone_clear_width'),'clear_depth_mm':r04.val(p,'phone_clear_depth'),'unconfirmed':'Actual soft-pad grip and loaded bracket flex require physical test.'}}
    for a in parts:
        sh=a['shape'];v,f=sh.tessellate(.08,.12);mesh=trimesh.Trimesh(vertices=[tuple(q) for q in v],faces=f,process=True)
        checks['parts'].append({'name':a['name'],'valid':sh.is_valid,'solids':len(sh.solids()),'volume_mm3':sh.volume,'bbox_mm':list(sh.bounding_box().size),'watertight':mesh.is_watertight,'is_volume':mesh.is_volume,'components':len(mesh.split())})
        export_brep(sh,str(ROOT/f'review/cache/phone_R06_{a["name"]}.brep'))
        for name,ref in core.items():checks['intersections'].append({'a':a['name'],'b':name,'volume_mm3':volume(sh.intersect(ref))})
    for i,a in enumerate(parts):
        for b in parts[i+1:]:checks['intersections'].append({'a':a['name'],'b':b['name'],'volume_mm3':volume(a['shape'].intersect(b['shape']))})
    # A centered 75 mm wide phone starts atop shelf with .2 mm depth allowance
    # on each side; this conservative depth exceeds the reported maximum12mm.
    probe=box(75,r04.val(p,'phone_clear_depth')-.4,140,(0,-74-r04.val(p,'phone_clear_depth')/2,116.01))
    checks['phone']['envelope_collision_mm3']={a['name']:volume(a['shape'].intersect(probe)) for a in parts}
    for group in MOUNTS:
        for x,y,z in group['centers_mm']:
            seat=group['head_bearing_y_mm'];ny=group['nut_bearing_y_mm'];length=12
            nut=_nut(x,ny,z);shaft=through_y(x,seat,z,1,length);head=through_y(x,seat-1.6,z,2,1.6)
            result={'group':group['id'],'center':[x,y,z],'nut_intrusion':{},'shaft_intrusion':{},'head_intrusion':{},'phone_hardware_intrusion_mm3':volume(probe.intersect(head+shaft+nut)),'nominal_thread_protrusion_mm':seat+length-(ny+1.6)}
            for a in parts+[{'name':n,'shape':s} for n,s in core.items()]:
                result['nut_intrusion'][a['name']]=volume(a['shape'].intersect(nut));result['shaft_intrusion'][a['name']]=volume(a['shape'].intersect(shaft))
                result['head_intrusion'][a['name']]=volume(a['shape'].intersect(head))
            checks['hardware'].append(result)
    checks['body_nut_installation_path']=[]
    for x in [-25,25]:
        nutpath=extrude(Plane(origin=(x,-62,50),x_dir=(1,0,0),z_dir=(0,1,0))*RegularPolygon(4.0/math.sqrt(3),6,rotation=30),amount=62)
        checks['body_nut_installation_path'].append({'x':x,'inside_cavity_approach_to_nut_volume_mm3':volume(core['H01_MAIN_SHELL'].intersect(nutpath))})
    checks['pass']=all(a['valid'] and a['solids']==1 and a['watertight'] and a['is_volume'] and a['components']==1 for a in checks['parts']) and all(v['volume_mm3']<1e-5 for v in checks['intersections']) and all(v<1e-5 for v in checks['phone']['envelope_collision_mm3'].values()) and all(v<1e-5 for h in checks['hardware'] for key in ['nut_intrusion','shaft_intrusion','head_intrusion'] for v in h[key].values()) and all(h['phone_hardware_intrusion_mm3']<1e-5 for h in checks['hardware'])
    checks['pass']=checks['pass'] and all(c['inside_cavity_approach_to_nut_volume_mm3']<1e-5 for c in checks['body_nut_installation_path'])
    (ROOT/'validation/phone_R06_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    return checks

if __name__=='__main__':
    p=r04.load_parameters(ROOT/'parameters.yaml');parts=build_parts(p);result=audit(parts,p);print(json.dumps(result,ensure_ascii=False,indent=2));assert result['pass']
