"""Build a separated mechanical prototype for printing with FreeCADCmd.

This uses the same global silhouette as build_visual_cockpit.py, but it is a
functional *fit prototype*: shell seam, visor aperture, camera bore, rear
cradle and desk cradle are separate. Real PCB, battery and mating dock sizes
must be measured before production.
"""
import json
import os
import math

import FreeCAD as App
import Part
import Mesh

HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"output","print_parts")
os.makedirs(OUT,exist_ok=True)
with open(os.path.join(HERE,"parameters.json"),encoding="utf8") as f:P=json.load(f)

def V(x,y,z):return App.Vector(float(x),float(y),float(z))
def wire(hx,yf,yr,cut,z):
    pts=[(-hx+cut,yf),(hx-cut,yf),(hx,yf+cut),(hx,yr-cut),
         (hx-cut,yr),(-hx+cut,yr),(-hx,yr-cut),(-hx,yf+cut)]
    vv=[V(x,y,z) for x,y in pts]
    return Part.makePolygon(vv+[vv[0]])
def loft(levels):return Part.makeLoft([wire(*a) for a in levels],True,False)
def box(x,y,z,dx,dy,dz):return Part.makeBox(dx,dy,dz,V(x,y,z))
def cyl(x,y,z,r,h,direction=(0,0,1)):
    return Part.makeCylinder(r,h,V(x,y,z),V(*direction))
def poly(points,vector):
    p=[V(*a) for a in points]
    return Part.Face(Part.makePolygon(p+[p[0]])).extrude(V(*vector))
def beam(a,b,r):
    va=V(*a);vb=V(*b);d=vb-va
    return Part.makeCylinder(r,d.Length,va,d)
def clean(name,shape):
    shape=shape.removeSplitter()
    if shape.isNull() or not shape.isValid() or shape.Volume<1:
        raise RuntimeError("Invalid part: "+name)
    return shape

doc=App.newDocument("Lingxi_mecha_cockpit_print_prototype")
objects=[]
def add(name,shape,color):
    shape=clean(name,shape)
    ob=doc.addObject("PartDesign::Feature",name)
    ob.Label=name.replace("_"," ")
    ob.Shape=shape
    if ob.ViewObject:
        ob.ViewObject.ShapeColor=color
    objects.append(ob)
    Mesh.export([ob],os.path.join(OUT,name+".stl"))
    print(name,round(shape.Volume,1),"mm3",len(shape.Solids),"solid(s)")
    return ob

# The octagonal wedge makes the exterior read as the selected mecha design.
outer=loft([(46,-37,36,8,5),(54,-44,38,10,15),(54,-42,37,10,36),
            (44,-30,32,8,55),(37,-19,27,7,66)])
inner=loft([(43.5,-34.5,33.5,7,7.6),(51.5,-41.5,35.5,8.5,17),
            (51.5,-39.5,34.5,8.5,35),(41.5,-27.5,29.5,6.5,53),
            (34.5,-16.5,24.5,5.5,63.5)])
shell=outer.cut(inner)
seam=23.0
lower=shell.common(box(-100,-100,0,200,200,seam))
upper=shell.common(box(-100,-100,seam,200,200,80))

# Tongue/groove at shell seam. At 0.4 mm nominal clearance this must be checked
# with a small fit coupon on the user's printer before a full print.
lip_outer=loft([(47,-35,30,6,seam-1),(47,-35,30,6,seam+3)])
lip_inner=loft([(44,-32,27,5,seam-1.2),(44,-32,27,5,seam+3.2)])
lower=lower.fuse(lip_outer.cut(lip_inner))
upper=upper.cut(loft([(47.4,-35.4,30.4,6.2,seam-.01),
                      (47.4,-35.4,30.4,6.2,seam+3.3)]))

# Sloping windshield opening, preserving the faceted corner posts. The PET
# canopy template is kept separate from the FDM printed shell.
windshield=[(-27,-47,32),(27,-47,32),(31,-39.8,41),(30,-30.2,53),
            (24,-23,62),(-24,-23,62),(-30,-31,53),(-31,-42,41)]
windshield[-2]=(-30,-30.2,53)
windshield[-1]=(-31,-39.8,41)
upper=upper.cut(poly(windshield,(0,35,0)))
visor=poly([(-29,-47.5,31.5),(29,-47.5,31.5),(34,-39.9,41),
            (33,-29.5,54),(27,-22.3,63),(-27,-22.3,63),(-33,-29.5,54),
            (-34,-39.9,41)],(0,1.1,0))

