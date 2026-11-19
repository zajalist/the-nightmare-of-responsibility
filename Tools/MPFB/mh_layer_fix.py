# Runs INSIDE MakeHuman via Tools/MPFB/mh_drive.py @Tools/MPFB/mh_layer_fix.py
# Writes an FoA variant of an OUTER garment (the tee) that drapes GAP_CM outside the inner garment (the pants) where
# they overlap, fading back to the original fit FADE_CM above the waistband. The inner garment is untouched, so it
# keeps covering the skin. The fix is baked into the .mhclo offsets: it still auto-fits any body, in MakeHuman and MPFB.
# Red-proven: poke-through count printed for the original pair (must be > 0) and for the variant (must be 0).
import os
import shutil
import uuid as uuidlib

import numpy as np
import getpath

# Override any of these by defining them before exec (e.g. OUTER, SRC_FOLDER, NEW_NAME, NEW_DISPLAY).
OUTER = globals().get("OUTER", "crude_male_shirt")
INNER = globals().get("INNER", "Pants_Wool")
SRC_FOLDER = globals().get("SRC_FOLDER", "elvs_crude_t-shirt_male")
SRC_DIR = getpath.getPath("data/clothes/" + SRC_FOLDER)
SRC_MHCLO = SRC_FOLDER + ".mhclo"
NEW_NAME = globals().get("NEW_NAME", "foa_crude_tee_layered")
NEW_DISPLAY = globals().get("NEW_DISPLAY", "FoA_Crude_Tee_Layered")
GAP_CM, FADE_CM = 0.5, 5.0


def proxy(name):
    for p in human.clothesProxies.values():
        if p.name == name:
            return p
    raise RuntimeError("not worn: " + name)


def fvert_of(p):
    return np.asarray(p.object.getSeedMesh().fvert).astype(np.int64)  # uint32 in MakeHuman; we need signed


def tris_of(f):
    quads = f[:, 2] != f[:, 3]
    return np.vstack([f[:, [0, 1, 2]], f[quads][:, [0, 2, 3]]])


def boundary_loops(f):
    edges = {}
    for row in f:
        ring = [row[0], row[1], row[2]] + ([row[3]] if row[3] != row[2] else [])
        for i in range(len(ring)):
            e = tuple(sorted((ring[i], ring[(i + 1) % len(ring)])))
            edges[e] = edges.get(e, 0) + 1
    adj = {}
    for e, k in edges.items():
        if k == 1:
            adj.setdefault(e[0], []).append(e[1]); adj.setdefault(e[1], []).append(e[0])
    loops, seen = [], set()
    for v in adj:
        if v in seen:
            continue
        stack, loop = [v], []
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x); loop.append(x); stack.extend(adj[x])
        loops.append(loop)
    return loops


class Surface:
    """Triangles of one garment, with per-triangle normals oriented away from the torso axis (winding is mixed)."""

    def __init__(self, co, f, axis):
        t = tris_of(f)
        self.co, self.f, self.t = co, f, t
        self.a, self.b, self.c = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]
        n = np.cross(self.b - self.a, self.c - self.a)
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        radial = (self.a + self.b + self.c) / 3.0 - np.array([axis[0], 0, axis[1]])
        radial[:, 1] = 0
        n[np.einsum("ij,ij->i", radial, n) < 0] *= -1
        self.n, self.axis = n, axis

    def loop_y(self, loop, pts):
        """Height of a boundary loop at the angle of each point around the torso axis."""
        lc = self.co[loop]
        ang = np.arctan2(lc[:, 0] - self.axis[0], lc[:, 2] - self.axis[1])
        o = np.argsort(ang)
        pa = np.arctan2(pts[:, 0] - self.axis[0], pts[:, 2] - self.axis[1])
        return np.interp(pa, ang[o], lc[o, 1], period=2 * np.pi)

    def ray_out(self, o, d):
        """Distance along each horizontal ray o+t*d to the OUTERMOST hit (nan = no hit), and that triangle's verts."""
        e1, e2 = self.b - self.a, self.c - self.a
        out = np.full(len(o), np.nan)
        tri = np.full((len(o), 3), -1)
        for i in range(len(o)):
            pv = np.cross(d[i], e2); det = (e1 * pv).sum(1)
            ok = np.abs(det) > 1e-12
            inv = 1.0 / np.where(ok, det, 1.0)
            tv = o[i] - self.a
            u = (tv * pv).sum(1) * inv
            q = np.cross(tv, e1)
            v = (q * d[i]).sum(1) * inv
            t = (q * e2).sum(1) * inv
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
            if hit.any():
                k = np.nonzero(hit)[0][np.argmax(t[hit])]
                out[i], tri[i] = t[k], self.t[k]
        return out, tri


