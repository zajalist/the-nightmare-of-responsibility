"""Sand morph stations (BP_SandMorph): one splat mesh per station whose splats flow between the shapes of a chain of
Lux3D objects, rising out of the sand, holding, flowing into the next object and finally slumping back.
Each splat's position in every shape lives in a small float texture (T_SandMorph_<station>: rows of 128 x 128 texels
per shape, xyz in metres, splat-local); the mesh carries the splat index in TEXCOORD_2.x and its rest position is the
first shape (the sand it rises from). Splats are paired across shapes coherently, by height band then angle around the
axis, so a morph reads as sand flowing up, around and over, never as random teleporting.
  python Tools/Splats/make_sand_morph.py [--selftest]
  -> P:/FoA-Assets/splatmesh/SM_SandMorph_<station>.gltf/.bin + P:/FoA-Assets/procedural/T_SandMorph_<station>.exr
     + P:/FoA-Assets/splatmesh/sand_morph_params.json (the rows and heights M_SplatMesh's morph needs)"""
import array
import json
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ply_to_splatmesh import CORNER_UV, NUDGE_M, gltf_doc, parse_ply, select, to_gltf  # noqa: E402

LUX = "P:/FoA-Assets/lux3d"
OUT_MESH = "P:/FoA-Assets/splatmesh"
OUT_TEX = "P:/FoA-Assets/procedural"
SIDE = 128                          # texels per side of one shape's block: SIDE^2 splats per station
N = SIDE * SIDE
# station: (object chain after the sand row, object size cm (largest dimension), sand row (radius cm, height cm))
STATIONS = {
    "Commode": (["alarm_clock_splat", "necktie_serpent", "the_shirt_enemy", "door_key", "wire_hanger"], 26.0, (18.0, 4.0)),
    "Desk": (["unpaid_bills", "glass_of_water", "bedside_book_stack", "sand_hourglass"], 20.0, (16.0, 3.0)),
    "Floor": (["sand_hand", "sand_crow", "melting_calendar", "heavy_hood"], 50.0, (35.0, 3.0)),
}


def points(name, n, rng):
    """n surface points of a Lux3D object in Unreal space (cm, z up): splat centres weighted by opacity x area, or
    an area-weighted sample of the textured mesh."""
    ply, glb = f"{LUX}/{name}/gaussian.ply", f"{LUX}/{name}/textured.glb"
    if os.path.exists(ply):
        data = open(ply, "rb").read()
        cnt, cols, sh = parse_ply(data)
        kept, _, _, _ = select(cnt, cols, sh, n, 1)
        g = np.array([to_gltf(cols["x"][i], cols["y"][i], cols["z"][i]) for i in kept])
    else:
        import trimesh
        m = trimesh.load(glb, force="mesh")
        g, _ = trimesh.sample.sample_surface(m, n, seed=int(rng.integers(1 << 30)))
        g = np.asarray(g)
    p = np.stack([g[:, 0], g[:, 2], g[:, 1]], 1) * 100.0       # glTF metres (y up) -> Unreal cm (z up)
    if len(p) < n:                                                 # a sparse capture: repeat with a little jitter
        extra = p[rng.integers(0, len(p), n - len(p))] + rng.normal(0, 0.05, (n - len(p), 3))
        p = np.concatenate([p, extra])
    return p[:n]


def fit(p, size):
    """Centre on the floor (base at z 0, axis through the xy centre) and scale so the largest dimension is size cm
    (a key stays key-shaped instead of being stretched to a clock's height)."""
    lo, hi = p.min(0), p.max(0)
    p = p - [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]
    return p * (size / max(np.ptp(p, 0).max(), 1e-3))


def sand_row(n, radius, height, rng):
    """The sand the objects rise from and slump back into: a low dome of radius cm and height cm."""
    r = radius * np.sqrt(rng.random(n))
    a = rng.random(n) * 2 * math.pi
    z = height * (1 - (r / radius) ** 2) ** 1.5 * rng.random(n) ** 0.3
    return np.stack([r * np.cos(a), r * np.sin(a), z], 1)


def order(p):
    """Coherent pairing order: 48 height bands bottom to top, then angle around the vertical axis."""
    z = (p[:, 2] - p[:, 2].min()) / max(np.ptp(p[:, 2]), 1e-3)
    ang = np.arctan2(p[:, 1], p[:, 0])
    return np.lexsort((ang, np.floor(z * 48)))


