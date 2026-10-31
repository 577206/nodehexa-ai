from pathlib import Path
import os,json,hashlib
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle,Circle,FancyBboxPatch
from matplotlib import font_manager
import numpy as np
from matplotlib.collections import PolyCollection
plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name()
plt.rcParams['axes.unicode_minus']=False
repo=ROOT.parents[1]; project=repo/'design/nocturne_hexapod'
meshfile=project/'review/cache/current_mesh.json'
d=json.loads(meshfile.read_text()); V=np.array(d['vertices'])
checks=json.loads((project/'validation/edge_frame_checks.json').read_text())
C={'bg':'#f4f6f8','ink':'#152436','sub':'#54677a','blue':'#286caa','red':'#ab2e3d','line':'#b9c5d1','green':'#238778'}
def note(ax,x,y,s,size=10,c=None,**kw):
 return ax.text(x,y,s,fontsize=size,color=c or C['ink'],**kw)
def dim(ax,a,b,label,off=10,col=None):
 col=col or C['blue']; a=np.array(a,float);b=np.array(b,float)
 delta=b-a; n=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)*off
 aa=a+n;bb=b+n
 for p,q in [(a,aa),(b,bb)]: ax.plot([p[0],q[0]],[p[1],q[1]],color=C['line'],lw=.7)
 ax.annotate('',xy=aa,xytext=bb,arrowprops=dict(arrowstyle='<->',lw=1,color=col,shrinkA=0,shrinkB=0))
 mid=(aa+bb)/2;vert=abs(delta[1])>abs(delta[0])
 ax.text(mid[0]+(-3 if vert else 0),mid[1]+(0 if vert else 3),label,ha='right' if vert else 'center',va='center' if vert else 'bottom',rotation=90 if vert else 0,fontsize=10,color=col,bbox=dict(facecolor=C['bg'],edgecolor='none',pad=1))
def footprint(part):
 faces=np.array([f['indices'] for f in d['faces'] if f['part_id']==part]); p=V[faces][:,:,:2]
 area=np.abs((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,1,1]-p[:,0,1])*(p[:,2,0]-p[:,0,0]))
 shape=p[area>1e-7]
 # Source u is length, v is width. Map width->X, length->Y; +Y is the declared design front.
 flat=shape.reshape(-1,2); lo=flat.min(0);hi=flat.max(0); cx=(lo[0]+hi[0])/2; cy=(lo[1]+hi[1])/2
 def trans(a):
  a=np.array(a);return np.column_stack((a[:,1]-cy,a[:,0]-cx))
 return shape,trans
fig=plt.figure(figsize=(15,10.5),facecolor=C['bg'])
fig.text(.055,.95,'机身尺寸基准  /  EDGE50',fontsize=25,weight='bold',color=C['ink'])
fig.text(.055,.915,'用户已确认：总加宽 50 mm（左右各 25 mm）  ·  单位 mm  ·  仅机身框架，不含六条腿',fontsize=11,color=C['sub'])
parts=[('N001_upper_frame_EDGE50_DRAFT','上框 / BodyTop',134.8090515,124.3431473,74.3431473),('N002_lower_frame_EDGE50_DRAFT','下框 / BodyButtom',130.3431396,128.3431482,78.3431482)]
for idx,(pid,title,L,W,W0) in enumerate(parts):
 ax=fig.add_axes([.055+idx*.47,.285,.435,.58]);ax.set_aspect('equal');ax.set_xlim(-101,101);ax.set_ylim(-95,101);ax.axis('off')
 shape,trans=footprint(pid)
 ax.add_collection(PolyCollection(trans(shape.reshape(-1,2)).reshape(-1,3,2),facecolors='#293844',edgecolors='none',antialiaseds=False))
 ax.add_patch(Rectangle((-W0/2,-L/2),W0,L,fill=False,ls=(0,(4,4)),ec='#99abbc',lw=1.1))
 ax.axhline(0,color='#a6b7c7',lw=.5,ls='-.');ax.axvline(0,color='#a6b7c7',lw=.5,ls='-.')
 dim(ax,(-W/2,L/2),(W/2,L/2),f'宽 {W:.2f}',off=12)
 dim(ax,(-W/2,-L/2),(-W/2,L/2),f'长 {L:.2f}',off=14)
 ax.annotate('前方 +Y',xy=(83,94),xytext=(83,81),ha='center',fontsize=9,color=C['blue'],arrowprops=dict(arrowstyle='->',color=C['blue']))
 note(ax,0,-87,title,14,ha='center',weight='bold')
 if idx==0:
  loops=json.loads((project/'validation/interfaces/BodyTop_section.json').read_text())['loops_uv_mm']
  centers=[]
  for k in [5,11]:
   a=np.array(loops[k]); mid=(a.min(0)+a.max(0))/2; p=np.array([mid[1]-74.3431473/2,mid[0]-L/2]);centers.append(p)
   ax.add_patch(Circle(p,3.1,fill=False,ec=C['red'],lw=1.4))
  spacing=float(np.linalg.norm(centers[1]-centers[0]));dim(ax,centers[0],centers[1],f'原机盖孔中心距 ≈ {spacing:.2f}',off=8,col=C['red'])
  # Void bounds only, not a rectangular safe zone.
  a=np.array(loops[1]);extent=a.max(0)-a.min(0)
  aperture={'length_bbox_mm':float(extent[0]),'width_bbox_mm':float(extent[1]),'note':'异形开口包围尺寸，不是矩形可用安装面'}
