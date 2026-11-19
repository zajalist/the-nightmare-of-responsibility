"""atmosphere lane: a labelled contact sheet of PNG frames (game view cropped out of the PIE window).
  python Tools/Audio/sheet.py <out.png> <cols> <frame.png> [<frame.png> ...]"""
import os
import sys

from PIL import Image, ImageDraw

out, cols, paths = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
tw, th = 640, 360
rows = (len(paths) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 18)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, p in enumerate(paths):
    im = Image.open(p).convert('RGB')
    w, h = im.size
    if abs(w - 1286) <= 4 and h >= 723:  # the floating PIE window: drop its title bar and borders
        im = im.crop((3, h - 723, w - 3, h - 3))
    x, y = (i % cols) * tw, (i // cols) * (th + 18)
    sheet.paste(im.resize((tw, th)), (x, y + 18))
    d.text((x + 4, y + 3), os.path.basename(p)[:60], fill=(230, 230, 230))
sheet.save(out)
print(out, len(paths))
