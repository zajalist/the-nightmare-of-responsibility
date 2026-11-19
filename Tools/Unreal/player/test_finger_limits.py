"""Joint limits use the shortest quaternion angle on either hand."""
import copy
from measure_grip_pose import finger_limits, m

for side in ('l', 'r'):
    ref = {f'{d}_0{j}_{side}': [(0,0,0),(0,0,0,1),(1,1,1)]
           for d in ('thumb','index','middle','ring','pinky') for j in (1,2,3)}
    pose = copy.deepcopy(ref)
    bone = 'index_02_'+side
    pose[bone][1] = m.qaxis((1,0,0),110)
    assert finger_limits(pose,ref,side)['joints_pass']
    pose[bone][1] = tuple(-v for v in pose[bone][1])
    assert finger_limits(pose,ref,side)['joints_pass']
    pose[bone][1] = m.qaxis((1,0,0),111)
    assert not finger_limits(pose,ref,side)['joints_pass']
print('Finger limits: bilateral boundary and quaternion-sign controls passed')
