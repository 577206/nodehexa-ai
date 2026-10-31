"""R05: user's marked-up silhouette, multi-facet canopy and side vents.
FreeCAD solid authoring. Millimetres; unmeasured appearance / separation review.
R03 stays immutable. No release STEP or printing package is produced here.
"""
import json,math,sys
from pathlib import Path
import FreeCAD as A
import Part,MeshPart
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'06_tools'))
from cad_edge_break_r05 import apply_edge_break,TARGET_PARTS
REV='R05'; OUT=ROOT/'02_parts'/REV; ASSEMBLY=ROOT/'03_assembly'
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
    edge_details={}
    # Physical edge breaks in the solid model, not a Blender-only modifier.
    # Do not dress mating lips, thin clear sheets or the master shell here.
    dressed={'P12','P13','P14','P17','P20','P21','P22','P23','P38','P39','P40','P42','P43','P45','P46','P47','P48','P49','P51'}
    if pid in dressed and pid not in TARGET_PARTS:
        for size in (.45,.25):
            try:
                candidate=s.makeChamfer(size,s.Edges)
                if candidate.isValid() and len(candidate.Solids)==1 and candidate.Volume>0:
                    s=candidate;edge_break=size;break
            except Exception:pass
        print('EDGE_BREAK',pid,edge_break,flush=True)
    mirror_from={'P22':'P20','P23':'P21','P26':'P24','P27':'P25','P39':'P38','P61':'P60','P69':'P68'}
    if pid in mirror_from:
        source_id=mirror_from[pid]
        s=mirror(DOC.getObject(source_id).Shape)
        source_entry=next(p for p in MAN if p['id']==source_id)
        edge_break=source_entry['edge_break_mm']
        edge_details=json.loads(json.dumps(source_entry.get('edge_break_details',{})))
        edge_details['mirrored_from']=source_id
        for e in edge_details.get('selected_edges',[]):e['midpoint_mm'][0]*=-1
    elif pid in TARGET_PARTS:
        s,edge_details=apply_edge_break(s,pid)
        edge_break=edge_details.get('size_mm',0)
        print('SELECTIVE_EDGE_BREAK',pid,edge_break,edge_details.get('selected_edge_count',0),flush=True)
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
    if edge_details:entry['edge_break_details']=edge_details
    MAN.append(entry);(folder/'part.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n');print('PART',pid,flush=True);return ob
# Source profile: narrower crown, long swept front, taper underneath.
rows=[[37,-35,38,13,6],[46,-48,43,15,14],[50,-50,43,14,32],[48,-43,38,14,50],[41,-31,34,11,66],[31,-14,27,8,80],[27,-7,24,7,84]]
inside=[[h-2.6,f+2.6,r-2.6,c-1.3,z+(2.6 if i==0 else -2.6 if i==len(rows)-1 else 0)] for i,(h,f,r,c,z) in enumerate(rows)]
outer=loft(rows);hollow=outer.cut(loft(inside))
# Five stations form four different slope zones, with two wraparound side facets each.
stations=[(33,-53,23),(40,-52,27),(58,-42,29),(73,-27,24),(81,-15,20)]
outline=[(-w-1,z-.2) for z,y,w in stations]+[(w+1,z-.2) for z,y,w in reversed(stations)]
hollow=hollow.cut(xz(outline,-70,67))
hollow=hollow.cut(cyl(0,-61,21,6,27,(0,1,0)))
for side in (-1,1):
    for xx in (17.5,21,24.5):
        for zz in (17,20.5,24,27.5):hollow=hollow.cut(cyl(side*xx,-59,zz,1.05,25,(0,1,0)))
lower=hollow.common(box(-90,-90,0,180,180,26.85));upper=hollow.common(box(-90,-90,27.15,180,180,100))
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
carrier=xz([(-24,38),(24,38),(26,52),(-26,52)],-43.7,2.2)
part('P07','eye_carrier','灯眼内托板',carrier,'black')
for sign,pid in ((-1,'P08'),(1,'P09')):
    pp=[(sign*8,41.5),(sign*22,48),(sign*22,45.8),(sign*8,39.4)]
    # Surface y=-53 at z36, then slopes back above it.
    pts=[(x,-52+(max(z-36,0)*9/19),z) for x,z in pp]
    # One planar lamp plate; taper represented by straight sloping silhouette.
    pts=[(x,-44.8,z) for x,z in pp]
    part(pid,'eye_lightguide_'+str(sign),'斜向眼睛导光件',poly(pts,(0,1.1,0)),'light','translucent')
