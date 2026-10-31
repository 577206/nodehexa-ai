from model import *
import json,hashlib,os,time
import numpy as np,trimesh
os.environ['MPLCONFIGDIR']=str(ROOT/'review/cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from color_raster import raster_colored
p=load_parameters(ROOT/'parameters.yaml');assembly=build_model(p);parts=list(assembly.children);refs=hardware_references(p)
checks={'revision':'R04','physical_fit':'prototype_unverified','parts':[],'collisions':[],'physical_groups':{},'bowl_collisions':[],'reference_conflicts':[]}
meshes=[]
for s in parts:
 assert s.is_valid and len(s.solids())==1,(s.label,len(s.solids()))
 v,t=s.tessellate(.08,.15);m=trimesh.Trimesh(vertices=[[v.X,v.Y,v.Z] for v in v],faces=t,process=True);m.fix_normals()
 m.update_faces(m.nondegenerate_faces());m.remove_unreferenced_vertices();m.fix_normals()
 if not (m.is_watertight and m.is_volume):print('MESH_WARNING',s.label,m.is_watertight,m.is_volume,flush=True)
 meshes.append((s.label,m,COLORS[s.label],False));checks['parts'].append({'id':s.label,'valid_solid':True,'closed_mesh':bool(m.is_watertight),'volume_mesh':bool(m.is_volume),'bbox_mm':list(s.bounding_box().size),'volume_mm3':s.volume})
 export_brep(s,str(ROOT/'review/cache'/f'R04_{s.label}.brep'))
for i,a in enumerate(parts):
 for b in parts[i+1:]:
  # Bounding box test only filters clearly separated pairs; actual CAD checks the rest.
  aa=a.bounding_box();bb=b.bounding_box()
  if any(tuple(aa.max)[j]<=tuple(bb.min)[j]+1e-6 or tuple(bb.max)[j]<=tuple(aa.min)[j]+1e-6 for j in range(3)):continue
  vol=volume(a.intersect(b))
  if vol>1e-5:checks['collisions'].append({'a':a.label,'b':b.label,'mm3':vol})
for pid in sorted(set(PART_IDS.values())):
 group=[s for s in parts if PART_IDS[s.label]==pid];joined=group[0]
 for s in group[1:]:joined=joined+s
 checks['physical_groups'][pid]={'regions':[s.label for s in group],'joined_solids':len(joined.solids()),'volume_mm3':joined.volume}
for ref,color in refs:
 if ref.label=='REF_FIXED_BOWL_R02' or ref.label=='REF_BOARDS_120x50_APPROX' or 'OLED_' in ref.label and 'PIXELS' not in ref.label:
  for s in parts:
   vol=volume(s.intersect(ref))
   if vol>1e-5:checks['bowl_collisions' if ref.label=='REF_FIXED_BOWL_R02' else 'reference_conflicts'].append({'a':s.label,'b':ref.label,'mm3':vol})
 v,t=ref.tessellate(.15,.25);m=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);m.fix_normals();meshes.append((ref.label,m,color,True))
checks['CAD_overlap_pass']=not checks['collisions'] and not checks['bowl_collisions']
checks['dimensions']={'phone_internal_width_mm':val(p,'phone_clear_width'),'phone_user_width_mm':val(p,'phone_nominal_width'),'phone_thickness_unmeasured':True,'dock_envelope_depth_mm':val(p,'dock_depth'),'fixed_bowl_height_mm':val(p,'bowl_height'),'assembly_without_reference_bbox_mm':list(assembly.bounding_box().size)}
(ROOT/'validation/R04_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps(checks,ensure_ascii=False),flush=True)
manifest=json.loads((ROOT/'review/manifest.json').read_text());manifest['project']['name']='灵犀橙灰深腔驾驶舱 R04'
manifest['versions']['current']['source']='../source/model.py';manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True};manifest['parameters']=[];manifest['parts']=[]
for name,m,color,isref in meshes:
 pid=PART_IDS.get(name,name)
 if any(a['id']==pid for a in manifest['parts']):continue
 manifest['parts'].append({'id':pid,'label':LABELS.get(pid,name+' / 参照不打印'),'visible':not ('PHONE_75' in name or 'BOARDS' in name or 'FIXED_BOWL' in name),'color':color[:7],'reference':isref})
