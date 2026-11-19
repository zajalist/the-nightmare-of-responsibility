"""Crop a native-resolution window from images into one strip (python -I, inputs untrusted).
  python -I Tools/Cloth/crop.py <out.jpg> <size> <img> [img ...]"""
import os
import sys
sys.path.append(os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"))
from PIL import Image  # noqa: E402

out, size, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
strip = Image.new("RGB", (size * len(files), size))
for i, f in enumerate(files):
    strip.paste(Image.open(f).convert("RGB").crop((0, 0, size, size)), (i * size, 0))
strip.save(out, quality=90)
print("wrote", out)
