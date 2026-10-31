"""Build source, check fixed interfaces, publish review and export batch2 only."""
from model import *
import json,hashlib,zipfile,xml.etree.ElementTree as ET
import numpy as np,trimesh,lib3mf

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def overlap_bounds(a,b):
 aa=a.bounding_box();bb=b.bounding_box()
 return all(min(amax,bmax)-max(amin,bmin)>1e-6 for amin,amax,bmin,bmax in zip(aa.min,aa.max,bb.min,bb.max))

p=load_parameters(ROOT/'parameters.yaml');assembly=build_model(p);parts=list(assembly.children);refs=hardware_references(p)
cache=ROOT/'review/cache';out=ROOT/'outputs/print_R06_batch2';out.mkdir(parents=True,exist_ok=True)
checks={'revision':'R06','status':'fit_print_prototype','physical_fit_verified':False,'parts':[],'intersections':[],'unchanged_core':[]}
meshes=[]
for i,shape in enumerate(parts):
 assert shape.is_valid and len(shape.solids())==1,shape.label
 export_brep(shape,str(cache/f'R06_{shape.label}.brep'))
 v,t=shape.tessellate(.055,.12);m=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True)
 m.update_faces(m.nondegenerate_faces());m.remove_unreferenced_vertices();m.fix_normals()
 row={'id':shape.label,'valid':True,'solids':1,'watertight':bool(m.is_watertight),'volume_mesh':bool(m.is_volume),'components':len(m.split()),'bbox_mm':list(shape.bounding_box().size),'CAD_volume_mm3':shape.volume,'triangles':len(m.faces),'batch':1 if i<4 else 2}
 checks['parts'].append(row);print(row,flush=True)
 assert m.is_watertight and m.is_volume and len(m.split())==1,row
 if i<4:
  original=import_brep(str(cache/f'R05A_{shape.label}.brep'))
  delta=volume(shape-original)+volume(original-shape);assert delta<1e-5,(shape.label,'changed',delta)
  checks['unchanged_core'].append({'id':shape.label,'symmetric_difference_mm3':delta})
 meshes.append((shape.label,m,COLORS[shape.label],False))

for i,a in enumerate(parts):
 for b in parts[i+1:]:
  if not overlap_bounds(a,b):continue
  vv=volume(a.intersect(b));checks['intersections'].append({'a':a.label,'b':b.label,'volume_mm3':vv})
  if vv>1e-5:print('COLLISION',a.label,b.label,vv,flush=True)
 for b,c in refs:
  if not overlap_bounds(a,b):continue
  vv=volume(a.intersect(b));checks['intersections'].append({'a':a.label,'b':b.label,'volume_mm3':vv})
  if vv>1e-5:print('REFERENCE COLLISION',a.label,b.label,vv,flush=True)
checks['pass']=all(x['volume_mm3']<1e-5 for x in checks['intersections'])
dump(ROOT/'validation/R06_checks.json',checks)
assert checks['pass'],'Collisions; see validation/R06_checks.json'
print('ALL CAD gates passed',flush=True)
dump(ROOT/'validation/mount_interfaces_R06.json',{'revision':'R06','units':'mm','frozen_core':MOUNT_INTERFACES,'decorative_fasteners':DECORATION_MOUNTS})

for ref,c in refs:
 v,t=ref.tessellate(.15,.25);m=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);m.fix_normals();meshes.append((ref.label,m,c,True))
