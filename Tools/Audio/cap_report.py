"""Counts audible copies per test window for pie_burst_cap.py (A preset 3D, B raw wave 3D, C preset 2D).
  python Tools/Audio/cap_report.py <name>   (reads Saved/HorrorShots/<name>_timeline.json and <name>_audio.jsonl)"""
import json
import sys

name = sys.argv[1]
D = 'P:/FoA/Saved/HorrorShots'
log = json.load(open(f'{D}/{name}_timeline.json'))
S = [json.loads(line) for line in open(f'{D}/{name}_audio.jsonl') if line.strip()]
for label in 'ABC':
    fires = [e['epoch'] for e in log if e['kind'] == 'fire' and e['label'] == label]
    if not fires:
        print(label, 'no fires')
        continue
    t0, t1 = fires[0], fires[-1] + 3.0
    peak, ids = 0, set()
    for s in S:
        if t0 <= s['epoch'] <= t1:
            live = [x for x in s['sounds'] if 'Sand_Burst' in x and not x.endswith('!')]
            peak = max(peak, len(live))
            ids.update(x.split('#')[1] for x in live)
    print(f'{label}: {len(fires)} fires in {fires[-1] - fires[0]:.2f} s -> max {peak} audible at once, {len(ids)} distinct instances seen')
