"""Offline genuine SPZ covariance versus current isotropic lean-disc footprint."""
import json
import math
import os
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(os.environ['APPDATA'])/'Python/Python314/site-packages')]
import numpy as np
import ply_to_splatmesh as source

def audit(path):
    count,cols,_=source.parse_spz(Path(path).read_bytes())
    s=np.exp(np.stack([cols['scale_'+str(i)] for i in range(3)],1).astype(float))
    alpha=1/(1+np.exp(-np.asarray(cols['opacity'])))
    w,x,y,z=np.stack([cols['rot_'+str(i)] for i in range(4)]).astype(float)
    length=np.sqrt(w*w+x*x+y*y+z*z);w/=length;x/=length;y/=length;z/=length
    # Quaternion columns, PLY->glTF flips Y/Z. A -X camera projects onto the YZ plane.
    axis_y=np.stack([-2*(x*y+w*z),-(1-2*(x*x+z*z)),-2*(y*z-w*x)],1)
    axis_z=np.stack([-2*(x*z-w*y),-2*(y*z+w*x),-(1-2*(x*x+y*y))],1)
    yy=np.sum((axis_y*s)**2,1);zz=np.sum((axis_z*s)**2,1);yz=np.sum(axis_y*axis_z*s*s,1)
    projected=np.sqrt(np.maximum(yy*zz-yz*yz,0))
    geometric=np.prod(s,1)**(2/3)
    ratio=projected/np.maximum(geometric,1e-12)
    def quantiles(values):return dict(zip(['p10','p50','p90','p99'],map(float,np.percentile(values,[10,50,90,99]))))
    order=np.sort(s,1)
    result=dict(source_points=count,kept=int((alpha>=.05).sum()),
        sigma_cm=quantiles(s.flatten()*100),thickness_over_major=quantiles(order[:,0]/order[:,2]),
        projected_area_over_current=quantiles(ratio),
        opacity_weighted_projected_area_over_current=float(np.sum(alpha*projected)/np.sum(alpha*geometric)),
        alpha=quantiles(alpha),lean_radius_cm=quantiles(np.sqrt(geometric)*200),
        windowed_two_sigma_gaussian_mass=float(1-(1+2)*math.exp(-2)),
        windowed_normalized_two_sigma_mass=float((1-3*math.exp(-2))/(1-math.exp(-2))),
        gaussian_three_sigma_mass=1-math.exp(-4.5))
    return result

if __name__=='__main__':
    result=audit('P:/FoA-Assets/level2/aholo/dream_interview_v2_20261112/world.spz')
    out=Path('P:/FoA/Saved/Integration/splat_visual_20261112/dream_footprint_audit.json')
    out.write_text(json.dumps(result,indent=1));print(json.dumps(result))
