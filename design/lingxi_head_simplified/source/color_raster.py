"""Small orthographic depth-buffer renderer for truthful CAD inspection images.
Avoids painter-order artifacts from overlapping CAD cap triangles in mplot3d.
"""
import numpy as np

def raster_colored(vertices,triangles,colors,elev,azim,width=1000,height=660,alphas=None):
    e,a=np.radians([elev,azim])
    toward=np.array([np.cos(e)*np.cos(a),np.cos(e)*np.sin(a),np.sin(e)])
    right=np.array([-np.sin(a),np.cos(a),0.])
    up=np.cross(toward,right)
    v=np.array(vertices);center=(v.min(0)+v.max(0))/2;v=v-center
    q=np.column_stack((v@right,-v@up,v@toward))
    bounds=np.ptp(q[:,:2],axis=0);scale=min((width-110)/bounds[0],(height-80)/bounds[1])
    q[:,:2]*=scale;q[:,:2]+=np.array([width/2,height/2])
    image=np.empty((height,width,3),dtype=np.uint8);image[:]=[238,242,245]
    depth=np.full((height,width),-np.inf)
    light=toward*.8+up*.6-right*.25;light/=np.linalg.norm(light)
    order=np.arange(len(triangles)) if alphas is None else np.argsort(1-np.asarray(alphas),kind="stable")
    for color_index in order:
        tri=triangles[color_index]
        pts=q[list(tri)];world=v[list(tri)]
        n=np.cross(world[1]-world[0],world[2]-world[0]);norm=np.linalg.norm(n)
        if norm<1e-12:continue
        n/=norm
        if np.dot(n,toward)<-1e-5:continue
        lo=np.maximum(np.floor(pts[:,:2].min(0)).astype(int),[0,0]);hi=np.minimum(np.ceil(pts[:,:2].max(0)).astype(int),[width-1,height-1])
        if np.any(hi<lo):continue
        x0,y0=lo;x1,y1=hi
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
        A,B,C=pts
        den=(B[1]-C[1])*(A[0]-C[0])+(C[0]-B[0])*(A[1]-C[1])
        if abs(den)<1e-10:continue
        u=((B[1]-C[1])*(xx-C[0])+(C[0]-B[0])*(yy-C[1]))/den
        w=((C[1]-A[1])*(xx-C[0])+(A[0]-C[0])*(yy-C[1]))/den
        k=1-u-w;z=u*A[2]+w*B[2]+k*C[2]
        area=depth[y0:y1+1,x0:x1+1]
        hit=(u>=-1e-6)&(w>=-1e-6)&(k>=-1e-6)&(z>area)
        shade=.42+.48*max(0,np.dot(n,light))+.10*max(0,np.dot(n,toward))
        col=np.clip(np.array(colors[color_index])*shade,0,255).astype(np.uint8)
        alpha=1.0 if alphas is None else float(alphas[color_index])
        if alpha>=.999:area[hit]=z[hit]
        tile=image[y0:y1+1,x0:x1+1]
        tile[hit]=(tile[hit]*(1-alpha)+col*alpha).astype(np.uint8)
    return image
