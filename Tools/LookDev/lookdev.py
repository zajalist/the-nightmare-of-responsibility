"""Offline reference renderer for the dream post-process (lookdev lane). Every step is one a UE post-process material
can do cheaply (a handful of taps, one tiling noise texture), so the pp lane can rebuild a look 1:1 from its LOOKS
entry. Inputs come from capture_passes.py.
  python Tools/LookDev/lookdev.py            -> Saved/LookDev/<look>_<cam>[_open].png + lookdev_sheet.png
  python Tools/LookDev/lookdev.py B          -> one look only (fast iteration)
Conventions: images are display-referred 0..1 (what an After-Tonemapping blendable sees in PostProcessInput0);
pixel sizes are at 1080p (scale by ViewSize.y / 1080); depth is UE scene depth in cm. The time-shift echo and every
streak run VERTICALLY in screen space (user preference), never along motion."""
import functools
import math
import os
import sys

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ROOT = "P:/FoA/Saved/LookDev"
SRC = ROOT + "/src"
CAMS = ["Shot_ThirdPerson", "Shot_Wide", "Shot_Window"]
POSE = {  # loc (cm), (pitch, yaw), horizontal fov; from the capture log (Dev/ShotCameras)
    "Shot_ThirdPerson": ((-60, -60, 175), (-8.1, 18.7), 80.0),
    "Shot_Wide": ((-340, 280, 270), (-16.9, -50.3), 80.0),
    "Shot_Window": ((250, 100, 160), (-2.0, -124.0), 80.0),
}
LW = np.array([0.2126, 0.7152, 0.0722], np.float32)


# ---------- helpers: each mirrors one material op ----------

def sm(e0, e1, x):  # HLSL smoothstep
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def lin(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def enc(x):
    x = np.clip(x, 0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


@functools.lru_cache(None)
def grid(h, w):
    return np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))


