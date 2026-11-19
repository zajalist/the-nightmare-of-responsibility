"""Builds the bedroom rugs as glTF (mesh + baked PBR textures). Runs outside the editor; import_dressing.py imports them.

  python Tools/Unreal/make_rugs.py [out_dir]      (default P:/FoA-Assets/dressing)
  python Tools/Unreal/make_rugs.py --selftest

A rug is a ~1 cm slab with a rounded binding, 2.5 cm corner radius, a soft kick-wrinkle, optionally one curled corner,
and knotted fringe on its short ends. The top texture is composed in rug space, so the border bands follow the edges and
miter at the corners like a woven rug, from two CC0 Poly Haven sets (P:/FoA-Assets/polyhaven/MANIFEST.md):
floral_jacquard gives the motif shapes, dirty_carpet the pile, grime and roughness.
Authored in Unreal space (cm, X along the rug's length, Z up); pivot at the center of the bottom, which rests on z = 0.
Needs numpy and Pillow.
"""
import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

PH = "P:/FoA-Assets/polyhaven/textures"
D = 14.0  # working texture density, px per cm (1400 px/m); the final textures are resampled from it
JAQ_TILE = (25.3, 38.4)  # floral_jacquard tile, cm (API dimensions)
CARPET_TILE = 60.0       # dirty_carpet tile, cm

RED, NAVY, IVORY = (128, 40, 36), (32, 40, 68), (200, 186, 152)
GOLD, DARK, ROSE = (168, 128, 74), (24, 22, 24), (172, 96, 74)

RUGS = [
    {   # large worn rug beside the bed: Heriz-like layout, one curled corner, a kick-wrinkle
        "name": "SM_Rug_Bedside", "L": 180.0, "W": 120.0, "tex": (2048, 2048), "seed": 7,
        "bands": [(0.0, 1.0, "binding", (40, 40, 54), None, None, 0),
                  (1.0, 2.8, "motif", IVORY, RED, DARK, 0.12),
                  (2.8, 3.3, "line", DARK, None, None, 0),
                  (3.3, 14.5, "motif", NAVY, IVORY, RED, 0.44),
                  (14.5, 15.0, "line", DARK, None, None, 0),
                  (15.0, 16.8, "motif", GOLD, NAVY, DARK, 0.12),
                  (16.8, 17.3, "line", DARK, None, None, 0)],
        "field": (RED, NAVY, IVORY, 2.0, 0.3), "medallion": (IVORY, RED, NAVY, 1.0, 40.0, 26.0), "spandrels": True,
        # placed at yaw 90 with its -X third under the bed: wear where feet land, wrinkle and curl on the open end
        "wear": (85.0, 66.0, 60.0, 28.0, 0.65), "stain": (140.0, 22.0, 4.2),
        "ripple": (130.0, 52.0, -50.0, 1.4, 5.0, 38.0), "curl": (1, 1, 3.2, 24.0),
    },
    {   # small rug inside the door: lighter field, striped border, dirtier where shoes land
        "name": "SM_Rug_Door", "L": 90.0, "W": 60.0, "tex": (1024, 1024), "seed": 3,
        "bands": [(0.0, 0.9, "binding", (46, 40, 38), None, None, 0),
                  (0.9, 2.0, "line", IVORY, None, None, 0),
                  (2.0, 2.4, "line", DARK, None, None, 0),
                  (2.4, 7.6, "motif", RED, IVORY, DARK, 0.2),
                  (7.6, 8.0, "line", DARK, None, None, 0),
                  (8.0, 9.0, "line", GOLD, None, None, 0)],
        "field": (IVORY, NAVY, ROSE, 0.55, 0.5), "medallion": None, "spandrels": False,
        "wear": (45.0, 18.0, 35.0, 14.0, 0.8), "stain": None,  # shoes land on the door side (local -Y)
        "ripple": (55.0, 20.0, 115.0, 0.9, 3.5, 16.0), "curl": None,
    },
]


# ---------- texture composition ----------

def _load(path, size=None):
    im = Image.open(path)
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


def _lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _fbm(shape, rng, cells, octaves=4):
    h, w = shape
    out, amp, total = np.zeros(shape, np.float32), 1.0, 0.0
    for _ in range(octaves):
        grid = rng.random((cells + 1, max(2, int(cells * w / h) + 1))).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(grid, "F").resize((w, h), Image.BICUBIC))
        total, amp, cells = total + amp, amp * 0.5, cells * 2
    out /= total
    return (out - out.min()) / max(1e-6, out.max() - out.min())


