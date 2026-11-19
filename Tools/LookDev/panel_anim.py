"""One intro panel as a 2.5D parallax shot (lookdev lane), from capture_layers.py output.
  python Tools/LookDev/panel_anim.py TestB [--still]
Each layer (far, mid, fx, near) gets its own ink-wash treatment (panels.treatment, keyed together), the fx layer a
charcoal-and-light treatment. The camera drifts and pushes; layers move at their own rates; dust drifts between
the layers; the light flickers; a thin sand trickle falls; black sand dissolves the panel in and out; the subtitle
fades in. Writes Saved/LookDev/panels/<name>.mp4 (1920x1080, 24 fps, 8 s), <name>_layers.png (contact sheet of the
layers) and the 2k layer textures T_Intro_<name>_<layer>.png."""
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lookdev as L  # noqa: E402
import panels as Pn  # noqa: E402

cv2 = L.cv2
SRC = Pn.OUT + "/layers_src"
ORDER = ["far", "mid", "figure", "fx", "near"]       # back to front
DEPTH = {"far": 0.25, "mid": 0.6, "figure": 0.62, "fx": 0.7, "near": 1.0}  # parallax rate
LOOK = {"far": (0.8, 0.22, 0.0, 0.7), "mid": (1.0, 0.0, 0.0, 0.7), "near": (1.2, 0.0, 0.45, 1.6)}  # figure is painted  # line, paper, ink, edge
FPS, SECS, OW, OH = 24, 8.0, 1920, 1080
TRICKLE = (0.47, 0.30, 0.62)                         # x, top, bottom of the sand trickle (fraction of frame)
TEXT = {"TestA": "Something stands at the foot of the bed. It is patient.",
        "TestB": "Something stands at the foot of the bed. It is patient."}


def read(name, layer, p):
    a = cv2.imread(f"{SRC}/{name}_{layer}_{p}_0.exr", cv2.IMREAD_UNCHANGED)
    return a[..., 2::-1].astype(np.float32) if p != "depth" else a[..., 2].astype(np.float32)


