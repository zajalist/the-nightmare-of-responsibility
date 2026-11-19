"""Offline case-support fit from actual Teen skin; preserves wrist/index/thumb."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import differential_evolution
sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from sleep_skin_contact import matrix
root=Path('P:/FoA/Saved/UIShots');source=root/'phone_grip_verified_20261108_0340'
p=json.loads((source/'phone_grip_body_pose.json').read_text());frames=json.loads((source/'phone_grip_frames.json').read_text())
retarget=json.loads(Path('P:/FoA/Saved/Integration/finger_retarget_test.json').read_text())['cases']
with np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz') as z:c={n:z[n] for n in z.files}
names=c['bone_names'].tolist();idx={n:i for i,n in enumerate(names)};parent=c['parent_indices'];bones={b['name']:b for b in p['bones']}
bm=np.array([matrix(bones[n]['position'],bones[n]['rotation'],bones[n]['scale']) for n in names]);local=np.array([np.linalg.inv(bm[parent[i]])@bm[i] if parent[i]>=0 else bm[i] for i in range(len(names))])
world=matrix(p['world']['position'],p['world']['rotation'],p['world']['scale']);f=frames['phone'];pm=matrix(f['position'],f['rotation'],f['scale']);case=np.linalg.inv(pm)@world
lo,hi=np.array(frames['parts']['Mesh']['bounds']);iv=np.repeat(np.arange(len(c['vertices_cm'])),np.diff(c['vertex_offsets']));verts=np.c_[c['vertices_cm'],np.ones(len(c['vertices_cm']))];inverse=np.linalg.inv(c['reference_matrices'])
angles={'middle':[55,70,30],'ring':[60,75,35],'pinky':[65,75,35]};relaxed={'middle':[15,25,10],'ring':[18,28,12],'pinky':[20,30,15]}
report={}
for digit,old in angles.items():
 chain=[idx[f'{digit}_0{j}_r'] for j in (1,2,3)];axes=[]
 for j,i in enumerate(chain):
  name=names[i];par=names[parent[i]]
  def q(case):return R.from_quat(retarget[case][par]['q']).inv()*R.from_quat(retarget[case][name]['q'])
  a=(q('neutral').inv()*q('relaxed')).as_rotvec();axes.append(a/np.linalg.norm(a))
 weight=np.zeros(len(verts));np.add.at(weight,iv,c['weight_values']*np.isin(c['weight_bones'],chain));selected=weight>.5;vis=np.where(selected)[0]
 mask=selected[iv];vix=iv[mask];wb=c['weight_bones'][mask];wv=c['weight_values'][mask]
 tipweight=np.zeros(len(verts));np.add.at(tipweight,iv,c['weight_values']*(c['weight_bones']==chain[-1]));tip=tipweight[vis]>.5
 def geometry(values):
  posed=bm.copy()
  for i,axis,prior,new in zip(chain,axes,old,values):
   rot=np.eye(4);rot[:3,:3]=R.from_rotvec(axis*np.radians(new-prior)).as_matrix();posed[i]=posed[parent[i]]@local[i]@rot
  deform=posed@inverse;v=np.zeros((len(verts),4));np.add.at(v,vix,np.einsum('nij,nj->ni',deform[wb],verts[vix])*wv[:,None]);v=(v[vis]@case.T)[:,:3]
  return v
 target=np.array([-8.15,{'middle':3.,'ring':1.4,'pinky':-.2}[digit],-.1])
 def terms(values):
  v=geometry(values);pad=v[tip]
  # Actual skin, not the joint. Nearest pad to a point just beyond the bottom edge.
  contact=np.min(np.linalg.norm(pad-target,axis=1))
  q=np.maximum(lo-v,v-hi);depth=np.maximum(-q.max(axis=1),0)
  # Keep support low: don't unfurl over the display's main content.
  front=(v[:,2]<lo[2])&(v[:,1]>lo[1])&(v[:,1]<hi[1]);occlusion=np.maximum(v[front,0]+6.0,0)
  score=contact**2*10+np.sum(depth**2)*80+np.sum(occlusion**2)*8+.0002*np.sum((np.array(values)-[40,25,15])**2)
  return score,contact,depth.max(),float(occlusion.max(initial=0)),v
 coupled=lambda a:np.array([a[0],a[1],a[1]*.6])
 result=differential_evolution(lambda a:terms(coupled(a))[0],[(5,85),(10,85)],seed=3,maxiter=80,popsize=12,tol=1e-7)
 fitted=coupled(result.x)
 score,contact,depth,occ,v=terms(fitted)
 report[digit]=dict(curls=fitted.tolist(),score=score,target=target.tolist(),tip_target_distance_cm=contact,max_case_penetration_cm=depth,front_screen_height_over_bottom_cm=occ+2,skin_bounds=[v.min(0).tolist(),v.max(0).tolist()])
 print(digit,json.dumps(report[digit]))
(root/'phone_support_contact_fit_experiment.json').write_text(json.dumps(dict(source=str(source),digits=report,preserve=['thumb_r','index_r','hand_r','all non-support tracks'],status='Rejected contact-target experiment: independent support-finger targets produce an awkward dangling pose. Do not bake.'),indent=2))
