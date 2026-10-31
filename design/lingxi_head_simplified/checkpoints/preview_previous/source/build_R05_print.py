"""Reproducible R05 first-batch structural-core export, mm. No decorative parts."""
from model import *
import json,hashlib,zipfile,xml.etree.ElementTree as ET
import numpy as np,trimesh,lib3mf

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

p=load_parameters(ROOT/'parameters.yaml')
assembly=build_model(p);parts=list(assembly.children);refs=hardware_references(p)
cache=ROOT/'review/cache';out=ROOT/'outputs/print_R05_batch1';out.mkdir(parents=True,exist_ok=True)
checks={'revision':'R05','status':'fit_print_prototype','physical_fit_verified':False,'parts':[],'intersections':[],'probes':[]}
meshes=[]
for shape in parts:
 assert shape.is_valid and len(shape.solids())==1,shape.label
 export_brep(shape,str(cache/f'R05_{shape.label}.brep'))
 v,t=shape.tessellate(.055,.12)
 mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True)
 mesh.update_faces(mesh.nondegenerate_faces());mesh.remove_unreferenced_vertices();mesh.fix_normals()
 record={'id':shape.label,'valid_solid':True,'solid_count':len(shape.solids()),'watertight':bool(mesh.is_watertight),'positive_closed_volume':bool(mesh.is_volume),'mesh_body_count':len(mesh.split()),'bbox_mm':list(shape.bounding_box().size),'CAD_volume_mm3':shape.volume,'mesh_volume_mm3':mesh.volume,'triangles':len(mesh.faces)}
 checks['parts'].append(record);print(record,flush=True)
 assert mesh.is_watertight and mesh.is_volume and len(mesh.split())==1,record
 meshes.append((shape.label,mesh,COLORS[shape.label],False))

for i,a in enumerate(parts):
 for b in parts[i+1:]+[r for r,c in refs]:
  vv=volume(a.intersect(b));checks['intersections'].append({'a':a.label,'b':b.label,'volume_mm3':vv})
  assert vv<1e-5,(a.label,b.label,vv)

shell,base=parts
for x in [-46,46]:
 for name,z,diam,h in [('access_well',.05,5.18,29.9),('base_shaft',30.01,2.38,3.98)]:
  probe=Pos(x,0,z)*Cylinder(diam/2,h,align=(Align.CENTER,Align.CENTER,Align.MIN));vv=volume(base.intersect(probe))
  checks['probes'].append({'id':name,'x':x,'intersection_mm3':vv});assert vv<1e-5,(name,x,vv)
 probe=Pos(x,0,34.01)*Cylinder(1.19,9.98,align=(Align.CENTER,Align.CENTER,Align.MIN));vv=volume(shell.intersect(probe))
 checks['probes'].append({'id':'shell_shaft','x':x,'intersection_mm3':vv});assert vv<1e-5,('shell_shaft',x,vv)
# Conservative insertion path to provisional board socket on the left side.
usb=box(45,14,9,(-47.5,-15,41.5));vv=volume(shell.intersect(usb))
checks['probes'].append({'id':'left_USB_route_14x9','intersection_mm3':vv});assert vv<1e-5,('USB',vv)
checks['mechanical_dimensions']={'fixed_bowl_mm':[86,86,29],'receiving_mouth_mm':[86.8,86.8],'main_taper_depth_mm':27.4,'guide_depth_mm':29.4,'head_base_hole_spacing_mm':92,'fixed_chassis_bowl_hole_spacing_mm':57.0041368,'base_screw_seat_Z_mm':30,'base_joint_Z_mm':34,'M2_nut_pocket_Z_mm':[37.2,39.2],'USB_window_YxZ_mm':[val(p,'usb_access_width'),val(p,'usb_access_height')],'connector_neck_mm':[17.94,4.4],'connector_solder_relief_mm':[22,8],'nominal_connector_face_gap_mm':.4}
checks['limitations']=['Physical fit and magnetic connector engagement not tested.','OLED/PCB/camera mounting inserts and all exterior ornaments are second-batch parts; their screw patterns must use frozen R05 interfaces.','3MF contains two separate objects in assembly coordinates, no slicing profile.']
checks['pass']=True
dump(ROOT/'validation/R05_checks.json',checks)
dump(ROOT/'validation/mount_interfaces_R05.json',{'revision':'R05','units':'mm','origin':'fixed bowl support plane Z0; camera +Y; right +X','source_sha256':sha(ROOT/'source/model.py'),'interfaces':MOUNT_INTERFACES})
print('CORE CAD and mesh gates passed',flush=True)

for ref,c in refs:
 v,t=ref.tessellate(.15,.25);mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);mesh.fix_normals();meshes.append((ref.label,mesh,c,True))
