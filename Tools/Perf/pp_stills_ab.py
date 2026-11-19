"""atmosphere lane: before/after stills of the dream post-process Low branch, Low and Medium, one sheet per moment.
  python Tools/Perf/pp_stills_ab.py <before run> <after run> <moment> [<moment> ...] --out <dir>
Each sheet is 2x2 (Low before, Low after / Medium before, Medium after). Per pair it prints the mean absolute
difference in 8-bit luma and the share of pixels that moved more than 8 levels; the head sway, grain and sand move
between captures, so a Medium pair is judged against that floor rather than against zero."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def luma(p):
    return np.asarray(Image.open(p).convert('L')).astype(np.float32)


def diff(a, b):
    d = np.abs(luma(a) - luma(b))
    return round(float(d.mean()), 2), round(float((d > 8).mean() * 100), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('before')
    ap.add_argument('after')
    ap.add_argument('moments', nargs='+')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for m in a.moments:
        cells = [(Path(a.before) / 'shots' / f'{m}_q{q}.png', Path(a.after) / 'shots' / f'{m}_q{q}.png') for q in (0, 1)]
        tw, th = 960, 540
        sheet = Image.new('RGB', (tw * 2, (th + 22) * 2), (16, 16, 16))
        d = ImageDraw.Draw(sheet)
        for r, (pb, pa) in enumerate(cells):
            for c, (p, tag) in enumerate(((pb, 'before'), (pa, 'after'))):
                sheet.paste(Image.open(p).convert('RGB').resize((tw, th)), (c * tw, r * (th + 22) + 22))
                d.text((c * tw + 6, r * (th + 22) + 5), f"{m}  {'Low' if r == 0 else 'Medium'}  {tag}", fill=(235, 235, 235))
            print(m, 'Low' if r == 0 else 'Medium', 'mean |d| luma, % px > 8:', diff(pb, pa))
        sheet.save(out / f'pp_low_{m}.png')
    print('sheets in', out)


if __name__ == '__main__':
    main()
