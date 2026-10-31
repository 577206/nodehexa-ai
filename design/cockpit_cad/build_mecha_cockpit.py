"""Run with FreeCADCmd: build the provisional Lingxi cockpit and printable parts.

The JSON file is the editable dimensional source of truth. The resulting FCStd
contains separate parts for visual inspection. Board holes and the robot adapter
are intentionally absent until the physical parts have been measured.
"""

import json
import math
import os
import sys

import FreeCAD as App
import Mesh
import Part


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(HERE, "parameters.json"), encoding="utf-8") as stream:
    P = json.load(stream)


def v(x, y, z):
    return App.Vector(float(x), float(y), float(z))


def bevel_wire(length, width, bevel, z, ycenter=0):
    a, b, c = length / 2, width / 2, bevel
    points = [(-a + c, -b), (a - c, -b), (a, -b + c),
              (a, b - c), (a - c, b), (-a + c, b),
              (-a, b - c), (-a, -b + c)]
    vectors = [v(x, y + ycenter, z) for x, y in points]
    return Part.makePolygon(vectors + [vectors[0]])


def plate(length, width, bevel, z, height, ycenter=0):
    return Part.Face(bevel_wire(length, width, bevel, z, ycenter)).extrude(v(0, 0, height))


def loft(levels):
    wires = [bevel_wire(*entry) for entry in levels]
    result = Part.makeLoft(wires, True, False)
    if not result.isValid():
        raise RuntimeError("Invalid loft")
    return result


def finish(shape):
    shape = shape.removeSplitter()
    if shape.isNull() or not shape.isValid() or shape.Volume <= 0:
        raise RuntimeError("Invalid or empty CAD solid")
    return shape


doc = App.newDocument("Lingxi_Mecha_Cockpit_Provisional")


def group(name, label):
    obj = doc.addObject("App::DocumentObjectGroup", name)
    obj.Label = label
    return obj


print_parts = group("PrintableParts", "01 Printable prototype parts")
reference = group("ReferenceEnvelopes", "02 Provisional component envelopes - DO NOT DRILL")


def part(name, label, shape, color, container=print_parts, transparency=0):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = finish(shape)
    container.addObject(obj)
    if obj.ViewObject:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
        obj.ViewObject.DisplayMode = "Flat Lines"
    return obj


length = P["body_length"]
width = P["body_width"]
wall = P["wall"]
tray_top = P["tray_height"]
height = P["body_height"]

# Low battery tray, open at the top. The raised inner perimeter is deliberately
# left without board standoffs: actual hole locations are not yet known.
tray = plate(length, width, 6, 0, tray_top)
tray = tray.cut(plate(length - 2 * wall, width - 2 * wall, 4.5,
                      P["floor"], tray_top + 1))
# A short keyed-by-shape locating rim gives the two printed shell halves a
# repeatable fit without assuming any of the unknown PCB mounting holes.
lip_length = length - 2 * wall - 2 * P["fit_clearance"] - 1.4
lip_width = width - 2 * wall - 2 * P["fit_clearance"] - 1.4
lip_base = plate(length - 2, width - 2, 5,
                 tray_top - 1, 1).cut(plate(lip_length - 3,
                 lip_width - 3, 3, tray_top - 1, 1.1))
lip_rise = plate(lip_length, lip_width, 4,
                 tray_top - 0.5, 3.5).cut(plate(lip_length - 3,
                 lip_width - 3, 3, tray_top - 0.5, 3.6))
tray = tray.fuse(lip_base).fuse(lip_rise)
foot = plate(P["dock_foot_length"], P["dock_foot_width"], 4,
             -P["dock_foot_depth"], P["dock_foot_depth"])
tray = tray.fuse(foot)

# Open underside pockets for four magnets. The floor above them remains solid.
for x in (-33, 33):
    for y in (-13, 13):
        tray = tray.cut(Part.makeCylinder(P["magnet_pocket_diameter"] / 2,
                        P["magnet_pocket_depth"], v(x, y, -P["dock_foot_depth"])))

