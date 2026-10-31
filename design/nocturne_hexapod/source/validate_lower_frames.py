import json
from lower_frame import *
from model import load_parameters,value

def vol(s):return abs(s.volume) if s else 0
records=[]
shift=value(load_parameters(ROOT/'parameters.yaml'),'body_width_increase')/2
for name in ['BodyButtom','BodyButtom-18650-2S']:
    old=reference_bottom(name);new=widened_bottom(name,shift*2)
    cy=old.bounding_box().center().Y;checks=[]
    for sign in [-1,1]:
        # Keep comparison 0.01 mm clear of the artificial split face.
        mask=Pos(65,cy+sign*100.01,4.5)*Box(150,200,20)
        ref_half=common(old,mask)
        moved_mask=Pos(0,sign*shift,0)*mask
        new_half=common(new,moved_mask)
        expected=Pos(0,sign*shift,0)*ref_half
        intersection=common(expected,new_half)
        delta=abs(vol(expected)+vol(new_half)-2*vol(intersection))
        checks.append(dict(side=sign,comparison='original half versus translated redesigned half, entire thickness',symmetric_difference_volume_mm3=delta,pass_check=delta<.02))
    bb=new.bounding_box().size
    sizes=[bb.X,bb.Y,bb.Z];target=[130.34313965,108.34314823,9]
    record=dict(id=new.label,valid=new.is_valid,solids=len(new.solids()),dimensions_mm=sizes,target_mm=target,dimension_pass=max(abs(a-b) for a,b in zip(sizes,target))<.001,interface_checks=checks,physical_fit_verified=False)
    record['pass']=record['valid'] and record['solids']==1 and record['dimension_pass'] and all(c['pass_check'] for c in checks)
    records.append(record)
report=dict(status='pass' if all(r['pass'] for r in records) else 'fail',width_increase_mm=shift*2,parts=records,method='unchanged rigid-translated original faceted reference regions; tolerance 0.02 mm3 Boolean comparison; excludes 0.01 mm next to center bridge',not_verified=['upper/lower full assembled alignment','mating walls and center plates','physical fit and strength'],alternatives_not_simultaneous=True)
(ROOT/'validation/lower_frame_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
assert report['status']=='pass'
