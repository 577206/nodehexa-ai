"""Small, physical canopy-frame details for the R06 FreeCAD assembly.

All dimensions are millimetres.  X is lateral, -Y faces the viewer, +Y goes
behind the glazing, and Z is up.  ``stations`` contains (z, y, half_width).

The two 0.8 mm longitudinal ribs follow X=+/-(half_width-7).  Their front
surfaces are Y=station_y+1.9 and they extend 0.8 mm rearward.  A bottom tie
joins them into one valid solid and lies inside the existing P03 bottom rail.
Small pads below the intermediate folds overlap P03's horizontal beams;
the caller must fuse extra_frame_shape into P03 rather than export it as a
second coincident part.

The three joiners are separate parts, with 9 x 2.4 mm frontal bodies, a blind
central slot and two bored pin seats.  Their Y setbacks account for the pane
slope above each fold, so the top of P06 cannot penetrate the steep G10 pane.
Their rear attachment tongue meets, but does not overlap, the back face of
P03's horizontal beam at Y=station_y+1.92.  These are appearance-prototype
dimensions; pin seats, thin ribs and retention need physical manufacturing
and assembly validation.

Usage::

    extra_frame, joiners = build_canopy_details(stations)
    frame = frame.fuse(extra_frame).removeSplitter()
    # joiners[0:3] replace P04, P05, P06 respectively.

``_standalone_check()`` performs a stand-alone geometry check against the
unchanged R05 canopy in the existing CAD file.  Call it explicitly from a
small FreeCADCmd runner, since FreeCADCmd does not always set __name__ to
"__main__".  It does not build, export, save or otherwise alter that document
or the R06 assembly.
"""

import json
from pathlib import Path

import FreeCAD as A
import Part


RIB_WIDTH = 0.8
RIB_FRONT_SETBACK = 1.9
RIB_DEPTH = 0.8
JOINER_HALF_HEIGHT = 1.2
GLASS_Y_THICKNESS = 1.0
GLASS_CLEARANCE = 0.35


def _v(*coordinates):
    return A.Vector(*map(float, coordinates))


def _box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, _v(x, y, z))


def _panel(points, depth):
    vertices = [_v(*point) for point in points]
    face = Part.Face(Part.makePolygon(vertices + [vertices[0]]))
    return face.extrude(_v(0, depth, 0))