# Four provisional signal-pad bores: UART TX/RX/GND + dock detect, no power.
for x in (-9, -3, 3, 9):
    tray = tray.cut(Part.makeCylinder(P["pogo_pad_hole_diameter"] / 2,
                    P["dock_foot_depth"] + P["floor"] + 0.5,
                    v(x, 0, -P["dock_foot_depth"])))
tray_obj = part("BatteryTray", "Lower shell / battery tray", tray, (0.12, 0.13, 0.15))

# Faceted upper housing with open bottom and open top. A separate roof avoids a
# long unsupported bridge when FDM printing the shell upright.
outer = loft([
    (length, width, 6, tray_top, 0),
    (length - 4, width - 4, 7, 38, 0),
    (length - 22, width - 14, 8, height - 3, 3),
])
inner = loft([
    (length - 2 * wall, width - 2 * wall, 4.5, tray_top - 1, 0),
    (length - 4 - 2 * wall, width - 4 - 2 * wall, 5.5, 38, 0),
    (length - 22 - 2 * wall, width - 14 - 2 * wall,
     6.5, height - 2, 3),
])
hull = outer.cut(inner)

# Camera below the panoramic eye visor. These openings leave a printable front
# border; final camera and screen retainers are added after exact PCB measuring.
eye_z = 41
hull = hull.cut(Part.makeBox(P["visor_opening_width"], 40,
                 P["visor_opening_height"],
                 v(-P["visor_opening_width"] / 2, -50, eye_z)))
hull = hull.cut(Part.makeCylinder(P["camera_hole_diameter"] / 2,
                 40, v(0, -50, 31), v(0, 1, 0)))

# Side acoustic holes near front, plus rear access slit for a removable phone
# rest. These are illustrative locations pending microphone orientation.
for x in (-40, -36, 36, 40):
    for z in (29, 33):
        hull = hull.cut(Part.makeCylinder(1.2, 37,
                        v(x, -50, z), v(0, 1, 0)))
hull_obj = part("UpperHull", "Faceted upper housing / open roof", hull,
                (0.22, 0.23, 0.25))

# Color-separated optional pieces. These are simple printed inserts, not
# bonded into the main shell, so they can be printed orange on a single-color
# printer and removed if a real PCB or connector needs the same space.
camera_ring = Part.makeCylinder(8.2, 1.8, v(0, -37, 31), v(0, 1, 0))
camera_ring = camera_ring.cut(Part.makeCylinder(5.6, 2,
                              v(0, -37.1, 31), v(0, 1, 0)))
ring_obj = part("CameraBezel", "Orange camera bezel - optional",
                camera_ring, (0.94, 0.21, 0.02))
left_trim = part("LeftAccent", "Left orange side trim - optional",
                 Part.makeBox(2.5, 26, 5, v(-55, -13, 31)),
                 (0.94, 0.21, 0.02))
right_trim = part("RightAccent", "Right orange side trim - optional",
                  Part.makeBox(2.5, 26, 5, v(52.5, -13, 31)),
                  (0.94, 0.21, 0.02))

roof = plate(length - 22, width - 14, 8, height - 3, 3, 3)
roof_obj = part("RoofLid", "Removable roof lid", roof, (0.42, 0.43, 0.44))

# Visor is an accurately sized flat sheet *template* in the FCStd assembly,
# not a 3D-printed transparent part. Its sealing flange is to be detailed later.
front_bottom_y = -34.2
front_top_y = -29.4
panel_points = [v(-33, front_bottom_y - 0.8, 40),
                v(33, front_bottom_y - 0.8, 40),
                v(33, front_top_y - 0.8, 62),
                v(-33, front_top_y - 0.8, 62)]
panel_wire = Part.makePolygon(panel_points + [panel_points[0]])
visor = Part.Face(panel_wire).extrude(v(0, -1.2, 0))
visor_obj = part("VisorTemplate", "Smoked visor sheet - cutting template",
                 visor, (0.02, 0.025, 0.03), reference, 55)

