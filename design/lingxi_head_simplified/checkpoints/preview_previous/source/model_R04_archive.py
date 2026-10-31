"""R04: rebuilt layered cockpit. CAD units mm, X right Y front Z up.
Actual printable solids, no render-only armour. Fixed R02 bowl is unchanged.
Electronics mounting and magnetic compression remain trial-fit parameters.
"""
from pathlib import Path
import yaml, importlib.util, math
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('r03',ROOT/'source/model_R03_archive.py');r03=importlib.util.module_from_spec(sp);sp.loader.exec_module(r03)
old=r03.old
GRAY='#7C8388FF';DARK='#41484FFF';ORANGE='#F37824FF';CLEAR='#B3A39448';LIGHT='#939A9FFF'
COLORS={};PART_IDS={};LABELS={}
box=r03.box;single=r03.single;volume=r03.volume;through_y=r03.through_y;through_x=r03.through_x;solid_rr=r03.solid_rr
load_parameters=r03.load_parameters;val=r03.val
# Narrow base, broad cheeks, tapering crown. Rear remains upright through the body.
ROWS=[(49,60,-56,14,0),(57,70,-64,17,10),(62,74,-66,17,28),(62,70,-66,17,50),(56,54,-65,14,76),(46,35,-61,11,96),(36,23,-51,9,108),(32,17,-45,8,111)]
STATIONS=[(39,77,35),(48,76,41),(74,62,42),(96,40,34),(107,26,27)]
BASE_CUP=None;OUTER=None;BODYSHELL=None;FASTENERS=[]
def poly(points):
 area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
 return Polygon(*(points if area>0 else list(reversed(points))),align=None)
def xy(points,z):return Plane.XY.offset(z)*poly(points)
def yz(points,x,depth):return extrude(Plane(origin=(x,0,0),x_dir=(0,1,0),z_dir=(1,0,0))*poly(points),amount=depth)
def xz(points,y,depth):return extrude(Plane(origin=(0,y,0),x_dir=(1,0,0),z_dir=(0,-1,0))*poly(points),amount=depth)
def union(*shapes):
 out=shapes[0]
 for sh in shapes[1:]:out=out+sh
 return single(out).clean()
def mirror(s,sign):return s if sign>0 else s.mirror(Plane.YZ)
def edge_break(s,size=.6):
 try:
  out=chamfer(s.edges(),length=size)
  if out.is_valid and len(out.solids())==len(s.solids()):return out
 except Exception:pass
 return s

def envelope():return loft([old.octagon(r) for r in ROWS],ruled=True)
def skin_x(points,stand=.0,t=2.8):
 return single(((Pos(stand+t,0,0)*OUTER)-(Pos(stand,0,0)*OUTER)).intersect(yz(points,0,100))).clean()
def front_skin(points,stand=0,t=2.4):
 return single(((Pos(0,stand+t,0)*OUTER)-(Pos(0,stand,0)*OUTER)).intersect(xz(points,110,110))).clean()

def bottom_dock(p):
 # Reuse exact central receiving cup + fasteners; replace only external high skirt.
 prior=r03.bottom_dock(p)
 central=single(prior.intersect(box(104,96,36,(0,0,17))))
 # Clip R03 outer skirt remnants off cup using rounded envelope incl screw bosses.
 cup_boundary=solid_rr(94,94,11,-.2,35)
 for side in [-1,1]:cup_boundary=cup_boundary+Pos(side*46,0,-.2)*Cylinder(5.9,35,align=(Align.CENTER,Align.CENTER,Align.MIN))
 central=single(central.intersect(cup_boundary))
 outside=envelope()
 # Low structural plinth; front cheeks now start low, cup lives inside shell.
 inner=loft([old.octagon((w-3,f-3,b+3,c-1,z-.1 if i==0 else z)) for i,(w,f,b,c,z) in enumerate(ROWS)],ruled=True)
 skirt=single((outside-inner).intersect(box(200,200,9.8,(0,0,4.9))))
 # Four short radial webs only below the board/bowl interfaces.
 webs=[]
 for sign in [-1,1]:
  webs.append(box(10,3,5,(sign*49,0,2.5)))
  webs.append(box(3,16,5,(0,sign*49,2.5)))
 base=union(central,skirt,*webs)
 # Re-cut full fixed bowl receiving envelope: preserves zero interference.
 cl=val(p,'dock_radial_clearance');h=val(p,'base_thickness');roof=val(p,'bowl_height')-2+cl
 cavity=loft([Plane.XY.offset(-.1)*RectangleRounded(val(p,'dock_pocket'),val(p,'dock_pocket'),7+cl),Plane.XY.offset(roof)*RectangleRounded(82+2*cl,82+2*cl,7+cl)],ruled=True)
 base=base-cavity
 return single(base).clean()

