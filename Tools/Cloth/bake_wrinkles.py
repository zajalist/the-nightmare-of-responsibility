"""Dynamic-wrinkle maps for the teen's garments, generated from the real skinning (run in the portable Blender).
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Cloth/bake_wrinkles.py <wake|suit> [out_dir]

Method (no sculpting, no Cycles bake):
1. Load the outfit's MHM through MPFB (same fitted, skinned garments the character lane exports).
2. Pose the game_engine rig into a neutral stance (arms down) and one "full" pose per channel. For every garment
   triangle, measure how the pose compresses the cloth relative to neutral (generalised eigenproblem of the two
   metric tensors, expressed in the BIND-pose frame the UVs live in). Compression, plus a bit of anisotropic
   stretch, is where real cloth buckles; the direction of least stretch is the direction the folds stack along.
3. Channels (mask RGBA): R elbow flex, G upper-arm reach/raise, B spine bend + hip flex, A knee flex.
   Left/right is NOT in the mask: the UE material splits it by pre-skinned local X (left = +X).
4. Per (channel, side) region: fold axis = dominant compression direction, wavelength per channel and fabric.
   Fold phase theta = 2pi * dot(p - c, axis) / lambda + domain warp, envelope broken up by noise.
5. Rasterise in the garment's own UVs (MikkTSpace tangents from Blender) and write the analytic slope of
   sin(theta) and cos(theta) as two tangent-space normal pairs: folds texture RG = sin, BA = cos.
   Any phase shift phi is then exact: n_xy = cos(phi) * RG + sin(phi) * BA, so the material can SLIDE folds.
Outputs (P:/FoA-Assets/character/cloth/bake/): <garment>_folds_gl.png (Blender), <garment>_folds_dx.png (UE,
green channels negated), <garment>_mask.png, <garment>_regions.json. Never saves a .blend."""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, "P:/FoA/Tools/MPFB")
from load_teen import load_teen  # noqa: E402
from mpfb_common import args  # noqa: E402

MH = "P:/FoA-Assets/character/makehuman_home/makehuman/v1py3/models/"
OUTFITS = {
    "wake": (MH + "foa_teen.mhm", {"foa_polo_layered": 1.0, "toigo_wool_pants": 1.15}),
    "suit": (MH + "foa_teen_suit.mhm", {"male_elegantsuit01": 1.25}),
}
CHANNELS = ("elbow", "arm", "torso", "knee")
LAMBDA = {"elbow": 0.040, "arm": 0.050, "torso": 0.055, "knee": 0.045}  # fold wavelength (m) before fabric factor
AMP = 0.0075          # fold height (m); slope = AMP * 2pi / lambda ~ 0.8 (texture holds +-1)
CHANNEL_AMP = 0.002   # corrected per-joint fields: 2 mm, independent of the retained legacy comparison bake
COMPRESS_REF = 0.20   # 20 % compression = full mask
STRETCH_W = 0.15      # anisotropic stretch buckles far less than compression
FOLD_RES, MASK_RES = 1024, 512
RNG = np.random.default_rng(1957)


# ---------------------------------------------------------------- posing
def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def rotate(rig, bone, axis, deg):
    """Rotate a pose bone about a world-space axis through its head (armature object is at the origin)."""
    pb = rig.pose.bones[bone]
    head = pb.matrix.to_translation()
    r = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-head)
    pb.matrix = r @ pb.matrix
    bpy.context.view_layer.update()


def bone_dir(rig, bone):
    pb = rig.pose.bones[bone]
    return (pb.tail - pb.head).normalized()


def pose_neutral(rig):
    reset_pose(rig)
    rotate(rig, "upperarm_l", (0, 1, 0), 30)   # A-pose (41 deg out) down to ~11 deg: arms hang
    rotate(rig, "upperarm_r", (0, 1, 0), -30)


def flex_elbows(rig, deg):
    for s in "lr":
        u, l = bone_dir(rig, "upperarm_" + s), bone_dir(rig, "lowerarm_" + s)
        rotate(rig, "lowerarm_" + s, u.cross(l), deg)  # the bind pose is already bent forward: keep bending that way


