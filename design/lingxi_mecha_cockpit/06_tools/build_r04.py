"""R04: user's marked-up silhouette, multi-facet canopy and side vents.
FreeCAD solid authoring. Millimetres; unmeasured appearance / separation review.
R03 stays immutable. No release STEP or printing package is produced here.
"""
import json,math
from pathlib import Path
import FreeCAD as A
import Part,MeshPart
ROOT=Path(__file__).resolve().parents[1]
REV='R04'; OUT=ROOT/'02_parts'/REV; ASSEMBLY=ROOT/'03_assembly'
DOC=A.newDocument('Lingxi_Cockpit_'+REV); MAN=[]
C={'gray':(.25,.265,.28),'dark':(.09,.10,.115),'black':(.025,.03,.035),'orange':(.95,.19,.02),'glass':(.25,.18,.12),'light':(1.0,.32,.015),'metal':(.62,.64,.66),'gold':(.85,.56,.16)}
def V(*p):return A.Vector(*map(float,p))
def box(x,y,z,dx,dy,dz):return Part.makeBox(dx,dy,dz,V(x,y,z))
def cyl(x,y,z,r,h,ax=(0,0,1)):return Part.makeCylinder(r,h,V(x,y,z),V(*ax))
def poly(pp,vec):
    vv=[V(*p) for p in pp];return Part.Face(Part.makePolygon(vv+[vv[0]])).extrude(V(*vec))
