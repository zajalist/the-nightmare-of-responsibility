"""Close only the three loose fingers against the exported UE phone triangles."""
import json
import numpy as np
from scipy.optimize import least_squares
import phone_native as N

path = N.ROOT/'Saved/AnimShots/review/phone_native_fit.json'
before = json.loads(path.read_text())
x = np.array(before['x'])
start = x[9:18].copy()

def residual(y):
    candidate = x.copy(); candidate[9:18] = y
    points = N.points(N.pose(candidate)); distance = N.sdf(points)
    values = [100*np.maximum(.12-distance[N.hand_rows],0),.01*(y-start)]
    for digit in ('middle','ring','pinky'):
        values.append(np.array([30*(distance[N.digit_rows[digit]].min()-.20),
            10*max(0,points[N.H.tips[digit],1].mean()+3.55)]))
    values.append(5*np.maximum(y[2::3]-.75*y[1::3]-5,0))
    return np.concatenate(values)

fit = least_squares(residual,start,bounds=(np.tile([8,12,8],3),np.tile([65,105,65],3)),max_nfev=100,ftol=1e-6)
x[9:18] = fit.x
report = N.metrics(x)
print('SURFACE FIT',report,'cost',fit.cost,flush=True)
assert report['min_skin_mm'] >= 1 and report['wrist_deg'] <= 35, report
assert all(1 <= d <= 3 for d in report['contacts_mm'].values()),report
assert all(report['tips'][d][1] < -3.55 for d in N.DIG),report
local = N.pose(x)
assert all(N.H.curl_motion(local,d,j)>0 for d in N.DIG+('thumb',) for j in (2,3))
backup = path.with_name('phone_native_fit_before_surface.json')
if not backup.exists():
    backup.write_text(json.dumps(before,indent=2))
path.write_text(json.dumps(dict(x=x.tolist(),metrics=report,cost=float(fit.cost),local=local),indent=2))
