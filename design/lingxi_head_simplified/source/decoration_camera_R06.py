"""Independent orange screw-on camera surround, on fixed R05A hole axes."""
from pathlib import Path
import importlib.util
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('core_camera',ROOT/'source/model_R05A_archive.py');core=importlib.util.module_from_spec(sp);sp.loader.exec_module(core)
r04=core.r04
MOUNTS=[{'part':'D13_CAMERA_BEZEL','axis':'Y','centers_mm':[[-11,74,26],[11,74,26]],'screw':'M2x12 pan head','quantity':2,'nut':'M2, AF4mm, thickness1.6mm','head_bearing_Y_mm':78.2,'nut_bearing_Y_mm':68.0,'stack_plus_nut_mm':11.8,'note':'Fit-print screw length based on1.6mm nut. Install nuts from inside before docking base; camera hardware mounting separate.'}]
def build_parts(p):
 pts=[(-9,12.5),(9,12.5),(15.4,18),(15.4,34),(10,39),(-10,39),(-15.4,34),(-15.4,18)]
 s=r04.edge_break(r04.xz(pts,78.2,4),.6)
 s=s-core.through_y(0,74,26,8,4.4)
 for x in [-11,11]:s=s-core.through_y(x,73.9,26,1.2,4.6)
 # Raised inner bevel emphasizes square mecha bezel; it does not enter lens aperture.
 s=core.single(s).clean()
 return [{'shape':s,'name':'D13_CAMERA_BEZEL','color':'#F37824FF','label':'摄像头橙色外框','hardware':MOUNTS}]
if __name__=='__main__':
 import json,trimesh
 p=core.load_parameters(ROOT/'parameters.yaml');shell=import_brep(str(ROOT/'review/cache/R05A_H01_MAIN_SHELL.brep'))
 parts=[import_brep(str(ROOT/'review/cache'/f'R05A_{n}.brep')) for n in ['H01_MAIN_SHELL','H02_DOCK_RECEIVER','H03_CLEAR_VISOR','H04_VISOR_FRAME']]
 s=build_parts(p)[0]['shape'];checks={'valid':s.is_valid,'solid_count':len(s.solids()),'volume_mm3':s.volume,'intersections':[core.volume(s.intersect(x)) for x in parts]}
 for x in [-11,11]:
  nut=Pos(x,66.4,26)*Rot(X=-90)*extrude(RegularPolygon(radius=4/3**.5,side_count=6,rotation=30),amount=1.6)
  checks[f'nut_{x}_intersect']=core.volume(nut.intersect(shell))
 v,t=s.tessellate(.055,.12);m=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);m.fix_normals();checks['mesh']={'watertight':m.is_watertight,'is_volume':m.is_volume,'connected':len(m.split())}
 export_brep(s,str(ROOT/'review/cache/camera_R06_D13_CAMERA_BEZEL.brep'))
 (ROOT/'validation/camera_R06_checks.json').write_text(json.dumps(checks,indent=2));print(checks)
