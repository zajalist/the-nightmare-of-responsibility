"""The judged frames of a jumpscare burst: up to 18 frames from just before the hit to the cut, labelled in game ms.
  python Tools/Unreal/horror/hold_strip.py <name> [from_s=-0.12] [to_s=0.9]  ->  Saved/HorrorShots/<name>_hold_strip.png"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

name = sys.argv[1]
lo, hi = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (-0.12, 0.9)
D = 'P:/FoA/Saved/HorrorShots'
log = json.load(open(f'{D}/{name}_timeline.json'))
slo = next((e['epoch'] for e in log if e['kind'] == 'cmd' and e['cmd'].startswith('slomo 0')), None)
end = next((e['epoch'] for e in log if e['kind'] == 'cmd' and e['cmd'] == 'slomo 1'), float('inf'))


def g(t):
    return t if slo is None or t <= slo else slo + (min(t, end) - slo) * 0.25 + max(0.0, t - end)


hit = g(next(e['epoch'] for e in log if e['kind'] == 'phase' and e['phase'] == 3))
fs = sorted(glob.glob(f'{D}/{name}_frames/*.png'), key=os.path.getmtime)
win = [(f, g(os.path.getmtime(f)) - hit) for f in fs if lo <= g(os.path.getmtime(f)) - hit <= hi]
win = [win[round(i * (len(win) - 1) / 17)] for i in range(18)] if len(win) > 18 else win  # evenly over the whole span
# the designed timing (docs/design/horror/jumpscare.md): stinger file starts 0.40 s before the hit, cut at +0.65 s
MARKS = [(-0.40, 'stinger starts'), (0.0, 'HIT'), (0.65, 'cut')]
tw, th, cols = 420, 236, 6
rows = (len(win) + cols - 1) // cols
s = Image.new('RGB', (cols * tw, rows * (th + 16)), (10, 10, 10))
dr = ImageDraw.Draw(s)
for i, (f, t) in enumerate(win):
    x, y = (i % cols) * tw, (i // cols) * (th + 16)
    s.paste(Image.open(f).convert('RGB').resize((tw, th)), (x, y + 16))
    mark = next((m for at, m in MARKS if abs(t - at) == min(abs(u - at) for _, u in win)), '')
    dr.text((x + 4, y + 2), f'{t * 1000:+.0f} ms  {mark}', fill=(255, 220, 120) if mark else (255, 255, 255))
s.save(f'{D}/{name}_hold_strip.png')
print(len(win), f'{D}/{name}_hold_strip.png')
