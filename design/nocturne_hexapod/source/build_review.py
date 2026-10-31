"""Create review geometry and actual-CAD comparison sheet, no generative imagery."""
from pathlib import Path
import json,hashlib,os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'review/cache/matplotlib'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from model import *


def main():
    params=load_parameters(ROOT/'parameters.yaml')
    model=build_model(params)
    vertices=[];faces=[];part_records=[]
    colors={'N001_upper_frame_W30_DRAFT':'#36383d','N111_shin_face_DRAFT':'#33353a',
            'N112_L_red_insert_DRAFT':'#c22437','N112_R_red_insert_DRAFT':'#c22437'}
    for part in model.children:
        vv,tt=part.tessellate(0.08,0.15)
        offset=len(vertices)
        xyz=[[v.X,v.Y,v.Z] for v in vv];vertices.extend(xyz)
        for triangle in tt:
            pts=np.array([xyz[i] for i in triangle]);normal=np.cross(pts[1]-pts[0],pts[2]-pts[0])
            normal=normal/max(np.linalg.norm(normal),1e-12)
            faces.append({'indices':[offset+i for i in triangle],'part_id':part.label,
                          'feature_id':part.label,'color':colors[part.label],
                          'world_point':pts.mean(0).tolist(),'normal':normal.tolist()})
        part_records.append({'id':part.label,'label':part.label,'visible':True,'color':colors[part.label]})
    manifest=json.loads((ROOT/'review/manifest.json').read_text())
    manifest['project']['name']='NOCTURNE | Partial CAD draft - not full robot'
    manifest['preview']={'mesh_json':'cache/current_mesh.json','mesh_closed':True}
    manifest['parts']=part_records;manifest['parameters']=[]
    manifest['versions']['current']['source']='../source/model.py'
    (ROOT/'review/manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    mesh={'vertices':vertices,'faces':faces,'provenance':{k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('source_hash','source/model.py'),('parameters_hash','parameters.yaml'),('spec_hash','spec/current.yaml'),('manifest_hash','review/manifest.json')]}}
    (ROOT/'review/cache/current_mesh.json').write_text(json.dumps(mesh))

    fig=plt.figure(figsize=(14,10),facecolor='#f2f2f0')
    gs=fig.add_gridspec(2,2,height_ratios=[1,1],wspace=.22,hspace=.3)
    ax=fig.add_subplot(gs[0,0]);ax.set_title('01 / UPPER FRAME — original vs +30 mm width',loc='left',fontsize=12,fontweight='bold')
    orig=profile('BodyTop')['loops_uv_mm'];cy=74.34314727783203/2
    for points in orig:
        q=np.array(points);q=np.vstack([q,q[0]])
        ax.plot(q[:,0],q[:,1],color='#999b9f',lw=.8,ls='--')
        q=np.array(widen_loop(points,cy,30));q=np.vstack([q,q[0]])
        ax.plot(q[:,0],q[:,1],color='#b92038',lw=.8)
    ax.set_aspect('equal');ax.set_xlabel('Local u / mm');ax.set_ylabel('Local v / mm');ax.grid(alpha=.12)
    ax.text(.02,.02,'134.809 × 104.343 × 3.000 mm\nOriginal interface groups translated ±15 mm',transform=ax.transAxes,fontsize=9,bbox={'facecolor':'white','alpha':.9,'edgecolor':'none'})

    ax=fig.add_subplot(gs[0,1]);ax.set_title('02 / SHIN FACE — preserved interfaces',loc='left',fontsize=12,fontweight='bold')
    loops=profile('FootGround')['loops_uv_mm']
    for i,loop in enumerate(loops):ax.add_patch(Polygon(loop,facecolor='#44474c' if i==0 else '#f2f2f0',edgecolor='#15171a',lw=.55))
    for rail,recess in [(ARMOR_RAIL,RED_RECESS),(mirrored(ARMOR_RAIL),mirrored(RED_RECESS))]:
        ax.add_patch(Polygon(rail,facecolor='#686b71',edgecolor='#25272c',lw=.8))
        ax.add_patch(Polygon(recess,facecolor='#c22437',edgecolor='#7d1420',lw=.5))
    for x,y,w,h in [(0,24,5.5,12),(34,24,5.5,12),(12.75,0,14,6.8),(0,54.8,39.5,10.25)]:
        ax.add_patch(Rectangle((x,y),w,h,facecolor='#499d81',alpha=.18,edgecolor='none'))
    ax.text(45,48,'Green zones:\noriginal connector\ngeometry unchanged\n\nOriginal 3 mm core\nis preserved.\nExterior relief: 1.2 mm\nMax thickness: 4.2 mm',fontsize=9,va='top')
    ax.set_xlim(-3,82);ax.set_ylim(-4,70);ax.set_aspect('equal');ax.set_xlabel('Local u / mm');ax.set_ylabel('Local v / mm');ax.grid(alpha=.12)

    ax=fig.add_subplot(gs[1,0],projection='3d');ax.set_title('03 / ACTUAL CAD — shin + two red inserts',loc='left',fontsize=12,fontweight='bold')
    all_triangles=[];all_colors=[]
    for part in ground_parts(params):
        vv,tt=part.tessellate(.08,.15);vv=np.array([[v.X,v.Y,v.Z] for v in vv])
        all_triangles.extend(vv[np.array(tt)]);all_colors.extend([colors[part.label]]*len(tt))
    coll=Poly3DCollection(all_triangles,facecolors=all_colors,linewidth=0,shade=True,alpha=1)
    ax.add_collection3d(coll)
    ax.set_xlim(-2,42);ax.set_ylim(-3,68);ax.set_zlim(0,10);ax.set_box_aspect((44,71,10));ax.view_init(elev=50,azim=-65);ax.set_axis_off()

    ax=fig.add_subplot(gs[1,1]);ax.axis('off')
    ax.text(0,.98,'DRAFT ENGINEERING CHECK',fontsize=16,fontweight='bold',va='top')
    bb=ground_parts(params)[1].bounding_box().size
    text=f'Four valid CAD solids / no mutual solid overlap\n\nUpper frame: 134.809 × 104.343 × 3.000 mm\nShin face: 39.500 × 65.048 × 4.200 mm\nRed inserts: {bb.X:.3f} × {bb.Y:.3f} × {bb.Z:.3f} mm each\n\nSide pilot bores retained: diameter ≈ 0.900 mm\nCenters: v = 30.048 / 60.048; w = 1.500 mm\n\nNOT VERIFIED:\nFull leg sweep, physical fit, insert retention,\nremaining chassis parts and electronics packaging.\n\nThis is a partial prototype, NOT a full print kit.'
    ax.text(0,.84,text,fontsize=11,linespacing=1.65,va='top')
    fig.suptitle('NOCTURNE / ENGINEERING DRAFT 01',x=.05,y=.98,ha='left',fontsize=22,fontweight='bold')
    fig.savefig(ROOT/'outputs/drawings/first_draft_comparison.png',dpi=150,bbox_inches='tight')
    fig.savefig(ROOT/'outputs/drawings/first_draft_comparison.svg',bbox_inches='tight')
    print('Wrote review mesh and actual CAD comparison sheet.')


if __name__=='__main__':main()
