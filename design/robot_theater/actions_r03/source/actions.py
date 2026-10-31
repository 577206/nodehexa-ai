"""Three original offline performance cues, sourced to the accepted R06/EDGE50.

All eye patterns are logical 8x8 concept art, not a hardware resolution claim.
All body rotations describe the complete chassis+head target, never a neck joint.
"""
from pathlib import Path
import hashlib
import json
import math

OUT = Path(__file__).resolve().parents[1]
REPO = OUT.parents[2]
R02 = OUT.parent / "aligned_r02"
FPS = 12

PATTERNS = {
    "normal": ["00000000", "00111100", "01111110", "01111110", "01111110", "01111110", "00111100", "00000000"],
    "calm": ["00000000", "00000000", "01111110", "01111110", "00111100", "00000000", "00000000", "00000000"],
    "smile": ["00000000", "00000000", "00111100", "01100110", "11000011", "00000000", "00000000", "00000000"],
    "squint": ["00000000", "01000010", "00100100", "00011000", "00100100", "01000010", "00000000", "00000000"],
    "heart": ["01100110", "11111111", "11111111", "11111111", "01111110", "00111100", "00011000", "00000000"],
    "spark": ["00011000", "00011000", "00111100", "11111111", "11111111", "00111100", "00011000", "00011000"],
    "check": ["00000001", "00000011", "00000110", "00001100", "11011000", "01110000", "00100000", "00000000"],
    "inbox": ["00000000", "00111100", "01100110", "11000011", "11011011", "11000011", "01111110", "00000000"],
    "pupil": ["00000000", "00000000", "00011000", "00111100", "00111100", "00011000", "00000000", "00000000"],
    "wide": ["00111100", "01111110", "11100111", "11000011", "11000011", "11100111", "01111110", "00111100"],
}

ACTIONS = [
    {"id": "hold_that_compliment", "title": "被夸后努力绷住", "seconds": 9.0,
     "hook": "嘴上很淡定，眼睛先投降", "lines": [(0.35, "嗯。"), (5.10, "客观评价，我收下了。")],
     "beats": [(0, "淡定收听"), (1.3, "努力绷住"), (2.2, "开心藏不住"), (3.3, "笑眼破功"), (5.1, "收下夸奖"), (7.8, "眨眼站好")],
     "keyframes": [(1.6, "绷住"), (3.7, "破功"), (6.3, "收下")], "color": "#B85B30"},
    {"id": "gossip_radar", "title": "八卦雷达上线", "seconds": 8.0,
     "hook": "刚说不爱听，已经凑近了", "lines": [(0.20, "我本来不爱听八卦。"), (4.45, "但你可以展开说说。")],
     "beats": [(0, "先装不感兴趣"), (1.4, "左边听听"), (2.4, "右边也听听"), (3.6, "一下认真了"), (4.45, "请展开说说"), (6.7, "礼貌回正")],
     "keyframes": [(1.8, "左听"), (3.8, "认真"), (5.2, "展开说说")], "color": "#35636D"},
    {"id": "compliment_receipt", "title": "夸奖签收", "seconds": 8.0,
     "hook": "一本正经地，把夸奖存起来", "lines": [(0.20, "夸奖已签收。"), (4.00, "本人将循环回味。")],
     "beats": [(0, "等待签收"), (1.2, "收到夸奖"), (2.0, "点头盖章"), (3.1, "再确认一次"), (4.0, "开始珍藏"), (6.6, "偷偷眨眼")],
     "keyframes": [(1.5, "收到"), (2.5, "盖章"), (5.2, "珍藏")], "color": "#8B485A"},
]


def curve(t, points):
    if t <= points[0][0]:
        return points[0][1]
    for (ta, a), (tb, b) in zip(points, points[1:]):
        if t <= tb:
            u = (t-ta)/(tb-ta)
            return a+(b-a)*(u*u*(3-2*u))
    return points[-1][1]


def wave(t, start, end, amplitude=1):
    if not start <= t <= end:
        return 0.0
    u = (t-start)/(end-start)
    return amplitude*math.sin(2*math.pi*u)*math.sin(math.pi*u)**2


def pose(action, t):
    p = {"rx_deg": 0.0, "ry_deg": 0.0, "rz_deg": 0.0, "x_mm": 0.0, "y_mm": 0.0, "z_mm": 0.0}
    if action["id"] == "hold_that_compliment":
        p["ry_deg"] = wave(t, 2.2, 3.3, 1.4)+wave(t, 3.3, 4.9, 2.4)
        p["x_mm"] = wave(t, 3.3, 4.9, 1.2)
        p["rx_deg"] = curve(t, [(0,0),(5.0,0),(5.5,1.5),(7.3,1.5),(8.0,0),(9,0)])
        p["z_mm"] = curve(t, [(0,0),(3.3,0),(3.65,1),(4.05,0),(9,0)])
    elif action["id"] == "gossip_radar":
        p["rz_deg"] = curve(t, [(0,0),(1.4,0),(1.8,-3),(2.3,-3),(2.85,3),(3.3,3),(3.6,0),(8,0)])
        p["rx_deg"] = curve(t, [(0,0),(3.6,0),(4.0,-2.4),(6.7,-2.4),(7.4,0),(8,0)])
        p["y_mm"] = curve(t, [(0,0),(3.6,0),(4.0,1.5),(6.7,1.5),(7.4,0),(8,0)])
    else:
        p["rx_deg"] = curve(t, [(0,0),(2.0,0),(2.3,-2.3),(2.65,0),(3.1,0),(3.4,-1.6),(3.75,0),(8,0)])
        p["ry_deg"] = wave(t, 4.0, 5.7, 1.8)
        p["z_mm"] = curve(t, [(0,0),(1.2,0),(1.45,-.8),(1.7,0),(8,0)])
    return p