# Major front cheek rails follow visor width but wrap outwards toward side vents.
railpieces=[]
for (z0,y0,w0),(z1,y1,w1) in zip(stations,stations[1:]):
    pts=[(w0+2,y0+6,z0),(w0+6.5,y0+6,z0),(w1+6.5,y1+6,z1),(w1+2,y1+6,z1)]
    railpieces.append(poly(pts,(0,4.2,0)))
rail=fuse(*railpieces)
rail_top=rail.common(box(-90,-90,49.6,180,180,50))
rail_bottom=rail.common(box(-90,-90,0,180,180,48.8))
for sign,pid,lowpid in ((1,'P10','P66'),(-1,'P11','P67')):
    part(pid,'cheek_rail_'+str(sign),'前侧上段舱罩护轨',rail_top if sign>0 else mirror(rail_top),'gray')
    part(lowpid,'lower_cheek_rail_'+str(sign),'前侧下段舱罩护轨',rail_bottom if sign>0 else mirror(rail_bottom),'gray')
# Camera bezel with recessed black square gasket and lens rings.
bezel=xz([(-10,10),(10,10),(13,14),(12,29),(9,32),(-9,32),(-12,29),(-13,14)],-55,5)
bezel=bezel.cut(cyl(0,-56,21,6.3,8,(0,1,0)))
part('P12','camera_bezel','下颏橙色镜头框',bezel,'orange')
gasket=xz([(-8,12),(8,12),(10,15),(10,27),(8,29),(-8,29),(-10,27),(-10,15)],-55.6,1.5).cut(cyl(0,-56,21,5.8,4,(0,1,0)))
part('P13','lens_gasket','镜头方形内衬',gasket,'black')
lens_body=cyl(0,-56.5,21,5.6,3,(0,1,0))
lens_body=lens_body.cut(cyl(0,-56.6,21,4.65,.9,(0,1,0)))
lens_body=lens_body.cut(cyl(0,-56.6,21,3.80,1.75,(0,1,0)))
lens_body=lens_body.cut(cyl(0,-56.6,21,3.20,3.3,(0,1,0)))
part('H01','lens_body','双台阶镜筒外观占位',lens_body,'black','hardware')
part('H02','lens_glass','凹入镜片外观占位',cyl(0,-54.85,21,3.18,.3,(0,1,0)),'glass','hardware')
# SIDE vent modules: normals face 62 degrees away from front, toward each side.
vo=[(-20,-17),(8,-19),(17,-7),(17,19),(7,24),(-18,8)]
vi=[(p[1],p[2]) for p in inset_quad([(0,y,z) for y,z in vo],3.3)]
vframe=yz(vo,-3,6.2).cut(yz(vi,-3.3,7))
vback=yz(vi,-1.1,1.5)
for z in (-10,-6,-2,2):vback=vback.cut(box(-1.5,-11,z,2.5,19,1.8))
# Louvers are all integral to a perimeter; orange fins join a narrow border.
vt=yz([(12,-14),(17,-7),(17,19),(7,24),(5,21),(13,16),(13,-5),(8,-13)],3.3,1.7)
for yy in (-10,-4,2):
    top=12+(yy+10)*.64
    vt=vt.fuse(yz([(yy,top),(yy+1.5,top+.9),(yy+7,5),(yy+5.5,4.3)],3.3,1.7))
vt=vt.fuse(yz([(-15,9),(7,23),(7.7,20.7),(-14,6.7)],3.3,1.7))
def sidepose(s,sign):
    # Local planar vent profiles scale together, including the shell cutter.
    m=A.Matrix();m.A22=.9;m.A33=.9
    q=s.transformGeometry(m);q.rotate(V(0,0,0),V(0,0,1),-28);q.translate(V(47.5,-28,32));return q if sign>0 else mirror(q)
for sign in (-1,1):
    window_points=inset_quad([(-12,y,z) for y,z in vi],-.2)
    cutter=sidepose(poly(window_points,(24,0,0)),sign)
    # Remove the receiving pocket too: the frame must seat into the shell,
    # not leave coincident walls through its material.
    lower=lower.cut(cutter);upper=upper.cut(cutter)
