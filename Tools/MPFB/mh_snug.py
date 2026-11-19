# Runs INSIDE MakeHuman via Tools/MPFB/mh_drive.py: pull the top of a worn garment (collar, shoulders, upper chest)
# in toward the body so it stops floating. Each vertex keeps its direction from the nearest skin point and its
# distance to the skin is scaled by s (S_COLLAR at the neck opening, S_SHOULDER below it, 1 by FADE_CM down), so
# double layers (collar bands, hems) keep their order. Rewrites the variant's .mhclo in place; refuses to run twice.
# Define TARGET (garment name), FOLDER (data/clothes/<folder>, holding <folder>.mhclo) before exec.
import os

import numpy as np
import getpath

S_COLLAR = globals().get("S_COLLAR", 0.35)
S_SHOULDER = globals().get("S_SHOULDER", 0.45)
FADE_CM = globals().get("FADE_CM", 22.0)
MIN_GAP_CM = globals().get("MIN_GAP_CM", 0.5)  # never closer to the skin than this (skin pokes through between verts)
MARK = "# foa_snug applied"
BODY_VERTS = 13380  # hm08: body skin verts come first, helper geometry after


def closest_on_tris(pt, a, b, c):
    """Ericson closest point from one point to many triangles; returns (points, distances)."""
    ab, ac, ap = b - a, c - a, pt - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp, cp = pt - b, pt - c
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        den = 1.0 / (va + vb + vc)
        res = a + ab * (vb * den)[:, None] + ac * (vc * den)[:, None]
        m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
        t = (d4 - d3) / ((d4 - d3) + (d5 - d6)); res[m] = (b + (c - b) * t[:, None])[m]
        m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        t = d2 / (d2 - d6); res[m] = (a + ac * t[:, None])[m]
        m = (d6 >= 0) & (d5 <= d6); res[m] = c[m]
        m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        t = d1 / (d1 - d3); res[m] = (a + ab * t[:, None])[m]
        m = (d3 >= 0) & (d4 <= d3); res[m] = b[m]
        m = (d1 <= 0) & (d2 <= 0); res[m] = a[m]
    return res, np.linalg.norm(res - pt, axis=1)


def smooth01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


path = getpath.getPath("data/clothes/%s/%s.mhclo" % (FOLDER, FOLDER))
text = open(path, encoding="utf-8").read()
assert MARK not in text, "already snugged; rebuild the variant first (mh_layer_fix.py), then snug once"
p = next(x for x in human.clothesProxies.values() if x.name == TARGET)
hco = human.getRestposeCoordinates()
unit = human.getHeightCm() / (hco[:, 1].max() - hco[:, 1].min())
co = p.getCoords()

# neck opening = the garment's highest boundary loop
f = np.asarray(p.object.getSeedMesh().fvert).astype(np.int64)
edges = {}
for row in f:
    ring = [row[0], row[1], row[2]] + ([row[3]] if row[3] != row[2] else [])
    for i in range(len(ring)):
        e = tuple(sorted((ring[i], ring[(i + 1) % len(ring)])))
        edges[e] = edges.get(e, 0) + 1
bverts = np.array(sorted({v for e, k in edges.items() if k == 1 for v in e}))
y_neck = np.percentile(co[bverts, 1], 97)  # top of the collar ring

d_below = (y_neck - co[:, 1]) * unit  # cm below the collar top
w = 1.0 - smooth01((d_below - 6.0) / (FADE_CM - 6.0))  # 1 down to the shoulders, 0 at FADE_CM
s = np.where(d_below < 3.0, S_COLLAR, S_SHOULDER + (S_COLLAR - S_SHOULDER) * (1 - smooth01((d_below - 3.0) / 3.0)))
s = 1.0 + (s - 1.0) * w
idx = np.nonzero(s < 0.999)[0]

