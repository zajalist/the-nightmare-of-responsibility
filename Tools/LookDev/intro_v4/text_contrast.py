"""Line contrast over the plates in an IN1 run (intro lane): for every frame whose line has fully formed and is not
leaving, the WCAG ratio between the glyphs (the brightest 0.7 % of the line's box) and what is behind them (the
median of the box's darker 85 %). The box is the line's slot: x 8 to 92 %, y 82.6 to 92.8 % of the game view.
  python Tools/LookDev/intro_v4/text_contrast.py <run>/IN1     -> per panel min and median ratio
Self-check: a synthetic white-on-black box must read above 15:1, grey-on-grey near 1:1."""
import json
import sys

import cv2
import numpy as np


def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def ratio(box):
    y = lin(cv2.cvtColor(box, cv2.COLOR_BGR2GRAY).astype(np.float32)).ravel()
    hi = np.percentile(y, 99.3)  # glyph cores; a short line covers under 3 % of the box
    fg = y[y >= hi].mean()
    bg = np.median(y[y <= np.percentile(y, 85)])
    return (fg + 0.05) / (bg + 0.05)


test = np.zeros((40, 400, 3), np.uint8)
test[15:25, 50:350:3] = 255
assert ratio(test) > 15, ratio(test)
assert ratio(np.full((40, 400, 3), 128, np.uint8)) < 1.2

run = sys.argv[1]
rows = [e for e in json.load(open(f'{run}/play.json'))['log'] if e.get('kind') == 'intro' and e.get('line')]
out = {}
for e in rows:
    ln = e['line']
    if ln['T'] < 1.0 or ln['leaving'] or 'COLLAPSED' in str(ln['vis']):
        continue
    im = cv2.imread(e['frame'])
    if im is None:
        continue
    im = im[36:756, 2:1282] if im.shape[0] >= 756 else im
    h, w = im.shape[:2]
    out.setdefault(e['i'], []).append(ratio(im[int(0.826 * h):int(0.928 * h), int(0.08 * w):int(0.92 * w)]))
for i, v in sorted(out.items()):
    print(f'panel {i}: frames {len(v)}, min {min(v):.1f}:1, median {np.median(v):.1f}:1')
