"""Explicit user-requested 3MF prototype export, not default STEP/CAD delivery.
Writes semantic material names, fallback display colors AND per-triangle material-
properties color groups. No printer-specific filament assignment or print plate.
"""
from pathlib import Path
import os,json,hashlib,zipfile,xml.etree.ElementTree as ET,sys
import numpy as np,trimesh
from model import *
from build123d import import_brep,Pos
os.environ['MPLCONFIGDIR']=str(ROOT/'review/cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
sys.path.insert(0,str(ROOT.parent/'lingxi_magnetic_bowl_mount/source'))
from raster_review import raster

params=load_parameters(ROOT/'parameters.yaml');model=build_model(params);parts=list(model.children)
for part in parts:assert part.is_valid and len(part.solids())==1,(part.label,part.is_valid,len(part.solids()))
meshes=[]
for part in parts:
 vv,tt=part.tessellate(.10,.18)
 mesh=trimesh.Trimesh(vertices=[[v.X,v.Y,v.Z] for v in vv],faces=tt,process=True)
 mesh.fix_normals();assert mesh.is_watertight and mesh.is_volume,part.label
 meshes.append(mesh)
checks={'valid_solids':len(parts),'closed_volume_meshes':len(meshes),'part_counts':{'orange_yellow_co_print_shell':1,'orange_base':1,'clear_visor':1},'color_region_meshes':len(parts),'color_names':['ORANGE','YELLOW','CLEAR'],'overlaps':[],'limitations':['STRUCTURE PROTOTYPE, not a production print release','Camera port, electronics standoffs, battery, speaker layout not designed','Visor backing seat modeled; final sliding retention / clips not validated','Screw positions and dimensions are draft; final nut/thread retention unverified','Magnetic pair exact axial compression, adhesive and holding strength not physically verified','3MF is assembled positions, not a sliced or arranged build plate','Transparent display color does not guarantee optically clear printed material']}
for i,a in enumerate(parts):
 for b in parts[i+1:]:
  r=a.intersect(b);vol=r.volume if r else 0
  checks['overlaps'].append({'a':a.label,'b':b.label,'mm3':float(vol)})
assert max(c['mm3'] for c in checks['overlaps'])<1e-5,checks['overlaps']
# Independently compare head base with existing actual bowl geometry at dock pose.
ref=ROOT.parent/'lingxi_magnetic_bowl_mount/review/cache/hood_R01.brep'
bowl=Pos(0,0,-27.2)*import_brep(ref)
r=parts[3].intersect(bowl);vol=r.volume if r else 0
checks['bowl_base_overlap_mm3']=float(vol)
assert vol<1e-5,vol

CORE='http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
MAT='http://schemas.microsoft.com/3dmanufacturing/material/2015/02'
ET.register_namespace('',CORE);ET.register_namespace('m',MAT)
q=lambda n:'{'+CORE+'}'+n
root=ET.Element(q('model'),{'unit':'millimeter','{http://www.w3.org/XML/1998/namespace}lang':'en-US','requiredextensions':'m'})
for name,text in [('Title','Lingxi Simplified Orange Yellow Head R01 - STRUCTURE PROTOTYPE'),('Application','build123d parametric prototype'),('Description','Orange/yellow co-print shell, orange base, separate clear visor. Not a final physical-fit release. Material assignment must be checked in slicer.')]:ET.SubElement(root,q('metadata'),{'name':name}).text=text
res=ET.SubElement(root,q('resources'));bases=ET.SubElement(res,q('basematerials'),{'id':'1'})
colors=['#F27619FF','#FFD329FF','#B6E3F280'];names=['ORANGE_SHELL_AND_BASE','YELLOW_CO_PRINT_REGIONS','CLEAR_VISOR_SEPARATE_PART']
for n,c in zip(names,colors):ET.SubElement(bases,q('base'),{'name':n,'displaycolor':c})
group=ET.SubElement(res,'{'+MAT+'}colorgroup',{'id':'2'})
for c in colors:ET.SubElement(group,'{'+MAT+'}color',{'color':c})
part_ids=[]
for i,(part,mesh) in enumerate(zip(parts,meshes)):
 oid=10+i;part_ids.append(oid);idx=1 if 'YELLOW' in part.label else 2 if 'CLEAR' in part.label else 0
 ob=ET.SubElement(res,q('object'),{'id':str(oid),'type':'model','name':part.label,'partnumber':part.label,'pid':'1','pindex':str(idx)})
 me=ET.SubElement(ob,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in mesh.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for f in mesh.faces:ET.SubElement(ts,q('triangle'),{'v1':str(f[0]),'v2':str(f[1]),'v3':str(f[2]),'pid':'2','p1':str(idx),'p2':str(idx),'p3':str(idx)})
# Keep main shell's three color-volume meshes grouped as ONE physical print object.
shell=ET.SubElement(res,q('object'),{'id':'100','type':'model','name':'P01_ORANGE_YELLOW_CO_PRINT_SHELL'})
comp=ET.SubElement(shell,q('components'))
for oid in part_ids[:3]:ET.SubElement(comp,q('component'),{'objectid':str(oid)})
build=ET.SubElement(root,q('build'))
for oid in [100,part_ids[3],part_ids[4]]:ET.SubElement(build,q('item'),{'objectid':str(oid)})
ctype=b'''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>'''
rels=b'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'''
out=ROOT/'outputs/color_prototype';out.mkdir(parents=True,exist_ok=True)
file=out/'Lingxi_Head_Simplified_R01_COLOR_PROTOTYPE.3mf'
with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml',ctype);z.writestr('_rels/.rels',rels)
 z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(file) as z:
 assert z.testzip() is None
 rt=ET.fromstring(z.read('3D/3dmodel.model'));assert rt.get('unit')=='millimeter'
 assert len(rt.findall('.//'+q('object')))==6
 assert len(rt.findall('.//{'+MAT+'}color'))==3
 assert len(rt.find(q('build')))==3
 for obj in rt.findall('.//'+q('object')):
  mm=obj.find(q('mesh'))
  if mm is None:continue
  nv=len(mm.find(q('vertices')))
  for tr in mm.find(q('triangles')):assert all(0<=int(tr.get(k))<nv for k in ['v1','v2','v3'])
checks['3mf_package']={'crc_pass':True,'model_objects':6,'physical_build_items':3,'color_properties':3,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'slicer_round_trip':'not verified in actual user slicer'}
# Independent official-lib3mf strict parser: validate colors, build items and meshes.
import lib3mf
wrapper=lib3mf.get_wrapper();loaded=wrapper.CreateModel();reader=loaded.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(file.resolve()))
assert loaded.GetMeshObjects().Count()==5
assert loaded.GetBuildItems().Count()==3
assert loaded.GetColorGroups().Count()==1
assert reader.GetWarningCount()==0
checks['official_lib3mf_strict_readback']={'mesh_objects':5,'build_items':3,'color_groups':1,'base_material_groups':loaded.GetBaseMaterialGroups().Count(),'warning_count':reader.GetWarningCount()}
(ROOT/'validation/color_prototype_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')

# Standard review template with actual source-derived colors.
manifest=json.loads((ROOT/'review/manifest.json').read_text());manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True}
manifest['parts']=[{'id':p.label,'label':p.label,'visible':True,'color':COLORS[p.label][:7]} for p in parts];manifest['parameters']=[]
(ROOT/'review/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
verts=[];faces=[]
for p,mesh in zip(parts,meshes):
 start=len(verts);verts.extend(mesh.vertices.tolist())
 for tri in mesh.faces:
  xyz=mesh.vertices[tri];n=np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]);n/=max(np.linalg.norm(n),1e-12)
  faces.append({'indices':[int(v)+start for v in tri],'part_id':p.label,'feature_id':p.label,'world_point':xyz.mean(0).tolist(),'normal':n.tolist(),'color':COLORS[p.label][:7]})
