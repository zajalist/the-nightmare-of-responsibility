"""Source files for the sand VFX (Tools/Unreal/build_vfx.py imports them into /Game/FoA/VFX).

  python Tools/Unreal/make_vfx_sources.py [out_dir]     (default P:/FoA-Assets/vfx)
  python Tools/Unreal/make_vfx_sources.py --selftest

- T_VFX_Noise.png  256x256 RGB, tiles seamlessly, each channel equalized to a uniform 0..1 histogram (so a threshold
                   t hides exactly a fraction t). R = per-texel grain, G = medium blobs (~16 px), B = large soft (~64 px).
                   Import sRGB off, uncompressed (BC1 would mix the three independent channels).
- SM_SandFall.gltf open 8-sided tube, 1 cm radius, 100 cm long hanging DOWN from its pivot (the pour point).
                   UV0 = (around 0..1, along 0 top .. 1 bottom). M_SandFall sets the real width with WPO.
"""
import math
import os
import random
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_procedural_meshes import write_gltf  # noqa: E402  (same Unreal-space -> glTF writer as the trims)

SIZE = 256


def value_noise(cells, seed):
    """Tileable smooth value noise, SIZE x SIZE, `cells` lattice cells per side."""
    rnd = random.Random(seed)
    lat = [[rnd.random() for _ in range(cells)] for _ in range(cells)]
    out = []
    for y in range(SIZE):
        fy = y * cells / SIZE
        y0 = int(fy)
        sy = (fy - y0) ** 2 * (3 - 2 * (fy - y0))
        r0, r1 = lat[y0 % cells], lat[(y0 + 1) % cells]
        row = []
        for x in range(SIZE):
            fx = x * cells / SIZE
            x0 = int(fx)
            sx = (fx - x0) ** 2 * (3 - 2 * (fx - x0))
            x1 = (x0 + 1) % cells
            a = r0[x0 % cells] + (r0[x1] - r0[x0 % cells]) * sx
            b = r1[x0 % cells] + (r1[x1] - r1[x0 % cells]) * sx
            row.append(a + (b - a) * sy)
        out.append(row)
    return out


def fbm(octaves, seed):
    layers = [(value_noise(c, seed + i), w) for i, (c, w) in enumerate(octaves)]
    return [[sum(l[y][x] * w for l, w in layers) for x in range(SIZE)] for y in range(SIZE)]


def equalize(img):
    """Rank-remap to a uniform histogram: thresholds then cover area linearly."""
    flat = sorted((v, i) for i, v in enumerate(p for row in img for p in row))
    out = [0.0] * len(flat)
    for rank, (_, i) in enumerate(flat):
        out[i] = rank / (len(flat) - 1)
    return [out[y * SIZE:(y + 1) * SIZE] for y in range(SIZE)]


def noise_channels():
    grain = equalize(value_noise(SIZE, 101))                     # one random value per texel
    blobs = equalize(fbm([(16, 1.0), (32, 0.5), (64, 0.25)], 202))
    broad = equalize(fbm([(4, 1.0), (8, 0.5), (16, 0.25)], 303))
    return grain, blobs, broad


def write_png(path, r, g, b):
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)
        for x in range(SIZE):
            raw += bytes((round(r[y][x] * 255), round(g[y][x] * 255), round(b[y][x] * 255)))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def sand_tube(sides=8, rows=32, radius=1.0, length=100.0):
    pos, nrm, uv, tris = [], [], [], []
    for k in range(rows + 1):
        for j in range(sides + 1):  # seam column duplicated so U runs 0..1
            a = 2 * math.pi * j / sides
            pos.append((radius * math.cos(a), radius * math.sin(a), -length * k / rows))
            nrm.append((math.cos(a), math.sin(a), 0.0))
            uv.append((j / sides, k / rows))
    w = sides + 1
    for k in range(rows):
        for j in range(sides):
            a, b, c, d = k * w + j, k * w + j + 1, (k + 1) * w + j + 1, (k + 1) * w + j
            tris += [(a, d, c), (a, c, b)]
    return pos, nrm, uv, tris


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    write_png(os.path.join(out_dir, "T_VFX_Noise.png"), *noise_channels())
    write_gltf(os.path.join(out_dir, "SM_SandFall.gltf"), sand_tube(), "SM_SandFall")


def selftest():
    for name, ch in zip("RGB", noise_channels()):
        flat = [p for row in ch for p in row]
        assert min(flat) == 0.0 and max(flat) == 1.0 and abs(sum(flat) / len(flat) - 0.5) < 1e-3, name
        if name != "R":  # smooth channels must wrap: last row/column continue into the first
            seam = sum(abs(ch[0][x] - ch[-1][x]) + abs(ch[x][0] - ch[x][-1]) for x in range(SIZE)) / (2 * SIZE)
            inner = sum(abs(ch[100][x] - ch[101][x]) for x in range(SIZE)) / SIZE
            assert seam < 3 * inner + 0.02, (name, seam, inner)
    pos, nrm, uv, tris = sand_tube()
    assert len(pos) == 33 * 9 and len(tris) == 2 * 32 * 8 and all(0 <= i < len(pos) for t in tris for i in t)
    assert max(p[2] for p in pos) == 0.0 and min(p[2] for p in pos) == -100.0
    assert uv[0] == (0.0, 0.0) and uv[-1] == (1.0, 1.0)
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        out = sys.argv[1] if len(sys.argv) > 1 else "P:/FoA-Assets/vfx"
        build(out)
        print("written", out)
