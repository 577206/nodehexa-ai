"""FreeCAD master: all assembly, STEP, STL and rendered geometry comes from here.

Millimetres. Script-driven parameters, no certified PCB/battery mounting dimensions.
Usage: FreeCADCmd path/to/build_cad.py
"""
import json
import math
from pathlib import Path
import FreeCAD as A
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / '01_specification/parameters.json').read_text())
DOC = A.newDocument('Lingxi_Cockpit_R03')
MANIFEST = []
COLORS = {'gray':(.26,.275,.29), 'dark':(.105,.115,.125),
          'black':(.025,.03,.035), 'orange':(.95,.22,.025),
          'glass':(.20,.16,.12), 'light':(1.0,.36,.025),
          'metal':(.62,.63,.64), 'gold':(.85,.56,.16)}

def v(*p): return A.Vector(*[float(a) for a in p])
def box(x,y,z,dx,dy,dz): return Part.makeBox(dx,dy,dz,v(x,y,z))
def cyl(x,y,z,r,h,axis=(0,0,1)): return Part.makeCylinder(r,h,v(x,y,z),v(*axis))
def poly(points, direction):
    pp=[v(*a) for a in points]
    return Part.Face(Part.makePolygon(pp+[pp[0]])).extrude(v(*direction))
def xz(points, y, thick): return poly([(x,y,z) for x,z in points],(0,thick,0))
def yz(points, x, thick): return poly([(x,y,z) for y,z in points],(thick,0,0))
def xy(points, z, thick): return poly([(x,y,z) for x,y in points],(0,0,thick))
def octwire(hx,yf,yr,c,z):
    pp=[(-hx+c,yf),(hx-c,yf),(hx,yf+c),(hx,yr-c),
        (hx-c,yr),(-hx+c,yr),(-hx,yr-c),(-hx,yf+c)]
    q=[v(x,y,z) for x,y in pp]
    return Part.makePolygon(q+[q[0]])
def loft(levels): return Part.makeLoft([octwire(*p) for p in levels], True, True)
def profile_at(z):
    rows=P['profiles']
    for a,b in zip(rows,rows[1:]):
        if a[4]<=z<=b[4]:
            t=(z-a[4])/(b[4]-a[4])
            return [a[i]+t*(b[i]-a[i]) for i in range(4)]+[z]
    raise ValueError(z)
def inset(row,d):
    hx,yf,yr,c,z=row
    return [hx-d,yf+d,yr-d,max(c-d*.55,1),z]
def fuse(*shapes):
    s=shapes[0]
    for p in shapes[1:]: s=s.fuse(p)
    return s.removeSplitter()
def move(shape, origin=(0,0,0), angle=0):
    s=shape.copy()
    if angle:s.rotate(v(0,0,0),v(0,0,1),angle)
    s.translate(v(*origin));return s
def mirrored(shape):
    m=A.Matrix();m.A11=-1
    return shape.transformGeometry(m)
def round_edges(s,r=.5):
    try:
        q=s.makeFillet(r,s.Edges)
        if q.isValid(): return q
    except Exception:pass
    return s
