"""Source-linked build figures. No invented whole-robot assembly."""
from pathlib import Path
from functools import lru_cache
import json
import hashlib
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps

OUT = Path(__file__).resolve().parents[1]
BG = "#F4F0E8"
INK = "#263139"
GRAY = "#727B80"
RED = "#AD3042"
ORANGE = "#C3652D"
LINE = "#D3CFC6"


@lru_cache(None)
def font(size, latin=False):
    path = "/System/Library/Fonts/Avenir Next.ttc" if latin else "/System/Library/Fonts/Hiragino Sans GB.ttc"
    return ImageFont.truetype(path, size)


def text(d, xy, value, size=26, color=INK, latin=False):
    d.text(xy, value, font=font(size, latin), fill=color)


def paste(img, path, box):
    asset = Image.open(path).convert("RGBA")
    asset = ImageOps.contain(asset, (box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
    x = box[0] + (box[2] - box[0] - asset.width) // 2
    y = box[1] + (box[3] - box[1] - asset.height) // 2
    img.paste(asset, (x, y), asset)


def header(img, title, subtitle):
    d = ImageDraw.Draw(img)
    text(d, (60, 35), title, 49)
    text(d, (60, 108), subtitle, 25, GRAY)
    d.line((60, 160, img.width - 60, 160), fill=LINE, width=2)


def head_views(lock):
    image = Image.new("RGB", (2100, 1260), BG)
    header(image, "当前 R06 简化驾驶舱 / 源码与图对应", "钟笑咪确认基准：红黑 EDGE50 底盘 ＋ lingxi_head_simplified R06；本页显示真实头部网格")
    for name, label, box in [
        ("head_hero", "01  三分之四视角", (25, 190, 880, 1045)),
        ("head_front", "02  正面", (875, 245, 1465, 835)),
        ("head_left", "03  左侧", (1460, 245, 2050, 835))]:
        paste(image, OUT / "renders" / (name + ".png"), box)
        text(ImageDraw.Draw(image), (box[0] + 30, box[3] + 5), label, 28)
    d = ImageDraw.Draw(image)
    text(d, (930, 920), "H01–H04  首批壳体、底座、透明盖与压框", 25)
    text(d, (930, 966), "D01–D16  通风口、肩甲、圆盖、镜框、手机架", 25)
    text(d, (930, 1012), "20 个打印件 ＋ 2 个 OLED 板卡位置参照", 25, ORANGE)
    text(d, (60, 1140), "model.py + 4 个 R06 模块 → 已核对哈希的 current_mesh.json → 本页三视图", 27)
    text(d, (60, 1190), "双 OLED 的有效显示区、像素分辨率与安装厚度尚未实测；本图不虚构发光像素或整机装配。", 23, GRAY)
    image.save(OUT / "current_head_views.png")


def parts_atlas(manifest):
    items = manifest["body_parts"]
    cols = 5
    rows = math.ceil(len(items) / cols)
    image = Image.new("RGB", (2100, 210 + rows * 455 + 130), BG)
    header(image, "红黑 EDGE50 / 当前打印文件对应图", "每格直接读取发布清单中的 STL；文件名、数量、颜色与 source SHA-256 均可追溯")
    for i, item in enumerate(items):
        x, y = 35 + (i % cols) * 412, 195 + (i // cols) * 455
        d = ImageDraw.Draw(image)
        d.rounded_rectangle((x, y, x + 398, y + 438), radius=16, fill="#E8E3DB")
        paste(image, OUT / item["image"], (x + 15, y + 5, x + 383, y + 300))
        d = ImageDraw.Draw(image)
        name = item["name"]
        # Exact filename wraps, preserving its identity.
        size = 16 if len(name) > 36 else 18
        chunks, line = [], ""
        for ch in name:
            if d.textlength(line + ch, font=font(size, True)) > 366:
                chunks.append(line)
                line = ch
            else:
                line += ch
        if line:
            chunks.append(line)
        if len(chunks) > 3:
            raise ValueError(f"Filename does not fit atlas tile: {name}")
        for j, chunk in enumerate(chunks):
            text(d, (x + 16, y + 300 + j * 21), chunk, size, INK, True)
        tag = "备选 / 不累计" if item["optional"] else f"{item['color']} / × {item['quantity']}"
        text(d, (x + 16, y + 363), tag, 22, RED if item["color"] == "RED" else ORANGE if item["optional"] else INK)
        dims = " × ".join(f"{v:.1f}" for v in item["dimensions_mm"])
        text(d, (x + 16, y + 400), dims + " mm", 20, GRAY, True)
    d = ImageDraw.Draw(image)
    y = image.height - 105
    text(d, (60, y), "N001 为 EDGE50 上板；N002 / N003 下板二选一。每格自动取景，比例不同；不是完整腿部或整机装配图。", 24)
    text(d, (60, y + 46), "来源：red_black_print_release_20261031/manifest.json；黑色 R02 + 红色 R01。仅展示现有真实零件。", 23, GRAY)
    image.save(OUT / "current_parts_atlas.png")


def geometry_map(profiles, manifest):
    image = Image.new("RGB", (2100, 1440), BG)
    header(image, "EDGE50 / 图、几何配置与代码对应", "数据由 C++ 编译并执行 firmware/include/config.h 取得；原机与 EDGE50 两种配置分别核对")
    d = ImageDraw.Draw(image)
    cx, cy, scale = 580, 710, 5.4
    # This is an envelope/coordinate diagram, never an inferred CAD assembly.
    top = next(p for p in manifest["body_parts"] if p["name"] == "N001_BodyTop_EDGE50.stl")
    bl, bw = top["dimensions_mm"][:2]
    d.rounded_rectangle((cx-bw/2*scale, cy-bl/2*scale, cx+bw/2*scale, cy+bl/2*scale), radius=25, outline=LINE, width=4)
    text(d, (245, 1110), "外框仅示上板包围尺寸", 22, GRAY)
    d.line((cx, 215, cx, 1140), fill=LINE, width=2)
    d.line((150, cy, 1040, cy), fill=LINE, width=2)
    text(d, (cx + 15, 210), "+Y 前方", 25)
    text(d, (950, cy+15), "+X", 25)
    positions = [(1,1),(1,0),(1,-1),(-1,-1),(-1,0),(-1,1)]
    old, new = profiles["original"], profiles["edge50"]
    for i, (sx, sy) in enumerate(positions):
        ox = sx * (old["mount_side_x_mm"] if sy == 0 else old["mount_corner_x_mm"])
        nx = sx * (new["mount_side_x_mm"] if sy == 0 else new["mount_corner_x_mm"])
        y = sy * new["mount_corner_y_mm"]
        a, b = (cx + ox*scale, cy-y*scale), (cx+nx*scale, cy-y*scale)
        d.line((*a,*b), fill=RED, width=4)
        sign = 1 if sx > 0 else -1
        d.polygon([(b[0],b[1]),(b[0]-sign*13,b[1]-7),(b[0]-sign*13,b[1]+7)], fill=RED)
        d.ellipse((a[0]-9,a[1]-9,a[0]+9,a[1]+9), fill="#8F999F")
        d.ellipse((b[0]-12,b[1]-12,b[0]+12,b[1]+12), fill=RED)
        text(d, (b[0]+(18 if sx>0 else -73),b[1]-18), f"L{i+1}", 24, RED, True)
        text(d, (min(a[0],b[0])+15,b[1]-39), f"{abs(nx-ox):g} mm", 19, RED, True)
    text(d, (240, 1180), "灰：原机腿根   红：EDGE50 几何目标", 25)
    x, y = 1170, 235
    text(d, (x,y), "同一份 config.h", 38)
    text(d, (x,y+68), "NODEHEXA_CHASSIS_EDGE50", 28, RED, True)
    def values(key):
        return f"{old[key]:g} -> {new[key]:g} mm"
    rows = [("侧向外移 / 每侧", values("side_translation_mm")),
            ("中腿 |X|", values("mount_side_x_mm")),
            ("前后角腿 |X|", values("mount_corner_x_mm")),
            ("前后角腿 |Y|", values("mount_corner_y_mm")),
            ("四段腿长", " / ".join(f"{v:g}" for v in new["link_lengths_mm"]) + " mm")]
    for i,(a,b) in enumerate(rows):
        yy = y+145+i*105
        text(d,(x,yy),a,24,GRAY)
        text(d,(x,yy+38),b,29,INK,True)
    text(d,(x,970),"构建环境",26,GRAY)
    text(d,(x,1015),"nodehexa-edge50-bench",29,RED,True)
    text(d,(x,1073),"禁动台架 / 舵机 PWM 关闭",27)
    text(d,(x,1123),"默认原机环境保留原机几何",23,GRAY)
    d.line((60,1280,2040,1280),fill=LINE,width=2)
    text(d,(60,1310),"已对应：CAD 的每侧 +25 mm → 编译常量 → 本图坐标。待核实：真实孔位、舵机轴、完整装配、载荷与碰撞。",25)
    text(d,(60,1360),"此图只说明几何配置；“我好看吗”的身体、双 OLED 与语音编排尚未接入实机固件。",24,GRAY)
    image.save(OUT / "code_geometry_map.png")


def main():
    lock = json.loads((OUT / "sources.lock.json").read_text())
    manifest = json.loads((OUT / "render_manifest.json").read_text())
    profiles = json.loads((OUT / "geometry_profiles.json").read_text())
    head_views(lock)
    parts_atlas(manifest)
    geometry_map(profiles, manifest)
    images = []
    for name in ["current_head_views.png", "current_parts_atlas.png", "code_geometry_map.png"]:
        p = OUT / name
        with Image.open(p) as im:
            size = im.size
            im.verify()
        images.append({"file": name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size": size})
    (OUT / "figures_manifest.json").write_text(json.dumps({"revision":"R02", "images":images,
        "sources_lock_sha256":hashlib.sha256((OUT/"sources.lock.json").read_bytes()).hexdigest(),
        "render_manifest_sha256":hashlib.sha256((OUT/"render_manifest.json").read_bytes()).hexdigest(),
        "composer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(images,ensure_ascii=False))


if __name__ == "__main__":
    main()
