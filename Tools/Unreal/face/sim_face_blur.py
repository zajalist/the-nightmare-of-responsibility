"""Offline stand-in for the face blur shader (numpy), to tune parameters on a burst's clean + mask frames without PIE.
  python Tools/Unreal/face/sim_face_blur.py <run> <view> [param=value ...]
Takes clean_<view> (colour) and mask_<view> (R = blur weight) and applies the per-line slip and drag of
pp_face_blur.hlsl (same structure, own hashes); prints face mean / std / low-frequency std against the clean face and
the leak_check readability NCC, writes Saved/FaceShots/<run>/sim_<view>.png. Approximate: no lens bend, no overhang."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from leak_check import grad_ncc, head_disc  # noqa: E402

ROOT = Path('P:/FoA/Saved/FaceShots')
P = dict(gain=1.05, comp=0.0,  # v11 (v10 was gain 0.84, comp 0.2)
         dark=0.4, slip=0.22, tear=0.3, len0=0.12, len1=0.14, keep_lf=0.0, lf_w=0.18, seed=1)


def smoothnoise(x, rng):
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    tab = rng.random(i.max() - i.min() + 2)
    return tab[i - i.min()] * (1 - f) + tab[i - i.min() + 1] * f


def run(clean, wmask, head, p):
    h, w, _ = clean.shape
    H = head[2] * 27.0 / 16.0
    W = 0.6 * H
    rng = np.random.default_rng(int(p['seed']))
    rows = np.arange(h)
    line = (rows // max(1, round(h / 540))).astype(int)
    yH = (rows - h / 2) / H
    n7, n3, n23 = smoothnoise(yH * 3, rng), smoothnoise(yH * 2, rng), smoothnoise(yH * 8, rng)
    lh = rng.random((line.max() + 1, 5))[line]  # per line: 17, jit, 71, 61, tear
    tear = (lh[:, 4] > 0.88).astype(float)
    ln = (p['len0'] + p['len1'] * n7 + 0.08 * (lh[:, 0] - 0.5)) * W
    off = (0.10 * (n3 - 0.5) + 0.08 * (n23 - 0.5) + (p['slip'] + p['tear'] * tear) * (lh[:, 1] - 0.5)) * W
    dirl = np.where(lh[:, 2] < 0.6, 1.0, -1.0)
    xs = np.arange(w)[None, :].astype(float)
    phase = rng.random((h, w))
    o = (off - 0.2 * ln * dirl)[:, None] + 0 * xs
    dx = (dirl * ln / 10)[:, None]
    rr = rows[:, None] + 0 * xs.astype(int)

    def at(img, x):
        return img[rr, np.clip(np.round(x).astype(int), 0, w - 1)]
    flip = at(wmask, xs + o + 5 * dx) < 0.25
    o = np.where(flip, (-off - 0.2 * ln * dirl)[:, None], o)
    acc = np.zeros_like(clean)
    ws = np.zeros((h, w))
    for i in range(10):
        s = xs + o + (i + phase) * dx
        m = at(wmask, s) * (0.3 + 0.7 * 2 ** (-0.5 * i))
        acc += at(clean, s) * m[..., None]
        ws += m
    base = clean
    smear = base + (acc / np.maximum(ws, 1e-3)[..., None] - base) * np.clip(ws * 1.5, 0, 1)[..., None]
    lum = lambda c: c.mean(-1)
    if p['keep_lf'] > 0:  # put the clean face's low-frequency light and dark back under the streaks
        k = max(1.0, p['lf_w'] * W)
        lf = lambda c: np.asarray(Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(k)), dtype=float) / 255
        ratio = (lum(lf(base)) + 0.02) / (lum(lf(smear)) + 0.02)
        smear = smear * (ratio ** p['keep_lf'])[..., None]
    lb, ls = lum(base), lum(smear)
    smear = smear * (1 + (np.clip(lb / np.maximum(ls, 1e-4), 0.35, 1) - 1) * p['dark'])[..., None]
    comb = 1 - 0.14 * (np.floor(rows / max(1, h / 1080)) % 3 >= 2)
    smear = smear * (p['gain'] * (0.8 + 0.35 * lh[:, 3]) * comb)[:, None, None]
    t = np.clip((lum(smear) - 0.3) / 0.6, 0, 1)
    smear = smear * (1 - p['comp'] * t * t * (3 - 2 * t))[..., None]
    return base + (smear - base) * wmask[..., None]


def main(run_name, view, kv):
    p = dict(P)
    p.update({k: float(v) for k, v in (a.split('=') for a in kv)})
    d = ROOT / run_name
    info = {s['label']: s for s in json.loads((d / 'shots.json').read_text())['shots']}
    head = (info.get('v10_' + view) or info[view])['head_px']
    clean = np.asarray(Image.open(d / f'clean_{view}.png').convert('RGB'), dtype=float) / 255
    mimg = np.asarray(Image.open(d / f'mask_{view}.png').convert('RGB'), dtype=float) / 255
    out = run(clean, mimg[..., 0], head, p)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(d / f'sim_{view}.png')
    m = mimg[..., 0] > 0.5
    face = head_disc(m.shape, (head[0], head[1] + 0.25 * head[2], head[2]), 0.75) & (mimg[..., 1] > 0.5)
    k = max(2, int(0.12 * head[2]))
    lfstd = lambda a: np.asarray(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(k)), dtype=float)[m].std()
    c, o = clean.mean(-1), out.mean(-1)
    res = dict(mean_ratio=o[m].mean() / c[m].mean(), std_ratio=o[m].std() / c[m].std(),
               lf_std_ratio=lfstd(o) / lfstd(c), ncc=grad_ncc(clean, out, face))
    print(view, {k2: round(float(v), 3) for k2, v in res.items()})
    return res


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