POSES = {
    "elbow": lambda rig: (pose_neutral(rig), flex_elbows(rig, 85)),
    "arm": lambda rig: (pose_neutral(rig),
                        rotate(rig, "upperarm_l", (1, 0, 0), -70), rotate(rig, "upperarm_r", (1, 0, 0), -70),
                        rotate(rig, "upperarm_l", (0, 1, 0), -25), rotate(rig, "upperarm_r", (0, 1, 0), 25)),
    "torso": lambda rig: (pose_neutral(rig),
                          rotate(rig, "spine_01", (1, 0, 0), 18), rotate(rig, "spine_02", (1, 0, 0), 12),
                          rotate(rig, "spine_03", (1, 0, 0), 10),
                          rotate(rig, "thigh_l", (1, 0, 0), -70), rotate(rig, "thigh_r", (1, 0, 0), -70)),
    "knee": lambda rig: (pose_neutral(rig), rotate(rig, "calf_l", (1, 0, 0), 95), rotate(rig, "calf_r", (1, 0, 0), 95)),
}


def world_coords(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    eo = obj.evaluated_get(deps)
    m = eo.to_mesh()
    co = np.empty(len(m.vertices) * 3, np.float64)
    m.vertices.foreach_get("co", co)
    eo.to_mesh_clear()
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world)
    return co @ mw[:3, :3].T + mw[:3, 3]


# ---------------------------------------------------------------- mesh data
def mesh_data(obj):
    me = obj.data
    me.calc_loop_triangles()
    me.calc_tangents(uvmap=me.uv_layers.active.name)
    nl = len(me.loops)
    get = lambda coll, attr, n, dt=np.float64: (lambda a: (coll.foreach_get(attr, a), a)[1])(np.empty(len(coll) * n, dt))
    d = {
        "tri_v": get(me.loop_triangles, "vertices", 3, np.int64).reshape(-1, 3),
        "tri_l": get(me.loop_triangles, "loops", 3, np.int64).reshape(-1, 3),
        "uv": get(me.uv_layers.active.data, "uv", 2).reshape(-1, 2),
        "tan": get(me.loops, "tangent", 3).reshape(-1, 3),
        "sgn": get(me.loops, "bitangent_sign", 1),
        "nrm": get(me.loops, "normal", 3).reshape(-1, 3),
        "edges": get(me.edges, "vertices", 2, np.int64).reshape(-1, 2),
    }
    mw = np.array(obj.matrix_world)[:3, :3]
    d["tan"], d["nrm"] = d["tan"] @ mw.T, d["nrm"] @ mw.T
    assert d["uv"].shape[0] == nl
    return d


# ---------------------------------------------------------------- strain
def tri_frames(x, tv):
    """Orthonormal 2D frame per triangle (u along edge 1) and the 2x2 edge matrix in it."""
    e1, e2 = x[tv[:, 1]] - x[tv[:, 0]], x[tv[:, 2]] - x[tv[:, 0]]
    n = np.cross(e1, e2)
    area = 0.5 * np.linalg.norm(n, axis=1)
    u = e1 / np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-12)
    w = np.cross(n / np.maximum(2 * area[:, None], 1e-12), u)
    E = np.stack([np.stack([(e1 * u).sum(1), (e2 * u).sum(1)], 1), np.stack([(e1 * w).sum(1), (e2 * w).sum(1)], 1)], 1)
    return u, w, E, area


def metric(xb, xd, tv, E):
    """Metric tensor C = F^T F of the deformation bind -> xd, in each bind triangle's 2D frame."""
    f1, f2 = xd[tv[:, 1]] - xd[tv[:, 0]], xd[tv[:, 2]] - xd[tv[:, 0]]
    Ds = np.stack([f1, f2], 2)                       # (T,3,2)
    Ei = np.linalg.pinv(E)                           # pinv: degenerate faces give zeros instead of raising
    F = Ds @ Ei                                      # (T,3,2)
    return np.einsum("tki,tkj->tij", F, F)


