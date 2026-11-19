"""Builds one before/after sheet per clip from the qa_hands_capture.py panels (plain Python + Pillow, no editor).
  python -I Tools/Unreal/player/compose_hands.py [PickUp_Table Interact Fixing_Kneeling]
-> P:/FoA/Saved/GraphShots/hands_UAL_<clip>_compare.png, 1600 px wide: columns before | after, rows
   three-quarter at contact-2f (the reach), three-quarter at contact, palm side at contact."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SRC = "P:/FoA/Saved/GraphShots/qa_hands"
DST = "P:/FoA/Saved/GraphShots"
ROWS = [("reach_3q", "3/4 view, 2 frames before contact"), ("contact_3q", "3/4 view, contact frame"),
        ("contact_palm", "palm side, contact frame")]
PW, PH, HEAD, LAB = 800, 500, 70, 34


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def sheet(clip):
    img = Image.new("RGB", (2 * PW, HEAD + len(ROWS) * (PH + LAB)), (24, 24, 24))
    d = ImageDraw.Draw(img)
    d.text((20, 18), f"UAL_{clip}: hands before / after the finger-chain fix", fill=(235, 235, 235), font=font(30))
    for col, (ver, title) in enumerate((("before", "BEFORE: metacarpals fed by finger chains"),
                                        ("after", "AFTER: metacarpals unmapped, phalanges one-to-one"))):
        for row, (key, label) in enumerate(ROWS):
            y = HEAD + row * (PH + LAB)
            d.text((col * PW + 14, y + 6), f"{title} | {label}", fill=(200, 200, 200), font=font(18))
            path = f"{SRC}/{clip}_{ver}_{key}.png"
            if os.path.exists(path):
                img.paste(Image.open(path).convert("RGB").resize((PW, PH)), (col * PW, y + LAB))
            else:
                d.text((col * PW + 30, y + LAB + 30), f"missing {os.path.basename(path)}", fill=(255, 90, 90), font=font(20))
    out = f"{DST}/hands_UAL_{clip}_compare.png"
    img.save(out)
    print(out)


for c in sys.argv[1:] or ["PickUp_Table", "Interact", "Fixing_Kneeling"]:
    sheet(c)
