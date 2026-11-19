"""Contact sheet of the LS_WakeUp stills (offline, no editor):
  python Tools/Unreal/cine/contact_sheet.py <stills dir> <out.png>
  python Tools/Unreal/cine/contact_sheet.py <MRQ frames dir> <out.png> --frames [--fps 15]   (tiles from LS_WakeUp.NNNN.png at FRAME_T)
One tile per shot in shot order, captioned with the shot number, name, lens, time range and beat timings. A missing still is a
black tile (shot 1 is black by design)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SHOTS = [("1_Black", "1  Black", "held black, the clock ticks", "0.0 to 3.0 s",
          "tick 0.0, alarm click 2.2, bell 2.3"),
         ("2_POV", "2  POV, eyes open", "24 mm  f/1.4", "3.0 to 9.2 s",
          "lids 3.0 to 5.4, hold 5.4 to 6.4, head turn 6.4 to 8.0"),
         ("2b_POV_clock", "2  POV, the head turn lands on the clock", "24 mm  f/1.4", "8.0 to 9.2 s",
          "focus lands 8.0, hold 8.0 to 9.2, cut on the hold"),
         ("3_Wide", "3  Wide, the room", "28 mm  f/4", "9.2 to 13.2 s",
          "locked off, he lies still, cut on the hold"),
         ("4_PushIn", "4  The slow push-in", "50 mm  f/2", "13.2 to 19.7 s",
          "hold to 14.2, push to 18.8, hold, dip 19.3 to 19.75"),
         ("5_TwoShot", "5  Bed-edge two-shot", "40 mm  f/2.8", "19.7 to 24.2 s",
          "dip up 19.75 to 20.15, anticipation 23.80, match cut"),
         ("6_Insert", "6  Insert, the clock and the sand", "40 mm  f/5.6", "24.2 to 28.4 s",
          "slap 25.30, collapse to 26.50, clear pile hold 27.30"),
         ("7_Stand", "7  The stand", "32 mm  f/2.8", "28.4 to 33.4 s",
          "breath to 29.4, stand and crane 29.4 to 31.4, hold"),
         ("8_HandBack", "8  Hand-back, then a 1.5 s blend to gameplay", "35 mm  f/8", "33.4 to 36.4 s",
          "idle blend 0.4 s, hold to 34.9, camera blend to 36.4")]
# --frames: the sequence second each tile is taken from (the hold beats of docs/cinematics/wakeup_shotlist.md)
FRAME_T = {"1_Black": 1.5, "2_POV": 5.9, "2b_POV_clock": 8.8, "3_Wide": 11.0, "4_PushIn": 19.0, "5_TwoShot": 22.0,
           "6_Insert": 25.8, "7_Stand": 32.5, "8_HandBack": 34.2}
TW, TH, CAP, PAD, COLS = 640, 360, 82, 14, 3


def main(src, out, frames=False, fps=30):
    rows = (len(SHOTS) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TW + (COLS + 1) * PAD, rows * (TH + CAP) + (rows + 1) * PAD), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    big = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    for i, (stem, title, lens, span, beats) in enumerate(SHOTS):
        x = PAD + (i % COLS) * (TW + PAD)
        y = PAD + (i // COLS) * (TH + CAP + PAD)
        path = os.path.join(src, "LS_WakeUp.%04d.png" % round(FRAME_T[stem] * fps) if frames else stem + ".png")
        tile = Image.open(path).convert("RGB").resize((TW, TH), Image.LANCZOS) if os.path.exists(path) else \
            Image.new("RGB", (TW, TH), (0, 0, 0))
        sheet.paste(tile, (x, y))
        d.text((x, y + TH + 6), title, font=big, fill=(235, 235, 235))
        d.text((x, y + TH + 32), "%s    %s" % (lens, span), font=small, fill=(160, 160, 160))
        d.text((x, y + TH + 54), beats, font=small, fill=(160, 160, 160))
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], "--frames" in a, int(a[a.index("--fps") + 1]) if "--fps" in a else 30)
