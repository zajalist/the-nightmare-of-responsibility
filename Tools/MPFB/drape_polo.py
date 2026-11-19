"""Polo drape pass (approved by main 2026-11-09): the polo stops reading painted on. Garment geometry only; the
body, the weights, the collar and the shoulders (the user-approved snug) are untouched.
  pwsh -File Tools/MPFB/run_blender.ps1 -Blend P:/FoA-Assets/character/mpfb/teen/foa_teen_underarm_wedge_review.blend Tools/MPFB/drape_polo.py
1. Bridge: each horizontal slice of the torso is pushed out to its convex hull, so the fabric spans the sternum and
   spine grooves instead of following them. Then tension on the front: a parabolic dilation over the unrolled torso
   (5 mm sag over 7 cm), so the cloth spans the pecs and the belly crease like a sheet.
2. Hang: front and back may not fall back toward the body faster than a 0.3 slope below a protrusion, so it drapes
   off the chest and belly instead of tucking under them.
3. Ease 4 mm, smoothed over the mesh, outward only; fades to zero from z 1.30 to 1.38 m (collar, shoulders) and
   toward the sleeves.
4. Sleeve hems: the band that stands off the arm (gap over 6 mm, within 3 cm of the opening) moves 40% of the way
   in, so it stops reading as a rubber ring.
Then the T1 counter (layering.check_pair, 8 poses, every pair with the polo) must read 0, else nothing is saved.
Out: P:/FoA-Assets/character/mpfb/teen/foa_teen_polo_drape.blend, Saved/CharacterShots/polo_drape/report.json"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
from layering import body_region, check_pair, ease_for_poses, garment_pairs, garments, rest_dirs  # noqa: E402
from poses import POSES, apply_pose, reset  # noqa: E402

OUT = 'P:/FoA/Saved/CharacterShots/polo_drape'
os.makedirs(OUT, exist_ok=True)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = bpy.data.objects['Human']
shirt = next(o for o in bpy.data.objects if o.name.endswith('.foa_polo_layered'))
# The T1 counter counts skin the game renders: this review blend has its Mask modifiers (helpers, Delete.*,
# Hidden_by.*) switched off for renders, so switch them back on, as in the exported pieces.
for o in bpy.data.objects:
    for m in getattr(o, 'modifiers', []):
        if m.type == 'MASK':
            m.show_viewport = True


def ramp(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def measure(label):
    reset(rig)
    checks = [(o, i) for o, i in garment_pairs(rig) + [(g, body) for g in garments(rig)] if shirt in (o, i)]
    dirs = {inner.name: rest_dirs(inner, rig) for _, inner in checks}
    regions = {g.name: body_region(g, rig) for g, inner in checks if inner is body}
    rows = {}
    for pose in POSES:
        apply_pose(rig, body, pose)
        for outer, inner in checks:
            n, worst, covered = check_pair(outer, inner, rig, dirs[inner.name], regions.get(outer.name) if inner is body else None)
            rows[f'{pose}|{outer.name}>{inner.name}'] = dict(outside=n, worst_mm=round(worst, 2), covered=covered)
            print(f'{label:6} {pose:10} {outer.name} > {inner.name}: outside {n:5d} worst {worst:6.2f} mm')
    reset(rig)
    return rows


def hull(pts):
    """2D convex hull (monotone chain), counter-clockwise."""
    pts = sorted(map(tuple, pts))
    if len(pts) < 3:
        return np.array(pts)

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(reversed(pts))
    return np.array(lo[:-1] + up[:-1])


def ray_to_hull(c, d, H):
    """Distance from c along unit d to the hull boundary (largest edge hit)."""
    best = 0.0
    for a, b in zip(H, np.roll(H, -1, axis=0)):
        e = b - a
        m = np.array([[d[0], -e[0]], [d[1], -e[1]]])
        if abs(np.linalg.det(m)) < 1e-12:
            continue
        t, s = np.linalg.solve(m, a - c)
        if t > 0 and -1e-6 <= s <= 1 + 1e-6:
            best = max(best, t)
    return best


def drape():
    reset(rig)
    mw = shirt.matrix_world
    P = np.array([mw @ v.co for v in shirt.data.vertices])
    names = {g.index: g.name for g in shirt.vertex_groups}
    arm = np.array([sum(g.weight for g in v.groups if names.get(g.group, '').startswith(('upperarm', 'lowerarm')))
                    for v in shirt.data.vertices])
    x, y, z = P.T
    torso = arm < 0.3
    fade = (1 - ramp(1.30, 1.38, z)) * (1 - ramp(0.05, 0.3, arm))
    new = P.copy()
    # 1. bridge: convex hull of each 3 cm slab of torso points
    for i in np.where(torso & (fade > 0))[0]:
        slab = torso & (np.abs(z - z[i]) < 0.015)
        xy = P[slab, :2]
        c = xy.mean(0)
        r = P[i, :2] - c
        n = np.linalg.norm(r)
        if n < 1e-4:
            continue
        rh = ray_to_hull(c, r / n, hull(xy))
        if rh > n:
            new[i, :2] = c + r / n * min(rh, n + 0.025)
    # 1b. tension: across the chest and belly front the fabric spans its peaks like a sheet (parabolic dilation in
    # the unrolled torso, 5 mm sag over 7 cm), so the pecs and the crease under them stop showing through
    yc0 = np.median(y[torso])
    cxy0 = np.array([np.median(x[torso]), yc0])
    rr0 = np.linalg.norm(new[:, :2] - cxy0, axis=1)
    s0 = np.arctan2(new[:, 1] - cxy0[1], new[:, 0] - cxy0[0]) * 0.17
    front = torso & (fade > 0) & (y < yc0) & (z > 1.0)
    for i in np.where(front)[0]:
        ds = np.abs((s0 - s0[i] + np.pi * 0.17) % (2 * np.pi * 0.17) - np.pi * 0.17)
        win = front & (ds < 0.10) & (np.abs(z - z[i]) < 0.10)
        need = np.max(rr0[win] - 1.0 * (ds[win] ** 2 + (z[win] - z[i]) ** 2))
        if need > rr0[i]:
            new[i, :2] = cxy0 + (new[i, :2] - cxy0) / rr0[i] * min(need, rr0[i] + 0.025)
    # 2. hang, around the torso axis: below a protrusion in the same column (8 degrees) the cloth may fall back
    # toward the axis by at most 0.3 per unit height (front, back and sides alike)
    yc = np.median(y[torso])
    cxy = np.array([np.median(x[torso]), yc])
    th = np.arctan2(new[:, 1] - cxy[1], new[:, 0] - cxy[0])
    for i in np.argsort(-z):  # top down, so a raised point carries further down the column
        if not (torso[i] and fade[i] > 0):
            continue
        dth = np.abs((th - th[i] + np.pi) % (2 * np.pi) - np.pi)
        col = torso & (dth < 0.14) & (z > z[i]) & (z < z[i] + 0.14)
        if not col.any():
            continue
        rr = np.linalg.norm(new[col, :2] - cxy, axis=1)
        need = np.max(rr - (z[col] - z[i]) * 0.3)
        ri = np.linalg.norm(new[i, :2] - cxy)
        if need > ri:
            new[i, :2] = cxy + (new[i, :2] - cxy) / ri * min(need, ri + 0.025)
    # 3. ease, smooth the displacement over the mesh, outward only, fade
    radial = np.c_[P[:, :2] - cxy, np.zeros(len(P))]
    radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-6)
    D = (new - P) + radial * 0.004 * torso[:, None]
    adj = [[] for _ in P]
    for e in shirt.data.edges:
        a, b = e.vertices
        adj[a].append(b)
        adj[b].append(a)
    for _ in range(6):
        D = 0.5 * D + 0.5 * np.array([D[a].mean(0) if a else D[i] for i, a in enumerate(adj)])
    D -= radial * np.minimum((D * radial).sum(1), 0)[:, None]  # outward only: drop any inward radial part
    D *= fade[:, None]
    # 4. sleeve hems: the stand-off band moves 40% of the way in
    edges = {}
    for f in shirt.data.polygons:
        for k in f.edge_keys:
            edges[k] = edges.get(k, 0) + 1
    bnd = np.array(sorted({i for k, c in edges.items() if c == 1 for i in k}))
    cuff_open = bnd[arm[bnd] > 0.5]
    bm = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    tree = BVHTree.FromPolygons([body.matrix_world @ v.co for v in bm.vertices], [list(f.vertices) for f in bm.polygons])
    hem = 0
    if len(cuff_open):
        for i in np.where(arm > 0.5)[0]:
            if np.min(np.linalg.norm(P[cuff_open] - P[i], axis=1)) > 0.03:
                continue
            loc, nrm, _, gap = tree.find_nearest(P[i])
            if loc is not None and gap > 0.006:
                D[i] += (np.array(loc) - P[i]) / gap * (0.4 * (gap - 0.004))
                hem += 1
    moved = np.linalg.norm(D, axis=1)
    big = np.argsort(-moved)[:12]
    print('largest moves (mm, x, y, z, arm):', [(round(float(moved[i] * 1000), 1), *np.round(P[i], 3).tolist(), round(float(arm[i]), 2)) for i in big])
    inv = np.array(mw.inverted().to_3x3())
    for v, d in zip(shirt.data.vertices, D):
        v.co += type(v.co)(inv @ d)
    shirt.data.update()
    stats = dict(moved_verts=int((moved > 1e-4).sum()), max_mm=round(float(moved.max() * 1000), 1),
                 mean_mm_moved=round(float(moved[moved > 1e-4].mean() * 1000), 1), hem_verts=hem,
                 collar_moved_max_mm=round(float(moved[(z > 1.38) & torso].max() * 1000), 3) if ((z > 1.38) & torso).any() else 0)
    print('drape', stats)
    assert stats['collar_moved_max_mm'] < 0.01, 'collar or shoulders moved'
    return stats


before = measure('BEFORE') if os.environ.get('FOA_SKIP_BEFORE') != '1' else {}
stats = drape()
# the pipeline's own posed easing (T1) for what the rest-pose drape cannot foresee, polo as the outer layer
# (polo over pants only: over the body it also eases toward a minimum gap at the collar, which must stay snug)
for inner in [i for o, i in garment_pairs(rig) if o is shirt]:
    ease_for_poses(shirt, inner, rig, pose_names=tuple(POSES))
after = measure('AFTER')
total_after = sum(r['outside'] for r in after.values())
report = dict(stats=stats, total_before=sum(r['outside'] for r in before.values()), total_after=total_after,
              before=before, after=after)
json.dump(report, open(OUT + '/report.json', 'w'), indent=1)
print(f"TOTAL outside verts: before {report['total_before']}, after {total_after}")
assert total_after == 0, 'clip counter not zero: not saved'
blend = 'P:/FoA-Assets/character/mpfb/teen/foa_teen_polo_drape.blend'
bpy.ops.wm.save_as_mainfile(filepath=blend)
print('saved', blend)