class Sources:
    """The two Poly Haven sets, pre-scaled so every lookup at density D is a 1:1 integer fetch (no aliasing)."""

    def __init__(self):
        jaq = _lum(_load(f"{PH}/floral_jacquard/floral_jacquard_diff_2k.jpg"))
        self.jaq_full = jaq
        self.jaq_q = np.percentile(jaq, np.arange(101))  # luminance quantiles, to set how much area the motif covers
        self._tiles = {}
        n = int(round(CARPET_TILE * D))
        base = f"{PH}/dirty_carpet/dirty_carpet"
        cl = _lum(_load(f"{base}_diff_2k.jpg", (n, n)))
        self.pile = cl / cl.mean()
        self.normal = _load(f"{base}_nor_gl_2k.jpg", (n, n)) * 2.0 - 1.0
        rough = _load(f"{base}_rough_2k.jpg", (n, n))
        self.rough = rough[..., 0] if rough.ndim == 3 else rough

    def motif(self, k, cover=0.5):
        """floral_jacquard as a 0..1 motif mask (one tile = k x its real size); about `cover` of the area is motif."""
        if (k, cover) not in self._tiles:
            w, h = int(round(JAQ_TILE[0] * k * D)), int(round(JAQ_TILE[1] * k * D))
            t = np.asarray(Image.fromarray(self.jaq_full, "F").resize((w, h), Image.LANCZOS))
            c = int(round(100 * (1.0 - cover)))
            lo, hi = self.jaq_q[max(0, c - 12)], self.jaq_q[min(100, c + 12)]
            self._tiles[(k, cover)] = np.clip((t - lo) / (hi - lo), 0.0, 1.0)
        return self._tiles[(k, cover)]


def _fetch(tile, x_cm, y_cm):
    h, w = tile.shape[:2]
    return tile[np.mod(np.floor(y_cm * D).astype(np.int64), h), np.mod(np.floor(x_cm * D).astype(np.int64), w)]


def _paint(mask, ground, motif, outline):
    """Ground -> outline -> motif across the motif mask's soft edge, so every shape gets a thin knotted outline."""
    a, b = _smooth(0.18, 0.42, mask)[..., None], _smooth(0.58, 0.82, mask)[..., None]
    g, o, m = (np.array(c, np.float32) / 255.0 for c in (ground, outline, motif))
    return (g * (1 - a) + o * a) * (1 - b) + m * b