def visor_geometry():
 # Shared continuous folded clear panel (12 main facets), with shaped five-sided rails.
 glass_sections=[];rails=[]
 for z,y,w in STATIONS:
  top=[(-w,y-8),(-w+8,y),(w-8,y),(w,y-8)]
  glass_sections.append(xy(top+[(x,yy-1.4) for x,yy in reversed(top)],z))
 glass=loft(glass_sections,ruled=True).clean()
 for side in [-1,1]:
  wires=[]
  for z,y,w in STATIONS:
   pts=[(w+.3,y-9.7),(w+7.6,y-9.7),(w+9.4,y-7.5),(w+8,y-3.5),(w+1,y-3.5),(w+.3,y-4.5)]
   if side<0:pts=[(-x,yy) for x,yy in reversed(pts)]
   wires.append(xy(pts,z-.2 if z==39 else z+.2 if z==107 else z))
  rails.append(loft(wires,ruled=True))
 # End returns follow lateral visor fold instead of a floating straight bar.
 for idx in [0,-1]:
  z,y,w=STATIONS[idx]
  cross=[(-w-7,y-9.7),(-w+6,y+.4),(w-6,y+.4),(w+7,y-9.7),(w+7,y-6.2),(w-6,y+4),(-w+6,y+4),(-w-7,y-6.2)]
  rails.append(extrude(xy(cross,z-3 if idx==0 else z),amount=3.2))
 frame=union(*rails)
 # Narrow rear support lips overlap the glass margin only in projection: their
 # front face sits behind the 1.4mm glass, allowing frame to clamp against body.
 supports=[]
 for side in [-1,1]:
  sections=[]
  for z,y,w in STATIONS:
   pts=[(w-1.1,y-10.4),(w+1.0,y-10.4),(w+1.0,y-9.7),(w-1.1,y-9.7)]
   if side<0:pts=[(-x,yy) for x,yy in reversed(pts)]
   sections.append(xy(pts,z))
  supports.append(loft(sections,ruled=True))
 frame=union(frame,*supports)
 # Screw seats bottom and crown only; remove visor by lifting complete frame.
 for x,y,z in [(-31,72.0,37),(31,72.0,37),(-23,23,108.6),(23,23,108.6)]:
  frame=frame-through_y(x,y-5,z,1.2,14)
 return glass,frame.clean()

def sidepose(s,sign=1):return mirror(Pos(65,47,47)*Rot(Z=28)*s,sign)
VENT_OUT=[(-23,-21),(8,-23),(21,-10),(21,12),(9,25),(-19,20)]
VENT_IN=[(-16,-14),(5,-16),(14,-7),(14,10),(6,17),(-12,13)]
def vent_geometry():
 # All black/gray louvers join the perimeter of their respective screw-on module.
 raw=yz(VENT_OUT,-3,6)
 # 0.6 mm edge breaks modelled in CAD, retained in export.
 raw=edge_break(raw,.6)
 raw=raw-yz(VENT_IN,-3.1,6.2)
 for y,z in [(-18,-12),(-15,15)]:raw=raw-through_x(-4,y,z,1.2,9)
 grid=yz(VENT_IN,-1.0,2)
 for z in [-10,-3,4,11]:grid=grid-box(5,25,3.4,(0,1,z))
 # Seat side bridges make grille physically continuous with perimeter.
 grid=union(grid,box(2,2,31,(0,-13,0)))
 grid=single(grid.intersect(yz(VENT_IN,-1,2)))
 return raw,grid

def camera_frame():
 shape=[(-10,13),(10,13),(15,18),(15,34),(10,39),(-10,39),(-15,34),(-15,18)]
 s=edge_break(xz(shape,79,5),.65)
 s=s-through_y(0,72,26,8,10)
 for x in [-11,11]:s=s-through_y(x,72,26,1.15,10)
 return s

