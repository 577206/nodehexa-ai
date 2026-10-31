from pathlib import Path
import os,json,hashlib
from model import *
os.environ['MPLCONFIGDIR']=str(ROOT/'review/cache/matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Rectangle,Circle
from build123d import Pos,Box,Cylinder,Align,Compound
plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name()
plt.rcParams['axes.unicode_minus']=False
params=load_parameters(ROOT/'parameters.yaml');p=lambda n:value(params,n)
model=build_model(params)
assert model.is_valid and len(model.solids())==1
# Validate the user-supplied envelope, excluding exactly the two approved 8mm corridors.
electronics=Pos(0,0,p('electronics_height')/2)*Box(p('electronics_width'),p('electronics_length'),p('electronics_height'))
for x,y in screw_centers(params):
 electronics=electronics-Pos(x,y,-.1)*Cylinder(p('well_outer_diameter')/2,22,align=(Align.CENTER,Align.CENTER,Align.MIN))
intersection=model.intersect(electronics)
collision=intersection.volume if intersection is not None else 0
shaft_checks=[]
for x,y in screw_centers(params):
 probe=Pos(x,y,-.1)*Cylinder(p('screw_clearance_diameter')/2-.01,32,align=(Align.CENTER,Align.CENTER,Align.MIN))
 obj=model.intersect(probe)
 shaft_checks.append({'axis_mm':[x,y],'blocked_volume_mm3':obj.volume if obj else 0})
assert abs(collision)<1e-6
assert all(abs(c['blocked_volume_mm3'])<1e-6 for c in shaft_checks)
# Confirm continuous open tool corridors above the seat and an open tail passage.
for x,y in screw_centers(params):
 probe=Pos(x,y,p('screw_seat_thickness')+.01)*Cylinder(p('well_access_diameter')/2-.01,32,align=(Align.CENTER,Align.CENTER,Align.MIN))
 o=model.intersect(probe);assert not o or abs(o.volume)<1e-6
probe=Pos(0,0,25)*Box(10,1,12)
o=model.intersect(probe);assert not o or abs(o.volume)<1e-6
bb=model.bounding_box().size
checks={'status':'pass_CAD_checks_only','valid':bool(model.is_valid),'solids':len(model.solids()),'bbox_mm':list(bb),'volume_mm3':model.volume,'confirmed_electronics_envelope_mm':[70,70,20],'approved_exclusions':'two8mm vertical screw corridors, user-confirmed','electronics_intersection_mm3':collision,'shaft_passages':shaft_checks,'effective_ceiling_mm':p('ceiling_height'),'nominal_roof_clearance_mm':p('ceiling_height')-p('electronics_height'),'screw_bearing_thickness_mm':p('screw_seat_thickness'),'nominal_10mm_screw_reach_below_seat_mm':10-p('screw_seat_thickness'),'reach_caveat':'Not actual thread engagement; account for original frame, receiver and screw tolerance.','connector_throat_mm':[p('throat_length'),p('throat_width')], 'underside_relief_mm':[p('relief_length'),p('relief_width')], 'collar_stop_z':p('flange_stop_z'), 'contact_face_z_nominal':p('flange_stop_z')+2,'physical_not_verified':['Original screw shaft/head/thread receiver and retained engagement','Connector exact ear/step profile, glue and spring compression','Real electronics placement, solder loops and mechanical leg sweep','Upper head counterpart, mass and magnetic holding force','External cable service openings not modeled']}
(ROOT/'validation/fit_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
# One joined solid, semantic regions rather than fake assembly parts.
def feature(q):
 x,y,z=q
 if abs(x)<14 and abs(y)<6 and z>23:return 'connector_pocket'
 if any((x-cx)**2+y*y<19 for cx,_ in screw_centers(params)):return 'two_recessed_screw_wells'
 if z>27.01:return 'head_keyed_nest'
 return 'fixed_hood'
v,t=model.tessellate(.08,.16);xyz=np.array([[q.X,q.Y,q.Z] for q in v]);faces=[]
for tri in t:
 a=xyz[list(tri)];normal=np.cross(a[1]-a[0],a[2]-a[0]);normal/=max(np.linalg.norm(normal),1e-12);c=a.mean(0)
 faces.append({'indices':list(tri),'part_id':model.label,'feature_id':feature(c),'world_point':c.tolist(),'normal':normal.tolist(),'color':'#3b4652'})
manifest=json.loads((ROOT/'review/manifest.json').read_text())
manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True}
manifest['parts']=[{'id':model.label,'label':'固定罩座 R02 / 单个实体','visible':True,'color':'#3b4652'}]
manifest['parameters']=[]
manifest['refs']=[{'id':'left_screw_seat','part_id':model.label,'entity_type':'face','feature_id':'two_recessed_screw_wells','label':'左盘头螺丝承压面','world_point':[-p('cover_hole_pitch')/2,2,p('screw_seat_thickness')],'normal':[0,0,1]},{'id':'connector_flange_stop','part_id':model.label,'entity_type':'face','feature_id':'connector_pocket','label':'凸缘向上止挡面','world_point':[9.3,0,p('flange_stop_z')],'normal':[0,0,-1]},{'id':'locating_rim','part_id':model.label,'entity_type':'face','feature_id':'head_keyed_nest','label':'驾驶舱定位边','world_point':[0,37,29],'normal':[0,0,1]}]
(ROOT/'review/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
provenance={k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}
(ROOT/'review/cache/current_mesh.json').write_text(json.dumps({'vertices':xyz.tolist(),'faces':faces,'provenance':provenance}))
registry={'features':[{'id':f['id'],'source':f"source/model.py:{f['id']}",'evidence':'validation/fit_checks.json','status':'CAD_valid; physical fit pending'} for f in __import__('yaml').safe_load((ROOT/'spec/current.yaml').read_text())['features']]}
spec=__import__('yaml').safe_load((ROOT/'spec/current.yaml').read_text())
registry['constraints']=[{'id':item,'source':'spec/current.yaml; source/model.py','evidence':'validation/fit_checks.json','status':'design_contract; see physical_not_verified limitations'} for item in spec['constraints']['narrative']]
registry['validation_targets']=[{'id':key,'source':'source/model.py; source/build_review.py','evidence':'validation/fit_checks.json','status':'CAD evidence or explicitly deferred physical requirement'} for group in spec['validation_targets'].values() for key in group]
(ROOT/'validation/feature_registry.json').write_text(json.dumps(registry,indent=2)+'\n')
# Actual CAD review image. The section is a visual cut only, not a saved part.
fig=plt.figure(figsize=(14,10.8),facecolor='#eef2f5')
fig.text(.05,.95,'碗底固定罩座  R02  /  实际CAD预览',fontsize=23,color='#203447')
fig.text(.05,.91,'器件 70×70×20 mm · 两处空螺丝通道已确认 · 普通盘头螺丝 · 接口从下往上顶，焊点留在里面',fontsize=11,color='#54697b')
section=model.intersect(Pos(0,30,15)*Box(100,60,40))
def render(ax,obj,elev,azim):
 from raster_review import raster
 if not hasattr(obj,'tessellate'): obj=Compound(children=list(obj))
 vv,tt=obj.tessellate(.10,.18);vv=np.array([[q.X,q.Y,q.Z] for q in vv])
 ax.imshow(raster(vv,tt,elev,azim));ax.axis('off');ax.set_facecolor('#eef2f5')

for i,(obj,el,az,title) in enumerate([(model,50,-60,'① 顶部：贯通接口、定位边和两处螺丝窝'),(model,-48,-60,'② 底部：中空罩体与低位螺丝座'),(section,12,-70,'③ 剖开查看：3 mm顶板，24 mm内净高')]):
 ax=fig.add_subplot(2,2,i+1);render(ax,obj,el,az);ax.set_title(title,fontsize=12,color='#203447',pad=-2)
a=fig.add_subplot(2,2,4);a.axis('off')
a.text(.02,.90,'R02 尺寸 / mm',fontsize=17,color='#203447')
a.text(.02,.77,'下口外形：86 × 86\n顶部外形：82 × 82\n最大高度：29\n罩内上部：76 × 76；净高24\n原孔中心距：57.004\n螺丝窝外径8；内径5.2\n螺丝通孔2.4；座底厚2.4\n上穿口：17.94 × 4.4\n下方避空：22 × 8；无托底\n顶部定位边高度：2',va='top',fontsize=12,color='#344c60',linespacing=1.65)
a.text(.02,-.10,'盘头孔与磁吸槽均为试装尺寸。\n未装入实体接插件，也未验证磁力或整机运动干涉。',fontsize=10,color='#ad3044',linespacing=1.6)
fig.text(.05,.035,'由参数化CAD直接生成；不是AI概念效果图。当前供结构检查，不是生产放行。',fontsize=11,color='#ad3044')
fig.subplots_adjust(left=.04,right=.98,top=.85,bottom=.11,hspace=.08,wspace=.03)
out=ROOT/'outputs/drawings';out.mkdir(parents=True,exist_ok=True)
fig.savefig(out/'bowl_mount_actual_CAD_R02.png',dpi=170)
fig.savefig(out/'bowl_mount_actual_CAD_R02.svg')
print(json.dumps({'CAD':checks['status'],'dimensions_mm':checks['bbox_mm'],'triangles':len(t),'electronic_collision_mm3':collision,'preview':'review/index.html'},ensure_ascii=False))
