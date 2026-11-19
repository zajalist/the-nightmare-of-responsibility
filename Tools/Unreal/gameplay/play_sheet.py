"""Contact sheet of a pie_play.py burst: one labelled frame per beat change (plus optional extra times).
  python Tools/Unreal/gameplay/play_sheet.py A [extra_seconds,...]   -> Saved/Integration/play_A_sheet.png
  python Tools/Unreal/gameplay/play_sheet.py ALL                     -> Saved/Integration/playthrough_sheet.png (A..D)"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

ROOT = 'P:/FoA/Saved/Integration'


def picks(plan, extra=()):
    log = json.load(open(f'{ROOT}/play_{plan}.json'))
    fs = sorted(glob.glob(f'{ROOT}/play_{plan}_frames/*.png'), key=os.path.getmtime)
    t0 = os.path.getmtime(fs[0])
    want = [(e['t'] + 0.6, f"{plan} {e['beat']}") for e in log if e['kind'] == 'beat']
    want += [(t, f'{plan} +{t:.0f}s') for t in extra]
    out = []
    for t, label in sorted(want):
        f = min(fs, key=lambda f: abs((os.path.getmtime(f) - t0) - t))
        out.append((label, f))
    return out


def sheet(items, path, cols=4):
    ims = []
    for label, f in items:
        im = Image.open(f).convert('RGB')
        im.thumbnail((480, 270))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 9 * len(label) + 10, 20), fill=(0, 0, 0))
        d.text((5, 4), label, fill=(255, 255, 255))
        ims.append(im)
    rows = (len(ims) + cols - 1) // cols
    W = Image.new('RGB', (480 * cols, 270 * rows))
    for i, im in enumerate(ims):
        W.paste(im, ((i % cols) * 480, (i // cols) * 270))
    W.save(path)
    print(path, len(ims), 'frames')


if __name__ == '__main__':
    plan = sys.argv[1]
    extra = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else []
    if plan == 'ALL':
        items = []
        for p in 'ABCD':
            if os.path.exists(f'{ROOT}/play_{p}.json'):
                items += picks(p)
        sheet(items, f'{ROOT}/playthrough_sheet.png', cols=5)
    else:
        sheet(picks(plan, extra), f'{ROOT}/play_{plan}_sheet.png')