def samples(f, co):
    """Vertices plus face centres and edge midpoints, so pokes between vertices are caught too."""
    t = tris_of(f)
    a, b, c = co[t[:, 0]], co[t[:, 1]], co[t[:, 2]]
    return np.vstack([co, (a + b + c) / 3, (a + b) / 2, (b + c) / 2, (a + c) / 2])


def pokes(outer_co, inner_co):
    """Inner-garment sample points not at least 1 mm inside the OUTERMOST outer surface, measured radially from
    the torso axis, wherever the outer garment covers them. Returns points, shortfall (units), hit-triangle verts, n."""
    out = Surface(outer_co, of, axis)
    pts = samples(inf, inner_co)
    pts = pts[pts[:, 1] > out.loop_y(hem, pts) + 0.3 / unit]
    ang = np.arctan2(pts[:, 0] - axis[0], pts[:, 2] - axis[1])
    d = np.c_[np.sin(ang), np.zeros_like(ang), np.cos(ang)]
    r_hit, tri = out.ray_out(np.c_[np.full(len(pts), axis[0]), pts[:, 1], np.full(len(pts), axis[1])], d)
    r_pt = np.hypot(pts[:, 0] - axis[0], pts[:, 2] - axis[1])
    cov = ~np.isnan(r_hit)
    short = r_pt - (r_hit - 0.1 / unit)
    bad = cov & (short > 0)
    return pts[bad], short[bad], tri[bad], int(cov.sum())


# start from the original pair (undo an earlier run, and the retired pants variant)
cl = G.getTask("Geometries", "Clothes")
for nm, src in ((NEW_DISPLAY, os.path.join(SRC_DIR, SRC_MHCLO)),
                ("FoA_Pants_Wool_Layered", getpath.getPath("data/clothes/toigo_wool_pants/toigo_wool_pants.mhclo"))):
    if any(p.name == nm for p in human.clothesProxies.values()):
        cl.proxyFileDeselected(next(p.file for p in human.clothesProxies.values() if p.name == nm))
        cl.proxyFileSelected(src)
retired = getpath.getPath("data/clothes/foa_wool_pants_layered")
if os.path.isdir(retired):
    shutil.rmtree(retired)

hco = human.getRestposeCoordinates()
unit = human.getHeightCm() / (hco[:, 1].max() - hco[:, 1].min())  # cm per MakeHuman unit
outer, inner = proxy(OUTER), proxy(INNER)
of, inf = fvert_of(outer), fvert_of(inner)
oco, ico = outer.getCoords(), inner.getCoords()
hem = min(boundary_loops(of), key=lambda L: oco[L, 1].mean())
axis = (oco[hem, 0].mean(), oco[hem, 2].mean())
top = max(boundary_loops(inf), key=lambda L: ico[L, 1].mean())  # pants waistband edge

bad, _, _, ncov = pokes(oco, ico)
print("BEFORE pokes", len(bad), "of", ncov)

# Grow the tee radially (horizontal, away from the axis) to GAP_CM outside the pants; fade out above the waistband.
pants = Surface(ico, inf, axis)
ang = np.arctan2(oco[:, 0] - axis[0], oco[:, 2] - axis[1])
dirs = np.c_[np.sin(ang), np.zeros_like(ang), np.cos(ang)]
r_o = np.hypot(oco[:, 0] - axis[0], oco[:, 2] - axis[1])
ytop = pants.loop_y(top, oco)
region = np.nonzero(oco[:, 1] < ytop + FADE_CM / unit)[0]
yev = np.minimum(oco[region, 1], ytop[region] - 0.3 / unit)
r_in, _ = pants.ray_out(np.c_[np.full(len(region), axis[0]), yev, np.full(len(region), axis[1])], dirs[region])
need = np.where(np.isnan(r_in), 0.0, np.maximum(0.0, r_in + GAP_CM / unit - r_o[region]))
x = np.clip((oco[region, 1] - ytop[region]) / (FADE_CM / unit), 0.0, 1.0)
w = 1.0 - x * x * (3 - 2 * x)  # smoothstep: 1 at the waistband and below, 0 at FADE_CM above
r_new = r_o.copy()
r_new[region] += need * w
if globals().get("DIAG"):
    nz = need[need > 0] * unit
    hy_o = Surface(oco, of, axis).loop_y(hem, oco[region])
    print("need cm: n=%d p50=%.2f p90=%.2f max=%.2f" % (len(nz), *np.percentile(nz, [50, 90, 100])) if len(nz) else "need: none")
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 30)):
        m = ((oco[region, 1] - hy_o) * unit >= lo) & ((oco[region, 1] - hy_o) * unit < hi) & (need > 0)
        print("  %2d-%2d cm above hem: %3d verts need, max %.2f cm" % (lo, hi, m.sum(), need[m].max() * unit if m.any() else 0))
    raise RuntimeError("DIAG only")

