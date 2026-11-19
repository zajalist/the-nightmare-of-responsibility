"""One captioned board from audit stills: python Tools/Rig/audit_board.py <out.jpg> <img>|<caption> ...  (2 columns)"""
import sys

from PIL import Image, ImageDraw, ImageFont

out, items = sys.argv[1], [a.split("|", 1) for a in sys.argv[2:]]
W, cap = 760, 92
font = ImageFont.load_default(size=17)
tiles = []
for path, text in items:
    im = Image.open(path).convert("RGB")
    im = im.resize((W, int(im.height * W / im.width)))
    tiles.append((im, text))
rows = [tiles[i:i + 2] for i in range(0, len(tiles), 2)]
H = sum(max(t[0].height for t in r) + cap for r in rows)
B = Image.new("RGB", (2 * W + 30, H + 20), (18, 18, 20))
g = ImageDraw.Draw(B)
y = 10
for r in rows:
    h = max(t[0].height for t in r)
    for j, (im, text) in enumerate(r):
        x = 10 + j * (W + 10)
        B.paste(im, (x, y))
        words, line, ly = text.split(), "", y + h + 6
        for w in words:  # wrap the caption
            if g.textlength(line + " " + w, font=font) > W - 10:
                g.text((x + 4, ly), line.strip(), fill=(235, 235, 235), font=font)
                line, ly = "", ly + 20
            line += " " + w
        g.text((x + 4, ly), line.strip(), fill=(235, 235, 235), font=font)
    y += h + cap
B.save(out, quality=88)
print("board", out, B.size)