# Separate desktop shoe. The 0.4 mm radial fit clearance is deliberately a
# starting assumption; print only a small fit coupon before finalizing.
base = plate(P["desk_base_length"], P["desk_base_width"], 12,
             -P["desk_base_height"], P["desk_base_height"])
base = base.cut(plate(P["dock_foot_length"] + 2 * P["fit_clearance"],
                      P["dock_foot_width"] + 2 * P["fit_clearance"],
                      4.4, -P["dock_foot_depth"],
                      P["dock_foot_depth"] + 0.1))
for x in (-28.5, 28.5):
    base = base.cut(Part.makeCylinder(1.7, P["desk_base_height"],
                    v(x, 45, -P["desk_base_height"])))
for x in (-52, 52):
    for y in (-42, 42):
        base = base.cut(Part.makeCylinder(5.5, 1.2,
                        v(x, y, -P["desk_base_height"])))
base_obj = part("DesktopBase", "Separate wide desktop shoe", base,
                (0.17, 0.18, 0.19))

# Detachable phone cradle for the first print: two slanted rear rails and one
# ledge. Final folding mechanism must be validated against the actual phone.
def side_rail(x):
    yz = [(38, 21), (44, 21), (58, 76), (53, 76)]
    pts = [v(x, y, z) for y, z in yz]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(v(7, 0, 0))

phone = side_rail(-32).fuse(side_rail(25))
phone = phone.fuse(Part.makeBox(72, 16, 5, v(-36, 37, 18)))
phone = phone.fuse(Part.makeBox(72, 5, 6, v(-36, 49, 18)))
for x0, xc in ((-33, -28.5), (24, 28.5)):
    phone = phone.fuse(Part.makeBox(9, 9, 21, v(x0, 40, 0)))
    phone = phone.cut(Part.makeCylinder(1.5, 16,
                      v(xc, 45, 0)))
phone_obj = part("PhoneRest", "Removable rear phone rest / fit prototype",
                 phone, (0.14, 0.15, 0.17))

# First-pass space reservations. Hide these by default because the true PCBs
# have not been measured and their mounting topology is not yet established.
battery = part("BatteryBay", "Battery bay reserved 65 x 55 x 12",
               Part.makeBox(P["battery_bay_length"], P["battery_bay_width"],
                            P["battery_bay_height"],
                            v(-P["battery_bay_length"] / 2,
                              -P["battery_bay_width"] / 2 + 3, P["floor"])),
               (0.22, 0.42, 0.72), reference, 70)
screen = part("ScreenEnvelope", "1.3 in OLED reference PCB 35.6 x 33 x 6.2",
              Part.makeBox(35.6, 6.2, 33, v(-17.8, -24, 30)),
              (0.83, 0.48, 0.12), reference, 70)

params = doc.addObject("Spreadsheet::Sheet", "Parameters")
params.Label = "Dimension source: parameters.json (mm, provisional)"
params.set("A1", "Parameter")
params.set("B1", "Value (mm)")
for row, (key, value) in enumerate(P.items(), start=2):
    if isinstance(value, (int, float)):
        params.set("A%d" % row, key)
        params.set("B%d" % row, str(value))

doc.recompute()
if doc.getObject("BatteryBay").Shape.common(tray_obj.Shape).Volume > 1:
    raise RuntimeError("Reserved battery bay intersects tray plastic")

doc.saveAs(os.path.join(OUT, "Lingxi-Mecha-Cockpit-Provisional.FCStd"))
for obj in (tray_obj, hull_obj, roof_obj, base_obj, phone_obj,
            ring_obj, left_trim, right_trim):
    path = os.path.join(OUT, "%s.stl" % obj.Name)
    Mesh.export([obj], path)
    print(obj.Name, "volume_mm3=%.1f" % obj.Shape.Volume,
          "bbox_mm=%.1f x %.1f x %.1f" % (
              obj.Shape.BoundBox.XLength, obj.Shape.BoundBox.YLength,
              obj.Shape.BoundBox.ZLength), "->", path)
print("Saved", doc.FileName)
App.closeDocument(doc.Name)