def layer_images(name, pose):
    """Treated RGBA (float) per layer at capture resolution."""
    L.POSE[name] = pose
    L.EXPO[name] = 1.0
    def alpha(ly):  # SceneColorHDR alpha is inverse opacity; the far layer is the opaque backdrop
        inv = cv2.imread(f"{SRC}/{name}_{ly}_alpha_0.exr", cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32)
        return np.ones_like(inv) if ly == "far" else 1 - np.clip(inv, 0, 1)
    raw = {ly: (read(name, ly, "color"), np.clip(read(name, ly, "depth"), 1, 1e6), read(name, ly, "normal"),
                read(name, ly, "base"), alpha(ly))
           for ly in ORDER if os.path.exists(f"{SRC}/{name}_{ly}_color_0.exr")}
    far_c, _, _, _, far_a = raw["far"]
    key = 0.055 / max(float(np.median((far_c @ L.LW)[far_a > 0.5])), 1e-7)  # one exposure for every layer (night)
    out = {}
    for ly, (c, d, n, b, a) in raw.items():
        n = n * 2 - 1 if n.min() >= 0 else n
        n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-4)
        wp, th = L.world_pos(name, d)
        if ly == "fx":
            rgb, a = charcoal_light(c * key, a)
        else:
            if ly != "far":  # clean edges: drop the 1 px rim the capture blended with black, extend the colour past it
                inner = cv2.erode((a > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(np.float32)
                c, b = fill_out(c, inner), fill_out(b, inner)
                a = L.blur(inner, 0.6)                                   # a 1-2 px anti-aliased edge, no halo
            rgb = Pn.treatment(c, d, n, b, wp, th, {"key": key, "line": LOOK[ly][0]})
            rgb = rgb + (Pn.PAPER - rgb) * LOOK[ly][1]                   # far: aerial perspective, lighter washes
            rgb = rgb + (Pn.INK - rgb) * LOOK[ly][2]                     # near: charcoal silhouette
        out[ly] = np.dstack([rgb, a])                                    # straight alpha; premultiplied at composite
    return out


def fill_out(img, mask):
    """Pull-push fill: colour outside `mask` comes from the nearest inside colours (so filters never pull black)."""
    out, m = img * mask[..., None], mask.copy()
    for s in (2, 4, 8, 16, 32):
        num, den = L.blur(img * mask[..., None], s), L.blur(mask, s)[..., None]
        fill = num / np.maximum(den, 1e-4)
        out = np.where((m[..., None] < 0.5) & (den > 1e-3), fill, out)
        m = np.maximum(m, (den[..., 0] > 1e-3).astype(np.float32))
    return out


def charcoal_light(c, a):
    """FX layer: light shafts become soft cream light (lighten), sand becomes charcoal grain (darken). Returned as a
    premultiplied-style pair: colour and coverage."""
    Y = c @ L.LW
    light = L.sm(0.05, 1.2, Y / (1 + Y))
    a = np.maximum(a, L.sm(0.03, 0.6, Y / (1 + Y)))                    # translucent shafts write no opacity: use light
    h, w = Y.shape
    grain = L.sample_noise(*np.meshgrid(np.arange(w) / 220.0, np.arange(h) / 220.0), 3)
    dark = (Y < 0.02) & (a > 0.3)                                     # sand splats render dark (black sand)
    col = np.where(dark[..., None], Pn.INK * (0.8 + 0.4 * grain[..., None]), Pn.PAPER * (0.75 + 0.25 * light[..., None]))
    cov = np.clip(np.where(dark, a * (0.6 + 0.4 * grain), light * a * 0.5), 0, 1)  # shafts stay subtle
    return col.astype(np.float32), L.blur(cov.astype(np.float32), 1.2)


def dust(h, w, n=260, seed=11):
    rng = np.random.default_rng(seed)
    return {"x": rng.uniform(0, w, n), "y": rng.uniform(0, h, n), "z": rng.uniform(0.2, 1.1, n),
            "r": rng.uniform(0.8, 2.6, n), "ph": rng.uniform(0, 6.28, n), "vx": rng.normal(0, 3, n), "vy": rng.normal(-2, 3, n)}


def sand_mask(t, h, w, inn):
    """Black-sand dissolve: grains fall away top to bottom (inn: 0..1 reveal progress)."""
    u, v = np.meshgrid(np.arange(w) / w, np.arange(h) / h)
    n = L.sample_noise(u * 6.0, v * 3.4, 3) * 0.35 + L.sample_noise(u * 1.3, v * 0.8, 0) * 0.65
    f = v * 0.6 + n * 0.4                                               # top first, grain by grain
    return L.sm(-0.04, 0.04, inn * 1.2 - 0.1 - f)


def render(name, layers, still=False):
    from PIL import Image, ImageDraw, ImageFont
    h, w = next(iter(layers.values())).shape[:2]
    os.makedirs(f"{Pn.OUT}/{name}_frames", exist_ok=True)
    paper = Pn.paper_tex(OH, OW)
    D = dust(OH, OW)
    font = ImageFont.truetype(Pn.FONT, 50)
    frames = [int(SECS * FPS * 0.5)] if still else range(int(SECS * FPS))
    for fi in frames:
        t = fi / FPS
        s = t / SECS
        ease = s * s * (3 - 2 * s)
        frame = np.zeros((OH, OW, 3), np.float32) + Pn.INK
        for ly in ORDER:
            if ly not in layers:
                continue
            p = DEPTH[ly]
            sc = (OW / w) * (1.0 + 0.035 * p * ease + 0.02)                  # slow push, nearer grows faster
            dx = (ease - 0.5) * 70 * p                                          # lateral drift, nearer moves more
            dy = (ease - 0.5) * -12 * p
            M = np.float32([[sc, 0, OW / 2 - sc * w / 2 + dx], [0, sc, OH / 2 - sc * h / 2 + dy]])
            lay = cv2.warpAffine(layers[ly], M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            col, a = lay[..., :3], np.clip(lay[..., 3:4], 0, 1)
            if ly == "fx":
                flick = 1 + 0.07 * math.sin(t * 7.1) * math.sin(t * 2.3 + 1.0)   # the light breathes and flickers
                a = np.clip(a * flick, 0, 1)
            frame = frame * (1 - a) + col * a                            # (col * a) is the premultiplied colour
            if ly == "mid":  # dust between mid and near: soft specks, brighter in the light
                X = (D["x"] + D["vx"] * t + 40 * D["z"] * (ease - 0.5)) % OW
                Y = (D["y"] + D["vy"] * t + 6 * np.sin(t * 0.7 + D["ph"])) % OH
                dl = np.zeros((OH, OW), np.float32)
                for x, y, r, z in zip(X, Y, D["r"], D["z"]):
                    cv2.circle(dl, (int(x * 4), int(y * 4)), int(r * z * 4), 1.0, -1, cv2.LINE_AA, shift=2)
                dl = L.blur(dl, 0.8) * (0.25 + 0.55 * np.clip(frame @ L.LW, 0, 1))
                frame = frame + (Pn.PAPER - frame) * dl[..., None] * 0.5
        # a thin sand trickle falling through the light (the element that moves inside the frame): grains, not a line
        tx = OW * TRICKLE[0] + 70 * DEPTH["mid"] * (ease - 0.5)
        y0, y1 = OH * TRICKLE[1], OH * TRICKLE[2]
        rng = np.random.default_rng(7)                                   # the same grains every frame: they fall
        gy = y0 + (rng.random(40) + t * 0.9) % 1.0 * (y1 - y0)
        gx = tx + rng.normal(0, 1.2, 40)
        gl = np.zeros((OH, OW), np.float32)
        for xx, yy in zip(gx, gy):
            fade = min(1.0, (yy - y0) / 30, (y1 - yy) / 30)
            cv2.ellipse(gl, (int(xx * 4), int(yy * 4)), (4, 9), 0, 0, 360, max(fade, 0), -1, cv2.LINE_AA, shift=2)
        frame = frame * (1 - 0.75 * gl[..., None]) + Pn.INK * 0.75 * gl[..., None]
        frame *= paper[..., None]
        r = np.hypot(*np.meshgrid((np.arange(OW) - OW / 2) / (OW / 2), (np.arange(OH) - OH / 2) / (OH / 2)))
        frame *= (1 - 0.45 * L.sm(0.6, 1.5, r))[..., None]
        frame *= (1 - 0.45 * L.sm(0.72, 1.0, np.arange(OH) / OH))[:, None, None]   # a darker foot for the subtitle
        reveal = min(1.0, t / 1.4) if t < 4 else min(1.0, (SECS - t) / 1.2)
        m = sand_mask(t, OH, OW, reveal)[..., None]
        frame = Pn.INK * 0.6 + (frame - Pn.INK * 0.6) * m
        im = Image.fromarray((np.clip(frame, 0, 1) * 255).astype(np.uint8))
        txt = TEXT.get(name, "")
        ta = max(0.0, min(1.0, (t - 1.6) / 0.8, (SECS - 1.0 - t) / 0.6))
        if txt and ta > 0:  # draw the line once, opaque, on its own layer; fade the whole layer (PIL text ignores alpha)
            lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(lay)
            tw = dr.textlength(txt, font=font)
            dr.text(((OW - tw) / 2 + 2, OH * 0.86 + 2), txt, font=font, fill=(10, 8, 6, 150))
            dr.text(((OW - tw) / 2, OH * 0.86), txt, font=font, fill=(236, 226, 204, 255))
            a = np.asarray(lay).astype(np.float32) / 255
            base = np.asarray(im).astype(np.float32) / 255
            k = a[..., 3:4] * ta
            im = Image.fromarray((np.clip(base * (1 - k) + a[..., :3] * k, 0, 1) * 255).astype(np.uint8))
        im.save(f"{Pn.OUT}/{name}_frames/{fi:04d}.png")
    if not still:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i",
                        f"{Pn.OUT}/{name}_frames/%04d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
                        "-movflags", "+faststart", f"{Pn.OUT}/{name}.mp4"], check=True)
        print("mp4", f"{Pn.OUT}/{name}.mp4")


def paint_figure(layers, cx, base, hgt, box):
    """The hooded figure as a hand-painted charcoal layer (SK_Hero renders as a thin shell in captures for now):
    the staged mesh is cut out of the mid layer inside its box, and the silhouette gets its own layer with alpha."""
    import storyboard_shapes as SS  # noqa: F401  (kept local: only this panel uses it)
    return SS.hooded_layer(layers, cx, base, hgt, box)


def layer_sheet(name, layers):
    from PIL import Image, ImageDraw, ImageFont
    cw, ch, gap = 768, 432, 14
    S = Image.new("RGB", (len(layers) * (cw + gap) + gap, ch + 70), (14, 13, 12))
    dr = ImageDraw.Draw(S)
    f = ImageFont.truetype(Pn.FONT, 30)
    for i, ly in enumerate([o for o in ORDER if o in layers]):
        rgba = cv2.resize(layers[ly], (cw, ch), interpolation=cv2.INTER_AREA)
        yy, xx = np.mgrid[0:ch, 0:cw]
        chk = np.where(((yy // 16 + xx // 16) % 2)[..., None] == 0, 0.30, 0.22).astype(np.float32)
        img = chk * (1 - rgba[..., 3:4]) + rgba[..., :3] * rgba[..., 3:4]
        S.paste(Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)), (gap + i * (cw + gap), gap))
        dr.text((gap + i * (cw + gap), ch + gap + 12), f"{ly} (parallax {DEPTH[ly]})", fill=(226, 214, 188), font=f)
        tex = cv2.resize(layers[ly], (2048, 1152), interpolation=cv2.INTER_AREA)      # 2k per layer (budget)
        cv2.imwrite(f"{Pn.OUT}/T_Intro_{name}_{ly}.png",
                    cv2.cvtColor((np.clip(tex, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    S.save(f"{Pn.OUT}/{name}_layers.png")
    print("layers", f"{Pn.OUT}/{name}_layers.png")


def self_check(name, layers):
    """Before sending: alpha edge width and halos per layer, then luminance pops between frames (outside the sand
    dissolves). Prints a verdict per check; nothing is written."""
    ok = True
    for ly, rgba in layers.items():
        if ly in ("far", "fx"):
            continue
        a = rgba[..., 3]
        solid = (a > 0.5).astype(np.uint8)
        rim = cv2.morphologyEx(solid, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).sum() / 2 + 1
        width = float(((a > 0.02) & (a < 0.98)).sum() / rim)
        ring = (a > 0.02) & (a < 0.5)
        band = (a > 0.98) & cv2.dilate(ring.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
        Y = rgba[..., :3] @ L.LW
        halo = float(max(0.0, Y[ring].mean() - Y[band].mean())) if ring.any() and band.any() else 0.0  # light fringe
        good = width <= 2.5 and halo < 0.08
        ok &= good
        print(f"check {ly}: alpha edge {width:.2f} px, halo {halo:.3f} -> {'ok' if good else 'FIX'}")
    fr = sorted(f for f in os.listdir(f"{Pn.OUT}/{name}_frames") if f.endswith(".png"))
    lum, worst, prev = [], (0.0, -1), None
    for i, f in enumerate(fr):
        y = cv2.imread(f"{Pn.OUT}/{name}_frames/{f}", cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
        lum.append(float(y.mean()))
        if prev is not None and 1.5 < i / FPS < SECS - 1.3:  # outside the sand dissolves
            worst = max(worst, (float((np.abs(y - prev) > 0.25).mean()), i))  # area that jumps in one frame
        prev = y
    steps = [abs(lum[i] - lum[i - 1]) for i in range(1, len(lum)) if 1.5 < i / FPS < SECS - 1.3]
    pop = max(steps) if steps else 0.0
    good = pop < 0.006 and worst[0] < 0.002
    ok &= good
    print(f"check frames: max mean-luminance step {pop:.4f}, largest area jumping in one frame {worst[0] * 100:.3f}% "
          f"(frame {worst[1]}) -> {'ok' if good else 'FIX'}")
    print("self-check", "PASSED" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    name = sys.argv[1]
    poses = {"TestB": ((330, 40, 160), (-7.1, -134.0), 60.0), "TestA": ((0, -330, 150), (-15.5, 22.0), 60.0)}
    lays = layer_images(name, poses[name])
    if name == "TestB":  # paint-over: the hooded figure where the staged SK_Hero stood (box from the capture)
        lays = paint_figure(lays, cx=930, base=1090, hgt=760, box=(700, 380, 1280, 1100))
    layer_sheet(name, lays)
    render(name, lays, still="--still" in sys.argv)
    if "--still" not in sys.argv:
        self_check(name, lays)
