#!/usr/bin/env python3
"""Build a single-mesh NodeHexa preview from the repository binary STLs.

The output is intentionally a compatibility model: one STL that FreeCAD and
slicers can display without resolving dozens of repeated document objects.
It uses the same reference-fit pose as build_nodehexa_assembly.FCMacro.
"""

from __future__ import annotations

import math
import os
import struct
from pathlib import Path


ROOT = Path("/Users/dyke_4/Documents/Codex/2026-10-21/nodehexa-ai/repository")
STL_DIR = ROOT / "mechanism" / "hexapod"
OUT = ROOT / "mechanism" / "assembly" / "NodeHexa-Whole-Robot-Combined.STL"

PAIR_SPACING = 8.0
SHIN_PITCH = 65.0
FOOT_PANEL_TILT = -20.0

LEG_LAYOUT = (
    ("FL", (48.0, 35.0, 10.0), 55.0),
    ("ML", (0.0, 39.0, 10.0), 90.0),
    ("RL", (-48.0, 35.0, 10.0), 125.0),
    ("FR", (48.0, -35.0, 10.0), -55.0),
    ("MR", (0.0, -39.0, 10.0), -90.0),
    ("RR", (-48.0, -35.0, 10.0), -125.0),
)


def matrix_mul(a, b):
    return tuple(
        tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3))
        for r in range(3)
    )


def matrix_vec(m, v):
    return tuple(sum(m[r][k] * v[k] for k in range(3)) for r in range(3))


def rotation_xyz(rx=0.0, ry=0.0, rz=0.0):
    rx, ry, rz = (math.radians(v) for v in (rx, ry, rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    mx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    my = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    mz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))
    return matrix_mul(matrix_mul(mz, my), mx)


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def unit(v):
    length = math.sqrt(sum(x * x for x in v))
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return tuple(x / length for x in v)


def read_binary_stl(path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"Invalid STL: {path}")
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + count * 50:
        raise ValueError(f"Expected a binary STL: {path}")
    triangles = []
    offset = 84
    for _ in range(count):
        values = struct.unpack_from("<12fH", data, offset)
        triangles.append(
            (
                (values[3], values[4], values[5]),
                (values[6], values[7], values[8]),
                (values[9], values[10], values[11]),
            )
        )
        offset += 50
    return triangles


CACHE = {}


def source(name):
    if name not in CACHE:
        tris = read_binary_stl(STL_DIR / f"{name}.STL")
        points = [p for tri in tris for p in tri]
        mins = tuple(min(p[i] for p in points) for i in range(3))
        maxs = tuple(max(p[i] for p in points) for i in range(3))
        centre = tuple((mins[i] + maxs[i]) * 0.5 for i in range(3))
        CACHE[name] = (tris, centre)
    return CACHE[name]


ALL_TRIANGLES = []


def place(name, target, rotation):
    tris, centre = source(name)
    for tri in tris:
        transformed = tuple(add(matrix_vec(rotation, sub(p, centre)), target) for p in tri)
        ALL_TRIANGLES.append(transformed)


def box(size, centre, rotation):
    sx, sy, sz = (v * 0.5 for v in size)
    vertices = (
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
    )
    faces = (
        (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
    )
    world = tuple(add(matrix_vec(rotation, v), centre) for v in vertices)
    ALL_TRIANGLES.extend(tuple(world[i] for i in face) for face in faces)


def leg_world(anchor, yaw, local):
    return add(anchor, matrix_vec(rotation_xyz(rz=yaw), local))


def leg_rotation(yaw, rx=0.0, ry=0.0, rz=0.0):
    return matrix_mul(rotation_xyz(rz=yaw), rotation_xyz(rx, ry, rz))


def build():
    # Body
    flat = rotation_xyz(rx=-90)
    place("TKRC-BodyButtom", (0, 0, 0), flat)
    place("TKRC-BodyCenter", (0, 0, 15), flat)
    place("TKRC-BodyTop", (0, 0, 34), flat)
    place("TKRC-BodySideWall", (0, 37, 17), rotation_xyz(rx=90))
    place("TKRC-BodySideWall", (0, -37, 17), rotation_xyz(90, 0, 180))
    place("TKRC-BodyBackWall", (-61, 0, 17), rotation_xyz(90, 0, 90))
    place("TKRC-BodyBackWall", (61, 0, 17), rotation_xyz(90, 0, -90))

    for _code, anchor, yaw in LEG_LAYOUT:
        parts = (
            ("TKRC-JointCross", (8, 0, 22), (0, 0, 0)),
            ("TKRC-JointTop", (20, PAIR_SPACING, 31), (0, 0, 0)),
            ("TKRC-JointDown", (20, -PAIR_SPACING, 13), (0, 0, 0)),
            ("TKRC-ThighTop", (40, PAIR_SPACING, 23), (0, 0, 0)),
            ("TKRC-ThighBottom", (40, -PAIR_SPACING, 23), (0, 0, 0)),
            ("TKRC-LegTop", (85, PAIR_SPACING, 20), (0, 5, 0)),
            ("TKRC-LegBottom", (85, -PAIR_SPACING, 20), (0, 5, 0)),
            ("TKRC-FootTop", (137, PAIR_SPACING - 1, -10), (0, SHIN_PITCH, 0)),
            ("TKRC-FootButtom", (137, -PAIR_SPACING + 1, -10), (0, SHIN_PITCH, 0)),
            ("TKRC-FootGround", (153, 0, -22), (-90, FOOT_PANEL_TILT, 0)),
            ("TKRC-FootTip", (170, 0, -57), (0, 0, 0)),
        )
        for name, local, angles in parts:
            place(name, leg_world(anchor, yaw, local), leg_rotation(yaw, *angles))

        for local, angles in (
            ((8, 0, 22), (0, 0, 0)),
            ((48, 0, 22), (0, 0, 0)),
            ((115, 0, 8), (0, SHIN_PITCH, 0)),
        ):
            box((23, 12.5, 24), leg_world(anchor, yaw, local), leg_rotation(yaw, *angles))

    box((72, 32, 3), (0, 0, 25), rotation_xyz())


def write_binary_stl(path):
    header = b"NodeHexa whole-robot compatibility mesh".ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(ALL_TRIANGLES)))
        for p1, p2, p3 in ALL_TRIANGLES:
            normal = unit(cross(sub(p2, p1), sub(p3, p1)))
            handle.write(struct.pack("<12fH", *(normal + p1 + p2 + p3), 0))


if __name__ == "__main__":
    os.makedirs(OUT.parent, exist_ok=True)
    build()
    write_binary_stl(OUT)
    print(f"Wrote {len(ALL_TRIANGLES):,} triangles to {OUT}")
