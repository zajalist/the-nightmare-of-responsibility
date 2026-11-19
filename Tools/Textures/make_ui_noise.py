"""T_UI_SandNoise: 256x256 tileable RGBA noise pack for the UI sand materials (procedural, CC0 by construction).
R = sparse sand specks (clump-weighted), G = grain clumps, B = smooth fBm (dissolve thresholds), A = vertical drip streaks.
usage: python make_ui_noise.py <out.png>"""
import sys
import numpy as np
from PIL import Image

N = 256
rng = np.random.default_rng(18)  # Day 18


def band(lo, hi):
    """Tileable noise: white noise filtered to a radial frequency band in Fourier space (periodic by construction)."""
    f = np.fft.fftfreq(N)
    r = np.hypot(*np.meshgrid(f, f))
    spec = np.fft.fft2(rng.standard_normal((N, N))) * ((r >= lo) & (r <= hi))
    x = np.real(np.fft.ifft2(spec))
    return (x - x.min()) / (x.max() - x.min())


def stretch(x, lo=2, hi=98):
    a, b = np.percentile(x, [lo, hi])
    return np.clip((x - a) / (b - a), 0, 1)


clumps = stretch(band(0.03, 0.09) * 0.7 + band(0.1, 0.2) * 0.3)      # sand clusters
# Sparse 1-2 px sand specks whose density follows the clumps (so R alone reads as sand, no mixing in shader).
p_speck = 0.03 + 0.22 * clumps ** 2
specks = (rng.random((N, N)) < p_speck) * (0.45 + 0.55 * rng.random((N, N)))
soft = np.real(np.fft.ifft2(np.fft.fft2(specks) * np.fft.fft2(np.roll(np.roll(
    np.pad([[0.05, 0.1, 0.05], [0.1, 0.4, 0.1], [0.05, 0.1, 0.05]], ((0, N - 3), (0, N - 3))), -1, 0), -1, 1))))
grain = np.clip(soft / np.percentile(soft, 99.7), 0, 1)              # tileable 3x3 soften (periodic convolution)
# Octave o covers 2^-(o+2)..2^-(o+1) cycles/px; low octaves weigh most so dissolve edges stay organic.
fbm = stretch(sum(band(1 / 2 ** (o + 2), 1 / 2 ** (o + 1)) * w for o, w in enumerate((0.12, 0.25, 0.5, 1.0, 1.0))))
# Drips: per-column random streak lengths, smeared vertically, tileable on both axes.
cols = band(0.02, 0.12)[0]  # one smooth row decides where streaks run
streak = np.zeros((N, N))
for x in range(N):
    if cols[x] > 0.55:
        y0, length = rng.integers(0, N), int(24 + 140 * (cols[x] - 0.55) / 0.45)
        ys = (y0 + np.arange(length)) % N
        streak[ys, x] = np.linspace(1, 0, length) ** 1.5
drip = stretch(np.maximum(streak, 0) * (0.6 + 0.4 * grain), 0, 99.5)
rgba = (np.stack([grain, clumps, fbm, drip], -1) * 255 + 0.5).astype(np.uint8)
Image.fromarray(rgba, "RGBA").save(sys.argv[1])
assert rgba.shape == (N, N, 4) and rgba[..., 3].max() > 200 and rgba[..., 2].std() > 30
print("wrote", sys.argv[1])
