"""Intro v4 plates (intro lane, offline). Builds two textures per panel for M_IntroPlate v4 (hlsl/intro_plate_v4.hlsl):
  T_IntroPlate_<P>      2048x1152  R ink-graded luminance, G nearness (0 far, 1 near), B the same with the panel's light
                                   on (only the phone differs), A subject matte (the figure, the shirt, the phone, him)
  T_IntroPlate_<P>_Back 1024x576   R back luminance with the subject and the near cutouts filled in (push-pull), G back
                                   nearness filled the same way, B back luminance with the light on, A near-cutout matte
The shader draws three planes from these: the back (a continuous depth warp of _Back), the subject and the near cutout
(rigid planes from the main plate at their own rates), so the planes slide past each other and never tear.
Source: the v3 plates (Saved/StoryShots/intro/plates, made by Tools/LookDev/intro_plates.py from in-engine captures).
  python Tools/LookDev/intro_v4/plates_v4.py [--preview]   -> Saved/StoryShots/intro/v4/*.png (+ masks_preview.jpg)
Self-check: push-pull fill keeps valid pixels and leaves no holes (asserted per panel)."""
import os
import sys

import cv2
import numpy as np

SRC = 'P:/FoA/Saved/StoryShots/intro/plates'
OUT = 'P:/FoA/Saved/StoryShots/intro/v4'
PANELS = ['Room', 'Phone', 'Shirt', 'Watcher', 'Lunge']


