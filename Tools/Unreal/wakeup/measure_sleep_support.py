"""Pose canonical visible skin and shirt surfaces; prepare exact bedding trace points."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import skin,matrix
root=Path('P:/FoA/Saved')
pose_path=Path(sys.argv[1]) if len(sys.argv)>1 else root/'AnimShots/wake_sleep_body_pose.json'
pose=json.loads(pose_path.read_text());bones={b['name']:b for b in pose['bones']}
world=pose['world'];wm=matrix(world['position'],world['rotation'],world['scale'])
points=[]
def add(name,point):points.append(dict(name=name,position=np.asarray(point).tolist()))
shirt,_,_=skin(pose_path,root/'WakeUp/teen_polo_skin_cache.npz')
for lo in range(275,336,10):
    patch=shirt[(shirt[:,0]>=lo)&(shirt[:,0]<lo+10)&(shirt[:,1]>-205)&(shirt[:,1]<-177)]
    if len(patch):add('shirt_back_'+str(lo),patch[patch[:,2].argmin()])
socks,_,_=skin(pose_path,root/'WakeUp/teen_socks_skin_cache.npz')
for side,mask in [('l',socks[:,1]>-190),('r',socks[:,1]<-190)]:
    patch=socks[mask];add('heel_'+side,patch[patch[:,2].argmin()])
landmarks=json.loads((root/'CharacterShots/mpfb/shirt_palm_diagnostic.json').read_text())['palms']
for side in 'lr':
    bone=bones['hand_'+side];transform=wm@matrix(bone['position'],bone['rotation'],bone['scale'])
    add('palm_'+side,(transform@np.r_[landmarks[side]['centroid_ue_cm'],1])[:3])
with np.load(root/'CharacterShots/mpfb/portrait_face/rigid_head_local_cm.npz') as f:
    head=np.column_stack((f['local'],np.ones(len(f['local']))))
bone=bones['head'];head=(head@(wm@matrix(bone['position'],bone['rotation'],bone['scale'])).T)[:,:3]
add('skull',head[head[:,2].argmin()])
report=dict(pose=str(pose_path),points=points,headward_skin_x=float(head[:,0].max()),toe_skin_x=float(socks[:,0].min()))
(root/'WakeUp/sleep_support_points.json').write_text(json.dumps(report,indent=1))
print(json.dumps(report,indent=1))
