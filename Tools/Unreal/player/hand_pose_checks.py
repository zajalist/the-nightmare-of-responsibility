"""Anatomical bake gate calibrated from UE's reference skin, independent of the twin."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'wakeup'))
import wake_math as m


def phone(sol, ref, palm_normal=(-.627473699193995,-.020155240125951313,-.7783768516054862)):
    """Reject free-aimed thumb hyperextension and an edge-facing palm before writing an asset."""
    names = ref['names']
    parents = {}
    for i, b in enumerate(names):
        if not i:
            parents[b] = None
            continue
        parents[b] = min(names[:i], key=lambda p:m.length(m.sub(m.add(ref['world'][p][0],
            m.qrot(ref['world'][p][1], ref['local'][b][0])), ref['world'][b][0])))
    results = {}
    for frame in ('hold', 'tap'):
        from measure_grip_pose import wrist_rotation
        wrist = wrist_rotation(sol[frame],ref['local'],'l')
        assert wrist['wrist_axial_pass'], (frame,'axial wrist twist',wrist)
        pose = m.Pose(sol[frame], parents).world()
        hq = pose['hand_l'][1]
        normal = m.qrot(m.qmul(hq, m.qinv(ref['world']['hand_l'][1])), palm_normal)
        phone_q = m.qmul(hq, sol['out']['attach']['rotation'])
        toward = m.qrot(phone_q, (0,0,-1))
        facing = math.degrees(math.acos(max(-1,min(1,m.dot(m.norm(normal),toward)))))
        assert facing <= 35, (frame, 'palm facing', facing)
        angles, motion = {}, {}
        for digit in ('index','middle','ring','pinky','thumb'):
            for j, limit in enumerate((85 if digit == 'thumb' else 90, 70 if digit == 'thumb' else 110, 80), 1):
                b = f'{digit}_0{j}_l'
                delta = m.qnorm(m.qmul(m.qinv(ref['local'][b][1]), sol[frame][b][1]))
                if delta[3] < 0:
                    delta = tuple(-v for v in delta)
                deg = math.degrees(2*math.acos(max(-1,min(1,delta[3]))))
                angles[b] = deg
                assert deg <= limit+.01, (frame,b,'joint limit',deg,limit)
                if j < 2:
                    continue  # thumb opposition and MCP spread are not pure hinges
                axis = m.norm(delta[:3])
                a = ref['world'][b]
                prev = ref['world'][f'{digit}_0{j-1}_l'][0]
                along = m.sub(ref['world'][f'{digit}_03_l'][0],a[0]) if j == 2 else m.sub(a[0], prev)
                velocity = m.cross(m.qrot(a[1],axis),along)
                signed = m.dot(velocity,palm_normal)
                motion[b] = signed
                assert deg >= 5 and signed > 0, (frame,b,'hyperextension or flat joint',deg,signed)
        results[frame] = dict(palm_facing_deg=facing, joint_degrees=angles, curl_sign_checks=motion,**wrist)
    return results