provenance={k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
(ROOT/'review/cache/current_mesh.json').write_text(json.dumps({'vertices':verts,'faces':faces,'provenance':provenance}))

# Actual CAD image; separate the three physical print pieces for inspection.
plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
# Per-face CAD colors are passed into the depth-buffer renderer.
from color_raster import raster_colored
fig,axs=plt.subplots(1,2,figsize=(15,8.5),facecolor='#eef2f5');fig.subplots_adjust(top=.79,bottom=.17,wspace=.08)
for ax,exploded in zip(axs,[False,True]):
 vv=[];tt=[];cc=[]
 for p,m in zip(parts,meshes):
  v=m.vertices.copy()
  if exploded:
   if 'BASE' in p.label:v[:,2]-=30
   elif 'VISOR' in p.label:v[:,1]+=33
   else:v[:,2]+=12
  start=len(vv);vv.extend(v);tt.extend(m.faces+start)
  color=COLORS[p.label];cc.extend([[int(color[i:i+2],16) for i in [1,3,5]]]*len(m.faces))
 ax.imshow(raster_colored(np.array(vv),np.array(tt),np.array(cc),30,55,width=1100,height=820));ax.axis('off')
 ax.set_title('实际CAD装配 / 橙黄材料区域' if not exploded else '三件拆分 / 面罩固定细节待完善',fontsize=14,color='#203447')
fig.text(.05,.93,'简化驾驶舱 R01  /  彩色3MF结构样机',fontsize=24,color='#203447')
fig.text(.05,.865,'罩壳（双色打印）＋底板＋透明面罩；黄色区域不增加螺丝。仅保留两处主体与底板固定点。',fontsize=12,color='#4d6477')
fig.text(.05,.09,'样机外形约104 ×136 ×81 mm；底部凹槽对应既有碗底。未设计最终电池、扬声器、摄像头支座。',fontsize=11,color='#4d6477')
fig.text(.05,.045,'结构样机，尚非可直接整套开打的成品；透明面罩的固定、螺丝接收端及磁吸接插件需要继续试配。',fontsize=11,color='#ad3444')
draw=ROOT/'outputs/drawings';draw.mkdir(parents=True,exist_ok=True);fig.savefig(draw/'simplified_head_actual_CAD_R01.png',dpi=150)
(out/'READ_ME_先看这里.txt').write_text('''橙黄简化驾驶舱 R01 / STRUCTURE PROTOTYPE
文件是真实CAD派生的3MF网格，不是图片。
物理零件：双色主体1件、橙色底板1件、透明面罩1件。主体由橙色和两块黄色材料区域共印成一件。
3MF包含对象名称、基础材料名称、显示颜色及每三角面的材料扩展颜色属性。请在切片软件逐项核对并指定实际耗材；没有打印机专属配置、切片或排盘。
文件按装配坐标保存，不可直接以当前排列开打。
透明显示色不代表打印后可光学透明。透明罩单独选料和处理。
此版为外观和对接结构样机：电池、扬声器、摄像头固定、面罩最终保持结构、螺丝接收端未完成验证。主体只留两个底板连接位置，不能按现阶段孔位认定已能牢固装配。
原固定碗底未包含在本头部3MF中，避免重复打印。
当前颜色：橙#F27619、黄#FFD329、透明罩单独标识。几何单位mm。
''')
print(json.dumps({'file':str(file),'size_bytes':file.stat().st_size,'valid_solids':len(parts),'physical_parts':3,'color_properties':3,'overlap_max_mm3':max(c['mm3'] for c in checks['overlaps']),'bowl_overlap_mm3':vol},ensure_ascii=False))
