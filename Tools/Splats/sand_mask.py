"""Sand mask for the QA check (d) from sand_capture.py's normals pair: a pixel is visible sand where the sand-only
GBuffer normal exists and roughly equals the whole scene's (anything in front of the sand changes the normal; the
tolerance absorbs the dithered edges, which differ between captures). The normals skip the post-process, so the mask is
then bent by the dream lens' barrel (M_PP_DreamLens: uv = 0.5 + (UV - 0.5)(1 + k r^2)/(1 + k), k = LensLook.z * 0.18)
to line up with the final frame.
  python Tools/Splats/sand_mask.py NALL.png NSAND.png OUT_MASK.png [k=0.045]
  python Tools/Splats/sand_mask.py --selftest"""
import sys

import numpy as np
from PIL import Image


def barrel(m, k):
    """Resample a mask the way the lens resamples the picture (nearest)."""
    h, w = m.shape
    v, u = np.mgrid[0:h, 0:w]
    uv = np.stack([(u + 0.5) / w, (v + 0.5) / h], -1)
    asp = np.array([w / h, 1.0])
    d = (uv - 0.5) * asp
    r2 = (d * d).sum(-1) / (0.25 * (asp * asp).sum())
    src = 0.5 + (uv - 0.5) * ((1.0 + k * r2) / (1.0 + k))[..., None]
    x = np.clip((src[..., 0] * w).astype(int), 0, w - 1)
    y = np.clip((src[..., 1] * h).astype(int), 0, h - 1)
    return m[y, x]


def mask(nall, nsand, tol=0.2, k=0.0):
    a, s = (np.asarray(Image.open(p).convert("RGB"), np.float32) / 255.0 for p in (nall, nsand))
    m = (s.max(2) > 0.02) & (np.abs(a - s).max(2) < tol)
    if k:
        m = barrel(m, k)
    # one pixel of erosion: dithered splat edges and TSR jitter make the rim unreliable
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    return e


def selftest():
    import os
    import tempfile
    d = tempfile.mkdtemp()
    a = np.zeros((8, 8, 3), np.uint8) + 128
    s = np.zeros((8, 8, 3), np.uint8)
    s[1:7, 1:7] = 128          # sand under the whole 6x6 block
    a[1:4, 1:7] = 200          # an occluder over its top half
    Image.fromarray(a).save(os.path.join(d, "a.png"))
    Image.fromarray(s).save(os.path.join(d, "s.png"))
    m = mask(os.path.join(d, "a.png"), os.path.join(d, "s.png"))
    assert m[5, 3] and not m[2, 3] and not m[0, 0] and m.sum() == 4, m.astype(int)  # rows 4-6 visible, eroded to 1x4
    b = barrel(np.eye(64, dtype=bool)[::-1] | np.eye(64, dtype=bool), 0.0)
    assert (b == (np.eye(64, dtype=bool)[::-1] | np.eye(64, dtype=bool))).all()      # k = 0 is the identity
    c = np.zeros((64, 64), bool)
    c[40, 40] = True
    assert barrel(c, 0.2)[41:44, 41:44].any() and not barrel(c, 0.2)[40, 40]          # barrel pushes a point outward
    print("selftest ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        selftest()
    else:
        m = mask(sys.argv[1], sys.argv[2], k=float(sys.argv[4]) if len(sys.argv) > 4 else 0.045)
        Image.fromarray((m * 255).astype(np.uint8)).save(sys.argv[3])
        print(sys.argv[3], int(m.sum()), "sand px")
