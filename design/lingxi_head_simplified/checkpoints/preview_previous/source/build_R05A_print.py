"""Reproducible R05A first-batch structural-core export, mm. Four separate parts, including clear cover and retainer."""
from model import *
import json,hashlib,zipfile,xml.etree.ElementTree as ET
import numpy as np,trimesh,lib3mf

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

p=load_parameters(ROOT/'parameters.yaml')
assembly=build_model(p);parts=list(assembly.children);refs=hardware_references(p)
cache=ROOT/'review/cache';out=ROOT/'outputs/print_R05A_batch1';out.mkdir(parents=True,exist_ok=True)
checks={'revision':'R05A','status':'fit_print_prototype','physical_fit_verified':False,'parts':[],'intersections':[],'probes':[]}
meshes=[]
for shape in parts:
 assert shape.is_valid and len(shape.solids())==1,shape.label
 export_brep(shape,str(cache/f'R05A_{shape.label}.brep'))
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

shell,base=parts[:2]
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
checks['limitations']=['Physical fit and magnetic connector engagement not tested.','OLED/PCB/camera mounting inserts and other exterior ornaments are second-batch parts; their screw patterns must use frozen R05A interfaces.','3MF contains four separate objects in assembly coordinates, no slicing profile.']
checks['unchanged_core']=[]
for shape in parts[:2]:
 old_shape=import_brep(str(cache/f'R05_{shape.label}.brep'))
 delta=volume(shape-old_shape)+volume(old_shape-shape)
 checks['unchanged_core'].append({'id':shape.label,'symmetric_difference_mm3':delta})
 assert delta<1e-5,(shape.label,delta)
checks['visor_retention']={'lower_screws':'2 x M2x20 pan head + 2 x M2 nuts','lower_axes_mm':[[-31,37],[31,37]],'upper_guides':'2 integral diameter2mm pins into existing diameter2.4mm blind holes','upper_axes_mm':[[-23,108.6],[23,108.6]],'visor_shift_Y_mm':5.5,'assembly':'Clear visor and frame are detachable toward +Y after removing lower2 screws.'}
checks['pass']=True
dump(ROOT/'validation/R05A_checks.json',checks)
dump(ROOT/'validation/mount_interfaces_R05A.json',{'revision':'R05A','units':'mm','origin':'fixed bowl support plane Z0; camera +Y; right +X','source_sha256':sha(ROOT/'source/model.py'),'interfaces':MOUNT_INTERFACES,'visor_retention':checks['visor_retention']})
print('CORE CAD and mesh gates passed',flush=True)

for ref,c in refs:
 v,t=ref.tessellate(.15,.25);mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);mesh.fix_normals();meshes.append((ref.label,mesh,c,True))
