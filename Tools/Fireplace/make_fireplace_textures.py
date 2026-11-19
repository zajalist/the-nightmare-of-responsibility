"""Generated (CC0, ours) textures for the bedroom fireplace.

  python Tools/Fireplace/make_fireplace_textures.py [out_dir]     (default P:/FoA-Assets/procedural/fireplace)
  python Tools/Fireplace/make_fireplace_textures.py --selftest

- T_FP_Hearth_{BaseColor,Normal,Roughness}: encaustic hearth tiles, unique over the 136 x 41.2 cm tile field
  (u along the wall, v = depth, image row 0 = back edge against the insert). 2048 x 512 px = 1506 x 1243 px/m.
  Black border, buff fillet, a 45-degree black/terracotta field of 6.7 cm tiles; soot and ash near the opening.
- T_FP_Grunge (linear RGB, tiles every 1 m = 1024 px/m): R casting pits, G dirt blotches, B vertical brush streaks.
- T_FP_GrungeNormal: normal map of the pits and brush ridges.
- T_FP_IronNormal: pits and isotropic grain only, for the iron, cinders and slate (no streaks).
- T_FP_White: 4 x 4 white, the default for grayscale texture parameters.
- T_FP_MaskNeutral: 4 x 4 (AO 1, no wear, no grime, no stain), the default for the baked-mask parameter.
- T_FP_Mask_* (baked by build_fireplace_blender.py on UV1): R AO, G wear, B grime, A 1 - smoke stain.
Normals use the DirectX convention (green = down), which Unreal expects.
"""
import os
import sys

import numpy as np
from PIL import Image

FIELD_W, FIELD_D = 136.0, 41.2           # cm, the tile field inside the slate kerb
BORDER, FILLET_D = 5.2, 1.2              # black border band, buff fillet (back/front)
HALF_DIAG = (FIELD_D - 2 * (BORDER + FILLET_D)) / 6   # 6 half-diagonals fill the field depth exactly
GROUT, ROUND, DEPTH = 0.11, 0.12, 0.15   # cm: grout half-width, tile edge round-over, grout depth


def noise(shape, sigma, seed):
    """Periodic Gaussian-filtered noise in [0, 1]; sigma is (rows, cols) in px."""
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal(shape))
    ky = np.fft.fftfreq(shape[0])[:, None]
    kx = np.fft.fftfreq(shape[1])[None, :]
    f *= np.exp(-2 * np.pi ** 2 * ((sigma[0] * ky) ** 2 + (sigma[1] * kx) ** 2))
    n = np.real(np.fft.ifft2(f))
    return (n - n.min()) / (np.ptp(n) or 1.0)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def tile_hash(tid, k):
    return np.modf(np.abs(np.sin(tid * 12.9898 + k * 78.233)) * 43758.5453)[0]


def strip(X, Y, rect, along, seg, centre):
    """Tiles laid in a rectangular strip: (mask, distance to own tile edge, tile index along the strip)."""
    x0, x1, y0, y1 = rect
    m = (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)
    t = ((X if along == "x" else Y) - centre) / seg + 0.5
    f = t - np.floor(t)
    d = np.minimum.reduce([X - x0, x1 - X, Y - y0, y1 - Y, seg * f, seg * (1 - f)])
    return m, d, np.floor(t)