# Camera bore below glass and the two microphone grille arrays. Camera and
# microphone placement remain cosmetic until verified against actual boards.
lower=lower.cut(cyl(0,-50,18.5,5.7,30,(0,1,0)))
for sx in (-1,1):
    for z in (16.5,20,23.5):
        for x in (17,20.5):
            lower=lower.cut(cyl(sx*x,-50,z,1.1,20,(0,1,0)))

# Four anti-rotation alignment posts in the lower shell; matching bores in
# the upper. They do not depend on unknown PCB holes.
for x in (-38,38):
    for y in (-23,23):
        lower=lower.fuse(cyl(x,y,seam-1.2,2.4,5.0))
        upper=upper.cut(cyl(x,y,seam,2.9,5.3))

# Recesses only. NO electrical power passes through the four signal contacts.
for x in (-33,33):
    for y in (-16,16):
        lower=lower.cut(cyl(x,y,4.9,3.15,2.7))
for x in (-7.5,-2.5,2.5,7.5):
    lower=lower.cut(cyl(x,0,4.9,1.0,3.3))

add("01_lower_battery_tray",lower,(.13,.14,.16))
add("02_upper_faceted_shell",upper,(.20,.22,.23))
add("03_smoked_visor_template",visor,(.10,.09,.08))

# Four separate orange windshield ribs. Use the 3-piece arms in the render as
# reference; each single printed rib is an integral L-shaped cosmetic piece.
for side in (-1,1):
    def p(x,y,z):return (side*x,y,z)
    arm=beam(p(34,-45,30),p(37,-31,54),2.7)
    arm=arm.fuse(beam(p(37,-31,54),p(35,-15,65),2.7))
    arm=arm.fuse(beam(p(35,-15,65),p(38,20,58),2.3))
    # The two pin shafts are intended to be dry-fitted, then bonded if needed.
    arm=arm.fuse(beam(p(35,-42,32),p(37,-40,32),1.5))
    add("04_"+("left" if side<0 else "right")+"_orange_canopy_rib",
        arm,(.94,.22,.02))

for side in (-1,1):
    x=side*39
    # Louver frame with attached horizontal slats (single printable piece).
    grille=box(x-12,-49,12,24,2,25)
    grille=grille.cut(box(x-10,-49.5,14,20,3,21))
    for z in (16,20.5,25,29.5,34):
        grille=grille.fuse(box(x-11,-50,z,22,2,1.7))
    add("05_"+("left" if side<0 else "right")+"_vent_grille",
        grille,(.06,.065,.07))

# Square orange camera socket, separate so it can be removed for lens focus.
bezel=box(-9.5,-53.5,10,19,6,18)
bezel=bezel.cut(cyl(0,-54,19,5.8,8,(0,1,0)))
add("06_camera_bezel",bezel,(.94,.22,.02))

# Phone stand supports a real phone only after a loading/stability test. It is
# intentionally independent of the cockpit's electronics compartment.
for side in (-1,1):
    x=side*31
    rail=beam((x,30,34),(x,43,88),2.8)
    rail=rail.fuse(box(x-3,40,54,6,5,35))
    add("07_"+("left" if side<0 else "right")+"_phone_upright",rail,
        (.18,.19,.20))
phone_shelf=box(-35,28,34,70,16,4).fuse(box(-35,40,34,70,5,8))
add("08_phone_shelf",phone_shelf,(.18,.19,.20))

# Desk cradle uses four discrete feet tied by a thin X-shaped underframe, so
# the cockpit can be removed without disconnecting any robot power supply.
for sx in (-1,1):
    for sy in (-1,1):
        a=(sx*39,sy*27,8);b=(sx*50,sy*36,-8)
        foot=beam(a,b,4.4).fuse(box(sx*50-8.5,sy*36-6,-12,17,12,5))
        add("09_foot_"+("L" if sx<0 else "R")+("F" if sy<0 else "B"),
            foot,(.15,.16,.18))

doc.recompute()
doc.saveAs(os.path.join(OUT,"Lingxi-Mecha-Cockpit-Printable-v2.FCStd"))
print("Wrote",len(objects),"separate prototype STL parts")
