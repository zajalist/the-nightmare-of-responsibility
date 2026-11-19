"""Rows of take strips from garment_anims.py renders: python Tools/Rig/garment_sheet.py <garment> <out.jpg>"""
import sys
from PIL import Image, ImageDraw, ImageFont
G, OUT = sys.argv[1], sys.argv[2]
D = "P:/FoA-Assets/character/garments/rig/anim/strips"
TAKES = ["Idle", "Telegraph", {"Shirt": "Lash", "Trousers": "Kick", "Sock": "Hop", "Tie": "CoilStrike"}[G], "HitReact", "Stun", "Defeat"]
T, LW = 200, 120
f = ImageFont.load_default(size=16)
S = Image.new("RGB", (LW + 6 * T, len(TAKES) * T), (18, 18, 20))
g = ImageDraw.Draw(S)
for r, take in enumerate(TAKES):
    g.text((8, r * T + T // 2 - 8), take, fill=(235, 235, 235), font=f)
    for k in range(6):
        S.paste(Image.open(f"{D}/{G}_{take}_{k}.png").convert("RGB").resize((T, T)), (LW + k * T, r * T))
S.save(OUT, quality=88)
print("sheet", OUT)
