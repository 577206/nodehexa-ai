"""Geometry evidence for the partial engineering draft; not physical approval."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from build123d import Box,Pos
from model import *


def volume(s):
    return abs(float(s.volume)) if s is not None else 0.0


def mismatch(a,b):
    return volume(a-b)+volume(b-a)


def main():
    params=load_parameters(ROOT/'parameters.yaml')
    parts=local_parts(params)
    original_ground=reference_ground()
    gp=profile('FootGround')
    reference_error=abs(original_ground.volume-gp['mesh_volume_mm3'])/gp['mesh_volume_mm3']
    ground=parts[1]
    zones=[('lower_joint_and_tip_band',Pos(19.75,17.5,3)*Box(45,35,10)),
           ('upper_connector_band',Pos(19.75,60,3)*Box(45,10.4,10))]
    checks=[]
    for name,box in zones:
        delta=mismatch(original_ground & box,ground & box)
        checks.append({'name':name,'symmetric_difference_volume_mm3':delta,'pass':delta<1e-5})
    top_ref=plate(profile('BodyTop')['loops_uv_mm'],3)
    top=parts[0]
    center=top_ref.bounding_box().center().Y
    shift=value(params,'body_width_increase')/2
    for sign in [-1,1]:
        mask=Pos(67.5,center+sign*125,1.5)*Box(150,250,5)
        old=top_ref & mask
        transformed=Pos(0,sign*shift,0)*old
        shifted_mask=Pos(0,sign*shift,0)*mask
        delta=mismatch(transformed,top & shifted_mask)
        checks.append({'name':f'upper_frame_original_half_{sign}_rigid_translation',
                       'symmetric_difference_volume_mm3':delta,'pass':delta<1e-4})
    records=[]
    for part in parts:
        bb=part.bounding_box()
        records.append({'id':part.label,'valid':bool(part.is_valid),'solids':len(part.solids()),
                        'bbox_local_mm':[bb.size.X,bb.size.Y,bb.size.Z],
                        'volume_mm3':part.volume,'physical_fit_verified':False})
    overlap=[]
    for i in range(1,len(parts)):
        for j in range(i+1,len(parts)):
            v=volume(parts[i] & parts[j])
            overlap.append({'parts':[parts[i].label,parts[j].label],'intersection_mm3':v,'pass':v<1e-5})
    passed=all(r['valid'] and r['solids']==1 for r in records) and all(c['pass'] for c in checks+overlap) and reference_error<0.0001
    report={'status':'pass' if passed else 'fail','scope':'Four CAD solids only; not whole-robot validation',
            'footground_reconstruction_relative_volume_error':reference_error,
            'interface_checks':checks,'parts':records,'intersections':overlap,
            'not_verified':['actual servo and leg assembly sweep','printing tolerances and strength','inlay retention','electronics packaging','all remaining body and leg parts'],
            'production_ready':False}
    (ROOT/'validation/first_draft_checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not passed:sys.exit(1)


if __name__=='__main__':main()
