"""Pick sheet for the MPFB teen directions: one row each, front, 3/4, full body, and the 3/4 in greyscale (the game is monochrome).
  python Tools/MPFB/direction_sheet.py              the A/B/C pick sheet (from build_directions.py stills)
  python Tools/MPFB/direction_sheet.py poses <tag>  one row of fit-proof poses (from pose_sheet.py stills)"""
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

SHOTS = "P:/FoA/Saved/CharacterShots/mpfb"
FONT = "P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-Medium.ttf"
LABELS = {  # keep in step with DIRECTIONS in build_directions.py
    "A": "A   Soft and round, freckled, side-swept mop, grey-blue eyes, 1.67 m",
    "B": "B   Big and tall, broad square face, close dark crop, dark eyes, 1.91 m",
    "C": "C   Stocky and pear-shaped, tired heavy-lidded eyes behind glasses, 1.63 m",
}
W, H, HEAD, PAD = 450, 550, 54, 10
cols = ("front", "tq", "body", "tq_mono")
OUT = f"{SHOTS}/directions_sheet.png"
if sys.argv[1:2] == ["poses"]:  # fit proof: one row, the poses in order
    tag = sys.argv[2]
    LABELS = {tag: f"{tag}   Fit check on the game rig: idle, walk mid-stride, sitting, arms raised"}
    cols = ("pose_idle", "pose_walk", "pose_sit", "pose_raise")
    OUT = f"{SHOTS}/{tag}_pose_sheet.png"
font = ImageFont.truetype(FONT, 34)
sheet = Image.new("RGB", (len(cols) * (W + PAD) + PAD, len(LABELS) * (H + HEAD + PAD) + PAD), (18, 18, 20))
draw = ImageDraw.Draw(sheet)
for r, (key, label) in enumerate(LABELS.items()):
    y = PAD + r * (H + HEAD + PAD)
    draw.text((PAD + 4, y + 8), label, font=font, fill=(235, 235, 235))
    for c, col in enumerate(cols):
        im = Image.open(f"{SHOTS}/{key}_{col.replace('_mono', '')}.png").convert("RGB").resize((W, H))
        if col.endswith("_mono"):
            im = ImageOps.autocontrast(im.convert("L"), cutoff=1).convert("RGB")
        sheet.paste(im, (PAD + c * (W + PAD), y + HEAD))
sheet.save(OUT)
print("wrote", OUT)
