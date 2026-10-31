"""Compose the offline render, exact 1-bit OLED inset and temporary speech."""
from pathlib import Path
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps
from timeline import OUT, FPS, DURATION, BEATS, beat, pose, oled_image, eye_state

W, H = 1600, 1080
BG = "#F4F0E8"
INK = "#252F34"
MUTED = "#747B7C"
ACCENT = "#D85B2C"
FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
EN = "/System/Library/Fonts/Avenir Next.ttc"


def font(size, latin=False):
    return ImageFont.truetype(EN if latin else FONT, size)


def text(draw, xy, value, size, fill=INK, latin=False):
    draw.text(xy, value, font=font(size, latin), fill=fill)


def eye_panel(t, w=400, h=200):
    eye = oled_image(t).convert("RGB").resize((w, h), Image.Resampling.NEAREST)
    # The display remains single-color white. No RGB/LED assumption.
    return eye


def shot(t):
    frame = min(round(FPS * DURATION), int(t * FPS) + 1)
    return Image.open(OUT / "renders" / f"pose_{frame:04d}.png").convert("RGB")


def compose(t):
    image = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(image)
    text(d, (55, 30), "灵犀 / 机器人戏精小剧场", 22, MUTED)
    text(d, (55, 73), "01  我好看吗？", 52)
    text(d, (1125, 44), "动作预演 · 待实机验证", 24, ACCENT)
    text(d, (1305, 86), f"{t:04.1f} / 12.0 s", 25, MUTED, True)
    d.line((55, 146, 1545, 146), fill="#D8D4CB", width=2)
    image.paste(shot(t).resize((950, 758), Image.Resampling.LANCZOS), (40, 164))
    d = ImageDraw.Draw(image)
    text(d, (1060, 188), "同一时刻的眼睛", 28)
    text(d, (1060, 232), "128 × 64 / 单色 OLED", 20, MUTED)
    d.rounded_rectangle((1044, 281, 1520, 531), radius=22, fill="#172025")
    image.paste(eye_panel(t), (1082, 306))
    d = ImageDraw.Draw(image)
    state = eye_state(t)[0]
    label = {"normal": "看着你", "heart": "爱心心跳", "smug": "已经开始得意了"}[state]
    text(d, (1060, 554), label, 24, ACCENT)
    b = beat(t)
    text(d, (1060, 620), f"{b[2]} / {b[3]}", 28)
    text(d, (1060, 669), b[5], 19, MUTED)
    p = pose(t)
    text(d, (1060, 738), f"机身侧倾  {p['ry_deg']:+.1f}°", 23)
    text(d, (1060, 777), "六足定点支撑 · 无独立脖子", 20, MUTED)
    # Dialogue stays legible and shares the video's master clock.
    if .2 <= t < 1.5:
        line = "“我好看吗？”"
    elif 8.1 <= t < 10.8:
        line = "“好了，不用夸，我自己知道。”"
    elif 7.1 <= t < 8.1:
        line = "（留一拍，等你夸它）"
    elif 10.8 <= t:
        line = "（站好，眨一下眼）"
    else:
        line = "（它正在认真展示自己）"
    d.rounded_rectangle((55, 914, 1545, 990), radius=14, fill="#E8E2D8")
    box = d.textbbox((0, 0), line, font=font(31))
    text(d, ((W - box[2]) / 2, 933), line, 31, INK)
    # One continuous time ruler for body, expression, subtitles and audio.
    x0, x1, y = 55, 1545, 1023
    d.line((x0, y, x1, y), fill="#D4CEC4", width=5)
    for b in BEATS:
        x = x0 + (x1 - x0) * b[0] / DURATION
        d.line((x, y - 5, x, y + 5), fill=BG, width=4)
    x = x0 + (x1 - x0) * t / DURATION
    d.line((x0, y, x, y), fill=ACCENT, width=5)
    d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=ACCENT)
    text(d, (55, 1041), "表演节奏与运动学示意；配音为本机临时语音", 16, MUTED)
    text(d, (1240, 1041), "LINGXI THEATER / 001", 17, MUTED, True)
    return image


def storyboard():
    times = [.7, 2.25, 3.65, 4.77, 6.82, 8.9]
    labels = ["问完，等你看", "左歪，停一下", "右歪，再停一下", "心跳两次", "得意摆，偷偷眨", "自己夸自己"]
    poster = Image.new("RGB", (1920, 1510), BG)
    d = ImageDraw.Draw(poster)
    text(d, (65, 35), "机器人戏精小剧场", 55)
    text(d, (65, 113), "01 我好看吗？   /   12 秒身体 × 像素 × 台词同步预演", 29, MUTED)
    text(d, (1500, 52), "预览 / 待实机验证", 25, ACCENT)
    for i, (t, label) in enumerate(zip(times, labels)):
        x, y = 55 + (i % 3) * 625, 195 + (i // 3) * 610
        d.rounded_rectangle((x, y, x + 605, y + 580), radius=18, fill="#E7E2D8")
        img = shot(t).resize((595, 475), Image.Resampling.LANCZOS)
        poster.paste(img, (x + 5, y + 5))
        # Enlarged expression is an inset, not a second physical screen.
        poster.paste(eye_panel(t, 160, 80), (x + 425, y + 365))
        d = ImageDraw.Draw(poster)
        text(d, (x + 22, y + 486), f"0{i+1}  {label}", 29)
        text(d, (x + 22, y + 535), f"{t:.2f} s", 21, ACCENT, True)
        if i == 5:
            text(d, (x + 135, y + 535), "好了，不用夸，我自己知道。", 21)
    text(d, (65, 1445), "六足求解采用当前固件腿长；外形为简化示意。图片可评审姿态，视频用于评审停顿和接梗。", 23, MUTED)
    poster.save(OUT / "storyboard.png")


def run():
    ffmpeg = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
              "-pixel_format", "rgb24", "-video_size", f"{W}x{H}", "-framerate", str(FPS),
              "-i", "pipe:0", "-i", str(OUT / "line_1.aiff"), "-i", str(OUT / "line_2.aiff"),
              "-filter_complex", "[1:a]adelay=200:all=1[a];[2:a]adelay=8100:all=1[b];[a][b]amix=inputs=2:normalize=0,apad,atrim=duration=12[audio]",
              "-map", "0:v", "-map", "[audio]", "-c:v", "libx264", "-preset", "medium",
              "-crf", "19", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "128k",
              "-t", str(DURATION), "-movflags", "+faststart", str(OUT / "am_i_cute_preview.mp4")]
    p = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    try:
        for i in range(round(FPS * DURATION)):
            p.stdin.write(compose(i / FPS).tobytes())
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("ffmpeg encoding failed")
    except BaseException:
        p.kill()
        raise
    storyboard()
    compose(4.77).save(OUT / "preview_cover.png")
    # A small silent looping preview for convenient inspection in Markdown.
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(OUT / "am_i_cute_preview.mp4"),
                    "-filter_complex", "fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                    "-loop", "0", str(OUT / "am_i_cute_preview.gif")], check=True)
    print(json.dumps({"video": str(OUT / "am_i_cute_preview.mp4"), "storyboard": str(OUT / "storyboard.png")}, ensure_ascii=False))


if __name__ == "__main__":
    run()
