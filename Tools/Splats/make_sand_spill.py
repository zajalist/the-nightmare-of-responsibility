"""Floor sand as SPILLS (the sand direction page, Nov 5): thin opaque meshes lying in the floor, not mounds.
Each spill is a height field over the floor: a few soft lobes warped by slow noise, viscous fingers at the rim, fine
relief and wet rivulets on top, a few centimetres thick at most, feathering to nothing at the rim. Port of the
prototype's field() / H() (scratchpad sand_direction/index.html) to numpy, in Unreal cm.

  python Tools/Splats/make_sand_spill.py [--selftest]   ->  P:/FoA-Assets/procedural/SM_SandSpill_{Path,Hearth,Bay}.gltf

Vertex colour feeds M_SandSpill: R = sand body (0 loose band .. 1 solid), G = wet strand (smoother, rim-lit),
B = 0, A = feather (the material keeps a 1.1 mm grain cell while A beats its hash: the rim dissolves into loose grains
and a dark contact band on the boards). Triangles where the whole cell is below the loose band are dropped.
Pivot = the spill's centre on the floor (z 0); the sheet sits 0.12 cm above the boards."""
import array
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ply_to_splatmesh import gltf_doc  # noqa: E402

OUT = "P:/FoA-Assets/procedural"
CELL = 1.5          # grid spacing, cm
THICK = 2.6         # body thickness at the fullest, cm
LIFT = 0.12         # above the boards, cm
# name: (seed, radius cm, (x stretch, y stretch), centre shift cm): sized to where each spill lies in the room
# Path: its body lies in the moonlight strip; a neck and a second lobe reach +x into the ThirdPerson camera's view
# (extra lobes: centre and half-size in units of R in the unstretched frame, weight).
EXTRA = {"SM_SandSpill_Path": [((1.25, 0.45), (0.45, 0.22), 0.9), ((2.2, 0.85), (0.5, 0.35), 1.0)]}
SPILLS = {"SM_SandSpill_Path": (11, 105.0, (1.0, 0.8), (0.0, 0.0)),
          "SM_SandSpill_Hearth": (12, 90.0, (0.9, 1.0), (0.0, 0.0)),
          "SM_SandSpill_Bay": (13, 80.0, (1.0, 0.55), (0.0, 25.0)),   # the alcove is 180 x 90 cm: wide and shallow
          "SM_SandSpill_Pour": (14, 45.0, (1.0, 0.8), (0.0, -10.0))}  # under the commode pour: its impact pile grows out of it


def h1(p):  # the prototype's hash: p = fract(p * (.1031, .1030)); p += dot(p, p.yx + 33.33); fract((p.x + p.y) * p.x)
    p = np.mod(p * np.array([0.1031, 0.1030]), 1.0)
    p = p + (p * (p[..., ::-1] + 33.33)).sum(-1, keepdims=True)
    return np.mod((p[..., 0] + p[..., 1]) * p[..., 0], 1.0)


def vn(p):
    i, f = np.floor(p), p - np.floor(p)
    f = f * f * (3.0 - 2.0 * f)
    a, b = h1(i), h1(i + [1.0, 0.0])
    c, d = h1(i + [0.0, 1.0]), h1(i + [1.0, 1.0])
    return (a + (b - a) * f[..., 0]) + ((c + (d - c) * f[..., 0]) - (a + (b - a) * f[..., 0])) * f[..., 1]


def fbm(p):
    s, a = 0.0, 0.5
    for _ in range(5):
        s = s + a * vn(p)
        p = p * 2.02 + 11.7
        a *= 0.5
    return s


def field(p, lobes, R):
    """p in cm (spill-local). Lobes are (centre, half-size, weight) in units of R; >0.42 = sand, 0.22-0.42 = loose."""
    m = p / 100.0
    w = np.stack([fbm(m * 1.6), fbm(m * 1.6 + [5.2, 0.0])], -1) - 0.5
    q = p / R + w * 0.55
    f = np.zeros(p.shape[:-1])
    for c, s, k in lobes:
        d = (q - c) / s
        f += k * np.exp(-(d * d).sum(-1))
    r, ang = np.linalg.norm(q, axis=-1), np.arctan2(q[..., 1], q[..., 0])
    tongues = np.abs(np.sin(ang * 4.0 + fbm(q * 1.5) * 6.0)) ** 6 * 0.32 * np.clip((r - 0.25) / 0.5, 0, 1) * np.clip((1.3 - r) / 0.3, 0, 1)
    return f + (fbm(q * 4.5) - 0.5) * 0.7 + tongues                  # viscous fingers and tongues at the rim


