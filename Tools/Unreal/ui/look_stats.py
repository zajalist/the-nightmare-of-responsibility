"""Numbers for the step-2 look match: mean luma per third (left, middle, right), the bright-area share and the warm
tint, page v3.1 frame vs PIE frame at the same beat.
  python Tools/Unreal/ui/look_stats.py <proof frames dir>"""
import glob
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from sbs import BEATS, page_frame  # noqa: E402


def stats(path):
    a = np.asarray(Image.open(path).convert('RGB').resize((480, 270))).astype(np.float32) / 255.0
    y = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    thirds = [float(y[:, i * 160:(i + 1) * 160].mean()) for i in range(3)]
    return thirds, float((y > 0.7).mean()), float((a[..., 0] - a[..., 2]).mean())


def main(src):
    for name, t in BEATS:
        game = sorted(glob.glob(os.path.join(src, f'*_{name}.png')))
        if not game:
            continue
        pf, _ = page_frame(t, name.startswith('menu'))
        for tag, f in (('page', pf), ('game', game[0])):
            th, bright, warm = stats(f)
            print(f'{name:10s} {tag}: thirds L/M/R {th[0]:.3f} {th[1]:.3f} {th[2]:.3f}  bright>0.7 {bright:.1%}  warm(R-B) {warm:+.3f}')


if __name__ == '__main__':
    main(sys.argv[1])
