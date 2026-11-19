"""Generates small procedural meshes as glTF for the bedroom (imported by the Unreal scripts).

  python Tools/Unreal/make_procedural_meshes.py [out_dir]     (default P:/FoA-Assets/procedural)
  python Tools/Unreal/make_procedural_meshes.py --selftest

Authored in Unreal space (cm, X forward, Y right, Z up); written as glTF (m, Y up), which Unreal's importer maps
back exactly (the Poly Haven imports rely on the same mapping). Trims are 100 cm runs along +X: scale X to length.
Profiles are (y, z) with +Y = out from the wall into the room, traced so the outside is on the left.
- SM_Baseboard     14 cm skirting board, ogee top; pivot on the floor/wall line
- SM_CrownMolding  10 x 10 cm cove cornice; pivot in the ceiling/wall corner, hangs down
- SM_Casing        9 cm chamfered door/window casing, centered on its width
- SM_FrameBar      6 x 6 cm chamfered window frame member, centered
- SM_Muntin        2.5 x 4 cm glazing bar, centered
- SM_Sill          20 cm deep window board with a bullnose; pivot at the back top edge
- SM_Mantel        18 cm mantel shelf with a cove under it; pivot at the back top edge
- SM_SandMound_A/B/C  irregular sand mounds about 1 m wide; pivot at the base center
- trims/SM_Trim_*  one unique mesh per bedroom trim run (18 cm baseboard, 14 cm crown, fluted window casings),
  mitered exactly at every corner, authored in world space (pivot = run start, place with identity rotation);
  trims/trims.json lists them for Tools/Unreal/place_trims.py
"""
import base64
import json
import math
import os
import struct
import sys

BASEBOARD = [(0.0, 0.0), (2.0, 0.0), (2.0, 9.0), (1.6, 10.0), (1.6, 11.5), (1.55, 12.0), (1.4, 12.5),
             (1.15, 12.9), (0.95, 13.2), (0.8, 13.5), (0.7, 13.8), (0.6, 14.0), (0.0, 14.0)]
CASING = [(0.0, -4.5), (1.7, -4.5), (2.2, -4.0), (2.2, 4.0), (1.7, 4.5), (0.0, 4.5)]
FRAME = [(-3.0, -2.5), (-2.5, -3.0), (2.5, -3.0), (3.0, -2.5), (3.0, 2.5), (2.5, 3.0), (-2.5, 3.0), (-3.0, 2.5), (-3.0, -2.5)]
MUNTIN = [(-1.25, -1.6), (-0.9, -2.0), (0.9, -2.0), (1.25, -1.6), (1.25, 1.6), (0.9, 2.0), (-0.9, 2.0), (-1.25, 1.6), (-1.25, -1.6)]
SILL = [(0.0, -3.0), (17.0, -3.0), (18.6, -2.6), (19.6, -1.5), (19.6, -0.6), (18.8, 0.0), (0.0, 0.0)]
MANTEL = [(0.0, -14.0), (3.0, -14.0), (3.0, -11.0), (5.5, -8.5), (9.0, -6.0), (13.0, -4.5), (18.0, -4.5), (18.0, 0.0), (0.0, 0.0)]


def crown_profile(steps=10):
    pts = [(0.0, -10.0), (0.9, -10.0), (0.9, -9.4)]
    cx, cy, r = 10.4, -10.4, 9.5
    a0, a1 = math.atan2(-9.4 - cy, 0.9 - cx), math.atan2(-0.9 - cy, 9.4 - cx)
    for i in range(1, steps):
        a = a0 + (a1 - a0) * i / steps
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts + [(9.4, -0.9), (10.0, -0.9), (10.0, 0.0), (0.0, 0.0)]


