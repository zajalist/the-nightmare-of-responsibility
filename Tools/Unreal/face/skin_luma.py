"""Skin luminance per view from a pie_face_shots.py run (clean_<view> frames, his head from mask_<view> G channel):
  python Tools/Unreal/face/skin_luma.py <run> [<run> ...]
Per view: mean luminance of the visible skin of his head (head mask minus the dark hair, luma > 0.12), its 99th
percentile, and the share of clipped pixels (> 0.95). Luma = Rec.709 on the 8-bit frame (display referred)."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('P:/FoA/Saved/FaceShots')
VIEWS = ('close_front', 'close_34', 'close_profile', 'mid_34', 'far_front', 'tps_34back')


def luma(p):
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255.0
    return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def run(name):
    out = {}
    for v in VIEWS:
        c, m = ROOT / name / f'clean_{v}.png', ROOT / name / f'mask_{v}.png'
        if not (c.exists() and m.exists()):
            continue
        y = luma(c)
        head = np.asarray(Image.open(m).convert('RGB'))[..., 1] > 127
        skin = head & (y > 0.12)
        if skin.sum() < 20:
            continue
        out[v] = dict(skin_mean=round(float(y[skin].mean()), 3), skin_p99=round(float(np.percentile(y[skin], 99)), 3),
                      clipped=round(float((y[skin] > 0.95).mean()), 4), px=int(skin.sum()))
    (ROOT / name / 'skin_luma.json').write_text(json.dumps(out, indent=1))
    return out


if __name__ == '__main__':
    for n in sys.argv[1:]:
        for v, r in run(n).items():
            print(n, v, r)