def phone_cradle(p):
 # Upright, sculpted side jaws and broad lower back support, open top insertion.
 gap=val(p,'phone_clear_width');d=val(p,'phone_clear_depth');top=val(p,'phone_support_top');back=-72
 outline=[(-gap/2-4,43),(gap/2+4,43),(gap/2+4,top-4),(gap/2,top),(-gap/2,top),(-gap/2-4,top-4)]
 shell=xz(outline,back+2,4)
 opening=[(-gap/2+8,63),(gap/2-8,63),(gap/2-8,top-10),(-gap/2+8,top-10)]
 shell=shell-xz(opening,back+3,6)
 tray=box(gap+8,d+8,4,(0,back-d/2,44))
 shell=shell+tray
 jaw=[(back-2,44),(back-d-5,44),(back-d-5,98),(back-d-3,106),(back-d+1,109),(back-2,109)]
 for side in [-1,1]:
  shell=shell+mirror(yz(jaw,gap/2,4),side)
  shell=shell+box(5,3,51,(side*(gap/2-.5),back-d-3.5,69.5))
  # shaped screw boss/spacer onto upright rear shell
  shell=shell+box(10,4,12,(side*25,-69,50))
 for x in [-25,25]:shell=shell-through_y(x,-80,50,1.2,19)
 return edge_break(single(shell).clean(),.5)

