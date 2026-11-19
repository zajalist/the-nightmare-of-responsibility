"""Native UE skin fixture and independent bake checks. No Blender coordinate conversion."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parents[1] / 'Unreal' / 'wakeup'))
import wake_math as m


def matrix(xf):
    out = np.eye(4)
    out[:3, :3] = R.from_quat(xf[1]).as_matrix() * np.asarray(xf[2])[None, :]
    out[:3, 3] = xf[0]
    return out


class Hand:
    def __init__(self, path):
        self.data = json.loads(Path(path).read_text())
        d = self.data
        self.parents = {b: p if p in d['local'] else None for b, p in d['parents'].items()}
        self.ids = {i: j for j, i in enumerate(d['ids'])}
        self.palm = [self.ids[i] for i in d['palm_ids']]
        self.tips = {b: [self.ids[i] for i in ids] for b, ids in d['tip_ids'].items()}
        self.ref = d['local']
        self.points = np.array(d['positions'])
        self.normals = np.array(d['normals'])
        self.palm_normal = self.normals[self.palm].mean(axis=0)
        self.palm_normal /= np.linalg.norm(self.palm_normal)
        self.weights = {}
        self.dom = [max(ws, key=lambda w:w[1])[0] for ws in d['weights']]
        for b in {b for ws in d['weights'] for b, _ in ws}:
            ws = np.array([dict(w).get(b, 0) for w in d['weights']])
            ix = np.flatnonzero(ws)
            inv = np.linalg.inv(matrix(d['world'][b]))
            local = self.points[ix] @ inv[:3, :3].T + inv[:3, 3]
            self.weights[b] = ix, ws[ix, None], local

    def world(self, local):
        return m.Pose(local, self.parents).world()

    def untwist_forearm(self, local, side):
        """Keep the hand target while putting axial rotation into the forearm, not the wrist."""
        result = copy.deepcopy(local)
        hand, forearm = 'hand_'+side, 'lowerarm_'+side
        world = self.world(local)
        hand_q = R.from_quat(world[hand][1])
        straight = hand_q * R.from_quat(self.ref[hand][1]).inv()
        direction = np.array(world[hand][0])-world[forearm][0]
        correction = R.from_quat(m.from_to(straight.apply(local[hand][0]),direction))
        forearm_q = correction * straight
        result[forearm] = [result[forearm][0], (R.from_quat(world[self.parents[forearm]][1]).inv()*forearm_q).as_quat().tolist(), result[forearm][2]]
        result[hand] = [result[hand][0], (forearm_q.inv()*hand_q).as_quat().tolist(), result[hand][2]]
        assert np.linalg.norm(np.array(self.world(result)[hand][0])-world[hand][0]) < 1e-5
        return result

    def skin(self, local):
        pose = self.world(local)
        out = np.zeros_like(self.points)
        for b, (ix, ws, local_points) in self.weights.items():
            t = matrix(pose[b])
            out[ix] += ws * (local_points @ t[:3, :3].T + t[:3, 3])
        return out

    def check_native_capture(self):
        live = self.data['live']
        got = self.skin(live['local'])
        t = matrix(live['body_world'])
        got = got @ t[:3, :3].T + t[:3, 3]
        error = np.linalg.norm(got - np.array(live['positions']), axis=1)
        assert error.max() < .02, ('native skin mismatch cm', float(error.max()))
        return dict(max_mm=float(error.max()*10), mean_mm=float(error.mean()*10))

    def flex_axis(self, bone):
        w = self.data['world']
        j = int(bone.split('_')[1])
        along = np.array(w[bone.replace('_0'+str(j)+'_', '_0'+str(j+1)+'_')][0])-w[bone][0] if j < 3 else np.array(w[bone][0])-w[bone.replace('_03_','_02_')][0]
        axis = np.cross(along,self.palm_normal)
        axis /= np.linalg.norm(axis)
        return R.from_quat(w[bone][1]).inv().apply(axis)

    def curl_motion(self, local, digit, joint=2, side='l'):
        """10 degrees along the baked local delta axis, tested on the reference skin."""
        bone = f'{digit}_0{joint}_{side}'
        delta = R.from_quat(self.ref[bone][1]).inv() * R.from_quat(local[bone][1])
        axis = delta.as_rotvec()
        if np.linalg.norm(axis) < 1e-6:
            return 0.
        q = R.from_quat(self.ref[bone][1]) * R.from_rotvec(axis / np.linalg.norm(axis) * np.deg2rad(10))
        test = copy.deepcopy(self.ref)
        test[bone][1] = q.as_quat().tolist()
        moved = (self.skin(test)[self.tips[digit]] - self.points[self.tips[digit]]).mean(axis=0)
        return float(moved @ self.palm_normal)


if __name__ == '__main__':
    hand = Hand(sys.argv[1])
    print('Native UE skin calibration', hand.check_native_capture())
    old = hand.data['live']['local']
    motions = {d:hand.curl_motion(old,d) for d in hand.tips}
    assert all(motions[d] > 0 for d in ('index','middle','ring','pinky'))
    assert motions['thumb'] < 0, 'old thumb must fail the anatomical curl check'
    print('Old bake regression reproduced:', motions)