manifest=json.loads((ROOT/'review/manifest.json').read_text());manifest['project']['name']='灵犀 R06 · 橙灰独立装饰件'
manifest['versions']['current']={'source':'../source/model.py','step':None};manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True};manifest['parameters']=[]
manifest['parts']=[{'id':n,'label':LABELS.get(n,n+' / 参照不打印'),'visible':not ref,'color':c[:7],'reference':ref} for n,m,c,ref in meshes]
dump(ROOT/'review/manifest.json',manifest)
provenance={k:sha(ROOT/f) for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
provenance['module_hashes']={n:sha(ROOT/'source'/f'{n}.py') for n in MODULES};provenance['frozen_core_hash']=sha(ROOT/'source/model_R05A_archive.py');provenance['visor_source_hash']=sha(ROOT/'source/visor_R05A.py')
vertices=[];faces=[]
for n,m,c,ref in meshes:
 start=len(vertices);vertices.extend(m.vertices.tolist())
 for tri in m.faces:
  pts=m.vertices[tri];normal=np.cross(pts[1]-pts[0],pts[2]-pts[0]);normal/=max(np.linalg.norm(normal),1e-12)
  faces.append({'indices':[int(a)+start for a in tri],'part_id':n,'feature_id':n,'world_point':pts.mean(0).tolist(),'normal':normal.tolist(),'color':c,'reference':ref})
(cache/'current_mesh.json').write_text(json.dumps({'vertices':vertices,'faces':faces,'source':'source/model.py and its declared decoration modules','parameters':{k:val(p,k) for k in p['parameters']},'provenance':provenance}))
(cache/'R06_scene.json').write_text(json.dumps({'objects':[{'name':n,'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'color':c,'reference':ref,'part_id':n} for n,m,c,ref in meshes]}))

exports=[];new_meshes=[(n,m,c,r) for n,m,c,r in meshes if n.startswith('D') and not r]
for name,m,color,ref in new_meshes:
 folder='01_ORANGE' if color.upper().startswith('#F37824') else '02_GRAY';(out/folder).mkdir(exist_ok=True)
 flat=m.copy();offset=-float(flat.bounds[0,2]);flat.apply_translation([0,0,offset]);path=out/folder/f'{name}_R06_1pc_mm.stl';flat.export(path)
 loaded=trimesh.load(path,force='mesh');assert loaded.is_watertight and loaded.is_volume
 exports.append({'file':str(path.relative_to(out)),'label':LABELS[name],'quantity':1,'color':folder[3:],'unit':'mm','assembly_to_STL_translation_mm':[0,0,offset],'sha256':sha(path)})
C='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';ET.register_namespace('',C);q=lambda t:'{'+C+'}'+t
root=ET.Element(q('model'),{'unit':'millimeter'});ET.SubElement(root,q('metadata'),{'name':'Title'}).text='Lingxi R06 - SECOND BATCH ONLY - separate gray and orange modules'
ET.SubElement(root,q('metadata'),{'name':'Description'}).text='Assembly coordinates, arrange individual objects before slicing. No R05A core parts. Fit-print prototype, no machine or material profile.'
resources=ET.SubElement(root,q('resources'));materials=ET.SubElement(resources,q('basematerials'),{'id':'1'})
for name,c in [('ORANGE','#F37824FF'),('GRAY','#7C8388FF')]:ET.SubElement(materials,q('base'),{'name':name,'displaycolor':c})
build=ET.SubElement(root,q('build'))
for i,(n,m,c,ref) in enumerate(new_meshes):
 oid=str(i+2);obj=ET.SubElement(resources,q('object'),{'id':oid,'type':'model','name':n,'pid':'1','pindex':'0' if c.upper().startswith('#F37824') else '1'})
 me=ET.SubElement(obj,q('mesh'));vs=ET.SubElement(me,q('vertices'));ts=ET.SubElement(me,q('triangles'))
 for x,y,z in m.vertices:ET.SubElement(vs,q('vertex'),{'x':f'{x:.8f}','y':f'{y:.8f}','z':f'{z:.8f}'})
 for a,b,c in m.faces:ET.SubElement(ts,q('triangle'),{'v1':str(a),'v2':str(b),'v3':str(c)})
 ET.SubElement(build,q('item'),{'objectid':oid})
path=out/'Lingxi_R06_Batch2_ORANGE_GRAY_Assembly.3mf'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
 z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
 z.writestr('3D/3dmodel.model',ET.tostring(root,encoding='utf-8',xml_declaration=True))
w=lib3mf.get_wrapper();mf=w.CreateModel();reader=mf.QueryReader('3mf');reader.SetStrictModeActive(True);reader.ReadFromFile(str(path))
assert reader.GetWarningCount()==0 and mf.GetMeshObjects().Count()==len(new_meshes) and mf.GetBuildItems().Count()==len(new_meshes)
exports.append({'file':path.name,'object_count':len(new_meshes),'strict_3mf_warnings':0,'unit':'mm','sha256':sha(path)})
dump(out/'PRINT_MANIFEST_R06.json',{'revision':'R06','status':'fit_print_prototype','source_provenance':provenance,'files':exports,'fasteners':DECORATION_MOUNTS,'parts':DECORATION_RECORDS,'core_changed':False,'physical_fit_verified':False})
for f in ['R06_checks.json','mount_interfaces_R06.json']:(out/f).write_bytes((ROOT/'validation'/f).read_bytes())
print('SECOND BATCH EXPORT COMPLETE',len(new_meshes),'new parts',flush=True)
