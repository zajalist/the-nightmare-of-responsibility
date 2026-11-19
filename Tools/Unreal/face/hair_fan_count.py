"""Hair-fan counter (offline, numpy + PIL) for a pie_face_shots.py 'hair' run: for each variant, the head-area pixels
at least 60 levels brighter with the phone light on than off, plus the p99 brightness with it on and his face's mean brightness on/off.
  python Tools/Unreal/face/hair_fan_count.py <run>     (Saved/FaceShots/<run>/hair_<variant>_{on,off}.png + shots.json)
Valid only when the base and base2 controls match (same phone pose throughout)."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

d = Path('P:/FoA/Saved/FaceShots') / sys.argv[1]
sh = {s['label']: s for s in json.loads((d / 'shots.json').read_text())['shots']}
names = [l[5:-3] for l in sh if l.startswith('hair_') and l.endswith('_on')]
x, y, r = sh[f'hair_{names[0]}_on']['head_px']
for v in names:
    on = np.asarray(Image.open(d / f'hair_{v}_on.png').convert('L'), dtype=float)
    off = np.asarray(Image.open(d / f'hair_{v}_off.png').convert('L'), dtype=float)
    yy, xx = np.mgrid[:on.shape[0], :on.shape[1]]
    disc = np.hypot(xx - x, yy - y) < r
    face = disc & (yy > y)  # lower half of the head disc: his face, which the phone should still light
    print(f'{v:16s} fan px {int(((on - off)[disc] > 60).sum()):7d}   p99 on {np.percentile(on[disc], 99):5.0f}'
          f'   face mean on {on[face].mean():5.1f} off {off[face].mean():5.1f}')
