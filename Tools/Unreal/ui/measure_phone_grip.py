"""Validate the freshly captured physical phone against actual skinned Teen fingertip pads."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import skin,matrix
out=Path('P:/FoA/Saved/UIShots');frames=json.loads((out/'phone_grip_frames.json').read_text())
pose=json.loads((out/'phone_grip_body_pose.json').read_text());bones={b['name']:b for b in pose['bones']}
world=matrix(pose['world']['position'],pose['world']['rotation'],pose['world']['scale'])
def bone(n):
    b=bones[n];return world@matrix(b['position'],b['rotation'],b['scale'])
v,c,meta=skin(out/'phone_grip_body_pose.json','P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz');assert not meta['fallback']
names=c['bone_names'].tolist();vi=np.repeat(np.arange(len(v)),np.diff(c['vertex_offsets']));weights={}
for name in ('index_03_r','thumb_03_r'):
    a=np.zeros(len(v));np.add.at(a,vi,c['weight_values']*(c['weight_bones']==names.index(name)));weights[name]=a
pads=[]
for digit in ('index','thumb'):
    points=v[weights[digit+'_03_r']>.5];end=bone(digit+'_03_r')[:3,3];start=bone(digit+'_02_r')[:3,3]
    axis=end-start;axis/=np.linalg.norm(axis);extension=(points-end)@axis;pads.append(points[extension>max(.1,extension.max()*.45)])
distance=cdist(*pads);i,j=np.unravel_index(distance.argmin(),distance.shape);contacts=np.array([pads[0][i],pads[1][j]])
phone=frames['phone'];pm=matrix(phone['position'],phone['rotation'],phone['scale']);local=(np.c_[contacts,np.ones(2)]@np.linalg.inv(pm).T)[:,:3]
lo,hi=np.array(frames['parts']['Mesh']['bounds']);outside=np.maximum(np.maximum(lo-local,local-hi),0)
gaps=np.linalg.norm(outside,axis=1)
handweights=np.zeros(len(v));valid=[n for n in names if n.endswith('_r') and n.startswith(('hand','index','thumb','middle','ring','pinky'))]
np.add.at(handweights,vi,c['weight_values']*np.isin(c['weight_bones'],[names.index(n) for n in valid]))
hand=(np.c_[v[handweights>.5],np.ones(sum(handweights>.5))]@np.linalg.inv(pm).T)[:,:3]
depth=np.maximum(-np.max(np.maximum(lo-hand,hand-hi),axis=1),0)
result=dict(pad_gap_cm=float(distance[i,j]),pad_case_local=local.tolist(),pad_to_case_box_gap_cm=gaps.tolist(),
    max_skin_vertex_penetration_cm=float(depth.max()),phone_scale=phone['scale'],source='Fresh actual message-view Teen skin and physical case transform')
assert max(gaps)<.15,result
assert depth.max()<.15,result
assert max(abs(np.array(phone['scale'])-1))<.001,result
(out/'phone_grip_contact_verified.json').write_text(json.dumps(result,indent=1));print(json.dumps(result,indent=1))
