"""Battle lane: compare the B3d frames (Low custom-depth cut). Usage: python low_depth_frames.py <run_dir> [out_png]
Pairs: medium_a vs medium_a2 and low_before vs low_before2 (noise floors, same state), medium_a vs medium_b (Medium
before and after a Low round trip), low_before2 vs low_after (the cut). Prints mean absolute difference (0-255) and the share of pixels that moved
more than 8 levels, and writes a sheet: the four frames on top, the Low diff (x8) below."""
import glob
import sys

import numpy as np
from PIL import Image

TAGS = ('ld_medium_a', 'ld_medium_a2', 'ld_low_before', 'ld_low_before2', 'ld_low_after', 'ld_medium_b')


def load(run):
    out = {}
    for t in TAGS:
        hits = sorted(glob.glob(f'{run}/**/frames/*_{t}.png', recursive=True))
        if hits:
            out[t] = np.asarray(Image.open(hits[-1]).convert('RGB')).astype(np.int16)
    return out


def diff(a, b):
    d = np.abs(a - b).max(axis=2)
    return round(float(d.mean()), 3), round(float((d > 8).mean()) * 100, 3), d


def selftest():
    a = np.zeros((4, 4, 3), np.int16)
    b = a.copy()
    b[0, 0] = 40
    m, share, _ = diff(a, b)
    assert m == 2.5 and share == 6.25, (m, share)


def main(run, out=None):
    f = load(run)
    missing = [t for t in TAGS if t not in f]
    assert not missing, missing
    res = {}
    for name, x, y in (('noise_medium', 'ld_medium_a', 'ld_medium_a2'), ('noise_low', 'ld_low_before', 'ld_low_before2'),
                       ('medium_roundtrip', 'ld_medium_a', 'ld_medium_b'), ('low_cut', 'ld_low_before2', 'ld_low_after')):
        m, share, d = diff(f[x], f[y])
        res[name] = dict(mean=m, moved_pct=share)
        if name == 'low_cut':
            heat = np.clip(d * 8, 0, 255).astype(np.uint8)
    print(res)
    if out:
        h, w = f['ld_medium_a'].shape[:2]
        s = 3
        tiles = [Image.fromarray(f[t].astype(np.uint8)).resize((w // s, h // s)) for t in
                 ('ld_medium_a', 'ld_low_before2', 'ld_low_after', 'ld_medium_b')]
        sheet = Image.new('RGB', (4 * (w // s), 2 * (h // s)))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * (w // s), 0))
        sheet.paste(Image.fromarray(heat).convert('RGB').resize((w // s, h // s)), (w // s, h // s))
        sheet.save(out)
        print('sheet', out)
    return res


if __name__ == '__main__':
    selftest()
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
