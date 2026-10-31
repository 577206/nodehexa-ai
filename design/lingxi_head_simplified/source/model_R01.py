from pathlib import Path
import yaml,math
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
COLORS={'H01_ORANGE_SHELL':'#F27619','H02_YELLOW_L':'#FFD329','H03_YELLOW_R':'#FFD329','H04_ORANGE_BASE':'#F27619','H05_CLEAR_VISOR':'#B6E3F280'}
def load_parameters(p):return yaml.safe_load(Path(p).read_text())
def val(p,n):return float(p['parameters'][n]['value'])
def polygon_ring(w,front,back,z):
 c=12
 return Plane.XY.offset(z)*Polygon((-w+c,back),(w-c,back),(w,back+c),(w,front-c),(w-c,front),(-w+c,front),(-w,front-c),(-w,back+c),align=None)
def rounded(w,h,r,z):return Pos(0,0,z)*RectangleRounded(w,h,r)
def window_polygon(w,h):
 return Polygon((-w/2,-h/2+5),(-w/2+5,-h/2),(w/2-5,-h/2),(w/2,-h/2+5),(w/2,h/2-5),(w/2-5,h/2),(-w/2+5,h/2),(-w/2,h/2-5),align=None)
def visor_plane(base):return Plane(origin=(0,70-.55*36,base+36),x_dir=(1,0,0),z_dir=(0,1,.55))
def faceted_shell(p):
 w=val(p,'width')/2;front=val(p,'length')/2+2;back=-(val(p,'length')/2-2);h=val(p,'shell_height');b=val(p,'base_thickness');wall=val(p,'wall')
 outer=loft([polygon_ring(w,front,back,b),polygon_ring(w-14,front-.55*h,back+24,b+h)])
 inner=loft([polygon_ring(w-wall,front-3.43,back+wall,b-.1),polygon_ring(w-14-wall,front-.55*(h-wall)-3.43,back+24+wall,b+h-wall)])
 shell=outer-inner
 plane=visor_plane(b)
 opening=extrude(plane*window_polygon(60,48),amount=12,both=True)
 # A larger backing seat, inset behind a small front lip. Prototype retention only.
 pocket=extrude(plane.offset(-.8)*window_polygon(64.5,52.5),amount=-6)
 shell=shell-opening-pocket
 # Integrated surface detail, no extra printed armor or fasteners.
 for z in [25,32,39,46]:
  x=w-(14*(z-b)/h)
  for sign in [-1,1]:
   shell=shell-Pos(sign*(x+.1),24,z)*Box(2,20,1.6)
 for x in [-15,15]:
  shell=shell-Pos(x,-5,b+h-.35)*Box(2.5,34,1.3)
 # Provisional camera aperture only, not a hardware-specific camera mount.
 camera_plane=Plane(origin=(0,front-.55*8,b+8),x_dir=(1,0,0),z_dir=(0,1,.55))
 shell=shell-extrude(camera_plane*Circle(5),amount=8,both=True)
 return shell

def visor_seat(p):
 plane=visor_plane(val(p,'base_thickness'));c=val(p,'visor_clearance')
 return extrude(plane.offset(-.8-c)*window_polygon(64.5-2*c,52.5-2*c),amount=-(2.6-2*c))

def two_fasteners(p,shell):
 b=val(p,'base_thickness');span=val(p,'screw_span')
 for sign in [-1,1]:
  x=sign*span/2
  shell=shell+Pos(x,0,b)*Cylinder(6,9,align=(Align.CENTER,Align.CENTER,Align.MIN))
  shell=shell-Pos(x,0,b-.1)*Cylinder(val(p,'shaft_diameter')/2,9.2,align=(Align.CENTER,Align.CENTER,Align.MIN))
 return shell.clean()

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

def color_regions(p,shell):
 parts=[];y=val(p,'yellow_start')
 for sign,label in [(-1,'H02_YELLOW_L'),(1,'H03_YELLOW_R')]:
  mask=Pos(sign*(y+20),35,35)*Box(40,65,36)
  region=shell.intersect(mask)
  if isinstance(region,ShapeList):region=Compound(children=list(region))
  shell=shell-region
  region.label=label;parts.append(region)
 shell.label='H01_ORANGE_SHELL'
 return [shell]+parts

def build_model(p):
 shell=two_fasteners(p,faceted_shell(p))
 parts=color_regions(p,shell)
 base=bottom_dock(p);base.label='H04_ORANGE_BASE';parts.append(base)
 visor=visor_seat(p);visor.label='H05_CLEAR_VISOR';parts.append(visor)
 for part in parts:
  he=COLORS[part.label];part.color=Color(*(int(he[i:i+2],16)/255 for i in (1,3,5)))
 return Compound(children=parts,label='LINGXI_SIMPLIFIED_HEAD_R01')

def write_step(model,path):
 Path(path).parent.mkdir(parents=True,exist_ok=True);export_step(model,str(path))
if __name__=='__main__':
 m=build_model(load_parameters(ROOT/'parameters.yaml'))
 for part in m.children:print(part.label,part.is_valid,len(part.solids()),round(part.volume,2))
