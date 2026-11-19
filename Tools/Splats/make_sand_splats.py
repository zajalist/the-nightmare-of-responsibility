#!/usr/bin/env python3
r"""make_sand_splats.py - procedural black-sand splat meshes for M_SplatMesh (FoA sand VFX).

    python Tools/Splats/make_sand_splats.py [out_dir]     (default P:/FoA-Assets/splatmesh)
    python Tools/Splats/make_sand_splats.py --selftest

Writes SM_SandStream and SM_SandMoundSplats_A/B/C as <name>.gltf/.bin/.splatmesh.json in the exact channel
layout of ply_to_splatmesh.py (one camera-facing quad per splat, UV0 corner, UV1 radius_cm + seed, UV2-6 zero
SH, UV7 sigmas, COLOR_0 display grey + opacity), plus sand_vfx_params.json: the material-instance values and
actor transforms that tie the meshes to L_Tutorial_Bedroom. Standard library only.

Roles. seed = (role + u) / 4 with u uniform, so the material reads role = floor(4 seed) and u = frac(4 seed).
Splats are written sorted by role so GPU waves run one code path. Rest positions are in mesh-local cm:
  SM_SandStream (origin = the commode's front lip, +X out of the commode, Z up)
    0 core grains   rest = (0, lateral offset at the lip, lift)    slide down the mound's front, fall, splash
    1 halo grains   same, wider and finer                           fray off the column
    2 dust          rest = the impact point                         puffs off the pile
    3 pile grains   on the spill pile (mound() seed 3, scaled)      creep down the pile in pulses
  SM_SandMoundSplats_A/B/C (mound-local cm, same transform as the SandMound_* actor)
    0 surface grains   on the surface, lifted by half a radius     avalanche tongues + breathing
    1 saltators        on the lower slopes                          hop downwind in meandering streamers
    2 wisps            7 tendril roots (all splats of a root share one 2 cm cell)   lift off as smoke-and-sand
    3 sparkle grains   on the surface                               breathe and glint
The mound surface is mound() from Tools/Unreal/make_procedural_meshes.py; mound_height() below is the Python
twin of the material's Mound() and the self-test checks it against the mesh.
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "Unreal"))
from ply_to_splatmesh import CHANNELS, CORNER_UV, NUDGE_M, gltf_doc  # noqa: E402
from make_procedural_meshes import mound  # noqa: E402

G = 980.0
COMMODE_TOP, COMMODE_FRONT_Y = 121.2, 239.8           # Commode bounds (probe of the live level)
MOUND_A_ACTOR = {"loc": (-150.0, 266.0, 121.2), "yaw": -17.0, "scale": 0.42}
MOUND_ACTORS = {  # label: (mesh key, location, yaw, uniform scale), as placed by Tools/Unreal/bedroom_v3.py
    "OnCommode": ("A", (-150.0, 266.0, 121.2), -17.0, 0.42),
    "Bay": ("B", (-60.0, -340.0, 0.0), 121.0, 0.9),
    "Hearth": ("C", (-280.0, -130.0, 0.0), -128.0, 0.7),
    "Path": ("A", (150.0, -40.0, 0.0), 158.0, 0.55),
}
MOUND_SEEDS = {"A": 1, "B": 2, "C": 3}
WIND_WORLD = (4.0, 9.0, 0.0)       # cm/s: a dream draught from the bay window into the room (+Y)
STREAM = {"throw": 26.0, "slide": 14.0, "lip_half_width": 1.6, "pile_scale": 0.22, "lift": 0.15}


def mound_shape(seed):
    """mound()'s constants as the material's Shape vector: (apex height, 6 rnd1, 6 rnd2, 6 rnd3)."""
    rnd = [math.sin(seed * 12.9898 + k * 78.233) * 43758.5453 % 1.0 for k in range(6)]
    return (24.0 * (0.9 + 0.2 * rnd[0]), rnd[1] * 6, rnd[2] * 6, rnd[3] * 6)


def mound_height(x, y, S):
    """Python twin of Mound() in M_SplatMesh (MF_SplatFlow): mound() defaults R 50, H 24, 14 rings."""
    a = math.atan2(y, x)
    t = math.hypot(x, y) / (50.0 * (1 + 0.12 * math.sin(3 * a + S[1]) + 0.08 * math.sin(5 * a + S[2])))
    if t >= 1.0:
        return 0.0
    ring = lambda tt: 24.0 * (1 - tt) ** 1.6 * (1 + 0.15 * math.sin(4 * a + S[3]) * tt)  # noqa: E731
    return S[0] + (ring(1 / 14) - S[0]) * t * 14 if t < 1 / 14 else ring(t)


def rot(v, yaw_deg):
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


class Splats:
    """Accumulates splats in UE local cm; write() emits the ply_to_splatmesh channel layout."""

    def __init__(self, rng):
        self.rng, self.rows = rng, []

    def add(self, role, pos, radius, grey, alpha, normal=(0.0, 0.0, 1.0)):
        u = min(max(self.rng.random(), 0.001), 0.999)  # keeps floor(4 seed) exact in float32
        self.rows.append((role, (role + u) / 4.0, pos, radius, grey, alpha, normal))

    def write(self, out_dir, name, extra):
        rows = sorted(self.rows, key=lambda r: r[1])  # by role, then u: coherent GPU waves
        A = {k: [] for k in CHANNELS}
        idx, e = [], NUDGE_M
        for j, (role, seed, p, radius, grey, alpha, n) in enumerate(rows):
            cx, cy, cz = p[0] / 100.0, p[2] / 100.0, p[1] / 100.0         # UE cm -> glTF m (x, z, y)
            gn = (n[0], n[2], n[1])
            tx, ty, tz = 1.0 - gn[0] * gn[0], -gn[0] * gn[1], -gn[0] * gn[2]  # glTF X made orthogonal to the normal
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) or 1.0
            A["POSITION"] += [cx - e, cy - e, cz, cx + e, cy - e, cz, cx + e, cy + e, cz, cx - e, cy + e, cz]
            A["NORMAL"] += list(gn) * 4
            A["TANGENT"] += [tx / tl, ty / tl, tz / tl, 1.0] * 4
            A["TEXCOORD_0"] += list(CORNER_UV)
            A["TEXCOORD_1"] += [radius, seed] * 4
            for t in (2, 3, 4, 5):
                A[f"TEXCOORD_{t}"] += [0.0, 0.0] * 4
            A["TEXCOORD_6"] += [0.0, radius / 2] * 4                        # SH B.z = 0, sigma0
            A["TEXCOORD_7"] += [radius / 2, radius / 2] * 4                 # isotropic sigmas
            A["COLOR_0"] += [grey, grey, grey, alpha] * 4
            b = 4 * j
            idx += [b, b + 1, b + 2, b, b + 2, b + 3]
        import array
        arrays = {k: array.array("f", v) for k, v in A.items()}
        doc, blob = gltf_doc(arrays, array.array("I", idx), name)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, name + ".bin"), "wb") as f:
            f.write(blob)
        with open(os.path.join(out_dir, name + ".gltf"), "w", encoding="utf-8") as f:
            json.dump(doc, f, separators=(",", ":"), allow_nan=False)
        counts = [sum(r[0] == k for r in rows) for k in range(4)]
        lo = [min(r[2][k] for r in rows) for k in range(3)]
        hi = [max(r[2][k] for r in rows) for k in range(3)]
        side = {"generator": "Tools/Splats/make_sand_splats.py", "splats": len(rows), "role_counts": counts,
                "rest_bounds_cm": {"min": lo, "max": hi},
                "radius_cm": {"min": min(r[3] for r in rows), "max": max(r[3] for r in rows)},
                "seed": "(role + u) / 4", "channels": CHANNELS, **extra}
        with open(os.path.join(out_dir, name + ".splatmesh.json"), "w", encoding="utf-8") as f:
            json.dump(side, f, indent=1)
        return rows, side


def sample_surface(mesh, rng, n, scale=1.0, offset=(0.0, 0.0, 0.0), keep=None):
    """Area-weighted points on a mound() mesh: [(pos, normal, t)] with t = radial position 0 apex .. 1 toe."""
    pos, nrm, _, tris = mesh
    areas, acc = [], 0.0
    for a, b, c in tris:
        u = [pos[b][k] - pos[a][k] for k in range(3)]
        v = [pos[c][k] - pos[a][k] for k in range(3)]
        cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        acc += math.sqrt(sum(x * x for x in cr))
        areas.append(acc)
    out = []
    while len(out) < n:
        k = _bisect(areas, rng.random() * acc)
        r1, r2 = rng.random(), rng.random()
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        a, b, c = tris[k]
        p = [pos[a][i] + r1 * (pos[b][i] - pos[a][i]) + r2 * (pos[c][i] - pos[a][i]) for i in range(3)]
        nn = [nrm[a][i] + r1 * (nrm[b][i] - nrm[a][i]) + r2 * (nrm[c][i] - nrm[a][i]) for i in range(3)]
        ln = math.sqrt(sum(x * x for x in nn)) or 1.0
        t = math.hypot(p[0], p[1]) / 50.0
        if keep and not keep(p, t, rng):
            continue
        out.append(([p[i] * scale + offset[i] for i in range(3)], [x / ln for x in nn], t))
    return out


def _bisect(acc, x):
    lo, hi = 0, len(acc) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if acc[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def logu(rng, a, b):
    return math.exp(math.log(a) + rng.random() * (math.log(b) - math.log(a)))


def build_mound(key, rng):
    """~9k splats on mound() seed MOUND_SEEDS[key], mound-local cm."""
    mesh = mound(MOUND_SEEDS[key])
    s = Splats(rng)
    for p, n, t in sample_surface(mesh, rng, 6300):
        r = logu(rng, 0.55, 1.1)
        s.add(0, [p[i] + n[i] * 0.5 * r for i in range(3)], r, 0.10 + 0.14 * rng.random(), 0.75 + 0.2 * rng.random(), n)
    for p, n, t in sample_surface(mesh, rng, 900, keep=lambda p, t, g: t > 0.45 or g.random() < 0.2):
        s.add(1, [p[0], p[1], p[2] + 0.3], logu(rng, 0.3, 0.6), 0.12, 0.85, n)
    roots = sample_surface(mesh, rng, 7, keep=lambda p, t, g: 0.18 < t < 0.6)
    for k in range(1300):
        (p, n, t) = roots[k % 7]
        cx, cy = (math.floor(p[0] / 2.0) + 0.5) * 2.0, (math.floor(p[1] / 2.0) + 0.5) * 2.0  # one 2 cm cell per tendril
        jx, jy = (rng.random() - 0.5) * 0.8, (rng.random() - 0.5) * 0.8
        z = mound_height(cx + jx, cy + jy, mound_shape(MOUND_SEEDS[key])) + 0.4
        s.add(2, [cx + jx, cy + jy, z], logu(rng, 0.5, 0.9), 0.2, 0.35 + 0.2 * rng.random(), n)
    for p, n, t in sample_surface(mesh, rng, 500):
        r = logu(rng, 0.35, 0.6)
        s.add(3, [p[i] + n[i] * 0.5 * r for i in range(3)], r, 0.25, 1.0, n)
    return s


def stream_layout():
    """Where the stream leaves the commode, how far it throws, and where the spill pile sits (world + local)."""
    S_A = mound_shape(MOUND_SEEDS["A"])
    pos = mound(MOUND_SEEDS["A"])[0]
    loc, yaw, sc = MOUND_A_ACTOR["loc"], MOUND_A_ACTOR["yaw"], MOUND_A_ACTOR["scale"]
    world = [(loc[0] + rot(p, yaw)[0] * sc, loc[1] + rot(p, yaw)[1] * sc) for p in pos]
    toe = min(world, key=lambda w: w[1])                                 # the mound's front toe, nearest the lip
    lip = (toe[0], COMMODE_FRONT_Y, COMMODE_TOP)
    # how high the mound stands 'slide' cm behind the lip (the feeding slope), mound-local -> world cm
    back = (lip[0], lip[1] + STREAM["slide"])
    ml = rot(((back[0] - loc[0]) / sc, (back[1] - loc[1]) / sc), -yaw)
    slide_h = mound_height(ml[0], ml[1], S_A) * sc
    S_C = mound_shape(MOUND_SEEDS["C"])
    drop, ps = COMMODE_TOP, STREAM["pile_scale"]
    z_land = -drop + S_C[0] * ps
    tf = math.sqrt(2 * (STREAM["lift"] - z_land) / G)
    x_land = STREAM["throw"] * tf
    return {"lip_world": lip, "slide_height": slide_h, "fall_time": tf, "x_land": x_land, "z_land": z_land,
            "pile_world": (lip[0], lip[1] - x_land, 0.0), "drop": drop, "shape_C": S_C}


def build_stream(rng, L):
    s = Splats(rng)
    hw, lift = STREAM["lip_half_width"], STREAM["lift"]
    for _ in range(9000):
        y = max(-hw, min(hw, rng.gauss(0.0, hw * 0.5)))
        s.add(0, [0.0, y, lift], logu(rng, 0.14, 0.3), 0.08 + 0.12 * rng.random(), 0.8 + 0.15 * rng.random())
    for _ in range(3000):
        y = max(-2 * hw, min(2 * hw, rng.gauss(0.0, hw * 0.7)))
        s.add(1, [0.0, y, lift], logu(rng, 0.08, 0.18), 0.12, 0.4 + 0.3 * rng.random())
    for _ in range(900):
        s.add(2, [L["x_land"] + (rng.random() - 0.5) * 4, (rng.random() - 0.5) * 4, L["z_land"] + 0.5],
              logu(rng, 0.5, 0.9), 0.2, 0.25 + 0.15 * rng.random())
    ps = STREAM["pile_scale"]
    for p, n, t in sample_surface(mound(MOUND_SEEDS["C"]), rng, 3100, ps, (L["x_land"], 0.0, -L["drop"])):
        r = logu(rng, 0.3, 0.55)
        s.add(3, [p[i] + n[i] * 0.4 * r for i in range(3)], r, 0.1 + 0.12 * rng.random(), 0.9, n)
    return s


def build_burst(rng):
    """SM_SandBurst: pooled one-shot bursts and footsteps (M_SplatMesh Mode 5). Grains in a 6 cm cloud, soft dust."""
    s = Splats(rng)
    for k in range(1200):
        role = 0 if k < 900 else 2
        v = [rng.gauss(0.0, 1.0) for _ in range(3)]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        rad = (6.0 if role == 0 else 4.0) * rng.random() ** (1 / 3)
        pos = [v[0] / n * rad, v[1] / n * rad, abs(v[2] / n) * rad * 0.6]
        if role == 0:
            s.add(0, pos, logu(rng, 0.2, 0.45), 0.1 + 0.12 * rng.random(), 0.85)
        else:
            s.add(2, pos, logu(rng, 0.6, 1.0), 0.2, 0.3)
    return s


def build_face_drift(rng):
    """SM_SandFaceDrift: grains on the front of a head (local +X forward, origin at the head centre) that flake off the
    eroded face (M_SplatMesh Mode 6). Attach to a head socket; the character lane orients it."""
    s = Splats(rng)
    while len(s.rows) < 600:
        v = [rng.gauss(0.0, 1.0) for _ in range(3)]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        d = [x / n for x in v]
        if d[0] < 0.35:  # front cap only: the eaten face, not the hair
            continue
        r = 10.5 + rng.random() * 1.5
        s.add(0, [d[0] * r * 0.85, d[1] * r * 0.75, d[2] * r], logu(rng, 0.12, 0.3), 0.12, 0.8, tuple(d))
    return s


def params(L):
    """Material-instance values and actor transforms (sand_vfx_params.json)."""
    def wind_local(yaw, scale):
        w = rot(WIND_WORLD, -yaw)
        return (round(w[0] / scale, 2), round(w[1] / scale, 2), 0.0)
    r4 = lambda v: [round(x, 4) for x in v]  # noqa: E731
    mounds = {}
    for label, (key, loc, yaw, sc) in MOUND_ACTORS.items():
        mounds[label] = {"mesh": f"SM_SandMoundSplats_{key}", "loc": loc, "yaw": yaw, "scale": sc,
                         "Shape": r4(mound_shape(MOUND_SEEDS[key])), "Place": [0.0, 0.0, 1.0, 0.0],
                         "Flow_wind_local": wind_local(yaw, sc)}
    lip = L["lip_world"]
    clock_base_z = COMMODE_TOP + mound_shape(1)[0] * MOUND_A_ACTOR["scale"] - 4.0   # half-buried in the peak
    return {
        "stream": {"loc": lip, "yaw": -90.0, "Shape": r4(L["shape_C"]),
                   "Place": r4((L["x_land"], 0.0, STREAM["pile_scale"], 0.0)),
                   "Tune": r4((L["drop"], STREAM["throw"], STREAM["slide"], L["slide_height"])),
                   "slide_height_cm": round(L["slide_height"], 3), "fall_time_s": round(L["fall_time"], 4)},
        "pile": {"mesh": "SM_SandMound_C", "loc": [round(x, 3) for x in L["pile_world"]], "yaw": -90.0,
                 "scale": STREAM["pile_scale"]},
        "clock": {"loc": (MOUND_A_ACTOR["loc"][0], MOUND_A_ACTOR["loc"][1], round(clock_base_z, 3)), "yaw": 180.0,
                  "Shape": r4(mound_shape(1)),
                  "Place": r4((0.0, 0.0, MOUND_A_ACTOR["scale"], math.radians(180.0 - MOUND_A_ACTOR["yaw"]))),
                  "Tune": r4((round(COMMODE_TOP - clock_base_z, 3), 14.0, 27.07, 7.0))},
        "mounds": mounds,
    }


def build(out_dir):
    rng = random.Random(20261105)
    L = stream_layout()
    info = {}
    for key in "ABC":
        _, side = build_mound(key, rng).write(out_dir, f"SM_SandMoundSplats_{key}", {"mound_seed": MOUND_SEEDS[key]})
        info[key] = side["role_counts"]
    _, side = build_stream(rng, L).write(out_dir, "SM_SandStream", {"layout": {k: v for k, v in L.items()}})
    info["stream"] = side["role_counts"]
    info["burst"] = build_burst(random.Random(7)).write(out_dir, "SM_SandBurst", {"mode": 5})[1]["role_counts"]
    info["face"] = build_face_drift(random.Random(8)).write(out_dir, "SM_SandFaceDrift", {"mode": 6})[1]["role_counts"]
    P = params(L)
    with open(os.path.join(out_dir, "sand_vfx_params.json"), "w", encoding="utf-8") as f:
        json.dump(P, f, indent=1)
    print("roles", info)
    print(json.dumps(P, indent=1))


def selftest():
    import tempfile
    # 1. the material's mound formula matches the mound() mesh it rides on (every vertex, all three seeds)
    for key, seed in MOUND_SEEDS.items():
        pos = mound(seed)[0]
        S = mound_shape(seed)
        assert abs(pos[0][2] - S[0]) < 1e-9, "apex"
        err = max(abs(mound_height(p[0], p[1], S) - p[2]) for p in pos[1:] if math.hypot(p[0], p[1]) < 49.0)
        assert err < 1e-6, (key, err)
    # 2. seeds decode to their role in float32, the stream lands on its pile, files are consistent
    import struct
    f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]  # noqa: E731
    rng = random.Random(1)
    s = Splats(rng)
    for role in range(4):
        for _ in range(500):
            s.add(role, (0, 0, 0), 0.2, 0.1, 1.0)
    assert all(math.floor(f32(r[1]) * 4) == r[0] and 0 < (f32(r[1]) * 4) % 1 < 1 for r in s.rows), "role decode"
    L = stream_layout()
    assert 0.4 < L["fall_time"] < 0.6 and 5 < L["x_land"] < 20, L
    assert abs(L["lip_world"][0] + 150) < 25 and 0 < L["slide_height"] < 6, L
    with tempfile.TemporaryDirectory() as tmp:
        rows, side = build_stream(random.Random(2), L).write(tmp, "t", {})
        doc = json.load(open(os.path.join(tmp, "t.gltf"), encoding="utf-8"))
        nv = 4 * len(rows)
        assert all(doc["accessors"][i]["count"] == nv for i in doc["meshes"][0]["primitives"][0]["attributes"].values())
        assert [r[0] for r in rows] == sorted(r[0] for r in rows), "sorted by role"
        assert side["role_counts"] == [9000, 3000, 900, 3100], side["role_counts"]
        assert side["rest_bounds_cm"]["min"][2] < -115 and side["rest_bounds_cm"]["max"][2] < 1, side["rest_bounds_cm"]
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        build(sys.argv[1] if len(sys.argv) > 1 else "P:/FoA-Assets/splatmesh")
