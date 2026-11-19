"""Intro cinematic panels (lookdev lane): in-engine captures pushed through an ink-wash illustration treatment,
split into depth layers for parallax. Offline only; the panels are baked into textures, so nothing here has to run
in a material. Sources are capture_passes.py captures named Panel_<n> (SIZE=2304x1296 for parallax overscan).
  python Tools/LookDev/panels.py            -> Saved/LookDev/panels/Panel_<n>.png, layers, contact sheet
Look: hand-inked contours (geometry ink + XDoG detail) over sepia washes in 4 soft bands with wet edges and
pigment granulation, on warm paper. The paper itself is a separate screen-fixed overlay (T_IntroPaper), so it
never slides with the parallax layers."""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lookdev as L  # noqa: E402

cv2 = L.cv2
OUT = L.ROOT + "/panels"
PAPER = np.array([0.93, 0.89, 0.80], np.float32)
INK = np.array([0.10, 0.075, 0.06], np.float32)


def treatment(c, d, n, b, wp, th, P):
    """HDR capture -> ink-wash illustration (RGB, no paper texture)."""
    h, w = d.shape
    res = h / 1080
    Y = c @ L.LW
    k = P["key"] if "key" in P else 0.09 / max(np.median(Y), 1e-7)    # key each panel on its mid-tones
    Y = Y * k * 2 ** P.get("ev", 0.0)                                    # (layers share their panel's key)
    y = L.enc(L.film(Y / (1 + Y / 1.2), toe=0.62))                      # lamps and shafts roll off, never clip
    # abstraction: edge-preserving smoothing (the painter simplifies), then soft-quantised wash bands
    ys = y.astype(np.float32)
    for _ in range(3):
        ys = cv2.bilateralFilter(ys, 9, 0.08, 6 * res)
    big = cv2.edgePreservingFilter(np.dstack([ys] * 3).__mul__(255).astype(np.uint8), flags=cv2.RECURS_FILTER,
                                   sigma_s=P.get("simplify", 50), sigma_r=0.25)[..., 0].astype(np.float32) / 255
    ys = 0.7 * big + 0.3 * ys                                            # broad washes, a little texture left
    lv = P.get("levels", 4)
    q = ys * lv
    yw = (np.floor(q) + L.sm(0.3, 0.7, q - np.floor(q))) / lv
    yw = 0.65 * yw + 0.35 * ys                                           # keep a little of the photograph inside
    # wet edges: pigment pools where a wash band ends; granulation settles in the darker washes
    edge = np.abs(yw - L.blur(yw, 2.5 * res))
    gran = L.sample_noise(*np.meshgrid(np.arange(w) / 300, np.arange(h) / 300), 2) - 0.5
    wash = np.clip(yw - edge * 1.4 - gran * 0.04 * (1 - yw), 0, 1)
    # lines: geometry ink (silhouettes, creases, albedo hairlines) plus XDoG for the drawn detail
    Pk = dict(L.LOOKS["B"][2])
    Pk.update(w_near=3.2 * P.get("line", 1.0), w_far=1.6, hair_w=0.7, fade=(1500, 3500), scratch=0.0,
              hatch=P.get("hatch", 0.7), hatch_cm=P.get("hatch_cm", 2.0), hatch_lo=(0.25, 0.45))
    ik, hatch = L.ink(d, n, b, wp, th, ys, Pk, res)                      # world-anchored engraving in the shade
    g1, g2 = L.blur(ys, 1.2 * res), L.blur(ys, 1.2 * 1.6 * res)
    xdog = 1 - L.sm(-0.02, 0.0, g1 - 0.98 * g2)                          # dark side of the luminance edges
    line = np.clip(np.maximum(ik, xdog * 0.6 * L.sm(0.08, 0.3, ys)), 0, 1)  # no XDoG mush in the blacks
    # colour: wash between ink umber and paper, lines in ink on top
    wash = wash * (1 - np.maximum(hatch, 0) * 0.55)
    t = wash[..., None]
    rgb = INK + (PAPER - INK) * t ** 0.9
    return rgb * (1 - line[..., None] * 0.9) + INK * line[..., None] * 0.9


