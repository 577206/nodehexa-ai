import FreeCAD as A,Part,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def V(x,y,z):return A.Vector(x,y,z)
def poly(loop,h):
 vs=[V(x,y,0) for x,y in loop];return Part.Face(Part.makePolygon(vs+[vs[0]])).extrude(V(0,0,h))
def move(s,y):
 q=s.copy();q.translate(V(0,y,0));return q
def widen(loop,c,d):
 out=[]
 for i,a in enumerate(loop):
  b=loop[(i+1)%len(loop)];sgn=1 if a[1]>=c else -1;out.append([a[0],a[1]+sgn*d/2])
  if (a[1]-c)*(b[1]-c)<0:
   x=a[0]+(c-a[1])/(b[1]-a[1])*(b[0]-a[0]);out.extend([[x,c+sgn*d/2],[x,c-sgn*d/2]])
 return out
for name in ['BodyButtom','BodyButtom-18650-2S']:
 s=Part.Shape();s.read(str(ROOT/'validation/interfaces'/f'{name}_reference.brep'));b=s.BoundBox;cy=(b.YMin+b.YMax)/2
 lo=s.common(Part.makeBox(150,200,20,V(-10,cy-200,-5)),1e-5)
 hi=s.common(Part.makeBox(150,200,20,V(-10,cy,-5)),1e-5)
 bridges=[]
 for f in lo.Faces:
  bb=f.BoundBox
  if bb.YLength<1e-5 and abs(bb.YMin-cy)<1e-5:bridges.append(move(f,-25).extrude(V(0,50,0)))
 moved=move(lo,-25).multiFuse([move(hi,25)]+bridges,1e-5).removeSplitter()
 outer=json.loads((ROOT/'validation/interfaces'/f'{name}_outer_profile.json').read_text())['outer_loop']
 footprint=poly(outer,12)
 face=poly(outer,0.001).Faces[0]
 wire=Part.Wire(Part.makePolygon([V(x,y,0) for x,y in outer]+[V(*outer[0],0)]).Edges)
 inset=wire.makeOffset2D(-0.05,0,False,False,False)
 insetface=Part.Face(inset.Wires[0] if inset.Wires else inset)
 band=poly(widen(outer,cy,50),3).cut(insetface.extrude(V(0,0,3)),1e-5)
 added=moved.cut(footprint,1e-5)
 masks=[]
 for sign in [-1,1]:
  for x0,x1,y0,y1 in [(-1,26,5,30),(104,132,5,30),(54,77,-1,18)]:
   if sign==1:y0,y1=78.34314823150635-y1,78.34314823150635-y0
   mask=Part.makeBox(x1-x0,y1-y0,12,V(x0,y0+sign*25,-1.5));masks.append(mask);band=band.cut(mask,1e-5)
 print("components",s.isValid(),band.isValid(),added.isValid(),s.Volume,band.Volume,added.Volume,footprint.Volume,flush=True)
 result=s.multiFuse([band,added],1e-5).removeSplitter()
 result.fix(.00001,.00001,.001)
 print(name,result.isValid(),len(result.Solids),result.Volume,flush=True)
 if not result.isValid() or len(result.Solids)!=1:raise RuntimeError('Invalid result')
 result.exportBrep(str(ROOT/'validation/interfaces'/f'{name}_edge50.brep'))
 checks=[]
 def mismatch(a,b):return a.cut(b,1e-5).Volume+b.cut(a,1e-5).Volume
 # Verify actual unchanged central core and all mounting blocks independently.
 for i,mask in enumerate(masks):
  delta=mismatch(result.common(mask,1e-5),moved.common(mask,1e-5));checks.append({'region':'outer_mount_'+str(i),'difference_mm3':delta,'pass':delta<.02})
 delta=mismatch(result.common(footprint,1e-5),s.common(footprint,1e-5));checks.append({'region':'original_core','difference_mm3':delta,'pass':delta<.02})
 report={'source':name,'valid':result.isValid(),'solids':len(result.Solids),'dimensions_mm':[result.BoundBox.XLength,result.BoundBox.YLength,result.BoundBox.ZLength],'checks':checks,'status':'pass' if all(q['pass'] for q in checks) else 'fail'}
 (ROOT/'validation'/f'{name}_edge50_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