def tap(img, dx, dy):
    """SceneTextureLookup at UV + (dx, dy) px, bilinear (dx / dy may be per-pixel arrays)."""
    X, Y = grid(*img.shape[:2])
    return cv2.remap(img, (X + dx).astype(np.float32), (Y + dy).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def blur(img, sigma):
    return cv2.GaussianBlur(img, (0, 0), sigma) if sigma > 0 else img


@functools.lru_cache(None)
def noise_tex(n=512, seed=7):
    """T_DreamNoise (RGBA8, 512, tiling, linear/no sRGB): R/G low-frequency fbm (warp), B fbm (smoke), A white noise
    (grain). Periodic by construction (band-pass filtered in the frequency domain), equalised to uniform 0..1."""
    path = ROOT + "/T_DreamNoise.png"
    if os.path.exists(path):
        return cv2.cvtColor(cv2.imread(path, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
    rng = np.random.default_rng(seed)
    fy, fx = np.meshgrid(np.fft.fftfreq(n) * n, np.fft.fftfreq(n) * n, indexing="ij")
    f = np.hypot(fx, fy)

    def fbm(lo, hi, beta):
        spec = np.fft.fft2(rng.standard_normal((n, n))) * np.where((f >= lo) & (f <= hi), 1 / np.maximum(f, 1) ** beta, 0)
        v = np.real(np.fft.ifft2(spec))
        return (v.ravel().argsort().argsort().reshape(n, n) / (n * n - 1)).astype(np.float32)

    tex = np.dstack([fbm(1, 12, 1.0), fbm(1, 12, 1.0), fbm(2, 64, 1.1), rng.random((n, n)).astype(np.float32)])
    cv2.imwrite(path, cv2.cvtColor((tex * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    return tex


def sample_noise(uv_x, uv_y, ch):
    """T_DreamNoise sample (wrap, bilinear) of channel ch at UV arrays."""
    tex = noise_tex()
    n = tex.shape[0]
    return cv2.remap(np.ascontiguousarray(tex[..., ch]), (uv_x * n).astype(np.float32), (uv_y * n).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


# ---------- inputs ----------

def load(cam):
    """HDR colour (linear, scaled by the shot's exposure), depth, normal, base colour."""
    c = cv2.imread(f"{SRC}/{cam}_color_0.exr", cv2.IMREAD_UNCHANGED)[..., 2::-1].astype(np.float32) * EXPO[cam]
    d = cv2.imread(f"{SRC}/{cam}_depth_0.exr", cv2.IMREAD_UNCHANGED)[..., 2].astype(np.float32)  # BGR(A): R is [2]
    n = cv2.imread(f"{SRC}/{cam}_normal_0.exr", cv2.IMREAD_UNCHANGED)[..., 2::-1].astype(np.float32)
    if n.min() >= 0:  # stored 0..1
        n = n * 2 - 1
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-4)
    b = cv2.imread(f"{SRC}/{cam}_base_0.exr", cv2.IMREAD_UNCHANGED)[..., 2::-1].astype(np.float32)
    d = np.clip(d, 1, 1e6)
    return cleanup(np.maximum(c, 0), d), d, n, b


def cleanup(c, d):
    """Capture fix, NOT part of the look: a scene capture can't converge the stochastic shadow dither that TSR
    resolves in game, so blur speckle on flat surfaces (high luminance variance, no depth edge) like the history would."""
    L = np.log(c @ LW + 1e-7)
    var = blur(L * L, 2) - blur(L, 2) ** 2
    z = 1 / d
    edge = np.abs(tap(z, -2, 0) + tap(z, 2, 0) - 2 * z) / z + np.abs(tap(z, 0, -2) + tap(z, 0, 2) - 2 * z) / z
    m = (sm(0.15, 0.6, var) * (1 - sm(0.01, 0.04, edge)))[..., None]
    return c + (blur(c, 2.5) - c) * m


def film(x, slope=0.88, toe=0.55, shoulder=0.26, black=0.0, white=0.04):
    """UE's filmic tonemapper curve (TonemapCommon.ush FilmToneMap) on linear values; output is linear, pre-sRGB."""
    ts, ss = 1 + black - toe, 1 + white - shoulder
    if toe > 0.8:
        tm = (1 - toe - 0.18) / slope + math.log10(0.18)
    else:
        bt = (0.18 + black) / ts - 1
        tm = math.log10(0.18) - 0.5 * math.log((1 + bt) / (1 - bt)) * (ts / slope)
    st = (1 - toe) / slope - tm
    shm = shoulder / slope - st
    lc = np.log10(np.maximum(x, 1e-10))
    straight = slope * (lc + st)
    toe_c = -black + (2 * ts) / (1 + np.exp((-2 * slope / ts) * (lc - tm)))
    sh_c = (1 + white) - (2 * ss) / (1 + np.exp((2 * slope / ss) * (lc - shm)))
    toe_c = np.where(lc < tm, toe_c, straight)
    sh_c = np.where(lc > shm, sh_c, straight)
    t = np.clip((lc - tm) / (shm - tm), 0, 1)
    t = 1 - t if shm < tm else t
    t = (3 - 2 * t) * t * t
    return np.maximum(0, toe_c + (sh_c - toe_c) * t)


def raw_frame(cam):
    """Column 0: the plain UE frame (default filmic tonemapper, colour, no dream post), same exposure."""
    c, _, _, _ = load(cam)
    return enc(np.clip(film(c), 0, 1))


def world_pos(cam, d):
    """AbsoluteWorldPosition reconstructed from scene depth (what a PP material gets for free)."""
    (x, y, z), (pitch, yaw), fov = POSE[cam]
    h, w = d.shape
    p, ya = math.radians(pitch), math.radians(yaw)
    F = np.array([math.cos(p) * math.cos(ya), math.cos(p) * math.sin(ya), math.sin(p)])
    R = np.array([-math.sin(ya), math.cos(ya), 0.0])
    U = np.array([-math.sin(p) * math.cos(ya), -math.sin(p) * math.sin(ya), math.cos(p)])
    th = math.tan(math.radians(fov) / 2)
    X, Y = grid(h, w)
    nx = (2 * (X + 0.5) / w - 1) * th
    ny = (1 - 2 * (Y + 0.5) / h) * th * h / w
    wp = np.array([x, y, z], float) + d[..., None] * (F + nx[..., None] * R + ny[..., None] * U)
    return wp.astype(np.float32), th


# ---------- the look stages, in pass order ----------

def coc_px(d, P, th, w, focus):
    """UE Cinematic (Diaphragm) DOF circle of confusion, as a radius in output pixels. A plain CameraComponent's
    focal length is SensorWidth / (2 tan(FOV/2)); a wide 90 deg lens only gets shallow focus on a large sensor."""
    f = 0.5 * P["sensor_mm"] / th
    dm, sm_ = d * 10.0, focus * 10.0                         # cm -> mm
    coc_mm = (f / P["fstop"]) * f * np.abs(dm - sm_) / (dm * (sm_ - f))
    return np.minimum(0.5 * coc_mm / P["sensor_mm"] * w, P["coc_max"] * w / 1920)


def disc(r):
    k = int(math.ceil(r))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    ker = np.clip(r + 0.5 - np.hypot(xx, yy), 0, 1).astype(np.float32)
    return ker / ker.sum()


def dof(c, d, coc, focus):
    """Layered gather: the background blurs only from background pixels (no halo of the sharp subject around it),
    the foreground blurs freely (spills over, like real bokeh). Hat-weighted blend between disc radii."""
    far = (d >= focus).astype(np.float32)
    out = np.zeros_like(c)
    radii = [0, 1.5, 3, 5, 8, 12, 17, 24, 32]
    for i, r in enumerate(radii):
        lo = radii[i - 1] if i else r - 1
        hi = radii[i + 1] if i + 1 < len(radii) else r + 1e6
        wgt = np.where(coc < r, np.clip((coc - lo) / max(r - lo, 1e-4), 0, 1), np.clip((hi - coc) / (hi - r), 0, 1))
        if not wgt.any():
            continue
        if r == 0:
            layer = c
        else:
            K = disc(r)
            wf = cv2.filter2D(far, -1, K)[..., None]
            bg = cv2.filter2D(c * far[..., None], -1, K) / np.maximum(wf, 1e-4)
            layer = np.where((far[..., None] > 0) & (wf > 0.05), bg, cv2.filter2D(c, -1, K))
        out += layer * wgt[..., None]
    return out


def tone(c, P):
    """Mono luma > exposure compensation > UE filmic tonemapper (volume Film* settings) > [After Tonemapping:]
    black / white point > S-curve > gamma. The smoothstep toe crushes without clipping."""
    Y = (c @ LW) * 2.0 ** P["ev"]
    Y = Y * P["roll"] / (P["roll"] + Y)            # HDR highlight roll-off before the tonemapper: shafts stay subtle
    Y = enc(film(Y, toe=P["film_toe"], shoulder=P["film_shoulder"]))
    t = np.clip((Y - P["black"]) / (P["white"] - P["black"]), 0, 1)
    t = t + (t * t * (3 - 2 * t) - t) * P["scurve"]
    return t ** P["gamma"]


def ink(d, n, b, wp, th, y, P, res, sy=0.0):
    """Lines: silhouettes from the inverse-depth Laplacian (near side only, so one clean stroke), creases from
    normals, albedo hairlines up close; width and opacity fall off with distance. sy shifts every tap vertically
    (the line-slip glitch). Returns ink 0..1 and hatch 0..1. Static per pixel: nothing blinks."""
    z = 1.0 / d
    wpx = (P["w_near"] + (P["w_far"] - P["w_near"]) * np.clip((d - 150) / 750, 0, 1)) * res
    z0 = tap(z, 0, sy)
    lap = np.maximum(0, -(tap(z, -wpx, sy) + tap(z, wpx, sy) - 2 * z0)) + \
        np.maximum(0, -(tap(z, 0, sy - wpx) + tap(z, 0, sy + wpx) - 2 * z0))
    sil = sm(P["sil"][0], P["sil"][1], lap / z0)
    o = res
    nb = (1 - np.sum(tap(n, -o, sy) * tap(n, o, sy), 2)) + (1 - np.sum(tap(n, 0, sy - o) * tap(n, 0, sy + o), 2))
    line = np.maximum(sil, sm(P["crease"][0], P["crease"][1], nb) * P["crease_w"])
    if P["hair_w"] > 0:
        bl = enc(b @ LW)
        lb = np.abs(tap(bl, -o, sy) - tap(bl, o, sy)) + np.abs(tap(bl, 0, sy - o) - tap(bl, 0, sy + o))
        line = np.maximum(line, sm(P["hair"][0], P["hair"][1], lb) * np.clip(1 - d / P["hair_dist"], 0, 1) * P["hair_w"])
    ink_ = np.clip(line * (1 - sm(P["fade"][0], P["fade"][1], d)) * P["ink"], 0, 1)
    hatch = np.zeros_like(d)
    if P["hatch"] > 0:  # world-anchored (planar on the dominant normal axis): it never swims; only in shadows
        ax = np.argmax(np.abs(n), axis=2)
        u = np.where(ax == 0, wp[..., 1], wp[..., 0])
        v = np.where(ax == 2, wp[..., 1], wp[..., 2])
        sp = P["hatch_cm"]
        aa = np.clip(d * 2 * th / d.shape[1] / sp, 0, 1)    # hatch cycles per pixel at this depth
        vis = 1 - sm(0.25, 0.45, aa)                         # fade out before it can alias
        a1, a2 = math.radians(P["hatch_deg"]), math.radians(P["hatch_deg"] + 90)
        wob = (sample_noise(u * 0.004, v * 0.004, 0) - 0.5) * 0.4    # world-anchored waver, like a hand-cut line
        c1 = np.cos(2 * math.pi * ((u * math.cos(a1) + v * math.sin(a1)) / sp + wob))
        c2 = np.cos(2 * math.pi * ((u * math.cos(a2) + v * math.sin(a2)) / sp + wob))
        band1 = sm(0.03, 0.08, y) * (1 - sm(P["hatch_lo"][0], P["hatch_lo"][1], y))   # mid-shadows: one direction
        band2 = sm(0.03, 0.06, y) * (1 - sm(P["hatch_hi"][0], P["hatch_hi"][1], y))   # darker: cross-hatch
        # engraving: tone is carried by line WIDTH (thin in the half-shadow, thick in the dark), not by density
        e1 = 1 - 4 * P["hatch_width"] * band1
        e2 = 1 - 4 * P["hatch_width"] * band2
        l1 = sm(e1 - aa * 2, e1 + aa * 2, c1) * (band1 > 0.02)
        l2 = sm(e2 - aa * 2, e2 + aa * 2, c2) * (band2 > 0.02)
        hatch = np.maximum(l1, l2) * vis * P["hatch"]
        ls = sm(0.8 - aa * 2, 0.8 + aa * 2, c1)                                  # fixed-width scratch line
        hatch = hatch - ls * vis * (1 - sm(0.015, 0.05, y)) * P["scratch"]       # deep black: scratched light
    return ink_, hatch


def vstreak(img, length, n_taps, thr, power):
    """Lighten-only vertical smear: each pixel takes the brightest of n taps above it, fading with distance.
    The time-shift blur (whole frame, gentle) and the pixel-sort glitch (column bands, strong) share it."""
    acc = img.copy()
    for i in range(1, n_taps + 1):
        src = tap(img, 0, -i * length / n_taps)
        acc = np.maximum(acc, np.clip((src - thr) / (1 - thr), 0, 1) * src * (1 - i / (n_taps + 1)) ** power)
    return acc


def split_tone(y, P):
    lo = np.array(P["shadow_tint"], np.float32)
    hi = np.array(P["high_tint"], np.float32)
    lo, hi = lo / (lo @ LW), hi / (hi @ LW)                  # unit-luma tints: the hue moves, brightness doesn't
    m = sm(P["split"][0], P["split"][1], y)[..., None]
    return y[..., None] * (lo * (1 - m) + hi * m)


def shoulder(x, knee, paper):
    """Highlights roll off into paper white and never reach 1.0 (user: the light emissivity is too high)."""
    k = paper - knee
    return np.where(x < knee, x, knee + k * (1 - np.exp(-np.maximum(x - knee, 0) / k)))


def render(cam, P, open_tier=False, t=None):
    """t = time in seconds for animated output (grain refresh at 24 Hz, echo breathing, smoke drift); None = still."""
    T = dict(P)
    if open_tier:
        T.update(P["open"])
    c, d, n, b = load(cam)
    h, w = d.shape
    res = h / 1080
    rng = np.random.default_rng(sum(map(ord, cam)))           # glitch placement: fixed per camera
    X, Y = grid(h, w)
    u, v = X / w, Y / h

    # pass 0, the soft photograph under the ink (user: "way too sharp, still looks like unreal"):
    # cinematic DOF focused on the subject, then lower micro-contrast (4 diagonal taps), then the mono tone curve
    wp, th = world_pos(cam, d)
    focus = FOCUS[cam] or float(np.median(d[h * 2 // 5:h * 3 // 5, w * 2 // 5:w * 3 // 5]))
    coc = coc_px(d, T, th, w, focus)
    c = dof(c, d, coc, focus)
    soft = (tap(c, -1.5 * res, -1.5 * res) + tap(c, 1.5 * res, -1.5 * res) + tap(c, -1.5 * res, 1.5 * res) +
            tap(c, 1.5 * res, 1.5 * res)) / 4
    c = c + (soft - c) * T["micro"]
    y = tone(c, T)

    # pass 1 (ink, After DOF so TSR resolves it): lines and hatching ON TOP of the soft image; out of focus they
    # thin out and fade, like a hand inking only what the eye resolves
    ik, hatch = ink(d, n, b, wp, th, y, T, res)
    focus_ink = 1 - T["ink_defocus"] * sm(1.5, 10.0, coc)
    ik, hatch = ik * focus_ink, hatch * focus_ink
    if T["slip"] > 0:  # glitch: the drawing drops a few px inside thin bands (registration error, vertical)
        band = np.zeros(h, np.float32)
        for _ in range(T["slip_bands"]):
            y0 = int(rng.uniform(0.15, 0.85) * h)
            band[y0:y0 + int(rng.uniform(6, 30) * res)] = 1
        ik2, _ = ink(d, n, b, wp, th, y, T, res, sy=-T["slip"] * res)
        ik = np.where(band[:, None] > 0, np.maximum(ik2 * focus_ink, ik * 0.35), ik)
    # ink is black over light and mid tones; in the near-black it turns into a faint light scratch (scratchboard),
    # so silhouettes stay readable in a low-key frame
    # pen pressure: a slow world-anchored variation (never swims, never blinks); the light lines are strongest
    # near the light, so the drawing emerges from the dark where the light reaches
    ik *= 1 - T["ink_press"] * sample_noise((wp[..., 0] + wp[..., 1]) * 0.006, wp[..., 2] * 0.006 + wp[..., 0] * 0.003, 1)
    dark = 1 - sm(0.03, 0.16, blur(y, 3 * res))
    lit = 0.35 + 0.65 * sm(0.0, 0.25, blur(y, 30 * res))
    img = y * (1 - ik) * (1 - np.maximum(hatch, 0)) + ik * dark * lit * T["ink_inv"] + np.maximum(-hatch, 0) * 0.16 * lit

    # pass 2: time-shift echo, VERTICAL (user): decaying copies slipping down the frame like a film frame in the gate
    if T["echo_n"] > 0:
        acc, wsum, wk = 0, 0, 1.0
        for k in range(1, T["echo_n"] + 1):
            wk *= T["echo_decay"]
            gap = T["echo_gap"] * (1 + 0.25 * math.sin(0.9 * t) if t is not None else 1)   # the gap breathes slowly
            acc = acc + tap(img, 0, -k * gap * res) * wk
            wsum += wk
        g = acc / wsum
        op = min(1.0, wsum * T["echo_gain"])
        img = img + (g - img) * op * T["echo_mix"] + np.maximum(g - img, 0) * op * T["echo_lighten"]
    if T["double"] > 0:  # one far ghost: the neighbouring frame showing through (projector slip)
        g = tap(img, 0, -T["double_px"] * res)
        img = img + np.maximum(g - img, 0) * T["double"] + (g - img) * T["double"] * 0.25
    if T["streak"] > 0:  # the time-shift blur: highlights smear downward (vertical slit-scan)
        img = img + (vstreak(img, T["streak_len"] * res, 10, T["streak_thr"], 1.2) - img) * T["streak"]

    # pass 2 glitches, all vertical: micro-tear columns, pixel-sort columns, frame slip with its frame line
    if T["tear"] > 0:
        col = np.zeros(w, np.float32)
        off = np.zeros(w, np.float32)
        for _ in range(T["tear_cols"]):
            x0 = int(rng.uniform(0.1, 0.9) * w)
            ww = int(rng.uniform(2, 8) * res) + 1
            col[x0:x0 + ww] = 1
            off[x0:x0 + ww] = rng.choice([-1, 1]) * rng.uniform(0.5, 1.0)
        torn = tap(img, 0, np.broadcast_to(off * T["tear"] * res, (h, w)))
        img = np.where(col[None, :] > 0, torn * 1.06 + 0.015, img)
    if T["sort"] > 0:
        col = np.zeros(w, np.float32)
        for _ in range(T["sort_cols"]):
            x0 = int(rng.uniform(0.2, 0.8) * w)
            col[x0:x0 + int(rng.uniform(8, 36) * res)] = 1
        img = img + (vstreak(img, T["sort_len"] * res, 12, T["sort_thr"], 0.6) - img) * col[None, :] * T["sort"]
    if T["frame_slip"] > 0:
        ys = T["frame_slip_at"] * h
        img = np.where(Y > ys, tap(img, 0, -T["frame_slip"] * res), img)
        img = img * (1 - 0.85 * sm(3 * res, 0, np.abs(Y - ys - 2 * res)))   # the dark frame line at the splice

    # pass 3, dream: depth haze toward a milky level (engine: Exponential Height Fog, its inscatter at this grey;
    # the lamp glow inside it comes from the mist below), milky frame edges, smoke-and-sand at the edges
    asp = w / h
    r = np.hypot(u - 0.5, v - 0.5) * 2                                   # 0 centre, 1 edge midpoints, 1.41 corners
    haze = (1 - np.exp(-np.maximum(d - T["haze_start"], 0) / T["haze_dist"])) * T["haze"]
    haze = np.clip(haze + sm(T["edge_haze"][0], T["edge_haze"][1], r) * T["edge_haze"][2], 0, 1)
    img = img + (T["haze_level"] - img) * haze
    if T["smoke"] > 0:  # long hanging tendrils (ridges of a vertically stretched noise), a little soft body
        sc = T["smoke_scale"]
        tt = t or 0.0
        wx = sample_noise(u * asp * 0.7 + tt * 0.01, v * 0.7, 0) - 0.5     # slow lateral sway
        nn = sample_noise(u * asp * 3.0 * sc + wx * T["smoke_warp"] * 3.0 * sc, v * 0.3 * sc - tt * 0.05, 0)  # falls
        ridge = (1 - np.abs(2 * nn - 1)) ** T["smoke_thin"]
        body = sm(0.6, 0.95, sample_noise(u * asp * 1.5 * sc + wx * 0.3, v * 0.25 * sc - tt * 0.03, 1))
        mask = sm(T["smoke_edge"][0], T["smoke_edge"][1], r + wx * 0.5)
        img = img * (1 - np.clip(body * 0.4 + ridge * 0.85, 0, 1) * mask * T["smoke"]) +             ridge ** 4 * mask * T["smoke"] * T["smoke_rim"] * sm(0.0, 0.3, blur(img, 20 * res) + 0.1)

    # pass 4, film: Pro-Mist diffusion (energy-conserving: scatter a fraction of the light into two wide blurs, in
    # linear light; engine = UE Bloom with threshold -1 plus matching exposure compensation), halation (bright pass,
    # two radii, warm), edge softness, vignette, shoulder, tint, grain
    ml = np.clip(img, 0, None) ** 2.2
    a1, a2 = T["mist"]
    ml = ml * (1 - a1 - a2) + blur(ml, T["mist_r"][0] * res) * a1 + blur(ml, T["mist_r"][1] * res) * a2
    img = ml ** (1 / 2.2)
    bright = np.maximum(img - T["halo_thr"], 0)
    halo = blur(bright, T["halo_r"][0] * res) * T["halo_w"][0] + blur(bright, T["halo_r"][1] * res) * T["halo_w"][1]
    img = img + (blur(img, T["edge_soft"][2] * res) - img) * sm(T["edge_soft"][0], T["edge_soft"][1], r)
    img = img * (1 - T["vignette"] * sm(0.35, 1.45, r) ** T["vignette_pow"])
    rgb = split_tone(np.clip(img, 0, None), T) + halo[..., None] * np.array(T["halo_tint"], np.float32)
    L = rgb @ LW
    rgb *= (shoulder(L, T["knee"], T["paper"]) / np.maximum(L, 1e-5))[..., None]
    fo = (np.array([0.0, 0.0]) if t is None else                          # a new grain offset 24 times a second
          np.random.default_rng(int(t * 24)).random(2) * 256)
    gn = sample_noise((X + fo[0]) / (256 * T["grain_px"] * res), (Y + fo[1]) / (256 * T["grain_px"] * res), 3) - 0.5
    gy = np.clip(rgb @ LW, 0, 1)
    rgb = rgb + (gn * T["grain"] * (T["grain_floor"] + (1 - T["grain_floor"]) * 4 * gy * (1 - gy)))[..., None]
    return np.clip(rgb, 0, 1)


# ---------- the four looks ----------

FOCUS = {cam: None for cam in CAMS}  # None = median depth of the frame centre
EXPO = {"Shot_ThirdPerson": 71.4, "Shot_Wide": 25.1, "Shot_Window": 53.4}  # stand-in for converged eye adaptation

BASE = dict(
    fstop=1.4, sensor_mm=144.0, coc_max=36, micro=0.45, ink_defocus=0.75,
    mist=(0.16, 0.10), mist_r=(10, 60),
    ev=0.0, roll=1.2, film_toe=0.62, film_shoulder=0.18, black=0.0, white=1.0, scurve=0.5, gamma=1.0,
    w_near=2.0, w_far=1.0, sil=(0.04, 0.10), crease=(0.25, 0.55), crease_w=0.6, hair=(0.15, 0.35), hair_w=0.0,
    hair_dist=400, fade=(900, 2200), ink=0.9, ink_inv=0.0, ink_press=0.45, scratch=0.0,
    hatch=0.0, hatch_cm=1.6, hatch_deg=35, hatch_width=0.18, hatch_lo=(0.22, 0.4), hatch_hi=(0.1, 0.2),
    shadow_tint=(1.035, 1.0, 0.875), high_tint=(1.05, 1.0, 0.84), split=(0.1, 0.7),
    echo_n=2, echo_gap=6, echo_decay=0.6, echo_gain=0.6, echo_mix=0.25, echo_lighten=0.5,
    double=0.0, double_px=60, streak=0.0, streak_len=60, streak_thr=0.45,
    slip=0, slip_bands=0, tear=0, tear_cols=0, sort=0, sort_cols=0, sort_len=140, sort_thr=0.5,
    frame_slip=0, frame_slip_at=0.62,
    haze=0.0, haze_start=200, haze_dist=900, haze_level=0.06, edge_haze=(0.8, 1.4, 0.0),
    smoke=0.0, smoke_scale=1.0, smoke_warp=0.1, smoke_thin=8, smoke_edge=(0.75, 1.35), smoke_rim=0.25,
    halo_thr=0.6, halo_r=(8, 40), halo_w=(0.4, 0.25), halo_tint=(1.0, 0.82, 0.55),
    edge_soft=(0.7, 1.4, 2.5), vignette=0.45, vignette_pow=1.6, knee=0.68, paper=0.92,
    grain=0.06, grain_px=1.2, grain_floor=0.35,
    open={},
)


def look(**kw):
    p = dict(BASE)
    p.update(kw)
    return p


LOOKS = {
    "A": ("Silver print", "a soft night photograph on warm paper: Pro-Mist glow, milky blacks, a whisper of contour ink", look(
        ev=1.0, scurve=0.35, gamma=0.95, black=0.0, knee=0.5, paper=0.87,
        ink=0.55, w_near=1.4, w_far=0.8, crease_w=0.25, ink_inv=0.16,
        mist=(0.22, 0.14), halo_thr=0.45, halo_w=(0.5, 0.35),
        haze=0.3, haze_start=250, haze_dist=900, haze_level=0.10,
        echo_n=2, echo_gap=6, echo_gain=0.45, streak=0.25,
        vignette=0.4, grain=0.07, grain_px=1.4,
        open=dict(echo_n=3, echo_gap=11, echo_gain=1.2, echo_mix=0.45, streak=0.6, slip=10, slip_bands=3,
                  tear=40, tear_cols=2, frame_slip=90, edge_haze=(0.6, 1.3, 0.35)),
    )),
    "B": ("Etched", "ink first: weighted contours, world-anchored hatching, scratchboard light in the blacks", look(
        ev=0.6, scurve=0.75, gamma=1.0,
        ink=1.0, w_near=3.0, w_far=1.2, sil=(0.03, 0.08), crease=(0.2, 0.45), crease_w=0.85, hair_w=0.6,
        hair=(0.1, 0.25), ink_inv=0.34, ink_defocus=0.5, knee=0.55, paper=0.88,
        hatch=0.85, hatch_cm=2.4, hatch_width=0.2, hatch_hi=(0.0, 0.001), scratch=0.5,
        mist=(0.10, 0.06), halo_w=(0.3, 0.15), grain=0.045, vignette=0.35,
        echo_n=2, echo_gain=0.35, echo_mix=0.15, echo_lighten=0.3,
        open=dict(echo_n=3, echo_gap=9, echo_gain=1.0, echo_mix=0.4, slip=14, slip_bands=4, tear=30, tear_cols=3,
                  sort=0.8, sort_cols=2, streak=0.4),
    )),
    "C": ("Smoke nocturne", "Inside and Limbo: depth dissolves into warm haze, near shapes go to silhouette, black sand smoke falls at the edges", look(
        ev=0.5, scurve=0.7, gamma=1.1,
        ink=0.7, w_near=2.2, crease_w=0.4, ink_inv=0.25,
        haze=0.6, haze_start=330, haze_dist=600, haze_level=0.09, edge_haze=(0.8, 1.4, 0.15), knee=0.5, paper=0.86,
        smoke=1.0, smoke_rim=0.35, smoke_edge=(0.5, 1.15),
        mist=(0.18, 0.12), halo_thr=0.45, halo_w=(0.45, 0.35),
        echo_n=3, echo_gain=0.5, streak=0.35, streak_len=90, vignette=0.55,
        open=dict(echo_gap=10, echo_gain=1.3, echo_mix=0.5, smoke=1.0, smoke_edge=(0.45, 1.1), sort=0.9, sort_cols=3,
                  sort_len=220, tear=50, tear_cols=2, streak=0.7),
    )),
    "D": ("Time slip", "the multiple exposure is the hero: every frame slips down the gate, the ink misregisters", look(
        ev=0.6, scurve=0.55, gamma=0.95,
        ink=0.85, w_near=2.2, crease_w=0.5, ink_inv=0.24, knee=0.55, paper=0.88,
        haze=0.3, haze_level=0.12, edge_haze=(0.7, 1.35, 0.2),
        echo_n=3, echo_gap=8, echo_decay=0.75, echo_gain=0.8, echo_mix=0.3, echo_lighten=0.8,
        double=0.3, double_px=90, streak=0.45, streak_len=80, slip=6, slip_bands=2,
        open=dict(echo_gap=13, echo_gain=1.6, echo_mix=0.55, double=0.55, double_px=130, slip=18, slip_bands=5,
                  tear=60, tear_cols=3, sort=0.7, sort_cols=2, frame_slip=140, streak=0.8, smoke=0.5),
    )),
}


def save(rgb, path):
    Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


def sheet(names):
    cw, ch, lab, top, gap = 576, 324, 300, 70, 12
    W = lab + 5 * (cw + gap) + gap
    H = top + len(names) * (ch + gap) + gap
    S = Image.new("RGB", (W, H), (14, 13, 12))
    dr = ImageDraw.Draw(S)
    f_big = ImageFont.truetype("C:/Windows/Fonts/georgiab.ttf", 64)
    f_name = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 26)
    f_small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 18)
    for i, t in enumerate(["Raw Unreal frame", "Third person", "Wide", "Window", "Open tier (third person)"]):
        dr.text((lab + gap + i * (cw + gap), 28), t, fill=(214, 204, 182), font=f_name)
    for r, key in enumerate(names):
        y = top + gap + r * (ch + gap)
        name, desc, _ = LOOKS[key]
        dr.text((24, y + 6), key, fill=(232, 222, 198), font=f_big)
        dr.text((24, y + 92), name, fill=(232, 222, 198), font=f_name)
        line, ly = "", y + 136
        for wd in desc.split():  # wrap the description into the label column
            if dr.textlength(line + " " + wd, font=f_small) > lab - 48:
                dr.text((24, ly), line.strip(), fill=(150, 142, 128), font=f_small)
                line, ly = "", ly + 24
            line += " " + wd
        dr.text((24, ly), line.strip(), fill=(150, 142, 128), font=f_small)
        for i, fn in enumerate([f"raw_{CAMS[0]}.png"] + [f"{key}_{c}.png" for c in CAMS] +
                               [f"{key}_{CAMS[0]}_open.png"]):
            S.paste(Image.open(f"{ROOT}/{fn}").resize((cw, ch), Image.LANCZOS), (lab + gap + i * (cw + gap), y))
    S.save(f"{ROOT}/lookdev_sheet.png")
    print("sheet", f"{ROOT}/lookdev_sheet.png")


GROUPS = [  # recipe printout: the LOOKS values, grouped by material pass
    ("DOF (UE Cinematic DOF)", ["fstop", "sensor_mm", "coc_max"]),
    ("Soft image", ["micro"]),
    ("Tone", ["ev", "roll", "film_toe", "film_shoulder", "black", "white", "scurve", "gamma"]),
    ("Ink", ["ink", "ink_inv", "ink_press", "w_near", "w_far", "sil", "crease", "crease_w", "hair", "hair_w", "hair_dist", "fade", "ink_defocus"]),
    ("Hatch", ["hatch", "scratch", "hatch_cm", "hatch_deg", "hatch_width", "hatch_lo", "hatch_hi"]),
    ("Echo (vertical)", ["echo_n", "echo_gap", "echo_decay", "echo_gain", "echo_mix", "echo_lighten", "double",
                         "double_px", "streak", "streak_len", "streak_thr"]),
    ("Glitch", ["slip", "slip_bands", "tear", "tear_cols", "sort", "sort_cols", "sort_len", "sort_thr", "frame_slip",
                "frame_slip_at"]),
    ("Atmosphere", ["haze", "haze_start", "haze_dist", "haze_level", "edge_haze", "smoke", "smoke_scale", "smoke_warp",
               "smoke_thin", "smoke_edge", "smoke_rim"]),
    ("Mist and halation", ["mist", "mist_r", "halo_thr", "halo_r", "halo_w", "halo_tint"]),
    ("Film", ["edge_soft", "vignette", "vignette_pow", "knee", "paper", "shadow_tint", "high_tint", "split", "grain",
              "grain_px", "grain_floor"]),
]


def recipe(key):
    name, desc, P = LOOKS[key]
    out = [f"Look {key}: {name} ({desc})"]
    for title, keys in GROUPS:
        vals = [f"{k}={P[k]}" + (f" (open {P['open'][k]})" if k in P["open"] else "") for k in keys]
        if any(P[k] for k in keys) or any(k in P["open"] for k in keys):
            out.append(f"  {title}: " + ", ".join(vals))
    out.append(f"  Focus (cm): " + ", ".join(f"{c}={FOCUS[c]}" for c in CAMS))
    return "\n".join(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--recipe"]:
        print("\n\n".join(recipe(k) for k in LOOKS))
        sys.exit()
    for cam in CAMS:
        save(raw_frame(cam), f"{ROOT}/raw_{cam}.png")
    for key in sys.argv[1:] or list(LOOKS):
        P = LOOKS[key][2]
        for cam in CAMS:
            save(render(cam, P), f"{ROOT}/{key}_{cam}.png")
            save(render(cam, P, open_tier=True), f"{ROOT}/{key}_{cam}_open.png")
            print("rendered", key, cam)
    sheet([k for k in LOOKS if os.path.exists(f"{ROOT}/{k}_{CAMS[0]}_open.png")])
