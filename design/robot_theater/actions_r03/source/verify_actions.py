"""Check current source binding, media decoding, and finite preview lengths."""
from pathlib import Path
import hashlib
import json
import subprocess
from PIL import Image
from actions import OUT,R02,REPO,ACTIONS,FPS,verify_inputs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path):
    return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames,duration","-show_entries","format=duration,size","-of","json",str(path)],text=True))


def main():
    verify_inputs()
    manifest=json.loads((OUT/"manifest.json").read_text())
    rendered=json.loads((OUT/"render_checks.json").read_text())
    composition=json.loads((OUT/"composition_manifest.json").read_text())
    assert manifest["actions_source_sha256"]==sha(OUT/"source/actions.py")
    assert manifest["r02_source_lock_sha256"]==sha(R02/"sources.lock.json")
    assert manifest["head_mesh_sha256"]==sha(REPO/manifest["head_mesh"])
    assert rendered["source_scene_sha256"]==sha(R02/"current_sources_preview.blend")
    assert rendered["renderer_sha256"]==sha(OUT/"source/render_actions.py")
    assert composition["composer_sha256"]==sha(OUT/"source/compose_actions.py")
    motion=json.loads((OUT/"motion_checks.json").read_text())
    assert motion["status"]=="PASS_IDEAL_KINEMATICS_ONLY"
    files=[]
    for action in ACTIONS:
        folder=OUT/action["id"]
        expected=round(action["seconds"]*FPS)
        assert len(list((folder/"renders").glob("head_*.png")))==expected
        data=probe(folder/"preview.mp4")
        video=next(s for s in data["streams"] if s["codec_name"]=="h264")
        assert video["width"]==1600 and video["height"]==1000
        assert int(video["nb_frames"])==round(action["seconds"]*24)
        assert abs(float(data["format"]["duration"])-action["seconds"])<.1
        timeline=json.loads((folder/"timeline.json").read_text())
        for sample in timeline["samples"]:
            for side in ["left","right"]:
                pattern=sample["eyes"][side]
                assert len(pattern)==8 and all(len(row)==8 and set(row)<=set("01") for row in pattern)
        files.append({"file":str((folder/"preview.mp4").relative_to(OUT)),"sha256":sha(folder/"preview.mp4"),"probe":data})
    reel=probe(OUT/"unique_actions_reel.mp4")
    assert abs(float(reel["format"]["duration"])-25)<.2
    subprocess.run(["ffmpeg","-v","error","-i",str(OUT/"unique_actions_reel.mp4"),"-f","null","-"],check=True)
    for name in ["three_actions_storyboard.png","unique_actions_reel.gif"]:
        with Image.open(OUT/name) as im:
            size=im.size
            if name.endswith(".gif"):
                frames=im.n_frames
                duration=sum((im.seek(i) or im.info.get("duration",0)) for i in range(frames))
                assert abs(duration-25000)<300
            else:
                frames=1;duration=None;im.verify()
        files.append({"file":name,"sha256":sha(OUT/name),"size":size,"frames":frames,"duration_ms":duration})
    result={"status":"PASS_OFFLINE_PREVIEW_CHECKS","files":files,"reel":reel,
            "reel_sha256":sha(OUT/"unique_actions_reel.mp4"),"full_reel_decoded":True,
            "cad_source_and_action_source_bound":True,"three_finite_actions":True,
            "hardware_motion_verified":False,"physical_oled_mapping_verified":False,
            "full_body_assembly_verified":False}
    (OUT/"delivery_checks.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"actions":len(ACTIONS),"reel_seconds":reel["format"]["duration"],"full_reel_decoded":True}))


if __name__=="__main__":main()