manifest=json.loads((ROOT/'review/manifest.json').read_text())
manifest['project']['name']='灵犀 R05 · 第一批主体与对接底座'
manifest['versions']['current']={'source':'../source/model.py','step':None}
manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True};manifest['parameters']=[]
manifest['parts']=[{'id':name,'label':LABELS.get(name,name+' / 参照不打印'),'visible':not ref,'color':c[:7],'reference':ref} for name,m,c,ref in meshes]
dump(ROOT/'review/manifest.json',manifest)
provenance={k:sha(ROOT/f) for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
for rev in ['02','03','04']:provenance[f'R{rev}_archive_hash']=sha(ROOT/f'source/model_R{rev}_archive.py')
vertices=[];faces=[]
for name,m,c,ref in meshes:
 start=len(vertices);vertices.extend(m.vertices.tolist())
 for tri in m.faces:
  pts=m.vertices[tri];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=max(np.linalg.norm(n),1e-12)
  faces.append({'indices':[int(i)+start for i in tri],'part_id':name,'feature_id':name,'world_point':pts.mean(0).tolist(),'normal':n.tolist(),'color':c,'reference':ref})
(cache/'current_mesh.json').write_text(json.dumps({'vertices':vertices,'faces':faces,'provenance':provenance}))
(cache/'R05_scene.json').write_text(json.dumps({'objects':[{'name':n,'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'color':c,'reference':r,'part_id':n} for n,m,c,r in meshes]}))
print('R05 scene and review published',flush=True)

exports=[]
for name,m,c,ref in meshes:
 if ref:continue
 flat=m.copy();offset=-float(flat.bounds[0,2]);flat.apply_translation([0,0,offset])
 path=out/f'{name}_R05_1pc_mm.stl';flat.export(path)
 check=trimesh.load(path,force='mesh');assert check.is_watertight and check.is_volume
 exports.append({'file':path.name,'quantity':1,'material_color':'gray','unit':'mm','assembly_to_STL_translation_mm':[0,0,offset],'sha256':sha(path)})

# Core-only 3MF with native base material colors. Assembly placement preserved.
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',C);q=lambda t:'{'+C+'}'+t
root=ET.Element(q('model'),{'unit':'millimeter'})
ET.SubElement(root,q('metadata'),{'name':'Title'}).text='Lingxi R05 - first batch structural core - 2 separate pieces'
ET.SubElement(root,q('metadata'),{'name':'Description'}).text='Fit-print prototype. Assembly coordinates; separate and arrange before slicing. No electronics or decorative parts.'
resources=ET.SubElement(root,q('resources'));materials=ET.SubElement(resources,q('basematerials'),{'id':'1'});ET.SubElement(materials,q('base'),{'name':'GRAY','displaycolor':GRAY})
build=ET.SubElement(root,q('build'))
for i,(name,m,c,ref) in enumerate(meshes[:2]):
 oid=str(i+2);obj=ET.SubElement(resources,q('object'),{'id':oid,'type':'model','name':name,'pid':'1','pindex':'0'});me=ET.SubElement(obj,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in m.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for a,b,c in m.faces:ET.SubElement(ts,q('triangle'),{'v1':str(a),'v2':str(b),'v3':str(c)})
 ET.SubElement(build,q('item'),{'objectid':oid})
path=out/'Lingxi_R05_Batch1_GRAY_2SeparateParts_Assembly.3mf'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
w=lib3mf.get_wrapper();mf=w.CreateModel();reader=mf.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(path));assert reader.GetWarningCount()==0
assert mf.GetMeshObjects().Count()==2 and mf.GetBuildItems().Count()==2
exports.append({'file':path.name,'two_separate_parts':True,'unit':'mm','strict_3mf_warnings':0,'sha256':sha(path)})
dump(out/'PRINT_MANIFEST_R05.json',{'revision':'R05','status':'fit_print_prototype','source_provenance':provenance,'files':exports})
(out/'先读我_第一批打印.txt').write_text('灵犀 R05 第一批：主体壳 + 头部深腔底座，两个分开的零件，各打印1件，灰色。单位毫米，100%比例。\n\n1. H01_MAIN_SHELL：主体外壳。无橙色装甲、无左右风口/圆盖、无手机架/透明面罩；这些第二批另打，用预留孔安装。\n2. H02_DOCK_RECEIVER：装在头内的深腔底座。机器人上固定的86×86×29 mm R02碗底继续沿用，不在本包内。\n3. 主体与深腔底座使用2颗M2×10盘头螺丝＋2颗M2螺母；先从内部侧面放入螺母，再从底面检修井向上拧入。螺母口为4.4mm对边/2mm高。不是锥形沉头。\n4. 3MF保留灰色和装配位置，内有两个独立对象，不含耗材/支撑/机器配置。切片时分开排布；两个STL已各自移至最低Z=0。不要把3MF按装配状态打印为整体。\n5. 保留左侧42×28 mm接线大口；磁吸头颈部17.94×4.4 mm、焊点避让22×8 mm。接头从内部顶部向下插，凸缘止挡，上方焊点空间保持开放。\n6. 碗底完整进入约29.4 mm深的对应腔，按原R02碗模型检查过几何避让。磁吸接触面名义间距0.4 mm，弹簧接点实际压缩/线序/保持力需实物试装；胶只粘塑料侧壁，别盖住触点。\n7. 这是首轮试装打印件；OLED/摄像头/主板安装内托和全部饰件后续另制，孔位以mount_interfaces_R05.json为准。建议先试插接头和试放M2螺母，再最终固定。\n8. 不含切片参数和支撑，悬空面/横向螺母槽在切片中检查支撑可清理性。\n')
for filename in ['mount_interfaces_R05.json','R05_checks.json']:(out/filename).write_bytes((ROOT/'validation'/filename).read_bytes())
zip_path=ROOT/'outputs/Lingxi_R05_Batch1_Core_2Parts.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(out.iterdir()):
  if f.is_file():z.write(f,arcname=f'Lingxi_R05_Batch1/{f.name}')
print('PRINT BUNDLE',zip_path,flush=True)
