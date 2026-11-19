"""Contact sheet of the six teen face directions: one row per face (studio front, studio 3/4, in the room), labelled.

  python Tools/faces_sheet.py [P:/FoA/Saved/CharacterShots/faces] [studio|room|all] [ABCDEF|GHIJKL]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1] if len(sys.argv) > 1 else "P:/FoA/Saved/CharacterShots/faces"
LABELS = {
    "A": "A   East Asian, angular cheekbones, side-swept fringe, clean shave",
    "B": "B   Black, long face, high cheekbones, short twists, clean shave",
    "C": "C   South Asian, soft oval face, strong nose, short side-swept fringe, clean shave",
    "D": "D   Northern European, square jaw, heavy brow, messy crop, clean shave",
    "E": "E   Mediterranean, long nose, narrow face, messy swept-up hair, clean shave",
    "F": "F   Mixed Black and Polynesian, broad face, curly fade, clean shave",
}
LABELS.update({  # round 2: heavier, softer teens
    "G": "G   Irish, fair and freckled, ginger curly mop, pale eyes",
    "H": "H   East Asian, bleached two-tone hair with dark roots, slit brow, flushed skin",
    "I": "I   Black, heterochromia (one pale eye), shaved-side cut, uneven skin tone",
    "J": "J   South Asian, overgrown fringe, acne, one ear sticking out",
    "K": "K   Latino, bowl cut, wide brows, amber eyes, round soft face",
    "L": "L   Polynesian, long hair in a messy bun, broad face, freckled brown skin, light hazel eyes",
})
CELL, PAD, HEAD = 420, 12, 34
MODE = sys.argv[2] if len(sys.argv) > 2 else "all"
cols = {"studio": ("front", "tq"), "room": ("room",), "all": ("front", "tq", "room")}[MODE]
LETTERS = sys.argv[3] if len(sys.argv) > 3 else "ABCDEF"
faces = [f for f in LETTERS if os.path.exists(os.path.join(ROOT, f, "front.png"))]
W = PAD + len(cols) * (CELL + PAD)
H = PAD + len(faces) * (HEAD + CELL + PAD)
sheet = Image.new("RGB", (W, H), (18, 18, 18))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
except OSError:
    font = ImageFont.load_default()
for r, f in enumerate(faces):
    y = PAD + r * (HEAD + CELL + PAD)
    d.text((PAD, y + 4), LABELS.get(f, f), fill=(235, 235, 235), font=font)
    for c, name in enumerate(cols):
        p = os.path.join(ROOT, f, name + ".png")
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((CELL, CELL), Image.LANCZOS)
            sheet.paste(im, (PAD + c * (CELL + PAD), y + HEAD))
tag = "" if LETTERS == "ABCDEF" else "_" + LETTERS
out = os.path.join(ROOT, ("faces_contact_sheet" if MODE == "all" else f"faces_contact_sheet_{MODE}") + tag + ".png")
sheet.save(out)
print(out, faces)
