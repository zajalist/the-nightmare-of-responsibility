"""Emit a native-calibrated phone hold and a small, non-penetrating thumb press for the existing bake chain."""
import copy
import json
import sys
import numpy as np
from scipy.optimize import least_squares
import phone_native as N

sys.path.insert(0,str(N.ROOT/'Tools/Unreal/player'))
import hand_pose_checks

fit = json.loads((N.ROOT/'Saved/AnimShots/review/phone_native_fit.json').read_text())
x = np.array(fit['x'])
report = N.metrics(x)
assert report['min_skin_mm'] >= 1 and report['palm_facing_deg'] <= 35, report
assert report['wrist_deg'] <= 35, report
assert all(1 <= d <= 3 for d in report['contacts_mm'].values()),report
assert 1 <= report['thumb_pad_gap_mm'] <= 3, report
assert all(report['tips'][d][1] < -3.55 for d in N.DIG), report
assert all(v > 0 for v in report['curl_motion'].values()), report

def tap_residual(a):
    t = x.copy(); t[21:23] = a
    ps = N.points(N.pose(t))
    return np.r_[40*(ps[N.thumb_pad,2].max()+.55), 100*np.maximum(.02-N.sdf(ps)[N.hand_rows],0)]

press = least_squares(tap_residual,x[21:23],bounds=(np.maximum(8,x[21:23]-6),np.minimum([65,50],x[21:23]+6)),max_nfev=80)
t = x.copy(); t[21:23] = press.x
tap_report = N.metrics(t)
assert tap_report['min_skin_mm'] >= 0 and 0 <= tap_report['thumb_pad_gap_mm'] < report['thumb_pad_gap_mm']-.4, tap_report
hold, tap = N.pose(x),N.pose(t)
world = N.H.world(hold)
hp,hq,_ = world['hand_l']
CQ = N.R.from_matrix(np.column_stack((N.F,N.RIGHT,N.UP)))
hand_q = N.R.from_quat(hq)
eye_space = lambda p: [float(np.dot(np.array(p)-N.eye,a)) for a in (N.F,N.RIGHT,N.UP)]
sol = dict(names=list(hold),hold=hold,tap=tap,out=dict(hold='UE skin calibrated palm cradle',eye=N.eye.tolist(),
    phone_centre=N.P.tolist(),screen_distance_cm=float(np.linalg.norm(N.P-N.eye)),native_check=dict(hold=report,tap=tap_report),
    attach=dict(location=hand_q.inv().apply(N.P-hp).tolist(),rotation=(hand_q.inv()*N.PQ).as_quat().tolist()),
    camera=dict(hand_location=eye_space(hp),hand_rotation=(CQ.inv()*hand_q).as_quat().tolist(),
        elbow_location=eye_space(world['lowerarm_l'][0]))))
ref = json.loads((N.ROOT/'Saved/AnimShots/teen_ref_pose.json').read_text())
try:
    old = json.loads((N.ROOT/'Saved/AnimShots/review/phone_before_native_solution.json').read_text())
    hand_pose_checks.phone(old,ref,N.H.palm_normal)
except AssertionError as e:
    print('Old bake rejected:',e)
else:
    raise AssertionError('old phone escaped the anatomical gate')
sol['out']['anatomy'] = hand_pose_checks.phone(sol,ref,N.H.palm_normal)
path = N.ROOT/'Saved/AnimShots/phone_native_solution.json'
path.write_text(json.dumps(sol,default=lambda a:a.tolist()))
print('NATIVE PHONE',path,'hold',report,'tap',tap_report)
