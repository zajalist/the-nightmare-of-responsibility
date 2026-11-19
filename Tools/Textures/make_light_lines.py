"""Generates T_Lines: a 128x1024 light-shaft band texture (one independent band pattern per RGB channel).

  python Tools/Textures/make_light_lines.py [out.png]     (default P:/FoA-Assets/procedural/T_Lines.png)
  python Tools/Textures/make_light_lines.py --selftest

Bands vary along V (1024 rows) and are constant along U, and they wrap seamlessly so the material can pan them.
Each channel is a sum of soft random stripes with its own density and width, so mixing two channels at different
pan speeds never visibly repeats. Import with sRGB off, compression Default (DXT1 ~64 KB).
"""
import math
import os
import random
import struct
import sys
import zlib

W, H = 128, 1024


def channel(seed, stripes, min_w, max_w, floor=0.05):
    rnd = random.Random(seed)
    row = [0.0] * H
    for _ in range(stripes):
        center, width, amp = rnd.uniform(0, H), rnd.uniform(min_w, max_w), rnd.uniform(0.3, 1.0)
        for y in range(H):
            d = min(abs(y - center), H - abs(y - center))  # wrap-around distance, keeps the texture tileable
            row[y] += amp * math.exp(-0.5 * (d / width) ** 2)
    peak = max(row) or 1.0
    return [min(1.0, floor + (1 - floor) * (v / peak) ** 1.2) for v in row]


def build():
    r = channel(11, 26, 4, 22)    # many thin streaks
    g = channel(23, 12, 10, 45)   # medium beams
    b = channel(37, 6, 30, 90)    # broad soft bands
    return r, g, b


def write_png(path, r, g, b):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        px = bytes((round(r[y] * 255), round(g[y] * 255), round(b[y] * 255)))
        raw += px * W
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)


def selftest():
    r, g, b = build()
    for c in (r, g, b):
        assert len(c) == H and 0.0 <= min(c) and max(c) <= 1.0
        assert max(c) - min(c) > 0.5, "channel has no contrast"
        assert abs(c[0] - c[-1]) < 0.2, "channel does not wrap"
    assert sum(abs(x - y) for x, y in zip(r, g)) > 50, "channels must differ"
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        out = sys.argv[1] if len(sys.argv) > 1 else "P:/FoA-Assets/procedural/T_Lines.png"
        write_png(out, *build())
        print("written", out)
