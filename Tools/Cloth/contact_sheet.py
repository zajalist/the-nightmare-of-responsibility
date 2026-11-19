"""Greyscale contact sheet of texture thumbnails (downloads are untrusted: run with python -I).
  python -I Tools/Cloth/contact_sheet.py <out.jpg> <img> [img ...]"""
import os
import sys
sys.path.append(os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"))  # PIL lives in the user site, which -I hides
from PIL import Image, ImageDraw  # noqa: E402

out, files = sys.argv[1], sys.argv[2:]
cols = 6
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 200, rows * 220), (30, 30, 30))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    x, y = (i % cols) * 200, (i // cols) * 220
    sheet.paste(Image.open(f).convert("L").convert("RGB").resize((200, 200)), (x, y))
    d.text((x + 4, y + 203), os.path.splitext(os.path.basename(f))[0], fill=(255, 255, 255))
sheet.save(out, quality=88)
print("wrote", out, len(files))
