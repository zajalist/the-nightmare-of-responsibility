"""Pick rested title and menu frames from a 'fast' sweep and run QA checks (a)/(b) on them.
title = the frame 0.2 s before the title-confirm SpaceBar; menu = the frame 0.3 s before the first Down.
  python Tools/Unreal/ui/qa_frames.py <sweep dir>   -> <sweep dir>/qa/{title,menu}_<run>.png, then foa_qa checks"""
import bisect
import json
import os
import shutil
import subprocess
import sys

d = sys.argv[1]
run = os.path.basename(d.rstrip('/\\'))
keys = json.load(open(os.path.join(d, 'keys.json')))['keys']
shots = json.load(open(os.path.join(d, 'shots.json')))
t0, req = shots['t0'], shots['requests']
pairs = sorted(g - w for g, w in zip(shots.get('game_t', []), shots.get('req_wall', [])) if g is not None and w is not None)
off = pairs[len(pairs) // 2] if pairs else 0.0
frames = sorted(f for f in os.listdir(os.path.join(d, 'frames')) if f.endswith('.png'))
frames = [f for f in frames if int(f[1:5]) - 1 < len(req) and req[int(f[1:5]) - 1] is not None]
times = [t0 + req[int(f[1:5]) - 1] - off for f in frames]


def at(epoch):
    return frames[min(max(bisect.bisect_left(times, epoch) - 1, 0), len(frames) - 1)]


space = next(k for k in keys if k['key'] == 'SpaceBar')
down = next(k for k in keys if k['key'] == 'Down')
q = os.path.join(d, 'qa')
os.makedirs(q, exist_ok=True)
for name, ep in (('title', space['epoch'] - 0.2), ('menu', down['epoch'] - 0.3)):
    src = at(ep)
    shutil.copy(os.path.join(d, 'frames', src), os.path.join(q, f'{name}_{run}.png'))
    print(name, src)
r = subprocess.run([sys.executable, 'P:/FoA/Tools/QA/foa_qa.py', 'checks', q], capture_output=True, text=True)
print('\n'.join(l for l in r.stdout.splitlines() if 'PASS' in l or 'FAIL' in l))
