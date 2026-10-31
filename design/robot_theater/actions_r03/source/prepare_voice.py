"""Temporary local TTS for timing review, no network voice service or robot I/O."""
import json
import subprocess
from actions import OUT,ACTIONS

records=[]
for action in ACTIONS:
    folder=OUT/action["id"]
    for i,(start,line) in enumerate(action["lines"]):
        path=folder/f"voice_{i+1}.aiff"
        subprocess.run(["say","-v","Tingting","-r","185","-o",str(path),line],check=True)
        duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)],text=True))
        assert start+duration<=action["seconds"]-.4,(action["id"],line,duration)
        records.append({"action":action["id"],"file":str(path.relative_to(OUT)),"start_seconds":start,"duration_seconds":duration,"text":line,"voice":"macOS Tingting temporary"})
(OUT/"voice_manifest.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"temporary_lines":len(records),"latest_end_in_each_action":{a["id"]:max(r["start_seconds"]+r["duration_seconds"] for r in records if r["action"]==a["id"]) for a in ACTIONS}},ensure_ascii=False))
