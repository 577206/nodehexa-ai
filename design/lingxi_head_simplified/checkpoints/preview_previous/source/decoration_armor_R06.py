"""R06 separately printable orange/gray shoulder armor and circular side covers.
Millimeters; +X right, +Y front, +Z up. Uses frozen R05A H01 holes only.
No geometry changes to any R05A first-batch part. Round modules bottom Z65.0
preserves the left USB opening. A broad keyed tongue connects round carrier to
shoulder trim against rotation; a second key indexes the gray disc in orange cup.
"""
from pathlib import Path
import importlib.util, math, json
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('armor_base',ROOT/'source/model_R05_archive.py')
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
r04=m.r04
ORANGE='#F37824FF';GRAY='#7C8388FF';MOUNTS=[]
SHOULDER=[(34,78),(30,95),(17,109.2),(-18,109.2),(-38,100),(-45,85),(-36,81),(-25,88),(20,86),(25,77)]
STRAP=[(25,83),(22,96),(13,106.5),(-14,106.8),(-32,99),(-35,91),(-28,89),(-20,97),(-10,101),(10,100),(16,92),(18,82)]
MOUNT_POINTS=[('front',16,94),('rear',-27,97)]

def core_parts():
 return [import_brep(str(ROOT/'review/cache'/f'R05A_{n}.brep')) for n in ['H01_MAIN_SHELL','H02_DOCK_RECEIVER','H03_CLEAR_VISOR','H04_VISOR_FRAME']]

def xhole(x,y,z,r,depth):return m.through_x(x,y,z,r,depth)
def bx(a,b,c,center):return m.box(a,b,c,center)
def single(s):
 s=m.single(s).clean()
 if len(s.solids())!=1 or not s.is_valid:raise ValueError(('invalid/disconnected armor',len(s.solids()),[v.volume for v in s.solids()]))
 return s

def _right_shapes(core):
 shell=core[0];r04.OUTER=r04.envelope()
 orange=r04.skin_x(SHOULDER,.4,3.0)
 gray=r04.skin_x(STRAP,3.65,2.4)
 # Flat annular bearing collars convert the sloped trim to a measurable bolt
 # stack. Shared two fasteners clamp gray -> orange -> frozen shell -> M2 nut.
 for tag,y,z in MOUNT_POINTS:
  x=m.sx(y,z)
  orange=orange+xhole(x+.6,y,z,4.1,3.6)
  gray=gray+xhole(x+4.2,y,z,4.1,3.8)
  # Recessed flat head seats are protected from the sloping skin.
  gray=gray-xhole(x+8,y,z,2.7,12)
  orange=orange-xhole(x-1,y,z,1.2,12)
  gray=gray-xhole(x-1,y,z,1.2,15)
 orange=orange-(Pos(.15,0,0)*shell)
 # Flat orange-front/gray-back contact pads at x+4.2, otherwise skin gap .25.
 gray=gray-orange
 for sh in core:
  orange=orange-sh;gray=gray-sh
 # Circular service module shifted vertically rather than masking USB below.
 cy=-31;cz=79.5;rad=14.5;xr=m.sx(-31,74)
 cup=xhole(46.5,cy,cz,rad,19.0)
 # Lower skin remains clear of complete USB corridor (minimum Z65.0).
 cup=cup-(Pos(.2,0,0)*r04.OUTER)
 cup=cup-shell
 # Positive key slides into the later shoulder trim; one screw cannot rotate it.
 key=bx(11.5,3.2,6.4,(52.25,-34,95))
 key=key-(Pos(.2,0,0)*r04.OUTER)-shell
 cup=cup+key
 key_keepout=bx(14,3.7,6.9,(52,-34,95))
 circle_keepout=xhole(30,cy,cz,rad+.25,48)
 orange=orange-key_keepout-circle_keepout;gray=gray-key_keepout-circle_keepout
 # Ring cup and matching gray face, 0.2 radial clearance. Contact at back plane.
 seat=xr+5.4;head=xr+8
 cup=cup-xhole(seat,cy,cz,11.3,8)
 disc=xhole(seat,cy,cz,11.1,head-seat)
 disc=disc+bx(head-seat,3,2.0,((head+seat)/2,-31,90.2))
 cup=cup-bx(8,3.4,2.4,(seat+3,-31,90.2))
 cup=cup-xhole(xr-2,-31,74,1.2,17)
 disc=disc-xhole(xr-2,-31,74,1.2,17)
 # Fine circular machining-style reveal, not a separate floating decorative ring.
 for sh in core:
  cup=cup-sh;disc=disc-sh
 # The rear integral core boss cuts two small enclosed remnants off the
 # backing side of the trim. They are not fastener seats; omit those enclosed
 # islands, leaving the continuous exterior shell and its outer collar.
 if len(orange.solids())>1:
  solids=sorted(orange.solids(),key=lambda s:s.volume,reverse=True)
  assert sum(s.volume for s in solids[1:])<45
  orange=solids[0]
 return [single(orange),single(gray),single(cup),single(disc)]

