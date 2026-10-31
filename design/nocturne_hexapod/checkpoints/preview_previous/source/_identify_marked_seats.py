from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'review/cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from edge_frames import *
from model import plate,profile
fig=plt.figure(figsize=(12,10),facecolor='#e9eff6')
parts=[plate(profile('BodyTop')['loops_uv_mm'],3),edge_top(),reference_bottom(),edge_bottom()]
labels=['TOP / ORIGINAL','TOP / EDGE +50 mm','BOTTOM / ORIGINAL','BOTTOM / EDGE +50 mm']
for i,(p,label) in enumerate(zip(parts,labels)):
 ax=fig.add_subplot(2,2,i+1,projection='3d');ax.set_facecolor('#e9eff6')
 vv,tt=p.tessellate(.08,.15);v=np.array([[a.X,a.Y,a.Z] for a in vv]);faces=v[np.array(tt)]
 ax.add_collection3d(Poly3DCollection(faces,facecolors='#e7edf5' if i%2 else '#8293a8',linewidth=0,shade=True))
 ax.set_xlim(-2,137);ax.set_ylim(-28,108);ax.set_zlim(0,15);ax.set_box_aspect((139,136,15));ax.view_init(elev=65,azim=-75);ax.set_axis_off()
 if i==3:
  for side in [-1,1]:
   for j,(x,y) in enumerate([(10,17),(65,8),(120,17)]):
    yy=y if side==-1 else 78.343-y
    for tag,shift in [('I',0),('O',side*25)]:
     ax.text(x,yy+shift,11,tag+str(side)+str(j),color='red' if tag=='I' else 'blue',fontsize=9)
 b=p.bounding_box().size;ax.set_title(label+f'\n{b.X:.3f} x {b.Y:.3f} x {b.Z:.3f} mm',fontsize=12,color='#133e6c')
fig.suptitle('EDGE50 / FIXED CENTRAL OPENING',fontsize=22,fontweight='bold',y=.98,color='#123c68')
fig.text(.07,.045,'Left / right edges +25 mm; original central opening and fixed mounts retained.\nOuter leg mount geometry preserved. Lower original inner seats retained. Draft: assembly fit not verified.',fontsize=10,color='#133e6c')
fig.savefig('/tmp/edge50_ids.png',dpi=150,bbox_inches='tight')
