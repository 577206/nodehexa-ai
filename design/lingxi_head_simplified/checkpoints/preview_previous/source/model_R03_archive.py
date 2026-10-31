"""R03 accepted orange/gray head. Reuses R02 folded canopy construction.
Fixed bowl remains atZ0; all dimensions mm. This is a CAD review prototype.
"""
from pathlib import Path
import yaml,importlib.util
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
_old_spec=importlib.util.spec_from_file_location('head_R02_archive',ROOT/'source/model_R02_archive.py')
old=importlib.util.module_from_spec(_old_spec);_old_spec.loader.exec_module(old)
GRAY='#727B83FF';DARK='#414A53FF';ORANGE='#F47920FF';CLEAR='#B9D9E535'
COLORS={};PART_IDS={};LABELS={}
def load_parameters(path):return yaml.safe_load(Path(path).read_text())
def val(p,n):return float(p['parameters'][n]['value'])
def box(x,y,z,c):return Pos(*c)*Box(x,y,z)
def volume(s):return sum(a.volume for a in s) if isinstance(s,ShapeList) else s.volume if s else 0

def single(s):
 if isinstance(s,ShapeList):
  solids=[sol for a in s for sol in a.solids()]
  if len(solids)==1:return solids[0]
  return Compound(children=solids)
 return s

def ring_profile(w,f,b,c,z):return old.octagon((w,f,b,c,z))
def solid_rr(w,l,r,z,h):return Pos(0,0,z)*extrude(RectangleRounded(w,l,r),amount=h)
def through_y(x,y,z,r,length):return extrude(Plane(origin=(x,y,z),x_dir=(1,0,0),z_dir=(0,1,0))*Circle(r),amount=length)
def through_x(x,y,z,r,length):return extrude(Plane(origin=(x,y,z),x_dir=(0,1,0),z_dir=(1,0,0))*Circle(r),amount=length)

# Original panel folds retained, moved up28mm and forward6mm for the deep dock.
STATIONS=[(z+28,y+6,w) for z,y,w in old.STATIONS]
ROWS=[(56,76,-70,14,34),(63,71,-70,14,64),(60,55,-70,14,94),(54,42,-65,12,108),(43,34,-51,10,118)]

def bottom_dock(p):
 w=val(p,'width')/2;length=val(p,'length');h=val(p,'base_thickness');cl=val(p,'dock_radial_clearance');roof_z=val(p,'bowl_height')-2+cl
 outside=loft([ring_profile(w-7,64,-58,13,0),ring_profile(w,76,-70,14,h)],ruled=True)
 base=outside
 # Hollow skirt plus thin docking cup, not a heavy solid block.
 hollow=loft([ring_profile(w-10,61,-55,11,-.1),ring_profile(w-3,73,-67,12,h-3)],ruled=True)
 base=base-hollow
 sleeve=loft([Plane.XY*RectangleRounded(val(p,'dock_pocket')+6,val(p,'dock_pocket')+6,10+cl),Plane.XY.offset(roof_z)*RectangleRounded(88+2*cl,88+2*cl,10+cl),Plane.XY.offset(h)*RectangleRounded(88+2*cl,88+2*cl,10+cl)],ruled=True)
 base=base+sleeve
 for sign in [-1,1]:base=base+Pos(sign*val(p,'screw_span')/2,0,h-10)*Cylinder(5.8,10,align=(Align.CENTER,Align.CENTER,Align.MIN))
 base=single(base.intersect(outside))
 # Whole bowl envelope, with per-side clearance; corner shape follows original.
 cavity=loft([Plane.XY.offset(-.1)*RectangleRounded(val(p,'dock_pocket'),val(p,'dock_pocket'),7+cl),Plane.XY.offset(roof_z)*RectangleRounded(82+2*cl,82+2*cl,7+cl)],ruled=True)
 base=base-cavity
 base=base-solid_rr(76+2*cl,76+2*cl,5+cl,27.3,val(p,'dock_depth')-27.3)
 base=base-box(6+2*cl,4+2*cl,2.2,(11,38,28.4))
 # Paired upper4P housing: insertion from electronic side above into collar.
 # Nominal faceZ29.4, flange-stopZ31.4; actual spring compression unverified.
 base=base-solid_rr(22,8,2,27.3,3.1)
 base=base-solid_rr(17.94,4.4,2.18,30.3,1.2)
 base=base-solid_rr(22,8,2,31.4,h-31.4+.1)
 for sign in [-1,1]:
  x=sign*val(p,'screw_span')/2
  # Deep driver wells keep the screw seating near the shell joint.
  base=base-Pos(x,0,-.1)*Cylinder(val(p,'pan_recess_diameter')/2,h-3.9,align=(Align.CENTER,Align.CENTER,Align.MIN))
  base=base-Pos(x,0,h-4)*Cylinder(val(p,'shaft_diameter')/2,4.1,align=(Align.CENTER,Align.CENTER,Align.MIN))
 return base.clean()

