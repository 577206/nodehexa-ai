from pathlib import Path
import sys,bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"))
import cad_review_shots as review_shots
review_shots.DIRS.update(three_quarter=(-1,1,.6))
names=[o.name for o in bpy.context.scene.objects if o.type=="MESH" and o.name.startswith("SM_H")]
print(review_shots.run(objects=names,out=str(ROOT/"outputs/renders/R05/R05_QA_wire.png"),views=["three_quarter","bottom"],mode="wire",res=850))