def compose(spec, src):
    """Returns (albedo, normal, orm) uint8 images at spec['tex'] for the rug's top face (cols = length, rows = width)."""
    L, W = spec["L"], spec["W"]
    cols, rows = int(round(L * D)), int(round(W * D))
    u = (np.arange(cols, dtype=np.float32) + 0.5) / D
    v = (np.arange(rows, dtype=np.float32) + 0.5) / D
    U, V = np.meshgrid(u, v)
    du, dv = np.minimum(U, L - U), np.minimum(V, W - V)
    d = np.minimum(du, dv)
    s = np.where(dv <= du, U, V)  # coordinate along the nearest edge; switching on the diagonal mitres the corners
    rng = np.random.default_rng(spec["seed"])

    color = np.zeros((rows, cols, 3), np.float32)
    inner = 0.0
    for t0, t1, kind, ground, motif, outline, k in spec["bands"]:
        sel = (d >= t0) & (d < t1)
        if kind == "motif":
            mask = _fetch(src.motif(k, 0.4), np.abs(d - (t0 + t1) / 2), s)  # mirrored across the band
            col = _paint(mask, ground, motif, outline)
        else:
            col = np.broadcast_to(np.array(ground, np.float32) / 255.0, color.shape).copy()
            if kind == "binding":  # overcast stitches wrapped around the edge cord
                col *= (0.8 + 0.2 * np.sin(2 * np.pi * s / 0.3))[..., None]
        color[sel] = col[sel]
        inner = max(inner, t1)

    fx, fy = np.abs(U - L / 2), np.abs(V - W / 2)  # four-way mirrored field, like a real rug's symmetric design
    field = d >= inner
    ground, motif, outline, k, cover = spec["field"]
    color[field] = _paint(_fetch(src.motif(k, cover), fx, fy), ground, motif, outline)[field]
    step = lambda x: np.floor(x / 0.8) * 0.8  # noqa: E731  stepped outlines, as knotted rows make them
    flat = lambda c: np.array(c, np.float32) / 255.0  # noqa: E731
    if spec["spandrels"]:  # quarter medallions in the field corners
        gx, gy = (L / 2 - inner) - fx, (W / 2 - inner) - fy
        q = step(gx) / (0.22 * L) + step(gy) / (0.3 * W)
        sp = field & (q < 1.0)
        color[sp] = _paint(_fetch(src.motif(1.0, 0.35), gx, gy), IVORY, RED, NAVY)[sp]
        color[field & (q >= 1.0) & (q < 1.05)] = flat(NAVY)
    if spec["medallion"]:
        mg, mm, mo, mk, a, b = spec["medallion"]
        q = step(fx) / a + step(fy) / b
        pend = np.abs(step(fx) - (a + 9.0)) / 8.0 + step(fy) / 6.0  # pendants at both ends
        med = field & ((q < 1.0) | (pend < 1.0))
        color[med] = _paint(_fetch(src.motif(mk, 0.35), fx, fy), mg, mm, mo)[med]
        ring = field & ~med & ((q < 1.05) | (pend < 1.12))
        color[ring] = flat(NAVY)
        color[field & ~med & ~ring & ((q < 1.075) | (pend < 1.2))] = flat(GOLD)
        color[field & (q < 0.18)] = _paint(_fetch(src.motif(0.5, 0.4), fx, fy), NAVY, IVORY, RED)[field & (q < 0.18)]

    # ---- age: sun fade, pile, dust at the edges, grime blotches, a walked-through patch, a cup ring ----
    abrash = np.asarray(Image.fromarray(rng.random((1, 7)).astype(np.float32), "F").resize((cols, 1), Image.BICUBIC))
    color *= (0.93 + 0.14 * abrash)[..., None]
    lum = _lum(color)[..., None]
    color = color * 0.72 + lum * 0.28  # sun-faded: old rugs read lighter and greyer than new ones
    color = color * 0.84 + 0.075
    pile = _fetch(src.pile, U, V)
    color *= (1.0 + 0.55 * (pile - 1.0))[..., None]
    color *= (1.0 - 0.14 * np.exp(-d / 5.0))[..., None]
    blot = _fbm((rows, cols), rng, 4)
    color *= (1.0 - 0.22 * _smooth(0.55, 0.9, blot))[..., None]
    wu, wv, ru, rv, amt = spec["wear"]
    region = np.exp(-(((U - wu) / ru) ** 2 + ((V - wv) / rv) ** 2))
    worn = np.clip(region * (0.45 + 0.9 * _fbm((rows, cols), rng, 8)) - 0.25, 0.0, 1.0) * amt
    foundation = np.array((150, 138, 118), np.float32) / 255.0 * (0.7 + 0.3 * pile[..., None])
    color = color * (1 - worn[..., None] * 0.75) + (color * 0.35 + foundation * 0.65) * (worn[..., None] * 0.75)
    if spec["stain"]:
        su, sv, sr = spec["stain"]
        r = np.hypot(U - su, V - sv)
        ring = 0.32 * np.exp(-((r - sr) / 0.35) ** 2) + 0.1 * (r < sr)
        color *= 1.0 - ring[..., None] * np.array((0.8, 0.9, 1.0), np.float32)
    albedo = np.clip(color, 0.0, 1.0)

    n = _fetch(src.normal, U, V).copy()
    n[..., :2] *= (1.0 - 0.6 * worn)[..., None]
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rough = np.clip(0.06 + 0.94 * _fetch(src.rough, U, V) - 0.08 * worn, 0.55, 1.0)
    ao = np.clip(0.62 + 0.38 * pile, 0.5, 1.0)
    orm = np.stack([ao, rough, np.zeros_like(ao)], axis=-1)

    size = spec["tex"]
    to8 = lambda a: np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)  # noqa: E731
    out_a = Image.fromarray(to8(albedo)).resize(size, Image.LANCZOS)
    out_n = np.asarray(Image.fromarray(to8(n * 0.5 + 0.5)).resize(size, Image.LANCZOS), np.float32) / 127.5 - 1.0
    out_n /= np.linalg.norm(out_n, axis=-1, keepdims=True)
    out_o = Image.fromarray(to8(orm)).resize(size, Image.LANCZOS)
    return out_a, Image.fromarray(to8(out_n * 0.5 + 0.5)), out_o


# ---------- mesh ----------

