"""Build an editable, dimensionally provisional Lingxi mecha cockpit in Blender.

The visual proportions follow references/turnaround-six-views.png.  No PCB hole,
camera FPC, battery, pogo-pin, magnet or robot mounting dimensions are certified.
Run: blender -b --python build_visual_cockpit.py
"""

import json
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(HERE, "parameters.json"), encoding="utf8") as f:
    P = json.load(f)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def mat(name, rgba, metallic=0, roughness=.45, emission=None, alpha=1):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgba, alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgba, alpha)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if alpha != 1:
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Transmission Weight"].default_value = .16
        m.surface_render_method = "BLENDED"
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 8
    return m


graphite = mat("01 warm charcoal armor", (.105, .113, .124), .30, .51)
armor = mat("02 gunmetal armor panels", (.24, .255, .27), .35, .42)
roofmat = mat("03 upper graphite plates", (.17, .18, .19), .32, .43)
orange = mat("04 safety orange exoskeleton", (.94, .20, .016), .22, .34)
black = mat("05 recessed vents", (.015, .018, .021), .12, .5)
glass = mat("06 smoked bronze transparent canopy", (.045, .041, .038), .18, .17, alpha=.56)
amber = mat("07 amber expressive eyes", (1, .19, .005), emission=(1, .13, 0))
lens = mat("08 camera optical glass", (.013, .018, .046), .42, .08)
steel = mat("09 screw and magnet steel", (.53, .55, .56), .73, .25)
gold = mat("10 signal contacts", (.82, .48, .11), .8, .26)
backdrop = mat("11 neutral photo background", (.82, .83, .84), .05, .7)


def link_mesh(name, verts, faces, material, group="Cockpit / body"):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["assembly_group"] = group
    return obj


def bevel(obj, amount=.8, segments=2):
    mod = obj.modifiers.new("edge break", "BEVEL")
    mod.width = amount
    mod.segments = segments
    obj.modifiers.new("weighted normals", "WEIGHTED_NORMAL")
    return obj


def cube(name, loc, dims, material, radius=0, group="Cockpit / body"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    obj["assembly_group"] = group
    if radius:
        bevel(obj, radius)
    return obj


def cylinder(name, loc, radius, depth, material, axis="Z", group="Cockpit / detail"):
    rot = (0, 0, 0) if axis == "Z" else ((math.pi / 2, 0, 0) if axis == "Y" else (0, math.pi / 2, 0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=loc, rotation=rot)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj["assembly_group"] = group
    bevel(obj, .25)
    return obj


def ring(name, loc, outer, inner, depth, material, axis="Y"):
    # A torus makes the camera and side-hinge rings read as actual recessed parts.
    rotation = (math.pi / 2, 0, 0) if axis == "Y" else ((0, math.pi / 2, 0) if axis == "X" else (0, 0, 0))
    bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=10,
        location=loc, rotation=rotation, major_radius=(outer + inner) / 2,
        minor_radius=(outer - inner) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    obj["assembly_group"] = "Cockpit / detail"
    return obj


def prism(name, points, vector, material, group="Cockpit / armor", edge=.45):
    n = len(points)
    vertices = list(points) + [tuple(Vector(p) + Vector(vector)) for p in points]
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2*n))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    obj = link_mesh(name, vertices, faces, material, group)
    if edge:
        bevel(obj, edge)
    return obj


def beam(name, p1, p2, width, material, group="Cockpit / exoskeleton"):
    a, b = Vector(p1), Vector(p2)
    ob = cube(name, (a+b)/2, (width, width, (b-a).length), material, width*.17, group)
    ob.rotation_euler = (b-a).to_track_quat("Z", "Y").to_euler()
    return ob


def ring8(hx, yf, yr, cut, z):
    return [(-hx+cut,yf,z),(hx-cut,yf,z),(hx,yf+cut,z),(hx,yr-cut,z),
            (hx-cut,yr,z),(-hx+cut,yr,z),(-hx,yr-cut,z),(-hx,yf+cut,z)]


def loft8(name, levels, material):
    verts = [p for level in levels for p in ring8(*level)]
    n = 8
    faces = [tuple(range(n-1,-1,-1)), tuple(range(n*(len(levels)-1),n*len(levels)))]
    for k in range(len(levels)-1):
        for i in range(n):
            j=(i+1)%n
            faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
    return link_mesh(name, verts, faces, material)


def screw(name, xyz, axis="Z"):
    cylinder(name, xyz, 1.8, .8, black, axis)


# Orientation: X left/right, negative Y faces the user, Z up. Millimetres.
# First silhouette pass: a squat wedge, broad at the cheeks, tapering into roof.
loft8("Single faceted core silhouette", [
    (46,-37,36,8,5), (54,-44,38,10,15), (54,-42,37,10,36),
    (44,-30,32,8,55), (37,-19,27,7,66)], graphite)

