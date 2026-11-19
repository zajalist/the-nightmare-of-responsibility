"""Focus-visibility sheet for an input sweep: for every input in keys.json, the frame just before it and the frame
0.4 s after, side by side, labelled with the input, the widget that has focus after it and whether UI handled it.
Read it frame by frame: after every move, the focused element must be unmistakable (brightness, vortex, value).
  python Tools/Unreal/ui/focus_sheet.py <sweep dir>   -> <sweep dir>/focus_sheet.png"""
import bisect
import json
import os
import sys

from PIL import Image, ImageDraw

d = sys.argv[1]
keys = json.load(open(os.path.join(d, 'keys.json')))['keys']
shots = json.load(open(os.path.join(d, 'shots.json')))
t0, req = shots['t0'], shots['requests']  # requests: PIE time of each kept frame
# wall seconds since t0 -> PIE time: the recorder logged both per request; take the median offset
pairs = sorted(g - w for g, w in zip(shots.get('game_t', []), shots.get('req_wall', [])) if g is not None and w is not None)
off = pairs[len(pairs) // 2] if pairs else 0.0
frames = sorted(f for f in os.listdir(os.path.join(d, 'frames')) if f.endswith('.png'))
frames = [f for f in frames if int(f[1:5]) - 1 < len(req) and req[int(f[1:5]) - 1] is not None]
times = [t0 + req[int(f[1:5]) - 1] - off for f in frames]  # back to wall epoch, comparable with keys' epoch
tw, th = 480, 270
sheet = Image.new('RGB', (tw * 2, len(keys) * (th + 18)), 'black')
dr = ImageDraw.Draw(sheet)
for i, k in enumerate(keys):
    y = i * (th + 18)
    for j, at in enumerate((k['epoch'] - 0.05, k['epoch'] + 0.4)):
        n = min(max(bisect.bisect_left(times, at), 0), len(frames) - 1)
        sheet.paste(Image.open(os.path.join(d, 'frames', frames[n])).convert('RGB').resize((tw, th)), (j * tw, y + 18))
    dr.text((4, y + 2), f"{k['t']:5.2f}s  {k['key']}  focus after: {k.get('focused')}  handled: {k.get('handled_by_ui')}"
            f"  {'ERR ' + k['err'] if k.get('err') else ''}", fill=(255, 90, 90))
out = os.path.join(d, 'focus_sheet.png')
sheet.save(out)
print(out, len(keys), 'inputs')