# skin triangles near the region
bf = np.asarray(human.meshData.fvert).astype(np.int64)
bf = bf[(bf < BODY_VERTS).all(1)]
bt = np.vstack([bf[:, [0, 1, 2]], bf[bf[:, 2] != bf[:, 3]][:, [0, 2, 3]]])
cen = hco[bt].mean(1)
near = cen[:, 1] > co[idx, 1].min() - 5.0 / unit
a, b, c = hco[bt[near, 0]], hco[bt[near, 1]], hco[bt[near, 2]]

D = np.zeros_like(co)
dist_before = np.empty(len(idx))
for k, v in enumerate(idx):
    q, d = closest_on_tris(co[v], a, b, c)
    j = int(np.argmin(d))
    dist_before[k] = d[j]
    g = MIN_GAP_CM / unit  # strictly increasing in distance, so stacked layers (neck tape, collar) keep their order
    keep = d[j] if d[j] <= g else g + (d[j] - g) * s[v]
    D[v] = (q[j] + (co[v] - q[j]) * (keep / max(d[j], 1e-9))) - co[v]
g_ = MIN_GAP_CM / unit
dist_after = np.where(dist_before <= g_, dist_before, g_ + (dist_before - g_) * s[idx])
# The collar band (top 2 cm) is folded double: scaling it toward the skin crushes its layers through each other.
# Move it rigidly with the neckline just below instead (mean D of its 3 nearest verts 2-4 cm down).
BAND_CM = 1.5
band = np.nonzero(d_below < BAND_CM)[0]
ring = np.nonzero((d_below >= BAND_CM) & (d_below < BAND_CM + 2.0))[0]
for v in band:  # blend: rigid with the ring at the collar top, its own snug at the band's bottom edge (no seam)
    nn = ring[np.argsort(np.linalg.norm(co[ring] - co[v], axis=1))[:3]]
    t = smooth01(d_below[v] / BAND_CM)
    D[v] = D[nn].mean(0) * (1 - t) + D[v] * t
print("collar band verts moved rigidly:", len(band))
print("snug verts", len(idx), "skin gap cm before p50/p90 %.2f/%.2f  after p50/p90 %.2f/%.2f  min after %.2f" % (
    np.median(dist_before) * unit, np.percentile(dist_before, 90) * unit,
    np.median(dist_after) * unit, np.percentile(dist_after, 90) * unit, dist_after.min() * unit))

M = p.tmatrix.getMatrix(hco)
off = (np.linalg.inv(M) @ (M @ p.offsets.T + D.T)).T
out, vi, in_verts = [], 0, False
for ln in text.splitlines():
    w_ = ln.split()
    if ln.startswith("verts"):
        in_verts = True; out.append(ln); continue
    if in_verts and w_ and w_[0].lstrip("-").isdigit():
        r, wt = p.ref_vIdxs[vi], p.weights[vi]
        if len(w_) == 1 and not D[vi].any():
            out.append(ln)
        else:
            out.append("%d %d %d %.5f %.5f %.5f %.5f %.5f %.5f" % (r[0], r[1], r[2], wt[0], wt[1], wt[2], *off[vi]))
        vi += 1
        continue
    in_verts = in_verts and not (w_ and not w_[0].lstrip("-").replace(".", "").isdigit())
    out.append(ln)
assert vi == len(co), (vi, len(co))
open(path, "w", encoding="utf-8").write(MARK + "\n" + "\n".join(out) + "\n")
cpath = os.path.splitext(path)[0] + ".mhpxy"
if os.path.exists(cpath):
    os.remove(cpath)  # stale compiled cache would win over the edited text

cl = G.getTask("Geometries", "Clothes")
cl.proxyFileDeselected(path)
cl.proxyFileSelected(path)
fresh = next(x for x in human.clothesProxies.values() if x.name == TARGET).getCoords()
print("fit error cm %.4f" % (np.abs(fresh - (co + D)).max() * unit))
G.redraw()