def extrude(profile, length=100.0):
    """Returns (positions, normals, uvs, triangles) in Unreal space. Smooth normals across the profile, flat caps."""
    n = len(profile)
    acc = [0.0]
    for i in range(n - 1):
        acc.append(acc[-1] + math.dist(profile[i], profile[i + 1]))
    total = acc[-1] or 1.0
    pos, nrm, uv, tris = [], [], [], []
    for i in range(n):  # outward normal = edge direction rotated -90 deg (outside is on the left of travel)
        ny = nz = 0.0
        for a, b in ((i - 1, i), (i, i + 1)):
            if 0 <= a and b < n:
                ey, ez = profile[b][0] - profile[a][0], profile[b][1] - profile[a][1]
                ny, nz = ny + ez, nz - ey
        ln = math.hypot(ny, nz) or 1.0
        nrm.append((0.0, ny / ln, nz / ln))
    nrm = nrm + nrm
    for x in (0.0, length):
        for (y, z), d in zip(profile, acc):
            pos.append((x, y, z))
            uv.append((x / length, d / total))
    for i in range(n - 1):
        a, b, c, d = i, i + 1, n + i + 1, n + i
        tris += [(a, b, c), (a, c, d)]
    for end, sign in ((0, -1.0), (n, 1.0)):  # caps: own vertices so they shade flat
        base = len(pos)
        for (y, z) in profile:
            pos.append((end and length, y, z))
            nrm.append((sign, 0.0, 0.0))
            uv.append((y / 20.0, z / 20.0))
        for i in range(1, n - 1):
            tris.append((base, base + i, base + i + 1))
    return pos, nrm, uv, tris


def mound(seed, radius=50.0, height=24.0, rings=14, sectors=40):
    rnd = [math.sin(seed * 12.9898 + k * 78.233) * 43758.5453 % 1.0 for k in range(6)]
    pos, uv = [(0.0, 0.0, height * (0.9 + 0.2 * rnd[0]))], [(0.5, 0.5)]
    for r in range(1, rings + 1):
        t = r / rings
        for s in range(sectors):
            a = 2 * math.pi * s / sectors
            wob = 1 + 0.12 * math.sin(3 * a + rnd[1] * 6) + 0.08 * math.sin(5 * a + rnd[2] * 6)
            h = height * (1 - t) ** 1.6 * (1 + 0.15 * math.sin(4 * a + rnd[3] * 6) * t)
            pos.append((radius * t * wob * math.cos(a), radius * t * wob * math.sin(a), max(h, 0.0)))
            uv.append((0.5 + 0.5 * t * math.cos(a), 0.5 + 0.5 * t * math.sin(a)))
    tris = [(0, 1 + s, 1 + (s + 1) % sectors) for s in range(sectors)]
    for r in range(1, rings):
        b0, b1 = 1 + (r - 1) * sectors, 1 + r * sectors
        for s in range(sectors):
            s2 = (s + 1) % sectors
            tris += [(b0 + s, b1 + s, b1 + s2), (b0 + s, b1 + s2, b0 + s2)]
    nrm = [[0.0, 0.0, 0.0] for _ in pos]
    for t in tris:
        p0, p1, p2 = (pos[i] for i in t)
        u = [p1[k] - p0[k] for k in range(3)]
        v = [p2[k] - p0[k] for k in range(3)]
        c = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        if c[2] < 0:
            c = (-c[0], -c[1], -c[2])
        for i in t:
            for k in range(3):
                nrm[i][k] += c[k]
    nrm = [tuple(x / (math.sqrt(sum(y * y for y in n)) or 1.0) for x in n) for n in nrm]
    return pos, nrm, uv, tris


# ---------- mitered trim runs: one unique mesh per straight run, authored in world space ----------
# Room outline (bedroom_v3.POLY) with the chimney-breast notch, so trims wrap the breast's outside corners.
TRIM_OUTLINE = [(-375, 300), (375, 300), (375, -300), (90, -300), (30, -390), (-150, -390), (-210, -300),
                (-375, -300), (-375, -80), (-330, -80), (-330, 80), (-375, 80)]
CEILING_Z = 300.0
# Square baseboard stops (s along the segment). Door: against DoorFrame_Bedroom's plinth blocks, whose side faces
# measure y 145.9 / 29.1 (3.35 deep, 22 tall). Chimney front: against the fireplace surround's plinths, flat faces at
# y +-67.5 (Tools/Fireplace/build_fireplace_blender.py: yc 59 +- 8.5, 5.8 deep, 19 tall).
BASE_GAPS = {1: (300.0 - 145.9, 300.0 - 29.1), 9: (80.0 - 67.5, 80.0 + 67.5)}
WINDOWS = {3: (26.0, 82.0), 4: (35.0, 145.0), 5: (26.0, 82.0)}  # segment -> opening s range (bedroom_v3.OPENINGS)
WIN_Z = (85.0, 215.0)
HARD_DEG = 40.0  # profile corners sharper than this get split normals
UP = (0.0, 0.0, 1.0)
# Ornament trim sheet T_TrimOrnament_N (bake_trim_ornament.py), sampled with UV1: U = across the band, V tiles
# along the run every ORN_TILE cm. Columns: flat (everything without carving), egg-and-dart, bead-and-reel.
ORN_TILE, ORN_FLAT_U = 12.0, 0.04
ORN_EGG, ORN_BEAD = (0.125, 0.5), (0.625, 0.95)


