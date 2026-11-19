"""Contact sheet from rom_audit renders: one row per pose+shot, one column per subject.
  python Tools/Rig/sheet.py <dir> <out.jpg> [subjects=teen,manny] [match=substr] [tile=300]"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

d, out = sys.argv[1], sys.argv[2]
opt = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
subjects = opt.get("subjects", "teen,manny").split(",")
tile = int(opt.get("tile", 300))
match = opt.get("match", "")
rows = {}
for f in sorted(glob.glob(os.path.join(d, "*.png"))):
    stem = os.path.splitext(os.path.basename(f))[0]
    key, who = stem.rsplit("_", 1)
    if who in subjects and match in stem:
        rows.setdefault(key, {})[who] = f
font = ImageFont.load_default(size=16)
lab = 150
W = Image.new("RGB", (lab + tile * len(subjects), 24 + tile * len(rows)), (20, 20, 22))
g = ImageDraw.Draw(W)
for j, s in enumerate(subjects):
    g.text((lab + j * tile + 6, 4), s, fill=(230, 230, 230), font=font)
for i, (key, fs) in enumerate(rows.items()):
    y = 24 + i * tile
    g.text((6, y + tile // 2 - 10), key.replace("_", " "), fill=(230, 230, 230), font=font)
    for j, s in enumerate(subjects):
        if s in fs:
            W.paste(Image.open(fs[s]).convert("RGB").resize((tile, tile)), (lab + j * tile, y))
W.save(out, quality=88)
print("sheet", out, len(rows), "rows")
