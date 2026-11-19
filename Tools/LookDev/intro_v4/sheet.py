"""Contact sheets of an IN1 run (intro lane): python Tools/LookDev/intro_v4/sheet.py <run>/IN1 <out.jpg> [stride] [panel]
Tiles are labelled with the panel and its clock from play.json's 'intro' log lines."""
import json
import os
import sys

import cv2
import numpy as np

run, out = sys.argv[1], sys.argv[2]
stride = int(sys.argv[3]) if len(sys.argv) > 3 else 4
only = int(sys.argv[4]) if len(sys.argv) > 4 else None
rows = [e for e in json.load(open(f'{run}/play.json'))['log'] if e.get('kind') == 'intro' and e.get('frame')]
rows = [e for e in rows if only is None or e['i'] == only][::stride]
tiles = []
for e in rows:
    im = cv2.imread(e['frame'])
    if im is None:
        continue
    im = cv2.resize(im[34:-2, 2:-2] if im.shape[0] == 760 else im, (480, 270))
    ln = e.get('line') or {}
    cv2.putText(im, f"p{e['i']} {e['pt']:.2f}s T{ln.get('T', 0):.2f}{' out' if ln.get('leaving') else ''}", (6, 18), 0, 0.5, (0, 255, 255), 1)
    tiles.append(im)
while len(tiles) % 6:
    tiles.append(np.zeros((270, 480, 3), np.uint8))
cv2.imwrite(out, np.vstack([np.hstack(tiles[i:i + 6]) for i in range(0, len(tiles), 6)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(out, len(rows))
