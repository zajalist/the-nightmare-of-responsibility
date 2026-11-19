"""Rig lane, offline: the wire-hanger paths for the two hanger uses, sampled every DT s of montage time.
  python Tools/Rig/hanger_use_keys.py   -> Saved/RigShots/hanger_use/keys.json (+ a top/side plot per use)
The hanger is BP_FoAHangerUse's grip anchor: the right hand follows it (BeginGrip 'Hanger', the twin-solved hold:
hand_in_object from grip_bake.json). Mesh frame (SM_Lux3D_WireHanger, UE): the bottom bar along X at z -16.4, the
straightened stem up +Z, its tip at (0, 0, 16.1); 42 x 32.8 cm.
Per sample: A = hanger in the PAWN frame (x forward, y right, z up from the capsule centre: carried while he kneels),
B = hanger in WORLD (at the work), W = blend A->B, P = the proxy shirt in world (bed only).
Geometry (Saved/RigShots/hanger_use/geometry.json, story's clothing_chase_contract.py):
  door  BP_Door leaf x 367.5..386.5, latch edge y 41.6; frame from y 29.1; latch height z 88.5 (ToolContact). The stem goes
        into the gap at y 41.0 along +X, 5 cm in, wiggles, the latch gives (contact), out.
  bed   frame rail underside z 28 at y -134 (the +Y side), mattress underside 34; story's SNAG (269.76, -150.87, 4.69) and
        kneel stance (269.759, -95) facing -Y (StartClothingHanger uses the same stance, so the hand-off is seamless).
        The stem goes under the rail tilted 35 deg down, hooks the shirt, two tugs, the snag lets go (contact)."""
import json
import math
from pathlib import Path

import numpy as np

OUT = Path('P:/FoA/Saved/RigShots/hanger_use')
OUT.mkdir(parents=True, exist_ok=True)
DT = 0.05
TIP = np.array([0.0, 0.0, 16.1])  # stem tip, mesh frame (cm)
SNAG = np.array([269.758846282959, -150.86858081817624, 4.687624835968017])
# the twin's hold (hanger_grip_solution.json object_ue axes, component space: +Y forward, -X right) -> pawn frame
NEUTRAL_X = np.array([0.46, -0.827, 0.324])   # the bar
NEUTRAL_Z = np.array([0.869, 0.495, 0.029])   # the stem


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def frame(stem, bar_hint):
    z = unit(stem)
    x = unit(np.asarray(bar_hint, float) - np.dot(bar_hint, z) * z)
    y = np.cross(z, x)
    return np.stack([x, y, z], 1)  # columns: mesh X, Y, Z in the target space


def quat(m):
    """Rotation matrix (columns = axes) -> (x, y, z, w)."""
    t = np.trace(m)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    i = int(np.argmax(np.diag(m)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1.0 + m[i, i] - m[j, j] - m[k, k]) * 2
    q = [0.0, 0.0, 0.0, 0.0]
    q[i] = 0.25 * s
    q[j] = (m[j, i] + m[i, j]) / s
    q[k] = (m[k, i] + m[i, k]) / s
    q[3] = (m[k, j] - m[j, k]) / s
    return q


def yaw_rot(deg):
    a = math.radians(deg)
    return np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])


def pitch_down(v, deg):
    """Tilt a horizontal direction down by deg."""
    h = unit([v[0], v[1], 0])
    a = math.radians(deg)
    return h * math.cos(a) + np.array([0, 0, -math.sin(a)])


def smooth(t0, t1, t):
    s = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return s * s * (3 - 2 * s)


def lerp(a, b, s):
    return np.asarray(a, float) * (1 - s) + np.asarray(b, float) * s


def pose(tip_world, rot):
    """Mesh origin so that the stem tip lands on tip_world."""
    return np.asarray(tip_world, float) - rot @ TIP


def carry(t, t_down, t_up, length):
    """The hanger carried in the pawn frame: standing at the hip, kneeling low in front."""
    k = smooth(0.0, t_down, t) * (1 - smooth(t_up, length, t))
    loc = lerp([28, 22, -8], [32, 22, -30], k)
    rot = frame(NEUTRAL_Z, NEUTRAL_X)
    return pose(loc + rot @ TIP, rot), rot


def door():
    L, CONTACT = 5.2, 3.35
    fwd = np.array([1.0, 0, 0])
    bar = NEUTRAL_X  # pawn yaw 0: pawn frame == world axes
    gap = np.array([367.5, 41.0, 88.5])
    rows = []
    for n in range(int(round(L / DT)) + 1):
        t = n * DT
        depth = -3.0 + 8.0 * smooth(1.4, 1.9, t)                    # feed: 3 cm short of the face -> 5 cm in
        wig = smooth(1.9, 2.1, t) * (1 - smooth(3.1, 3.3, t))
        dz = 1.2 * math.sin(2 * math.pi * 3.2 * (t - 1.9)) * wig     # wiggle up/down
        yaw = 5.0 * math.sin(2 * math.pi * 2.1 * (t - 1.9)) * wig    # and side to side about the gap
        depth += 0.8 * math.sin(2 * math.pi * 1.6 * (t - 1.9)) * wig
        depth += 1.5 * smooth(3.25, 3.35, t)                         # the latch gives
        depth -= 10.0 * smooth(3.45, 3.95, t)                        # out
        stem = yaw_rot(yaw) @ fwd
        rot = frame(stem, bar)
        tip = gap + np.array([depth, 0, dz]) + np.array([0, 0, 0])
        a_loc, a_rot = carry(t, 0.8, 4.2, L)
        w = smooth(0.8, 1.4, t) * (1 - smooth(3.95, 4.25, t))
        rows.append(dict(t=round(t, 3), A=[a_loc.tolist(), quat(a_rot)], B=[pose(tip, rot).tolist(), quat(rot)], W=w,
                         P=[[0, 0, -500], [0, 0, 0, 1]], tip=tip.tolist()))
    return dict(length=L, contact=CONTACT, stance=[367.5 - 75.0, 41.0 - 18.0, 0.0], slide=0.6, proxy_hide=0.0, rows=rows)


