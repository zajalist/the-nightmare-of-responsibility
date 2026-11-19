"""Bakes the two bedroom-trim textures into P:/FoA-Assets/procedural/.

  python Tools/Unreal/bake_trim_ornament.py
  python Tools/Unreal/bake_trim_ornament.py --selftest

T_TrimOrnament_N.png (sampled with the trims' UV1): 256 x 512, DirectX convention (Unreal). U runs across a band,
V tiles along the run every ORN_TILE (12 cm). Columns (make_procedural_meshes.ORN_*): flat, egg-and-dart (crown
ovolo, 3.46 cm band, 3.0 cm period), bead-and-reel (baseboard bead, 2.36 cm band, 2.4 cm period). Heights in cm.

T_TrimPaint_Mask.png (sampled with UV0, world scale: U = profile arc m, V = run m; tiles every 1 m): 256 x 1024,
linear. One board of Poly Haven white_planks_clean (CC0), so no tongue-and-groove seam can land on a trim:
R = paint brightness from the grain (mean 0.5: BaseColor = Paint * R), G = satin roughness 0.30-0.50,
B = tileable scuff blotches (used only by MI_Trim_Baseboard). Replaces three 2k samples and a procedural Noise.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_procedural_meshes import ORN_BEAD, ORN_EGG, ORN_TILE  # noqa: E402

W, H = 256, 512
EGG_BAND, EGG_PERIOD = 3.46, 3.0      # ovolo arc (cm), egg spacing (cm)
BEAD_BAND, BEAD_PERIOD = 2.36, 2.4    # bead arc (cm), olive + two reels (cm)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def egg_and_dart(s, t):
    """s along the run (cm, 0..period), t across the band (cm, 0 = bottom edge). Returns height (cm)."""
    sc = s - EGG_PERIOD / 2
    taper = 0.82 + 0.18 * np.clip((t - 0.5) / 2.4, 0, 1)  # eggs hang pointy end down
    r = np.sqrt((sc / (0.92 * taper)) ** 2 + ((t - 1.9) / 1.3) ** 2)
    h = np.full_like(s, -0.10)                                   # carved-back ground
    h = np.where((r > 1.12) & (r < 1.36), 0.14 * np.sin(np.pi * (r - 1.12) / 0.24), h)  # shell (tongue) rim
    h = np.where(r <= 1.0, -0.06 + 0.32 * np.sqrt(np.clip(1 - r * r, 0, 1)), h)       # the egg
    d = np.minimum(s, EGG_PERIOD - s)                            # distance to the dart axis
    head = np.where(t < 1.3, 0.40 * np.clip((t - 0.3) / 1.0, 0, 1), 0.10)  # arrowhead, tip pointing down
    dart = np.where((t > 0.3) & (t < 3.2) & (d < head), 0.16 * (1 - d / np.maximum(head, 1e-3)), -1.0)
    h = np.maximum(h, dart)
    return h * smooth(0.0, 0.18, t) * smooth(0.0, 0.18, EGG_BAND - t)


def bead_and_reel(s, t):
    """Olive (1.5 cm) then two reels (0.26 cm discs) per period; the relief rides on the round bead."""
    olive = np.where(s < 1.5, 0.20 * np.sqrt(np.clip(1 - ((s - 0.75) / 0.75) ** 2, 0, 1)), 0.0)
    reels = sum(np.where(np.abs(s - c) < 0.13, 0.17 * np.sqrt(np.clip(1 - ((s - c) / 0.13) ** 2, 0, 1)), 0.0)
                for c in (1.78, 2.12))
    h = np.maximum(olive, reels) - 0.20
    return h * np.sin(np.pi * np.clip(t / BEAD_BAND, 0, 1)) ** 0.6


def bake():
    height = np.zeros((H, W))
    rows = (np.arange(H) + 0.5) / H * ORN_TILE                  # cm along the run
    cell = {}
    for (u0, u1), band, period, fn in ((ORN_EGG, EGG_BAND, EGG_PERIOD, egg_and_dart),
                                       (ORN_BEAD, BEAD_BAND, BEAD_PERIOD, bead_and_reel)):
        c0, c1 = int(round(u0 * W)), int(round(u1 * W))
        t = (np.arange(c0, c1) + 0.5 - c0) / (c1 - c0) * band   # cm across the band
        S, T = np.meshgrid(rows % period, t, indexing="ij")
        height[:, c0:c1] = fn(S, T)
        cell[(c0, c1)] = (band / (c1 - c0), ORN_TILE / H)       # cm per texel (across, along)
    nx, ny = np.zeros((H, W)), np.zeros((H, W))
    for (c0, c1), (du, dv) in cell.items():
        hb = height[:, c0:c1]
        gx = (np.pad(hb, ((0, 0), (1, 1)), mode="edge")[:, 2:] - np.pad(hb, ((0, 0), (1, 1)), mode="edge")[:, :-2]) / (2 * du)
        gy = (np.roll(hb, -1, axis=0) - np.roll(hb, 1, axis=0)) / (2 * dv)  # wraps: V tiles along the run
        nx[:, c0:c1], ny[:, c0:c1] = -gx, -gy                   # DirectX: +Y follows increasing V (image rows)
    n = np.stack([nx, ny, np.ones((H, W))], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8), height


PLANKS = "P:/FoA-Assets/polyhaven/textures/white_planks_clean/white_planks_clean_{}_2k.jpg"
BOARD = slice(111, 183)  # one board's interior in the 2k planks set: no groove (they repeat every ~97 px), fewest cross-marks


def periodic_noise(n, feature_px, seed):
    """Tileable noise (FFT low-pass of white noise), zero mean, unit std."""
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    spec = np.fft.fft2(np.random.default_rng(seed).standard_normal((n, n)))
    field = np.real(np.fft.ifft2(spec * np.exp(-(fx ** 2 + fy ** 2) * (np.pi * feature_px) ** 2 / 2)))
    return (field - field.mean()) / field.std()


def bake_mask():
    def strip(kind):  # one board of the planks set, 0..1
        return np.asarray(Image.open(PLANKS.format(kind)), dtype=np.float32)[:, BOARD] / 255.0

    rgb = strip("diff")
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    lum = lin @ np.array([0.3, 0.59, 0.11], dtype=np.float32)    # Unreal's Desaturation weights
    rough = strip("rough")
    rough = rough[..., 0] if rough.ndim == 3 else rough
    size = lambda a: np.asarray(Image.fromarray(a.astype(np.float32), "F").resize((256, 1024), Image.BICUBIC))  # noqa: E731
    flat = lambda a: a - a.mean(axis=1, keepdims=True) + a.mean()  # noqa: E731  drop cross-grain bands, keep streaks
    r = size(flat(0.5 * lum / lum.mean()))
    g = size(flat(0.30 + 0.20 * rough))
    n = periodic_noise(1024, 26.0, 7) + 0.5 * periodic_noise(1024, 8.0, 11)  # ~5 cm blotches + grit, physical px
    b = size(np.clip(0.30 + 0.33 * n, 0.0, 1.0))
    return np.clip(np.stack([r, g, b], axis=-1), 0, 1)


def selftest():
    m = bake_mask()
    assert m.shape == (1024, 256, 3) and abs(m[..., 0].mean() - 0.5) < 0.01, m[..., 0].mean()
    assert 0.30 <= m[..., 1].min() and m[..., 1].max() <= 0.50, "roughness must stay satin"
    assert np.abs(m[..., 0].mean(axis=1) - 0.5).max() < 0.01, "a cross-grain band would stripe every metre of trim"
    for c in (0, 1, 2):  # tiles along the run: the wrap step is no bigger than any step inside the tile
        assert np.abs(m[0, :, c] - m[-1, :, c]).max() <= np.abs(np.diff(m[..., c], axis=0)).max() + 1e-6, c
    nor = np.asarray(Image.open(PLANKS.format("nor_gl")), dtype=np.float32)[:, BOARD, 0]
    assert np.abs(nor.mean(axis=0) - 128).max() < 12, "board strip must not contain a groove"
    img, height = bake()
    flat = img[:, :int(ORN_EGG[0] * W) - 2]
    assert (flat == [128, 128, 255]).all(), "flat column must be a neutral normal"
    egg = slice(int(ORN_EGG[0] * W), int(ORN_EGG[1] * W))
    inner = np.abs(np.diff(height[:, egg], axis=0)).max()
    assert np.abs(height[0, egg] - height[-1, egg]).max() <= inner + 1e-9, "must tile along the run (no step at the wrap)"
    assert height[:, egg].max() > 0.2 and img[:, egg, 0].std() > 5, "egg-and-dart relief missing"
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        out = "P:/FoA-Assets/procedural"
        Image.fromarray(bake()[0], "RGB").save(f"{out}/T_TrimOrnament_N.png")
        Image.fromarray(np.round(bake_mask() * 255).astype(np.uint8), "RGB").save(f"{out}/T_TrimPaint_Mask.png")
        print("written", out, "T_TrimOrnament_N.png T_TrimPaint_Mask.png")