def shift(pattern, amount):
    return ["".join(row[x-amount] if 0 <= x-amount < 8 else "0" for x in range(8)) for row in pattern]


def close(pattern, amount):
    if amount <= .05:
        return pattern
    height = max(1, round(8*(1-amount)))
    result = ["00000000"]*8
    for y in range(height):
        result[(8-height)//2+y] = pattern[min(7,round(y*7/max(1,height-1)))]
    if height == 1:
        result[3] = "01111110"
    return result


def blink(t, start, end):
    return math.sin(math.pi*(t-start)/(end-start))**2 if start <= t <= end else 0


def eyes(action, t):
    aid = action["id"]
    left = right = PATTERNS["normal"]
    label = "普通眼睛"
    if aid == "hold_that_compliment":
        if t < 2.2:
            left = right = PATTERNS["calm"]
            label = "假装淡定"
        elif t < 3.3:
            left = right = PATTERNS["squint"]
            label = "努力绷住"
        elif t < 5.0:
            left = PATTERNS["smile"]
            right = PATTERNS["heart"] if 3.55 <= t < 4.25 else PATTERNS["smile"]
            label = "笑眼破功，冒出一颗心"
        elif t < 7.8:
            left = right = PATTERNS["smile"]
            label = "淡定地收下夸奖"
        right = close(right, blink(t, 7.85, 8.25))
    elif aid == "gossip_radar":
        if t < 1.4:
            left = right = PATTERNS["calm"]
            label = "我不感兴趣，真的"
        elif t < 2.4:
            left = right = shift(PATTERNS["pupil"], -2)
            label = "左边听听"
        elif t < 3.6:
            left = right = shift(PATTERNS["pupil"], 2)
            label = "右边也听听"
        elif t < 4.45:
            left = right = PATTERNS["wide"]
            label = "突然睁大，认真听"
        elif t < 6.7:
            left = PATTERNS["wide"]
            right = PATTERNS["spark"] if t < 5.15 else PATTERNS["wide"]
            label = "请展开说说"
        left = close(left, blink(t, 7.1, 7.5))
        right = close(right, blink(t, 7.1, 7.5))
    else:
        if 1.2 <= t < 2.0:
            left = right = PATTERNS["inbox"]
            label = "夸奖到达收件箱"
        elif 2.0 <= t < 3.8:
            left = right = PATTERNS["check"]
            label = "认真点头，盖章签收"
        elif 3.8 <= t < 6.6:
            left = PATTERNS["heart"]
            right = PATTERNS["smile"]
            label = "珍藏起来，循环回味"
        right = close(right, blink(t, 6.65, 7.05))
    return {"left": left, "right": right, "label": label}


def bitmap(pattern):
    from PIL import Image
    image = Image.new("RGB", (8,8), "black")
    for y,row in enumerate(pattern):
        for x,v in enumerate(row):
            if v == "1":
                image.putpixel((x,y),(255,255,255))
    return image


def verify_inputs():
    lock = json.loads((R02/"sources.lock.json").read_text())
    for record in lock["sources"]:
        if hashlib.sha256((REPO/record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Accepted model/code source has changed: {record['path']}")
    profiles = json.loads((R02/"geometry_profiles.json").read_text())
    return lock, profiles["edge50"]


def prepare():
    lock, geometry = verify_inputs()
    OUT.mkdir(parents=True,exist_ok=True)
    sequences = []
    frame_offset = 0
    for action in ACTIONS:
        folder = OUT/action["id"]
        (folder/"textures").mkdir(parents=True,exist_ok=True)
        (folder/"renders").mkdir(exist_ok=True)
        samples = []
        count = round(action["seconds"]*FPS)
        for i in range(count):
            t = i/FPS
            e = eyes(action,t)
            for side in ["left","right"]:
                bitmap(e[side]).save(folder/"textures"/f"{side}_{i+1:04d}.png")
            samples.append({"frame":i+1,"t":t,"body":pose(action,t),"eyes":e})
        doc = {**action,"status":"OFFLINE_PREVIEW_NOT_HARDWARE_READY","fps":FPS,"render_frames":count,
               "body_frame":"whole chassis + head, +X right, +Y front, +Z up; no neck joint",
               "eye_format":"two independent logical 8x8 single-color concept rasters; physical active areas and resolutions unknown",
               "geometry":geometry,"samples":samples}
        (folder/"timeline.json").write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n")
        sequences.append({"id":action["id"],"title":action["title"],"start_frame":frame_offset+1,"frames":count,"seconds":action["seconds"]})
        frame_offset += count
    manifest = {"revision":"R03","accepted_baseline":"red-black EDGE50 + simplified R06 head", "actions":sequences,
                "render_fps":FPS,"total_seconds":sum(a["seconds"] for a in ACTIONS),"frames":frame_offset,
                "geometry":geometry,"r02_source_lock_sha256":hashlib.sha256((R02/"sources.lock.json").read_bytes()).hexdigest(),
                "head_mesh":lock["head_mesh"],"head_mesh_sha256":hashlib.sha256((REPO/lock["head_mesh"]).read_bytes()).hexdigest(),
                "actions_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "firmware_motion_or_oled_driver_modified":False,"robot_connected":False}
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"actions":len(ACTIONS),"frames":frame_offset,"seconds":manifest["total_seconds"]},ensure_ascii=False))


if __name__ == "__main__":
    prepare()