# Front lower chin, cheek facets and side plates.  Their dark seam makes the
# complex armor read as an assembly rather than one smooth box.
prism("projecting front chin", [(-31,-45,11),(31,-45,11),(37,-46,20),
       (34,-45,29),(-34,-45,29),(-37,-46,20)], (0,-3,0), armor)
for sign in (-1,1):
    x=lambda q:sign*q
    side="Left" if sign<0 else "Right"
    prism(side+" upper faceted cheek",[(x(34),-43,29),(x(49),-37,24),
          (x(54),-23,31),(x(50),-19,47),(x(40),-28,53),(x(32),-33,39)],
          (sign*2,0,0),armor)
    prism(side+" side armor shield",[(x(53),-25,15),(x(56),-11,17),
          (x(56),18,23),(x(51),29,36),(x(51),-16,36)],
          (sign*2,0,0),armor)
    # Slanted orange exoskeleton overhead, like the reference's shoulder ribs.
    beam(side+" orange windshield spar lower",(x(34),-45,30),(x(37),-31,54),5,orange)
    beam(side+" orange windshield spar roof",(x(37),-31,54),(x(35),-15,65),5,orange)
    beam(side+" orange roof shoulder",(x(35),-15,65),(x(38),20,58),4,orange)
    beam(side+" gray outer roof spar",(x(43),-18,58),(x(45),18,52),6,armor)
    beam(side+" cheek orange slash",(x(48),-41,26),(x(43),-29,41),3.6,orange)
    # Large circular side pivot is an important recognition cue.
    cylinder(side+" hinge boss",(x(56),13,34),12,3.5,black,"X")
    ring(side+" hinge orange rim",(x(58.2),13,34),9.8,7.1,2,orange,"X")
    cylinder(side+" hinge core",(x(58.5),13,34),5.9,1.2,armor,"X")
    cylinder(side+" hinge center",(x(59.3),13,34),1.7,.8,black,"X")

# Louver sets flank the central camera; keep the full front face open and dark.
for sign in (-1,1):
    side="Left" if sign<0 else "Right"
    x0=sign*39
    prism(side+" black vent recess",[(x0-12,-47,12),(x0+12,-47,12),
        (x0+11,-47,35),(x0-11,-47,35)],(0,-1.3,0),black)
    for j in range(4):
        z=16+j*4.2
        cube(side+f" horizontal louver {j+1}",(x0,-49,z),(22,1.6,1.6),graphite,.3)
    for j in range(3):
        x=sign*(36+j*3.3)
        beam(side+f" orange gill {j+1}",(x,-50,34),(x+sign*2,-50,26),1.7,orange)
    for ix in range(2):
        for iz in range(3):
            cylinder(side+f" acoustic port {ix}-{iz}",(sign*(17+ix*3.5),-49.15,17+iz*3.5),1.0,.7,black,"Y")

# Panoramic windshield: one large six-sided sloping panel, with side glazing.
# A smoky translucent single sheet sits on a black gasket and thin gray frame.
glass_front=[(-29,-47,31),(29,-47,31),(34,-42,41),(33,-31,54),
             (27,-23,63),(-27,-23,63),(-33,-31,54),(-34,-42,41)]
prism("deep canopy gasket",[(x,y+.75,z) for x,y,z in glass_front],(0,1.6,0),black,
      "Cockpit / canopy",.3)
prism("smoked panoramic canopy",glass_front,(0,1.35,0),glass,"Cockpit / canopy",.2)
for i in range(len(glass_front)):
    p,q=glass_front[i],glass_front[(i+1)%len(glass_front)]
    beam(f"canopy perimeter {i+1}",p,q,1.35,roofmat,"Cockpit / canopy")
for sign in (-1,1):
    x=lambda q:sign*q
    prism(("L" if sign<0 else "R")+" canopy side pane",
          [(x(34),-42,41),(x(36),-29,51),(x(32),-18,59),(x(27),-23,63)],
          (sign*.6,0,0),glass,"Cockpit / canopy",.15)

# Two short slanted eye bars immediately in front of the tinted surface are a
# render stand-in for addressable LEDs behind a real canopy; their final light
# pipes and electronics require later measurements.
for sign in (-1,1):
    side="L" if sign<0 else "R"
    beam(side+" illuminated eye",(sign*27,-47.9,39.4),
         (sign*10,-47.9,35.6),2.2,amber,"Cockpit / lighting")
    beam(side+" inner eye tip",(sign*10,-47.9,35.6),
         (sign*7.8,-47.7,36.8),1.45,amber,"Cockpit / lighting")

