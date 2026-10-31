"""Measure real part interferences; no claim of fit based on render alone."""
import json
from pathlib import Path
import FreeCAD as A
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'03_assembly/manifest_R06.json').read_text())
d=A.openDocument(str(ROOT/'03_assembly/Lingxi_Cockpit_R06.FCStd'))
parts=[p for p in m['parts'] if p['category']!='hardware']
validation=[]
for p in m['parts']:
    ob=d.getObject(p['id']);s=ob.Shape
    delta=abs(s.Volume-p['volume_mm3'])
    validation.append({'id':p['id'],'valid':s.isValid(),'solids':len(s.Solids),
                       'positive_volume':s.Volume>0,'manifest_volume_difference_mm3':delta,
                       'files_present':all((ROOT/p['folder']/name).exists() for name in
                                            [p['id']+'.FCStd',p['id']+'_review.stl','part.json'])})
all_valid=all(v['valid'] and v['solids']==1 and v['positive_volume']
              and v['manifest_volume_difference_mm3']<=.000501 and v['files_present'] for v in validation)
hits=[]
for i,p in enumerate(parts):
    a=d.getObject(p['id']).Shape
    for q in parts[i+1:]:
        b=d.getObject(q['id']).Shape
        if not a.BoundBox.intersect(b.BoundBox):continue
        volume=a.common(b).Volume
        if volume>.05:hits.append({'parts':[p['id'],q['id']],'overlap_mm3':round(volume,3)})
hits.sort(key=lambda r:r['overlap_mm3'],reverse=True)
result={'status':'PASS' if not hits and all_valid else 'INTERFACES_NEED_REVIEW','rigid_part_interferences':hits,
        'all_saved_parts_valid':all_valid,'saved_part_validation':validation,
        'note':'Hardware omitted. Volumetric overlap does not evaluate minimum wall thickness, assembly paths or physical tolerances.'}
(ROOT/'03_assembly/interference_R06.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
