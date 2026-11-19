"""Solve the left-hand rotation for the phone hold from a pie_phone.py measurement (offline, numpy).
  python Tools/Unreal/player/calib_phone_hand.py <phone proof folder>
From a raised frame: the Teen hand_l bone's local finger axis (toward middle_01_l) and palm normal (the side of the
measured wrist-to-palm offset used by environment contact, 1.935,-6.298,0.318 in hand_l space) are mapped onto the
phone: fingers along the back toward the screen-right edge and up (-Y_mesh + 0.5 X_mesh), palm facing the glass
(-Z_mesh, the palm on the back). Prints PhoneHandRot as the rotation in the Screen-socket frame (UE Rotator),
and the wrist offset from Palm_L in hand space for the graph."""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

PALM_OFFSET = np.array([1.935470523, -6.297890748, 0.318129632])  # wrist -> palm contact, hand_l local (Teen basis)


def rot_quat(p, y, r):
    """UE FRotator::Quaternion (degrees) -> (x, y, z, w)."""
    sp, cp = math.sin(math.radians(p) / 2), math.cos(math.radians(p) / 2)
    sy, cy = math.sin(math.radians(y) / 2), math.cos(math.radians(y) / 2)
    sr, cr = math.sin(math.radians(r) / 2), math.cos(math.radians(r) / 2)
    return np.array([cr * sp * sy - sr * cp * cy, -cr * sp * cy - sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy])


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_rotator(m):
    """Rotation matrix (columns = local X, Y, Z in world) -> UE Rotator (pitch, yaw, roll) degrees."""
    x, y, z = m[:, 0], m[:, 1], m[:, 2]
    pitch = math.degrees(math.atan2(x[2], math.hypot(x[0], x[1])))
    yaw = math.degrees(math.atan2(x[1], x[0]))
    # roll: rotate the yaw/pitch-only frame's Y onto the actual Y about X
    m0 = quat_mat(rot_quat(pitch, yaw, 0.0))
    y0, z0 = m0[:, 1], m0[:, 2]
    roll = math.degrees(math.atan2(-np.dot(y, z0), np.dot(y, y0)))
    return pitch, yaw, roll


def parse_rot(s):
    v = dict(re.findall(r'(pitch|yaw|roll): (-?[\d.]+)', s))
    return float(v['pitch']), float(v['yaw']), float(v['roll'])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def basis(a, b):
    """Orthonormal frame with first axis a, second axis b made perpendicular, third a x b (columns)."""
    a = unit(a)
    b = unit(b - np.dot(b, a) * a)
    return np.stack([a, b, np.cross(a, b)], axis=1)


rows = json.loads((Path(sys.argv[1]) / 'phone.json').read_text())['rows']
row = max((r for r in rows if 'raise_' in r), key=lambda r: r['raise_'])
H = quat_mat(rot_quat(*parse_rot(row['hand_l_rot'])))
hand = np.array(row['hand_l'])
f_local = H.T @ unit(np.array(row['middle_01_l']) - hand)
n_local = PALM_OFFSET - np.dot(PALM_OFFSET, f_local) * f_local  # palm side of the finger axis
ax = {k: unit(v) for k, v in row['mesh_axes'].items()}
F = unit(-ax['y'] + 0.5 * ax['x'])  # fingers: up the back toward the screen's right edge
N = -ax['z']  # the palm faces the glass from behind
want = basis(F, N) @ basis(f_local, n_local).T  # hand_l world rotation that puts f on F and n on N
# the Screen socket is the mesh frame pitched -90: X -> -Z_mesh (out of the glass), Y -> Y_mesh, Z -> +X_mesh (top)
screen = np.stack([-ax['z'], ax['y'], ax['x']], axis=1)
rel = screen.T @ want  # PhoneHandRot: the hand rotation in the screen-socket frame
print('raise', row['raise_'], 'finger axis local', np.round(f_local, 3), 'palm side local', np.round(unit(n_local), 3))
print('PhoneHandRot (pitch, yaw, roll) =', tuple(round(a, 2) for a in mat_rotator(rel)))
print('wrist from Palm_L: Palm_L_world - hand_rot * %s' % PALM_OFFSET.tolist())
