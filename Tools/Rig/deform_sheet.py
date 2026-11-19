"""Compose the finger and forearm deformation sheet from Tools/Unreal/rig/pose_sheet.py frames, with red boxes on the
faults found by eye. python Tools/Rig/deform_sheet.py <frames dir> <out.jpg>"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

D, OUT = Path(sys.argv[1]), sys.argv[2]
T = 430  # tile size; frames are 960 px
ROWS = [  # (label, left frame, right frame, verdict)
    ("Open relaxed", "00_open_relaxed_fp", "00_open_relaxed_tp", "OK: soft natural curl, no stretch."),
    ("Full fist", "01_full_fist_fp", "01_full_fist_tp", "FAULT: thumb tip goes thin and sinks into the index finger."),
    ("Phone-grip curl, left", "02_phone_grip_left_fp", "02_phone_grip_left_tp", "OK: wraps from the knuckles; no webbing stretch."),
    ("Screwdriver grip, right", "03_screwdriver_grip_right_fp", "03_screwdriver_grip_right_tp", "FAULT: thumb tip pierces the index and middle fingertips."),
    ("Index point", "04_index_point_fp", "04_index_point_tp", "OK: clean straight index, tidy fist."),
    ("Wide splay", "05_wide_splay_fp", "05_wide_splay_tp", "OK: webbing stretches evenly, no tearing."),
    ("Wrist roll +60", "06_wrist_roll_plus60_fp", "06_wrist_roll_plus60_tp", "OK: roll spreads along the forearm, no candy wrapper."),
    ("Wrist roll -60", "07_wrist_roll_minus60_fp", "07_wrist_roll_minus60_tp", "OK: same, other way."),
    ("Slap elbow, right", "08_slap_elbow_right_elbow_nosleeve", "08_slap_elbow_right_elbow_sleeve",
     "Sleeve hidden (left): smooth elbow. Sleeve shown (right): the step is the polo sleeve hem."),
]
BOXES = {  # frame -> boxes in 960-px frame coordinates
    "01_full_fist_tp": [(600, 375, 700, 550)],
    "03_screwdriver_grip_right_tp": [(625, 425, 715, 555)],
    "08_slap_elbow_right_elbow_sleeve": [(320, 165, 650, 265)],
}
font = ImageFont.load_default(size=19)
small = ImageFont.load_default(size=17)
LW = 230
H = 40 + len(ROWS) * (T + 34)
S = Image.new("RGB", (LW + 2 * T + 30, H), (18, 18, 20))
g = ImageDraw.Draw(S)
g.text((LW, 10), "first-person eye", fill=(230, 230, 230), font=font)
g.text((LW + T + 10, 10), "close third-person (slap row: sleeve hidden | shown)", fill=(230, 230, 230), font=small)
y = 40
for label, a, b, verdict in ROWS:
    g.text((10, y + T // 2 - 12), label, fill=(240, 240, 240), font=font)
    for j, name in enumerate((a, b)):
        im = Image.open(D / f"{name}.png").convert("RGB")
        d = ImageDraw.Draw(im)
        for box in BOXES.get(name, []):
            d.rectangle(box, outline=(235, 30, 30), width=6)
        S.paste(im.resize((T, T)), (LW + j * (T + 10), y))
    colour = (255, 120, 110) if verdict.startswith("FAULT") else (200, 220, 200)
    g.text((LW, y + T + 6), verdict, fill=colour, font=small)
    y += T + 34
S.save(OUT, quality=90)
print("sheet", OUT, S.size)