def paper_tex(h, w, seed=3):
    """T_IntroPaper: fibres + tooth, ~1.0 mean, applied with Modulate over everything."""
    rng = np.random.default_rng(seed)
    tooth = L.blur(rng.standard_normal((h, w)).astype(np.float32), 0.8)
    fib = L.blur(rng.standard_normal((h, w)).astype(np.float32), 1.0)
    fib = cv2.filter2D(fib, -1, np.ones((1, 15), np.float32) / 15)        # short horizontal fibres
    blot = L.blur(rng.standard_normal((h // 8, w // 8)).astype(np.float32), 3)
    blot = cv2.resize(blot, (w, h), interpolation=cv2.INTER_CUBIC)
    p = 1 + tooth * 0.035 + fib * 0.05 + blot * 0.05
    return np.clip(p / p.mean(), 0.8, 1.1)


# name: (narration subtitle, seconds, treatment params, layer count)
PANELS = {
    "Panel_1": ("There is a man who keeps sleeping through his life.", 7, {"ev": 0.6}, 4),
    "Panel_2": ("He means to get up. He has meant to for a while.", 6, {"ev": 0.4}, 3),
    "Panel_3": ("Seventeen days. He crossed out every one.", 7, {"ev": 0.3}, 2),
    "Panel_4": ("The letters wait. The cup waits. Everything waits.", 7, {"ev": 0.4}, 3),
    "Panel_5": ("In this dream, the chores have grown teeth.", 8, {"ev": 0.2, "line": 1.3}, 3),
    "Panel_6": ("They are completely serious. Today, you will get dressed.", 6, {"ev": 0.3, "line": 1.2}, 3),
    "Panel_7": ("Today, you will leave the house.", 6, {"ev": 0.5}, 3),
    "Panel_8": ("", 4, {"ev": 0.3}, 2),  # T0: the phone buzzes; reuses the Panel_3 capture
}
SOURCE = {"Panel_8": "Panel_3"}
FONT = "P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-Medium.ttf"  # the game font, weight 500
NIGHTSTAND_TOP = 79.0  # cm, from the level probe


def poses():
    """Panel camera poses from Tools/LookDev/panels.txt (name cam x,y,z,pitch,yaw,fov), overridden by the capture
    log lines 'POSE <name> x,y,z,pitch,yaw,fov' in panels/src/poses.txt (real camera actors supply their own)."""
    out = {}
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (here + "/panels.txt", OUT + "/src/poses.txt"):
        if not os.path.exists(path):
            continue
        for ln in open(path, encoding="utf-8"):
            parts = ln.split()
            if len(parts) >= 3:
                x, y, z, pitch, yaw, fov = (float(v) for v in parts[-1].split(","))
                out[parts[1] if parts[0] == "POSE" else parts[0]] = ((x, y, z), (pitch, yaw), fov)
    return out


def ink_stroke(img, pts, width, rng, color=INK, wobble=1.2, alpha=0.92):
    """A hand-inked stroke: jittered polyline, width swelling in the middle, anti-aliased."""
    pts = np.asarray(pts, np.float32)
    seg = np.linspace(0, 1, 24)
    path = np.concatenate([p0 + (p1 - p0) * seg[:, None] for p0, p1 in zip(pts[:-1], pts[1:])])
    path = path + L.blur(rng.standard_normal(path.shape).astype(np.float32), 3) * wobble
    mask = np.zeros(img.shape[:2], np.float32)
    for i in range(len(path) - 1):
        t = i / max(len(path) - 2, 1)
        wdt = max(1, int(round(width * (0.55 + 0.45 * np.sin(np.pi * t)))))
        cv2.line(mask, tuple(int(v) for v in np.round(path[i] * 4)), tuple(int(v) for v in np.round(path[i + 1] * 4)),
                 1.0, wdt, cv2.LINE_AA, shift=2)
    m = np.clip(mask, 0, 1)[..., None] * alpha
    img[:] = img * (1 - m) + np.asarray(color, np.float32) * m


def phone(img, cx, cy, scale, lit, crossed, buzz, seed=5):
    """The phone, drawn by hand onto the top-down panel: ink outline, a calendar on the screen with `crossed` days
    struck through, a warm screen glow on the nightstand, and buzz marks when it rings."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    pw, ph = 7.2 * scale, 15.0 * scale
    x0, y0, x1, y1 = cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2
    X, Y = L.grid(h, w)
    r = np.hypot((X - cx) / (pw * 1.6), (Y - cy) / (ph * 1.1))
    img[:] = img + np.array([1.0, 0.92, 0.72], np.float32) * (lit * 0.35 * np.exp(-r * r * 1.5))[..., None]
    img[(X > x0) & (X < x1) & (Y > y0) & (Y < y1)] = INK * 1.2            # the black glass
    sx0, sy0, sx1, sy1 = x0 + 0.5 * scale, y0 + 1.6 * scale, x1 - 0.5 * scale, y1 - 1.6 * scale
    scr = (X > sx0) & (X < sx1) & (Y > sy0) & (Y < sy1)
    img[scr] = img[scr] * (1 - lit) + PAPER * 0.9 * lit                  # the screen, lit like paper
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        ink_stroke(img, [a, b], 0.35 * scale, rng)
    cw, ch = (sx1 - sx0) / 7, (sy1 - sy0 - 2.5 * scale) / 5             # calendar: 7 columns, 5 rows
    for day in range(31):
        col, row = day % 7, day // 7
        gx, gy = sx0 + col * cw, sy0 + 2.5 * scale + row * ch
        cv2.rectangle(img, (int(gx + 2), int(gy + 2)), (int(gx + cw - 2), int(gy + ch - 2)),
                      tuple(float(v) for v in INK * 1.5), 1, cv2.LINE_AA)
        if day < crossed:
            ink_stroke(img, [(gx + 0.2 * cw, gy + 0.2 * ch), (gx + 0.8 * cw, gy + 0.8 * ch)], 0.16 * scale, rng, wobble=0.6)
            ink_stroke(img, [(gx + 0.8 * cw, gy + 0.2 * ch), (gx + 0.2 * cw, gy + 0.8 * ch)], 0.16 * scale, rng, wobble=0.6)
    ink_stroke(img, [(sx0 + 0.8 * scale, sy0 + 1.0 * scale), (sx1 - 2.5 * scale, sy0 + 1.0 * scale)], 0.25 * scale, rng)
    if buzz:  # vibration marks, three arcs a side
        for side in (-1, 1):
            for k in range(3):
                rr = pw / 2 + (1.2 + 1.1 * k) * scale
                pts = [(cx + side * rr * np.cos(t), cy + rr * 1.8 * np.sin(t)) for t in np.linspace(-0.5, 0.5, 6)]
                ink_stroke(img, pts, 0.3 * scale, rng, wobble=0.8)


def split_layers(rgb, d, k):
    """k depth layers for parallax, far to near. Cuts sit at depth-histogram valleys near even quantiles, so objects
    rarely tear. Each layer's colour has the nearer content inpainted away; its alpha covers its own depth range,
    dilated 3 px so the seams never show."""
    ld = np.log(np.clip(d, 10, 5e4))
    qs = np.quantile(ld, np.linspace(0, 1, k + 1)[1:-1])
    hist, edges = np.histogram(ld, 256)
    cuts = []
    for q in qs:
        lo, hi = np.searchsorted(edges, q - 0.15), np.searchsorted(edges, q + 0.15)
        j = lo + int(np.argmin(hist[lo:hi])) if hi > lo else np.searchsorted(edges, q)
        cuts.append(edges[min(j, 255)])
    bounds = [-1e9] + sorted(cuts) + [1e9]
    out = []
    u8 = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    for i in range(k, 0, -1):                                            # far -> near
        lo, hi = bounds[i - 1], bounds[i]
        own = ((ld >= lo) & (ld < hi)).astype(np.uint8)
        nearer = (ld < lo).astype(np.uint8)
        col = cv2.inpaint(u8, cv2.dilate(nearer, np.ones((9, 9), np.uint8)), 7, cv2.INPAINT_TELEA) if nearer.any() else u8
        alpha = np.ones_like(own) if i == k else cv2.dilate(own, np.ones((7, 7), np.uint8))
        alpha = L.blur(alpha.astype(np.float32), 1.0)
        out.append(np.dstack([col, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)]))
    return out, [float(np.exp(b)) for b in sorted(cuts)]


def contact_sheet(names):
    from PIL import Image, ImageDraw, ImageFont
    cw, ch, gap, cap = 720, 405, 16, 70
    S = Image.new("RGB", (4 * cw + 5 * gap, 2 * (ch + cap) + 3 * gap), (14, 13, 12))
    dr = ImageDraw.Draw(S)
    f = ImageFont.truetype(FONT, 28)
    for i, n in enumerate(names):
        x, y = gap + (i % 4) * (cw + gap), gap + (i // 4) * (ch + cap + gap)
        S.paste(Image.open(f"{OUT}/{n}.png").resize((cw, ch), Image.LANCZOS), (x, y))
        dr.text((x, y + ch + 10), PANELS[n][0] or "(the phone buzzes: beat T0)", fill=(226, 214, 188), font=f)
        dr.text((x + cw - 40, y + ch + 10), f"{PANELS[n][1]}s", fill=(130, 122, 108), font=f)
    S.save(f"{OUT}/intro_contact_sheet.png")
    print("sheet", f"{OUT}/intro_contact_sheet.png")


def build(name, paper, poses_):
    src = SOURCE.get(name, name)
    c, d, n, b = L.load(src)
    wp, th = L.world_pos(src, d)
    _text, _secs, P, k = PANELS[name]
    rgb = treatment(c, d, n, b, wp, th, P)
    if src == "Panel_3":  # drawn by hand: no phone prop exists in the level yet
        h, w = d.shape
        sc = w / (2 * (poses_[src][0][2] - NIGHTSTAND_TOP) * math.tan(math.radians(poses_[src][2] / 2)))  # px per cm
        if name == "Panel_3":
            phone(rgb, w * 0.42, h * 0.5, sc, 0.55, 17, False)
        else:
            phone(rgb, w * 0.42, h * 0.5, sc, 0.95, 0, True)
    layers, cuts = split_layers(rgb, d, k)
    os.makedirs(f"{OUT}/layers", exist_ok=True)
    for i, lay in enumerate(layers):                                     # 2k at most per layer (budget)
        cv2.imwrite(f"{OUT}/layers/T_Intro_{name}_L{i}.png",
                    cv2.cvtColor(cv2.resize(lay, (2048, 1152), interpolation=cv2.INTER_AREA), cv2.COLOR_RGBA2BGRA))
    L.save(rgb * paper[..., None], f"{OUT}/{name}.png")
    print(name, "layers", len(layers), "cuts (cm)", [round(x) for x in cuts])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    L.SRC = OUT + "/src"
    POSES = poses()
    for nm, pose in POSES.items():
        L.POSE[nm] = pose
        L.EXPO[nm] = 1.0                                                  # treatment() keys each panel itself
    names = sys.argv[1:] or list(PANELS)
    h, w = cv2.imread(f"{L.SRC}/Panel_3_depth_0.exr", cv2.IMREAD_UNCHANGED).shape[:2]
    paper = paper_tex(h, w)
    L.save(np.dstack([paper / 1.1] * 3), f"{OUT}/T_IntroPaper.png")    # Modulate overlay, x1.1 in the material
    for nm in names:
        build(nm, paper, POSES)
    contact_sheet(list(PANELS))
