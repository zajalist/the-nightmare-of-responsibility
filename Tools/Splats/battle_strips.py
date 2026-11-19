"""Per-event strips for the battle-sand proof (world lane): each [battlesand] transition from a PIE burst, with the
frames taken from just before it to 1.2 s after, one row per event.
  python Tools/Splats/battle_strips.py Saved/WorldShots/battle/<run>   (reads <run>_transitions.txt, <run>_frames/)
  -> <run>_strips.png, and a table of events (time, kind, frames found) on stdout
Log stamps are UTC ([2026.11.10-22.03.36:141]); frame times are file mtimes (epoch), so both meet as epoch seconds."""
import calendar
import glob
import os
import re
import sys

from PIL import Image, ImageDraw

run = sys.argv[1]
STAMP = re.compile(r'^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]')
KINDS = ('rise', 'garment', 'hit', 'equipped', 'won', 'state', 'shed')


def events():
    out = []
    for line in open(f'{run}_transitions.txt', encoding='utf-8', errors='replace'):
        m = STAMP.match(line)
        if not m:
            continue
        y, mo, d, h, mi, s, ms = (int(x) for x in m.groups())
        t = calendar.timegm((y, mo, d, h, mi, s)) + ms / 1000.0
        msg = line.split('[battlesand]', 1)[1].strip()
        msg = msg.split(' ', 1)[1] if ' ' in msg else msg       # drop the game-time stamp
        kind = msg.split(' ', 1)[0]
        if kind in ('shed', 'state'):                            # bookkeeping, not an on-screen event of its own
            continue
        if kind == 'garment' and not msg.endswith(('Telegraph', 'Stunned', 'Defeated', 'Attack')):
            continue
        out.append((t, kind, msg))
    return out


frames = sorted((os.path.getmtime(f), f) for f in glob.glob(f'{run}_frames/*.png'))
ev = events()
W, H, N = 384, 216, 6
rows = []
for t, kind, msg in ev:
    near = [f for ft, f in frames if t - 0.25 <= ft <= t + 1.25][:N]
    print(f'{t:.2f} {kind:9s} frames {len(near)}  {msg}')
    if near:
        rows.append((msg, near))
if not rows:
    sys.exit('no event has frames')
sheet = Image.new('RGB', (W * N, (H + 24) * len(rows)), (0, 0, 0))
dr = ImageDraw.Draw(sheet)
for r, (msg, fs) in enumerate(rows):
    dr.text((6, r * (H + 24) + 4), msg[:120], fill=(255, 80, 80))
    for c, f in enumerate(fs):
        sheet.paste(Image.open(f).convert('RGB').resize((W, H)), (c * W, r * (H + 24) + 24))
sheet.save(f'{run}_strips.png')
print('strips', f'{run}_strips.png', len(rows), 'events')
