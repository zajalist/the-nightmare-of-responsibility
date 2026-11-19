"""A 90-degree wrist twist must move into the forearm without moving the held hand."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation as R
from ue_hand import Hand
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from measure_grip_pose import wrist_rotation

for side,path in [('r','screwdriver_0_fixture.json'),('l','ue_hand_l_fixture.json')]:
    h=Hand('P:/FoA/Saved/AnimShots/review/'+path)
    local=copy.deepcopy(h.ref);hand='hand_'+side;forearm='lowerarm_'+side;w=h.world(local)
    axis=np.array(local[hand][0]);axis/=np.linalg.norm(axis)
    local[forearm][1]=(R.from_quat(local[forearm][1])*R.from_rotvec(axis*np.pi/2)).as_quat().tolist()
    twisted=h.world(local)
    local[hand][1]=(R.from_quat(twisted[forearm][1]).inv()*R.from_quat(w[hand][1])).as_quat().tolist()
    old=(R.from_quat(h.ref[hand][1]).inv()*R.from_quat(local[hand][1])).magnitude()*180/np.pi
    assert old>89
    assert not wrist_rotation(local,h.ref,side)['wrist_axial_pass']
    fixed=h.untwist_forearm(local,side)
    tuple_fixed=h.untwist_forearm({b:tuple(v) for b,v in local.items()},side)
    assert np.max(np.abs(h.skin(tuple_fixed)-h.skin(fixed)))<1e-8
    assert (R.from_quat(h.ref[hand][1]).inv()*R.from_quat(fixed[hand][1])).magnitude()<1e-6
    assert wrist_rotation(fixed,h.ref,side)['wrist_axial_pass']
    assert np.max(np.linalg.norm(h.skin(fixed)-h.skin(h.ref),axis=1))<1e-5
    assert fixed[forearm][0] is not local[forearm][0]
print('Left/right wrist twist regression passes; hand target and reference skin preserved')