part('P01','lower_shell','收边下壳／电池仓',lower,'dark',note='内衬和 PCB 定位待量；真实侧孔已开。')
part('P02','upper_shell','多折线内层主壳',upper,'dark')
for sign,n in ((1,14),(-1,17)):
    for idx,s,slug,name,col in [(n,vframe,'vent_frame','侧面格栅装甲框','gray'),(n+1,vback,'vent_louvers','侧面黑色百叶','black'),(n+2,vt,'vent_fins','侧面橙色斜鳍片','orange')]:
        placed=sidepose(s,sign)
        part(f'P{idx:02}',slug+str(sign),name,placed,col)
# Slimmer front cheek shields are individual shells following the lower face.
def front_skin(points,stand_off=.3,thickness=2.4):
    return trans(outer,(0,-stand_off-thickness,0)).cut(trans(outer,(0,-stand_off,0))).common(xz(points,-90,90)).removeSplitter()
cheek=front_skin([(14,11),(26.5,11),(30.5,31),(29,36),(25,32.5),(15,32.5)])
for xx in (17.5,21,24.5):
    for zz in (17,20.5,24,27.5):cheek=cheek.cut(cyl(xx,-65,zz,1.05,35,(0,1,0)))
for sign,pid in ((1,'P60'),(-1,'P61')):
    part(pid,'front_cheek_shield'+str(sign),'前脸独立打孔颊甲',cheek if sign>0 else mirror(cheek),'gray')
transition=front_skin([(29.5,33),(34,32),(43,43),(42,50),(35.5,56),(31,51)],.35,2.3).cut(rail_top).cut(rail_bottom)
transition=transition.cut(sidepose(vframe,1)).cut(sidepose(vt,1))
for sign,pid in ((1,'P68'),(-1,'P69')):
    part(pid,'diagonal_cheek_bridge'+str(sign),'前侧斜向过渡颊甲',transition if sign>0 else mirror(transition),'gray')
# Swept shoulder armor is a skin over the actual loft, not a flat slab.
def skin_x(points,stand_off=.35,thickness=2.8):
    return trans(outer,(stand_off+thickness,0,0)).cut(trans(outer,(stand_off,0,0))).common(yz(points,0,100)).removeSplitter()
intake_outline=[(12,65),(25,61),(31,69),(25,79),(17,81),(11,76)]
intake=skin_x(intake_outline,.25,4.5)
for yy in (17,21,25):intake=intake.cut(skin_x([(yy,67),(yy+1.5,67),(yy+1.5,75),(yy,75)],3.05,2))
intake_clear=[(p[1],p[2]) for p in inset_quad([(0,y,z) for y,z in intake_outline],-.35)]
intake_pocket=skin_x(intake_clear,.1,7)
shoulder=[(-26,57),(-21,71),(-12,80),(8,81),(20,71),(22,64),(19,64),(16,71),(7,77),(-12,76),(-17,69),(-22,56)]
strap=[(-20,57),(-16,70),(-6,80),(13,78),(22,65),(18,61),(13,68),(7,74),(-5,74),(-11,67),(-15,56)]
sh=skin_x(shoulder,.25,3.5).cut(intake_pocket);st=skin_x(strap,3.95,2.6).cut(intake_pocket)
# The intake clearance trims off the short dangling rear tip of the strap.
# Omit that disconnected design remnant, leaving one continuous shoulder band.
st_fragments=sorted(st.Solids,key=lambda s:s.Volume,reverse=True)
print('SHOULDER_TRIM_VOLUMES', [round(s.Volume,3) for s in st_fragments],flush=True)
st=st_fragments[0]
for y,z in ((-13,70),(4,77)):st=st.cut(cyl(20,y,z,1.7,40,(1,0,0)))
for sign,n in ((1,20),(-1,22)):
    part(f'P{n}','shoulder_orange'+str(sign),'折角橙色肩部护架',sh if sign>0 else mirror(sh),'orange')
    part(f'P{n+1}','shoulder_strap'+str(sign),'灰色肩部压甲',st if sign>0 else mirror(st),'gray')
# Inset upper service panels break up the former blank side wall.
upper_service=skin_x([(-13,61),(-9,69),(1,74),(16,72),(18,63),(10,60)],.25,2.4).cut(sh).cut(st).cut(intake_pocket)
for yy,zz in ((-5,65),(11,66)):
    upper_service=upper_service.cut(cyl(20,yy,zz,1.4,40,(1,0,0)))
for sign,pid in ((1,'P62'),(-1,'P63')):
    part(pid,'upper_service_inset'+str(sign),'肩甲下凹黑色检修面板',upper_service if sign>0 else mirror(upper_service),'black')