(ROOT/'review/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
vertices=[];faces=[]
for name,m,color,isref in meshes:
 st=len(vertices);vertices.extend(m.vertices.tolist())
 for tri in m.faces:
  pts=m.vertices[tri];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=max(np.linalg.norm(n),1e-12)
  faces.append({'indices':[int(i)+st for i in tri],'part_id':PART_IDS.get(name,name),'feature_id':name,'world_point':pts.mean(0).tolist(),'normal':n.tolist(),'color':color,'reference':isref})
provenance={k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
provenance['R02_archive_hash']=hashlib.sha256((ROOT/'source/model_R02_archive.py').read_bytes()).hexdigest()
(ROOT/'review/cache/current_mesh.json').write_text(json.dumps({'vertices':vertices,'faces':faces,'provenance':provenance}))
scene_objects=[]
for name,m,color,isref in meshes:
 scene_objects.append({'name':name,'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'color':color,'reference':isref,'part_id':PART_IDS.get(name,name)})
(ROOT/'review/cache/R04_scene.json').write_text(json.dumps({'objects':scene_objects}))
plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(2,2,figsize=(16,13),facecolor='#eef2f5');fig.subplots_adjust(top=.87,bottom=.09,hspace=.08,wspace=.02)
views=[(24,128,'前左侧 / 原折面面罩与独立风口','hero'),(15,175,'左侧 / 大接线口与直立手机架','side'),(-35,120,'底部 / 29 mm碗底完整嵌入深腔','bottom'),(18,120,'分件 / 面罩、底座、风口和手机架','exploded')]
for ax,(e,a,title,mode) in zip(axes.flat,views):
 vv=[];tt=[];cc=[];aa=[]
 for name,m,color,isref in meshes:
  if 'FIXED_BOWL' in name or 'BOARDS' in name or 'PHONE_75' in name or 'SOFT_PAD' in name:continue
  verts=m.vertices.copy()
  if mode=='bottom' and isref:continue
  if mode=='exploded':
   if name in ['VISOR_FRAME','CLEAR_VISOR']:verts[:,1]+=32;verts[:,2]+=13
   if name.startswith('VENT'):verts[:,0]+= -22 if '_-1' in name else 22
   if name.startswith('PHONE'):verts[:,1]-=30
   if name=='DOCK_BASE':verts[:,2]-=28
  st=len(vv);vv.extend(verts);tt.extend(m.faces+st);cc.extend([[int(color[k:k+2],16) for k in [1,3,5]]]*len(m.faces));aa.extend([int(color[7:9],16)/255 if len(color)==9 else 1]*len(m.faces))
 ax.imshow(raster_colored(np.asarray(vv),np.asarray(tt),np.asarray(cc),e,a,width=1100,height=850,alphas=np.asarray(aa)));ax.axis('off');ax.set_title(title,fontsize=13,color='#253C50')
fig.text(.05,.95,'橙灰机甲驾驶舱 R04 · 实际 CAD 审阅',fontsize=24,color='#253C50')
fig.text(.05,.905,'重建四段折面罩、低位下巴和真实分层装甲；碗底86×86×29不变；手机架净宽76 mm。',fontsize=13,color='#52697B')
fig.text(.05,.045,'结构样机：板厚、OLED有效区/安装孔、手机厚度、磁吸压缩量及螺丝配合尚待实测；不是生产放行。',fontsize=11,color='#A13C36')
fig.savefig(ROOT/'outputs/drawings/head_R04_actual_CAD.png',dpi=140)
print('R04 preview saved',flush=True)