# Camera below the canopy, proud of the front mask.
cube("square front camera socket",(0,-50.6,18.6),(19,6,18),orange,2,"Cockpit / camera")
cube("dark camera inset",(0,-54.1,18.6),(14,1.5,13),black,1.5,"Cockpit / camera")
cylinder("camera lens barrel",(0,-55.2,18.6),5.6,2.3,graphite,"Y","Cockpit / camera")
ring("camera silver inner rim",(0,-56.8,18.6),4.5,3.5,1,steel)
cylinder("camera optical element",(0,-57.0,18.6),3.5,.9,lens,"Y","Cockpit / camera")
cylinder("camera reflective pupil",(.7,-57.5,19.3),1.2,.2,black,"Y","Cockpit / camera")

# Roof layering and fastening give the pod a believable 3D-printed assembly.
prism("roof upper access plate",[(-25,-18,66),(25,-18,66),(30,7,66),
       (22,26,66),(-22,26,66),(-30,7,66)],(0,0,2.2),roofmat)
prism("roof central black service slot",[(-18,4,68.3),(18,4,68.3),
       (15,19,68.3),(-15,19,68.3)],(0,0,.5),black)
for x in (-23,23):
    for y in (-10,17):
        screw(f"roof M3 screw {x} {y}",(x,y,69),"Z")
for sign in (-1,1):
    for j,y in enumerate((-11,-2,7)):
        screw(f"shoulder screw {sign} {j}",(sign*46,y,59-j*.8),"Z")

# Rear phone cradle, with a central crossbar and two vivid side clamps.
for sign in (-1,1):
    x=sign*31
    beam(("L" if sign<0 else "R")+" rear phone upright",
         (x,30,33),(x,43,90),5,graphite,"Phone cradle")
    beam(("L" if sign<0 else "R")+" orange phone grip",
         (x-sign*2,43,56),(x-sign*2,43,88),4,orange,"Phone cradle")
cube("phone cradle lower shelf",(0,36,37),(70,15,4),graphite,1,"Phone cradle")
cube("phone cradle back crossbar",(0,43,85),(67,4,5),graphite,1,"Phone cradle")

# Four small separate desk feet, not a thick slab: this is the characteristic
# stance in the selected reference photo.  The feet are a separate desk cradle.
for signx in (-1,1):
    for signy in (-1,1):
        x,y=signx*39,signy*27
        beam(f"desk cradle outrigger {signx} {signy}",(x,y,8),
             (signx*50,signy*36,-9),8,graphite,"Desktop cradle")
        cube(f"desk foot {signx} {signy}",(signx*50,signy*36,-10),
             (17,12,5),graphite,1.2,"Desktop cradle")
        cube(f"foot orange inset {signx} {signy}",(signx*50,signy*36,-6.9),
             (9,6,.9),orange,.25,"Desktop cradle")

# Docking underside and four visual magnet disks.  Contact layout is only a
# *placeholder*; the mating electrical/mechanical adapter is not yet engineered.
cube("underside docking recess",(0,0,4.2),(73,37,1.3),black,2,"Dock placeholder")
cube("four contact recess",(0,0,2.9),(30,15,1.2),graphite,1.7,"Dock placeholder")
for x in (-7.5,-2.5,2.5,7.5):
    cylinder(f"signal contact {x}",(x,0,1.9),1.35,1.5,gold,"Z","Dock placeholder")
for x in (-35,35):
    for y in (-17,17):
        cylinder(f"magnet placeholder {x} {y}",(x,y,2.0),4.2,1.3,steel,"Z","Dock placeholder")


def aim(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()


cube("studio floor",(0,0,-14),(500,500,1),backdrop,.0,"Presentation")
for name,position,power,size in [
    ("large left softbox",(-130,-150,200),1400,180),
    ("upper right fill",(130,60,170),950,155),
    ("front rim",(40,-200,95),480,90),
]:
    bpy.ops.object.light_add(type="AREA",location=position)
    ob=bpy.context.object;ob.name=name;ob.data.energy=power;ob.data.size=size
    aim(ob,(0,0,32))

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=48
scene.view_settings.view_transform="AgX"
scene.view_settings.look="AgX - Medium High Contrast"
scene.render.resolution_x=1400
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.8,.81,.83,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.6
scene.render.image_settings.file_format="PNG"


def render(name, position, point, scale):
    bpy.ops.object.camera_add(location=position)
    cam=bpy.context.object;cam.name="CAM_"+name
    aim(cam,point)
    cam.data.type="ORTHO";cam.data.ortho_scale=scale
    scene.camera=cam
    scene.render.filepath=os.path.join(OUT,name+".png")
    bpy.ops.render.render(write_still=True)
    cam.hide_render=True


bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT,"Lingxi-Mecha-Cockpit-Visual-v2.blend"))
render("cockpit-front-three-quarter-v2",(142,-190,125),(0,-2,35),164)
render("cockpit-front-v2",(0,-230,49),(0,0,35),145)
render("cockpit-side-v2",(230,-20,70),(0,0,35),165)
render("cockpit-top-v2",(0,-15,245),(0,0,35),155)

print("Built visual cockpit v2; dimensions and interfaces provisional")
