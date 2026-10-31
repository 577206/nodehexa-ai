"""Offline performance study. Never sends commands to the robot."""
from pathlib import Path
import json
import math
import re

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
FPS = 12
DURATION = 12.0
HEART = ("01100110", "11111111", "11111111", "11111111",
         "01111110", "00111100", "00011000", "00000000")
NORMAL = ("00000000", "00111100", "01111110", "01111110",
          "01111110", "01111110", "00111100", "00000000")
SMUG = ("00000000", "00000000", "00111100", "01100110",
        "11000011", "00000000", "00000000", "00000000")
BEATS = [
    (0.0, 1.5, "01", "先问一句", "我好看吗？", "普通眼睛 · 等你看过来"),
    (1.5, 2.7, "02", "往左歪，停一下", "", "双眼变爱心 · 身体侧倾"),
    (2.7, 4.4, "03", "再往右歪", "", "另一侧停顿 · 回到中间"),
    (4.4, 5.9, "04", "心动两下", "", "爱心放大、缩小 × 2"),
    (5.9, 7.2, "05", "开始小得意", "", "轻摆一次 · 右眼爱心眨一下"),
    (7.2, 10.8, "06", "自己接住这个梗", "好了，不用夸，我自己知道。", "停顿后接台词 · 得意眼睛"),
    (10.8, 12.0, "07", "站好，眨眼收尾", "", "恢复普通眼睛 · 双眼轻眨"),
]


def smooth(a, b, t):
    u = min(1.0, max(0.0, t))
    u = u * u * (3.0 - 2.0 * u)
    return a + (b - a) * u


def curve(t, points):
    if t <= points[0][0]:
        return points[0][1]
    for (ta, a), (tb, b) in zip(points, points[1:]):
        if t <= tb:
            return smooth(a, b, (t - ta) / (tb - ta))
    return points[-1][1]


def pose(t):
    # World +X right, +Y rear, +Z up, face toward -Y. No independent neck.
    tilt = curve(t, [(0, 0), (1.5, 0), (2.05, -6), (2.7, -6),
                     (3.35, 6), (3.9, 6), (4.4, 0), (12, 0)])
    sway = 0.0
    if 5.9 <= t <= 7.1:
        u = (t - 5.9) / 1.2
        # Rest-to-rest window, no velocity jump at entry/exit.
        sway = math.sin(2 * math.pi * u) * math.sin(math.pi * u) ** 2
    pitch = curve(t, [(0, 0), (7.2, 0), (7.7, -2), (10.35, -2),
                      (10.8, 0), (12, 0)])
    return {"rx_deg": pitch, "ry_deg": tilt + 2.5 * sway,
            "rz_deg": 5 * sway, "x_mm": 2.0 * sway, "y_mm": 0.0, "z_mm": 0.0}


def eye_state(t):
    state = "normal" if t < 1.5 or t >= 10.8 else "heart"
    scale = 1.0
    if 4.4 <= t < 5.9:
        u = (t - 4.4) / 0.75
        scale = 1.0 + 0.25 * math.sin(math.pi * (u % 1.0)) ** 2
    right_close = 0.0
    if 6.65 <= t < 7.05:
        right_close = math.sin(math.pi * (t - 6.65) / 0.4) ** 2
    if 7.2 <= t < 10.8:
        state = "smug"
    both_close = 0.0
    if 11.0 <= t < 11.4:
        both_close = math.sin(math.pi * (t - 11.0) / 0.4) ** 2
    return state, scale, both_close, max(right_close, both_close)


def oled_image(t):
    from PIL import Image
    img = Image.new("1", (128, 64), 0)
    state, scale, left_close, right_close = eye_state(t)
    pattern = {"normal": NORMAL, "heart": HEART, "smug": SMUG}[state]
    glyph = Image.new("1", (8, 8), 0)
    for y, row in enumerate(pattern):
        for x, v in enumerate(row):
            glyph.putpixel((x, y), int(v))
    for cx, close in [(39, left_close), (89, right_close)]:
        w = round(32 * scale)
        h = max(3, round(w * (1 - 0.94 * close)))
        eye = glyph.resize((w, h), Image.Resampling.NEAREST)
        img.paste(eye, (cx - w // 2, 32 - h // 2))
    return img


def beat(t):
    return next((b for b in BEATS if b[0] <= t < b[1]), BEATS[-1])


def geometry():
    text = (ROOT / "firmware/include/config.h").read_text()
    keys = ["kLegMountLeftRightX", "kLegMountOtherX", "kLegMountOtherY",
            "kLegRootToJoint1", "kLegJoint1ToJoint2", "kLegJoint2ToJoint3", "kLegJoint3ToTip"]
    g = {k: float(re.search(r"const float " + k + r"\s*=\s*([\d.]+)", text)[1]) for k in keys}
    g["standby_height_mm"] = g["kLegJoint3ToTip"] * 0.9659 - g["kLegJoint2ToJoint3"] * 0.5
    return g


def prepare():
    (OUT / "textures").mkdir(parents=True, exist_ok=True)
    (OUT / "renders").mkdir(exist_ok=True)
    for i in range(round(FPS * DURATION)):
        oled_image(i / FPS).convert("RGB").save(OUT / "textures" / f"oled_{i+1:04d}.png")
    payload = {"status": "PREVIEW_NOT_HARDWARE_VALIDATED", "duration_seconds": DURATION,
               "render_fps": FPS, "coordinates": "+X right; +Y rear; +Z up; front -Y; millimeters",
               "geometry_source": "firmware/include/config.h", "geometry": geometry(),
               "beats": BEATS, "samples": [{"t": i / 50, **pose(i / 50)} for i in range(601)]}
    (OUT / "timeline.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    prepare()