def build(station, chain, height, sand, seed):
    rng = np.random.default_rng(seed)
    shapes = [sand_row(N, *sand, rng)] + [fit(points(o, N, rng), height) for o in chain]
    rows = [s[order(s)] for s in shapes]                           # row k, index i: the same splat in every shape
    tex = np.zeros((SIDE * len(rows), SIDE, 4), np.float32)
    for k, r in enumerate(rows):
        tex[k * SIDE:(k + 1) * SIDE, :, :3] = (r / 100.0).reshape(SIDE, SIDE, 3)   # metres
        tex[k * SIDE:(k + 1) * SIDE, :, 3] = 1.0
    import imageio.v3 as iio
    os.makedirs(OUT_TEX, exist_ok=True)
    iio.imwrite(f"{OUT_TEX}/T_SandMorph_{station}.exr", tex, extension=".exr")
    # the mesh: one quad per splat at its sand-row position; TEXCOORD_2.x = its index into the texture
    rest = rows[0]
    py = random.Random(seed)
    A = {k: array.array("f") for k in ("POSITION", "NORMAL", "TANGENT", "COLOR_0") + tuple(f"TEXCOORD_{t}" for t in range(8))}
    idx, e = array.array("I"), NUDGE_M
    for i, (x, y, z) in enumerate(rest):
        cx, cy, cz = x / 100.0, z / 100.0, y / 100.0
        A["POSITION"].extend((cx - e, cy - e, cz, cx + e, cy - e, cz, cx + e, cy + e, cz, cx - e, cy + e, cz))
        A["NORMAL"].extend((0.0, 1.0, 0.0) * 4)                      # up: the morph material brings its own normals
        A["TANGENT"].extend((1.0, 0.0, 0.0, 1.0) * 4)
        A["TEXCOORD_0"].extend(CORNER_UV)
        radius = 0.35 * (0.7 + 0.6 * py.random()) * height / 22.0
        A["TEXCOORD_1"].extend((radius, min(max(py.random(), 0.001), 0.999) / 4.0) * 4)   # role 0, (role + u) / 4
        A["TEXCOORD_2"].extend((float(i), 0.0) * 4)
        for t in (3, 4, 5, 6, 7):
            A[f"TEXCOORD_{t}"].extend((0.0, 0.0) * 4)
        A["COLOR_0"].extend((0.1, 0.1, 0.1, 0.95) * 4)
        b = 4 * i
        idx.extend((b, b + 1, b + 2, b, b + 2, b + 3))
    name = f"SM_SandMorph_{station}"
    doc, blob = gltf_doc(A, idx, name)
    with open(f"{OUT_MESH}/{name}.bin", "wb") as fh:
        fh.write(blob)
    with open(f"{OUT_MESH}/{name}.gltf", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    span = max(float(np.abs(r[:, :2]).max()) for r in rows)
    info = {"rows": ["sand"] + chain, "side": SIDE, "splats": N, "height_cm": height, "half_extent_cm": round(span, 1),
            "top_cm": round(max(float(r[:, 2].max()) for r in rows), 1)}
    print(station, info)
    return rows, info


def selftest():
    rng = np.random.default_rng(0)
    s = sand_row(1000, 18.0, 4.0, rng)
    assert (s[:, 2] >= 0).all() and (s[:, 2] <= 4.0 + 1e-6).all() and np.hypot(s[:, 0], s[:, 1]).max() <= 18.0
    p = fit(rng.normal(size=(500, 3)) * [3, 3, 10] + [5, 5, 50], 22.0)
    assert abs(p[:, 2].min()) < 1e-6 and abs(np.ptp(p, 0).max() - 22.0) < 1e-6
    o = order(p)
    assert sorted(o.tolist()) == list(range(500)), "a permutation"
    zb = np.floor((p[o, 2] - p[:, 2].min()) / np.ptp(p[:, 2]) * 48)
    assert (np.diff(zb) >= 0).all(), "bottom to top"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        params = {}
        for k, (station, (chain, h, sand)) in enumerate(STATIONS.items()):
            params[station] = build(station, chain, h, sand, 100 + k)[1]
        json.dump(params, open(f"{OUT_MESH}/sand_morph_params.json", "w"), indent=1)
