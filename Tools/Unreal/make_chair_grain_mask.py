"""Offline (system Python + PIL): per-UV-island grain rotation mask for painted_wooden_chair_01, for M_PropWood.
  python Tools/Unreal/make_chair_grain_mask.py  ->  P:/FoA-Assets/procedural/T_Chair_GrainRot.png (256 px, 255 = rotate 90 deg)
walnut_veneer_02's grain runs along U, so UV islands that are long along V (legs, posts) are flagged and M_PropWood swaps
the wood UV there; the flags are dilated into the gutters because the mask is sampled with nearest filtering, no mips."""
import json
import struct

import numpy as np
from PIL import Image, ImageDraw

ROOT = "P:/FoA-Assets/polyhaven/models/painted_wooden_chair_01/"
OUT = "P:/FoA-Assets/procedural/T_Chair_GrainRot.png"
RES = 256


def main():
    g = json.load(open(ROOT + "painted_wooden_chair_01_1k.gltf"))
    buf = open(ROOT + g["buffers"][0]["uri"], "rb").read()

    def read(ai):
        a = g["accessors"][ai]
        bv = g["bufferViews"][a["bufferView"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5125: "I"}[a["componentType"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", struct.calcsize(fmt) * n)
        return [struct.unpack_from("<" + fmt * n, buf, off + i * stride) for i in range(a["count"])]

    prim = g["meshes"][0]["primitives"][0]
    uv = read(prim["attributes"]["TEXCOORD_0"])
    idx = [i[0] for i in read(prim["indices"])]
    par = list(range(len(uv)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    seen = {}
    for i, c in enumerate(uv):  # vertices split at hard edges but sharing a UV belong to one island
        k = (round(c[0], 4), round(c[1], 4))
        if k in seen:
            par[find(i)] = find(seen[k])
        else:
            seen[k] = i
    tris = [idx[t:t + 3] for t in range(0, len(idx), 3)]
    for a, b, c in tris:
        par[find(a)] = find(b)
        par[find(b)] = find(c)
    islands = {}
    for t in tris:
        islands.setdefault(find(t[0]), []).append(t)
    mask, filled = Image.new("L", (RES, RES), 0), Image.new("L", (RES, RES), 0)
    dm, df = ImageDraw.Draw(mask), ImageDraw.Draw(filled)
    for ts in islands.values():
        us = [uv[v][0] for t in ts for v in t]
        vs = [uv[v][1] for t in ts for v in t]
        flag = 255 if (max(vs) - min(vs)) > 1.25 * (max(us) - min(us)) else 0
        for t in ts:
            poly = [(uv[v][0] * RES, uv[v][1] * RES) for v in t]
            dm.polygon(poly, fill=flag)
            df.polygon(poly, fill=255)
    m, fl = np.asarray(mask).copy(), np.asarray(filled) > 0
    for _ in range(4):
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            take = ~fl & np.roll(fl, (dy, dx), (0, 1))
            m[take] = np.roll(m, (dy, dx), (0, 1))[take]
            fl = fl | take
    assert len(islands) > 10 and 0 < (m > 127).mean() < 1, "unexpected UV layout"
    Image.fromarray(m).save(OUT)
    print(OUT, len(islands), "islands")


if __name__ == "__main__":
    main()
