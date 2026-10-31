"""Compose synchronized CAD, conceptual expressions, leg reference and speech."""
from pathlib import Path
from functools import lru_cache
import json
import subprocess
import hashlib
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
from actions import OUT,REPO,R02,FPS,ACTIONS,pose,eyes,bitmap,verify_inputs

W,H=1600,1000
BG="#F4F0E8";INK="#263139";MUTED="#747C80";LINE="#D9D3C9"
VOICE=json.loads((OUT/"voice_manifest.json").read_text())
verify_inputs()


@lru_cache(None)
def font(size,latin=False):
    return ImageFont.truetype("/System/Library/Fonts/Avenir Next.ttc" if latin else "/System/Library/Fonts/Hiragino Sans GB.ttc",size)


def text(d,xy,value,size=25,color=INK,latin=False):
    d.text(xy,value,font=font(size,latin),fill=color)


def paste(image,path,box):
    asset=Image.open(path).convert("RGBA")
    asset=ImageOps.contain(asset,(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
    x=box[0]+(box[2]-box[0]-asset.width)//2;y=box[1]+(box[3]-box[1]-asset.height)//2
    image.paste(asset,(x,y),asset)


def stage(action,t):
    return next((name for start,name in reversed(action["beats"]) if start<=t),action["beats"][0][1])


def frame_path(action,t):
    i=min(round(action["seconds"]*FPS),int(t*FPS)+1)
    return OUT/action["id"]/"renders"/f"head_{i:04d}.png"


def eye_inset(image,action,t,x,y,size=168):
    d=ImageDraw.Draw(image);e=eyes(action,t)
    # Front-view order matches the CAD: robot right (+X) is viewer left.
    for j,(side,label) in enumerate([("right","右眼"),("left","左眼")]):
        xx=x+j*(size+35)
        d.rounded_rectangle((xx-12,y-12,xx+size+12,y+size+12),radius=14,fill="#172126")
        image.paste(bitmap(e[side]).resize((size,size),Image.Resampling.NEAREST),(xx,y))
        text(ImageDraw.Draw(image),(xx+size//2-22,y+size+22),label,20,MUTED)


LEG_REFERENCE = REPO / "design/red_black_print_release_20261031/approved_color_reference.png"


def compose(action,index,t):
    image=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(image)
    text(d,(50,25),"灵犀戏精小剧场 / R03",22,MUTED)
    text(d,(50,66),f"0{index+1}  {action['title']}",47)
    text(d,(1030,30),"当前 R06 外形 · 动作概念预演",23,action["color"])
    text(d,(1300,77),f"{t:04.1f} / {action['seconds']:04.1f} s",23,MUTED,True)
    d.line((50,140,1550,140),fill=LINE,width=2)
    paste(image,frame_path(action,t),(30,150,945,875))
    d=ImageDraw.Draw(image)
    text(d,(65,173),action["hook"],25,action["color"])
    text(d,(65,835),"R06 CAD 同步朝向示意 / 无独立颈部",20,MUTED)
    text(d,(1000,177),"双 OLED 表情概念",28)
    text(d,(1000,222),"8×8 逻辑图案；实际屏幕规格待确认",18,MUTED)
    eye_inset(image,action,t,1055,282)
    d=ImageDraw.Draw(image)
    text(d,(1000,505),stage(action,t),30,action["color"])
    text(d,(1000,553),eyes(action,t)["label"],21,MUTED)
    paste(image,LEG_REFERENCE,(990,565,1540,775))
    d=ImageDraw.Draw(image)
    text(d,(1000,791),"红黑机甲腿件参照 · 动态装配未校准",20,MUTED)
    p=pose(action,t)
    values=f"俯仰 {p['rx_deg']:+.1f}°   侧倾 {p['ry_deg']:+.1f}°   偏航 {p['rz_deg']:+.1f}°"
    text(d,(1000,831),values,18,MUTED)
    line=next((r["text"] for r in VOICE if r["action"]==action["id"] and r["start_seconds"]<=t<r["start_seconds"]+r["duration_seconds"]+.15),None)
    dialogue="“"+line+"”" if line else "（"+stage(action,t)+"）"
    d.rounded_rectangle((50,884,1550,951),radius=13,fill="#E7E0D5")
    width=d.textlength(dialogue,font=font(29))
    text(d,((W-width)/2,899),dialogue,29)
    d.line((50,974,1550,974),fill=LINE,width=4)
    d.line((50,974,50+1500*t/action["seconds"],974),fill=action["color"],width=4)
    text(d,(50,982),"预览/待实机验证 · 表情为概念覆盖 · 非完整总装或硬件同步测试",12,MUTED)
    return image


def encode(action,index):
    folder=OUT/action["id"]
    lines=[r for r in VOICE if r["action"]==action["id"]]
    command=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{W}x{H}","-framerate",str(FPS),"-i","pipe:0"]
    for r in lines:command.extend(["-i",str(OUT/r["file"])])
    filters=[]
    for i,r in enumerate(lines):filters.append(f"[{i+1}:a]adelay={round(r['start_seconds']*1000)}:all=1[a{i}]")
    filters.append("".join(f"[a{i}]" for i in range(len(lines)))+f"amix=inputs={len(lines)}:normalize=0,apad,atrim=duration={action['seconds']}[audio]")
    command.extend(["-filter_complex",";".join(filters),"-map","0:v","-map","[audio]","-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p","-r","24","-c:a","aac","-b:a","128k","-t",str(action["seconds"]),"-movflags","+faststart",str(folder/"preview.mp4")])
    p=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for i in range(round(action["seconds"]*FPS)):
            p.stdin.write(compose(action,index,i/FPS).tobytes())
        p.stdin.close()
        if p.wait()!=0:raise RuntimeError(f"Encoding failed: {action['id']}")
    except BaseException:
        p.kill();raise
    compose(action,index,action["keyframes"][1][0]).save(folder/"cover.png")


def storyboard():
    image=Image.new("RGB",(2100,2090),BG)
    d=ImageDraw.Draw(image)
    text(d,(60,35),"灵犀的三种戏精反应",54)
    text(d,(60,113),"当前 R06 真实外形 × 双眼概念表情 × 原地身体姿态 / 25 秒预演",27,MUTED)
    for row,action in enumerate(ACTIONS):
        y=188+row*610
        d=ImageDraw.Draw(image)
        text(d,(60,y),f"0{row+1}  {action['title']}",34,action["color"])
        for col,(t,label) in enumerate(action["keyframes"]):
            x=45+col*687;yy=y+57
            d.rounded_rectangle((x,yy,x+661,yy+492),radius=16,fill="#E8E2D8")
            paste(image,frame_path(action,t),(x+5,yy,x+656,yy+420))
            eye_inset(image,action,t,x+430,yy+315,72)
            d=ImageDraw.Draw(image)
            text(d,(x+20,yy+440),label,27)
            text(d,(x+485,yy+443),f"{t:.1f} s",23,MUTED,True)
    text(ImageDraw.Draw(image),(60,2040),"预览 / 待实机验证。完整装配、双 OLED 实际显示区与驱动、载荷和碰撞尚未验证。",23,MUTED)
    image.save(OUT/"three_actions_storyboard.png")


def main():
    for index,action in enumerate(ACTIONS):encode(action,index)
    listing="".join(f"file '{a['id']}/preview.mp4'\n" for a in ACTIONS)
    (OUT/"reel_inputs.txt").write_text(listing)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(OUT/"reel_inputs.txt"),"-c","copy","-movflags","+faststart",str(OUT/"unique_actions_reel.mp4")],check=True)
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(OUT/"unique_actions_reel.mp4"),"-filter_complex","fps=8,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4","-loop","0",str(OUT/"unique_actions_reel.gif")],check=True)
    storyboard()
    record={"status":"COMPOSED_PREVIEW","composer_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"source_r02_lock_sha256":hashlib.sha256((R02/"sources.lock.json").read_bytes()).hexdigest(),"actions":[a["id"] for a in ACTIONS],"video":"unique_actions_reel.mp4","storyboard":"three_actions_storyboard.png"}
    (OUT/"composition_manifest.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(record,ensure_ascii=False))


if __name__=="__main__":main()