def build_model(p):
 global OUTER,BASE_CUP,BODYSHELL
 COLORS.clear();PART_IDS.clear();LABELS.clear();FASTENERS.clear();parts=[]
 def add(sh,name,color,pid,label):
  sh=single(sh)
  for i,s in enumerate(sh.solids()):
   nm=name if len(sh.solids())==1 else name+'_'+str(i)
   s.label=nm;s.color=Color(*(int(color[k:k+2],16)/255 for k in [1,3,5]));parts.append(s);COLORS[nm]=color;PART_IDS[nm]=pid;LABELS[pid]=label
  return sh
 print('BUILD outer',flush=True);OUTER=envelope();wall=val(p,'wall')
 inner=[]
 for i,(w,f,b,c,z) in enumerate(ROWS):inner.append((w-wall,f-wall,b+wall,c-1.2,z-.1 if i==0 else z-wall if i==len(ROWS)-1 else z))
 body=fillet(OUTER.edges(),radius=.65)-loft([old.octagon(r) for r in inner],ruled=True)
 body=single(body.intersect(box(220,220,130,(0,0,75)))) # z10+
 glass,frame=visor_geometry()
 body=body-old.rect_loft(STATIONS,1.0,-.5,.5)
 body=body-frame-glass
 print('BUILD dock',flush=True);base=bottom_dock(p);BASE_CUP=base
 body=body-base
 # Internal supports for retained two base screws, joining to both side walls.
 for side in [-1,1]:
  x=side*val(p,'screw_span')/2
  body=body+box(16,10,8,(side*54,0,38))
  body=body+Pos(x,0,34)*Cylinder(6,10,align=(Align.CENTER,Align.CENTER,Align.MIN))
  body=body-Pos(x,0,33.9)*Cylinder(1.05,10.3,align=(Align.CENTER,Align.CENTER,Align.MIN))
 # Rich body-following side armor, fused into the shell to limit screw count.
 print('BUILD armor',flush=True);orange_masks=[]
 for side in [-1,1]:
  # Gray diagonal cheek sweeps toward the upper rear circular cap.
  cheek=skin_x([(46,54),(41,67),(17,81),(-23,82),(-41,73),(-39,62),(-12,66),(16,64),(31,53)],-.3,4.2)
  body=body+mirror(cheek,side)
  # Orange shoulder rail follows the actual shell rather than a painted patch.
  shoulder=skin_x([(43,78),(32,99),(16,108),(-17,108),(-37,98),(-44,83),(-35,81),(-29,93),(-14,101),(14,101),(25,94),(34,76)],-.3,3.4)
  body=body+mirror(shoulder,side);orange_masks.append(mirror(shoulder,side))
  # Gray raised overstrap: broad angled inset, leave orange border visible.
  strap=skin_x([(30,81),(24,96),(12,106),(-9,106),(-23,99),(-26,91),(-19,89),(-15,96),(-7,100),(10,100),(17,93),(22,79)],2.8,2.3)
  # A slender embedded stem ties the skin into the shell; upper strap remains raised.
  tie=skin_x([(24,81),(28,82),(19,96),(14,101),(10,100),(16,93)],-.15,3.5)
  body=body+mirror(union(strap,tie),side)
  # Rear orange intake pad, deliberately only 2 broad slots, integral.
  intake=skin_x([(-49,81),(-47,94),(-39,102),(-30,99),(-32,85)],-.2,4)
  for yy in [-43,-38]:intake=intake-yz([(yy,85),(yy+1.3,85),(yy+1.3,96),(yy,96)],53,8)
  body=body+mirror(intake,side);orange_masks.append(mirror(intake,side))
  # Vent socket cut is identical to the angled screw-on module envelope.
  body=body-sidepose(yz(VENT_OUT,-20,30),side)
  for yy,zz in [(-18,-12),(-15,15)]:
   seat=sidepose(through_x(-20,yy,zz,3.8,16.8),side)
   body=body+seat
   body=body-sidepose(through_x(-21,yy,zz,1.05,23),side)
  # Circular rear service cover on a sculpted chassis cheek.
  mount=through_x(50,-31,74,16,12)
  body=body+mirror(mount,side)
  body=body-mirror(through_x(60.5,-31,74,12.7,3),side)
  # lower inset maintenance ribs below side disc; maintain left USB corridor
  if side>0:
   for zz in [30,35]:body=body-mirror(box(4,28,1.3,(61,-28,zz)),side)
 # Large left-side opening, keep actual board-local coordinate from user.
 body=body-box(45,val(p,'usb_access_width'),val(p,'usb_access_height'),(-59,-24,val(p,'usb_access_center_z')))
 # Front perforated cheek panels and lowered camera at Z26, ahead of bowl.
 for side in [-1,1]:
  patch=front_skin([(18,13),(33,14),(38,35),(35,38),(18,38)],-.25,3.3)
  body=body+mirror(patch,side)
  for x in [22,27,32]:
   for z in [20,24,28,32]:body=body-through_y(side*x,59,z,1,23)
 body=body-through_y(0,55,26,7.8,30)
 for side in [-1,1]:
  body=body+through_y(side*11,69,26,3,5)
  body=body-through_y(side*11,68,26,1.05,7)
 # Rear attachment supports follow near vertical rear wall; port is on left.
 for x in [-25,25]:
  body=body+box(10,5,12,(x,-64.5,50))
  body=body-through_y(x,-70,50,1.05,12)
 # Crown hatch integrates a low bridge handle and shallow recessed slots.
 hatch=edge_break(Pos(0,-12,111)*extrude(RectangleRounded(51,43,5),amount=2.4),.45)
 # Attach crown plate to sloping shell with four short feet.
 for x in [-18,18]:
  for y in [-25,0]:body=body+box(4,5,6,(x,y,108.5))
 body=body+hatch
 for x in [-12,12]:body=body+box(4,9,4,(x,-17,115))
 body=body+edge_break(box(28,9,3,(0,-17,118)),.6)
 for x in [-17,17]:body=body-box(1.6,15,1,(x,2,113.1))
 # Clean full receiver again after merging armor. Module/body contact is nominal.
 # Deliberate crown corner clearance notches remove the two frame-cut thin wedges.
 for side in [-1,1]:body=body-box(3.2,5.2,4.5,(side*29.3,24.7,105.5))
 # Camera overlaps lower frame only at the crown of its orange border; relief is intentional.
 frame=single(frame-camera_frame())
 body=single(body-frame-glass-base)
 # Aligned pilot holes behind the four frame screws.
 for x,y,z in [(-31,72.0,37),(31,72.0,37),(-23,23,108.6),(23,23,108.6)]:
  body=body-through_y(x,y-9,z,1.05,16)
 # Split integral colored cap regions against the main shell, avoiding duplicate volume.
 cap_regions=[]
 for side in [-1,1]:
  ann=through_x(62,-31,74,14.6,2)-through_x(61.9,-31,74,11.8,2.2)
  disc=through_x(60.5,-31,74,11.8,3.5)+through_x(58,-31,74,3,4)
  disc=disc-through_x(63,-31,74,1.4,2)
  cap_regions.extend([mirror(ann,side),mirror(disc,side)])
 for region in cap_regions:body=body-region
 # True solid color regions: no overlapping colour overlays.
 print('BUILD colors',flush=True);combined=union(*orange_masks);acc=single(body.intersect(combined));gray=body-acc
 add(gray,'SHELL_GRAY',GRAY,'P01_SHELL','01 头盔主体 / 实体分层灰甲')
 add(acc,'SHOULDER_ORANGE',ORANGE,'P01_SHELL','01 头盔主体 / 橙色肩框')
 for side in [-1,1]:
  ann=through_x(62,-31,74,14.6,2)-through_x(61.9,-31,74,11.8,2.2)
  disc=through_x(60.5,-31,74,11.8,3.5)
  # Integral axle ties inner disk to outer cap support.
  disc=disc+through_x(58,-31,74,3,4)
  disc=disc-through_x(63,-31,74,1.4,2)
  add(mirror(ann,side),f'CAP_RING_{side}',ORANGE,'P01_SHELL','01 头盔主体 / 橙色圆盖环')
  add(mirror(disc,side),f'CAP_FACE_{side}',DARK,'P01_SHELL','01 头盔主体 / 灰色圆盖芯')
 add(frame,'VISOR_FRAME',GRAY,'P02_VISOR','02 宽折面罩压框')
 add(glass,'CLEAR_VISOR',CLEAR,'P03_CLEAR','03 独立透明折面罩')
 add(base,'DOCK_BASE',DARK,'P04_BASE','04 内藏29mm深腔 / 碗底不变')
 vf,vg=vent_geometry()
 for side in [-1,1]:
  add(sidepose(vf,side),f'VENT_FRAME_{side}',ORANGE,f'P05_VENT_{side}','05 左风口' if side<0 else '06 右风口')
  add(sidepose(vg,side),f'VENT_GRILLE_{side}',DARK,f'P05_VENT_{side}','05 左风口' if side<0 else '06 右风口')
 holder=phone_cradle(p);mask=box(10,40,130,(41,-80,95))+box(10,40,130,(-41,-80,95))
 acol=single(holder.intersect(mask));add(holder-acol,'PHONE_BACK',GRAY,'P07_PHONE','07 直立手机托 / 含壳75mm')
 add(acol,'PHONE_JAWS',ORANGE,'P07_PHONE','07 直立手机托 / 含壳75mm')
 add(camera_frame(),'CAMERA_BEZEL',ORANGE,'P08_CAMERA','08 低位镜头框')
 BODYSHELL=body
 return Compound(children=parts,label='LINGXI_R04_COCKPIT')