# Side panel layout: individually removable, shell-following armor, backing and service strips.
def side_skin_patch(points,stand_off=.4,thickness=2.8):
    # Keeping the true loft profile avoids floating flat panels and preserves
    # the tapered shoulder and rear bevel underneath each removable tile.
    outside=trans(outer,(stand_off+thickness,0,0))
    inside=trans(outer,(stand_off,0,0))
    return outside.cut(inside).common(yz(points,0,100)).removeSplitter()
def side_surface_x(y,z):
    hit=Part.makeLine(V(0,y,z),V(90,y,z)).section(outer)
    return max(p.Point.x for p in hit.Vertexes)
def side_surface_axis(y,z):
    d=.03
    dy=(side_surface_x(y+d,z)-side_surface_x(y-d,z))/(2*d)
    dz=(side_surface_x(y,z+d)-side_surface_x(y,z-d))/(2*d)
    n=V(1,-dy,-dz);n.normalize();return n
def side_hole(s,y,z,offset,r=1.25,head_r=2.05):
    n=side_surface_axis(y,z);p=V(side_surface_x(y,z)+offset,y,z)
    # Coaxial through-bore and 0.30 mm shallow head seat in the actual skin.
    s=s.cut(Part.makeCylinder(r,12,p-n*8,n))
    return s.cut(Part.makeCylinder(head_r,1.0,p-n*.30,n))
def side_screw(y,z,offset):
    n=side_surface_axis(y,z);p=V(side_surface_x(y,z)+offset,y,z)-n*.25
    sh=cyl(0,0,0,1.88,1.12)
    hx=[(math.cos(i*math.pi/3)*.78,math.sin(i*math.pi/3)*.78) for i in range(6)]
    sh=sh.cut(xy(hx,.42,.9))
    sh.Placement=A.Placement(p,A.Rotation(V(0,0,1),n));return sh
# One continuous black substrate sits below the replaceable armor panels.
# The panel top is at X(surface)+3.95, backing top at +1.35: touching layers,
# not coincident independent solids. The exposed black reveals are real gaps.
back_outline=[(-8,23),(-7,45),(-3,60),(4,65),(22,64),(32,53),(35,39),(32,23),(23,15),(6,10),(-4,14)]
axis_y,axis_z,axis_r=19,49,13.2
axclear=cyl(0,axis_y,axis_z,axis_r+.45,90,(1,0,0))
backing=side_skin_patch(back_outline,.15,1.20).cut(axclear)
# Trapezoidal upper tile: swept leading edge, inset shoulder edge and circular
# relief surrounding the separate axis cap. Its narrow incised lines are CAD cuts.
upper_outline=[(-7,53),(-1,63.5),(15,63.5),(18,61),(7,48),(-3,47.5)]
sideplate=side_skin_patch(upper_outline,1.35,2.60).cut(axclear)
for dy in (0,1.8):
    engraving=[(-3,54+dy),(5.8,57.1+dy),(6.1,56.45+dy),(-2.7,53.35+dy)]
    sideplate=sideplate.cut(side_skin_patch(engraving,3.35,.95))
upper_screws=[(2,59),(-.5,52)]
for yy,zz in upper_screws:sideplate=side_hole(sideplate,yy,zz,3.95)
# Lower tile closes the same silhouette with a stepped trapezoid and two
# countersunk points; it is gray, not merged visually into the dark lower shell.
lower_outline=[(-5,14),(8,10),(22,15),(25,24),(20,26),(3,26),(-4,22)]
lowerplate=side_skin_patch(lower_outline,1.35,2.35)
for dy in (0,1.7):
    engraving=[(0,17+dy),(14,20.6+dy),(14.2,20+dy),(.2,16.4+dy)]
    lowerplate=lowerplate.cut(side_skin_patch(engraving,3.15,.85))
lower_screws=[(-.5,20),(20,21)]
for yy,zz in lower_screws:lowerplate=side_hole(lowerplate,yy,zz,3.70)
# Rear-lower infill is an intentional independent tile with a dark seam to the
# lower plate. P58/P59 are preserved as stable physical part identities.
infill_outline=[(27.5,27.5),(32,29),(34,39),(31.8,41),(29,36.5),(25.5,34),(25,30)]
infill=side_skin_patch(infill_outline,1.35,2.35).cut(axclear)
infill=side_hole(infill,29,31,3.70,1.05,1.8)
# Two offset inspection strips are built from the same loft skin. They no
# longer use a constant-X extrusion that hid one end and floated the other.
service_spec=[(42,-5.0,6.5),(32,-2.8,22.0)]
service_parts=[];service_screws=[]
for z,y0,y1 in service_spec:
    contour=[(y0+1,z-2.7),(y1-.8,z-2.7),(y1+1,z-1.2),(y1+1,z+1.2),(y1-.8,z+2.7),(y0+1,z+2.7),(y0-.8,z+1.1),(y0-.8,z-1.1)]
    strip=side_skin_patch(contour,1.35,1.95).cut(axclear)
    for yy in (y0+2.3,y1-2.3):
        strip=side_hole(strip,yy,z,3.30)
        service_screws.append((yy,z,3.30))
    service_parts.append(strip)
