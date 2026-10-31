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
    zones=[('original_3mm_core',Pos(19.75,32.5,1.49999)*Box(45,70,2.99998)),
           ('left_lower_connector',Pos(2.75,30,3)*Box(5.5,12,10)),
           ('right_lower_connector',Pos(36.75,30,3)*Box(5.5,12,10)),
           ('tip_mount',Pos(19.75,3.4,3)*Box(14,6.8,10)),
           ('upper_connector_band',Pos(19.75,60,3)*Box(45,10.4,10))]
    checks=[]
    for name,box in zones:
        delta=mismatch(original_ground & box,ground & box)
        checks.append({'name':name,'symmetric_difference_volume_mm3':delta,'pass':delta<1e-5})
    records=[]
    for part in parts:
        bb=part.bounding_box()
        records.append({'id':part.label,'valid':bool(part.is_valid),'solids':len(part.solids()),
                        'bbox_local_mm':[bb.size.X,bb.size.Y,bb.size.Z],
                        'volume_mm3':part.volume,'physical_fit_verified':False})
    overlap=[]
    for i in range(1,4):
        for j in range(i+1,4):
            v=volume(parts[i] & parts[j])
            overlap.append({'parts':[parts[i].label,parts[j].label],'intersection_mm3':v,'pass':v<1e-5})
    passed=all(r['valid'] and r['solids']==1 for r in records) and all(c['pass'] for c in checks+overlap) and reference_error<0.0001
    report={'status':'pass' if passed else 'fail','scope':'Six CAD solids including two alternative lower frames; not whole-robot validation',
            'footground_reconstruction_relative_volume_error':reference_error,
            'interface_checks':checks,'parts':records,'intersections':overlap,
            'not_verified':['actual servo and leg assembly sweep','printing tolerances and strength','inlay retention','electronics packaging','all remaining body and leg parts'],
            'production_ready':False}
    (ROOT/'validation/first_draft_checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not passed:sys.exit(1)


if __name__=='__main__':main()