def buckle(xb, xn, xp, tv, axis=None):
    """Per triangle: buckle amount and the bind-space direction folds stack along.
    axis (T,3) given: compression measured ALONG that bone axis only, so a bent elbow or knee lights the inner
    side (where LBS shortens the cloth) and not the outer side (where LBS only collapses the circumference).
    axis None: the direction of least relative stretch, plus some anisotropic stretch (arm reach pulls the back)."""
    u, w, E, area = tri_frames(xb, tv)
    Cn, Cp = metric(xb, xn, tv, E), metric(xb, xp, tv, E)
    ok = (area > 1e-9) & (np.abs(np.linalg.det(Cn)) > 1e-12) & (np.abs(np.linalg.det(E)) > 1e-12)  # MakeHuman meshes have a few degenerate faces
    Cn[~ok], Cp[~ok] = np.eye(2), np.eye(2)
    M = np.linalg.inv(Cn) @ Cp                       # generalised eigenproblem Cp v = l^2 Cn v
    tr, det = M[:, 0, 0] + M[:, 1, 1], np.linalg.det(M)
    disc = np.sqrt(np.maximum(tr * tr / 4 - det, 0))
    lmin, lmax = np.sqrt(np.maximum(tr / 2 - disc, 1e-9)), np.sqrt(np.maximum(tr / 2 + disc, 1e-9))
    lam = lmin ** 2
    v = np.stack([M[:, 0, 1], lam - M[:, 0, 0]], 1)  # eigenvector for lmin
    alt = np.stack([lam - M[:, 1, 1], M[:, 1, 0]], 1)
    use_alt = np.linalg.norm(v, axis=1) < np.linalg.norm(alt, axis=1)
    v[use_alt] = alt[use_alt]
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    d = v[:, :1] * u + v[:, 1:] * w
    amount = (np.maximum(0, 1 - lmin) + STRETCH_W * np.maximum(0, lmax - 1)) * ok
    if axis is not None:
        a2 = np.stack([(axis * u).sum(1), (axis * w).sum(1)], 1)
        inplane = np.linalg.norm(a2, axis=1)
        a2 /= np.maximum(inplane, 1e-9)[:, None]
        la = np.sqrt(np.einsum("ti,tij,tj->t", a2, Cp, a2) / np.maximum(np.einsum("ti,tij,tj->t", a2, Cn, a2), 1e-12))
        amount = np.maximum(0, 1 - la) * ok * np.clip(inplane * 1.5, 0, 1)   # faces seen end-on along the axis fade out
        d = a2[:, :1] * u + a2[:, 1:] * w
    return amount, d, area


def to_vertices(nv, tv, area, val, d=None):
    wv = np.zeros(nv)
    acc = np.zeros(nv)
    for k in range(3):
        np.add.at(wv, tv[:, k], area)
        np.add.at(acc, tv[:, k], area * val)
    out = acc / np.maximum(wv, 1e-12)
    if d is None:
        return out
    ten = np.zeros((nv, 3, 3))
    dd = (area * val)[:, None, None] * d[:, :, None] * d[:, None, :]
    for k in range(3):
        np.add.at(ten, tv[:, k], dd)
    return out, ten


def smooth(val, edges, iters):
    nv = val.shape[0]
    deg = np.bincount(edges.ravel(), minlength=nv).astype(np.float64)
    for _ in range(iters):
        acc = np.zeros_like(val)
        np.add.at(acc, edges[:, 0], val[edges[:, 1]])
        np.add.at(acc, edges[:, 1], val[edges[:, 0]])
        val = 0.5 * val + 0.5 * acc / np.maximum(deg, 1)[:, None] if val.ndim > 1 else 0.5 * val + 0.5 * acc / np.maximum(deg, 1)
    return val


# ---------------------------------------------------------------- regions
def make_regions(xb, mask, ten, lam, edges):
    """Split each channel into left/right lobes; each lobe gets an axis, a centre and its own warp field."""
    side_l = np.clip((xb[:, 0] + 0.03) / 0.06, 0, 1)   # left = +X in Blender and UE
    regions = []
    for ci, ch in enumerate(CHANNELS):
        for side, sw in (("L", side_l), ("R", 1 - side_l)):
            m = mask[:, ci] * sw
            if m.sum() < 1.0:
                continue
            lobes = [m]
            pts = xb[m > 0.2]
            if len(pts) > 20:   # 2-means: an arm reach compresses the front armpit AND pulls the back
                c = pts[RNG.choice(len(pts), 2, replace=False)]
                for _ in range(12):
                    lab = np.argmin(((xb[:, None, :] - c[None]) ** 2).sum(2), 1)
                    c = np.array([np.average(xb[lab == k], axis=0, weights=m[lab == k] + 1e-9) if (lab == k).any() else c[k] for k in range(2)])
                if np.linalg.norm(c[0] - c[1]) > 0.14 and min((m * (lab == k)).sum() for k in range(2)) > 0.25 * m.sum():
                    soft = np.exp(-((xb[:, None, :] - c[None]) ** 2).sum(2) / (2 * 0.06 ** 2))
                    soft = smooth(soft / np.maximum(soft.sum(1, keepdims=True), 1e-9), edges, 4)
                    lobes = [m * soft[:, k] for k in range(2)]
            for lm in lobes:
                t = (ten[:, ci] * (lm * sw)[:, None, None]).sum(0)
                axis = np.linalg.eigh(t)[1][:, -1]
                centre = np.average(xb, axis=0, weights=lm + 1e-9)
                f = RNG.normal(size=(6, 3))
                f *= (2 * math.pi / (lam[ch] * RNG.uniform(2.0, 4.0, size=6)))[:, None] / np.linalg.norm(f, axis=1, keepdims=True)
                g = RNG.normal(size=(4, 3))
                g *= (2 * math.pi / (lam[ch] * RNG.uniform(3.0, 6.0, size=4)))[:, None] / np.linalg.norm(g, axis=1, keepdims=True)
                regions.append({"channel": ch, "side": side, "vmask": lm, "axis": axis, "centre": centre,
                                "lambda": lam[ch], "warp_f": f, "warp_p": RNG.uniform(0, 6.283, 6),
                                "break_f": g, "break_p": RNG.uniform(0, 6.283, 4)})
    return regions


