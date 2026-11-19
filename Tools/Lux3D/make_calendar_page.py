"""The wall calendar's page as a texture, so the count is exact: days 1-17 crossed out in pen, the 18th (today) left
open with a light pen ring. The script's line is "Seventeen days. Not that anyone's counting." Lux3D's own page
(task 5308486) scattered its crosses over an atlas, so the count can't be fixed there; this page lies over its front.
  python Tools/Lux3D/make_calendar_page.py  ->  P:/FoA-Assets/lux3d/wall_calendar/T_Lux3D_WallCalendar_Page.png
Font: Cormorant Garamond (OFL, P:/FoA-Assets/fonts). Monochrome game: dark ink on aged paper, no colour needed."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024
OUT = 'P:/FoA-Assets/lux3d/wall_calendar/T_Lux3D_WallCalendar_Page.png'
F = 'P:/FoA-Assets/fonts/CormorantGaramond/CormorantGaramond-'
rnd = random.Random(17)
img = Image.new('RGB', (W, H), (226, 220, 204))
d = ImageDraw.Draw(img)
for _ in range(1400):   # paper tooth: fine flecks
    x, y, r = rnd.randrange(W), rnd.randrange(H), rnd.choice((1, 1, 2))
    c = rnd.randrange(170, 215)
    d.ellipse((x - r, y - r, x + r, y + r), fill=(c, c - 4, c - 14))
stain = Image.new('L', (W, H), 0)
sd = ImageDraw.Draw(stain)
for _ in range(14):    # a few soft age stains, blurred so they never read as dots
    x, y, r = rnd.randrange(W), rnd.randrange(H), rnd.randrange(40, 140)
    sd.ellipse((x - r, y - r, x + r, y + r), fill=rnd.randrange(10, 26))
stain = stain.filter(ImageFilter.GaussianBlur(40))
img = Image.composite(Image.new('RGB', (W, H), (176, 160, 130)), img, stain)
img = img.filter(ImageFilter.GaussianBlur(0.8))
d = ImageDraw.Draw(img)
ink = (34, 30, 28)
d.text((W // 2, 92), 'OCTOBER', font=ImageFont.truetype(F + 'Bold.ttf', 112), fill=ink, anchor='mm')
top, left, cw, ch = 210, 52, (W - 104) // 7, (H - 210 - 48) // 5
for i, wd in enumerate('MTWTFSS'):
    d.text((left + cw * i + cw // 2, top - 26), wd, font=ImageFont.truetype(F + 'SemiBold.ttf', 34), fill=ink, anchor='mm')
for r in range(6):
    d.line((left, top + ch * r, left + cw * 7, top + ch * r), fill=(70, 64, 58), width=3)
for c in range(8):
    d.line((left + cw * c, top, left + cw * c, top + ch * 5), fill=(70, 64, 58), width=3)
num = ImageFont.truetype(F + 'Medium.ttf', 40)
first = 2   # the 1st falls on a Wednesday
pen = (16, 14, 14)
for day in range(1, 32):
    k = first + day - 1
    col, row = k % 7, k // 7
    if row > 4:   # the 31st shares the last row's cell in a 5-row grid
        row, col = 4, col
    x0, y0 = left + cw * col, top + ch * row
    d.text((x0 + cw - 12, y0 + 10), str(day), font=num, fill=ink, anchor='ra')
    if day <= 17:   # crossed out, each stroke a little different
        j = lambda: rnd.uniform(-7, 7)
        for (ax, ay, bx, by) in ((14, 46, cw - 14, ch - 12), (cw - 14, 46, 14, ch - 12)):
            d.line((x0 + ax + j(), y0 + ay + j(), x0 + bx + j(), y0 + by + j()), fill=pen, width=rnd.choice((9, 10, 11)))
    elif day == 18:   # today: a loose pen ring, not crossed
        cx, cy, rr = x0 + cw / 2, y0 + ch / 2 + 8, min(cw, ch) * 0.38
        pts = [(cx + rr * math.cos(t / 20 * 2 * math.pi) * (1 + rnd.uniform(-0.04, 0.04)),
                cy + rr * 0.86 * math.sin(t / 20 * 2 * math.pi) * (1 + rnd.uniform(-0.04, 0.04))) for t in range(22)]
        d.line(pts, fill=pen, width=6, joint='curve')
img.save(OUT)
print('page ->', OUT, 'crossed 1-17, ring on 18')