def body_shell(p):
 wall=val(p,'wall')
 outer=loft([old.octagon(r) for r in ROWS],ruled=True)
 inner=[]
 for i,(w,f,b,c,z) in enumerate(ROWS):inner.append((w-wall,f-wall,b+wall,c-1.2,z-.1 if i==0 else z-wall if i==len(ROWS)-1 else z))
 body=outer-loft([old.octagon(r) for r in inner],ruled=True)
 body=body-old.rect_loft(STATIONS,5,-3.2,3.2)
 # Two lower frame anchor pads, inherited original contour shifted consistently.
 for x in [-30,30]:
  body=body+through_y(x,67.8,50,3.3,6.567)
  body=body-through_y(x,67.7,50,1.05,7)
 for x in [-37,37]:body=body-box(3.6,12,4.6,(x,70,52))
 for sign in [-1,1]:
  # Base joint posts, accessible from below removable docking part.
  x=sign*val(p,'screw_span')/2
  body=body+box(12,10,8,(sign*51,0,38))
  body=body+Pos(x,0,34)*Cylinder(7,10,align=(Align.CENTER,Align.CENTER,Align.MIN))
  body=body-Pos(x,0,33.9)*Cylinder(1.05,10.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
 # Side ventilation apertures, kept away from folded visor edges.
 for sign in [-1,1]:
  cutter=box(25,27,30,(sign*62,24,66))
  body=body-cutter
  for z in [50,82]:
   pad=box(8.4,9,9,(sign*59.1,0,z))
   body=body+pad
   hole=through_x(54,0,z,1.2,16)
   body=body-(hole if sign==1 else hole.mirror(Plane.YZ))
 # Generous left-side reach-in window: board socket remains recessed.
 body=body-box(40,val(p,'usb_access_width'),val(p,'usb_access_height'),(-60,-24,val(p,'usb_access_center_z')))
 # Integrated circular side cap supports, kept above port and behind vent.
 for sign in [-1,1]:
  cap=through_x(57,-40,81,12,10)
  if sign<0:cap=cap.mirror(Plane.YZ)
  body=body+cap
 # Upright rear phone mount pads and M2 through locations.
 for x in [-25,25]:
  body=body+box(10,6,12,(x,-69,50))
  body=body-through_y(x,-74,50,1.2,12)
 # Camera frame supports and provisional aperture.
 for x in [-10,10]:
  body=body+through_y(x,71,46,3,5.4)
  body=body-through_y(x,70.9,46,1.05,5.6)
 body=body-through_y(0,64,46,6,25)
 # Integrated front grille perforations, not separate fastener parts.
 for sign in [-1,1]:
  for dx in [-3,0,3]:
   for z in [40,43,46]:body=body-through_y(sign*24+dx,65,z,.8,18)
 # Low crown bridge recalls the original handle feature.
 for x in [-12,12]:body=body+box(4,12,4,(x,-10,119))
 body=body+box(28,12,3,(0,-10,122))
 # Shallow crown panel seam grooves, leave structural roof thickness.
 for x in [-24,24]:body=body-box(1,25,1.2,(x,-27,117.7))
 return single(body.clean())

def canopy():return Pos(0,6,28)*old.canopy()
def canopy_frame():return Pos(0,6,28)*old.canopy_frame()

def camera_bezel():
 plane=Plane(origin=(0,76.4,46),x_dir=(1,0,0),z_dir=(0,1,0))
 shell=extrude(plane*RectangleRounded(27,20,4),amount=3)
 shell=shell-extrude(plane.offset(-.1)*Circle(6.2),amount=3.2)
 # Two screw tabs are inside the camera frame; trial M2 size.
 for x in [-10,10]:shell=shell-through_y(x,76.3,46,1.15,4)
 return shell

def vent_module():
 plane=Plane(origin=(63.3,0,0),x_dir=(0,1,0),z_dir=(1,0,0))
 outline=Polygon((-5,41),(28,41),(44,52),(44,81),(29,93),(-5,87),align=None)
 inside=Polygon((5,49),(25,49),(37,57),(37,77),(25,85),(5,80),align=None)
 frame=extrude(plane*(outline-inside),amount=4)
 grille=extrude(plane*inside,amount=2)
 for z in [53,61,69,77]:
  grille=grille-box(6,36,4,(65,24,z))
 # Add narrow side uprights to join louvers, then clip to inner shape.
 stiff=box(2,2,42,(64.3,6,67))+box(2,2,42,(64.3,25,67))
 grille=single((grille+stiff).intersect(extrude(plane*inside,amount=2)))
 for z in [50,82]:frame=frame-through_x(63.2,0,z,1.2,5)
 return single(frame),single(grille)

def phone_cradle(p):
 gap=val(p,'phone_clear_width');d=val(p,'phone_clear_depth');top=val(p,'phone_support_top')
 w=gap+8;front=-76-d
 rear=box(w,4,top-40,(0,-74,(top+40)/2))
 rear=rear-box(gap-14,6,top-68,(0,-74,(top+60)/2))
 tray=box(w,d+8,4,(0,-74-d/2,42))
 holder=rear+tray
 for sign in [-1,1]:
  x=sign*(gap/2+2)
  holder=holder+box(4,d+4,70,(x,-76-d/2,79))
  # Return lips stop phone moving outwards; entrance open from above.
  holder=holder+box(7,3,46,(sign*(gap/2+.5),front-1.5,67))
  # Back mounting spacers contact rear head atY-72.
 for x in [-25,25]:
  holder=holder-through_y(x,-79,50,1.2,12)
 # Keep flat backrest structural; soft pads are separate references.
 return single(holder.clean())

def build_model(p):
 COLORS.clear();PART_IDS.clear();LABELS.clear();parts=[]
 def add(s,name,color,pid,label):
  s=single(s);s.label=name;h=color;s.color=Color(*(int(h[i:i+2],16)/255 for i in [1,3,5]));COLORS[name]=color;PART_IDS[name]=pid;LABELS[pid]=label;parts.append(s)
 body=body_shell(p)
 # Color zones are co-printed regions of the same shell, no extra screws.
 masks=[]
 for sign in [-1,1]:masks.append(box(18,45,50,(sign*44,26,104)))
 mask=masks[0]+masks[1]
 accents=single(body.intersect(mask));gray=body-accents
 add(gray,'BODY_GRAY',GRAY,'P01_BODY','01 灰色主体 / 橙色眉甲共印')
 if accents:
  for i,solid in enumerate(accents.solids()):add(solid,f'BODY_ORANGE_{i}',ORANGE,'P01_BODY','01 灰色主体 / 橙色眉甲共印')
 # Thin orange annular cap regions meet gray cap atX67.
 for sign in [-1,1]:
  ann=through_x(67,-40,81,11,1.2)-through_x(66.9,-40,81,8.5,1.4)
  if sign<0:ann=ann.mirror(Plane.YZ)
  add(ann,f'CAP_TRIM_{sign}',ORANGE,'P01_BODY','01 灰色主体 / 橙色眉甲共印')
 add(canopy_frame(),'VISOR_FRAME',GRAY,'P02_VISOR_FRAME','02 可拆面罩框')
 add(canopy(),'CLEAR_VISOR',CLEAR,'P03_CLEAR_VISOR','03 透明折面罩')
 add(bottom_dock(p),'DOCK_BASE',GRAY,'P04_DOCK_BASE','04 深腔对接底座 / 完整套入碗底')
 for sign in [-1,1]:
  frame,grill=vent_module()
  if sign<0:frame=frame.mirror(Plane.YZ);grill=grill.mirror(Plane.YZ)
  add(frame,f'VENT_FRAME_{sign}',ORANGE,f'P05_VENT_{sign}',('05 左' if sign<0 else '06 右')+'可拆风口 / 双色共印')
  # Multiple disconnected louvers would not be independently printable; union with frame defines physical part.
  for i,s in enumerate(grill.solids()):add(s,f'VENT_GRILL_{sign}_{i}',DARK,f'P05_VENT_{sign}',('05 左' if sign<0 else '06 右')+'可拆风口 / 双色共印')
 holder=phone_cradle(p);mask=box(12,40,120,(val(p,'phone_clear_width')/2+3,-83,95))+box(12,40,120,(-val(p,'phone_clear_width')/2-3,-83,95))
 accents=single(holder.intersect(mask));gray=holder-accents
 add(gray,'PHONE_GRAY',GRAY,'P07_PHONE','07 手机架 / 75mm带壳宽度')
 for i,s in enumerate(accents.solids()):add(s,f'PHONE_ORANGE_{i}',ORANGE,'P07_PHONE','07 手机架 / 75mm带壳宽度')
 add(camera_bezel(),'CAMERA_BEZEL',ORANGE,'P08_CAMERA','08 摄像头装饰框 / 孔位待实测')
 return Compound(children=parts,label='LINGXI_R03_REVIEW')

def oled_references():
 p=load_parameters(ROOT/'parameters.yaml');ow=val(p,'oled_board_width');oh=val(p,'oled_board_height');spacing=val(p,'oled_center_spacing')
 plane=Plane(origin=(0,63.9665,80),x_dir=(1,0,0),z_dir=(0,1,.5333));refs=[]
 for x,side in [(-spacing/2,'L'),(spacing/2,'R')]:
  pcb=extrude((plane.offset(-7)*Pos(x,0))*Rectangle(ow,oh),amount=-1.6);pcb.label='REF_OLED_'+side+'_27x28_APPROX';refs.append((pcb,'#315F86FF'))
  display=extrude((plane.offset(-6.8)*Pos(x,1.5))*Rectangle(24,16),amount=.3);display.label='REF_DISPLAY_'+side+'_ACTIVE_UNMEASURED';refs.append((display,'#10191FFF'))
  eye=extrude((plane.offset(-6.4)*Pos(x,1.5))*Polygon((-9,-2),(-4,-3),(4,-3),(9,-2),(9,0),(4,-1),(-4,-1),(-9,0),align=None),amount=.15);eye.label='REF_OLED_PIXELS_'+side;refs.append((eye,'#FFAD30FF'))
 mask=extrude(plane.offset(-6.3)*Rectangle(70,34),amount=.5)
 for x in [-spacing/2,spacing/2]:mask=mask-extrude((plane.offset(-6.4)*Pos(x,1.5))*Rectangle(24.4,16.4),amount=.8)
 mask.label='REF_EDGE_MASK_ACTIVE_AREA_UNMEASURED';refs.append((mask,DARK))
 return refs

def hardware_references(p):
 refs=oled_references()
 # Fixed bowl sourced from its own unchanged R02 builder, identity transform.
 path=ROOT.parent/'lingxi_magnetic_bowl_mount/source/model.py'
 spec=importlib.util.spec_from_file_location('fixed_bowl',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 bowl=mod.build_model(mod.load_parameters(path.parents[1]/'parameters.yaml'));bowl.label='REF_FIXED_BOWL_R02'
 refs.append((bowl,'#A6B4C0FF'))
 board=box(50,120,1.6,(0,0,41));board.label='REF_BOARDS_120x50_APPROX';refs.append((board,'#375E56FF'))
 # Phone thickness only visual, not a measured specification.
 phone=box(val(p,'phone_nominal_width'),10,150,(0,-82,119));phone.label='REF_PHONE_75_WIDTH_THICKNESS_ASSUMED';refs.append((phone,'#323C48AA'))
 for sign in [-1,1]:
  pad=box(.6,8,45,(sign*(val(p,'phone_clear_width')/2-.3),-81,70));pad.label=f'REF_SOFT_PAD_{sign}';refs.append((pad,'#59616BFF'))
 return refs

def write_step(model,path):export_step(model,str(path))
if __name__=='__main__':
 m=build_model(load_parameters(ROOT/'parameters.yaml'))
 for s in m.children:print(s.label,s.is_valid,len(s.solids()),round(s.volume,1),flush=True)
