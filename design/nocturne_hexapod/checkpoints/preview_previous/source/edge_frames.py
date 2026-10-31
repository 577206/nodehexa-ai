"""W50 perimeter bands. Keep original central structure; move external mounts.
Lower references preserve mesh-derived facets, not nominal analytic surfaces.
"""
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from build123d import Compound

def cut(a,b):
 op=BRepAlgoAPI_Cut(a.wrapped,b.wrapped);op.SetFuzzyValue(.0001);op.Build();return Compound.cast(op.Shape())

import json
import numpy as np
from functools import lru_cache
from build123d import Face,Wire,Solid,Pos,Box,Color
from lower_frame import ROOT,reference_bottom,widened_bottom,common

def prism(loop,h=3):
 return Solid.extrude(Face(Wire.make_polygon([(x,y,0) for x,y in loop],close=True)),(0,0,h))

def widen(loop,cy,amount):
 out=[]
 for i,a in enumerate(loop):
  b=loop[(i+1)%len(loop)];sgn=1 if a[1]>=cy else -1
  out.append([a[0],a[1]+sgn*amount/2])
  if (a[1]-cy)*(b[1]-cy)<0:
   x=a[0]+(cy-a[1])/(b[1]-a[1])*(b[0]-a[0]);out.extend([[x,cy+sgn*amount/2],[x,cy-sgn*amount/2]])
 return out

@lru_cache(maxsize=4)
def edge_top(amount=50.):
 d=json.loads((ROOT/'validation/interfaces/BodyTop_section.json').read_text());loops=d['loops_uv_mm'];cy=74.34314727783203/2
 # Keep central aperture and the two central cover-mount holes unchanged.
 result=prism(widen(loops[0],cy,amount))
 for i,loop in enumerate(loops[1:],1):
  fixed=i in (1,5,11)
  hole=prism(loop)
  if not fixed:hole=Pos(0,(1 if np.mean(np.array(loop)[:,1])>cy else -1)*amount/2,0)*hole
  result=result-hole
 result=result.clean();result.label='N001_upper_frame_EDGE50_DRAFT';result.color=Color(.90,.93,.97)
 return result

def lower_mount_masks(amount=50.):
 # Full original lower mounting blocks, including bearing seats and slot ends.
 for side in [-1,1]:
  ranges=[(-1,26,5,30),(104,132,5,30),(54,77,-1,18)]
  for x0,x1,y0,y1 in ranges:
   if side==1:y0,y1=78.34314823150635-y1,78.34314823150635-y0
   yield Pos((x0+x1)/2,(y0+y1)/2+side*amount/2,4.5)*Box(x1-x0,y1-y0,12)

@lru_cache(maxsize=4)
def edge_bottom(name='BodyButtom',amount=50.):
 from build123d import import_brep
 if abs(amount-50)>1e-8:
  raise ValueError('Lower EDGE50 frame requires rebuilding source/build_edge_bottom_freecad.py for a changed extension')
 result=import_brep(ROOT/'validation/interfaces'/f'{name}_edge50.brep')
 result.label='N002_lower_frame_EDGE50_DRAFT' if name=='BodyButtom' else 'N003_lower_frame_18650_2S_EDGE50_ALTERNATIVE_DRAFT'
 result.color=Color(.90,.93,.97)
 return result
