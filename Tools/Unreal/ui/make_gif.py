"""GIF of a frame range from a sweep, at the recorder's real frame timing (from shots.json), 640 px wide.
  python Tools/Unreal/ui/make_gif.py <sweep dir> <out.gif> <first>-<last> [crop x0,y0,x1,y1]"""
import json
import os
import sys

from PIL import Image

d, out, rng = sys.argv[1], sys.argv[2], sys.argv[3]
a, b = (int(v) for v in rng.split('-'))
req = json.load(open(os.path.join(d, 'shots.json')))['requests']
crop = tuple(int(v) for v in sys.argv[4].split(',')) if len(sys.argv) > 4 else None
ims, durs = [], []
for f in range(a, b + 1):
    p = os.path.join(d, 'frames', f'f{f:04d}.png')
    if not os.path.exists(p):
        continue
    im = Image.open(p).convert('RGB')
    if crop:
        im = im.crop(crop)
    w = 640 if im.width > 640 else im.width
    ims.append(im.resize((w, round(im.height * w / im.width))).quantize(colors=128))
    nxt = req[f] if f < len(req) and req[f] is not None else None
    cur = req[f - 1] if f - 1 < len(req) and req[f - 1] is not None else None
    durs.append(int(1000 * (nxt - cur)) if nxt is not None and cur is not None and 0 < nxt - cur < 1 else 42)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=durs, loop=0, optimize=True)
print(out, len(ims), 'frames', round(sum(durs) / 1000, 2), 's')
