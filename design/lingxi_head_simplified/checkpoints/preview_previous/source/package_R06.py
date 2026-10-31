"""Finalize verified second batch with clear part counts and assembly instructions."""
from pathlib import Path
import json,zipfile,hashlib,shutil,re,collections
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'outputs/print_R06_batch2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
m=json.loads((out/'PRINT_MANIFEST_R06.json').read_text());qa=json.loads((ROOT/'validation/R06_blender_qa.json').read_text())
assert qa['asset']['pass'];assert all(x['pass'] for x in qa['individual_print_mesh_checks'].values())
assert qa['visual_review_status'].startswith('REVIEWED'), 'Inspect actual renders before packaging'
assert json.loads((ROOT/'validation/R06_checks.json').read_text())['pass']
service=json.loads((ROOT/'validation/service_R06_checks.json').read_text())
# A failure cannot be silently shipped as a successful check.
assert service.get('pass',False),service
files=[f for f in m['files'] if f['file'].endswith('.stl')];assert len(files)==16
for f in m['files']:assert sha(out/f['file'])==f['sha256']
counts=collections.Counter();colorcounts=collections.Counter()
for group in m['fasteners']:
 size=re.search(r'M2x\d+',group['screw']).group();counts[size]+=group['quantity']
for f in files:colorcounts[f['color']]+=f['quantity']
lines=['灵犀 R06 第二批：橙灰装饰配件','单位：毫米。各STL按100%比例，每种1件，共16件。','',f"橙色{colorcounts['ORANGE']}件，灰色{colorcounts['GRAY']}件。第一批主体、底座、透明盖、压框不在此包，不要重复打印。",'','打印清单：']
for f in sorted(files,key=lambda x:x['file']):lines.append(f"{f['file']}  ×1  {f['label']}")
lines += ['','新增五金清单（本批，不含上一批）：']
for size,num in sorted(counts.items(),key=lambda x:int(x[0][3:])):lines.append(f'{size} 盘头螺丝 ×{num}')
lines += [f'M2六角螺母 ×{sum(counts.values())}（按对边4.0mm、厚1.6mm校核；实物尺寸仍需试配）。','手机接触边另贴薄软垫。通风口螺丝头直径须不大于4.4mm。','',
'装配顺序：',
'1. 先拆下头部深腔底座H02，预留内部扶住M2螺母的空间；内部电子尚未安装时装饰螺母最容易操作。',
'2. 通风口每侧先灰百叶、后橙外框，共用上下两颗螺丝，上孔M2×25，下孔M2×20。百叶不要粘死。',
'3. 肩甲每侧橙甲在内、灰压条在外，共用两颗M2×16；圆盖每侧橙杯＋灰盖，共用一颗M2×16。圆盖上方止转舌片先插入肩甲配合槽，再共同装到主体。',
'4. 必须清理原主体的两处后肩孔（Y=-27/Z=97）：用Ø2.4mm钻头手动去除孔末端约0.034mm薄边，保持原孔轴线，不要扩大到M3。这是冻结主体已有的薄膜，未改第一批STL。',
'5. 摄像头橙色框使用2颗M2×12，先从内侧安螺母。Ø16开口仅是外框，摄像头实际固定支架尚未包含。',
'6. 手机架先用4颗M2×12装好左右橙夹，再用2颗M2×12连接背托和主体。手机从上方滑入，螺丝头藏入凹位。净宽76mm对应带壳75mm；净厚13mm，对应带壳厚10–12mm，软垫厚度按手机实物调整，不要硬挤。',
'7. 检查左侧Type-C插线通道和面罩拆卸通道后，再装H02底座。紧固到贴合即可；0.2mm左右设计间隙与打印误差需要实际试配。','',
'文件说明：',
'01_ORANGE与02_GRAY按材料分开。STL没有颜色；3MF带两种颜色与16个独立对象，位置为装配坐标，切片时必须分开排布，不要合并成整体打印。没有打印机、耗材、支撑或G-code配置。',
'实际模型渲染中的4件第一批主体是装配参照，不属于本批16件。透明效果、螺母安装及手机承重仍需实物试装；数字网格/配合检查不等于实际强度验证。',
'侧面圆盖的防转舌槽是功能结构，不要切掉；不需要用胶把可拆装饰件固定死。','']
(out/'先读我_第二批打印和装配.txt').write_text('\n'.join(lines))
m['hardware_summary']=dict(counts);m['hardware_summary']['M2_nut']=sum(counts.values());m['print_counts']={'total':16,**dict(colorcounts)};m['fit_limitations']=['Existing rear shoulder bores need manual diameter2.4mm membrane cleanup; original core unchanged.','Cased-phone thickness10–12mm;13mm slot and soft pads, physical fit required.','Digital prototype; actual strength, phone retention and electrical integration not tested.'];dump(out/'PRINT_MANIFEST_R06.json',m)
for f in ['R06_blender_qa.json','service_R06_checks.json','armor_R06_checks.json','phone_R06_checks.json','vent_R06_checks.json','camera_R06_checks.json']:
 shutil.copy2(ROOT/'validation'/f,out/f)
for f in ['R06_hero.png','R06_left.png','R06_rear.png']:
 shutil.copy2(ROOT/'outputs/renders/R06'/f,out/f)
dump(out/'SHA256SUMS.json',{str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file() and f.name!='SHA256SUMS.json'})
zp=ROOT/'outputs/Lingxi_R06_Batch2_OrangeGray_16Parts.zip'
with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(out.rglob('*')):
  if f.is_file():z.write(f,'Lingxi_R06_Batch2/'+str(f.relative_to(out)))
with zipfile.ZipFile(zp) as z:assert z.testzip() is None;assert len([n for n in z.namelist() if n.endswith('.stl')])==16
print(json.dumps({'zip':str(zp),'bytes':zp.stat().st_size,'color_counts':dict(colorcounts),'hardware':dict(counts),'nut_count':sum(counts.values())},ensure_ascii=False))