def _height_fields(spec):
    """Bottom height b(x, y) >= 0 in rug-local cm (origin at the rug center)."""
    L, W = spec["L"], spec["W"]
    ph = spec["seed"] * 1.7

    def bottom(x, y):
        b = 0.18 * (np.sin(x / 9.0 + ph) * np.sin(y / 7.0 - ph) + 0.6 * np.sin((x + y) / 13.0 + 2 * ph))
        cu, cv, ang, amp, sig, half = spec["ripple"]
        px, py = cu - L / 2, cv - W / 2
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        along = (x - px) * dx + (y - py) * dy
        across = -(x - px) * dy + (y - py) * dx
        win = _smooth(-half, -half + 10.0, along) * (1.0 - _smooth(half - 10.0, half, along))
        b = b + amp * np.exp(-(across / sig) ** 2) * win
        if spec["curl"]:
            sx, sy, lift, reach = spec["curl"]
            diag = ((sx * L / 2 - x) * sx + (sy * W / 2 - y) * sy) / math.sqrt(2.0)
            b = b + lift * np.clip(1.0 - diag / reach, 0.0, 1.0) ** 2
        return np.maximum(b, 0.0)

    return bottom


def build_mesh(spec, step=2.5, radius=2.5, thick=1.0):
    """Returns primitives [(pos, nrm, uv, tris), ...]: 0 = rug body, 1 = fringe. Arrays in Unreal cm."""
    L, W = spec["L"], spec["W"]
    bottom = _height_fields(spec)
    nu, nv = int(math.ceil(L / step)), int(math.ceil(W / step))
    gu, gv = np.meshgrid(np.linspace(0, L, nu + 1), np.linspace(0, W, nv + 1), indexing="ij")
    x, y = gu - L / 2, gv - W / 2
    cx, cy = L / 2 - radius, W / 2 - radius  # pull the square corners onto 2.5 cm arcs
    ox, oy = np.maximum(np.abs(x) - cx, 0.0), np.maximum(np.abs(y) - cy, 0.0)
    r = np.hypot(ox, oy)
    k = np.where(r > radius, radius / np.maximum(r, 1e-9), 1.0)
    x = np.sign(x) * (np.minimum(np.abs(x), cx) + ox * k)
    y = np.sign(y) * (np.minimum(np.abs(y), cy) + oy * k)
    zb = bottom(x, y)
    dedge = np.minimum(np.minimum(gu, L - gu), np.minimum(gv, W - gv))
    zt = zb + thick * (0.8 + 0.2 * _smooth(0.6, 2.0, dedge))  # pile stands a little proud of the binding

    def grid_normals(z, up):
        gx, gy = np.gradient(z, axis=0), np.gradient(z, axis=1)
        ex = np.stack([np.gradient(x, axis=0), np.gradient(y, axis=0), gx], -1)
        ey = np.stack([np.gradient(x, axis=1), np.gradient(y, axis=1), gy], -1)
        nrm = np.cross(ex, ey)
        nrm *= np.sign(nrm[..., 2:3]) * (1 if up else -1)
        return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)

    nverts = (nu + 1) * (nv + 1)
    idx = np.arange(nverts).reshape(nu + 1, nv + 1)
    uv = np.stack([gu / L, gv / W], -1).reshape(-1, 2)
    pos = [np.stack([x, y, zt], -1).reshape(-1, 3), np.stack([x, y, zb], -1).reshape(-1, 3)]
    nrm = [grid_normals(zt, True).reshape(-1, 3), grid_normals(zb, False).reshape(-1, 3)]
    uvs = [uv, uv]
    a, b, c, dd = idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()
    quads = np.concatenate([np.stack([a, b, c], -1), np.stack([a, c, dd], -1)])
    tris = [quads, quads + nverts]

    # binding: a half-round cord joining the top and bottom boundary loops (welded to both)
    ring = np.concatenate([idx[:, 0], idx[-1, 1:], idx[-2::-1, -1], idx[0, -2:0:-1]])
    P = pos[0][ring]
    tang = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    out = np.stack([tang[:, 1], -tang[:, 0], np.zeros(len(P))], -1)
    out /= np.linalg.norm(out, axis=-1, keepdims=True)
    out *= np.sign(np.sum(out[:, :2] * P[:, :2], -1))[:, None]  # face away from the rug center
    top_z, bot_z = pos[0][ring, 2], pos[1][ring, 2]
    loops = [ring]
    base = 2 * nverts
    side_p, side_n, side_uv = [], [], []
    for j, th in enumerate((math.pi / 4, math.pi / 2, 3 * math.pi / 4)):
        bulge = 0.3 * (top_z - bot_z)
        p = P.copy()
        p[:, :2] += out[:, :2] * (bulge * math.sin(th))[:, None]
        p[:, 2] = bot_z + (top_z - bot_z) * (1 + math.cos(th)) / 2
        side_p.append(p)
        side_n.append(out * math.sin(th) + np.array([0, 0, math.cos(th)]))
        side_uv.append(uv[ring])
        loops.append(base + j * len(ring) + np.arange(len(ring)))
    loops.append(ring + nverts)
    pos.append(np.concatenate(side_p))
    nrm.append(np.concatenate(side_n))
    uvs.append(np.concatenate(side_uv))
    for l0, l1 in zip(loops[:-1], loops[1:]):
        n0, n1 = np.roll(l0, -1), np.roll(l1, -1)
        tris.append(np.concatenate([np.stack([l0, n0, n1], -1), np.stack([l0, n1, l1], -1)]))
    body = (np.concatenate(pos), np.concatenate(nrm), np.concatenate(uvs), np.concatenate(tris))
    return [body, fringe(spec, bottom)]