manifest=json.loads((ROOT/'review/manifest.json').read_text())
manifest['project']['name']='灵犀 R05A · 主体、底座、透明盖与压框'
manifest['versions']['current']={'source':'../source/model.py','step':None}
manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True};manifest['parameters']=[]
manifest['parts']=[{'id':name,'label':LABELS.get(name,name+' / 参照不打印'),'visible':not ref,'color':c[:7],'reference':ref} for name,m,c,ref in meshes]
dump(ROOT/'review/manifest.json',manifest)
provenance={k:sha(ROOT/f) for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
provenance['visor_source_hash']=sha(ROOT/'source/visor_R05A.py')
for rev in ['02','03','04','05']:provenance[f'R{rev}_archive_hash']=sha(ROOT/f'source/model_R{rev}_archive.py')
vertices=[];faces=[]
for name,m,c,ref in meshes:
 start=len(vertices);vertices.extend(m.vertices.tolist())
 for tri in m.faces:
  pts=m.vertices[tri];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=max(np.linalg.norm(n),1e-12)
  faces.append({'indices':[int(i)+start for i in tri],'part_id':name,'feature_id':name,'world_point':pts.mean(0).tolist(),'normal':n.tolist(),'color':c,'reference':ref})
(cache/'current_mesh.json').write_text(json.dumps({'vertices':vertices,'faces':faces,'provenance':provenance}))
(cache/'R05A_scene.json').write_text(json.dumps({'objects':[{'name':n,'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'color':c,'reference':r,'part_id':n} for n,m,c,r in meshes]}))
print('R05A scene and review published',flush=True)

exports=[]
for name,m,c,ref in meshes:
 if ref:continue
 flat=m.copy();offset=-float(flat.bounds[0,2]);flat.apply_translation([0,0,offset])
 path=out/f'{name}_R05A_1pc_mm.stl'
 if name in ['H01_MAIN_SHELL','H02_DOCK_RECEIVER']:
  path=out/f'{name}_R05_1pc_mm.stl'
  path.write_bytes((ROOT/'outputs/print_R05_batch1'/path.name).read_bytes())
 else:flat.export(path)
 check=trimesh.load(path,force='mesh');assert check.is_watertight and check.is_volume
 exports.append({'file':path.name,'quantity':1,'material_color':'clear' if 'CLEAR_VISOR' in name else 'gray','unit':'mm','assembly_to_STL_translation_mm':[0,0,offset],'sha256':sha(path)})

# Core-only 3MF with native base material colors. Assembly placement preserved.
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',C);q=lambda t:'{'+C+'}'+t
root=ET.Element(q('model'),{'unit':'millimeter'})
ET.SubElement(root,q('metadata'),{'name':'Title'}).text='Lingxi R05A - first batch structural core - 4 separate pieces'
ET.SubElement(root,q('metadata'),{'name':'Description'}).text='Fit-print prototype. Assembly coordinates; separate and arrange before slicing. Contains transparent cover and gray retainer. No electronics or orange decorations.'
resources=ET.SubElement(root,q('resources'));materials=ET.SubElement(resources,q('basematerials'),{'id':'1'});ET.SubElement(materials,q('base'),{'name':'GRAY','displaycolor':GRAY});ET.SubElement(materials,q('base'),{'name':'CLEAR_VISOR_SEPARATE_MATERIAL','displaycolor':'#E8F5FF55'})
build=ET.SubElement(root,q('build'))
for i,(name,m,c,ref) in enumerate(meshes[:4]):
 oid=str(i+2);obj=ET.SubElement(resources,q('object'),{'id':oid,'type':'model','name':name,'pid':'1','pindex':'1' if 'CLEAR_VISOR' in name else '0'});me=ET.SubElement(obj,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in m.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for a,b,c in m.faces:ET.SubElement(ts,q('triangle'),{'v1':str(a),'v2':str(b),'v3':str(c)})
 ET.SubElement(build,q('item'),{'objectid':oid})
path=out/'Lingxi_R05A_Batch1_GRAY_CLEAR_4SeparateParts_Assembly.3mf'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
w=lib3mf.get_wrapper();mf=w.CreateModel();reader=mf.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(path));assert reader.GetWarningCount()==0
assert mf.GetMeshObjects().Count()==4 and mf.GetBuildItems().Count()==4
exports.append({'file':path.name,'separate_parts':4,'unit':'mm','strict_3mf_warnings':0,'sha256':sha(path)})
dump(out/'PRINT_MANIFEST_R05A.json',{'revision':'R05A','status':'fit_print_prototype','source_provenance':provenance,'files':exports})
(out/'先读我_第一批打印.txt').write_text('灵犀 R05A 第一批打印：4种零件，每种1件。单位毫米，100%比例。\n\n打印清单\n1. H01_MAIN_SHELL_R05：主体外壳，灰色，1件。\n2. H02_DOCK_RECEIVER_R05：头部深腔底座，灰色，1件。\n3. H03_CLEAR_VISOR_R05A：透明折面盖，透明材料，1件。\n4. H04_VISOR_FRAME_R05A：独立可拆压框，灰色，1件。\nH01/H02的STL与上一个两件包逐字节相同。已打印主体/底座的，只需补打H03和H04，不必重打。\n机器人上固定的R02碗底继续沿用，不在这4件里。橙色装饰、侧风口、手机架、OLED/摄像头内托后续另打。\n\n装配透明盖\n把透明盖放到灰色压框后面，四个安装耳对准压框孔/销。上方两根一体定位销穿过透明耳孔，插入主体上方两个原有盲孔；下方两孔用2颗M2×20盘头螺丝和2颗M2螺母固定。不是4颗贯穿螺丝。下方螺母从主体内部放入，需先装面罩再封底座。轻拧到贴合即可，透明耳不能压裂。拆卸时卸下下方2颗螺丝，向前取下面罩/压框。透明光学面与压框前唇互相搭接。\n\n主体与深腔底座\n另用2颗M2×10盘头螺丝＋2颗M2螺母。从内部侧面放入螺母，再从底面检修井向上拧入。共需M2×20两颗、M2×10两颗、M2螺母四颗。\n深腔完整接收原86×86×29mm碗底，名义间隙约0.4mm；左侧42×28mm接线大口、磁吸颈部17.94×4.4mm和22×8mm焊点避让均保持R05设计。\n\n文件说明\n3MF内含4个独立对象和GRAY/CLEAR两种材料标记，保留装配位置；不是已经排好的打印板，也不含打印机/耗材/支撑配置。切片时拆分为对象后分别排布，透明盖单独指定透明材料。不要将装配状态合并打印。STL不含颜色，按上述清单选材料；每个STL已移到最低Z=0。\n3MF透明显示色和预览图不保证打印后透光清晰。透明件的实际视觉效果取决于材料、打印和后处理。面板名义Y向厚度1.4mm，耳部更厚；并非各处等法向厚度。\n这是首轮试装件：已做实体、网格、配合路径检查，尚未经实物试装。接头实际压缩、螺丝螺母尺寸及透明盖安装仍需试配。胶只用于磁吸接头塑料侧壁，不粘触点，也不要将可拆透明盖粘死。\n')
for filename in ['mount_interfaces_R05A.json','R05A_checks.json']:(out/filename).write_bytes((ROOT/'validation'/filename).read_bytes())
zip_path=ROOT/'outputs/Lingxi_R05A_Batch1_Core_Visor_4Parts.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(out.iterdir()):
  if f.is_file():z.write(f,arcname=f'Lingxi_R05A_Batch1/{f.name}')
print('PRINT BUNDLE',zip_path,flush=True)
