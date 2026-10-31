import json,numpy as np
from edge_frames import *
from model import plate,profile

def volume(s):return abs(s.volume) if s else 0

def difference(a,b):return abs(volume(a)+volume(b)-2*volume(common(a,b)))
records=[]
top=edge_top();d=profile('BodyTop');ref=plate(d['loops_uv_mm'],3);checks=[]
for i,loop in enumerate(d['loops_uv_mm'][1:],1):
 shift=0 if i in (1,5,11) else (25 if np.mean(np.array(loop)[:,1])>37.17157 else -25)
 tool=Pos(0,shift,0)*prism(loop)
 v=volume(common(top,tool));checks.append({'feature':'central_aperture' if i==1 else f'hole_{i}','shift_mm':shift,'blocked_volume_mm3':v,'pass':v<.001})
# At fixed central cover holes, preserve the original hole and full local plate thickness.
for i in [5,11]:
 q=np.array(d['loops_uv_mm'][i]);x,y=(q.min(0)+q.max(0))/2;mask=Pos(x,y,1.5)*Box(4,4,4)
 delta=difference(common(ref,mask),common(top,mask));checks.append({'feature':f'fixed_mount_region_{i}','difference_mm3':delta,'pass':delta<.001})
records.append({'id':top.label,'valid':top.is_valid,'solids':len(top.solids()),'dimensions_mm':list(top.bounding_box().size),'checks':checks})
for name in ['BodyButtom','BodyButtom-18650-2S']:
 new=edge_bottom(name)
 report=json.loads((ROOT/'validation'/f'{name}_edge50_checks.json').read_text())
 records.append({'id':new.label,'valid':new.is_valid,'solids':len(new.solids()),'dimensions_mm':list(new.bounding_box().size),'checks':report['checks']})
passed=all(p['valid'] and p['solids']==1 and all(c['pass'] for c in p['checks']) for p in records)
r={'status':'pass' if passed else 'fail','parts':records,'notes':['Lower original internal mount features retained unused; outward translated mounts used for legs.','No full servo sweep or physical fit test.','Lower frame variants are alternatives.']}
(ROOT/'validation/edge_frame_checks.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2),flush=True)
assert passed