def hearth_maps(W=2048, H=512, ss=2):
    w, h = W * ss, H * ss
    X, Y = np.meshgrid((np.arange(w) + 0.5) / w * FIELD_W, (np.arange(h) + 0.5) / h * FIELD_D)
    cls = np.zeros(X.shape, np.int8)          # 0 black border, 1 buff fillet, 2 black field, 3 terracotta field
    edge = np.full(X.shape, 99.0)
    tid = np.zeros(X.shape)
    cx, cy = FIELD_W / 2, FIELD_D / 2
    fx0 = (FIELD_W - 26 * HALF_DIAG) / 2      # 26 half-diagonals across: whole/half tiles meet the fillet
    fy0 = BORDER + FILLET_D
    fx1, fy1 = FIELD_W - fx0, FIELD_D - fy0
    def lay(c, rect, along, seg, centre, sid):
        m, d, t = strip(X, Y, rect, along, seg, centre)
        cls[m], edge[m], tid[m] = c, d[m], (t * 31 + sid * 977)[m]

    W_, D_ = FIELD_W, FIELD_D
    # black border: 6" (15.2 cm) strips centred on the hearth front and back, two per side, square corners
    lay(0, (BORDER, W_ - BORDER, 0, BORDER), "x", 15.2, cx, 1)
    lay(0, (BORDER, W_ - BORDER, D_ - BORDER, D_), "x", 15.2, cx, 2)
    side = (D_ - 2 * BORDER) / 2
    lay(0, (0, BORDER, BORDER, D_ - BORDER), "y", side, cy + side / 2, 3)
    lay(0, (W_ - BORDER, W_, BORDER, D_ - BORDER), "y", side, cy + side / 2, 4)
    for j, (rx, ry) in enumerate(((0, 0), (W_ - BORDER, 0), (0, D_ - BORDER), (W_ - BORDER, D_ - BORDER))):
        lay(0, (rx, rx + BORDER, ry, ry + BORDER), "x", BORDER, rx + BORDER / 2, 5 + j)
    # buff fillet: 6" strips along front and back, one piece per side
    lay(1, (BORDER, W_ - BORDER, BORDER, fy0), "x", 15.2, cx, 11)
    lay(1, (BORDER, W_ - BORDER, fy1, D_ - BORDER), "x", 15.2, cx, 12)
    lay(1, (BORDER, fx0, fy0, fy1), "y", 99.0, cy, 13)
    lay(1, (fx1, W_ - BORDER, fy0, fy1), "y", 99.0, cy, 14)
    inf = (X >= fx0) & (X < fx1) & (Y >= fy0) & (Y < fy1)
    d2 = 2 * HALF_DIAG
    s = d2 / np.sqrt(2)
    mm, nn = (X - fx0 + Y - fy0) / d2, (X - fx0 - (Y - fy0)) / d2
    fm, fn = mm - np.floor(mm), nn - np.floor(nn)
    e = np.minimum.reduce([s * fm, s * (1 - fm), s * fn, s * (1 - fn), X - fx0, fx1 - X, Y - fy0, fy1 - Y])
    cls[inf] = (2 + (np.floor(mm) + np.floor(nn)) % 2)[inf]
    edge[inf], tid[inf] = e[inf], (np.floor(mm) * 1013 + np.floor(nn) + 50000)[inf]

    # surface: flat-topped tiles with a small round-over, bedded slightly unevenly; grout sits DEPTH below
    r1, r2, r3, r4 = (tile_hash(tid, k) for k in (1, 2, 3, 4))
    pxcm = (h / FIELD_D, w / FIELD_W)
    mottle = noise(X.shape, (0.35 * pxcm[0], 0.35 * pxcm[1]), 11)
    dirt = noise(X.shape, (6 * pxcm[0], 6 * pxcm[1]), 12)
    fine = noise(X.shape, (0.12 * pxcm[0], 0.12 * pxcm[1]), 14)
    lift = 0.05 * r1 + 0.03 * (noise(X.shape, (9 * pxcm[0], 9 * pxcm[1]), 15) - 0.5)   # cm, per tile + bedding
    height = (DEPTH + lift) * smooth(GROUT, GROUT + ROUND, edge)
    grout = 1.0 - smooth(GROUT * 0.6, GROUT * 1.4, edge)
    # damage on a few field tiles: eaten-away chipped edges, and hairline cracks
    field = cls >= 2
    corner = np.hypot(fm - np.round(r4), fn - np.round(tile_hash(tid, 6))) * s   # cm to one random corner
    chip_w = 1.0 + 1.6 * fine
    chipped = field & (r3 > 0.972) & (corner < chip_w) & (edge > GROUT)
    a = r4 * 6.283
    line = np.abs((fm - 0.5) * np.cos(a) + (fn - 0.5) * np.sin(a) + 0.06 * (fine - 0.5))
    cracked = field & (tile_hash(tid, 5) > 0.975) & (line < 0.007 + 0.005 * fine) & (edge > GROUT)
    height = np.where(chipped, height - 0.12 * np.clip(1 - corner / chip_w, 0, 1) - 0.03, height)
    height = np.where(cracked, height - 0.08, height)
    pal = np.array([[34, 32, 30], [196, 170, 128], [36, 34, 32], [138, 62, 44]], np.float64)  # sRGB
    col = pal[cls]
    col *= (0.93 + 0.14 * r1)[..., None] * (0.95 + 0.1 * mottle)[..., None] * (1.0 - 0.12 * dirt)[..., None]
    col = np.where(chipped[..., None], np.array([92.0, 84, 76]) * (0.75 + 0.5 * fine[..., None]), col)  # fired body
    col = np.where(cracked[..., None], col * 0.3, col)
    # soot and ash: heaviest at the back centre, in front of the grate
    near = np.exp(-((X - cx) / 28) ** 2) * np.exp(-Y / 11)
    col *= (1.0 - 0.6 * near * (0.6 + 0.4 * dirt))[..., None]
    ash = np.clip(near * (0.5 + 0.8 * noise(X.shape, (1.2 * pxcm[0], 1.2 * pxcm[1]), 13)) - 0.22, 0, 1) * 0.6
    col = col * (1 - ash[..., None]) + np.array([112, 108, 102]) * ash[..., None]
    col = col * (1 - grout[..., None]) + (np.array([58, 54, 50]) * (0.8 + 0.4 * dirt[..., None])) * grout[..., None]
    rough = 0.36 + 0.12 * r2 + 0.10 * mottle + 0.15 * dirt
    rough = np.where(chipped | cracked, 0.85, rough)
    rough = rough * (1 - grout) + 0.92 * grout
    rough = np.clip(rough + 0.45 * ash, 0, 1)
    damage = (np.unique(tid[chipped]).size, np.unique(tid[cracked]).size)

    def down(a):  # box-filter the supersampled maps back to W x H
        return a.reshape(H, ss, W, ss, *a.shape[2:]).mean(axis=(1, 3))

    col, rough, height = down(col), down(rough), down(height)
    gy, gx = np.gradient(height, FIELD_D / H, FIELD_W / W)  # cm per cm
    n = np.dstack([-gx, -gy, np.ones_like(gx)])            # DirectX: green follows +row (down)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return col, rough, n, cls, damage


