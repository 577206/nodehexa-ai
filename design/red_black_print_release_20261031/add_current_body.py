"""Add approved EDGE50 body plates to BLACK R02; preserve R01 archive."""
from pathlib import Path
import sys,json,hashlib,zipfile
import numpy as np
import trimesh
from build123d import export_stl
ROOT=Path(__file__).resolve().parent
CAD=ROOT.parent/'nocturne_hexapod'
sys.path.insert(0,str(CAD/'source'))
from edge_frames import edge_top,edge_bottom

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=ROOT/'NodeHexa_BLACK_R01_pending_body.zip'
m=json.loads((ROOT/'BLACK/manifest.json').read_text())
rows=[]
for name,shape,optional in [
 ('N001_BodyTop_EDGE50.stl',edge_top(),False),
 ('N002_BodyBottom_EDGE50_InnerSeatsRemoved.stl',edge_bottom('BodyButtom'),False),
 ('N003_BodyBottom_18650_2S_EDGE50_InnerSeatsRemoved.stl',edge_bottom('BodyButtom-18650-2S'),True)]:
 folder=ROOT/'BLACK'/('optional_not_in_main_count' if optional else 'models')/'QTY_01'
 folder.mkdir(parents=True,exist_ok=True);p=folder/name
 assert shape.is_valid and len(shape.solids())==1
 assert export_stl(shape,p,tolerance=.01,angular_tolerance=.1)
 mesh=trimesh.load(p,force='mesh')
 assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,name
 assert np.allclose(mesh.extents,list(shape.bounding_box().size),atol=.02),name
 assert abs(mesh.volume-shape.volume)/shape.volume<.001,name
 row=dict(color='BLACK',file=str(p.relative_to(ROOT)),quantity=1,sha256=digest(p),dimensions_mm=mesh.extents.tolist(),watertight=bool(mesh.is_watertight),source='nocturne_hexapod/source/edge_frames.py',note='普通下板与18650-2S下板二选一，只打印一个下板' if 'Bottom' in name else '中央开口保持原尺寸，两侧各增宽25 mm',physical_fit_verified=False)
 rows.append(row)
 target=m['optional'] if optional else m['parts']
 target[:]=[r for r in target if r['file']!=row['file']];target.append(row)
m.update(status='body_added_fit_checks_pending',revision='R02',body_source_hashes={str(p.relative_to(CAD)):digest(p) for p in [CAD/'source/edge_frames.py',CAD/'source/build_edge_bottom_freecad.py',CAD/'spec/current.yaml',CAD/'validation/interfaces/BodyButtom_edge50.brep',CAD/'validation/interfaces/BodyButtom-18650-2S_edge50.brep']})
(ROOT/'BLACK/manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
text='''黑色打印件 R02 / 2026-10-31
已加入最新 EDGE50 机身上下板：两侧各加宽25 mm，中央开口原尺寸不变。
两种下板均已移除内侧六个旧座凸起，保留3 mm底板及外侧六个腿座。
上板打印1件；普通下板与18650-2S下板二选一，共打印1件。普通版放主目录仅为清单默认，不代表已确认电池版本。
每种STL只放一份，请按QTY目录数量复制打印。单位毫米。此包使用黑色耗材。
原有红黑分色方案不变；红色压缩包另用原版R01。
原有腿部与侧墙等模型保持原样。本次只更新机身板，整机装配、侧墙与加宽机身匹配、运动干涉及实物适配尚未验证。
Armor_L/R暂按每条腿各1件，即左右各6件；FootGround保留6件。
BodyCenter-Thin为普通BodyCenter的替换备选，不累计打印。
机盖、驾驶舱、底座、螺丝及舵机不在包内。
\n主清单：\n'''
text+='\n'.join(f"{Path(r['file']).name} × {r['quantity']}" for r in m['parts'])
text+='\n主清单共 '+str(sum(r['quantity'] for r in m['parts']))+' 件（含上、下板各1件；备选不累计）。\n\n备选：\n'+'\n'.join(f"{Path(r['file']).name} × {r['quantity']}：{r['note']}" for r in m['optional'])+'\n'
(ROOT/'BLACK/PRINT_README.txt').write_text(text)
archive=ROOT/'NodeHexa_BLACK_R02_EDGE50.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for p in sorted((ROOT/'BLACK').rglob('*')):
  if p.is_file() and not p.name.startswith('.'):z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(archive) as z,zipfile.ZipFile(old) as previous:
 assert z.testzip() is None
 preserved=0
 for n in previous.namelist():
  if n.lower().endswith('.stl'):
   assert z.read(n)==previous.read(n),n;preserved+=1
 for r in rows:assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['sha256']
report={'status':'pass','archive':archive.name,'archive_sha256':digest(archive),'prior_meshes_preserved':preserved,'added_body_parts':rows,'main_print_quantity':sum(r['quantity'] for r in m['parts']),'lower_variants':'choose exactly one','physical_fit_verified':False}
(ROOT/'R02_body_package_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
root_manifest=json.loads((ROOT/'manifest.json').read_text());root_manifest['black_current_archive']=archive.name;root_manifest['status']='body_added_fit_checks_pending';root_manifest['parts']=[r for r in root_manifest['parts'] if r.get('color')!='BLACK']+m['parts'];root_manifest['optional']=m['optional'];root_manifest['pending']=['左右外壳配对及间隙试装','确认普通或18650-2S下板','加宽机身与原侧墙等零件的装配验证'];(ROOT/'manifest.json').write_text(json.dumps(root_manifest,ensure_ascii=False,indent=2))
(ROOT/'README.txt').write_text('当前黑色包：NodeHexa_BLACK_R02_EDGE50.zip\n当前红色包：NodeHexa_RED_R01_pending_body.zip（红色零件未变）\n旧黑色R01保留作历史版本，请使用R02。\n\n'+text)
print(json.dumps(report,ensure_ascii=False,indent=2))
