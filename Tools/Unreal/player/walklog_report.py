"""Where does the first-person eye bob come from? Reads review.json's per-tick walk log (pie_fp_review.py).
  python Tools/Unreal/player/walklog_report.py <review folder>
For each height (camera, Face head, Body head, Body pelvis, source Manny head) prints min, max and span while walking,
and the span of each relative to the pelvis, so animation bob, retarget/IK drops and Face drift separate cleanly."""
import json
import sys
from pathlib import Path

rows = json.loads((Path(sys.argv[1]) / 'review.json').read_text()).get('walklog', [])
walk = [r for r in rows if r.get('speed', 0) > 20]
print('ticks', len(rows), 'walking', len(walk))
if walk:
    for k in ('cam_z', 'face_head_z', 'body_head_z', 'pelvis_z', 'src_head_z'):
        v = [r[k] for r in walk]
        print('%-12s min %7.1f max %7.1f span %5.1f' % (k, min(v), max(v), max(v) - min(v)))
    for k in ('cam_z', 'body_head_z', 'src_head_z'):
        v = [r[k] - r['pelvis_z'] for r in walk]
        print('%-12s - pelvis  span %5.1f' % (k, max(v) - min(v)))
    print('first rows', walk[:3])
