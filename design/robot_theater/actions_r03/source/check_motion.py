"""Ideal kinematic checks for fixed six-foot targets, not stability validation."""
import json
import math
from pathlib import Path
import numpy as np
from actions import OUT, ACTIONS, pose, verify_inputs


def rotation(p):
    x,y,z = [math.radians(p[k]) for k in ["rx_deg","ry_deg","rz_deg"]]
    rx=np.array([[1,0,0],[0,math.cos(x),-math.sin(x)],[0,math.sin(x),math.cos(x)]])
    ry=np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
    rz=np.array([[math.cos(z),-math.sin(z),0],[math.sin(z),math.cos(z),0],[0,0,1]])
    return rz@ry@rx


def rig(geometry):
    sx,mx,my=[geometry[k] for k in ["mount_side_x_mm","mount_corner_x_mm","mount_corner_y_mm"]]
    mounts=np.array([(mx,my,0),(sx,0,0),(mx,-my,0),(-mx,-my,0),(-sx,0,0),(-mx,my,0)],dtype=float)
    angles=[45,0,-45,-135,180,135]
    l0,l1,l2,l3=geometry["link_lengths_mm"]
    height=l3*.9659-l2*.5
    radial=l0+l1+l2*.866+l3*.2588
    feet=np.array([(m[0]+radial*math.cos(math.radians(a)),m[1]+radial*math.sin(math.radians(a)),0) for m,a in zip(mounts,angles)])
    return mounts,angles,feet,height


def leg(i, R,T, geometry):
    mounts,angles,feet,height=rig(geometry)
    l0,l1,l2,l3=geometry["link_lengths_mm"]
    a=math.radians(angles[i]); c,s=math.cos(a),math.sin(a)
    C=np.array([[c,-s,0],[s,c,0],[0,0,1]])
    target=C.T@(R.T@(feet[i]-T)-mounts[i])
    x,y,z=target; q0=math.atan2(y,x-l0)
    u=math.hypot(x-l0,y)-l1; dist=math.hypot(u,z)
    c1=(dist*dist+l2*l2-l3*l3)/(2*l2*dist)
    c2=(dist*dist-l2*l2+l3*l3)/(2*l3*dist)
    if not -1<=c1<=1 or not -1<=c2<=1:
        raise ValueError("Unreachable leg target")
    alpha,beta=math.acos(c1),math.acos(c2)
    q1=math.atan2(z,u)+alpha; q2=math.pi/2-alpha-beta
    d=np.array([math.cos(q0),math.sin(q0),0])
    p0=np.zeros(3);p1=np.array([l0,0,0]);p2=p1+d*l1
    p3=p2+d*l2*math.cos(q1)+np.array([0,0,l2*math.sin(q1)])
    end=p3+d*l3*math.cos(q1+q2-math.pi/2)+np.array([0,0,l3*math.sin(q1+q2-math.pi/2)])
    points=[R@(mounts[i]+C@p)+T for p in [p0,p1,p2,p3,end]]
    return points,[math.degrees(q) for q in [q0,q1,q2]],float(np.linalg.norm(points[-1]-feet[i]))


def check():
    _,geometry=verify_inputs()
    _,_,feet,height=rig(geometry)
    records=[]
    for action in ACTIONS:
        mins=np.full(3,1e6);maxs=-mins.copy(); maxerror=0;violations=[]
        n=round(action["seconds"]*50)+1
        for i in range(n):
            t=i/50;p=pose(action,t);R=rotation(p)
            T=np.array([p["x_mm"],p["y_mm"],height+p["z_mm"]])
            for j in range(6):
                pts,qs,error=leg(j,R,T,geometry)
                mins=np.minimum(mins,qs);maxs=np.maximum(maxs,qs);maxerror=max(maxerror,error)
                for k,(q,(lo,hi)) in enumerate(zip(qs,[(-45,45),(-45,75),(-60,60)])):
                    if not lo<=q<=hi:violations.append([t,j,k,q])
        final=pose(action,action["seconds"])
        assert all(abs(v)<1e-9 for v in final.values()),"Action does not end at neutral"
        assert not violations,violations[:3]
        records.append({"id":action["id"],"samples_20ms":n,"joint_min_deg":mins.tolist(),"joint_max_deg":maxs.tolist(),
                        "max_fk_foot_error_mm":maxerror,"servo_limit_violations":violations,"ends_at_neutral":True,
                        "all_six_foot_targets_fixed":True})
    result={"status":"PASS_IDEAL_KINEMATICS_ONLY","geometry":geometry,"actions":records,
            "not_validated":["complete physical assembly","servo torque/speed/power","center of mass or dynamic stability","leg and body collision","real OLED display area/driver","real speech and robot synchronization"]}
    (OUT/"motion_checks.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"actions_checked":len(records),"pose_samples":sum(r["samples_20ms"] for r in records),"status":result["status"]}))


if __name__=="__main__":check()