def bed():
    L, CONTACT = 5.2, 3.35
    yaw = -90.0
    R = yaw_rot(yaw)                       # pawn -> world
    fwd = R @ np.array([1.0, 0, 0])        # (0, -1, 0)
    bar = R @ NEUTRAL_X
    hooked = SNAG + np.array([0, 3.0, 2.5])        # the tip just past the shirt's near edge
    entry = np.array([SNAG[0], -128.0, 15.0])       # under the rail's outer face (z 28 there)
    rows = []
    for n in range(int(round(L / DT)) + 1):
        t = n * DT
        s_in = smooth(1.3, 2.0, t)
        sweep = 4.0 * math.sin(2 * math.pi * 1.4 * (t - 1.3)) * s_in * (1 - smooth(1.8, 2.0, t))  # feeling for it
        tip = lerp(entry, hooked, s_in) + np.array([sweep, 0, 0])
        tip = tip + np.array([0, 0, -2.0 * smooth(2.0, 2.15, t) + 4.0 * smooth(2.15, 2.3, t)])  # dip under, lift: hooked
        tug1 = smooth(2.35, 2.5, t) * (1 - smooth(2.55, 2.7, t))
        tug2 = smooth(2.8, 2.95, t) * (1 - smooth(3.0, 3.15, t))
        tip = tip + np.array([0, 4.0 * tug1 + 5.0 * tug2, 0])         # two tugs: back out, the snag pulls it in again
        free = smooth(3.3, 3.45, t)
        tip = tip + np.array([0, 9.0 * free + 10.0 * smooth(3.45, 3.9, t), 1.0 * free])  # it lets go: the pull carries on
        tilt = 35.0 - 8.0 * smooth(2.15, 2.3, t) * (1 - free)       # the hook lifts a little once it has the shirt
        rot = frame(pitch_down(fwd, tilt), bar)
        a_loc, a_rot = carry(t, 0.7, 4.1, L)
        w = smooth(0.7, 1.3, t) * (1 - smooth(3.9, 4.15, t))
        # the proxy shirt (hidden under the bed until now): at the snag, it jerks with each tug, stays put after contact
        shirt = SNAG + np.array([0, 2.0 * tug1 + 2.5 * tug2, 0])
        rows.append(dict(t=round(t, 3), A=[a_loc.tolist(), quat(a_rot)], B=[pose(tip, rot).tolist(), quat(rot)], W=w,
                         P=[shirt.tolist(), quat(yaw_rot(0))], tip=tip.tolist()))
    return dict(length=L, contact=CONTACT, stance=[269.759, -95.0, -90.0], slide=0.6, proxy_hide=CONTACT, rows=rows)


def check(name, d):
    """Clearance of the stem path: bed rail / mattress, door face; prints the minimum margins."""
    tips = np.array([r['tip'] for r in d['rows'] if r['W'] > 0.99])
    if name == 'bed':
        # stem segment from tip back 32.5 cm along its direction: its height where it crosses y = -134 (rail) must be < 26
        worst = -99.0
        for r in d['rows']:
            if r['W'] < 0.99:
                continue
            org = np.array(r['B'][0])
            x, y, z, w = r['B'][1]
            q = np.array([x, y, z])
            stem = 2 * q.dot([0, 0, 1]) * q + (w * w - q.dot(q)) * np.array([0, 0, 1.0]) + 2 * w * np.cross(q, [0, 0, 1])
            tip = np.array(r['tip'])
            if tip[1] > -134:
                continue
            k = (-134 - tip[1]) / (-stem[1]) if stem[1] < 0 else 0
            worst = max(worst, tip[2] + k * (-stem[2]))
        print(name, 'stem height at the rail (must be < 26):', round(worst, 1), 'tip z range', tips[:, 2].min().round(1), tips[:, 2].max().round(1))
    else:
        print(name, 'tip x range', tips[:, 0].min().round(1), tips[:, 0].max().round(1), 'z', tips[:, 2].min().round(1), tips[:, 2].max().round(1))


keys = dict(dt=DT, hand_in_object=json.load(open('P:/FoA/Saved/AnimShots/grip_bake.json'))['Hanger']['hand_in_object'],
            door=door(), bed=bed())
for k in ('door', 'bed'):
    check(k, keys[k])
Path(OUT / 'keys.json').write_text(json.dumps(keys))
print('keys', {k: len(keys[k]['rows']) for k in ('door', 'bed')})
