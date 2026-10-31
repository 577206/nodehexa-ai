"""R03 color-layout review export: no printer configuration or unmeasured hardware."""
from model import *
import json,hashlib,zipfile,xml.etree.ElementTree as ET
import trimesh,lib3mf
p=load_parameters(ROOT/'parameters.yaml');m=build_model(p);parts=list(m.children)
checks=json.loads((ROOT/'validation/R03_checks.json').read_text())
assert checks['CAD_overlap_pass'] and not checks['reference_conflicts']
assert all(a['joined_solids']==1 for a in checks['physical_groups'].values())
provenance=json.loads((ROOT/'review/cache/current_mesh.json').read_text())['provenance']
for key,f in [('source_hash','source/model.py'),('spec_hash','spec/current.yaml'),('parameters_hash','parameters.yaml')]:assert provenance[key]==hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';M='http://schemas.microsoft.com/3dmanufacturing/material/2015/02'
ET.register_namespace('',C);ET.register_namespace('m',M);q=lambda t:'{'+C+'}'+t
rt=ET.Element(q('model'),{'unit':'millimeter','requiredextensions':'m'})
ET.SubElement(rt,q('metadata'),{'name':'Title'}).text='Lingxi Orange Gray Head R03 - CAD REVIEW PROTOTYPE'
ET.SubElement(rt,q('metadata'),{'name':'Description'}).text='Eight physical parts,16 color regions. Assembly coordinates, not build plate. Electronics reference geometry excluded. No production fit certification.'
res=ET.SubElement(rt,q('resources'));bm=ET.SubElement(res,q('basematerials'),{'id':'1'});cg=ET.SubElement(res,'{'+M+'}colorgroup',{'id':'2'})
colors=[GRAY,DARK,ORANGE,CLEAR]
for name,c in zip(['GRAY_SHELL','DARK_GRAY_LOUVERS','ORANGE_TRIM','CLEAR_VISOR'],colors):ET.SubElement(bm,q('base'),{'name':name,'displaycolor':c});ET.SubElement(cg,'{'+M+'}color',{'color':c})
groups={}
for i,s in enumerate(parts):
 assert s.is_valid and len(s.solids())==1
 v,t=s.tessellate(.07,.14);mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);mesh.fix_normals();assert mesh.is_watertight and mesh.is_volume
 idx=colors.index(COLORS[s.label]);oid=10+i;pid=PART_IDS[s.label];groups.setdefault(pid,[]).append(oid)
 obj=ET.SubElement(res,q('object'),{'id':str(oid),'type':'model','name':s.label,'pid':'1','pindex':str(idx)});me=ET.SubElement(obj,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in mesh.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for f in mesh.faces:ET.SubElement(ts,q('triangle'),{'v1':str(f[0]),'v2':str(f[1]),'v3':str(f[2]),'pid':'2','p1':str(idx),'p2':str(idx),'p3':str(idx)})
build=ET.SubElement(rt,q('build'))
for i,(pid,ids) in enumerate(groups.items()):
 oid=100+i;obj=ET.SubElement(res,q('object'),{'id':str(oid),'type':'model','name':pid+' '+LABELS[pid]});co=ET.SubElement(obj,q('components'))
 for cid in ids:ET.SubElement(co,q('component'),{'objectid':str(cid)})
 ET.SubElement(build,q('item'),{'objectid':str(oid)})
out=ROOT/'outputs/color_prototype';out.mkdir(parents=True,exist_ok=True);path=out/'Lingxi_OrangeGray_R03_REVIEW_ONLY.3mf'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',ET.tostring(rt,encoding='utf-8',xml_declaration=True))
w=lib3mf.get_wrapper();model=w.CreateModel();reader=model.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(path.resolve()));assert reader.GetWarningCount()==0
assert model.GetMeshObjects().Count()==len(parts) and model.GetBuildItems().Count()==len(groups)
report={'file':str(path),'strict_reader_warnings':reader.GetWarningCount(),'material_meshes':len(parts),'physical_parts':len(groups),'references_excluded':True,'status':'review_prototype_not_print_release','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(ROOT/'validation/R03_color_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(out/'R03_审阅说明.txt').write_text('R03橙灰机甲驾驶舱，外形与结构审阅样机；不是打印定稿。\n8个物理零件，每件1个：主体、面罩框、透明面罩、深腔底座、左风口、右风口、手机架、摄像头框。\n主体/风口/手机架的颜色区域合为各自一个物理零件。OLED、手机、电路板、固定碗底和软垫参照不在3MF中。\n该3MF保存颜色和装配位置，需要在切片软件指定实际耗材和摆放，不含打印配置。\n手机带壳宽75mm，支架内宽76mm，用软垫夹持。手机厚度未量，槽深14mm仅为布局尺寸。\n缺少最终OLED安装孔、摄像头及主板固定座，面罩保持方式需试装；磁吸压缩行程和螺丝配合未验证。\nR01/R02旧头部文件保留供回退，以R03审阅为准。\n')
print(json.dumps(report,ensure_ascii=False))
