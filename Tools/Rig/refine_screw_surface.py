"""Refine solved screwdriver fingers against UE's captured triangles, not the Blender proxy."""
import copy,json
import numpy as np
import trimesh
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
from export_screw_runtime import H,ROOT,K,mesh,load,distance
TREE=cKDTree(mesh.triangles_center)
DIGITS=('thumb','index','middle','ring','pinky')

def run(i):
 s,p=load(i,False);o=s['object_ue']; inv=R.from_quat(o['quat']).inv(); scale=o['scale'][0]*K
 for digit in DIGITS:
  bones=[f'{digit}_0{j}_r' for j in (1,2,3)]; rows=np.array([k for k,b in enumerate(H.dom) if b.startswith(digit+'_')]);pad=np.array([H.ids[k] for k in H.data['thumb_pad_ids']]) if digit=='thumb' else rows
  def pose(x):
   a=copy.deepcopy(p)
   a[bones[0]][1]=(R.from_quat(H.ref[bones[0]][1])*R.from_rotvec(np.deg2rad(x[:3]))).as_quat().tolist()
   for j,b in enumerate(bones[1:]):a[b][1]=(R.from_quat(H.ref[b][1])*R.from_rotvec(H.flex_axis(b)*np.deg2rad(x[3+j]))).as_quat().tolist()
   return a
  def distances(a):
   pts=inv.apply(H.skin(a)-o['loc'])/o['scale']; subset=np.unique(np.r_[rows,pad]); pts=pts[subset]
   _,ids=TREE.query(pts,k=96); q=trimesh.triangles.closest_point(mesh.triangles[ids].reshape(-1,3,3),np.repeat(pts,96,axis=0)).reshape(-1,96,3)
   ds=np.linalg.norm(q-pts[:,None,:],axis=2); col=ds.argmin(1); rr=np.arange(len(pts)); q=q[rr,col]; ids=ids[rr,col];ds=ds[rr,col]*np.where(np.einsum('ij,ij->i',pts-q,mesh.face_normals[ids])>=0,1,-1)*scale
   return ds[np.searchsorted(subset,rows)],ds[np.searchsorted(subset,pad)]
  def seed(a):
   rv=(R.from_quat(H.ref[bones[0]][1]).inv()*R.from_quat(a[bones[0]][1])).as_rotvec()*180/np.pi
   return np.r_[rv,[(R.from_quat(H.ref[b][1]).inv()*R.from_quat(a[b][1])).magnitude()*180/np.pi for b in bones[1:]]]
  original=seed(p);lo=[-85]*3+[15,15];hi=[85]*3+[70 if digit=='thumb' else 110,75];best=None
  starts=[original]
  if digit=='thumb':starts += [seed(load(j,False)[1]) for j in (0,3)]
  def residual(x):
   ds,ps=distances(pose(x))
   return np.r_[400*np.maximum(.16-ds,0),40*(ps.min()-.20),15*max(0,np.linalg.norm(x[:3])-(84 if digit=='thumb' else 89)),.015*(x-original)]
  for start in starts:
   fit=least_squares(residual,np.clip(start,lo,hi),bounds=(lo,hi),max_nfev=100,diff_step=1e-3)
   if best is None or fit.cost<best.cost:best=fit
  p=pose(best.x);print(i,digit,'cost',best.cost,'angles',best.x,flush=True)
 for b in [f'{d}_0{j}_r' for d in DIGITS for j in (1,2,3)]:s['pose'][b]=p[b][1]
 report=distance(s,p);print('native',i,report,flush=True)
 assert min(report.values())>=1.0 and max(report[d] for d in DIGITS)<=3,report
 import sys
 sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from measure_grip_pose import finger_limits
 assert finger_limits(p,H.ref,'r')['joints_pass']
 assert all(H.curl_motion(p,d,j,'r')>0 for d in DIGITS for j in (2,3))
 s['native_clearance_mm']=report;(ROOT/f'screwdriver_screw{i}_native_solution.json').write_text(json.dumps(s,indent=2))
if __name__=='__main__':
 for i in ([int(__import__("sys").argv[1])] if len(__import__("sys").argv)>1 else range(4)):run(i)
