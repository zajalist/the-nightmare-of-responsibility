"""Frame-by-frame strip of a hand-off capture folder (pie_handoff_strip.py): every frame, in order, labelled with its
index, sequence time, view target, camera-to-head distance and whether the head parts render.
  python Tools/Unreal/player/handoff_sheet.py <folder>   -> <folder>/strip.jpg and a summary line per frame"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

folder = Path(sys.argv[1])
rows = [r for r in json.loads((folder / 'frames.json').read_text())['rows'] if 'i' in r and 'yaw_shot' not in r]
g0 = next((r['game_t'] for r in rows if r.get('done') and 'game_t' in r), None)  # game time of the hand-off
cols, w, h = 6, 400, 273
CROP = (7, 137, 1293, 1015)  # the PIE viewport inside the editor window that 'Shot showui' grabs
shots = [(r, folder / ('f%03d.png' % r['i'])) for r in rows]
shots = [(r, f) for r, f in shots if f.exists()]
missing = [r['i'] for r in rows if not (folder / ('f%03d.png' % r['i'])).exists()]
sheet = Image.new('RGB', (cols * w, ((len(shots) + cols - 1) // cols) * (h + 30)), (20, 20, 20))
for k, (r, f) in enumerate(shots):
    im = Image.open(f).convert('RGB').crop(CROP).resize((w, h))
    x, y = (k % cols) * w, (k // cols) * (h + 30)
    sheet.paste(im, (x, y))
    head = 'head ON' if r.get('Face') is True else 'head hidden'
    luma = sum(Image.open(f).convert('L').crop(CROP).resize((64, 44)).getdata()) / (64 * 44)
    dt = '' if g0 is None or 'game_t' not in r else ' g%+.3fs' % (r['game_t'] - g0)
    label = 'f%03d seq %s%s %s %s luma %.0f' % (r['i'], r.get('seq'), dt, 'DONE' if r.get('done') else 'cine', head, luma)
    ImageDraw.Draw(sheet).text((x + 4, y + h + 6), label, fill=(255, 220, 120))
    print(label, r.get('view'))
sheet.save(folder / 'strip.jpg', quality=88)
print('strip', folder / 'strip.jpg', len(shots), 'frames; rows without an image:', missing)
