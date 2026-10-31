"""User-requested colored 3MF: R02 layout prototype, no reference electronics."""
from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as ET
import trimesh,lib3mf
from model import *

p=load_parameters(ROOT/'parameters.yaml');m=build_model(p);parts=list(m.children)
meshes=[]
checks={'revision':'R02','state':'layout_prototype_not_production','physical_parts':4,'material_region_meshes':6,'references_excluded':True,'overlaps':[]}
for a in parts:
 assert a.is_valid and len(a.solids())==1,a.label
 v,t=a.tessellate(.1,.18)
 mm=trimesh.Trimesh(vertices=[[q.X,q.Y,q.Z] for q in v],faces=t,process=True);mm.fix_normals()
 assert mm.is_watertight and mm.is_volume,a.label
 meshes.append(mm)
for i,a in enumerate(parts):
 for b in parts[i+1:]:
  rr=a.intersect(b);vv=(sum(q.volume for q in rr) if isinstance(rr,ShapeList) else rr.volume) if rr else 0
  checks['overlaps'].append({'a':a.label,'b':b.label,'mm3':vv});assert vv<1e-5,(a.label,b.label,vv)
bowl=Pos(0,0,-27.2)*import_brep(ROOT.parent/'lingxi_magnetic_bowl_mount/review/cache/hood_R01.brep')
rr=parts[-1].intersect(bowl);vv=(sum(q.volume for q in rr) if isinstance(rr,ShapeList) else rr.volume) if rr else 0
checks['fixed_bowl_base_intersection_mm3']=vv;assert vv<1e-5,vv
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';M='http://schemas.microsoft.com/3dmanufacturing/material/2015/02'
ET.register_namespace('',C);ET.register_namespace('m',M);q=lambda t:'{'+C+'}'+t
rt=ET.Element(q('model'),{'unit':'millimeter','requiredextensions':'m'})
ET.SubElement(rt,q('metadata'),{'name':'Title'}).text='Lingxi OLED Mecha Head R02 - LAYOUT PROTOTYPE'
ET.SubElement(rt,q('metadata'),{'name':'Description'}).text='Four physical parts. No OLED references or unmeasured final mounting bracket. Assign actual filaments in slicer. Not production fit verified.'
res=ET.SubElement(rt,q('resources'));bm=ET.SubElement(res,q('basematerials'),{'id':'1'});cg=ET.SubElement(res,'{'+M+'}colorgroup',{'id':'2'})
for n,c in [('ORANGE_BODY_BASE','#F27619FF'),('YELLOW_BODY_REGIONS_AND_FRAME','#FFD329FF'),('CLEAR_CANOPY','#C5E5EE30')]:
 ET.SubElement(bm,q('base'),{'name':n,'displaycolor':c});ET.SubElement(cg,'{'+M+'}color',{'color':c})
ids=[]
for i,(a,mm) in enumerate(zip(parts,meshes)):
 oid=10+i;ids.append(oid);idx=1 if 'YELLOW' in a.label else 2 if 'CLEAR' in a.label else 0
 obj=ET.SubElement(res,q('object'),{'id':str(oid),'type':'model','name':a.label,'pid':'1','pindex':str(idx)})
 me=ET.SubElement(obj,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in mm.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for f in mm.faces:ET.SubElement(ts,q('triangle'),{'v1':str(f[0]),'v2':str(f[1]),'v3':str(f[2]),'pid':'2','p1':str(idx),'p2':str(idx),'p3':str(idx)})
body=ET.SubElement(res,q('object'),{'id':'100','type':'model','name':'P01_ORANGE_YELLOW_BODY_CO_PRINT_ONE_PIECE'});com=ET.SubElement(body,q('components'))
for oid in ids[:3]:ET.SubElement(com,q('component'),{'objectid':str(oid)})
bu=ET.SubElement(rt,q('build'))
for oid in [100]+ids[3:]:ET.SubElement(bu,q('item'),{'objectid':str(oid)})
out=ROOT/'outputs/color_prototype';out.mkdir(exist_ok=True,parents=True);path=out/'Lingxi_OLED_Head_R02_LAYOUT_PROTOTYPE.3mf'
ct='''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
rels='''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml',ct);z.writestr('_rels/.rels',rels);z.writestr('3D/3dmodel.model',ET.tostring(rt,encoding='utf-8',xml_declaration=True))
w=lib3mf.get_wrapper();mm=w.CreateModel();rd=mm.QueryReader('3mf');rd.SetStrictModeActive(True);rd.ReadFromFile(str(path.resolve()))
assert rd.GetWarningCount()==0
assert mm.GetMeshObjects().Count()==6 and mm.GetBuildItems().Count()==4 and mm.GetColorGroups().Count()==1
checks['strict_lib3mf']={'warnings':0,'meshes':6,'build_items':4,'color_groups':1};checks['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
checks['limitations']=['OLED PCB envelope approximate; pin-inclusive thickness, active display and hole centers unmeasured','OLED carrier/mask not finalized, references excluded','Camera mount, other electronics and battery packaging not finalized','Base screws and removable canopy retention require physical verification','Magnetic connector axial compression and pull strength not verified','Assembled coordinates, not arranged build plate; no printer settings','Clear color is visualization, not assurance of optical transparency']
(ROOT/'validation/R02_color_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
(out/'READ_ME_先看这里.txt').write_text('''当前版本：R02 橙黄OLED机甲头部，布局样机。R01已被替代。\n共4个物理打印零件：橙黄双色主体1、黄色面罩护框1、透明折面罩1、橙色底板1。主体有3个材料区域，共印成一个主体。\n3MF含命名材料与颜色，导入切片软件后要指定实际耗材。当前为装配坐标，不是排盘，不能直接按当前姿态开打。\nOLED蓝板、显示区、像素图案和临时遮边框均为参照，未混入打印文件。实际OLED支架与遮边框开口待量尺寸后完善。\n四个零件和原碗底的几何关系经过CAD检查，实际螺丝保持、面罩保持、触点压缩、磁吸力和全部电子件包装尚未验证。\n透明显示色不代表打印后能光学透明。此文件仅用于外形审阅和试样，不是整套可生产成品。\n''')
print(json.dumps({'file':str(path),'strict_readback':checks['strict_lib3mf'],'bowl_overlap_mm3':vv},ensure_ascii=False))
