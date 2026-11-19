"""T_SandGrain: the spill's grain baked into one small tileable texture, so M_SandSpill takes two or three samples
instead of ~30 procedural hashes (low-end budget). 256 x 256 texels at 1.1 mm = a 28 cm tile; the material samples it
on two incommensurate tilings (one turned 37 deg), which hides the repeat, and the mips average the grain away with
distance (no LOD line).
  R, G  fine grain normal tilt (white noise per texel, 0.5 = flat)
  B     smooth clumps (tileable value noise, ~4.4 mm cells, two octaves)
  A     glint mask (0.3% of texels, 1 = a near-mirror grain)
  python Tools/Splats/make_sand_grain_tex.py [--selftest]  ->  P:/FoA-Assets/procedural/T_SandGrain.png (linear, no sRGB)"""
import sys

import numpy as np
from PIL import Image

N = 256
OUT = "P:/FoA-Assets/procedural/T_SandGrain.png"


def tile_value_noise(rng, cells):
    """Smooth value noise that tiles over N texels: random lattice of cells x cells, smoothstep-interpolated."""
    g = rng.random((cells, cells))
    t = np.arange(N) * cells / N
    i, f = np.floor(t).astype(int), t - np.floor(t)
    f = f * f * (3 - 2 * f)
    i1 = (i + 1) % cells
    a, b = g[i][:, i], g[i][:, i1]
    c, d = g[i1][:, i], g[i1][:, i1]
    fx, fy = f[None, :], f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def make(seed=7):
    rng = np.random.default_rng(seed)
    r, g = rng.random((N, N)), rng.random((N, N))
    b = 0.65 * tile_value_noise(rng, 58) + 0.35 * tile_value_noise(rng, 116)
    b = (b - b.min()) / (b.max() - b.min())
    a = (rng.random((N, N)) < 0.003).astype(np.float64)
    return np.stack([r, g, b, a], -1)


def selftest():
    t = make()
    assert t.shape == (N, N, 4) and t.min() >= 0 and t.max() <= 1
    b = t[..., 2]
    assert abs(b[0] - b[-1]).mean() < 0.08 and abs(b[:, 0] - b[:, -1]).mean() < 0.08, "clumps tile seamlessly"
    assert 0.001 < t[..., 3].mean() < 0.006, "rare glints"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        Image.fromarray((make() * 255 + 0.5).astype(np.uint8), "RGBA").save(OUT)
        print("wrote", OUT)
