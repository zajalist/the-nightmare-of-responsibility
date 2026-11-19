"""Offline joint and attachment checks on pie_pose_capture.capture_grip JSON. No editor connection."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal/wakeup')
import wake_math as m


def reference_hierarchy():
    ref = json.loads(Path('P:/FoA/Saved/AnimShots/teen_ref_pose.json').read_text())
    names, parents = ref['names'], {}
    for i, bone in enumerate(names[1:], 1):
        lp = ref['local'][bone][0]
        parents[bone] = min(names[:i], key=lambda p: m.length(m.sub(
            m.add(ref['world'][p][0], m.qrot(ref['world'][p][1], lp)), ref['world'][bone][0])))
    return ref, parents


def finger_limits(local, reference, side):
    degrees, limits = {}, {}
    for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        for j, limit in zip((1, 2, 3), ((85, 70, 80) if digit == 'thumb' else (90, 110, 80))):
            bone = f'{digit}_0{j}_{side}'
            q = m.qnorm(m.qmul(m.qinv(reference[bone][1]), local[bone][1]))
            degrees[bone] = math.degrees(2 * math.acos(min(1, abs(q[3]))))
            limits[bone] = limit
    return dict(joint_deg=degrees, joint_limits=limits, joints_pass=all(v <= limits[b]+.01 for b,v in degrees.items()))


def wrist_rotation(local, reference, side):
    bone = 'hand_'+side
    q = m.qnorm(m.qmul(m.qinv(reference[bone][1]),local[bone][1]))
    if q[3] < 0:
        q = tuple(-v for v in q)
    axis = m.norm(m.qrot(m.qinv(reference[bone][1]),reference[bone][0]))
    twist = math.degrees(2*math.atan2(m.dot(q[:3],axis),q[3]))
    return dict(wrist_axial_twist_deg=twist,wrist_axial_limit_deg=20,wrist_axial_pass=abs(twist)<=20,
                wrist_reference_rotation_deg=math.degrees(2*math.acos(min(1,q[3]))))


def measure(path):
    cap = json.loads(Path(path).read_text())
    ref, parents = reference_hierarchy()
    w = m.Pose(cap['hold'], parents).world()
    hand = cap.get('hand', 'hand_r')
    side = hand[-1]
    shoulder, elbow, wrist = [w[b][0] for b in (f'upperarm_{side}', f'lowerarm_{side}', hand)]
    fa, ua = m.sub(wrist, elbow), m.sub(elbow, shoulder)
    fingers = m.sub(w[f'middle_01_{side}'][0], wrist)
    angle = lambda a, b: math.degrees(math.acos(max(-1, min(1, m.dot(m.norm(a), m.norm(b))))))
    body = cap['body_world']
    world_hand = m.add(body[0], m.qrot(body[1], tuple(wrist[i] * body[2][i] for i in range(3))))
    obj = next(iter(cap['objects'].values()))
    relative = obj['in_hand']
    hand_rot = m.qmul(body[1], w[hand][1])
    obj_from_hand = m.add(world_hand, m.qrot(hand_rot, tuple(relative[0][i] * body[2][i] for i in range(3))))
    error = m.length(m.sub(obj_from_hand, obj['world'][0])) * 10
    assert error < 0.1, ('captured hierarchy did not round-trip', error)
    return dict(pose=str(path), wrist_deg=round(angle(fa, fingers), 2), elbow_deg=round(angle(m.mul(ua, -1), fa), 2),
                **finger_limits(cap['hold'], ref['local'], side),
                **wrist_rotation(cap['hold'], ref['local'], side),
                attachment_error_mm=round(error, 6), shoulder=shoulder, elbow=elbow, wrist=wrist)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        result = measure(path)
        Path(path).with_suffix('.metrics.json').write_text(json.dumps(result, indent=1))
        print(json.dumps(result))
