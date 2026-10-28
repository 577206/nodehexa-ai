#!/usr/bin/env python3
"""Render orthographic silhouettes of the NodeHexa body STL parts."""

from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
STL_DIR = ROOT / "mechanism" / "hexapod"
OUTPUT = ROOT / "mechanism" / "assembly" / "NodeHexa-Body-Parts-Overview.png"

PARTS = (
    ("TKRC-BodyButtom", (0, 2)),
    ("TKRC-BodyButtom-18650-2S", (0, 2)),
    ("TKRC-BodyCenter", (0, 2)),
    ("TKRC-BodyCenter-Thin", (0, 2)),
    ("TKRC-BodyTop", (0, 2)),
    ("TKRC-BodySideWall", (0, 1)),
    ("TKRC-BodyBackWall", (0, 1)),
)


def read_triangles(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
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


def font(size):
    for candidate in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_part(name, axes, width=720, height=430, supersample=3):
    triangles = read_triangles(STL_DIR / f"{name}.STL")
    projected = [tuple((p[axes[0]], p[axes[1]]) for p in tri) for tri in triangles]
    points = [point for tri in projected for point in tri]
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    size_x, size_y = max_x - min_x, max_y - min_y

    s = supersample
    canvas = Image.new("RGB", (width * s, height * s), "white")
    draw = ImageDraw.Draw(canvas)
    margin_x, margin_top, margin_bottom = 45 * s, 85 * s, 40 * s
    usable_w = width * s - margin_x * 2
    usable_h = height * s - margin_top - margin_bottom
    scale = min(usable_w / size_x, usable_h / size_y)
    origin_x = (width * s - size_x * scale) / 2
    origin_y = margin_top + (usable_h - size_y * scale) / 2

    def transform(point):
        return (
            origin_x + (point[0] - min_x) * scale,
            origin_y + (max_y - point[1]) * scale,
        )

    for triangle in projected:
        draw.polygon([transform(p) for p in triangle], fill=(80, 91, 103))

    draw.text((30 * s, 20 * s), name, font=font(28 * s), fill=(20, 25, 30))
    dimension = f"plan: {size_x:.3f} x {size_y:.3f} mm"
    draw.text((30 * s, 53 * s), dimension, font=font(19 * s), fill=(80, 90, 100))
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def main():
    tiles = [render_part(name, axes) for name, axes in PARTS]
    columns = 2
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 720, rows * 430), (238, 241, 244))
    for index, tile in enumerate(tiles):
        x = (index % columns) * 720
        y = (index // columns) * 430
        sheet.paste(tile, (x, y))
    sheet.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