# Small recessed dash marks belong to the substrate, visible between the two
# strips, rather than being floating decorative meshes.
for yy in (-2,1,4):
    backing=backing.cut(side_skin_patch([(yy,36.4),(yy+1.2,36.4),(yy+1.2,38.0),(yy,38.0)],.95,.7))
# A conformal cylindrical pedestal joins the round side cap to the sloped
# shell. The cap face remains planar for a real circular orange ring.
disc_front=52.2
disc=cyl(0,axis_y,axis_z,axis_r,disc_front,(1,0,0)).cut(trans(outer,(.15,0,0)))
disc=disc.cut(cyl(0,axis_y,axis_z,1.55,60,(1,0,0)))
ring=cyl(disc_front+.1,axis_y,axis_z,11.1,1.5,(1,0,0)).cut(cyl(disc_front,axis_y,axis_z,9.1,2,(1,0,0)))
center=cyl(disc_front+.2,axis_y,axis_z,8.6,1.0,(1,0,0)).cut(cyl(disc_front,axis_y,axis_z,1.55,2,(1,0,0)))
for sign,n in ((1,24),(-1,26)):
    p=lambda shape:shape if sign>0 else mirror(shape)
    part(f'P{n}','side_upper_armor'+str(sign),'侧面上层梯形拼甲',p(sideplate),'gray',note='顺主体折面；独立嵌甲、两道真实浅刻线；不是平面贴片。')
    part(f'P{n+1}','side_lower_armor'+str(sign),'侧面下层收边拼甲',p(lowerplate),'gray',note='与上方检修带分缝，双孔贴面螺钉。')
    part('P58' if sign>0 else 'P59','hinge_lower_infill'+str(sign),'轴盖下方后侧嵌甲',p(infill),'gray')
    part('P70' if sign>0 else 'P71','side_service_backing'+str(sign),'侧甲黑色检修底板',p(backing),'black',note='连续贴合壳面，暴露部分形成真实装甲分缝。')
    for j,strip in enumerate(service_parts):
        part(f'P{28+j*2+(sign>0):02}','service_'+str(j)+str(sign),'贴壳双螺钉检修条 '+str(j+1),p(strip),'dark')
    for j,ss,col,slug in [(0,disc,'dark','hinge_base'),(1,ring,'orange','hinge_ring'),(2,center,'black','hinge_center')]:
        part(f'P{32+j if sign>0 else 35+j}',slug+str(sign),'侧面圆形轴盖分件',p(ss),col)
# Every screw is located from the current loft face and aligned to its normal.
# Ten hardware placeholders per side, H60-H79, leave older IDs unchanged.
side_hardware=service_screws+[(yy,zz,3.70) for yy,zz in lower_screws]+[(29,31,3.70)]+[(yy,zz,3.95) for yy,zz in upper_screws]
for sign,start in ((1,60),(-1,70)):
    for j,(yy,zz,offset) in enumerate(side_hardware):
        sh=side_screw(yy,zz,offset)
        part(f'H{start+j:02}','side_fastener_'+str(start+j),'侧甲贴面螺钉占位',sh if sign>0 else mirror(sh),'black','hardware')
    sh=cyl(disc_front+1.25,axis_y,axis_z,1.9,1.1,(1,0,0))
    # A true socket recess in the cap's central screw head.
    hx=[(axis_y+math.cos(i*math.pi/3)*.78,axis_z+math.sin(i*math.pi/3)*.78) for i in range(6)]
    sh=sh.cut(yz(hx,disc_front+1.75,1))
    part(f'H{start+9:02}','axis_fastener_'+str(sign),'轴盖中心螺钉占位',sh if sign>0 else mirror(sh),'black','hardware')
