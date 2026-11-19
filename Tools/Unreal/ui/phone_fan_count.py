"""Face's hair-fan metric (Tools/Unreal/face/hair_fan_count.py) on a UI phone-light sweep: in the disc around his head,
the pixels at least 60 levels brighter with the light on than with it hidden, plus the p99 brightness with it on.
Baseline: face's base, 25,295 px, p99 229 (shipping light at the screen). Target: near 0 px, p99 well under 229.
  python Tools/Unreal/ui/phone_fan_count.py <start marker file>
Pairs pie_call's stills.jsonl rows (one per still, in order) with the ScreenShot files written after the marker."""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

mark = os.path.getmtime(sys.argv[1])
shots = sorted((p for p in Path('P:/FoA/Saved/Screenshots/WindowsEditor').glob('ScreenShot*.png') if p.stat().st_mtime > mark),
               key=lambda p: p.stat().st_mtime)
rows = [r for r in map(json.loads, open('P:/FoA/Saved/UIShots/aaa/stills.jsonl', encoding='utf-8')) if r['t'] > mark]
assert len(rows) == len(shots), (len(rows), len(shots))
pairs = list(zip(rows, shots))
off = next(p for r, p in pairs if r['call'] == 'PHONELIGHT' and r['cmd'] == 'hide')
o = np.asarray(Image.open(off).convert('L'), dtype=float)
yy, xx = np.mgrid[:o.shape[0], :o.shape[1]]
first = next(p for r, p in pairs if r['call'] == 'PHONELIGHT' and r['cmd'].startswith('v:'))
lit = (np.asarray(Image.open(first).convert('L'), dtype=float) - o) > 20  # where the shipping light reaches him
x, y = xx[lit].mean(), yy[lit].mean()
rad = 2.0 * np.sqrt(lit.sum() / np.pi)
disc = np.hypot(xx - x, yy - y) < rad  # shortcut: the disc is derived from the first variant's lit area, not the head socket
print('light hidden:', off.name, 'disc', int(x), int(y), int(rad), 'of', o.shape[::-1])
for r, p in pairs:
    if r['call'] == 'PHONELIGHT' and r['cmd'].startswith('v:'):
        on = np.asarray(Image.open(p).convert('L'), dtype=float)
        print(f"{r['cmd'][2:]:28s} {p.name}  fan px {int(((on - o)[disc] > 60).sum()):6d}   p99 on {np.percentile(on[disc], 99):5.0f}"
              f"   face mean +{(on - o)[disc].mean():5.1f}")
