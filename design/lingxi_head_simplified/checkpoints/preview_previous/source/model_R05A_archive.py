"""R05A first-print core plus removable visor. mm,+Y front,+X right,+Z up.
H01/H02 are unchanged R05 structural parts. H03 clear cover and H04 retainer
are separate first-batch parts. All other decorations remain second-batch.
"""
from pathlib import Path
import importlib.util,yaml,math
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('r04',ROOT/'source/model_R04_archive.py');r04=importlib.util.module_from_spec(sp);sp.loader.exec_module(r04)
r03=r04.r03;old=r04.old
box=r04.box;single=r04.single;volume=r04.volume;union=r04.union;mirror=r04.mirror;through_x=r04.through_x;through_y=r04.through_y;solid_rr=r04.solid_rr
load_parameters=r04.load_parameters;val=r04.val
GRAY='#7C8388FF';DARK='#41484FFF';ORANGE='#F37824FF';CLEAR='#B3A39448'
COLORS={};PART_IDS={};LABELS={};MOUNT_INTERFACES=[]
ROWS=r04.ROWS;STATIONS=r04.STATIONS

def bottom_dock(p):
 # Fixed central cup has original full-depth receiving, key and4P passages.
 base=r04.bottom_dock(p)
 # Deliberately open the lower screw-well/cavity boundary: do not print a
 # near-tangent0.007mm web. Load-bearing screw seats atZ30 stay unchanged.
 for side in [-1,1]:
  base=base-box(4.4,4.0,12.1,(side*44.0,0,5.95))
  x=side*val(p,'screw_span')/2
  base=base-Pos(x,0,-.1)*Cylinder(val(p,'pan_recess_diameter')/2,30.1,align=(Align.CENTER,Align.CENTER,Align.MIN))
  base=base-Pos(x,0,29.9)*Cylinder(val(p,'shaft_diameter')/2,4.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
 return single(base).clean()

def sx(y,z):
 for a,b in zip(ROWS,ROWS[1:]):
  if a[4]<=z<=b[4]:
   t=(z-a[4])/(b[4]-a[4]);w,f,back,c=[a[i]+t*(b[i]-a[i]) for i in range(4)]
   return min(w,w-(y-(f-c)),w-((back+c)-y))
 raise ValueError('outside shell stations')

def top_support_shell(p):
 MOUNT_INTERFACES.clear();wall=val(p,'wall')
 out=r04.envelope()
 # Keep analytic loft topology for watertight export; structural silhouette is R04.
 inside=[(w-wall,f-wall,b+wall,c-1.2,z-.1 if i==0 else z-wall if i==len(ROWS)-1 else z) for i,(w,f,b,c,z) in enumerate(ROWS)]
 shell=out-loft([old.octagon(r) for r in inside],ruled=True)
 shell=single(shell.intersect(box(220,220,130,(0,0,75)))) # Z10 upward; low cup plinth9.8
 glass,frame=r04.visor_geometry();frame=frame-r04.camera_frame()
 shell=shell-old.rect_loft(STATIONS,1,-.5,.5)-frame-glass
 # Intentional clearance around top frame corners; no detached thin wedges.
 for side in [-1,1]:shell=shell-box(3.4,5.5,5,(side*29.3,24.7,105.4))
 # Real docking-joint posts. Screws are installed upward through the cup.
 for side in [-1,1]:
  x=side*val(p,'screw_span')/2
  post=Pos(x,0,34)*Cylinder(6,10,align=(Align.CENTER,Align.CENTER,Align.MIN))
  shell=shell+post+box(16,10,8,(side*54,0,38))
  shell=shell-Pos(x,0,33.9)*Cylinder(val(p,'shaft_diameter')/2,10.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
  # M2 nut side-loading pocket, AF4.4/depth2; M2x10 from seatZ30.
  nut=Pos(x,0,37.2)*extrude(RegularPolygon(radius=4.4/math.sqrt(3),side_count=6,rotation=30),amount=2)
  channel=box(4.4,8,2,(x,4,38.2))
  shell=shell-nut-channel
  MOUNT_INTERFACES.append({'id':f'BASE_{side}','center_mm':[x,0,34],'axis':[0,0,1],'through_diameter_mm':val(p,'shaft_diameter'),'nut':'M2 AF4.4/depth2 trial allowance','nut_z_mm':[37.2,39.2]})
 # Screw-on decorative panels have simple, connected side bosses, no decorative skins.
 # Three grouped attachment areas per side, not dozens of cosmetic screw dimples.
 for side in [-1,1]:
  for tag,y,z in [('VENT_UPPER',22,68),('VENT_LOWER',23,29),('SHOULDER_FRONT',16,94),('SHOULDER_REAR',-27,97),('ROUND_COVER',-31,74)]:
   x=sx(y,z);boss=through_x(x-6,y,z,3.8,6.6)
   shell=shell+mirror(boss,side)
   shell=shell-mirror(through_x(x-6.1,y,z,1.2,6.9),side)
   MOUNT_INTERFACES.append({'id':tag+('_L' if side<0 else '_R'),'center_mm':[side*(x+.6),y,z],'axis':[side,0,0],'through_diameter_mm':2.4,'inside':'accessible M2 nut/washer; ornament will adapt to this frozen interface'})
 # A broad grille window; screw-on vent module is a future independent part.
 for side in [-1,1]:
  shell=shell-mirror(box(32,23,22,(60,24,48)),side)
 # User's large left TypeC reach-in route. Hardware socket lies further inboard.
 shell=shell-box(45,val(p,'usb_access_width'),val(p,'usb_access_height'),(-59,-24,val(p,'usb_access_center_z')))
 # Low front camera opening and physically connected bezel screw pads.
 shell=shell-through_y(0,55,26,7.8,30)
 for x in [-11,11]:
  shell=shell+through_y(x,68,26,3.8,6)
  shell=shell-through_y(x,66,26,1.2,11)
  MOUNT_INTERFACES.append({'id':f'CAMERA_{x}','center_mm':[x,74,26],'axis':[0,1,0],'through_diameter_mm':2.4})
 # Continuous structural windshield ledge, retained behind removable transparent visor.
 # Front/back ends use robust tabs; final retaining frame must use these hole centers.
 # Upper screw bores clear theZ107 ledge by0.4mm; no tangent zero-thickness edge.
 for x,y,z in [(-31,72,37),(31,72,37),(-23,23,108.6),(23,23,108.6)]:
  if z<50:
   boss=through_y(x,67,z,3.5,4.6)
  else:
   boss=through_y(x,16,z,3.2,6.5)
   # Tongue connects to uncut crown behind opening, stays behind glass.
   boss=boss+box(6,9,3.2,(x,15,108.2))
  shell=shell+boss
  shell=shell-through_y(x,y-11,z,1.2,17)
  MOUNT_INTERFACES.append({'id':f'VISOR_{x}_{z}','center_mm':[x,71.6 if z<50 else 22.5,z],'axis':[0,1,0],'through_diameter_mm':2.4})
 # Two rear mount pads retain original75mm phone cradle attachment area.
 for x in [-25,25]:
  shell=shell+box(10,5,12,(x,-64.5,50))
  shell=shell-through_y(x,-70,50,1.2,12)
  MOUNT_INTERFACES.append({'id':f'PHONE_{x}','center_mm':[x,-67,50],'axis':[0,-1,0],'through_diameter_mm':2.4})
 # Short front side perforations remain integrated into primary shell, no trim.
 for side in [-1,1]:
  for x in [22,27,32]:
   for z in [20,24,28,32]:shell=shell-through_y(side*x,59,z,1,23)
 # Open ceiling tray remains clear of boards; zero overlap with counterpart cup.
 shell=single(shell-bottom_dock(p)-glass)
 return shell.clean()

def build_model(p):
 COLORS.clear();PART_IDS.clear();LABELS.clear()
 shell=top_support_shell(p);base=bottom_dock(p)
 from visor_R05A import visor_parts
 glass,frame=visor_parts(shell)
 for shape,name,label in [(shell,'H01_MAIN_SHELL','H01 主体壳 / 第一批打印1件'),(base,'H02_DOCK_RECEIVER','H02 头部深腔底座 / 第一批打印1件'),(glass,'H03_CLEAR_VISOR','H03 透明盖 / 第一批打印1件'),(frame,'H04_VISOR_FRAME','H04 灰色压框 / 第一批打印1件')]:
  if len(shape.solids())!=1:raise ValueError(f'{name}: disconnected {len(shape.solids())} solids: '+str([(s.volume,tuple(s.bounding_box().min),tuple(s.bounding_box().max)) for s in shape.solids()]))
  assert shape.is_valid,name
  shape.label=name;shape.color=Color(.49,.51,.53);COLORS[name]='#E8F5FF55' if name=='H03_CLEAR_VISOR' else GRAY;PART_IDS[name]=name;LABELS[name]=label
 return Compound(children=[shell,base,glass,frame],label='R05A_FIRST_BATCH_WITH_REMOVABLE_VISOR')

def hardware_references(p):
 refs=[]
 for sh,c in r04.hardware_references(p):
  if any(k in sh.label for k in ['FIXED_BOWL','BOARDS','OLED_L','OLED_R']):refs.append((sh,c))
 return refs

def write_step(model,path):export_step(model,str(path))
if __name__=='__main__':
 m=build_model(load_parameters(ROOT/'parameters.yaml'))
 for s in m.children:print(s.label,s.is_valid,len(s.solids()),s.volume,tuple(s.bounding_box().size))
