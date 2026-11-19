"""Review sheet for a grip: tiles with captions under one title line.
  python Tools/Rig/grip_sheet.py <out.jpg> "<title>" "<caption>=<image.png>" ... [cols=3] [tile=420]"""
import sys

from PIL import Image, ImageDraw, ImageFont

out, title = sys.argv[1], sys.argv[2]
opt = dict(a.split("=", 1) for a in sys.argv[3:] if a.split("=", 1)[0] in ("cols", "tile"))
tiles = [a.split("=", 1) for a in sys.argv[3:] if a.split("=", 1)[0] not in ("cols", "tile")]
cols, tw = int(opt.get("cols", 3)), int(opt.get("tile", 420))
th, cap, head = tw * 9 // 16, 26, 34
rows = (len(tiles) + cols - 1) // cols
font = ImageFont.load_default(size=17)
W = Image.new("RGB", (cols * tw, head + rows * (th + cap)), (18, 18, 20))
g = ImageDraw.Draw(W)
g.text((8, 8), title, fill=(235, 235, 235), font=font)
for k, (c, path) in enumerate(tiles):
    x, y = (k % cols) * tw, head + (k // cols) * (th + cap)
    im = Image.open(path).convert("RGB")
    im.thumbnail((tw - 4, th - 4))
    W.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
    g.text((x + 6, y + th + 3), c, fill=(210, 210, 210), font=font)
W.save(out, quality=90)
print("wrote", out)
