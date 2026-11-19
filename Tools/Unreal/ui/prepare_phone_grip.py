"""Fit the physical case to a widened, already validated key pinch on the Teen hand."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
from scipy.spatial.distance import cdist
from scipy.spatial.transform import Rotation as R
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from sleep_skin_contact import matrix

out=Path('P:/FoA/Saved/UIShots')
p=json.loads((out/'phone_grip_body_pose.json').read_text())
k=json.loads(Path('P:/FoA/Saved/AnimShots/key_pinch/20261108_030427/pressure_body.json').read_text())
with np.load('P:/FoA/Saved/WakeUp/teen_body_full_skin_cache.npz') as z:c={n:z[n] for n in z.files}
names=c['bone_names'].tolist();parents=c['parent_indices'];idx={n:i for i,n in enumerate(names)}
def mats(d):
    b={x['name']:x for x in d['bones']}
    return np.array([matrix(b[n]['position'],b[n]['rotation'],b[n]['scale']) for n in names])
pm,km=mats(p),mats(k);h=idx['hand_r'];world=matrix(p['world']['position'],p['world']['rotation'],p['world']['scale'])
fingers=[i for i,n in enumerate(names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
base=pm.copy()
for i in fingers:base[i]=pm[h]@np.linalg.inv(km[h])@km[i]
joint=idx['index_02_r'];par=parents[joint]
lp=np.linalg.inv(pm[par])@pm[joint];lk=np.linalg.inv(km[par])@km[joint]
axis=(R.from_matrix(lp[:3,:3]).inv()*R.from_matrix(lk[:3,:3])).as_rotvec()
axis/=np.linalg.norm(axis)
verts=np.c_[c['vertices_cm'],np.ones(len(c['vertices_cm']))];vi=np.repeat(np.arange(len(verts)),np.diff(c['vertex_offsets']))
weights={n:np.zeros(len(verts)) for n in ('index_03_r','thumb_03_r')};handweight=np.zeros(len(verts))
for n,w in weights.items():np.add.at(w,vi,c['weight_values']*(c['weight_bones']==idx[n]))
np.add.at(handweight,vi,c['weight_values']*np.isin(c['weight_bones'],[h]+fingers))
def pose(curl):
    bm=base.copy();local=lk.copy();local[:3,:3]=lk[:3,:3]@R.from_rotvec(axis*np.radians(curl-65)).as_matrix()
    bm[joint]=bm[par]@local
    child=idx['index_03_r'];bm[child]=bm[joint]@np.linalg.inv(km[joint])@km[child]
    deform=bm@np.linalg.inv(c['reference_matrices']);v=np.zeros((len(verts),4))
    np.add.at(v,vi,np.einsum('nij,nj->ni',deform[c['weight_bones']],verts[vi])*c['weight_values'][:,None])
    v=(v@world.T)[:,:3];pads=[]
    for digit in ('index','thumb'):
        patch=v[weights[digit+'_03_r']>.5];b=(world@bm[idx[digit+'_03_r']])[:3,3];a=(world@bm[idx[digit+'_02_r']])[:3,3]
        direction=b-a;direction/=np.linalg.norm(direction);extension=(patch-b)@direction
        pads.append(patch[extension>max(.1,extension.max()*.45)])
    distances=cdist(*pads);i,j=np.unravel_index(distances.argmin(),distances.shape)
    return float(distances[i,j]),pads[0][i],pads[1][j],v,bm
curl=brentq(lambda a:pose(a)[0]-1.22,0,20)
gap,index,thumb,v,bm=pose(curl);center=(index+thumb)/2;normal=(index-thumb)/gap
up=np.array([0.,0.,1.]);up-=normal*np.dot(up,normal);up/=np.linalg.norm(up)
side=np.cross(normal,up);rotation=np.column_stack((up,side,normal))
# The rest of the curled fingers stay outside the bottom/side of the case.
handpoints=v[handweight>.5]
anchor=np.array([-7.95,3.58,0.])
phone=np.eye(4);phone[:3,:3]=rotation;phone[:3,3]=center-rotation@anchor
hand=world@bm[h];relative=np.linalg.inv(hand)@phone;scale=np.linalg.norm(relative[:3,:3],axis=0)
q=R.from_matrix(relative[:3,:3]/scale).as_quat()
local=(handpoints-phone[:3,3])@rotation;box=np.abs(local-np.array([.00085,-.0051,-.0132]))-np.array([7.98935,3.5937,.5988])
depth=np.maximum(-np.max(box,axis=1),0)
result=dict(index_02_curl_deg=curl,pad_gap_cm=gap,relative_location=relative[:3,3].tolist(),relative_quaternion=q.tolist(),
    relative_scale=scale.tolist(),pinch_case_local=anchor.tolist(),max_skin_vertex_penetration_cm=float(depth.max()),
    contact_world=center.tolist(),source='Measured Teen skin, validated key pinch widened only at index middle joint; case lower corner between thumb and index',proof_pending=True)
(out/'phone_grip_fit.json').write_text(json.dumps(result,indent=1));print(json.dumps(result,indent=1))
