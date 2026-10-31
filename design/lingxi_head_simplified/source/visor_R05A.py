"""Clear removable cover and retaining frame, fitted to unchanged R05 core."""
from pathlib import Path
import importlib.util
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('r05',ROOT/'source/model_R05_archive.py');r05=importlib.util.module_from_spec(sp);sp.loader.exec_module(r05)
r04=r05.r04

def visor_parts(shell):
 glass,frame=r04.visor_geometry()
 # Remove the old rear lips: the clear panel can now be placed from the rear
 # of the detached frame, then secured between front lips and body supports.
 for side in [-1,1]:
  sections=[];front=[]
  for z,y,w in r04.STATIONS:
   pts=[(w-1.1,y-10.4),(w+1.0,y-10.4),(w+1.0,y-9.7),(w-1.1,y-9.7)]
   lip=[(w-1.4,y-6.3),(w+1.0,y-8.7),(w+1.0,y-7.3),(w-1.4,y-4.9)]
   if side<0:
    pts=[(-x,yy) for x,yy in reversed(pts)]
    lip=[(-x,yy) for x,yy in reversed(lip)]
   sections.append(r04.xy(pts,z));front.append(r04.xy(lip,z))
  frame=frame-loft(sections,ruled=True)
  frame=frame+loft(front,ruled=True)
 # The old panel was trapped in the shell's four support cutouts. Bring only
 # this removable subassembly forward5.5mm; the R05 body and bowl stay fixed.
 glass=Pos(0,5.5,0)*glass
 frame=Pos(0,5.5,0)*frame
 # Transparent mounting ears provide real through-fastening/support. The
 # lower two use M2x20 screws/nuts; the existing upper body holes are blind,
 # so the gray frame has integral alignment pins, not fictitious throughbolts.
 for x,z,back,front,rad in [(-31,37,73.0,79.8,3.5),(31,37,73.0,79.8,3.5),(-23,108.6,23.7,29.6,3.1),(23,108.6,23.7,29.6,3.1)]:
  glass=glass+r05.through_y(x,back,z,rad,front-back)
  glass=glass-r05.through_y(x,back-.1,z,1.25,front-back+.2)
  y0,y1=(80.0,85.0) if z<50 else (29.8,34.0)
  frame=frame+r05.through_y(x,y0,z,4.5,y1-y0)
  if z<50:frame=frame-r05.through_y(x,60,z,1.2,30)
 # Subtract the clear ears from their gray outer frame. Front lips overlap
 # the panel edge in projection; actual solid intersections remain zero.
 glass=r05.single(glass).clean()
 frame=frame-shell-glass
 for x in [-23,23]:
  # Pin reaches2.5mm into unchanged blind hole;2.0 vs2.4mm diameters.
  frame=frame+r05.through_y(x,20,108.6,1.0,10.2)
 frame=r05.single(frame).clean()
 return glass,frame

if __name__=='__main__':
 import trimesh,json
 shell=import_brep(str(ROOT/'review/cache/R05_H01_MAIN_SHELL.brep'))
 for name,s in zip(['H03_CLEAR_VISOR','H04_VISOR_FRAME'],visor_parts(shell)):
  v,t=s.tessellate(.055,.12);m=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);m.fix_normals()
  print(name,s.is_valid,len(s.solids()),s.volume,list(s.bounding_box().size),m.is_watertight,m.is_volume,len(m.split()),flush=True)
  export_brep(s,str(ROOT/'review/cache'/f'R05A_{name}.brep'))
