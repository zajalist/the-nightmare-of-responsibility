"""playercam lane: the phone screen's text in every PCP frame (pie_play.py), cropped from the logged screen box, with a
sharpness score (variance of the Laplacian of the grey crop, normalised by its contrast: ghosted text scores lower),
and one sheet of the crops, enlarged, row per tag.
  python Tools/Unreal/player/pc_phone_crops.py <PCP plan dir> <out.png>"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def score(im):
    g = np.asarray(im.convert('L'), dtype=np.float32)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var() / max(g.std(), 1.0) ** 2)


def main(plan_dir, out):
    log = json.load(open(os.path.join(plan_dir, 'play.json'), encoding='utf-8'))['log']
    shots = [e for e in log if e['kind'] == 'pc_phone' and e.get('box') and e.get('frame') and os.path.exists(e['frame'])]
    rows, res = {}, []
    for e in shots:
        im = Image.open(e['frame']).convert('RGB')
        x0, y0, x1, y1 = e['box']
        w, h = x1 - x0, y1 - y0
        box = (max(0, x0 + int(w * 0.05)), max(0, y0 + int(h * 0.08)), min(im.width, x1 - int(w * 0.05)), min(im.height, y0 + int(h * 0.45)))
        crop = im.crop(box)  # the status bar, "Today" and the task list
        s = round(score(crop), 3)
        res.append(dict(tag=e['tag'], t=e['t'], score=s, frame=os.path.basename(e['frame'])))
        rows.setdefault(e['tag'], []).append((crop, s))
    tw = 260
    th = max((int(c.height * tw / max(c.width, 1)) for r in rows.values() for c, _ in r), default=200)
    cols = max(len(r) for r in rows.values())
    sheet = Image.new('RGB', (cols * tw + 90, len(rows) * (th + 18)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for i, (tag, r) in enumerate(rows.items()):
        d.text((4, i * (th + 18) + th // 2), tag, fill=(230, 230, 230))
        for j, (c, s) in enumerate(r):
            sheet.paste(c.resize((tw, int(c.height * tw / max(c.width, 1))), Image.LANCZOS), (90 + j * tw, i * (th + 18)))
            d.text((92 + j * tw, i * (th + 18) + th + 2), f'{s:.2f}', fill=(200, 200, 120))
    sheet.save(out)
    by = {}
    for r in res:
        by.setdefault(r['tag'], []).append(r['score'])
    print(json.dumps({k: dict(n=len(v), min=min(v), median=float(np.median(v)), max=max(v)) for k, v in by.items()}, indent=1))
    print('sheet', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
