"""Read-only audit of retained R04 receiving base for the R05 print batch.

Uses the actual cached dock BREP and regenerates the unchanged fixed R02 bowl
from its authoring source. Writes only this audit's evidence JSON, no CAD edits.
Connector probes represent nominal supplier envelopes, not validated hardware.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json
from build123d import import_brep, ShapeList, Pos, Plane, RectangleRounded, Cylinder, Box, Align, extrude

ROOT=Path(__file__).resolve().parents[1]
BOWL_ROOT=ROOT.parent/'lingxi_magnetic_bowl_mount'
BASE_FILE=ROOT/'review/cache/R04_DOCK_BASE.brep'
OUTPUT=ROOT/'validation/audit_dock_R05.json'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base',type=Path,default=BASE_FILE)
parser.add_argument('--output',type=Path,default=OUTPUT)
args=parser.parse_args()
BASE_FILE=args.base.resolve();OUTPUT=args.output.resolve()

def volume(shape):
    if not shape:return 0.0
    return sum(s.volume for s in shape) if isinstance(shape,ShapeList) else shape.volume
def overlap(a,b):return volume(a.intersect(b))
def rr(w,l,z,h,r=1.98):return Pos(0,0,z)*extrude(RectangleRounded(w,l,r),amount=h)
def cyl(x,z,r,h):return Pos(x,0,z)*Cylinder(r,h,align=(Align.CENTER,Align.CENTER,Align.MIN))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bounds(shape):
    b=shape.bounding_box();return {'min_mm':list(b.min),'max_mm':list(b.max),'size_mm':list(b.size)}

spec=importlib.util.spec_from_file_location('audit_fixed_bowl_R02',BOWL_ROOT/'source/model.py')
bowl_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(bowl_module)
bowl_parameters=bowl_module.load_parameters(BOWL_ROOT/'parameters.yaml')
bowl=bowl_module.build_model(bowl_parameters)
base=import_brep(str(BASE_FILE))
report={
 'audit':'retained_head_dock_for_R05','units':'mm','scope':'Read-only actual BREP interfaces, not production acceptance',
 'coordinates':{'X':'right','Y':'front','Z':'up','bowl_placement':'identity, frame top Z0'},
 'provenance':{'dock_brep':str(BASE_FILE),'dock_sha256':sha(BASE_FILE),'dock_mtime':BASE_FILE.stat().st_mtime,
   'bowl_source_sha256':sha(BOWL_ROOT/'source/model.py'),'bowl_parameters_sha256':sha(BOWL_ROOT/'parameters.yaml')},
 'base':{'valid':base.is_valid,'solid_count':len(base.solids()),'volume_mm3':base.volume,**bounds(base)},
 'bowl':{'valid':bowl.is_valid,'solid_count':len(bowl.solids()),'volume_mm3':bowl.volume,**bounds(bowl)},
 'nest':{'static_overlap_mm3':overlap(base,bowl),'minimum_separation_mm':base.distance_to(bowl),'vertical_lift':[]},
 'head_fasteners':[],'bowl_fasteners':[],'upper_connector':{},'lower_connector':{},
}
for dz in [0,.5,2,5,10,20,30]:
 report['nest']['vertical_lift'].append({'head_translation_z_mm':dz,'collision_mm3':overlap(Pos(0,0,dz)*base,bowl)})

for x in [-46,46]:
 # Slightly inset probes avoid treating exact CAD face contacts as interference.
 access=overlap(base,cyl(x,.05,2.59,29.90))
 shaft=overlap(base,cyl(x,29.95,1.19,4.10))
 seat_ring=cyl(x,30.02,2.5,.10)-cyl(x,30.01,1.30,.12)
 full_ring=volume(seat_ring)
 report['head_fasteners'].append({'axis_xy_mm':[x,0],'counterbore_nominal_diameter_mm':5.2,
  'shaft_nominal_diameter_mm':2.4,'underside_head_seat_z_mm':30,'upper_mating_face_z_mm':34,
  'local_bearing_thickness_mm':4,'counterbore_clear_probe_mm3':access,'shaft_clear_probe_mm3':shaft,
  'lower_5mm_access_blocked_mm3':overlap(base,cyl(x,.05,2.59,4.90)),
  'above_5mm_access_blocked_mm3':overlap(base,cyl(x,5.05,2.59,24.90)),
  'seat_probe_solid_fraction':overlap(base,seat_ring)/full_ring,
  '10mm_underhead_screw_nominal_reach_above_base_mm':6,
  'reach_note':'Arithmetic only; actual main-shell captive nut placement, screw type, engagement and actual screw length are not verified by this base-only audit.'})
for x,y in bowl_module.screw_centers(bowl_parameters):
 report['bowl_fasteners'].append({'axis_xy_mm':[x,y],'shaft_diameter_mm':2.4,'tool_access_diameter_mm':5.2,
  'outer_reserved_corridor_diameter_mm':8,'seat_z_mm':2.4,
  'shaft_clear_probe_mm3':overlap(bowl,cyl(x,.01,1.19,28.98)),
  'access_clear_probe_mm3':overlap(bowl,cyl(x,2.41,2.59,26.58)),
  '10mm_underhead_screw_nominal_reach_below_bowl_mm':7.6})

# Upper: front face points -Z. Nominal 2 mm neck reaches from Z29.4 to31.4.
# Lower: front face points +Z. Neck reaches from Z27 to29.
upper_neck=rr(17.54,4,29.4,2)
lower_neck=rr(17.54,4,27,2)
report['upper_connector']={
 'insertion':'downward from the head electronics side (+Z to -Z)',
 'contact_face_normal':[0,0,-1],'nominal_face_z_mm':29.4,'flange_lower_stop_z_mm':31.4,
 'collar_z_mm':[30.4,31.4],'throat_nominal_mm':[17.94,4.4],
 'upper_relief_mm':[22,8],'front_housing_envelope_mm':[17.54,4,2],
 'nominal_installed_neck_collision_mm3':overlap(base,upper_neck),
 'downward_insertion_probes':[{'raised_z_mm':dz,'collision_mm3':overlap(base,Pos(0,0,dz)*upper_neck)} for dz in [8,4,2,.5,0]],
 'flange_stop_probe':{'description':'Artificial 0.2mm thick nominal19.54x4 flange slice; demonstrates end support, not flange thickness',
  'correct_side_collision_mm3':overlap(base,rr(19.54,4,31.401,.2)),
  'overinserted_collision_mm3':overlap(base,rr(19.54,4,31.199,.2))},
}
report['lower_connector']={
 'insertion':'upward from bowl interior (-Z to +Z)','contact_face_normal':[0,0,1],
 'nominal_face_z_mm':29,'flange_upper_stop_z_mm':27,'collar_top_z_mm':28,
 'nominal_installed_neck_collision_mm3':overlap(bowl,lower_neck),
 'flange_stop_probe':{'correct_side_collision_mm3':overlap(bowl,rr(19.54,4,26.799,.2)),
                      'overinserted_collision_mm3':overlap(bowl,rr(19.54,4,27.001,.2))},
}
report['contact_pair']={
 'head_face_z_mm':29.4,'bowl_face_z_mm':29,'nominal_face_plane_gap_mm':.4,
 'electrical_contact_verified':False,
 'note':'Opposite mechanical directions are modelled. A .4mm housing-face gap cannot prove pogo-pin contact or spring compression. Male/female profiles, spring free length/stroke and connector polarity must be checked.'}
report['thin_wall_observation']={
 'location':'Near bottom of deep screw-access wells at X +/-46,Y0',
 'nominal_well_inner_x_mm':46-5.2/2,
 'nominal_cavity_half_width_at_start_mm':86.8/2,
 'nominal_web_at_cavity_start_mm':46-5.2/2-86.8/2,
 'analytic_web_at_z0_mm':(46-5.2/2)-(86.8/2 + (82.8/2-86.8/2)*(.1/27.5)),
 'note':'These analytic values describe the unrepaired nominal well/cavity boundary, not the final cut geometry. R05 deliberately opens it with a 4.4 x 4.0 x 12.1mm notch. The independent notch probes below verify that cut without confusing it with the load-bearing Z30 seat.'}
report['lower_access_notches']=[
 {'center_xyz_mm':[side*44,0,5.95], 'nominal_cut_mm':[4.4,4.0,12.1],
  'inset_probe_mm':[4.38,3.98,12.08],
  'blocked_probe_mm3':overlap(base,Pos(side*44,0,5.95)*Box(4.38,3.98,12.08))}
 for side in [-1,1]]
report['checks_in_scope']=[
 'Cached receiving base CAD validity and connected-solid count',
 'Static bowl clearance and sampled vertical release path',
 'Two distinct screw-axis sets and nominal bore access probes',
 'Deliberately open lower screw-well/cavity junction and intact Z30 bearing annuli',
 'Opposing upper/lower connector insertion directions and nominal collar stops',
]
report['not_verified']=[
 'Actual connector male/female shapes, body tolerances, spring reach and compression',
 'Magnet holding force versus complete head/phone mass, impacts and tipping',
 'Actual screw diameters, head heights, thread engagement, printed pilot retention and tool dimensions',
 'Printer/material tolerances, bridging/support access and fit after printing',
 'PCB, solder and cable strain-relief envelopes above upper connector and below lower connector',
 'Head plinth versus robot frame/leg swept volumes and external wiring',
 'New R05 main-shell mating holes and contact surfaces; must audit after rebuild',
]
failures=[]
if not base.is_valid or len(base.solids())!=1:failures.append('base_solid_invalid')
if report['nest']['static_overlap_mm3']>1e-5:failures.append('bowl_interference')
if any(v['collision_mm3']>1e-5 for v in report['nest']['vertical_lift']):failures.append('vertical_release_interference')
if any(v['counterbore_clear_probe_mm3']>1e-5 or v['shaft_clear_probe_mm3']>1e-5 or v['seat_probe_solid_fraction']<.999 for v in report['head_fasteners']):failures.append('head_fastener_interface')
if any(v['blocked_probe_mm3']>1e-5 for v in report['lower_access_notches']):failures.append('lower_access_notch_blocked')
if any(v['shaft_clear_probe_mm3']>1e-5 or v['access_clear_probe_mm3']>1e-5 for v in report['bowl_fasteners']):failures.append('bowl_fastener_interface')
if report['upper_connector']['nominal_installed_neck_collision_mm3']>1e-5 or report['lower_connector']['nominal_installed_neck_collision_mm3']>1e-5:failures.append('nominal_neck_interference')
report['CAD_failures']=failures
report['status']='CAD_interface_checks_pass_physical_fit_unverified' if not failures else 'CAD_interface_failures'
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
