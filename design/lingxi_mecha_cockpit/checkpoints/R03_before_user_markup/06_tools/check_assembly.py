"""Measure real part interferences; no claim of fit based on render alone."""
import json
from pathlib import Path
import FreeCAD as A
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'03_assembly/manifest.json').read_text())
d=A.openDocument(str(ROOT/'03_assembly/Lingxi_Cockpit_R03.FCStd'))
parts=[p for p in m['parts'] if p['category']!='hardware']
hits=[]
for i,p in enumerate(parts):
    a=d.getObject(p['id']).Shape
    for q in parts[i+1:]:
        b=d.getObject(q['id']).Shape
        if not a.BoundBox.intersect(b.BoundBox):continue
        volume=a.common(b).Volume
        if volume>.05:hits.append({'parts':[p['id'],q['id']],'overlap_mm3':round(volume,3)})
hits.sort(key=lambda r:r['overlap_mm3'],reverse=True)
result={'status':'PASS' if not hits else 'INTERFACES_NEED_REVIEW','rigid_part_interferences':hits,
        'note':'Hardware omitted. Volumetric overlap does not evaluate minimum wall thickness, assembly paths or physical tolerances.'}
(ROOT/'03_assembly/interference_report.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