def build(name, seed, R, stretch, shift):
    rng = np.random.default_rng(seed)
    lobes = [(np.array([0.0, 0.0]), np.array([0.62, 0.40]), 1.0)]
    for k in range(3):
        a = rng.uniform(0, 2 * np.pi)
        lobes.append((np.array([np.cos(a), np.sin(a)]) * rng.uniform(0.35, 0.6), rng.uniform([0.24, 0.18], [0.38, 0.30]), rng.uniform(0.65, 0.85)))
    lobes += [(np.array(c), np.array(sz), k) for c, sz, k in EXTRA.get(name, [])]
    sx, sy = stretch
    lo = np.min([c - 2.0 * sz for c, sz, _ in lobes] + [np.array([-1.2, -1.2])], 0) * R    # grid box over every lobe
    hi = np.max([c + 2.0 * sz for c, sz, _ in lobes] + [np.array([1.2, 1.2])], 0) * R
    us = np.arange(lo[0], hi[0], CELL)
    vs = np.arange(lo[1], hi[1], CELL)
    U, Vv = np.meshgrid(us, vs, indexing="ij")
    X, Y = U * sx + shift[0], Vv * sy + shift[1]
    P = np.stack([X, Y], -1)
    loc = np.stack([U, Vv], -1)                                        # the field lives in the unstretched frame
    edge = np.minimum(np.minimum(U - lo[0], hi[0] - U), np.minimum(Vv - lo[1], hi[1] - Vv))
    f = field(loc, lobes, R) - 0.6 * np.clip((30.0 - edge) / 30.0, 0, 1)    # nothing reaches the grid's edge
    m = P / 100.0
    sand = np.clip((f - 0.42) / 0.2, 0, 1) ** 2 * (3 - 2 * np.clip((f - 0.42) / 0.2, 0, 1))
    body = np.clip((f - 0.42) / 0.63, 0, 1)
    body = body * body * (3 - 2 * body)
    relief = (fbm(m * 22.0) - 0.5) * 0.4 * np.clip((f - 0.45) / 0.35, 0, 1)
    sd = 1.0 - np.abs(np.sin((m[..., 0] * 0.8 + m[..., 1] * 0.6) * 70.0 + fbm(m * 4.0) * 9.0))
    band = np.clip((f - 0.35) / 0.2, 0, 1) * (1.0 - np.clip((f - 0.75) / 0.25, 0, 1))
    strand = sd ** 8 * band
    Z = LIFT + body * THICK + relief + strand * 0.25
    feather = np.clip((f - 0.2) / 0.3, 0, 1)
    # normals from the height field (UE space, z up)
    gx = np.gradient(Z, CELL * sx, axis=0)
    gy = np.gradient(Z, CELL * sy, axis=1)                             # (grid spacing in world cm along each axis)
    N = np.stack([-gx, -gy, np.ones_like(Z)], -1)
    N /= np.linalg.norm(N, axis=-1, keepdims=True)
    # cells kept where any corner reaches the loose band
    keep = feather > 0.0
    cell = keep[:-1, :-1] | keep[1:, :-1] | keep[:-1, 1:] | keep[1:, 1:]
    used = np.zeros_like(keep)
    used[:-1, :-1] |= cell
    used[1:, :-1] |= cell
    used[:-1, 1:] |= cell
    used[1:, 1:] |= cell
    ids = -np.ones(Z.shape, int)
    ids[used] = np.arange(used.sum())
    pos = np.stack([X, Y, Z], -1)[used]
    nrm = N[used]
    col = np.stack([sand, strand, np.zeros_like(Z), feather], -1)[used]
    tris = []
    ci, cj = np.nonzero(cell)
    a, b, c, d = ids[ci, cj], ids[ci + 1, cj], ids[ci, cj + 1], ids[ci + 1, cj + 1]
    tris = np.concatenate([np.stack([a, b, d], -1), np.stack([a, d, c], -1)])
    # glTF: metres, Y up, (x, z, y); front faces counter-clockwise, oriented to the +Z (up) normal
    g = np.stack([pos[:, 0], pos[:, 2], pos[:, 1]], -1) / 100.0
    gn = np.stack([nrm[:, 0], nrm[:, 2], nrm[:, 1]], -1)
    cr = np.cross(g[tris[:, 1]] - g[tris[:, 0]], g[tris[:, 2]] - g[tris[:, 0]])
    flip = (cr * gn[tris].sum(1)).sum(-1) < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    uv = np.stack([pos[:, 0], pos[:, 1]], -1) / 100.0               # metres: tiles for any texture use
    A = {"POSITION": array.array("f", g.astype(np.float32).ravel()), "NORMAL": array.array("f", gn.astype(np.float32).ravel()),
         "TEXCOORD_0": array.array("f", uv.astype(np.float32).ravel()), "COLOR_0": array.array("f", col.astype(np.float32).ravel())}
    doc, blob = gltf_doc(A, array.array("I", tris.astype(np.uint32).ravel()), name)
    doc["asset"]["generator"] = "FoA make_sand_spill.py"
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/{name}.bin", "wb") as fh:
        fh.write(blob)
    with open(f"{OUT}/{name}.gltf", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    info = {"verts": int(len(pos)), "tris": int(len(tris)), "max_height_cm": round(float(Z[used].max()), 2),
            "extent_cm": [round(float(pos[:, k].min()), 1) for k in (0, 1)] + [round(float(pos[:, k].max()), 1) for k in (0, 1)],
            "sand_share": round(float((col[:, 0] > 0.5).mean()), 3)}
    print(name, info)
    return pos, col, tris, info


def crumbs(name, pos, col, n=1500, seed=5):
    """Loose grains around a spill's rim as a splat mesh (the direction page: splats only where sand is loose, 0.5-2 px
    at 1080p). Sampled from the spill's own vertices in the loose band (feather between 0.05 and 0.6), jittered off
    the grid, on the boards. Role 2 = creep (M_SplatMesh mound mode): they inch along the floor."""
    import random
    from make_sand_splats import Splats, logu
    rng = random.Random(seed)
    band = np.nonzero((col[:, 3] > 0.05) & (col[:, 3] < 0.6))[0]
    s = Splats(rng)
    for i in rng.sample(list(band), min(n, len(band))):
        x, y = pos[i, 0] + rng.uniform(-CELL, CELL), pos[i, 1] + rng.uniform(-CELL, CELL)
        s.add(2, [x, y, LIFT + 0.08], logu(rng, 0.05, 0.12), 0.1, 0.9)
    s.write("P:/FoA-Assets/splatmesh", name.replace("SM_SandSpill_", "SM_SandCrumbs_"), {"spill": name})
    print("crumbs", name, len(s.rows))


def selftest():
    p = np.random.default_rng(0).uniform(-300, 300, (1000, 2))
    v = vn(p / 10.0)
    assert v.min() >= 0.0 and v.max() <= 1.0, "value noise in [0, 1]"
    pos, col, tris, info = build("SM_SandSpill_Test", 1, 60.0, (1.0, 1.0), (0.0, 0.0))
    assert info["max_height_cm"] <= LIFT + THICK + 0.7, "a few centimetres thick at most"
    assert 0.1 < info["sand_share"] < 0.9, "a body plus a loose rim"
    assert (col[:, 3] >= 0).all() and (col[:, 3] <= 1).all()
    for ext in (".gltf", ".bin"):
        os.remove(f"{OUT}/SM_SandSpill_Test{ext}")
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        for name, (seed, R, st, sh) in SPILLS.items():
            pos, col, _, _ = build(name, seed, R, st, sh)
            crumbs(name, pos, col)
