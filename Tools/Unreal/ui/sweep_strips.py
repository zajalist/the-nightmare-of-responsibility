"""Strips of consecutive sweep frames for each intro defect (before/after evidence for intro_bugs.md).
  python Tools/Unreal/ui/sweep_strips.py <sweep dir> <tag> name:first-last [name:first-last ...]
Writes <sweep dir>/strip_<name>.png: every frame of the range, 8 per row, labelled fNNNN and seconds."""
import json
import os
import sys

from PIL import Image, ImageDraw


def main(d, tag, ranges):
    fps = json.load(open(os.path.join(d, 'keys.json')))['fps']
    req = json.load(open(os.path.join(d, 'shots.json')))['requests']  # the recorder's real request times
    tm = lambda f: req[f - 1] if f - 1 < len(req) else f / fps  # noqa: E731
    for spec in ranges:
        name, rng = spec.split(':')
        a, b = (int(v) for v in rng.split('-'))
        frames = list(range(a, b + 1))
        cols, tw, th = 8, 240, 135
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * tw, rows * (th + 14)), 'black')
        dr = ImageDraw.Draw(sheet)
        for k, f in enumerate(frames):
            p = os.path.join(d, 'frames', f'f{f:04d}.png')
            if not os.path.exists(p):
                continue
            x, y = (k % cols) * tw, (k // cols) * (th + 14)
            sheet.paste(Image.open(p).convert('RGB').resize((tw, th)), (x, y))
            dr.text((x + 2, y + th), f'{tag} f{f:04d} {tm(f):.1f}s', fill=(255, 90, 90))
        out = os.path.join(d, f'strip_{name}.png')
        sheet.save(out)
        print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