def arc(cy, cz, r, a0, a1, steps):
    return [(cy + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def clean(pts):
    out = []
    for p in pts:
        p = (round(p[0], 6), round(p[1], 6))
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    return out


def base_profile():
    """18 cm skirting: flat 1.8 cm plinth, quirked bead, cyma reversa, top bead. (depth, z), CCW."""
    pts = [(0.0, 0.0), (1.8, 0.0), (1.8, 12.4), (1.6, 12.4)] + arc(1.6, 13.15, 0.75, -90, 90, 10) + [(1.35, 13.9)]
    pts += [(1.35 - 0.85 * (1 - math.cos(math.pi * i / 10)) / 2, 13.9 + 0.26 * i) for i in range(1, 11)]
    return clean(pts + [(0.75, 16.5)] + arc(0.75, 16.95, 0.45, -90, 90, 8) + [(0.55, 17.4), (0.55, 18.0), (0.0, 18.0)])


def crown_profile14():
    """14 cm cornice hanging from the ceiling: bead, ovolo (egg-and-dart band), fillet, deep cove, top fillet."""
    pts = [(0.0, -14.0), (0.9, -14.0), (0.9, -13.4)] + arc(0.9, -12.7, 0.7, -90, 90, 8) + [(1.3, -12.0)]
    pts += arc(1.3, -9.8, 2.2, -90, 0, 10) + [(3.5, -9.2), (4.2, -9.2)] + arc(11.0, -9.2, 6.8, 180, 90, 16)
    return clean(pts + [(11.0, -1.8), (11.8, -1.8), (11.8, 0.0), (0.0, 0.0)])


def casing_profile(width=7.5):
    """Fluted casing (depth, across) with across = 0 at the opening edge: staff bead, three flutes, back band."""
    pts = [(0.0, 0.0), (1.0, 0.0)] + arc(1.0, 0.6, 0.6, -90, 90, 8) + [(1.6, 1.5)]
    w, h = 0.9, 0.32
    r = (h * h + w * w / 4) / (2 * h)
    half = math.degrees(math.asin(w / 2 / r))
    for c in (2.4, 3.65, 4.9):
        pts += arc(1.6 - h + r, c, r, 180 + half, 180 - half, 8)
    pts += [(1.6, 5.8), (2.2, 6.2), (2.2, width - 0.5)] + arc(1.7, width - 0.5, 0.5, 0, 90, 6) + [(0.0, width)]
    return clean(pts)


def triangulate(poly):
    """Ear clipping for a simple polygon; returns index triangles (orientation fixed later by the writer)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    idx = list(range(len(poly))) if area > 0 else list(range(len(poly)))[::-1]
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])  # noqa: E731
    tris = []
    while len(idx) > 3:
        for j in range(len(idx)):
            a, b, c = idx[j - 1], idx[j], idx[(j + 1) % len(idx)]
            if cross(poly[a], poly[b], poly[c]) <= 1e-9:
                continue
            if any(min(cross(poly[a], poly[b], poly[q]), cross(poly[b], poly[c], poly[q]),
                       cross(poly[c], poly[a], poly[q])) > -1e-9 for q in idx if q not in (a, b, c)):
                continue
            tris.append((a, b, c))
            idx.pop(j)
            break
        else:  # only collinear/degenerate vertices left: drop one and carry on
            idx.pop(next(j for j in range(len(idx)) if abs(cross(poly[idx[j - 1]], poly[idx[j]], poly[idx[(j + 1) % len(idx)]])) <= 1e-9))
    return tris + [tuple(idx)]


def band(profile, a, b, cols):
    """Ornament band over the profile points a..b (inclusive), mapped onto trim-sheet columns cols."""
    return (profile.index(a), profile.index(b), cols)


def sweep(profile, origin, ex, ey, ez, x0, x1, k0=0.0, k1=0.0, key=0, bands=()):
    """Extrudes a (p0, p1) profile along ex in world space (cm): point p maps to origin + ex*x + ey*p0 + ez*p1.
    Each end is cut by the corner's bisecting plane: x_start = x0 + k0*m, x_end = x1 - k1*m with m = p[key] and
    k = 1/tan(corner angle / 2) (0 square, 1 inside 90, -1 outside 90). UVs are world scale: u = profile arc (m),
    v = run x (m). UV1 maps the profile segments inside `bands` onto ornament columns, the rest onto the flat one.
    Returns {"mesh": (pos, nrm, uv, tris, uv1) in world space, "start"/"end": cut points, "pivot"}."""
    n = len(profile)
    world = lambda x, p: tuple(origin[i] + ex[i] * x + ey[i] * p[0] + ez[i] * p[1] for i in range(3))  # noqa: E731
    vec = lambda a, b: tuple(ey[i] * a + ez[i] * b for i in range(3))  # noqa: E731
    xs = [x0 + k0 * p[key] for p in profile]
    xe = [x1 - k1 * p[key] for p in profile]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(profile, profile[1:] + profile[:1]))
    sgn = 1.0 if area > 0 else -1.0
    seg_n, acc = [], [0.0]
    for a, b in zip(profile, profile[1:]):
        l = math.dist(a, b)
        seg_n.append((sgn * (b[1] - a[1]) / l, -sgn * (b[0] - a[0]) / l))
        acc.append(acc[-1] + l)

    def vnormal(i, s):  # smooth across shallow profile turns, split at hard corners
        if i in (0, n - 1):
            return seg_n[s]
        a, b = seg_n[i - 1], seg_n[i]
        if a[0] * b[0] + a[1] * b[1] < math.cos(math.radians(HARD_DEG)):
            return seg_n[s]
        l = math.hypot(a[0] + b[0], a[1] + b[1])
        return ((a[0] + b[0]) / l, (a[1] + b[1]) / l)

    def orn_u(i, s):  # every segment owns its vertices, so UV1 can jump between columns at band edges
        for i0, i1, (c0, c1) in bands:
            if i0 <= s < i1:
                return c0 + (c1 - c0) * (acc[i] - acc[i0]) / (acc[i1] - acc[i0])
        return ORN_FLAT_U

    pos, nrm, uv, tris, uv1 = [], [], [], [], []
    for s in range(n - 1):
        b0 = len(pos)
        for i in (s, s + 1):
            nv = vec(*vnormal(i, s))
            for x in (xs[i], xe[i]):
                pos.append(world(x, profile[i]))
                nrm.append(nv)
                uv.append((acc[i] / 100.0, x / 100.0))
                uv1.append((orn_u(i, s), x / ORN_TILE))
        tris += [(b0, b0 + 2, b0 + 3), (b0, b0 + 3, b0 + 1)]
    ekey = ey if key == 0 else ez
    cap_tris = triangulate(profile)
    for xcut, k, sign in ((xs, k0, -1.0), (xe, k1, 1.0)):
        cn = tuple(sign * ex[i] + k * ekey[i] for i in range(3))
        l = math.sqrt(sum(c * c for c in cn))
        b0 = len(pos)
        for p, x in zip(profile, xcut):
            pos.append(world(x, p))
            nrm.append(tuple(c / l for c in cn))
            uv.append((p[0] / 100.0, p[1] / 100.0))
            uv1.append((ORN_FLAT_U, 0.0))
        tris += [(b0 + a, b0 + b, b0 + c) for a, b, c in cap_tris]
    return {"mesh": (pos, nrm, uv, tris, uv1), "pivot": world(x0, (0.0, 0.0)),
            "start": [world(x, p) for p, x in zip(profile, xs)], "end": [world(x, p) for p, x in zip(profile, xe)]}


def outline_frames(poly):
    """Per segment (start, length, direction, inward normal) and per vertex the miter factor k = 1/tan(angle/2)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    segs = []
    for i, p0 in enumerate(poly):
        p1 = poly[(i + 1) % len(poly)]
        L = math.dist(p0, p1)
        d = ((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L)
        segs.append((p0, L, d, (d[1], -d[0]) if area < 0 else (-d[1], d[0])))
    ks = []
    for i in range(len(poly)):  # vertex i joins segment i-1 (A) and segment i (B): nA - nB = k (dA + dB)
        _, _, da, na = segs[i - 1]
        _, _, db, nb = segs[i]
        s = (da[0] + db[0], da[1] + db[1])
        ks.append(((na[0] - nb[0]) * s[0] + (na[1] - nb[1]) * s[1]) / (s[0] ** 2 + s[1] ** 2))
    return segs, ks


def trim_runs():
    """All bedroom trim runs: {name: sweep result}. Baseboards and crowns follow TRIM_OUTLINE, window casings
    are mitered at the head corners and stand on the sills."""
    segs, ks = outline_frames(TRIM_OUTLINE)
    base, crown, casing = base_profile(), crown_profile14(), casing_profile()
    base_orn = [band(base, (1.6, 12.4), (1.6, 13.9), ORN_BEAD)]        # bead-and-reel on the quirked bead
    crown_orn = [band(crown, (1.3, -12.0), (3.5, -9.8), ORN_EGG)]       # egg-and-dart on the ovolo
    runs = {}
    for i, (p0, L, d, n) in enumerate(segs):
        k0, k1 = ks[i], ks[(i + 1) % len(segs)]
        ex, ey = (d[0], d[1], 0.0), (n[0], n[1], 0.0)
        g = BASE_GAPS.get(i)
        pieces = [(0.0, g[0], k0, 0.0), (g[1], L, 0.0, k1)] if g else [(0.0, L, k0, k1)]
        for j, (a, b, ka, kb) in enumerate(pieces):
            runs[f"Base_{i:02d}" + ("ab"[j] if g else "")] = sweep(base, (p0[0], p0[1], 0.0), ex, ey, UP, a, b, ka, kb,
                                                                   bands=base_orn)
        runs[f"Crown_{i:02d}"] = sweep(crown, (p0[0], p0[1], CEILING_Z), ex, ey, UP, 0.0, L, k0, k1, bands=crown_orn)
    zb, zt = WIN_Z
    for i, (s0, s1) in WINDOWS.items():
        p0, _L, d, n = segs[i]
        at = lambda s, z: (p0[0] + d[0] * s, p0[1] + d[1] * s, z)  # noqa: E731
        ex, ey = (d[0], d[1], 0.0), (n[0], n[1], 0.0)
        runs[f"WinCasing_{i}_Head"] = sweep(casing, at(s0, zt), ex, ey, UP, 0.0, s1 - s0, -1.0, -1.0, key=1)
        runs[f"WinCasing_{i}_L"] = sweep(casing, at(s0, zb), UP, ey, (-d[0], -d[1], 0.0), 0.0, zt - zb, 0.0, -1.0, key=1)
        runs[f"WinCasing_{i}_R"] = sweep(casing, at(s1, zb), UP, ey, ex, 0.0, zt - zb, 0.0, -1.0, key=1)
        # Sill, sash and muntins (were scaled SM_Sill / SM_FrameBar / SM_Muntin actors from bedroom_v3: UV0 0..1 per piece and
        # no UV1, so M_PaintedWoodTrim's ornament stamped egg-and-dart and bead columns across the flat sill top). As runs they
        # get the casings' world-scale UV0 and an all-flat UV1. Same placement as bedroom_v3.build_trims_and_openings.
        mid = lambda s, z: (p0[0] + d[0] * s - n[0] * 15.0, p0[1] + d[1] * s - n[1] * 15.0, z)  # noqa: E731  frame sits mid-wall
        along = (-d[0], -d[1], 0.0)
        runs[f"WinSill_{i}"] = sweep(SILL, at(s0 - 8.0, zb), ex, ey, UP, 0.0, s1 - s0 + 16.0)
        runs[f"WinSash_{i}_Bottom"] = sweep(FRAME, mid(s0, zb + 3.0), ex, ey, UP, 0.0, s1 - s0)
        runs[f"WinSash_{i}_Top"] = sweep(FRAME, mid(s0, zt - 3.0), ex, ey, UP, 0.0, s1 - s0)
        runs[f"WinSash_{i}_L"] = sweep(FRAME, mid(s0 + 3.0, zb), UP, ey, along, 0.0, zt - zb)
        runs[f"WinSash_{i}_R"] = sweep(FRAME, mid(s1 - 3.0, zb), UP, ey, along, 0.0, zt - zb)
        runs[f"WinMuntin_{i}_V"] = sweep(MUNTIN, mid((s0 + s1) / 2.0, zb + 3.0), UP, ey, along, 0.0, zt - zb - 6.0)
        runs[f"WinMuntin_{i}_H"] = sweep(MUNTIN, mid(s0 + 3.0, (zb + zt) / 2.0), ex, ey, UP, 0.0, s1 - s0 - 6.0)
    return runs


def trim_joints(runs):
    """(run A end, run B start-or-end) pairs that must coincide: every outline corner and every casing head corner."""
    n = len(TRIM_OUTLINE)
    last = lambda kind, i: runs.get(f"{kind}_{i:02d}b") or runs[f"{kind}_{i:02d}"]  # noqa: E731
    first = lambda kind, i: runs.get(f"{kind}_{i:02d}a") or runs[f"{kind}_{i:02d}"]  # noqa: E731
    pairs = [(last(k, (i - 1) % n)["end"], first(k, i)["start"], f"{k} corner {i}") for k in ("Base", "Crown") for i in range(n)]
    for i in WINDOWS:
        head = runs[f"WinCasing_{i}_Head"]
        pairs += [(head["start"], runs[f"WinCasing_{i}_L"]["end"], f"window {i} left"),
                  (head["end"], runs[f"WinCasing_{i}_R"]["end"], f"window {i} right")]
    return pairs


def build_trims(out_dir):
    """Writes one glTF per run (pivot = run start, identity rotation) and trims.json for place_trims.py."""
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    for name, run in trim_runs().items():
        pos, nrm, uv, tris, uv1 = run["mesh"]
        pv = run["pivot"]
        local = [tuple(p[k] - pv[k] for k in range(3)) for p in pos]
        write_gltf(os.path.join(out_dir, f"SM_Trim_{name}.gltf"), (local, nrm, uv, tris, uv1), f"SM_Trim_{name}",
                   material=False)
        manifest.append({"mesh": f"SM_Trim_{name}", "label": f"Trim_{name}", "kind": name.split("_")[0],
                         "pivot": list(pv)})
    with open(os.path.join(out_dir, "trims.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    return manifest


def to_gltf_space(p):  # Unreal cm (X fwd, Y right, Z up) -> glTF m (right-handed, Y up)
    return (p[0] / 100.0, p[2] / 100.0, p[1] / 100.0)


def write_gltf(path, mesh, name, material=True):
    """mesh = (pos, nrm, uv, tris) or (pos, nrm, uv, tris, uv1); uv1 becomes TEXCOORD_1."""
    pos, nrm, uv, tris = mesh[:4]
    gp = [to_gltf_space(p) for p in pos]
    gn = [(n[0], n[2], n[1]) for n in nrm]
    fixed = []
    for a, b, c in tris:  # glTF front faces are counter-clockwise: orient each triangle to its intended normal
        u = [gp[b][k] - gp[a][k] for k in range(3)]
        v = [gp[c][k] - gp[a][k] for k in range(3)]
        cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        want = [gn[a][k] + gn[b][k] + gn[c][k] for k in range(3)]
        fixed.append((a, b, c) if sum(cr[k] * want[k] for k in range(3)) >= 0 else (a, c, b))
    blob = b"".join(struct.pack("<3f", *p) for p in gp)
    nrm_off = len(blob)
    blob += b"".join(struct.pack("<3f", *n) for n in gn)
    uv_off = len(blob)
    blob += b"".join(struct.pack("<2f", u, 1.0 - v) for u, v in uv)
    idx_off = len(blob)
    blob += b"".join(struct.pack("<3I", *t) for t in fixed)
    mins = [min(p[k] for p in gp) for k in range(3)]
    maxs = [max(p[k] for p in gp) for k in range(3)]
    doc = {
        "asset": {"version": "2.0", "generator": "FoA make_procedural_meshes.py"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                                  "indices": 3}]}],
        "buffers": [{"byteLength": len(blob), "uri": "data:application/octet-stream;base64," + base64.b64encode(blob).decode()}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": nrm_off, "target": 34962},
                        {"buffer": 0, "byteOffset": nrm_off, "byteLength": uv_off - nrm_off, "target": 34962},
                        {"buffer": 0, "byteOffset": uv_off, "byteLength": idx_off - uv_off, "target": 34962},
                        {"buffer": 0, "byteOffset": idx_off, "byteLength": len(blob) - idx_off, "target": 34963}],
        "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(gp), "type": "VEC3", "min": mins, "max": maxs},
                      {"bufferView": 1, "componentType": 5126, "count": len(gn), "type": "VEC3"},
                      {"bufferView": 2, "componentType": 5126, "count": len(uv), "type": "VEC2"},
                      {"bufferView": 3, "componentType": 5125, "count": 3 * len(fixed), "type": "SCALAR"}],
    }
    if len(mesh) > 4:
        uv1_off = len(blob)
        blob += b"".join(struct.pack("<2f", u, 1.0 - v) for u, v in mesh[4])
        doc["buffers"] = [{"byteLength": len(blob), "uri": "data:application/octet-stream;base64," + base64.b64encode(blob).decode()}]
        doc["bufferViews"].append({"buffer": 0, "byteOffset": uv1_off, "byteLength": len(blob) - uv1_off, "target": 34962})
        doc["accessors"].append({"bufferView": 4, "componentType": 5126, "count": len(mesh[4]), "type": "VEC2"})
        doc["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_1"] = 4
    if material:  # trims skip it: Interchange would make a throwaway material instance per file
        doc["meshes"][0]["primitives"][0]["material"] = 0
        doc["materials"] = [{"name": "M_" + name, "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.5, 0.5, 1.0]}}]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return fixed


ROOM_POLY = [(-375, 300), (375, 300), (375, -300), (90, -300), (30, -390), (-150, -390), (-210, -300), (-375, -300)]  # bedroom_v3.POLY


def offset_poly(poly, t):
    """Each edge pushed t cm outward, corners re-met (mitered); works for either winding."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))
    out = []
    for i, p in enumerate(poly):
        ns = []
        for a, b in ((poly[i - 1], p), (p, poly[(i + 1) % len(poly)])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy)
            ns.append((dy / ln, -dx / ln) if area > 0 else (-dy / ln, dx / ln))
        k = t / (1.0 + ns[0][0] * ns[1][0] + ns[0][1] * ns[1][1])
        out.append((p[0] + (ns[0][0] + ns[1][0]) * k, p[1] + (ns[0][1] + ns[1][1]) * k))
    return out


def floor_slab(poly=ROOM_POLY, under=10.0, thick=20.0):
    """The bedroom floor as the room's own outline (10 cm under the walls), 20 cm thick, top at z 0. It replaces a
    scaled cube (810 x 750) whose corners showed through the bay's angled windows. UV0 is world planar in metres;
    MI_Floor_OldWood is world-projected anyway, so the look doesn't change."""
    ring = offset_poly(poly, under)
    pos, nrm, uv, tris = [], [], [], []
    for z, nz in ((0.0, 1.0), (-thick, -1.0)):
        base = len(pos)
        for x, y in ring:
            pos.append((x, y, z))
            nrm.append((0.0, 0.0, nz))
            uv.append((x / 100.0, y / 100.0))
        tris += [(base + a, base + b, base + c) for a, b, c in triangulate(ring)]
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
    for i, a in enumerate(ring):   # sides: own vertices so they shade flat
        b = ring[(i + 1) % len(ring)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        n = (dy / ln, -dx / ln, 0.0) if area > 0 else (-dy / ln, dx / ln, 0.0)
        base = len(pos)
        for (x, y), z in ((a, 0.0), (b, 0.0), (b, -thick), (a, -thick)):
            pos.append((x, y, z))
            nrm.append(n)
        uv += [(0.0, 0.0), (ln / 100.0, 0.0), (ln / 100.0, thick / 100.0), (0.0, thick / 100.0)]
        tris += [(base, base + 1, base + 2), (base, base + 2, base + 3)]
    return pos, nrm, uv, tris


def build_all():
    meshes = {"SM_Baseboard": extrude(BASEBOARD), "SM_CrownMolding": extrude(crown_profile()),
              "SM_Casing": extrude(CASING), "SM_FrameBar": extrude(FRAME), "SM_Muntin": extrude(MUNTIN),
              "SM_Sill": extrude(SILL), "SM_Mantel": extrude(MANTEL), "SM_FloorSlab": floor_slab()}
    for name, seed in (("SM_SandMound_A", 1), ("SM_SandMound_B", 2), ("SM_SandMound_C", 3)):
        meshes[name] = mound(seed)
    return meshes


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for name, mesh in build_all().items():
        write_gltf(os.path.join(out_dir, name + ".gltf"), mesh, name)
    build_trims(os.path.join(out_dir, "trims"))


def selftest():
    import tempfile
    meshes = build_all()
    for name, (pos, nrm, uv, tris) in meshes.items():
        assert tris and all(0 <= i < len(pos) for t in tris for i in t), name
        assert len(pos) == len(nrm) == len(uv), name
        assert all(abs(math.sqrt(sum(c * c for c in n)) - 1.0) < 1e-3 for n in nrm), name
    bb = meshes["SM_Baseboard"][0]
    assert max(p[2] for p in bb) == 14.0 and min(p[1] for p in bb) == 0.0 and max(p[0] for p in bb) == 100.0
    cr = meshes["SM_CrownMolding"][0]
    assert max(p[2] for p in cr) == 0.0 and min(p[2] for p in cr) == -10.0
    # the vertex at the top of the baseboard's flat front (y = 2, z = 9) must face into the room (+Y); skip cap verts
    front = [n for p, n in zip(*meshes["SM_Baseboard"][:2]) if p[1] == 2.0 and p[2] == 9.0 and n[0] == 0.0]
    assert front and all(n[1] > 0.9 for n in front), front
    with tempfile.TemporaryDirectory() as tmp:
        fixed = write_gltf(os.path.join(tmp, "t.gltf"), meshes["SM_Sill"], "t")
        doc = json.load(open(os.path.join(tmp, "t.gltf"), encoding="utf-8"))
        assert doc["accessors"][3]["count"] == 3 * len(fixed)
    # trims: 90 deg inside corners cut at 45 (k = 1), chimney outside corners k = -1, bay corners at their bisector
    _segs, ks = outline_frames(TRIM_OUTLINE)
    assert abs(ks[1] - 1.0) < 1e-9 and abs(ks[9] + 1.0) < 1e-9 and abs(ks[10] + 1.0) < 1e-9, ks
    assert abs(ks[3] - math.tan(math.radians(90 - 236.3099 / 2))) < 1e-4, ks[3]  # bay reflex corner, 236.31 deg
    for prof in (base_profile(), crown_profile14(), casing_profile()):
        area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(prof, prof[1:] + prof[:1]))) / 2
        tri = sum(abs((prof[b][0] - prof[a][0]) * (prof[c][1] - prof[a][1]) -
                      (prof[b][1] - prof[a][1]) * (prof[c][0] - prof[a][0])) / 2 for a, b, c in triangulate(prof))
        assert abs(tri - area) < 1e-6, (tri, area)  # caps cover the profile exactly, no overlapping ears
    assert max(p[1] for p in base_profile()) == 18.0 and min(p[1] for p in crown_profile14()) == -14.0
    runs = trim_runs()
    for name, run in runs.items():
        pos, nrm, uv, tris, uv1 = run["mesh"]
        assert tris and all(0 <= i < len(pos) for t in tris for i in t), name
        assert len(pos) == len(nrm) == len(uv) == len(uv1) and all(abs(math.hypot(*n) - 1.0) < 1e-6 for n in nrm), name
    carved = {round(u, 6) for u, _v in runs["Crown_00"]["mesh"][4]}
    assert min(carved) == ORN_FLAT_U and ORN_EGG[0] in carved and ORN_EGG[1] in carved, "crown ovolo must map onto egg-and-dart"
    for name, run in trim_runs().items():
        if name.startswith(("WinSill", "WinSash", "WinMuntin")):
            pos, nrm, uv, tris, uv1 = run["mesh"]
            assert all(u == ORN_FLAT_U for u, _ in uv1), f"{name}: flat window parts take no carving"
            assert max(v for _, v in uv) < 3.0, f"{name}: UV0 is world scale (m), not 0..1 per piece"
    for a, b, what in trim_joints(runs):  # mitered ends of neighbouring runs coincide point for point
        gap = max(math.dist(p, q) for p, q in zip(a, b))
        assert len(a) == len(b) and gap < 1e-6, (what, gap)
    door = runs["Base_01a"]["end"] + runs["Base_01b"]["start"]
    assert {round(p[1], 6) for p in door} == {145.9, 29.1}, "baseboard must stop square against the door plinths"
    hearth = runs["Base_09a"]["end"] + runs["Base_09b"]["start"]
    assert {round(p[1], 6) for p in hearth} == {-67.5, 67.5}, "baseboard must stop square against the surround plinths"
    slab = floor_slab()[0]   # the slab follows the bay: nothing outside the angled walls, and it reaches under the walls
    inside = lambda q, poly: sum((y1 > q[1]) != (y2 > q[1]) and q[0] < (x2 - x1) * (q[1] - y1) / (y2 - y1) + x1  # noqa: E731
                                 for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1])) % 2 == 1
    ring = offset_poly(ROOM_POLY, 10.0)
    assert not inside((200.0, -350.0), ring) and not inside((-300.0, -350.0), ring), "slab must not poke out past the bay walls"
    assert inside((-60.0, -385.0), ring) and inside((370.0, 295.0), ring), "slab must cover the bay and the corners"
    assert abs(min(p[1] for p in slab) + 400.0) < 1e-6 and max(p[2] for p in slab) == 0.0, (min(p[1] for p in slab),)
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        build(sys.argv[1] if len(sys.argv) > 1 else "P:/FoA-Assets/procedural")
        print("written")