# ---------------------------------------------------------------- raster
def raster(d, res):
    """Texel -> (triangle, barycentrics) for every texel centre inside a UV triangle (row 0 = v 0)."""
    uv = d["uv"][d["tri_l"]] * res - 0.5            # (T,3,2) texel-centre coordinates
    tri = np.full(res * res, -1, np.int64)
    bary = np.zeros((res * res, 3))
    for t in range(uv.shape[0]):
        a, b, c = uv[t]
        lo = np.floor(np.minimum(np.minimum(a, b), c)).astype(int)
        hi = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        lo, hi = np.clip(lo, 0, res - 1), np.clip(hi, 0, res - 1)
        xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        p = np.stack([xs.ravel(), ys.ravel()], 1).astype(np.float64)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-12:
            continue
        l0 = ((b[1] - c[1]) * (p[:, 0] - c[0]) + (c[0] - b[0]) * (p[:, 1] - c[1])) / den
        l1 = ((c[1] - a[1]) * (p[:, 0] - c[0]) + (a[0] - c[0]) * (p[:, 1] - c[1])) / den
        l2 = 1 - l0 - l1
        inside = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
        idx = (p[inside, 1] * res + p[inside, 0]).astype(np.int64)
        tri[idx] = t
        bary[idx] = np.stack([l0, l1, l2], 1)[inside]
    return tri, bary