fig.text(.06,.235,'灰色虚框：原机外接范围；深色：当前加宽草稿的实际投影。红圈：保留的原机盖孔。',fontsize=10,color=C['sub'])
fig.text(.06,.195,'上框：原宽 74.34 → 124.34；厚度 3.00。     下框：原宽 78.34 → 128.34；最大厚度 9.00（基础板约 3）。',fontsize=11,color=C['ink'])
fig.text(.06,.155,f'上框中央异形开口包围尺寸：约 {aperture["length_bbox_mm"]:.2f} × {aperture["width_bbox_mm"]:.2f}；不可当作完整矩形安装面。',fontsize=11,color=C['ink'])
fig.text(.06,.115,'尚未确定：上下框装配间距、电子板最高点、腿部完整运动包络、头部重量与重心。不能由单件厚度推算整机高度。',fontsize=10,color=C['sub'])
fig.text(.06,.075,'依据：仓库当前 EDGE50 预览网格和孔截面；尺寸为文件几何值，非实物测量。待收到用户新版上下机身后复核。',fontsize=10,color=C['sub'])
fig.text(.06,.035,'R01  /  2026-10-31   ·   连接讨论用尺寸图，非加工开孔图',fontsize=10,color=C['red'])
fig.savefig(ROOT/'body_dimensions_EDGE50_R01.png',dpi=190)
fig.savefig(ROOT/'body_dimensions_EDGE50_R01.svg')
plt.close(fig)

fig=plt.figure(figsize=(15,9),facecolor=C['bg'])
fig.text(.05,.94,'头部快拆连接方案  /  机械固定与通信分开设计',fontsize=23,weight='bold',color=C['ink'])
fig.text(.05,.89,'方案示意：不锁定孔位、磁铁规格或接口外形尺寸；等待新版机身与硬件包络后定尺寸。',fontsize=11,color=C['sub'])
ax=fig.add_axes([.04,.17,.54,.65]);ax.set_xlim(0,120);ax.set_ylim(0,118);ax.axis('off')
for x,y,w,h,col,label in [(16,91,85,19,'#253546','驾驶舱 / 独立电源与电子板'),(24,72,69,8,'#ad3545','头部对接底板'),(24,48,69,8,'#697e91','机身快拆座'),(14,25,89,8,'#a5b5c4','架空转接架 / 避让主板和接线'),(6,8,105,5,'#253546','机身原上框')]:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.3,rounding_size=1',facecolor=col,edgecolor='none'))
 ax.text(x+w/2,y+h/2,label,color='white' if y!=25 else '#152436',fontsize=10,ha='center',va='center')
for x in [25,92]:
 ax.plot([x,x],[13,25],color='#6a8093',lw=5)
 ax.plot([x,x],[33,48],color='#6a8093',lw=3,ls='--')