def part(pid,slug,title,shape,color,category='fdm',notes='',print_axis=None):
    shape=shape.removeSplitter()
    if shape.isNull() or not shape.isValid() or shape.Volume<.01:
        raise RuntimeError(f'{pid}: invalid solid')
    if len(shape.Solids)!=1:
        raise RuntimeError(f'{pid}: {len(shape.Solids)} disconnected solids')
    folder=ROOT/'02_parts'/f'{pid}_{slug}'
    folder.mkdir(parents=True,exist_ok=True)
    ob=DOC.addObject('PartDesign::Feature',pid)
    ob.Label=f'{pid} | {title}'
    ob.Shape=shape
    ob.addProperty('App::PropertyString','PartId','Identity');ob.PartId=pid
    ob.addProperty('App::PropertyString','Manufacturing','Identity');ob.Manufacturing=category
    ob.addProperty('App::PropertyColor','RenderColor','Identity');ob.RenderColor=COLORS[color]
    if ob.ViewObject:
        ob.ViewObject.ShapeColor=COLORS[color]
        if color=='glass':ob.ViewObject.Transparency=65
    # Part FCStd retains assembly coordinates and identity.
    pd=A.newDocument('Part_'+pid)
    po=pd.addObject('PartDesign::Feature',pid);po.Shape=shape;po.Label=ob.Label
    po.addProperty('App::PropertyString','Manufacturing');po.Manufacturing=category
    if po.ViewObject:po.ViewObject.ShapeColor=COLORS[color]
    pd.recompute();pd.saveAs(str(folder/f'{pid}.FCStd'));A.closeDocument(pd.Name)
    shape.exportStep(str(folder/f'{pid}.step'))
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.10,AngularDeflection=.14,Relative=False)
    mesh.write(str(folder/f'{pid}_assembly.stl'))
    printable=shape.copy()
    if print_axis:
        axis,degrees=print_axis
        printable.rotate(v(0,0,0),v(*axis),degrees)
    bb=printable.BoundBox
    printable.translate(v(-(bb.XMin+bb.XMax)/2,-(bb.YMin+bb.YMax)/2,-bb.ZMin))
    MeshPart.meshFromShape(Shape=printable,LinearDeflection=.10,AngularDeflection=.14,Relative=False).write(str(folder/f'{pid}_print.stl'))
    bb=shape.BoundBox
    entry={'id':pid,'slug':slug,'title':title,'category':category,'material':color,
           'folder':str(folder.relative_to(ROOT)),'stl':str((folder/f'{pid}_assembly.stl').relative_to(ROOT)),
           'volume_mm3':round(shape.Volume,3),'size_mm':[round(bb.XLength,3),round(bb.YLength,3),round(bb.ZLength,3)],
           'valid':shape.isValid(),'solids':len(shape.Solids),'notes':notes,'print_axis':print_axis}
    (folder/'part.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
    MANIFEST.append(entry)
    print('PART',pid,entry['size_mm'],flush=True)
    return ob

# Structural shell: deliberately faceted, narrow crown, broad shoulders and chin.
levels=P['profiles']
outer=loft(levels)
inside=[]
for i,row in enumerate(levels):
    q=inset(row,P['wall'])
    if i==0:q[4]+=P['wall']
    if i==len(levels)-1:q[4]-=P['wall']
    inside.append(q)
hollow=outer.cut(loft(inside))
zseam=P['seam_z']
lower=hollow.common(box(-100,-100,0,200,200,zseam))
upper=hollow.common(box(-100,-100,zseam,200,200,100))

# The registration tongue overlaps the actual wall; no floating ring or posts.
p=profile_at(zseam)
def level_at(row,z):return row[:4]+[z]
lpout=inset(p,2.0);lpin=inset(p,4.3)
lip=loft([level_at(lpout,zseam-1.5),level_at(lpout,zseam+3)])
lip=lip.cut(loft([level_at(lpin,zseam-2),level_at(lpin,zseam+3.5)]))
lower=lower.fuse(lip)
clear=inset(p,2.0-P['fit_clearance'])
upper=upper.cut(loft([level_at(clear,zseam-.1),level_at(clear,zseam+3.4)]))

# Four bottom-access M3 fasteners. The upper receiver has connected side ribs.
for x in (-35,35):
    for y in (-20,20):
        boss=cyl(x,y,7.1,4.6,zseam-7.1)
        lower=lower.fuse(boss)
        lower=lower.cut(cyl(x,y,4.8,1.7,zseam+1))
        lower=lower.cut(cyl(x,y,4.8,3.2,3.2))
        rib=box(35 if x>0 else -54,y-2,zseam,19,4,8)
        receiver=fuse(cyl(x,y,zseam,4.6,9),rib).common(outer)
        upper=upper.fuse(receiver)
        upper=upper.cut(cyl(x,y,zseam-.1,2.1,4.6))
        upper=upper.cut(cyl(x,y,zseam-.1,1.65,10))

# Receiver ribs must also respect the tongue clearance after being fused in.
groove_outer=loft([level_at(clear,zseam-.1),level_at(clear,zseam+3.4)])
groove_inner=inset(p,4.3+P['fit_clearance'])
groove_inner=loft([level_at(groove_inner,zseam-.2),level_at(groove_inner,zseam+3.5)])
upper=upper.cut(groove_outer.cut(groove_inner))

# Open front window. The two transparent facets and their frame are independent.
window_outline=[(-25,32),(25,32),(32,58),(22,80),(-22,80),(-32,58)]
upper=upper.cut(xz(window_outline,-70,65))
lower=lower.cut(cyl(0,-60,18,5.7,30,(0,1,0)))
for sign in (-1,1):
    for x in (17,20.5,24):
        for z in (14,17.5,21):
            lower=lower.cut(cyl(sign*x,-60,z,1.1,25,(0,1,0)))

# Dock contact cassette and magnet pockets. Board-to-robot mount pitch unknown.
lower=lower.cut(box(-18,-11,4,36,22,5))
for x in (-23,23):lower=lower.cut(cyl(x,0,4.8,1.15,5))
for x in (-31,31):
    for y in (-20,20):lower=lower.cut(cyl(x,y,4.9,3.1,2.4))

# Orange upper armor pin seats. Cosmetic parts are fitted separately by color.
for sign in (-1,1):
    for y,z in ((-18,72),(15,69)):
        upper=upper.cut(cyl(sign*29,y,z,1.65,15,(sign,0,0)))

lo=part('P01','lower_shell','下壳／电池仓',lower,'dark',notes='M3 底部螺钉孔、四磁铁袋、接触盒开口；电池压板未定尺寸。')
up=part('P02','upper_shell','上壳／斜面舱体',upper,'gray',notes='接收 M3 嵌件与定位唇；PCB 安装孔待实测。',print_axis=((1,0,0),180))

# Window facets: two planar sheets make the visual canopy manufacturable.
def glass_y(z):
    return -49+(z-33)*(13/26) if z<=59 else -36+(z-59)*(20/21)
def pane(coords,depth=1.0,back=0):
    return poly([(x,glass_y(z)+back,z) for x,z in coords],(0,depth,0))
bottomcoords=[(-26,33),(26,33),(31,59),(-31,59)]
topcoords=[(-31,59),(31,59),(22,80),(-22,80)]
part('P03','lower_visor','透明舱盖下片',pane(bottomcoords),'glass','clear_sheet',
     '平面透明片模板；厚度占位 1 mm，可按轮廓裁片；视线在镜片下方。',((1,0,0),-63.435))
part('P04','upper_visor','透明舱盖上片',pane(topcoords),'glass','clear_sheet',
     '与下片构成折面，优先透明 PET 裁片，边缘用可拆压框固定。',((1,0,0),-46.397))
frame_bottom=pane([(-29,30),(29,30),(34,59.2),(-34,59.2)],2,1)
frame_bottom=frame_bottom.cut(pane([(-25,34),(25,34),(30,57),(-30,57)],4,0))
frame_top=pane([(-34,59),(34,59),(24,82),(-24,82)],2,1)
frame_top=frame_top.cut(pane([(-30,61),(30,61),(21,78.5),(-21,78.5)],4,0))
frame=fuse(frame_bottom,frame_top)
part('P05','canopy_frame','折面舱盖压框',frame,'dark',notes='两片玻璃的承托边；细螺钉压条细节待薄片厚度确认。')

# Light guide carriers and two swept amber slits, all behind the transparent pane.
carrier=pane([(-27,35),(27,35),(29,48),(-29,48)],2.2,3.6)
for x in (-20,20):carrier=carrier.cut(cyl(x,-50,42,1.8,20,(0,1,0)))
part('P06','eye_carrier','双眼灯板承托',carrier,'black',notes='承托面已建；LED PCB 规格未定。')
for sign,ident in ((-1,'P07'),(1,'P08')):
    coords=[(sign*8,38.5),(sign*26,44.5),(sign*26,42.6),(sign*8,36.7)]
    part(ident,'eye_lightguide_'+('L' if sign<0 else 'R'),'眼睛导光件',pane(coords,.8,2),'light','translucent',
         '乳白透光件，LED 发光是渲染表示，非自带电路。')

# Orange angular exoskeleton shoulder, rectangular-section armor, not round bars.
shoulder=[(-30,53),(-26,70),(-14,83),(12,81),(25,66),(22,59),
          (17,63),(9,74),(-12,76),(-19,66),(-22,52)]
right_rib=yz(shoulder,33,6)
for y,z in ((-18,72),(15,69)):
    right_rib=right_rib.fuse(cyl(29,y,z,1.4,5,(1,0,0)))
part('P09','orange_shoulder_R','右橙色肩部护架',right_rib,'orange',notes='两根定位销；后续按外壳接触区域微调。',print_axis=((0,1,0),90))
part('P10','orange_shoulder_L','左橙色肩部护架',mirrored(right_rib),'orange',print_axis=((0,1,0),-90))

# Layered mechanical outer straps, separate gray printed armor.
strap=[(-28,52),(-21,70),(-9,79),(12,77),(23,62),(21,57),
       (16,63),(8,72),(-7,73),(-16,65),(-22,50)]
rs=yz(strap,40,3.2)
for y,z in ((-13,71),(14,68)):rs=rs.cut(cyl(39,y,z,1.7,6,(1,0,0)))
part('P11','outer_strap_R','右外侧装甲压条',rs,'dark',print_axis=((0,1,0),90))
part('P12','outer_strap_L','左外侧装甲压条',mirrored(rs),'dark',print_axis=((0,1,0),-90))

# Front corner vent modules, angled away from center to follow faceted cheeks.
ventout=[(-12,-17),(8,-17),(13,-7),(12,10),(3,18),(-8,15)]
ventin=[(-8,-13),(5,-13),(9,-6),(8,8),(2,13),(-5,11)]
ventframe=xz(ventout,0,3).cut(xz(ventin,-1,5))
grille=xz(ventin,2.8,1.2)
# Real open slots through lower area, connected by the perimeter.
for z in (-10,-5,0):grille=grille.cut(box(-6,2,z,13,3,2.4))
orangeedge=xz([(9,-15),(12,-8),(11,9),(3,17),(1,14),(8,7),(8,-8),(6,-14)],-.8,1.7)
# Diagonal fins attached to orange top border, all part of one printed insert.
for x in (-5,-1,3):
    fin=xz([(x,12),(x+1.5,12),(x+4,3),(x+2.5,3)],-.8,1.7)
    orangeedge=orangeedge.fuse(fin)
orangeedge=orangeedge.fuse(xz([(-6,12),(4,16),(5,13),(-5,10)],-.8,1.7))
for sign,baseid in ((1,13),(-1,16)):
    angle=sign*29
    origin=(sign*42,-47,31)
    def vent_world(s):
        if sign<0:s=mirrored(s)
        return move(s,origin,angle)
    suffix='R' if sign>0 else 'L'
    part(f'P{baseid:02}','vent_frame_'+suffix,'侧前格栅装甲框 '+suffix,vent_world(ventframe),'gray',notes='模块独立，内侧固定耳尚需与实际声学器件位置协调。')
    part(f'P{baseid+1:02}','vent_grille_'+suffix,'黑色百叶窗 '+suffix,vent_world(grille),'black')
    part(f'P{baseid+2:02}','vent_trim_'+suffix,'橙色鳍片饰件 '+suffix,vent_world(orangeedge),'orange')

# Faceted square camera frame, with a real through hole and M2 side tabs.
cam=xz([(-9,8),(9,8),(12,11),(12,25),(9,28),(-9,28),(-12,25),(-12,11)],-51,5)
cam=cam.cut(cyl(0,-52,18,5.8,8,(0,1,0)))
for x in (-9,9):cam=cam.cut(cyl(x,-52,18,1.1,8,(0,1,0)))
part('P19','camera_bezel','橙色前摄像头框',cam,'orange',notes='11.6 mm 光孔和 M2 孔为待校准尺寸。',print_axis=((1,0,0),90))
cam_in=cyl(0,-52.5,18,5.3,2,(0,1,0)).cut(cyl(0,-53,18,3.8,3,(0,1,0)))
part('P20','camera_retainer','镜头装饰压环',cam_in,'black',print_axis=((1,0,0),90))

# Side circular housings layered over trapezoid plates.
sidepoly=[(-16,25),(23,28),(29,40),(24,55),(1,61),(-17,50),(-20,35)]
side=yz(sidepoly,49,3)
side=side.cut(cyl(48,12,43,1.7,6,(1,0,0)))
for sign,pid in ((1,21),(-1,22)):
    part(f'P{pid}','side_armor_'+('R' if sign>0 else 'L'),'侧面层叠装甲',side if sign>0 else mirrored(side),'gray',print_axis=((0,1,0),sign*90))
hinge=cyl(52,12,43,11.5,3,(1,0,0)).cut(cyl(51,12,43,1.7,5,(1,0,0)))
trim=cyl(55,12,43,9.7,1.6,(1,0,0)).cut(cyl(54.8,12,43,7.8,2,(1,0,0)))
for sign,pid in ((1,23),(-1,25)):
    suffix='R' if sign>0 else 'L'
    part(f'P{pid}','hinge_disc_'+suffix,'侧圆形轴盖 '+suffix,hinge if sign>0 else mirrored(hinge),'dark',print_axis=((0,1,0),sign*90))
    part(f'P{pid+1}','hinge_ring_'+suffix,'侧轴橙色圈 '+suffix,trim if sign>0 else mirrored(trim),'orange',print_axis=((0,1,0),sign*90))

# Top service plate and black inset. This is a removable decorative roof panel.
roof=xy([(-19,-9),(19,-9),(24,-2),(21,15),(15,19),(-15,19),(-21,15),(-24,-2)],83,2.4)
for x in (-16,16):
    for y in (-3,12):roof=roof.cut(cyl(x,y,82,1.15,5))
part('P27','roof_panel','顶部检修装饰板',roof,'dark')
insetplate=xy([(-12,1),(12,1),(10,12),(-10,12)],85.4,.8)
part('P28','roof_inset','顶部黑色嵌片',insetplate,'black')

# Separate side utility panels and shoulder intakes add the reference's layered
# armor depth. Every decoration remains a separate, closed CAD solid.
utility=yz([(-16,28),(4,27),(7,34),(2,38),(-16,39)],52,2.2)
for yy in (-11,1):utility=utility.cut(cyl(51,yy,33,1.2,5,(1,0,0)))
part('P40','side_utility_R','右侧黑色检修面板',utility,'black',print_axis=((0,1,0),90))
part('P41','side_utility_L','左侧黑色检修面板',mirrored(utility),'black',print_axis=((0,1,0),-90))
intake=yz([(12,66),(23,60),(29,69),(24,79),(16,82),(10,77)],39,5)
for yy in (16,20,24):
    intake=intake.cut(box(41.5,yy,67,4,1.5,8))
part('P42','shoulder_intake_R','右肩橙色通风罩',intake,'orange',print_axis=((0,1,0),90))
part('P43','shoulder_intake_L','左肩橙色通风罩',mirrored(intake),'orange',print_axis=((0,1,0),-90))

# Rear phone cradle: two flat printable uprights and one shelf; bolts/slots.
upright=yz([(39,31),(46,30),(59,106),(56,112),(50,111)],32,5)
upright=upright.common(box(20,30,34,30,40,100))
upright=upright.fuse(box(30,39,34,9,10,8))
upright=upright.cut(cyl(34.5,44,33.9,1.7,9))
upright=upright.cut(cyl(34.5,44,37,2.1,6))
upright=upright.cut(cyl(31,53,98,1.6,7,(1,0,0)))
for sign,pid in ((1,29),(-1,30)):
    part(f'P{pid}','phone_upright_'+('R' if sign>0 else 'L'),'手机支架侧臂',upright if sign>0 else mirrored(upright),'dark',notes='仅保留手机定位宽度；手机实物尺寸与重心待验证。',print_axis=((0,1,0),sign*90))
shelf=fuse(box(-40,39,30,80,16,4),box(-40,50,31,80,5,8))
for x in (-34.5,34.5):shelf=shelf.cut(cyl(x,44,29.9,1.7,6))
part('P31','phone_shelf','手机托架底托',shelf,'dark')
grip=round_edges(box(29,51,72,5,5,36),.8)
part('P32','phone_grip_R','右橙色手机挡条',grip,'orange')
part('P33','phone_grip_L','左橙色手机挡条',mirrored(grip),'orange')

# Replaceable underside docking cassette, independent of shell and feet.
dock=box(-20,-13,3,40,26,2)
dock=fuse(dock,box(-25,-4,3,50,8,2))
for x in (-23,23):dock=dock.cut(cyl(x,0,2.9,1.15,3))
for x in (-7.5,-2.5,2.5,7.5):dock=dock.cut(cyl(x,0,2.9,1.0,3))
part('P34','dock_cassette','四触点底部接触盒',dock,'black',notes='触点和磁铁是外购件；机器人侧孔距未确认。')

# Separate tabletop cradle, the body seats on this, not on the moving robot.
base=loft([(39,-28,29,8,-.5),(41,-30,31,8,4.5)])
base=base.cut(loft([(34,-23,24,6,-1),(34,-23,24,6,5)]))
for x in (-31,31):
    for y in (-20,20):
        # Integrated pads connect to the ring, providing a continuous solid.
        base=base.fuse(cyl(x,y,-.5,5.5,5))
        base=base.cut(cyl(x,y,2.3,3.1,3))
for x in (-36,36):
    for y in (-24,24):base=base.cut(cyl(x,y,-1,1.7,7))
part('P35','desktop_cradle','独立桌面磁吸底座框',base,'dark')
foot_shape=yz([(-23,-.5),(-29,-.5),(-44,-10),(-43,-14),(-29,-14),(-20,-2)],-7,14)
foot_shape=foot_shape.cut(cyl(0,-24,-2,1.7,8))
for signx,signy,pid in ((1,1,36),(-1,1,37),(1,-1,38),(-1,-1,39)):
    foot=foot_shape.copy()
    if signy<0:
        m=A.Matrix();m.A22=-1;foot=foot.transformGeometry(m)
    foot.translate(v(signx*36,0,0))
    part(f'P{pid}','desktop_foot_'+str(pid-35),'桌面底座脚 '+str(pid-35),foot,'dark',notes='上方 M3 固定孔与底座框对应。',print_axis=((0,1,0),90))

# Hardware envelopes are reference-only, never included in FDM release list.
part('H01','camera_lens','镜头外观占位',cyl(0,-54,18,3.7,2,(0,1,0)),'glass','hardware','BF3901 镜头尺寸待量；仅用于检查光孔。')
for x,y,idx in [(-31,-20,2),(31,-20,3),(-31,20,4),(31,20,5)]:
    part(f'H{idx:02}','magnet_'+str(idx-1),'磁铁占位',cyl(x,y,5,3,2.0),'metal','hardware')
for i,x in enumerate((-7.5,-2.5,2.5,7.5),6):
    part(f'H{i:02}','pogo_'+str(i-5),'信号触点占位',cyl(x,0,4.6,.8,3),'gold','hardware')

def bolt_head(center,axis=(0,0,1),r=2):
    # Recessed hex socket, visual envelope only, hardware must be purchased.
    a=v(*axis);origin=v(*center)
    s=Part.makeCylinder(r,1.35,origin,a)
    q=cyl(0,0,.45,.85,1.1)
    q.rotate(v(0,0,0),v(0,0,1),30)
    rot=A.Rotation(v(0,0,1),a)
    q.Placement=A.Placement(origin,rot)
    return s.cut(q)
num=10
for x in (-16,16):
    for y in (-3,12):
        part(f'H{num:02}','roof_screw_'+str(num),'顶部螺钉头占位',bolt_head((x,y,85.4),r=1.8),'black','hardware');num+=1
for sign in (-1,1):
    for yy,zz in ((-13,71),(14,68),(-11,33),(1,33),(12,43)):
        xx=43.2 if zz>60 else (54.2 if zz<40 else 55.2)
        part(f'H{num:02}','side_screw_'+str(num),'侧部螺钉头占位',bolt_head((sign*xx,yy,zz),(sign,0,0),1.8),'black','hardware');num+=1

def revise(pid,shape):
    """Re-export a modified interface from the same CAD source of truth."""
    shape=shape.removeSplitter()
    if not shape.isValid() or len(shape.Solids)!=1:
        for i,s in enumerate(shape.Solids):
            b=s.BoundBox
            print('FRAGMENT',pid,i,round(s.Volume,3),(round(b.XMin,1),round(b.XMax,1),round(b.YMin,1),round(b.YMax,1),round(b.ZMin,1),round(b.ZMax,1)),flush=True)
        raise RuntimeError(f'{pid}: invalid revised interface / {len(shape.Solids)} solids')
    ob=DOC.getObject(pid);ob.Shape=shape
    entry=next(e for e in MANIFEST if e['id']==pid)
    folder=ROOT/entry['folder']
    pd=A.newDocument('Rev_'+pid);po=pd.addObject('PartDesign::Feature',pid)
    po.Shape=shape;po.Label=ob.Label
    pd.recompute();pd.saveAs(str(folder/f'{pid}.FCStd'));A.closeDocument(pd.Name)
    shape.exportStep(str(folder/f'{pid}.step'))
    MeshPart.meshFromShape(Shape=shape,LinearDeflection=.10,AngularDeflection=.14,Relative=False).write(str(folder/f'{pid}_assembly.stl'))
    ss=shape.copy()
    if entry['print_axis']:ss.rotate(v(0,0,0),v(*entry['print_axis'][0]),entry['print_axis'][1])
    bb=ss.BoundBox;ss.translate(v(-(bb.XMin+bb.XMax)/2,-(bb.YMin+bb.YMax)/2,-bb.ZMin))
    MeshPart.meshFromShape(Shape=ss,LinearDeflection=.10,AngularDeflection=.14,Relative=False).write(str(folder/f'{pid}_print.stl'))
    bb=shape.BoundBox
    entry.update(volume_mm3=round(shape.Volume,3),size_mm=[round(bb.XLength,3),round(bb.YLength,3),round(bb.ZLength,3)])
    (folder/'part.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')

# Exact mating recesses remove rigid intersections. Their production clearance,
# retention strength and assembly direction still require physical fit coupons.
for base,insert in [('P29','P32'),('P30','P33'),('P13','P15'),('P16','P18'),
                    ('P42','P11'),('P43','P12'),('P40','P23'),('P41','P25')]:
    revise(base,DOC.getObject(base).Shape.cut(DOC.getObject(insert).Shape))
for pid in ('P01','P02'):
    shell=DOC.getObject(pid).Shape
    for other in ['P05','P06','P09','P10','P11','P12','P14','P17',
                  'P21','P22','P23','P25','P29','P30','P31','P40','P41','P42','P43']:
        shell=shell.cut(DOC.getObject(other).Shape)
    revise(pid,shell)

DOC.recompute()
DOC.addObject('App::FeaturePython','DesignStatus').addProperty('App::PropertyString','Status')
DOC.DesignStatus.Status='视觉与装配样机，未完成实物安装验证；参见 README'
DOC.saveAs(str(ROOT/'03_assembly/Lingxi_Cockpit_R03.FCStd'))
Part.export([ob for ob in DOC.Objects if hasattr(ob,'Shape')],str(ROOT/'03_assembly/Lingxi_Cockpit_R03.step'))
result={'revision':'R03','units':'mm','source':'06_tools/build_cad.py','parts':MANIFEST,
        'all_valid':all(a['valid'] and a['solids']==1 for a in MANIFEST),
        'status':'PROTOTYPE_NOT_RELEASED','shell_common_volume_mm3':round(lo.Shape.common(up.Shape).Volume,6)}
(ROOT/'03_assembly/manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
if result['shell_common_volume_mm3']>.01:
    raise RuntimeError('Upper/lower shell interference: '+str(result['shell_common_volume_mm3']))
print('BUILD_COMPLETE',len(MANIFEST),'parts; shell overlap',result['shell_common_volume_mm3'],flush=True)