def box(h, w, x0, y0, x1, y1, feather=0.04):
    """A soft box: 1 inside, fading over `feather` (UV) at any edge that is not the frame's own edge."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / w, yy / h
    ramp = lambda d: np.clip(d / feather, 0, 1)  # noqa: E731
    m = np.ones((h, w), np.float32)
    for lo, hi, c in ((x0, x1, u), (y0, y1, v)):
        m *= (ramp(c - lo) if lo > 0 else 1) * (ramp(hi - c) if hi < 1 else 1)
    return m


def masks(name, near, a):
    """(subject, near cutout) mattes, 0..1, at plate size. Rules picked by eye from the nearness contours."""
    h, w = near.shape
    subj = a.copy()
    cut = np.zeros_like(near)
    if name == 'Room':  # no subject plane: the bed rides the back's depth warp
        cut = ((near > 0.80) * box(h, w, 0.40, 0.0, 0.58, 0.32)                     # the chandelier
               + (near > 0.50) * box(h, w, 0.0, 0.0, 0.25, 0.84)                    # the near curtains
               + (near > 0.62) * box(h, w, 0.94, 0.0, 1.0, 0.9))                     # the wardrobe's edge
    elif name == 'Phone':
        cut = (near > 0.60) * box(h, w, 0.0, 0.0, 0.17, 1.0)                        # the books
    elif name == 'Watcher':
        cut = ((near > 0.78) * box(h, w, 0.66, 0.66, 1.0, 1.0)                       # the plant
               + (near > 0.55) * box(h, w, 0.70, 0.0, 1.0, 1.0))                     # the curtains
    cut = np.clip(cut, 0, 1).astype(np.float32) * (1 - (a > 0.5))
    soft = lambda m: cv2.GaussianBlur(cv2.morphologyEx(m.astype(np.float32), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)), (0, 0), 1.2)
    return np.clip(soft(subj), 0, 1), np.clip(soft(cut), 0, 1)


def pushpull(img, valid):
    """Fill invalid pixels from coarser averages of the valid ones (a smooth inpaint, cheap at 2k)."""
    levels = [(img * valid, valid)]
    while min(levels[-1][1].shape) > 4:
        v, m = levels[-1]
        levels.append((cv2.resize(v, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
                       cv2.resize(m, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)))
    v, m = levels[-1]
    fill = np.where(m > 1e-4, v / np.maximum(m, 1e-4), (v.sum() / max(m.sum(), 1e-4)))
    for v, m in reversed(levels[:-1]):
        up = cv2.resize(fill, (v.shape[1], v.shape[0]), interpolation=cv2.INTER_LINEAR)
        own = np.where(m > 1e-4, v / np.maximum(m, 1e-4), up)
        k = np.clip(m * 2.0, 0, 1)
        fill = own * k + up * (1 - k)
    return fill


def fill(ch, valid, grain=True):
    """Hole fill for the back plane: Telea inpaint at half size over a push-pull base (edges carry into the hole),
    then the neighbourhood's own fine grain at its local strength, so a revealed patch reads as wall, not as a smudge."""
    base = pushpull(ch, valid)
    h, w = ch.shape
    small = cv2.resize(base, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    m = (cv2.resize(valid, (w // 2, h // 2), interpolation=cv2.INTER_AREA) < 0.99).astype(np.uint8)
    tel = cv2.inpaint((np.clip(small, 0, 1) * 255).astype(np.uint8), m, 6, cv2.INPAINT_TELEA).astype(np.float32) / 255
    tel = cv2.resize(tel, (w, h), interpolation=cv2.INTER_CUBIC)
    deep = np.clip(cv2.distanceTransform((valid < 0.99).astype(np.uint8), cv2.DIST_L2, 5) / 24.0, 0, 1)
    out = np.where(valid > 0.99, ch, tel * (1 - deep) + base * deep)  # Telea fans out deep inside big holes
    if grain:
        hp = ch - cv2.GaussianBlur(ch, (0, 0), 1.5)
        std = pushpull(np.sqrt(cv2.GaussianBlur(hp * hp * valid, (0, 0), 12) / np.maximum(cv2.GaussianBlur(valid, (0, 0), 12), 1e-3)), valid)
        n = cv2.GaussianBlur(np.random.default_rng(7).standard_normal(ch.shape).astype(np.float32), (0, 0), 0.7)
        out = out + (1 - valid) * n / (n.std() + 1e-6) * std
    return np.clip(out, 0, 1).astype(np.float32)


def xdog(y, sigma, tau=0.98, eps=0.012, phi=90.0, k=1.6):
    d = cv2.GaussianBlur(y, (0, 0), sigma) - tau * cv2.GaussianBlur(y, (0, 0), sigma * k)
    return np.clip(np.where(d >= eps, 1.0, 1.0 + np.tanh(phi * (d - eps))), 0, 1)


def ink(y, near, mattes=None):
    """Photoreal B&W with inked contrast: a light flatten of render noise, an inky toe, XDoG contour lines on the
    log luminance (they read in the dark too) and silhouette lines where the depth jumps."""
    y8 = (np.clip(y, 0, 1) * 255).astype(np.uint8)
    flat = cv2.edgePreservingFilter(cv2.cvtColor(y8, cv2.COLOR_GRAY2BGR), flags=1, sigma_s=12, sigma_r=0.12)[..., 0] / 255.0
    t = 0.55 * flat + 0.45 * y
    big = cv2.GaussianBlur(t, (0, 0), 40)
    t = np.clip(t + 0.35 * (t - big), 0, 1)                    # local contrast, the inked punch
    t = t * t * (3 - 2 * t) * 0.4 + t * 0.6                     # a soft S, deep toe
    ly = np.log1p(y * 14) / np.log1p(14)
    lines = xdog(ly.astype(np.float32), 1.1) * (0.55 + 0.45 * xdog(ly.astype(np.float32), 2.2, tau=0.985, eps=0.006, phi=60))  # fine + bold
    gx, gy = cv2.Sobel(near, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(near, cv2.CV_32F, 0, 1, ksize=3)
    sil = cv2.GaussianBlur(np.clip(np.hypot(gx, gy) * 3 - 0.15, 0, 1), (0, 0), 0.9)
    if mattes is not None:  # the nearness edge sits a few px outside a cutout: draw it just inside instead
        hard = (mattes > 0.5).astype(np.uint8)
        ring = cv2.dilate(hard, np.ones((25, 25), np.uint8)) - hard
        inner = (hard - cv2.erode(hard, np.ones((5, 5), np.uint8))).astype(np.float32)
        sil = np.maximum(sil * (1 - ring), cv2.GaussianBlur(inner, (0, 0), 0.8) * 0.9)
    return np.clip(t * (0.45 + 0.55 * lines) * (1 - 0.8 * sil), 0, 1).astype(np.float32)


def build(name):
    im = cv2.imread(f'{SRC}/T_IntroPlate_{name}.png', cv2.IMREAD_UNCHANGED).astype(np.float32) / 255.0
    lum, near, lit, a = im[..., 2], im[..., 1], im[..., 0], im[..., 3]
    subj, cut = masks(name, near, a)
    both = np.maximum(subj, cut)
    r = ink(lum, near, both)
    b = ink(lit, near, both) if name == 'Phone' else r
    hole = np.clip(np.maximum(subj, cut) * 1.6, 0, 1)
    hole = cv2.dilate(hole, np.ones((7, 7), np.uint8))           # the cutout's own rim never bleeds into the back
    valid = (1 - hole).astype(np.float32)
    back = [fill(ch, valid, grain=ch is not near) for ch in (r, near, b)]
    assert all(np.isfinite(ch).all() for ch in back), name
    assert np.abs(back[0] - r)[valid > 0.99].mean() < 0.02, name  # the fill leaves the visible back alone
    os.makedirs(OUT, exist_ok=True)
    main = np.dstack([b, near, r, subj])                         # cv2 writes BGRA: B=lit, G=near, R=lum, A=subject
    cv2.imwrite(f'{OUT}/T_IntroPlate_{name}.png', (np.clip(main, 0, 1) * 255 + 0.5).astype(np.uint8))
    small = [cv2.resize(ch, (1024, 576), interpolation=cv2.INTER_AREA) for ch in (*back, cut)]
    small = np.dstack([small[2], small[1], small[0], small[3]])  # BGRA: B=back lit, G=back near, R=back lum, A=cut
    cv2.imwrite(f'{OUT}/T_IntroPlate_{name}_Back.png', (np.clip(small, 0, 1) * 255 + 0.5).astype(np.uint8))
    return r, subj, cut, back[0]


if __name__ == '__main__':
    tiles = []
    for n in PANELS:
        r, subj, cut, back = build(n)
        vis = cv2.cvtColor((r * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR).astype(np.float32)
        vis[..., 2] += subj * 120
        vis[..., 1] += cut * 120
        tiles.append(np.hstack([cv2.resize(np.clip(vis, 0, 255).astype(np.uint8), (800, 450)),
                                cv2.resize(cv2.cvtColor((back * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR), (800, 450))]))
        print(n, 'subject %.3f cut %.3f' % (subj.mean(), cut.mean()))
    if '--preview' in sys.argv:
        cv2.imwrite(f'{OUT}/masks_preview.jpg', np.vstack(tiles))
        print(f'{OUT}/masks_preview.jpg')
