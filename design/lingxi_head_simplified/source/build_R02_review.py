from pathlib import Path
import os,json,hashlib,sys
import numpy as np,trimesh
from model import *
os.environ['MPLCONFIGDIR']=str(ROOT/'review/cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from color_raster import raster_colored
p=load_parameters(ROOT/'parameters.yaml');model=build_model(p);parts=list(model.children)
ref=oled_references();checks={'revision':'R02','scope':'restored mecha form and shared-visor OLED reference layout','physical_fit':'not verified','parts':[],'intersections':[],'physical_part_count':4,'manufactured_material_regions':6,'OLED':{'provisional_module_mm':[27,28],'thickness_mm':None,'active_area_mm':None,'eye_center_spacing_mm':33,'overall_two_board_width_mm':60,'PCB_holes':'not modeled; unmeasured','references_excluded_from_print':True},'limitations':['Exact OLED dimensions, pin-inclusive thickness and active aperture not confirmed','Mask is visual reference only, not a finalized printable opening','OLED retainer/PCB mounting geometry not released','Camera bore, frame fastening and actual component fit remain prototype','Transparent pane retention and available adhesive/sheet process not verified']}
meshes=[]
for part in parts:
 assert part.is_valid and len(part.solids())==1,part.label
 v,t=part.tessellate(.10,.18);mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);mesh.fix_normals()
 assert mesh.is_watertight and mesh.is_volume,part.label
 meshes.append((part.label,mesh,COLORS[part.label],False))
 checks['parts'].append({'id':part.label,'solid':True,'closed_volume_mesh':True,'dimensions_mm':list(part.bounding_box().size)})
for i,a in enumerate(parts):
 for b in parts[i+1:]:
  r=a.intersect(b);v=(sum(x.volume for x in r) if isinstance(r,ShapeList) else r.volume) if r else 0
  if v>1e-7:checks['intersections'].append({'a':a.label,'b':b.label,'mm3':v})
print('overlap candidates',checks['intersections'],flush=True)
# No fit claims; retain any actual conflict visibly as a report, not hide geometry.
checks['CAD_overlap_pass']=not any(x['mm3']>1e-5 for x in checks['intersections'])
for part,color in ref:
 v,t=part.tessellate(.12,.20);mesh=trimesh.Trimesh(vertices=[[a.X,a.Y,a.Z] for a in v],faces=t,process=True);mesh.fix_normals();meshes.append((part.label,mesh,color,True))
manifest=json.loads((ROOT/'review/manifest.json').read_text());manifest['project']['name']='灵犀橙黄OLED机甲头部 R02'
manifest['versions']['current']['source']='../source/model.py'
manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True}
part_map={'R02_ORANGE_BODY':'P01_BODY','R02_YELLOW_SIDE_L':'P01_BODY','R02_YELLOW_SIDE_R':'P01_BODY','R02_YELLOW_VISOR_FRAME':'P02_VISOR_FRAME','R02_CLEAR_CANOPY':'P03_CLEAR_CANOPY','R02_ORANGE_BASE':'P04_BASE'}
labels={'P01_BODY':'01 橙黄双色主体 / 共印一件','P02_VISOR_FRAME':'02 黄色面罩护框','P03_CLEAR_CANOPY':'03 透明折面罩','P04_BASE':'04 橙色对接底板'}
manifest['parts']=[]
for name,m,color,isref in meshes:
 pid=part_map.get(name,name)
 if any(a['id']==pid for a in manifest['parts']):continue
 manifest['parts'].append({'id':pid,'label':labels.get(pid,name+' / 参照，不打印'),'visible':True,'color':color[:7],'reference':isref})
manifest['parameters']=[]
(ROOT/'review/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
vertices=[];faces=[]
for name,m,color,isref in meshes:
 start=len(vertices);vertices.extend(m.vertices.tolist())
 for tri in m.faces:
  pts=m.vertices[tri];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=max(np.linalg.norm(n),1e-12)
  faces.append({'indices':[int(i)+start for i in tri],'part_id':part_map.get(name,name),'feature_id':name,'world_point':pts.mean(0).tolist(),'normal':n.tolist(),'color':color,'reference':isref})
prov={k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]};prov['R02_helper_hash']=hashlib.sha256((ROOT/'source/model_R02.py').read_bytes()).hexdigest()
(ROOT/'review/cache/current_mesh.json').write_text(json.dumps({'vertices':vertices,'faces':faces,'provenance':prov}))
(ROOT/'validation/R02_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')

plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
fig,axes=plt.subplots(1,3,figsize=(18,8),facecolor='#eef2f5');fig.subplots_adjust(top=.78,bottom=.18,wspace=.02)
for ax,(view,title) in zip(axes,[((25,62),'机甲轮廓 / 橙黄装甲与共享面罩'),((8,90),'正面 / 两块OLED参照布局'),((18,62),'移开面罩 / 屏幕与遮边框位置')]):
 vv=[];tt=[];cc=[];aa=[]
 for name,m,color,isref in meshes:
  verts=m.vertices.copy()
  if title.startswith('移开'):
   if name in ['R02_CLEAR_CANOPY','R02_YELLOW_VISOR_FRAME']:verts[:,1]+=35;verts[:,2]+=20
  st=len(vv);vv.extend(verts);tt.extend(m.faces+st);cc.extend([[int(color[k:k+2],16) for k in [1,3,5]]]*len(m.faces));aa.extend([int(color[7:9],16)/255 if len(color)==9 else 1.]*len(m.faces))
 ax.imshow(raster_colored(np.array(vv),np.array(tt),np.array(cc),*view,width=1000,height=850,alphas=np.array(aa)));ax.axis('off');ax.set_title(title,fontsize=12,color='#203447')
fig.text(.04,.94,'OLED机甲驾驶舱 R02  /  恢复折面与分层结构',fontsize=24,color='#203447')
fig.text(.04,.865,'双屏藏在同一块透明罩后；保留侧面进风口、圆形侧盖、护框与下颏镜头框。只减少零碎装饰和多余螺丝。',fontsize=12,color='#4a6275')
fig.text(.04,.10,'OLED暂按每块27 ×28 mm参照放置；板厚、插针空间和实际发光区未量，遮边框及安装孔尚未定型。',fontsize=12,color='#ad3444')
fig.text(.04,.045,'实际CAD与硬件参照预览。屏幕蓝板、显示区和眼睛图案为位置说明，不属于打印件或已完成的驱动程序。',fontsize=11,color='#4a6275')
out=ROOT/'outputs/drawings';out.mkdir(parents=True,exist_ok=True);fig.savefig(out/'OLED_mecha_head_R02_actual_CAD.png',dpi=160)
print('R02 review drawn; CAD overlap pass:',checks['CAD_overlap_pass'])