def grunge_maps(N=1024):
    pits = noise((N, N), (1.1, 1.1), 21)
    pits = np.clip((pits - 0.35) / 0.3, 0, 1) ** 1.6                     # sparse dark pits
    dirt = 0.5 * noise((N, N), (60, 60), 22) + 0.3 * noise((N, N), (14, 14), 23) + 0.2 * noise((N, N), (4, 4), 24)
    dirt = np.clip((dirt - dirt.mean()) * 2.2 + 0.5, 0, 1)
    streak = noise((N, N), (55, 1.4), 25)                                  # long in v (rows): vertical brush marks
    streak = np.clip((streak - 0.5) * 2.5 + 0.5, 0, 1)
    rgb = np.dstack([pits, dirt, streak])
    hgt = 1.2 * pits + 0.5 * streak
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx * 1.0, -gy * 1.0, np.ones_like(gx)])  # gentle: used directly as NormalTex on paint and iron
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return rgb, n


def iron_normal(N=1024):
    """Cast-iron surface for the insert, cinders and slate: sand-casting pits and an isotropic grain, no directional
    streaks (the grunge normal's vertical brush streaks read as rain on iron)."""
    pits = np.clip((noise((N, N), (1.1, 1.1), 21) - 0.35) / 0.3, 0, 1) ** 1.6
    grain = noise((N, N), (0.7, 0.7), 26)
    hgt = 1.0 * pits + 0.35 * grain
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx * 1.5, -gy * 1.5, np.ones_like(gx)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def to8(a):
    return np.clip(np.round(a), 0, 255).astype(np.uint8)


def save(out, name, arr, mode):
    Image.fromarray(arr, mode).save(os.path.join(out, name + ".png"), optimize=True)


def build(out):
    os.makedirs(out, exist_ok=True)
    col, rough, n, _, damage = hearth_maps()
    print('chipped, cracked tiles', damage)
    save(out, "T_FP_Hearth_BaseColor", to8(col), "RGB")
    save(out, "T_FP_Hearth_Roughness", to8(rough * 255), "L")
    save(out, "T_FP_Hearth_Normal", to8((n * 0.5 + 0.5) * 255), "RGB")
    rgb, gn = grunge_maps()
    save(out, "T_FP_Grunge", to8(rgb * 255), "RGB")
    save(out, "T_FP_GrungeNormal", to8((gn * 0.5 + 0.5) * 255), "RGB")
    save(out, "T_FP_IronNormal", to8((iron_normal() * 0.5 + 0.5) * 255), "RGB")
    save(out, "T_FP_White", np.full((4, 4), 255, np.uint8), "L")  # default for grayscale texture parameters
    save(out, "T_FP_MaskNeutral", np.tile(np.array([255, 0, 0, 255], np.uint8), (4, 4, 1)), "RGBA")  # AO 1, no wear/grime/stain
    with open(os.path.join(out, "SOURCES.txt"), "w", encoding="utf-8") as fh:
        fh.write("T_FP_* textures: generated by P:/FoA/Tools/Fireplace/make_fireplace_textures.py for FoA. "
                 "Original work, no third-party content. License: CC0.\n")


def selftest():
    col, rough, n, cls, _ = hearth_maps(W=512, H=128, ss=1)
    assert col.shape == (128, 512, 3) and rough.shape == (128, 512)
    assert abs(26 * HALF_DIAG - (FIELD_W - 2 * ((FIELD_W - 26 * HALF_DIAG) / 2))) < 1e-9
    assert set(np.unique(cls)) == {0, 1, 2, 3}, np.unique(cls)
    assert cls[0, 256] == 0 and cls[64, 256] in (2, 3) and cls[-1, 256] == 0   # border, field, border
    assert np.all(np.abs(np.linalg.norm(n, axis=2) - 1) < 1e-6) and n[..., 2].min() > 0
    rgb, gn = grunge_maps(N=128)
    assert rgb.min() >= 0 and rgb.max() <= 1 and gn.shape == (128, 128, 3)
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        build(sys.argv[1] if len(sys.argv) > 1 else "P:/FoA-Assets/procedural/fireplace")
        print("written")