def _fuse(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def _require_single(shape, label):
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1 or shape.Volume <= 0:
        raise ValueError(f"{label}: expected one valid positive-volume solid")
    return shape


def _joiner_setback(previous, current, following):
    z, y, _ = current
    before_slope = abs((y - previous[1]) / (z - previous[0]))
    after_slope = abs((following[1] - y) / (following[0] - z))
    return max(2.4, GLASS_Y_THICKNESS + max(before_slope, after_slope)
               * JOINER_HALF_HEIGHT + GLASS_CLEARANCE)


def build_canopy_details(stations):
    """Return (one extra frame solid, three independent valid joiner solids).

    The return order of joiners is the order of the three internal stations.
    The caller owns the document objects, part IDs and export operations.
    """
    stations = [tuple(map(float, station)) for station in stations]
    if len(stations) != 5 or any(len(station) != 3 for station in stations):
        raise ValueError("Expected five (z, y, half_width) canopy stations")
    if any(b[0] <= a[0] for a, b in zip(stations, stations[1:])):
        raise ValueError("Canopy stations must have strictly increasing Z")
    if any(station[2] <= 8 for station in stations):
        raise ValueError("Canopy is too narrow for the existing 7 mm wing facets")

    ribs = []
    half_rib = RIB_WIDTH / 2
    for sign in (-1, 1):
        for a, b in zip(stations, stations[1:]):
            z0, y0, w0 = a
            z1, y1, w1 = b
            x0 = sign * (w0 - 7)
            x1 = sign * (w1 - 7)
            ribs.append(_panel([
                (x0 - half_rib, y0 + RIB_FRONT_SETBACK, z0),
                (x0 + half_rib, y0 + RIB_FRONT_SETBACK, z0),
                (x1 + half_rib, y1 + RIB_FRONT_SETBACK, z1),
                (x1 - half_rib, y1 + RIB_FRONT_SETBACK, z1),
            ], RIB_DEPTH))
        # These tabs are wholly behind the glass and positively engage the
        # P03 cross-beams below the crease, without requiring a fragile point.
        for z, y, width in stations[1:-1]:
            x = sign * (width - 7)
            ribs.append(_box(x - .45, y + 1.78, z - .30, .90, 1.0, .22))

    z0, y0, w0 = stations[0]
    rib_x = w0 - 7
    ribs.append(_box(-rib_x - half_rib, y0 + 1.9, z0 - .30,
                     2 * (rib_x + half_rib), .8, .80))
    extra_frame = _require_single(_fuse(ribs), "extra_frame")

    joiners = []
    for index, (z, y, _width) in enumerate(stations[1:-1], start=1):
        setback = _joiner_setback(stations[index - 1], stations[index], stations[index + 1])
        front_y = y + setback
        body = _box(-4.5, front_y, z - JOINER_HALF_HEIGHT, 9.0, 1.4,
                    2 * JOINER_HALF_HEIGHT)
        tongue = _box(-3.3, y + 1.92, z - .30, 6.6,
                      setback + .35 - 1.92, .60)
        body = body.fuse(tongue)
        for x in (-3.0, 3.0):
            boss = Part.makeCylinder(.75, .65, _v(x, front_y - .30, z), _v(0, 1, 0))
            body = body.fuse(boss)
            seat = Part.makeCylinder(.30, .42, _v(x, front_y - .31, z), _v(0, 1, 0))
            body = body.cut(seat)
        body = body.cut(_box(-1.75, front_y - .01, z - .35, 3.5, .56, .70))
        joiners.append(_require_single(body.removeSplitter(), f"P{index + 3:02}"))
    return extra_frame, joiners


def _standalone_check():
    stations = [(33, -53, 23), (40, -52, 27), (58, -42, 29),
                (73, -27, 24), (81, -15, 20)]
    extra_frame, joiners = build_canopy_details(stations)
    root = Path(__file__).resolve().parents[1]
    reference = A.openDocument(str(root / "03_assembly/Lingxi_Cockpit_R05.FCStd"))
    try:
        base_frame = reference.getObject("P03").Shape
        glazing = [reference.getObject(f"G{i:02}").Shape for i in range(1, 13)]
        combined = _require_single(base_frame.fuse(extra_frame).removeSplitter(), "combined_P03")
        report = {"extra_frame": {"valid": extra_frame.isValid(), "solids": len(extra_frame.Solids)},
                  "combined_P03": {"valid": combined.isValid(), "solids": len(combined.Solids)},
                  "extra_frame_glass_overlap_mm3": max(extra_frame.common(g).Volume for g in glazing),
                  "extra_frame_P03_common_mm3": extra_frame.common(base_frame).Volume,
                  "joiners": []}
        assert report["extra_frame_glass_overlap_mm3"] < 1e-7
        assert report["extra_frame_P03_common_mm3"] > 0
        for index, shape in enumerate(joiners, start=1):
            overlap = max(shape.common(glass).Volume for glass in glazing)
            frame_overlap = shape.common(base_frame).Volume
            frame_distance = shape.distToShape(base_frame)[0]
            entry = {"id": f"P{index + 3:02}", "valid": shape.isValid(),
                     "solids": len(shape.Solids),
                     "front_setback_mm": round(_joiner_setback(stations[index - 1], stations[index], stations[index + 1]), 6),
                     "glass_overlap_mm3": overlap, "P03_overlap_mm3": frame_overlap,
                     "P03_distance_mm": frame_distance}
            report["joiners"].append(entry)
            assert overlap < 1e-7, entry
            assert frame_overlap < 1e-7 and frame_distance < 1e-7, entry
        print("CANOPY_DETAILS_SELF_CHECK " + json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        A.closeDocument(reference.Name)


if __name__ == "__main__":
    _standalone_check()
