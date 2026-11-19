"""Door-tool lane: a labelled contact sheet of chosen QA frames.
  python Tools/Unreal/doortool/sheet.py OUT.jpg COLS frame1.png frame2.png ...   (globs allowed)"""
import glob
import os
import sys

from PIL import Image, ImageDraw

out, cols = sys.argv[1], int(sys.argv[2])
files = [f for a in sys.argv[3:] for f in (sorted(glob.glob(a)) or [a])]
assert files, 'no frames'
w = 640
tiles = []
for f in files:
    im = Image.open(f).convert('RGB')
    im = im.resize((w, int(im.height * w / im.width)))
    ImageDraw.Draw(im).text((8, 30), os.path.basename(f), fill=(255, 255, 0))
    tiles.append(im)
h = max(t.height for t in tiles)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w, rows * h))
for k, t in enumerate(tiles):
    sheet.paste(t, ((k % cols) * w, (k // cols) * h))
sheet.save(out, quality=90)
print(out, len(tiles))
