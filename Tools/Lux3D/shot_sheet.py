"""Contact sheet + luma stats for a set of PIE Shot frames (world lane lighting proof).
  python Tools/Lux3D/shot_sheet.py <frames dir> <out.png> [label,label,...]
Luma is Rec.709 on the sRGB frame (what the player sees). 'crushed' = share of pixels below 0.04 (reads as black),
'readable' = share between 0.08 and 0.9. Prints one row per frame and the mean; writes a 4-column sheet."""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
labels = sys.argv[3].split(',') if len(sys.argv) > 3 else []
fs = sorted(glob.glob(os.path.join(src, '*.png')), key=os.path.getmtime)
assert fs, f'no frames in {src}'
W, H, COLS = 640, 360, 4
rows = (len(fs) + COLS - 1) // COLS
sheet = Image.new('RGB', (W * COLS, H * rows))
stats = []
for i, f in enumerate(fs):
    im = Image.open(f).convert('RGB')
    a = np.asarray(im, dtype=np.float32) / 255.0
    y = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    s = dict(name=labels[i] if i < len(labels) else os.path.basename(f), mean=y.mean(), p10=np.percentile(y, 10),
             p50=np.percentile(y, 50), p90=np.percentile(y, 90), crushed=(y < 0.04).mean(), readable=((y > 0.08) & (y < 0.9)).mean())
    stats.append(s)
    t = im.resize((W, H))
    d = ImageDraw.Draw(t)
    d.rectangle((0, 0, W, 22), fill=(0, 0, 0))
    d.text((6, 4), f"{s['name']}  mean {s['mean']:.3f}  crushed {s['crushed']:.0%}", fill=(255, 255, 255))
    sheet.paste(t, ((i % COLS) * W, (i // COLS) * H))
sheet.save(out)
print(f"{'frame':16s} {'mean':>6s} {'p10':>6s} {'p50':>6s} {'p90':>6s} {'crushed':>8s} {'readable':>9s}")
for s in stats:
    print(f"{s['name']:16s} {s['mean']:6.3f} {s['p10']:6.3f} {s['p50']:6.3f} {s['p90']:6.3f} {s['crushed']:8.1%} {s['readable']:9.1%}")
m = {k: np.mean([s[k] for s in stats]) for k in ('mean', 'p10', 'p50', 'p90', 'crushed', 'readable')}
print(f"{'MEAN':16s} {m['mean']:6.3f} {m['p10']:6.3f} {m['p50']:6.3f} {m['p90']:6.3f} {m['crushed']:8.1%} {m['readable']:9.1%}")
print('sheet ->', out)
