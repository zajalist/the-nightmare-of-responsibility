"""Check captured planted feet during the first straight, steady walk; no editor calls."""
import json
import math
import statistics
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv)>1 else 'P:/FoA/Saved/AnimShots/loco_feet_latest.json')
rows = [r for r in json.loads(path.read_text()) if r['phase']=='loco' and r['seg']==0]
assert rows, 'No straight-walk samples'
result = {}
for bone in ('ball_l','ball_r'):
    speeds = []
    for a,b in zip(rows,rows[1:]):
        dt=b['t']-a['t']
        p,q=a['Body'][bone],b['Body'][bone]
        if .005<dt<.1 and math.hypot(*a['velocity'][:2])>125 and a['t']-rows[0]['t']>1 and max(p[2],q[2])<5:
            speeds.append(math.hypot(q[0]-p[0],q[1]-p[1])/dt)
    assert len(speeds)>=20, (bone,'Insufficient planted-foot samples',len(speeds))
    result[bone]=dict(samples=len(speeds),median_cm_s=statistics.median(speeds))
print(json.dumps(result,indent=2))
assert all(r['median_cm_s']<8 for r in result.values()), 'Planted feet visibly slide during steady walking'