def fringe(spec, bottom, pitch=0.42, width=0.22, segs=4):
    """Knotted fringe on both short ends: tassels of 6 strands that splay a little and lie on the floor."""
    L, W = spec["L"], spec["W"]
    rng = np.random.default_rng(spec["seed"] + 100)
    pos, nrm, uv, tris = [], [], [], []
    for end in (-1.0, 1.0):
        ys = np.arange(-W / 2 + 3.0, W / 2 - 3.0, pitch)
        tassel_ang = 0.0
        for i, y0 in enumerate(ys):
            if i % 6 == 0:
                tassel_ang = rng.normal(0.0, 0.1)
            ang = tassel_ang + rng.normal(0.0, 0.035) + (i % 6 - 2.5) * 0.012
            length = 7.5 + rng.normal(0.0, 0.7)
            bend = rng.normal(0.0, 0.006)
            x0 = end * (L / 2 - 0.4)
            z0 = float(bottom(np.array(x0), np.array(y0))) + 0.45
            d = np.array([end * math.cos(ang), math.sin(ang), 0.0])
            side = np.array([-d[1], d[0], 0.0])
            base = sum(len(p) for p in pos)
            pts, ns = [], []
            for kk in range(segs + 1):
                t = length * kk / segs
                c = np.array([x0, y0, 0.0]) + d * t + side * bend * t * t
                c[2] = 0.11 + (z0 - 0.11) * math.exp(-t / 1.2)
                for sgn in (-1.0, 1.0):  # tilted normals fake a round strand on a flat ribbon
                    pts.append(c + side * sgn * width / 2)
                    nn = np.array([0, 0, 0.8]) + side * sgn * 0.6
                    ns.append(nn / np.linalg.norm(nn))
            pos.append(np.array(pts))
            nrm.append(np.array(ns))
            uv.append(np.array([[kk / segs, sgn * 0.5 + 0.5] for kk in range(segs + 1) for sgn in (-1, 1)]))
            for kk in range(segs):
                q = base + 2 * kk
                tris.append([[q, q + 2, q + 3], [q, q + 3, q + 1]])
    return (np.concatenate(pos), np.concatenate(nrm), np.concatenate(uv),
            np.array(tris, dtype=np.int64).reshape(-1, 3))


# ---------- glTF ----------