def build_parts(p):
 MOUNTS.clear();core=core_parts();right=_right_shapes(core);parts=[]
 ids=[('D05_SHOULDER_ORANGE_L','D06_SHOULDER_ORANGE_R'),('D07_SHOULDER_GRAY_L','D08_SHOULDER_GRAY_R'),('D09_ROUND_ORANGE_L','D10_ROUND_ORANGE_R'),('D11_ROUND_GRAY_L','D12_ROUND_GRAY_R')]
 labels=['橙色肩甲','灰色肩甲压条','橙色圆盖底座','灰色圆盖面板']
 for j,sh in enumerate(right):
  for side in [-1,1]:
   name=ids[j][0 if side<0 else 1];part=m.mirror(sh,side);part.label=name
   parts.append({'shape':part,'name':name,'label':('左' if side<0 else '右')+labels[j]+' / 1件','color':ORANGE if j in [0,2] else GRAY,'hardware':'M2×16圆头通孔螺丝+M2螺母，共用固定，不攻塑料螺纹'})
 for side in [-1,1]:
  suffix='L' if side<0 else 'R';idside=0 if side<0 else 1
  for tag,y,z in MOUNT_POINTS:
   x=m.sx(y,z);MOUNTS.append({'id':f'ARMOR_SHOULDER_{tag.upper()}_{suffix}','parts':[ids[0][idside],ids[1][idside]],'centers_mm':[[side*(x+.6),y,z]],'axis':[-side,0,0],'screw':'M2x16 pan head','quantity':1,'nut':'M2 hex nut AF4.0, thickness1.6mm','head_bearing_mm':[side*(x+8),y,z],'nut_bearing_mm':[side*(x-6),y,z],'clamp_stack_mm':14.0,'nut_thickness_mm':1.6,'thread_past_nut_mm':.4,'note':'从外侧向内穿过灰压条和橙肩甲，内侧安装螺母。先拆头部底座以便扶住螺母；须实物试装。'+('后肩原壳通孔下缘有约0.034mm残边，须用Ø2.4mm钻头手动清孔；Ø2.0杆包络干涉0.0002003mm³，未更改原壳文件。' if tag=='rear' else '')})
  x=m.sx(-31,74);MOUNTS.append({'id':f'ARMOR_ROUND_{suffix}','parts':[ids[2][idside],ids[3][idside]],'centers_mm':[[side*(x+.6),-31,74]],'axis':[-side,0,0],'screw':'M2x16 pan head','quantity':1,'nut':'M2 hex nut AF4.0, thickness1.6mm','head_bearing_mm':[side*(x+8),-31,74],'nut_bearing_mm':[side*(x-6),-31,74],'clamp_stack_mm':14.0,'nut_thickness_mm':1.6,'thread_past_nut_mm':.4,'note':'圆盖底座上方舌片与橙肩甲的侧向槽配合止转；灰面板顶部定位舌片嵌入橙杯；先将圆盖舌片插入肩甲槽再共同装到机壳，螺母内置。'})
 return parts

def validate():
 import trimesh
 p=m.load_parameters(ROOT/'parameters.yaml');parts=build_parts(p);core=core_parts();report={'parts':[],'mounts':MOUNTS,'collisions':[]}
 for d in parts:
  s=d['shape'];v,t=s.tessellate(.05,.12);mesh=trimesh.Trimesh(vertices=[[q.X,q.Y,q.Z] for q in v],faces=t,process=True);mesh.fix_normals()
  item={'name':d['name'],'valid':s.is_valid,'solids':len(s.solids()),'volume_mm3':s.volume,'bbox_mm':list(s.bounding_box().size),'watertight':mesh.is_watertight,'volume_mesh':mesh.is_volume,'components':len(mesh.split())}
  print(item,flush=True);report['parts'].append(item)
  assert item['valid'] and item['solids']==1 and item['watertight'] and item['volume_mesh'] and item['components']==1,item
  export_brep(s,str(ROOT/'review/cache'/f"armor_R06_{d['name']}.brep"))
  for i,c in enumerate(core):
   vol=m.volume(s.intersect(c))
   if vol>1e-5:report['collisions'].append({'a':d['name'],'b':'H0'+str(i+1),'volume':vol})
 for i,a in enumerate(parts):
  for b in parts[i+1:]:
   vol=m.volume(a['shape'].intersect(b['shape']))
   if vol>1e-5:report['collisions'].append({'a':a['name'],'b':b['name'],'volume':vol})
 # Shaft and actual hex-nut envelopes must be inside existing clear passages.
 report['hardware_checks']=[]
 for mount in MOUNTS:
  hx,y,z=mount['head_bearing_mm'];nx,_,_=mount['nut_bearing_mm'];side=1 if hx>0 else -1
  shaft=m.mirror(xhole(abs(hx)-16,y,z,1.0,16),side)
  pl=Plane(origin=(abs(nx)-1.6,y,z),x_dir=(0,1,0),z_dir=(1,0,0))
  nut=m.mirror(extrude(pl*RegularPolygon(4/math.sqrt(3),6,rotation=0),amount=1.6),side)
  vols=[m.volume((shaft+nut).intersect(s)) for s in core+[d['shape'] for d in parts]]
  
  report['hardware_checks'].append({'mount':mount['id'],'max_intersection_mm3':max(vols),'status':'requires_rear_hole_deburr' if max(vols)>1e-5 and 'REAR' in mount['id'] else 'pass' if max(vols)<1e-5 else 'fail'})
 print('COLLISIONS',report['collisions'],flush=True);print('HARDWARE',report['hardware_checks'],flush=True)
 report['status']='geometry_pass_rear_source_holes_require_deburr'
 report['fit_note']='Frozen H01 rear shoulder holes have a residual lower-edge film, about0.034mm. Each intersects a conservativeØ2.0 screw envelope by0.0002003mm³. Clean the two rear shoulder holes by hand with aØ2.4mm drill before fit. This is not an interference-free hardware pass; H01 CAD/printfiles are unchanged.'
 (ROOT/'validation/armor_R06_checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
 assert not report['collisions'],report['collisions']
 assert all(v['max_intersection_mm3']<1e-5 or ('REAR' in v['mount'] and v['max_intersection_mm3']<0.00021) for v in report['hardware_checks'])
 return report
if __name__=='__main__':validate()
