"""Monochrome side-by-side sheet with plain captions under each panel (the game grade removes colour).
  python -I Tools/Cloth/compose.py <out.png> <panel_height> <img>=<caption> [...]"""
import os
import sys
sys.path.append(os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

out, h = sys.argv[1], int(sys.argv[2])
items = [a.split("=", 1) for a in sys.argv[3:]]
ims = [Image.open(p).convert("L") for p, _ in items]
ims = [im.resize((round(im.width * h / im.height), h)) for im in ims]
try:
    font = ImageFont.truetype("arial.ttf", 22)
except OSError:
    font = ImageFont.load_default()
sheet = Image.new("L", (sum(i.width for i in ims), h + 40), 16)
d = ImageDraw.Draw(sheet)
x = 0
for im, (_, cap) in zip(ims, items):
    sheet.paste(im, (x, 0))
    d.text((x + 10, h + 8), cap, fill=225, font=font)
    x += im.width
sheet.save(out)
print("wrote", out)
