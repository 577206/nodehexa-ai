from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[1]/'review/cache/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from lower_frame import *
fig=plt.figure(figsize=(13,10),facecolor='#f1f3f5')
for row,name in enumerate(['BodyButtom','BodyButtom-18650-2S']):
 for col in range(2):
  p=reference_bottom(name) if col==0 else widened_bottom(name)
  ax=fig.add_subplot(2,2,row*2+col+1,projection='3d')
  vv,tt=p.tessellate(.08,.15);v=np.array([[a.X,a.Y,a.Z] for a in vv]);faces=v[np.array(tt)]
  ax.add_collection3d(Poly3DCollection(faces,facecolors='#697582' if col==0 else '#a73346',linewidth=0,shade=True))
  ax.set_xlim(0,135);ax.set_ylim(-17,96);ax.set_zlim(0,15);ax.set_box_aspect((135,113,15));ax.view_init(elev=57,azim=-65);ax.set_axis_off()
  b=p.bounding_box().size
  ax.set_title(f'{name} | '+('ORIGINAL' if col==0 else '+30 mm CENTER EXTENSION')+f'\n{b.X:.3f} x {b.Y:.3f} x {b.Z:.3f} mm',fontsize=12,pad=12)
fig.suptitle('NOCTURNE / LOWER FRAME WIDTH UPDATE',fontsize=22,fontweight='bold',y=.98)
fig.text(.05,.055,'Both alternatives: left / right interface groups translated 15 mm; local seats and maximum thickness retained.\nReference-derived faceted CAD. Select ONE lower frame. Assembly fit and strength are not yet verified.',fontsize=11)
fig.savefig(ROOT/'outputs/drawings/lower_frame_width_update.png',dpi=150,bbox_inches='tight')