def oled_references():
 p=load_parameters(ROOT/'parameters.yaml');ow=val(p,'oled_board_width');oh=val(p,'oled_board_height');sp=val(p,'oled_center_spacing')
 plane=Plane(origin=(0,68.8,61.5),x_dir=(1,0,0),z_dir=(0,1,.5385));refs=[]
 for x,side in [(-sp/2,'L'),(sp/2,'R')]:
  pcb=extrude((plane.offset(-7)*Pos(x,0))*Rectangle(ow,oh),amount=-1.6);pcb.label='REF_OLED_'+side;refs.append((pcb,'#315F86FF'))
  display=extrude((plane.offset(-6.8)*Pos(x,0))*Rectangle(24,16),amount=.3);display.label='REF_DISPLAY_'+side;refs.append((display,'#11191EFF'))
  # Eye expression is illustrative OLED pixels, not a separate printed strip.
  pts=[(-10,3),(10,-4),(10,-6),(-10,.5)] if x<0 else [(-10,-4),(10,3),(10,.5),(-10,-6)]
  eye=extrude((plane.offset(-6.4)*Pos(x,0))*Polygon(*pts,align=None),amount=.15);eye.label='REF_OLED_PIXELS_'+side;refs.append((eye,'#FF9E32FF'))
 mask=extrude(plane.offset(-6.2)*RectangleRounded(70,34,3),amount=.5)
 for x in [-sp/2,sp/2]:mask=mask-extrude((plane.offset(-6.3)*Pos(x,0))*Rectangle(24.4,16.4),amount=.8)
 mask.label='REF_EDGE_MASK_UNMEASURED';refs.append((mask,'#172025FF'))
 return refs

def hardware_references(p):
 refs=oled_references()
 for sh,c in r03.hardware_references(p):
  if any(s in sh.label for s in ['OLED','DISPLAY','EDGE_MASK','SOFT_PAD']):continue
  if 'PHONE_' in sh.label:sh=Pos(0,2,0)*sh
  refs.append((sh,c))
 # Lens reference provides inspection realism; does not invent camera mount holes.
 lens=through_y(0,74.4,26,7.7,4.2)-through_y(0,77.8,26,5.2,1)
 lens.label='REF_CAMERA_LENS_HOUSING';refs.append((lens,'#30363DFF'))
 glass=through_y(0,77.9,26,5.1,.3);glass.label='REF_CAMERA_LENS_GLASS';refs.append((glass,'#574572FF'))
 # Screw heads illustrated only at real drilled mounting locations.
 for side in [-1,1]:
  for yy,zz in [(-18,-12),(-15,15)]:
   head=through_x(3,yy,zz,2.6,1.5)-through_x(4,yy,zz,1.0,.7)
   head=sidepose(head,side);head.label=f'REF_VENT_SCREW_{side}_{zz}';refs.append((head,'#262D33FF'))
 for xx in [-11,11]:
  head=through_y(xx,79,26,2,1)-through_y(xx,79.5,26,.8,.6)
  head.label=f'REF_CAMERA_SCREW_{xx}';refs.append((head,'#262D33FF'))
 return refs

def write_step(model,path):export_step(model,str(path))
if __name__=='__main__':
 m=build_model(load_parameters(ROOT/'parameters.yaml'))
 for s in m.children:print(s.label,s.is_valid,len(s.solids()),round(s.volume,2),flush=True)
