"""Character luma per shot from PIE Shot pairs (world lane cine lighting proof).
  python Tools/Lux3D/char_luma.py <frames dir> <out.png> label,label,...
Frames come in pairs, oldest first: the shot as filmed, then the same frame with the player hidden (driver HIDE).
Where the pair differs (luma delta > 0.04) is the character; reports its mean luma, p99 and clipped share (> 0.95),
Rec.709 on the 8-bit frame like Tools/Unreal/face/skin_luma.py, and writes a sheet with the mask outlined in red."""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def luma(im):
    a = np.asarray(im, dtype=np.float32) / 255.0
    return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)


src, out = sys.argv[1], sys.argv[2]
labels = sys.argv[3].split(',') if len(sys.argv) > 3 else []
fs = sorted(glob.glob(os.path.join(src, '*.png')), key=os.path.getmtime)
assert fs and len(fs) % 2 == 0, f'{len(fs)} frames in {src}: expected filmed/hidden pairs'
W, H, COLS = 640, 360, 4
n = len(fs) // 2
sheet = Image.new('RGB', (W * COLS, H * ((n + COLS - 1) // COLS)))
rows = []
for i in range(n):
    a, b = Image.open(fs[2 * i]).convert('RGB'), Image.open(fs[2 * i + 1]).convert('RGB')
    ya, yb = luma(a), luma(b)
    m = np.abs(ya - yb) > 0.04
    v = ya[m]
    name = labels[i] if i < len(labels) else os.path.basename(fs[2 * i])
    r = dict(name=name, px=int(m.sum()), mean=float(v.mean()) if v.size else 0.0,
             p99=float(np.percentile(v, 99)) if v.size else 0.0, clip=float((v > 0.95).mean()) if v.size else 0.0)
    rows.append(r)
    tile = a.copy()
    edge = m & ~np.roll(m, 1, 0) | m & ~np.roll(m, 1, 1)
    arr = np.asarray(tile).copy()
    arr[edge] = (255, 0, 0)
    tile = Image.fromarray(arr).resize((W, H))
    ImageDraw.Draw(tile).text((6, 4), f"{name}  mean {r['mean']:.2f}  p99 {r['p99']:.2f}  clip {r['clip']:.0%}", fill=(255, 40, 40))
    sheet.paste(tile, ((i % COLS) * W, (i // COLS) * H))
    print(f"{name:16s} px {r['px']:7d}  mean {r['mean']:.3f}  p99 {r['p99']:.3f}  clip {r['clip']:.1%}")
sheet.save(out)
print('sheet ->', out)
