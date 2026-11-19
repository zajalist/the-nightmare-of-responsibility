"""Frame-by-frame review grids: every STEP-th frame of a folder as 192x108 thumbs, 10 per row, captioned with seconds.
  python Tools/Unreal/cine/frame_grid.py <MRQ frames dir> <fps> <step> <t0> <t1> <out.png>   (offline)"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

src, fps, step, t0, t1, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
frames = sorted(glob.glob(os.path.join(src, "LS_WakeUp.*.png")))
pick = [f for f in frames if t0 <= int(f.split(".")[-2]) / fps <= t1][::step]
W, H, C, COLS = 192, 108, 16, 10
rows = (len(pick) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * W, rows * (H + C)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 12)
for i, f in enumerate(pick):
    x, y = (i % COLS) * W, (i // COLS) * (H + C)
    sheet.paste(Image.open(f).convert("RGB").resize((W, H)), (x, y))
    d.text((x + 3, y + H), "%.2f s" % (int(f.split(".")[-2]) / fps), font=font, fill=(200, 200, 200))
sheet.save(out)
print("wrote", out, len(pick))