def dilate(img, covered, steps):
    """Grow edge texels outward so mips and bilinear filtering never pull in empty space at UV seams."""
    img, cov = img.copy(), covered.copy()
    for _ in range(steps):
        acc = np.zeros_like(img)
        cnt = np.zeros(cov.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(np.roll(img * cov[..., None], dy, 0), dx, 1)
            cnt += np.roll(np.roll(cov.astype(np.float64), dy, 0), dx, 1)
        grow = (~cov) & (cnt > 0)
        img[grow] = acc[grow] / cnt[grow][:, None]
        cov = cov | grow
    return img


def save_png(path, rgba):
    h, w, _ = rgba.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.clip(rgba, 0, 1).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    print("wrote", path)


def bind_axes(rig, xb, tv):
    """Per-triangle reference axis per channel, in bind pose: limb axis on the triangle's own side; torso vertical."""
    reset_pose(rig)
    left = xb[tv].mean(1)[:, 0] > 0
    def limb(a, b):
        out = np.zeros((len(tv), 3))
        for s, m in (("l", left), ("r", ~left)):
            v = bone_dir(rig, a + "_" + s) + bone_dir(rig, b + "_" + s)
            out[m] = np.array(v.normalized())
        return out
    return {"elbow": limb("upperarm", "lowerarm"), "knee": limb("thigh", "calf"),
            "torso": np.tile([0.0, 0.0, 1.0], (len(tv), 1)), "arm": None}


def bake_garment(name, obj, fabric, rig, xb, poses, out):
    d = mesh_data(obj)
    tv, nv = d["tri_v"], len(xb)
    axes = bind_axes(rig, xb, tv)
    lam = {k: v * fabric for k, v in LAMBDA.items()}
    mask = np.zeros((nv, 4))
    ten = np.zeros((nv, 4, 3, 3))
    for ci, ch in enumerate(CHANNELS):
        amount, dirs, area = buckle(xb, poses["neutral"], poses[ch], tv, axes[ch])
        val, t = to_vertices(nv, tv, area, amount, dirs)
        print("STAT", name, ch, np.round(np.percentile(val, [50, 75, 90, 99]), 3))
        mask[:, ci] = np.clip(val / COMPRESS_REF, 0, 1)
        ten[:, ci] = t
    mask = smooth(mask, d["edges"], 4)
    regions = make_regions(xb, mask, ten, lam, d["edges"])

    # mask texture (bind-pose vertex masks interpolated per texel)
    tri, bary = raster(d, MASK_RES)
    cov = tri >= 0
    mtex = np.zeros((MASK_RES * MASK_RES, 4))
    mtex[cov] = np.einsum("nk,nkc->nc", bary[cov], mask[tv[tri[cov]]])
    mtex = dilate(mtex.reshape(MASK_RES, MASK_RES, 4), cov.reshape(MASK_RES, MASK_RES), 6)
    save_png(os.path.join(out, name + "_mask.png"), mtex)

    # folds texture
    tri, bary = raster(d, FOLD_RES)
    cov = tri >= 0
    ti, b = tri[cov], bary[cov]
    P = np.einsum("nk,nkc->nc", b, xb[tv[ti]])
    lp = d["tri_l"][ti]
    N = np.einsum("nk,nkc->nc", b, d["nrm"][lp])
    T = np.einsum("nk,nkc->nc", b, d["tan"][lp])
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    T -= N * (T * N).sum(1, keepdims=True)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    B = np.cross(N, T) * np.sign(d["sgn"][lp[:, 0]])[:, None]   # MikkTSpace: B = sign * N x T
    env = np.stack([np.einsum("nk,nk->n", b, r["vmask"][tv[ti]]) for r in regions], 1) if regions else np.zeros((len(ti), 0))
    env = np.clip((env - 0.05) / 0.30, 0, 1)
    env = env * env * (3 - 2 * env)
    channel_env=env.copy()
    for channel in CHANNELS:
        indexes=[i for i,r in enumerate(regions) if r['channel']==channel]
        if indexes:
            channel_env[:,indexes] /= np.maximum(channel_env[:,indexes].sum(1,keepdims=True),1.0)
    env /= np.maximum(env.sum(1, keepdims=True), 1.0)              # partition where lobes overlap
    gs, gc = np.zeros((len(ti), 3)), np.zeros((len(ti), 3))
    channel_s=np.zeros((4,len(ti),3));channel_c=np.zeros_like(channel_s)
    for k, r in enumerate(regions):
        q = P - r["centre"]
        ph = q @ r["warp_f"].T + r["warp_p"]
        theta = 2 * math.pi * (q @ r["axis"]) / r["lambda"] + 1.6 * np.sin(ph).sum(1) / math.sqrt(6)
        dtheta = 2 * math.pi * r["axis"] / r["lambda"] + 1.6 * (np.cos(ph) @ r["warp_f"]) / math.sqrt(6)
        brk = np.clip(0.6 + 0.5 * np.sin(q @ r["break_f"].T + r["break_p"]).sum(1) / 2.0, 0.15, 1.0)
        e = (AMP * env[:, k] * brk)[:, None]
        gs += e * np.cos(theta)[:, None] * dtheta     # grad of e*sin(theta), envelope gradient neglected
        gc -= e * np.sin(theta)[:, None] * dtheta     # grad of e*cos(theta)
        ci=CHANNELS.index(r['channel'])
        local=(CHANNEL_AMP*channel_env[:,k]*brk)[:,None]
        if name == 'foa_polo_layered' and r['channel']=='torso':
            # A loose polo compresses near its waist; an upright chest must not become corrugated.
            waist = float(xb[:,2].min()) + .065
            local *= np.exp(-((P[:,2]-waist)/.085)**2)[:,None]
        channel_s[ci] += local*np.cos(theta)[:,None]*dtheta
        channel_c[ci] -= local*np.sin(theta)[:,None]*dtheta
    # tangent-space slope of a height field: n ~ (-dh/dT, -dh/dB, 1) (OpenGL: B = +V)
    s_xy = -np.stack([(gs * T).sum(1), (gs * B).sum(1)], 1)
    c_xy = -np.stack([(gc * T).sum(1), (gc * B).sum(1)], 1)
    folds = np.full((FOLD_RES * FOLD_RES, 4), 0.5)
    folds[cov] = 0.5 + 0.5 * np.clip(np.concatenate([s_xy, c_xy], 1), -1, 1)
    folds = dilate(folds.reshape(FOLD_RES, FOLD_RES, 4), cov.reshape(FOLD_RES, FOLD_RES), 8)
    save_png(os.path.join(out, name + "_folds_gl.png"), folds)
    dx = folds.copy()
    dx[..., 1], dx[..., 3] = 1 - dx[..., 1], 1 - dx[..., 3]       # DirectX green for UE
    save_png(os.path.join(out, name + "_folds_dx.png"), dx)

    # Four independent fields share one sampler. Each 1024-square cell has a 32-pixel edge gutter.
    # UE UVs have flipped V relative to Blender, so upper array rows become the top atlas cells.
    atlas=np.full((2048,2048,4),.5)
    sample=np.linspace(0,FOLD_RES-1,960)
    low=np.floor(sample).astype(int);high=np.minimum(low+1,FOLD_RES-1);fraction=sample-low
    for ci in range(4):
        slope=-np.stack([(channel_s[ci]*T).sum(1),-(channel_s[ci]*B).sum(1),
                         (channel_c[ci]*T).sum(1),-(channel_c[ci]*B).sum(1)],1)
        field=np.full((FOLD_RES*FOLD_RES,4),.5)
        field[cov]=.5+.5*np.clip(slope,-1,1)
        field=dilate(field.reshape(FOLD_RES,FOLD_RES,4),cov.reshape(FOLD_RES,FOLD_RES),8)
        scaled=field[:,low]*(1-fraction)[None,:,None]+field[:,high]*fraction[None,:,None]
        scaled=scaled[low]*(1-fraction)[:,None,None]+scaled[high]*fraction[:,None,None]
        tile=np.pad(scaled,((32,32),(32,32),(0,0)),mode='edge')
        x=(ci%2)*1024;y=(1-ci//2)*1024
        atlas[y:y+1024,x:x+1024]=tile
    save_png(os.path.join(out,name+'_channels_dx.png'),atlas)

    e = d["uv"][d["tri_l"]][:, 1:] - d["uv"][d["tri_l"]][:, :1]
    uv_area = 0.5 * np.abs(e[:, 0, 0] * e[:, 1, 1] - e[:, 0, 1] * e[:, 1, 0]).sum()
    _, _, _, area3 = tri_frames(xb, tv)
    info = {"garment": name, "fabric_factor": fabric, "uv_coverage": float(uv_area), "area_m2": float(area3.sum()),
            "channel_fold_height_mm":CHANNEL_AMP*1000,"channel_atlas_gutter_px":32,
            "px_per_m_at_1k": float(1024 * math.sqrt(uv_area / area3.sum())),
            "mask_coverage": {ch: float((mask[:, i] > 0.3).mean()) for i, ch in enumerate(CHANNELS)},
            "slope_p99": float(np.percentile(np.abs(np.concatenate([s_xy, c_xy], 1)), 99)) if len(s_xy) else 0.0,
            "regions": [{"channel": r["channel"], "side": r["side"], "axis": [round(float(a), 3) for a in r["axis"]],
                         "centre": [round(float(a), 3) for a in r["centre"]], "lambda": r["lambda"]} for r in regions]}
    with open(os.path.join(out, name + "_regions.json"), "w") as f:
        json.dump(info, f, indent=1)
    print("INFO", json.dumps({k: v for k, v in info.items() if k != "regions"}), "regions", len(regions))


def main():
    a = args()
    outfit = a[0] if a else "wake"
    out = a[1] if len(a) > 1 else "P:/FoA-Assets/character/cloth/bake"
    os.makedirs(out, exist_ok=True)
    mhm, garments = OUTFITS[outfit]
    body, rig = load_teen(mhm)
    objs = {g: o for o in bpy.data.objects for g in garments if o.type == "MESH" and o.name.endswith("." + g)}
    reset_pose(rig)
    xb = {g: world_coords(o) for g, o in objs.items()}
    poses = {g: {} for g in objs}
    for p, fn in [("neutral", pose_neutral)] + [(c, POSES[c]) for c in CHANNELS]:
        fn(rig)
        for g, o in objs.items():
            poses[g][p] = world_coords(o)
    reset_pose(rig)
    for g, o in objs.items():
        bake_garment(g, o, garments[g], rig, xb[g], poses[g], out)


if __name__ == "__main__":
    main()