for it in range(6):  # monotonic: radii only grow, capped, so it cannot diverge
    D = dirs * (r_new - r_o)[:, None]
    bad, short, tri, _ = pokes(oco + D, ico)
    print("refine pass", it, "poking samples", len(bad))
    if not len(bad):
        break
    for sh, tv in zip(short, tri):
        tv = tv[tv >= 0]
        r_new[tv] = np.minimum(r_o[tv] + 2.5 / unit, r_new[tv] + sh + 0.2 / unit)
D = dirs * (r_new - r_o)[:, None]

# new offsets: world offset M@off + D, back through M^-1
M = outer.tmatrix.getMatrix(hco)
off = (np.linalg.inv(M) @ (M @ outer.offsets.T + D.T)).T

dst = getpath.getPath("data/clothes/" + NEW_NAME)
os.makedirs(dst, exist_ok=True)
for fn in os.listdir(SRC_DIR):
    if fn.endswith((".obj", ".mhmat", ".png", ".thumb")):
        if fn.endswith(".mhmat") and os.path.exists(os.path.join(dst, fn)):
            continue  # keep the FoA material edits (e.g. the matte polo)
        shutil.copy2(os.path.join(SRC_DIR, fn), dst)
out, vi, in_verts = [], 0, False
for ln in open(os.path.join(SRC_DIR, SRC_MHCLO), encoding="utf-8").read().splitlines():
    w_ = ln.split()
    if ln.startswith("verts"):
        in_verts = True; out.append(ln); continue
    if in_verts and w_ and w_[0].lstrip("-").isdigit():
        r, wt = outer.ref_vIdxs[vi], outer.weights[vi]
        if len(w_) == 1 and not D[vi].any():
            out.append(ln)
        else:
            out.append("%d %d %d %.5f %.5f %.5f %.5f %.5f %.5f" % (r[0], r[1], r[2], wt[0], wt[1], wt[2], *off[vi]))
        vi += 1
        continue
    in_verts = in_verts and not (w_ and not w_[0].lstrip("-").replace(".", "").isdigit())
    if w_ and w_[0] == "uuid":
        ln = "uuid " + str(uuidlib.uuid5(uuidlib.NAMESPACE_URL, "foa/" + NEW_NAME))
    elif w_ and w_[0] == "name":
        ln = "name " + NEW_DISPLAY
    out.append(ln)
assert vi == len(oco), (vi, len(oco))
path = os.path.join(dst, NEW_NAME + ".mhclo")
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")

# swap it in and re-check on a fresh fit
cl.proxyFileDeselected(os.path.join(SRC_DIR, SRC_MHCLO))
cl.proxyFileSelected(path)
fresh = proxy(NEW_DISPLAY).getCoords()
bad, _, _, ncov = pokes(fresh, proxy(INNER).getCoords())
G.redraw()
print("AFTER pokes", len(bad), "of", ncov, "fit error cm %.4f" % (np.abs(fresh - (oco + D)).max() * unit),
      "moved verts", int((np.abs(D).sum(1) > 1e-9).sum()), "max move cm %.2f" % (np.linalg.norm(D, axis=1).max() * unit))
if len(bad):
    fo = Surface(fresh, of, axis)
    for pt in bad:
        print("  poke at angle %.0f deg, %.2f cm above hem, %.2f cm above pants top" % (
            np.degrees(np.arctan2(pt[0] - axis[0], pt[2] - axis[1])),
            (pt[1] - fo.loop_y(hem, pt[None])[0]) * unit, (pt[1] - pants.loop_y(top, pt[None])[0]) * unit))
assert len(bad) == 0, "pokes remain"