# Orange rear shoulder intake, real recessed three-slot detailing.
for sign,n in ((1,38),(-1,39)):part(f'P{n}','shoulder_intake'+str(sign),'后肩橙色导流罩',intake if sign>0 else mirror(intake),'orange')
# Low roof plate, recessed hatch, actual lifted handle with two separately bolted pedestals.
roof=xy([(-21,-8),(21,-8),(24,-1),(21,18),(15,24),(-15,24),(-21,18),(-24,-1)],84,2)
roof=roof.cut(box(-12,0,85.2,24,15,2))
for x in (-17,17):
    for y in (-2,5):roof=roof.cut(cyl(x,y,83.8,1.2,3))
part('P40','roof_hatch','顶部检修甲板',roof,'gray')
part('P41','roof_inset','顶部凹槽内衬',box(-11.7,.3,85.2,23.4,14.4,.6),'black')
for sign,n in ((1,42),(-1,43)):
    s=yz([(11,86),(21,86),(22,89),(20,92),(12,92),(10,89)],sign*18-3,6)
    s=s.cut(cyl(sign*18-3.2,16,89.5,1.55,6.4,(1,0,0)))
    part(f'P{n}','handle_mount'+str(sign),'顶部把手安装座',s,'dark')
part('P44','roof_handle','顶部横向提手',cyl(-20,16,89.5,1.5,40,(1,0,0)),'black')
# Compact phone dock: short backrest tilted back ten degrees as an assembly.
# The top of a full-size phone will project above this support; phone not modeled.
def phonepose(s):
    q=s.copy();q.rotate(V(0,52,38),V(1,0,0),-10);return q
back=xz([(-34,39),(34,39),(36,88),(32,95),(-32,95),(-36,88)],53,3.2)
for x in (-28,28):back=back.cut(box(x-1,54.8,50,2,2,31))
rail_profile=[(28,40),(36,40),(36,88),(32,95),(28,95),(30,87),(30,49),(27,46)]
rail_seat=xz(rail_profile,48.9,7.4)
back=back.cut(rail_seat).cut(mirror(rail_seat))
part('P45','phone_backplate','后倾手机托架背板',phonepose(back),'dark')
for sign,n in ((1,46),(-1,47)):
    rail=xz(rail_profile,49,7)
    part(f'P{n}','phone_orange_rail'+str(sign),'橙色手机托架侧边',phonepose(rail if sign>0 else mirror(rail)),'orange')
shelf=fuse(box(-36,45,35,72,12,4),box(-36,45,36,72,3,6))
part('P48','phone_shelf','后倾手机下托',phonepose(shelf),'dark')
# Two printed webs connect the cradle shelf to the rear shell support region.
web=yz([(38,29),(41,29),(54,35),(54,38),(47,38),(39,34)],24,4)
for sign,pid in ((1,'P64'),(-1,'P65')):
    part(pid,'phone_mount_web'+str(sign),'手机托架底部连接肋',web if sign>0 else mirror(web),'dark')
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
    for y,z in [(-13,70),(4,77)]:
        shs=side_screw(y,z,6.55)
        part(f'H{num:02}','screw_'+str(num),'肩部贴面螺钉占位',shs if sign>0 else mirror(shs),'black','hardware');num+=1
    num+=7
for x in (-17,17):
    for y in (-2,5):part(f'H{num:02}','screw_'+str(num),'顶盖螺钉占位',screw((x,y,86),(0,0,1),1.6),'black','hardware');num+=1
for x,y in [(-31,-20),(31,-20),(-31,20),(31,20)]:
    part(f'H{num:02}','magnet_'+str(num),'磁铁占位',cyl(x,y,5,3,2),'metal','hardware');num+=1
for x in (-7.5,-2.5,2.5,7.5):
    part(f'H{num:02}','contact_'+str(num),'磁吸信号触点占位',cyl(x,0,3.8,.8,3),'gold','hardware');num+=1
DOC.recompute();A.setActiveDocument(DOC.Name)
DOC.saveAs(str(ASSEMBLY/f'Lingxi_Cockpit_{REV}.FCStd'))
report={'revision':REV,'status':'DRAFT_REVIEW_NOT_PRINT_RELEASE','units':'mm','source':'06_tools/build_r05.py','parts':MAN,'all_valid':all(p['valid'] and p['solids']==1 for p in MAN),'canopy_facets':12,'side_vent_normals':[[.882948,-.469472,0],[-.882948,-.469472,0]],'shell_profiles':rows,'canopy_stations':stations,'limitations':['Hardware dimensions unmeasured','Accessory retention and assembly interference not cleared','Original desktop base remains provisional']}
(ASSEMBLY/f'manifest_{REV}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('BUILD_COMPLETE',len(MAN),flush=True)