def xy(pp,z,t):return poly([(x,y,z) for x,y in pp],(0,0,t))
def yz(pp,x,t):return poly([(x,y,z) for y,z in pp],(t,0,0))
def xz(pp,y,t):return poly([(x,y,z) for x,z in pp],(0,t,0))
def inset_quad(points,d=.16):
    # Offset every edge in the pane's own plane; do not shrink in world X/Z.
    vv=[V(*p) for p in points];origin=vv[0]
    u=vv[1]-origin;u.normalize();n=(vv[1]-origin).cross(vv[2]-origin);n.normalize();v=n.cross(u)
    q=[((p-origin).dot(u),(p-origin).dot(v)) for p in vv]
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1]));sgn=1 if area>0 else -1
    lines=[]
    for a,b in zip(q,q[1:]+q[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];ll=math.hypot(dx,dy)
        lines.append(((a[0]-sgn*dy*d/ll,a[1]+sgn*dx*d/ll),(dx,dy)))
    out=[]
    for i,(b,s) in enumerate(lines):
        a,r=lines[i-1];den=r[0]*s[1]-r[1]*s[0]
        t=((b[0]-a[0])*s[1]-(b[1]-a[1])*s[0])/den
        p=origin+u*(a[0]+t*r[0])+v*(a[1]+t*r[1]);out.append((p.x,p.y,p.z))
    return out
def fuse(*ss):
    s=ss[0]
    for q in ss[1:]:s=s.fuse(q)
    return s.removeSplitter()
def mirror(s):
    return s.mirror(V(0,0,0),V(1,0,0))
def trans(s,vec):q=s.copy();q.translate(V(*vec));return q
def octwire(row):
    h,f,r,c,z=row;pp=[(-h+c,f),(h-c,f),(h,f+c),(h,r-c),(h-c,r),(-h+c,r),(-h,r-c),(-h,f+c)]
    vv=[V(x,y,z) for x,y in pp];return Part.makePolygon(vv+[vv[0]])
def loft(rows):return Part.makeLoft([octwire(r) for r in rows],True,True)
def part(pid,slug,title,s,color,cat='fdm',group='cockpit',note=''):
    s=s.removeSplitter()
    edge_break=0
    # Physical edge breaks in the solid model, not a Blender-only modifier.
    # Do not dress mating lips, thin clear sheets or the master shell here.
    dressed={'P12','P13','P14','P17','P20','P21','P22','P23','P38','P39','P40','P42','P43','P45','P46','P47','P48','P49','P51'}
    if pid in dressed:
        for size in (.45,.25):
            try:
                candidate=s.makeChamfer(size,s.Edges)
                if candidate.isValid() and len(candidate.Solids)==1 and candidate.Volume>0:
                    s=candidate;edge_break=size;break
            except Exception:pass
        print('EDGE_BREAK',pid,edge_break,flush=True)
    if s.isNull() or not s.isValid() or len(s.Solids)!=1 or s.Volume<=0:raise RuntimeError(f'{pid}: valid={s.isValid()} solids={len(s.Solids)}')
    ob=DOC.addObject('PartDesign::Feature',pid);ob.Shape=s;ob.Label=f'{pid} | {title}'
    for k,val in [('PartId',pid),('Category',cat),('GroupName',group),('Status','unmeasured_review_prototype')]:ob.addProperty('App::PropertyString',k,'Identity');setattr(ob,k,val)
    ob.addProperty('App::PropertyColor','RenderColor','Identity');ob.RenderColor=C[color]
    ob.addProperty('App::PropertyInteger','ReviewTransparency','Identity');ob.ReviewTransparency=65 if color=='glass' else 0
    if ob.ViewObject:ob.ViewObject.ShapeColor=C[color];ob.ViewObject.Transparency=ob.ReviewTransparency
    folder=OUT/(pid+'_'+slug);folder.mkdir(parents=True,exist_ok=True)
    pd=A.newDocument('Export_'+pid);po=pd.addObject('PartDesign::Feature',pid);po.Shape=s;po.Label=ob.Label
    pd.recompute();pd.saveAs(str(folder/(pid+'.FCStd')));A.closeDocument(pd.Name)
    MeshPart.meshFromShape(Shape=s,LinearDeflection=.065,AngularDeflection=.12,Relative=False).write(str(folder/(pid+'_review.stl')))
    b=s.BoundBox
    entry={'id':pid,'slug':slug,'title':title,'category':cat,'group':group,'material':color,'folder':str(folder.relative_to(ROOT)),'stl':str((folder/(pid+'_review.stl')).relative_to(ROOT)),'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':round(s.Volume,3),'size_mm':[round(b.XLength,3),round(b.YLength,3),round(b.ZLength,3)],'edge_break_mm':edge_break,'notes':note}
    MAN.append(entry);(folder/'part.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n');print('PART',pid,flush=True);return ob
# Source profile: narrower crown, long swept front, taper underneath.
rows=[[39,-35,38,14,6],[49,-48,43,16,14],[54,-50,43,15,32],[52,-43,38,15,50],[44,-31,34,12,66],[33,-14,27,9,80],[28,-7,24,7,84]]
inside=[[h-2.6,f+2.6,r-2.6,c-1.3,z+(2.6 if i==0 else -2.6 if i==len(rows)-1 else 0)] for i,(h,f,r,c,z) in enumerate(rows)]
outer=loft(rows);hollow=outer.cut(loft(inside))
# Five stations form four different slope zones, with two wraparound side facets each.
stations=[(28,-53,24),(36,-53,29),(55,-44,31),(72,-28,25),(81,-15,20)]
outline=[(-w-1,z-.2) for z,y,w in stations]+[(w+1,z-.2) for z,y,w in reversed(stations)]
hollow=hollow.cut(xz(outline,-70,67))
hollow=hollow.cut(cyl(0,-61,17,6,27,(0,1,0)))
for side in (-1,1):
    for xx in (17.5,21,24.5):
        for zz in (13,16.5,20,23.5):hollow=hollow.cut(cyl(side*xx,-59,zz,1.05,20,(0,1,0)))
lower=hollow.common(box(-90,-90,0,180,180,27));upper=hollow.common(box(-90,-90,27,180,180,100))
# Genuine separate shell halves. Fit lip retained for a subsequent fit-calibration pass.
# Shells are exported after cutting the actual side vent openings.

# Faceted panes: each quadrilateral is planar and individually removable.
facets=[]
for j,((z0,y0,w0),(z1,y1,w1)) in enumerate(zip(stations,stations[1:])):
    panels=[('C',[(-w0+7,y0,z0),(w0-7,y0,z0),(w1-7,y1,z1),(-w1+7,y1,z1)]),
            ('R',[(w0-7,y0,z0),(w0,y0+7,z0),(w1,y1+7,z1),(w1-7,y1,z1)]),
            ('L',[(-w0,y0+7,z0),(-w0+7,y0,z0),(-w1+7,y1,z1),(-w1,y1+7,z1)])]
    for k,(suffix,pts) in enumerate(panels):
        pid=f'G{j*3+k+1:02}';part(pid,'visor_'+str(j+1)+suffix,'舱罩折面 '+str(j+1)+suffix,poly(inset_quad(pts),(0,1,0)),'glass','clear_sheet',note='每边退让0.16mm，片间名义缝0.32mm；待裁片装配试验。');facets.append(pts)
# Perimeter frame follows all four longitudinal changes (not a flat screen bezel).
frameparts=[]
for (z0,y0,w0),(z1,y1,w1) in zip(stations,stations[1:]):
    for sign in (-1,1):
        pp=[(sign*(w0-.6),y0+6.5,z0),(sign*(w0+3.5),y0+6.5,z0),(sign*(w1+3.5),y1+6.5,z1),(sign*(w1-.6),y1+6.5,z1)]
        frameparts.append(poly(pp,(0,3.8,0)))
for idx in (0,-1):
    z,y,w=stations[idx];frameparts.append(box(-w-3.5,y+6.5,z-1.2,2*w+7,3.8,2.4))
# Connecting undercut rails at the lower and upper ends span the side-pane depth.
for z,y,w in (stations[0],stations[-1]):
    frameparts.append(box(-w+6.5,y+1,z-.7,2*(w-6.5),9.3,1.4))
# Thin physical seam bars on the inner side of the three horizontal folds.
for z,y,w in stations[1:-1]:
    frameparts.append(box(-w+6.7,y+1.12,z-.38,2*(w-6.7),.8,.76))
    for sg in (-1,1):
        frameparts.append(poly([(sg*(w-7.2),y+1,z-.38),(sg*(w+.2),y+8.4,z-.38),(sg*(w+.2),y+8.4,z+.38),(sg*(w-7.2),y+1,z+.38)],(0,.85,0)))
frame=fuse(*frameparts)
part('P03','canopy_frame','多折面舱罩承托框',frame,'dark',note='外侧窄压框及片间接缝；独立透明薄片需要实物固定验证。')
# Small bronze seam carriers behind each horizontal break; subtle mechanical canopy fasteners.
for j,(z,y,w) in enumerate(stations[1:-1],1):
    part(f'P{3+j:02}','visor_joiner_'+str(j),'舱罩内接缝扣 '+str(j),box(-4,y+1.1,z-.9,8,2,1.8),'dark')
# Lower face behind glass, LED slit inserts: use actual extruded CAD solids.
carrier=xz([(-26,29),(26,29),(29,44),(-29,44)],-47.7,2.2)
part('P07','eye_carrier','灯眼内托板',carrier,'black')
for sign,pid in ((-1,'P08'),(1,'P09')):
    pp=[(sign*8,33.5),(sign*25,40),(sign*25,37.8),(sign*8,31.4)]
    # Surface y=-53 at z36, then slopes back above it.
    pts=[(x,-52+(max(z-36,0)*9/19),z) for x,z in pp]
    # One planar lamp plate; taper represented by straight sloping silhouette.
    pts=[(x,-47.9,z) for x,z in pp]
    part(pid,'eye_lightguide_'+str(sign),'斜向眼睛导光件',poly(pts,(0,1.1,0)),'light','translucent')
# Major front cheek rails follow visor width but wrap outwards toward side vents.
railpieces=[]
for (z0,y0,w0),(z1,y1,w1) in zip(stations,stations[1:]):
    pts=[(w0+2,y0+6,z0),(w0+8,y0+6,z0),(w1+8,y1+6,z1),(w1+2,y1+6,z1)]
    railpieces.append(poly(pts,(0,4.2,0)))
rail=fuse(*railpieces)
for sign,pid in ((1,'P10'),(-1,'P11')):part(pid,'cheek_rail_'+str(sign),'前侧舱罩护轨',rail if sign>0 else mirror(rail),'gray')
# Camera bezel with recessed black square gasket and lens rings.
bezel=xz([(-10,6),(10,6),(13,10),(12,25),(9,28),(-9,28),(-12,25),(-13,10)],-55,5)
bezel=bezel.cut(cyl(0,-56,17,6.3,8,(0,1,0)))
part('P12','camera_bezel','下颏橙色镜头框',bezel,'orange')
gasket=xz([(-8,8),(8,8),(10,11),(10,23),(8,25),(-8,25),(-10,23),(-10,11)],-55.6,1.5).cut(cyl(0,-56,17,5.8,4,(0,1,0)))
part('P13','lens_gasket','镜头方形内衬',gasket,'black')
part('H01','lens_body','镜头外观占位',cyl(0,-56.5,17,5.6,3,(0,1,0)),'black','hardware')
part('H02','lens_glass','镜片外观占位',cyl(0,-56.7,17,3.4,.3,(0,1,0)),'glass','hardware')
# SIDE vent modules: normals face 62 degrees away from front, toward each side.
vo=[(-19,-17),(10,-17),(17,-7),(17,11),(6,20),(-12,15)]
vi=[(-14,-12),(7,-12),(12,-5),(12,8),(5,14),(-9,10)]
vframe=yz(vo,-3,6.2).cut(yz(vi,-3.3,7))
vback=yz(vi,-1.1,1.5)
for z in (-9,-4,1):vback=vback.cut(box(-1.5,-10,z,2.5,17.5,2.4))
# Louvers are all integral to a perimeter; orange fins join a narrow border.
vt=yz([(14,-14),(17,-7),(17,10),(6,19),(3,16),(13,8),(13,-6),(10,-13)],3.3,1.7)
for yy in (-8,-2,4):
    top=11+(yy+8)*7/17
    vt=vt.fuse(yz([(yy,top),(yy+1.7,top+.7),(yy+8,4),(yy+6.3,3)],3.3,1.7))
vt=vt.fuse(yz([(-10,11),(7,18),(8,15),(-9,8)],3.3,1.7))
def sidepose(s,sign):
    q=s.copy();q.rotate(V(0,0,0),V(0,0,1),-28);q.translate(V(51,-29,31));return q if sign>0 else mirror(q)
for sign in (-1,1):
    window_points=inset_quad([(-12,y,z) for y,z in vi],-.2)
    cutter=sidepose(poly(window_points,(24,0,0)),sign)
    # Remove the receiving pocket too: the frame must seat into the shell,
    # not leave coincident walls through its material.
    lower=lower.cut(cutter);upper=upper.cut(cutter)
part('P01','lower_shell','收边下壳／电池仓',lower,'dark',note='内衬和 PCB 定位待量；真实侧孔已开。')
part('P02','upper_shell','多折线主壳',upper,'gray')
for sign,n in ((1,14),(-1,17)):
    for idx,s,slug,name,col in [(n,vframe,'vent_frame','侧面格栅装甲框','gray'),(n+1,vback,'vent_louvers','侧面黑色百叶','black'),(n+2,vt,'vent_fins','侧面橙色斜鳍片','orange')]:
        placed=sidepose(s,sign)
        part(f'P{idx:02}',slug+str(sign),name,placed,col)
# Swept shoulder bars and outer stepped armor strips.
shoulder=[(-30,52),(-26,68),(-14,81),(9,82),(24,70),(25,61),(19,60),(18,68),(7,75),(-13,75),(-20,65),(-23,51)]
strap=[(-25,51),(-19,69),(-7,79),(13,77),(23,64),(20,58),(15,65),(8,72),(-6,72),(-13,65),(-20,49)]
sh=yz(shoulder,33.5,6);st=yz(strap,40.2,3.5)
for y,z in ((-13,70),(13,70)):st=st.cut(cyl(39,y,z,1.7,7,(1,0,0)))
for sign,n in ((1,20),(-1,22)):
    part(f'P{n}','shoulder_orange'+str(sign),'折角橙色肩部护架',sh if sign>0 else mirror(sh),'orange')
    part(f'P{n+1}','shoulder_strap'+str(sign),'灰色肩部压甲',st if sign>0 else mirror(st),'gray')
# Side panel layout: large bevel-edged upper tile, smaller lower tiles with real recessed seams.
def side_skin_patch(points,stand_off=.4,thickness=2.8):
    # Offset along X preserves the exact stepped crown and rear chamfer of the
    # master loft.  Clipping a solid skin avoids non-planar polygon faces and
    # follows every shell station, including stations inside the panel outline.
    outside=trans(outer,(stand_off+thickness,0,0))
    inside=trans(outer,(stand_off,0,0))
    return outside.cut(inside).common(yz(points,0,100)).removeSplitter()
sideplate=side_skin_patch([(-7,44),(3,59),(22,59),(32,50),(30,32),(18,26),(2,29)])
sideplate=sideplate.cut(cyl(30,19,45,13.35,40,(1,0,0)))
# The engraving follows the same shell skin; its 0.65 mm recess remains visible
# at both the wider waist and the inward-sloping upper shoulder.
for z in (49,51):
    channel=[(-2,z),(9,z+4),(10,z+3.3),(-2,z-.8)]
    sideplate=sideplate.cut(side_skin_patch(channel,2.55,1.1))
# The upper edge stays 1.5 mm below the adjacent upper panel's lower edge.
# This produces a real dark separation rather than two coincident armor faces.
lowerplate=side_skin_patch([(-5,14),(12,9),(30,20),(32,28.5),(30,30.5),(18,24.5),(2,27.5),(-4,25.5)],.4,2.5)
for yy,zz in ((1,19),(23,25)):lowerplate=lowerplate.cut(cyl(30,yy,zz,1.6,40,(1,0,0)))
for sign,n in ((1,24),(-1,26)):
    # The circular mounting clearance separates the lower infill from the
    # shoulder armor. Give it its own physical part and folder.
    skins=sorted(sideplate.Solids,key=lambda s:s.CenterOfMass.z,reverse=True)
    if len(skins)>2:raise RuntimeError('Unexpected side armor fragments')
    part(f'P{n}','side_upper_armor'+str(sign),'侧面上层梯形装甲',skins[0] if sign>0 else mirror(skins[0]),'gray')
    if len(skins)==2:
        pid='P58' if sign>0 else 'P59'
        part(pid,'hinge_lower_infill'+str(sign),'轴盖下方独立嵌甲',skins[1] if sign>0 else mirror(skins[1]),'gray',note='由轴盖避让孔分离出的下部嵌甲，独立装配。')
    part(f'P{n+1}','side_lower_armor'+str(sign),'侧面下层收边装甲',lowerplate if sign>0 else mirror(lowerplate),'dark')
# Two horizontal small maintenance plates with recessed screw heads.
for j,(z,y0,y1) in enumerate([(36,-5,13),(28,-2,20)]):
    s=yz([(y0,z-3),(y1,z-3),(y1+2,z),(y1,z+3),(y0,z+3),(y0-1,z)],53.6,2.0)
    for yy in (y0+2,y1-2):s=s.cut(cyl(53,yy,z,1.4,4,(1,0,0)))
    for sign in (-1,1):part(f'P{28+j*2+(sign>0):02}','service_'+str(j)+str(sign),'侧面双层检修盖',s if sign>0 else mirror(s),'black')
for sign,n in ((1,32),(-1,35)):
    disc=cyl(53,19,45,13.2,3.2,(1,0,0)).cut(cyl(52.5,19,45,1.6,5,(1,0,0)))
    ring=cyl(56.3,19,45,11.1,1.5,(1,0,0)).cut(cyl(56,19,45,9.1,3,(1,0,0)))
    center=cyl(56.4,19,45,8.6,1.0,(1,0,0)).cut(cyl(56,19,45,1.6,3,(1,0,0)))
    for j,ss,col,slug in [(0,disc,'dark','hinge_base'),(1,ring,'orange','hinge_ring'),(2,center,'black','hinge_center')]:part(f'P{n+j}',slug+str(sign),'侧面圆形轴盖分件',ss if sign>0 else mirror(ss),col)
# Orange rear shoulder intake, real recessed three-slot detailing.
intake=yz([(12,65),(25,61),(31,69),(25,79),(17,81),(11,76)],40,5)
for yy in (17,21,25):intake=intake.cut(box(43.5,yy,67,3,1.5,8))
for sign,n in ((1,38),(-1,39)):part(f'P{n}','shoulder_intake'+str(sign),'后肩橙色导流罩',intake if sign>0 else mirror(intake),'orange')
# Low roof plate, recessed hatch, actual lifted handle with two separately bolted pedestals.
roof=xy([(-21,-8),(21,-8),(24,-1),(21,18),(15,24),(-15,24),(-21,18),(-24,-1)],84,2)
roof=roof.cut(box(-12,0,85.2,24,15,2))
for x in (-17,17):
    for y in (-2,17):roof=roof.cut(cyl(x,y,83.8,1.2,3))
part('P40','roof_hatch','顶部检修甲板',roof,'gray')
part('P41','roof_inset','顶部凹槽内衬',box(-11.7,.3,85.2,23.4,14.4,.6),'black')
for sign,n in ((1,42),(-1,43)):
    s=yz([(10,86),(22,86),(24,90),(21,95),(12,95),(9,91)],sign*18-3,6)
    s=s.cut(cyl(sign*18-3.2,16,92,1.9,6.4,(1,0,0)))
    s=s.cut(cyl(sign*17,17,85.9,2.0,1.5))
    part(f'P{n}','handle_mount'+str(sign),'顶部把手安装座',s,'dark')
part('P44','roof_handle','顶部横向提手',cyl(-20,16,92,1.7,40,(1,0,0)),'black')
# Rear phone dock consists of a broad back plate, orange wrap rails and low shelf.
back= xz([(-34,37),(34,37),(36,103),(32,112),(-32,112),(-36,103)],45,3.2)
# Structural stiffening slots stay in its rear face, leaving continuous thickness.
for x in (-28,28):back=back.cut(box(x-1,46.8,56,2,2,37))
# Clear the phone side rail seats before exporting the back plate.
rail_seat=xz([(28,40),(36,40),(36,104),(32,112),(28,112),(30,103),(30,49),(27,46)],40.9,7.2)
back=back.cut(rail_seat).cut(mirror(rail_seat))
part('P45','phone_backplate','手机托架背板',back,'dark')
for sign,n in ((1,46),(-1,47)):
    rail=xz([(28,40),(36,40),(36,104),(32,112),(28,112),(30,103),(30,49),(27,46)],41,7)
    part(f'P{n}','phone_orange_rail'+str(sign),'橙色手机托架侧边',rail if sign>0 else mirror(rail),'orange')
shelf=fuse(box(-36,37,35,72,12,4),box(-36,37,36,72,3,6))
part('P48','phone_shelf','手机下托',shelf,'dark')
rearframe=xz([(-32,8),(32,8),(38,20),(35,35),(27,41),(-27,41),(-35,35),(-38,20)],41,4)
rearframe=rearframe.cut(box(-18,40.5,8,36,6,22))
for x in (-27,27):
    for z in (16,30):rearframe=rearframe.cut(cyl(x,40.5,z,1.5,6,(0,1,0)))
part('P49','rear_service_frame','后部检修框',rearframe,'gray')
rearinsert=box(-15,42,8,30,2.8,21.5)
for z in (12,17,22,27):rearinsert=rearinsert.cut(box(-11,44, z,22,2,1.3))
part('P50','rear_service_cover','后部条纹检修盖',rearinsert,'black')
part('P51','rear_latch','后部橙色锁扣占位',box(-10,43.2,33,20,3.2,4),'orange')
# Original desktop base remains a distinct assembly, not a permanent four-leg body.
old=A.openDocument(str(ASSEMBLY/'Lingxi_Cockpit_R03.FCStd'))
for orig,n in [('P34',52),('P35',53),('P36',54),('P37',55),('P38',56),('P39',57)]:
    ob=old.getObject(orig)
    copyshape=ob.Shape.copy()
    if orig in ['P36','P37','P38','P39']:
        # Keep the complete provisional foot. Seat its upper face against the
        # underside of the ring rather than cutting away its connecting neck.
        ring_bottom=old.getObject('P35').Shape.BoundBox.ZMin
        copyshape.translate(V(0,0,ring_bottom-copyshape.BoundBox.ZMax))
    part(f'P{n}','legacy_'+orig,'磁吸底座／接触盒 '+orig,copyshape,'dark',group='desktop_base' if orig!='P34' else 'cockpit',note='沿用 R03，实体尺寸待校准。')
A.closeDocument(old.Name)
# Hardware screw envelopes, decorative hex-socket recess, separate from printed parts.
def screw(center,axis,r=1.8):
    s=cyl(0,0,0,r,1.1)
    hexpts=[(math.cos(i*math.pi/3)*.85,math.sin(i*math.pi/3)*.85) for i in range(6)]
    s=s.cut(xy(hexpts,.4,1))
    s.Placement=A.Placement(V(*center),A.Rotation(V(0,0,1),V(*axis)));return s
num=3
for sign in (-1,1):
    for y,z,x in [(-13,70,43.7),(13,70,43.7),(-3,36,55.6),(11,36,55.6),(0,28,55.6),(18,28,55.6),(1,19,53.29),(23,25,54.96),(19,45,57.6)]:
        part(f'H{num:02}','screw_'+str(num),'侧甲螺钉占位',screw((sign*x,y,z),(sign,0,0)),'black','hardware');num+=1
for x in (-17,17):
    for y in (-2,17):part(f'H{num:02}','screw_'+str(num),'顶盖螺钉占位',screw((x,y,86),(0,0,1),1.6),'black','hardware');num+=1
for x,y in [(-31,-20),(31,-20),(-31,20),(31,20)]:
    part(f'H{num:02}','magnet_'+str(num),'磁铁占位',cyl(x,y,5,3,2),'metal','hardware');num+=1
for x in (-7.5,-2.5,2.5,7.5):
    part(f'H{num:02}','contact_'+str(num),'磁吸信号触点占位',cyl(x,0,3.8,.8,3),'gold','hardware');num+=1
DOC.recompute();A.setActiveDocument(DOC.Name)
DOC.saveAs(str(ASSEMBLY/f'Lingxi_Cockpit_{REV}.FCStd'))
report={'revision':REV,'status':'DRAFT_REVIEW_NOT_PRINT_RELEASE','units':'mm','source':'06_tools/build_r04.py','parts':MAN,'all_valid':all(p['valid'] and p['solids']==1 for p in MAN),'canopy_facets':12,'side_vent_normals':[[.882948,-.469472,0],[-.882948,-.469472,0]],'shell_profiles':rows,'canopy_stations':stations,'limitations':['Hardware dimensions unmeasured','Accessory retention and assembly interference not cleared','Original desktop base remains provisional']}
(ASSEMBLY/f'manifest_{REV}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('BUILD_COMPLETE',len(MAN),flush=True)
