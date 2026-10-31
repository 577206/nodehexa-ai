"""Reference-derived lower frames: rigid half translation plus center bridges.
BRep references retain STL facets, not recovered nominal analytic CAD surfaces.
"""
from pathlib import Path
from functools import lru_cache
from build123d import import_brep, Box, Pos, Solid, Compound, Color, Shape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

def common(a,b):
    op=BRepAlgoAPI_Common(a.wrapped,b.wrapped)
    op.SetFuzzyValue(1e-5);op.Build()
    return Compound.cast(op.Shape())

ROOT=Path(__file__).resolve().parents[1]

@lru_cache(maxsize=2)
def reference_bottom(name='BodyButtom'):
    return import_brep(ROOT/'validation/interfaces'/f'{name}_reference.brep')

@lru_cache(maxsize=4)
def widened_bottom(name='BodyButtom',increase=30.0):
    ref=reference_bottom(name)
    cy=ref.bounding_box().center().Y
    lo=common(ref,Pos(65,cy-100,4.5)*Box(150,200,20))
    hi=common(ref,Pos(65,cy+100,4.5)*Box(150,200,20))
    bridges=[]
    for face in lo.faces():
        bb=face.bounding_box()
        if bb.size.Y<1e-5 and abs(bb.center().Y-cy)<1e-5:
            bridges.append(Solid.extrude(Pos(0,-increase/2,0)*face,(0,increase,0)))
    if not bridges:raise RuntimeError('No center crossing face')
    lower=Pos(0,-increase/2,0)*lo
    upper=Pos(0,increase/2,0)*hi
    result=lower.fuse(upper,*bridges,tol=1e-5).clean()
    if not result.is_valid or len(result.solids())!=1:raise RuntimeError('Invalid widened bottom')
    result.label='N002_lower_frame_W30_DRAFT' if name=='BodyButtom' else 'N003_lower_frame_18650_2S_W30_ALTERNATIVE_DRAFT'
    result.color=Color(.90,.93,.97)
    return result
