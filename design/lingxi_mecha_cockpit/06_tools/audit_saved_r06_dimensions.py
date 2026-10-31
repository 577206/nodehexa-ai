"""Read saved R06 without regenerating geometry. Run using FreeCAD Python."""
import FreeCAD as A
import json, hashlib
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'03_assembly/Lingxi_Cockpit_R06.FCStd'
m = json.loads((ROOT/'03_assembly/manifest_R06.json').read_text())
doc = A.openDocument(str(source))
parts=[]
for p in m['parts']:
    s=doc.getObject(p['id']).Shape
    b=s.optimalBoundingBox()
    size=[b.XLength,b.YLength,b.ZLength]
    parts.append(dict(id=p['id'], title=p['title'], category=p['category'], group=p['group'], material=p['material'], valid=s.isValid(), solids=len(s.Solids), volume_mm3=s.Volume, size_mm=size, bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax], previous_size_mm=p['size_mm'], volume_matches_saved_manifest=abs(s.Volume-p['volume_mm3'])<.001))
def envelope(ps):
    b=A.BoundBox()
    for p in ps:b.add(doc.getObject(p['id']).Shape.optimalBoundingBox())
    return dict(size_mm=[b.XLength,b.YLength,b.ZLength], bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax])
phone={'P45','P46','P47','P48','P64','P65'}
report=dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),units='mm',method='OCCT optimalBoundingBox on saved solids; ordinary BoundBox may overestimate B-spline geometry',geometry_modified=False,status='inspection_only_not_print_release',counts=dict(Counter(p['category'] for p in parts)),all=envelope(parts),head_excluding_phone_and_desktop_base=envelope([p for p in parts if p['group']!='desktop_base' and p['id'] not in phone]),main_shell=envelope([p for p in parts if p['id'] in {'P01','P02'}]),parts=parts)
out=ROOT/'04_review/inspection_20261030/dimension_audit.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='parts'},ensure_ascii=False),flush=True)
print('valid_single_solids',sum(p['valid'] and p['solids']==1 for p in parts),'of',len(parts),flush=True)
print('inflated_dimension_entries',sum(any(abs(a-b)>.1 for a,b in zip(p['size_mm'],p['previous_size_mm'])) for p in parts),flush=True)