for x in [32,84]:
 ax.add_patch(Rectangle((x,56),4,7,facecolor=C['blue']))
 ax.plot([x+2,x+2],[63,72],color=C['blue'],lw=1,ls='--')
for x in [43,72]:
 ax.add_patch(Rectangle((x,56),7,2.5,facecolor=C['red']))
 ax.add_patch(Rectangle((x,69),7,2.5,facecolor=C['red']))
for x in np.linspace(53,65,6): ax.plot([x,x],[56,61],color='#b08a3e',lw=2)
ax.add_patch(Rectangle((91,53),4,22,facecolor='#526c7b'))
ax.annotate('抬起拆卸',xy=(111,83),xytext=(111,61),ha='center',fontsize=10,color=C['blue'],arrowprops=dict(arrowstyle='->',color=C['blue'],lw=1.5))
ax.text(60,-1,'层间距为展示而拉开，不代表真实装配高度',fontsize=9,color=C['sub'],ha='center')
notes=[('01  固定转接架','优先复用原机孔位；至少四处承压支撑。\n若只有两处螺丝，还需止转结构；不借用舵机轴固定。'),('02  防呆定位＋限位肩','一圆定位柱、一长槽定位，避免重复约束。\n台肩承压，定位件承担横向力；触点不承担结构载荷。'),('03  磁吸＋可释放锁扣','磁铁帮助对准并保持吸合；锁扣防止走动时脱落。\n磁铁尺寸、数量与锁扣强度按头部质量再选。'),('04  弹簧触点 / Pogo Pin','建议预留六触点：GND×2、TX、RX、DET、备用。\nTX/RX交叉；DET用来识别装上/拆下，串口再握手。'),('05  维持两套独立电源','底盘电池供底盘，驾驶舱电池或充电宝供头部。\n首版触点不接电源；两边UART电平确认兼容并共地。'),('06  连接状态机','装入→稳定检测→握手→允许互动/开机动作。\n拆走或通信超时→底盘停止；头部继续作为桌宠。')]
for i,(h,t) in enumerate(notes):
 y=.80-i*.112
 fig.text(.61,y,h,fontsize=13,weight='bold',color=C['ink'])
 fig.text(.61,y-.045,t,fontsize=10,color=C['sub'],linespacing=1.6)
fig.text(.055,.065,'桌面底座复用相同机械对接形状；连接机器人后才开放机器人动作。手机托管带来的偏载需要单独检查。',fontsize=11,color=C['ink'])
fig.text(.055,.025,'R01 / 方案草图；尚未选定实物磁吸连接器，触点顺序与热插拔电路需在电气设计阶段确认。',fontsize=10,color=C['red'])
fig.savefig(ROOT/'head_body_dock_concept_R01.png',dpi=190)
fig.savefig(ROOT/'head_body_dock_concept_R01.svg')
plt.close(fig)
meta={'date':'2026-10-31','status':'dimension_reference_and_connection_proposal_only','user_confirmed_width_increase_mm':50,'side_translation_mm':25,'new_user_body_files_received':False,'source_mesh':str(meshfile.relative_to(repo)),'source_mesh_sha256':hashlib.sha256(meshfile.read_bytes()).hexdigest(),'coordinate_system':{'X':'right / width','Y':'design front / length; confirm against final electronics installation','Z':'up'},'frame_dimensions_length_width_height_mm':{p['id']:p['dimensions_mm'] for p in checks['parts']},'aperture_bbox':aperture,'original_cover_hole_center_distance_mm':spacing,'limitations':['Frame dimension reference only; excludes legs','No measured assembly height or electronics envelope','Existing STL/mesh coordinates assumed mm','Current source already EDGE50; no geometry regenerated or modified','New user body files pending','Magnet/pin/hole sizes and adapter dimensions not yet fixed'],'proposal':{'mechanism':'fixed riser adapter + guided magnetic dock + release latch','contacts':['GND','GND','TX','RX','DET','reserve'],'power':'independent; no power rail connected in first revision','detach':'stop base on detach or communication timeout'}}
(ROOT/'dimension_basis.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print('Created body dimension reference, dock concept PNG/SVG, dimension_basis.json')
print('Cover hole center distance:',spacing,'mm')
