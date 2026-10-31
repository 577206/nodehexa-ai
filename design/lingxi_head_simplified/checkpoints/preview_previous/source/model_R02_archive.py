"""R02 restored faceted head with shared canopy and provisional twin OLED layout.
Actual OLED mounting holes/active mask apertures are intentionally not fabricated.
"""
from pathlib import Path
import yaml,math
from build123d import *
def load_parameters(p):return yaml.safe_load(Path(p).read_text())

def val(p,n):return float(p['parameters'][n]['value'])

def polygon_ring(w,front,back,z):
 c=12
 return Plane.XY.offset(z)*Polygon((-w+c,back),(w-c,back),(w,back+c),(w,front-c),(w-c,front),(-w+c,front),(-w,front-c),(-w,back+c),align=None)

def bottom_dock(p):
 b=val(p,'base_thickness');w=val(p,'width');l=val(p,'length');d=val(p,'dock_pocket')
 base=extrude(polygon_ring(w/2,l/2+2,-(l/2-2),0),amount=b)
 base=base-extrude(RectangleRounded(d,d,5.3),amount=val(p,'dock_depth'))
 # Accommodate the one asymmetrical key on fixed R01 rim.
 base=base-Pos(11,38,0)*Box(6.6,4.6,val(p,'dock_depth'),align=(Align.CENTER,Align.CENTER,Align.MIN))
 base=base+Pos(0,0,b-.1)*extrude(RectangleRounded(26,10,2),amount=1.5)
 base=base-Pos(0,0,val(p,'dock_depth')-.05)*extrude(RectangleRounded(20,4.5,2.2),amount=4.05)
 base=base-Pos(0,0,6.3)*extrude(RectangleRounded(12,2.4,.4),amount=2)
 for sign in [-1,1]:
  x=sign*val(p,'screw_span')/2
  base=base-Pos(x,0,-.1)*Cylinder(val(p,'shaft_diameter')/2,b+.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
  base=base-Pos(x,0,-.1)*Cylinder(val(p,'pan_recess_diameter')/2,2.1,align=(Align.CENTER,Align.CENTER,Align.MIN))
 return base.clean()
ROOT=Path(__file__).resolve().parents[1]
COLORS={'R02_ORANGE_BODY':'#F27619FF','R02_YELLOW_SIDE_L':'#FFD329FF','R02_YELLOW_SIDE_R':'#FFD329FF','R02_YELLOW_VISOR_FRAME':'#FFD329FF','R02_CLEAR_CANOPY':'#C5E5EE30','R02_ORANGE_BASE':'#F27619FF'}
# Width/front/rear/chamfer/height; richer original-R06-inspired stations.
ROWS=[(52,70,-66,14,6),(57,65,-63,14,36),(48,49,-51,13,66),(31,26,-31,9,90)]
# Front canopy wraps around two sides and folds across three height spans.
STATIONS=[(26,68.167,35),(38,65.433,39),(66,50.5,39),(82,35.167,30)]

def octagon(row):
 w,f,b,c,z=row
 return Plane.XY.offset(z)*Polygon((-w+c,b),(w-c,b),(w,b+c),(w,f-c),(w-c,f),(-w+c,f),(-w,f-c),(-w,b+c),align=None)
def xy_profile(points,z):return Plane.XY.offset(z)*Polygon(*points,align=None)
def rect_loft(stations,extra=0,zlo=0,zhi=0):
 wires=[]
 for i,(z,y,w) in enumerate(stations):
  zz=z+(zlo if i==0 else zhi if i==len(stations)-1 else 0)
  wires.append(xy_profile([(-w-extra,15),(w+extra,15),(w+extra,120),(-w-extra,120)],zz))
 return loft(wires,ruled=True)
def body_shell(p):
 wall=val(p,"wall")
 outer=loft([octagon(r) for r in ROWS],ruled=True)
 inner=[]
 for i,(w,f,b,c,z) in enumerate(ROWS):
  inner.append((w-wall,f-wall-.4,b+wall,c-1.3,z-.1 if i==0 else z-wall if i==len(ROWS)-1 else z))
 body=outer-loft([octagon(r) for r in inner],ruled=True)
 # Remove a real receiver for the wrapped clear canopy and its one-piece frame.
 body=body-rect_loft(STATIONS,5.0,-3.2,3.2)
 # Integrated rounded side caps, cut louvers and roof grooves: no decorative screws.
 for sign in [-1,1]:
  plane=Plane(origin=(sign*51,-16,49),x_dir=(0,1,0),z_dir=(sign,0,0))
  cap=extrude(plane*Circle(12),amount=7)
  body=body+cap
  body=body-extrude(plane.offset(5.5)*Circle(8.8),amount=2)
 for z in [27,34,41,48,55]:
  # Outer X follows piecewise facade profile.
  w=57-(max(0,z-36))*9/30 if z>=36 else 52+(z-6)*5/30
  for sign in [-1,1]:body=body-Pos(sign*(w+.2),12,z)*Box(2,21,1.8)
 for x in [-12,12]:body=body-Pos(x,-4,89.6)*Box(2.5,26,1.5)
 # Lower camera opening remains an explicitly provisional appearance aperture.
 plane=Plane(origin=(0,68,18),x_dir=(1,0,0),z_dir=(0,1,.167))
 bezel=extrude(plane*RectangleRounded(25,15,3),amount=2)
 body=body+bezel
 body=body-extrude(plane*Circle(5.2),amount=12,both=True)
 # Two base locations retained; final threaded receivers are still not released.
 for x in [-45,45]:
  body=body+Pos(x,0,6)*Cylinder(6,9,align=(Align.CENTER,Align.CENTER,Align.MIN))
  body=body-Pos(x,0,5.9)*Cylinder(1.2,9.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
 # Two low visor-frame anchor pads, independent of the magnetic seam.
 for x in [-30,30]:
  pl=Plane(origin=(x,61.8,22.0),x_dir=(1,0,0),z_dir=(0,1,0))
  body=body+extrude(pl*Circle(3.3),amount=6.567)
  body=body-extrude(pl.offset(-.1)*Circle(1.0),amount=6.9)
 # Local relief below the main visor receiver for the two lower frame returns.
 # 0.3mm clearance; keep the central lower screw anchor pads untouched.
 for x in [-37,37]:body=body-Pos(x,64,24)*Box(3.6,12,4.6)
 return body.clean()

def canopy():
 sections=[]
 for z,y,w in STATIONS:
  outer=[(-w,y-7),(-w+8,y),(w-8,y),(w,y-7)]
  points=outer+[(x,yy-1.5) for x,yy in reversed(outer)]
  sections.append(xy_profile(points,z))
 return loft(sections,ruled=True).clean()

def canopy_frame():
 rails=[]
 for sign in [-1,1]:
  profiles=[]
  for z,y,w in STATIONS:
   ys=y-7
   # Thin forward lip, outside glass; small rear bearing lip.
   pp=[(w+.35,ys-1.9),(w+3.5,ys-1.9),(w+3.5,ys+1.7),(w-.6,ys+1.7),(w-.6,ys+.8),(w+.35,ys+.8)]
   if sign<0:pp=[(-x,yy) for x,yy in reversed(pp)]
   profiles.append(xy_profile(pp,z-.5 if z==STATIONS[0][0] else z+.5 if z==STATIONS[-1][0] else z))
  rails.append(loft(profiles,ruled=True))
 # End straps join both side rails outside the clear-panel height interval.
 for i in [0,-1]:
  z,y,w=STATIONS[i];zz=z-4.0 if i==0 else z+1.7
  bar=Pos(0,y+1.5,zz)*Box(2*w+7,2.6,4 if i==0 else 3)
  rails.append(bar)
  for sign in [-1,1]:rails.append(Pos(sign*(w+2),y-3,24 if i==0 else zz)*Box(3,10,4 if i==0 else 3))
 frame=rails[0]
 for shape in rails[1:]:frame=frame+shape
 frame=frame-Pos(0,68,22)*Box(28,24,10)
 # Small matching holes through the lower strap, pan heads face forward.
 for x in [-30,30]:
  pl=Plane(origin=(x,67.8,22.0),x_dir=(1,0,0),z_dir=(0,1,0))
  frame=frame-extrude(pl*Circle(1.2),amount=5)
 return frame.clean()

def build_model(p):
 raw=body_shell(p);regions=[]
 for sign,label in [(-1,'R02_YELLOW_SIDE_L'),(1,'R02_YELLOW_SIDE_R')]:
  mask=Pos(sign*58,-7,46)*Box(38,75,45)
  a=raw.intersect(mask)
  if isinstance(a,ShapeList):a=Compound(children=list(a))
  raw=raw-a;a.label=label;regions.append(a)
 raw.label='R02_ORANGE_BODY'
 frame=canopy_frame();frame.label='R02_YELLOW_VISOR_FRAME'
 glass=canopy();glass.label='R02_CLEAR_CANOPY'
 base=bottom_dock(p);base.label='R02_ORANGE_BASE'
 parts=[raw]+regions+[frame,glass,base]
 for a in parts:
  h=COLORS[a.label];a.color=Color(*(int(h[i:i+2],16)/255 for i in [1,3,5]))
 return Compound(children=parts,label='R02_OLED_MECHA_HEAD_REVIEW')

def oled_references():
 p=load_parameters(ROOT/"parameters.yaml");ow=val(p,"oled_board_width");oh=val(p,"oled_board_height");spacing=val(p,"oled_center_spacing")
 # Provisional envelopes only: NOT included in print export, no guessed PCB holes.
 plane=Plane(origin=(0,57.9665,52),x_dir=(1,0,0),z_dir=(0,1,.5333))
 result=[]
 for x,side in [(-spacing/2,'L'),(spacing/2,'R')]:
  pcb=extrude((plane.offset(-7)*Pos(x,0))*Rectangle(ow,oh),amount=-1.6)
  pcb.label='REF_OLED_'+side+'_27x28_APPROX';result.append((pcb,'#315F86FF'))
  glass=extrude((plane.offset(-6.8)*Pos(x,1.5))*Rectangle(24,16),amount=.3)
  glass.label='REF_DISPLAY_'+side+'_ACTIVE_UNMEASURED';result.append((glass,'#10191FFF'))
  # Purely illustrative pixel expression, not a physical LED strip.
  yy=[(-9,-2),(-4,-3),(4,-3),(9,-2),(9,0),(4,-1),(-4,-1),(-9,0)]
  eye=extrude((plane.offset(-6.4)*Pos(x,1.5))*Polygon(*yy,align=None),amount=.15)
  eye.label='REF_OLED_PIXELS_'+side;result.append((eye,'#FFE238FF'))
 mask=extrude(plane.offset(-6.3)*Rectangle(70,34),amount=.5)
 for x in [-spacing/2,spacing/2]:mask=mask-extrude((plane.offset(-6.4)*Pos(x,1.5))*Rectangle(24.4,16.4),amount=.8)
 mask.label='REF_EDGE_MASK_ACTIVE_AREA_UNMEASURED';result.append((mask,'#F27619FF'))
 return result

def write_step(model,path):export_step(model,str(path))
if __name__=='__main__':
 m=build_model(load_parameters(ROOT/'parameters.yaml'))
 for a in m.children:print(a.label,a.is_valid,len(a.solids()),round(a.volume,1))
 print('OLED refs',len(oled_references()))
