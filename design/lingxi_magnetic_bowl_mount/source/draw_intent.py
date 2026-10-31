from pathlib import Path
import os
P=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(P/'review/cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Polygon,Circle
from matplotlib import font_manager
plt.rcParams['font.family']=font_manager.FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc').get_name()
plt.rcParams['axes.unicode_minus']=False
BG='#f2f5f8';INK='#203243';RED='#a62d40';BLUE='#2477af';GRAY='#95a7b7';GOLD='#bd964b'
f=plt.figure(figsize=(15,9.6),facecolor=BG)
f.text(.05,.94,'固定“碗底”罩座  /  R01 结构说明',fontsize=25,color=INK)
f.text(.05,.895,'已确认：两颗原机螺丝固定罩座 · 下方敞空 · 顶部嵌磁吸口 · 头部可拿走 · 不加锁扣',fontsize=12,color=INK)
a=f.add_axes([.04,.32,.56,.52]);a.set_xlim(-60,60);a.set_ylim(-9,63);a.axis('off')
# Diagram is a section intent sketch only: no dimensions implied except reference hole pitch.
a.add_patch(Rectangle((-51,-3),102,3,facecolor=GRAY))
a.add_patch(Rectangle((-19,0),38,19,facecolor='#bac5cf',ls='--',ec=GRAY))
a.text(0,12,'中央主板 / 插头 / 焊线\n包络待量',ha='center',va='center',fontsize=10,color=INK)
for s in [-1,1]:
 # Roof, skirt and bearing foot: schematic, not construction dimensions.
 a.add_patch(Polygon([(s*7,33),(s*31,33),(s*42,23),(s*42,0),(s*34,0),(s*34,3),(s*39,3),(s*39,22),(s*30,30),(s*7,30)],facecolor=INK))
 x=s*28.5020684
 a.add_patch(Rectangle((x-5,3),10,27,facecolor=BG,edgecolor=GRAY,lw=.8))
 a.add_patch(Rectangle((x-6,0),12,3,facecolor=INK))
 # Counterbore/countersink shape still TBD; display head schematically.
 a.add_patch(Rectangle((x-2.3,3),4.6,1.6,facecolor=GOLD))
 a.plot([x,x],[3,-5],color=GOLD,lw=2)
 a.annotate('',xy=(x,8),xytext=(x,27),arrowprops={'arrowstyle':'->','color':BLUE,'lw':1.2})
 a.plot([x,x],[0,-7],color=GRAY,lw=.7,ls='--')
a.add_patch(Rectangle((-11,30),22,3,facecolor=INK))
a.add_patch(Rectangle((-10,29),20,5,facecolor=GOLD,edgecolor=RED,lw=1.2))
a.plot([-4,-4],[29,26],color=GOLD,lw=1.5);a.plot([0,0],[29,26],color=GOLD,lw=1.5);a.plot([4,4],[29,26],color=GOLD,lw=1.5)
a.text(0,38,'顶面凹槽嵌入磁吸接口\n接触面朝上，焊脚朝空腔',ha='center',fontsize=10,color=RED)
a.text(-44,48,'两个深螺丝窝：从顶面下工具\n螺丝头在底部安装脚处藏平',fontsize=10,color=BLUE)
a.annotate('',xy=(-28.5,13),xytext=(-34,45),arrowprops={'arrowstyle':'->','color':BLUE})
a.annotate('',xy=(48,30),xytext=(48,0),arrowprops={'arrowstyle':'<->','color':BLUE})
a.text(51,15,'净空 H\n待量',fontsize=10,va='center',color=BLUE)
a.annotate('',xy=(-28.502,-7),xytext=(28.502,-7),arrowprops={'arrowstyle':'<->','color':BLUE})
a.text(0,-6.5,'原机孔中心距约 57.00 mm',fontsize=10,color=BLUE,ha='center',va='bottom',bbox={'facecolor':BG,'edgecolor':'none','pad':1})
f.text(.075,.305,'剖面关系示意：外形宽度、高度、壁厚尚未定尺寸；底部没有整块封板。',fontsize=10,color=INK)

b=f.add_axes([.65,.47,.30,.36]);b.set_xlim(0,100);b.set_ylim(0,78);b.axis('off')
b.text(50,73,'头部与罩座：凹凸定位＋磁吸',ha='center',fontsize=13,color=INK)
# Upper complementary shallow skirt; lower locating rim; no latch.
b.add_patch(Polygon([(12,48),(88,48),(88,23),(77,23),(77,41),(23,41),(23,23),(12,23)],facecolor=RED))
b.add_patch(Polygon([(15,9),(85,9),(85,16),(73,16),(73,30),(68,30),(68,16),(32,16),(32,30),(27,30),(27,16),(15,16)],facecolor=INK))
b.add_patch(Rectangle((40,15),20,4,facecolor=GOLD))
b.add_patch(Rectangle((40,37),20,4,facecolor=GOLD))
b.text(50,53,'可拆驾驶舱的下底面',ha='center',fontsize=10,color=RED)
b.text(50,3,'固定在机器人上的罩座',ha='center',fontsize=10,color=INK)
b.annotate('提起',xy=(95,57),xytext=(95,36),ha='center',fontsize=10,color=BLUE,arrowprops={'arrowstyle':'->','color':BLUE})
b.text(50,-7,'配合留间隙；不是零间隙硬塞或卡死',ha='center',fontsize=10,color=BLUE)

f.text(.65,.39,'磁吸口：按你给的4P尺寸图做接口参考',fontsize=12,color=INK)
f.text(.65,.35,'图示总轮廓长 19.54；另一层轮廓长 17.54。\n宽 4.00；触点间距 2.54；图示壳体高 4.00 mm。',fontsize=10,color=INK,linespacing=1.6)
f.text(.65,.285,'凹槽需分清台阶和安装耳，不能直接开紧配矩形孔。\n胶只放外壳支撑处，触点、弹簧针和配合面留净。',fontsize=10,color=INK,linespacing=1.6)
f.text(.05,.225,'电气：四触点中使用 GND / TX / RX 三根线，另一触点留空；最终先核对两端顺序。',fontsize=12,color=INK)
f.text(.05,.18,'螺丝：约10 mm只是长度信息；先确认头型，再决定锥形沉头孔或圆柱沉孔，并校核实际咬合长度。',fontsize=11,color=INK)
f.text(.05,.13,'罩座：优先罩住中央主板区，裙边给插头、出线和维护让位；实际覆盖范围与器件净空需复核。',fontsize=11,color=INK)
f.text(.05,.08,'状态：本图用于核对结构理解，不是可打印模型或加工孔位图；待高度与螺丝信息后生成CAD。',fontsize=11,color=RED)
f.text(.05,.035,'2026-10-31  /  磁吸件尺寸取自用户提供的尺寸图；机器人照片只作形态和布局参考。',fontsize=10,color='#607286')
out=P/'outputs/drawings';out.mkdir(parents=True,exist_ok=True)
f.savefig(out/'bowl_mount_intent_R01.png',dpi=180)
f.savefig(out/'bowl_mount_intent_R01.svg')
print(out/'bowl_mount_intent_R01.png')
