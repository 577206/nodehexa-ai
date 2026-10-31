"""User-requested R02 trial STL exports; rebuild source, verify solids and insertion."""
from model import *
from build123d import export_stl, ShapeList
import trimesh,json,hashlib
p=load_parameters(ROOT/'parameters.yaml');v=lambda n:value(p,n)
m=build_model(p)
assert m.is_valid and len(m.solids())==1
# Supplier reference neck, only confirmed outline; no unmeasured solder surrogate.
neck=Pos(0,0,27)*extrude(RectangleRounded(17.54,4,1.999),amount=2)
collisions=[]
for dz in [-8,-4,-2,0]:
 q=m.intersect(Pos(0,0,dz)*neck)
 vol=q.volume if q else 0
 assert abs(vol)<1e-6,(dz,vol)
 collisions.append({'dz':dz,'collision_mm3':vol})
# At flange stop plane, a nominal19.54 end span cannot enter17.94 throat.
flange_probe=Pos(0,0,27.05)*extrude(RectangleRounded(19.54,4,1.999),amount=.1)
q=m.intersect(flange_probe);stop_volume=(sum(a.volume for a in q) if isinstance(q,ShapeList) else q.volume) if q else 0
assert stop_volume>0
# Small coupon reproduces upper7mm of central mounting roof; crop stays connected.
coupon=m.intersect(Pos(0,0,26)*Box(32,16,8))
if isinstance(coupon,ShapeList):
 solids=[solid for item in coupon for solid in item.solids()]
 assert len(solids)==1,len(solids)
 coupon=solids[0]
assert coupon.is_valid and len(coupon.solids())==1
coupon=Pos(0,0,-coupon.bounding_box().min.Z)*coupon
out=ROOT/'outputs/print';out.mkdir(parents=True,exist_ok=True)
records=[]
for obj,name in [(m,'B001_Bowl_Mount_R02_BOTTOM_INSERT_86x86x29mm_1pc.stl'),(coupon,'Connector_Fit_Coupon_R02_32x16mm_OPTIONAL.stl')]:
 f=out/name;assert export_stl(obj,str(f),tolerance=.025,angular_tolerance=.08)
 mesh=trimesh.load_mesh(f);assert mesh.is_watertight and mesh.is_volume
 records.append({'file':name,'dimensions_mm':mesh.extents.tolist(),'watertight':True,'volume_mesh':True,'quantity':1,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
report={'revision':'R02','status':'CAD_checked_trial_fit_required','units':'mm','outputs':records,'front_neck_insertion':collisions,'flange_upward_stop_probe_mm3':stop_volume,'interface':{'throat_mm':[17.94,4.4],'underside_relief_mm':[22,8],'flange_stop_z':27,'collar_top_z':28,'nominal_mating_face_z':29},'physical_not_verified':['Connector outline/tolerance and fit','Solder/insulation envelope below roof','Adhesive holding strength and real head counterpart'],'hashes':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ['source/model.py','parameters.yaml','spec/current.yaml']}}
(out/'R02_print_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(out/'R02_打印与安装说明.txt').write_text('R02 从下向上安装连接器。单位毫米，100%比例。\n碗底打印1件，外形86×86×29mm；灰色在切片软件中选择。\n建议先打印小试装片（可选），核对实际接口配合。\n磁吸前端由碗底内部向上伸出17.94×4.4mm通口，突出边沿止挡在下方；焊点与线束留在内部，不穿过小孔。\n下部22×8mm避空没有托底。胶只用于塑料外壳接触面，避开接触面和弹针。\n接口面名义Z29，薄定位口顶部Z28，外部定位边仍Z29。\n两机盖螺丝位置、孔径、罩体外形不变。\n这是试装版：未验证真实打印公差、焊点与绝缘包络和胶粘强度。\nR01旧版已暂停使用，请勿混用。\n')
print(json.dumps(report,ensure_ascii=False))
