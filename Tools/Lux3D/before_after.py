"""Side-by-side before/after sheet for the props art pass (devlog media):
  python Tools/Lux3D/before_after.py OUT.png BEFORE.png AFTER.png [BEFORE2.png AFTER2.png ...]
Each pair becomes one row, before on the left, after on the right, 640 px wide each."""
import sys

from PIL import Image

out, files = sys.argv[1], sys.argv[2:]
assert files and len(files) % 2 == 0, 'pairs of before/after images'
rows = []
for b, a in zip(files[::2], files[1::2]):
    ib, ia = (Image.open(p).convert('RGB') for p in (b, a))
    h = round(640 * ib.height / ib.width)
    rows.append((ib.resize((640, h)), ia.resize((640, round(640 * ia.height / ia.width)))))
H = sum(max(x.height, y.height) for x, y in rows)
sheet = Image.new('RGB', (1288, H + 8 * (len(rows) - 1)), (12, 12, 12))
y = 0
for b, a in rows:
    sheet.paste(b, (0, y))
    sheet.paste(a, (648, y))
    y += max(b.height, a.height) + 8
sheet.save(out)
print(out, sheet.size)
