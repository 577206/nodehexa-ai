"""User-requested STL prototype exports, deliberately separate from production."""
from pathlib import Path
import json,shutil
import trimesh
from build123d import export_stl
from model import *


def main():
    folder=ROOT/'outputs/parts_DRAFT_NOT_FULL_KIT'
    folder.mkdir(parents=True,exist_ok=True)
    records=[]
    for part in local_parts(load_parameters(ROOT/'parameters.yaml')):
        d=folder/part.label;d.mkdir(exist_ok=True)
        step=ROOT/'outputs/step'/(part.label+'.step')
        if not step.exists():raise RuntimeError('Run official STEP export first')
        shutil.copy2(step,d/step.name)
        stl=d/(part.label+'.stl')
        export_stl(part,str(stl),tolerance=.025,angular_tolerance=.1)
        mesh=trimesh.load(stl,force='mesh')
        record={'id':part.label,'units':'mm','bbox_mm':mesh.extents.tolist(),
                'CAD_solids':len(part.solids()),'CAD_valid':bool(part.is_valid),
                'STL_watertight':bool(mesh.is_watertight),'STL_winding_consistent':bool(mesh.is_winding_consistent),
                'mesh_volume_mm3':float(mesh.volume),'CAD_volume_mm3':part.volume,
                'status':'prototype_for_review_not_production','physical_fit_verified':False,
                'files':[step.name,stl.name]}
        (d/'dimensions.json').write_text(json.dumps(record,indent=2))
        if not (record['STL_watertight'] and record['STL_winding_consistent']):
            raise RuntimeError('Mesh defect: '+part.label)
        records.append(record)
    (folder/'manifest.json').write_text(json.dumps({'status':'PARTIAL_DRAFT_NOT_FULL_KIT','parts':records},indent=2))
    (folder/'READ_FIRST.txt').write_text('NOCTURNE 第一批工程草模，非完整打印套件。\n单位 mm。每个文件夹包含独立 STEP、STL 和尺寸记录。\n本批仅包含加宽上框架、小腿正面甲片和两枚红色饰条。\n上框架不能与原宽度底架直接配套组装；其余机身件尚未完成改版。\n小腿甲片为局部外观样件，整腿运动间隙、实际配合和饰条固定方式尚未验证。\n原有螺丝座厚度在已检查接口区保持；新增装饰高度 1.2 mm。\n红色细条厚度约 0.55 mm，其打印和固定需要小样验证。\n不要将本目录当作整机生产放行文件。\n',encoding='utf-8')
    print(json.dumps({'exported_parts':len(records),'all_STL_closed':True,'folder':str(folder)},ensure_ascii=False))


if __name__=='__main__':main()