def _orient(gp, gn, tris):
    """glTF front faces are counter-clockwise: flip any triangle whose winding disagrees with its vertex normals."""
    p0, p1, p2 = gp[tris[:, 0]], gp[tris[:, 1]], gp[tris[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    want = gn[tris[:, 0]] + gn[tris[:, 1]] + gn[tris[:, 2]]
    flip = np.sum(cr * want, -1) < 0
    out = tris.copy()
    out[flip, 1], out[flip, 2] = tris[flip, 2], tris[flip, 1]
    return out


def write_rug(out_dir, spec, prims, images):
    name = spec["name"]
    short = name.replace("SM_", "")
    folder = os.path.join(out_dir, short)
    os.makedirs(folder, exist_ok=True)
    tex_names = {}
    for kind, img in images.items():
        fn = f"T_{short}_{kind}.png"
        img.save(os.path.join(folder, fn))
        tex_names[kind] = fn
    blob, views, accessors, gl_prims = b"", [], [], []

    def add(arr, comp, typ, target, minmax=False):
        nonlocal blob
        data = arr.astype("<f4" if comp == 5126 else "<u4").tobytes()
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        acc = {"bufferView": len(views) - 1, "componentType": comp, "count": len(arr), "type": typ}
        if minmax:
            acc["min"], acc["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        accessors.append(acc)
        blob += data
        return len(accessors) - 1

    for m, (pos, nrm, uv, tris) in enumerate(prims):
        gp = np.stack([pos[:, 0], pos[:, 2], pos[:, 1]], -1) / 100.0  # Unreal cm -> glTF m, Y up
        gn = np.stack([nrm[:, 0], nrm[:, 2], nrm[:, 1]], -1)
        t = _orient(gp, gn, tris)
        gl_prims.append({"attributes": {"POSITION": add(gp, 5126, "VEC3", 34962, True),
                                        "NORMAL": add(gn, 5126, "VEC3", 34962),
                                        "TEXCOORD_0": add(uv, 5126, "VEC2", 34962)},
                         "indices": add(t.reshape(-1), 5125, "SCALAR", 34963), "material": m})
    doc = {
        "asset": {"version": "2.0", "generator": "FoA make_rugs.py"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"name": name, "primitives": gl_prims}],
        "images": [{"uri": tex_names[k], "name": tex_names[k][:-4]} for k in ("Albedo", "Normal", "ORM")],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "textures": [{"source": i, "sampler": 0} for i in range(3)],
        "materials": [
            {"name": f"M_{short}", "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 2},
                "metallicFactor": 0.0, "roughnessFactor": 1.0},
             "normalTexture": {"index": 1}, "occlusionTexture": {"index": 2}},
            {"name": f"M_{short}_Fringe", "pbrMetallicRoughness": {  # dirty undyed cotton
                "baseColorFactor": [0.40, 0.355, 0.27, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.95}},
        ],
        "buffers": [{"byteLength": len(blob), "uri": f"{name}.bin"}],
        "bufferViews": views, "accessors": accessors,
    }
    with open(os.path.join(folder, f"{name}.bin"), "wb") as fh:
        fh.write(blob)
    with open(os.path.join(folder, f"{name}.gltf"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return folder


def build(out_dir, only=None):
    src = Sources()
    for spec in RUGS:
        if only and spec["name"] not in only:
            continue
        albedo, normal, orm = compose(spec, src)
        prims = build_mesh(spec)
        folder = write_rug(out_dir, spec, prims, {"Albedo": albedo, "Normal": normal, "ORM": orm})
        albedo.convert("L").resize((512, int(512 * spec["W"] / spec["L"]))).save(os.path.join(folder, "preview_gray.png"))
        ntri = sum(len(p[3]) for p in prims)
        print(f"{spec['name']}: {ntri} tris, textures {spec['tex']}, "
              f"px/m {spec['tex'][0] / spec['L'] * 100:.0f} x {spec['tex'][1] / spec['W'] * 100:.0f} -> {folder}")


def selftest():
    spec = dict(RUGS[0])
    prims = build_mesh(spec)
    for pos, nrm, uv, tris in prims:
        assert tris.min() >= 0 and tris.max() < len(pos)
        assert len(pos) == len(nrm) == len(uv)
        assert np.allclose(np.linalg.norm(nrm, axis=-1), 1.0, atol=1e-4)
        assert pos[:, 2].min() >= 0.0, "nothing may sink below the floor"
    body, fr = prims
    assert abs(body[0][:, 2].min()) < 1e-6, "the rug must rest on the floor"
    span = body[0].max(0) - body[0].min(0)
    assert abs(span[0] - spec["L"]) < 1.0 and abs(span[1] - spec["W"]) < 1.0, span
    flat = body[0][(np.abs(body[0][:, 0]) < 20) & (np.abs(body[0][:, 1]) < 10)]
    assert flat[:, 2].max() < 2.5, "away from the wrinkle and curl the rug is about 1 cm thick"
    assert body[2].min() >= 0.0 and body[2].max() <= 1.0
    assert fr[0][:, 0].max() > spec["L"] / 2 + 5, "fringe reaches past the short ends"
    t = _orient(body[0], body[1], body[3])
    up = np.cross(body[0][t[:, 1]] - body[0][t[:, 0]], body[0][t[:, 2]] - body[0][t[:, 0]])
    top = body[1][t[:, 0], 2] > 0.99
    assert (up[top, 2] > 0).all(), "top faces wind towards +Z"
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        build(args[0] if args else "P:/FoA-Assets/dressing", only=[a[7:] for a in sys.argv if a.startswith("--only=")])
