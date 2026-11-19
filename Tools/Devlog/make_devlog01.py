"""Devlog #1 video for FoA. Renders into P:/FoA-Devlog/videos/devlog01:
  devlog01_noVO.mp4 (1080p30 H.264 ~18 Mbps, AAC 48 kHz, -14 LUFS / -1 dBTP), devlog01_sfx.wav (SFX + ambience stem),
  media/ (one file per shot and per transition) + devlog01.fcpxml (editable timeline), devlog01_vo_beats.txt
  (timecoded narration beats + YouTube chapters), contact_sheet.png and thumbnail.png.
    python Tools/Devlog/make_devlog01.py [--preview]     # --preview: half-res stills check only, no encode
Sources are read-only. Recording footage is checked frame by frame: any frame where the editor is not in front
(terminals, other windows) is replaced by the last good frame, so no agent chat or private window ever appears.
"""
import glob
import json
import math
import os
import re
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile
from scipy.signal import resample_poly

OUT = "P:/FoA-Devlog/videos/devlog01"
MEDIA, WORK = f"{OUT}/media", f"{OUT}/work"
S, A, D = "P:/FoA/Saved", "P:/FoA-Assets", "P:/FoA-Devlog"
REC = f"{D}/recordings"
HERO_CLOCK = f"{S}/Devlog/hero_clock.mp4"
W, H, FPS = 1920, 1080, 30
F = f"{A}/fonts"
FONT = {"serif": f"{F}/CormorantGaramond/CormorantGaramond-Light.ttf",
        "serif_r": f"{F}/CormorantGaramond/CormorantGaramond-Regular.ttf",
        "serif_i": f"{F}/CormorantGaramond/CormorantGaramond-Italic.ttf",
        "sans": f"{F}/IBMPlexSans/IBMPlexSans-Light.ttf", "sans_r": f"{F}/IBMPlexSans/IBMPlexSans-Regular.ttf",
        "sans_m": f"{F}/IBMPlexSans/IBMPlexSans-Medium.ttf", "sans_sb": f"{F}/IBMPlexSans/IBMPlexSans-SemiBold.ttf"}
INK = (236, 229, 216)        # warm paper white for text
BG = (12, 11, 10)
EDITOR_REF = f"{D}/_ref/editor_layout.png"
EDITOR_PATCHES = [(0, 80, 760, 40), (1280, 125, 620, 30), (1282, 380, 90, 350)]  # toolbar, Outliner tabs, Hayba icon column
_fonts = {}


def font(key, size):
    if (key, size) not in _fonts:
        _fonts[key, size] = ImageFont.truetype(FONT[key], size)
    return _fonts[key, size]


# ---------- look ----------

_luts = {}


def grade(img, amount=1.0, gain=1.0, lift=0.0):
    """Warm monochrome: luminance, exposure, gentle S-curve, paper tint, all as 8-bit lookup tables (fast enough for
    every video frame). amount<1 keeps some of the source colour."""
    key = (gain, lift)
    if key not in _luts:
        v = np.clip(np.arange(256, dtype=np.float32) / 255 * gain + lift, 0, 1)
        v = v * 0.6 + (v * v * (3 - 2 * v)) * 0.4
        _luts[key] = [np.clip(v * k * 255, 0, 255).astype(np.uint8) for k in (1.0, 0.955, 0.875)]
        _luts[key, "c"] = np.clip(np.arange(256) * gain + lift * 255, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(np.ascontiguousarray(img), cv2.COLOR_RGB2GRAY)
    warm = cv2.merge([cv2.LUT(gray, lut) for lut in _luts[key]])
    if amount >= 1:
        return warm
    return cv2.addWeighted(cv2.LUT(np.ascontiguousarray(img), _luts[key, "c"]), 1 - amount, warm, amount, 0)


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_vig = (1 - 0.38 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.3).clip(0.45, 1)
VIGNETTE = cv2.merge([(_vig * 255).astype(np.uint8)] * 3)
_rng = np.random.default_rng(7)
GRAIN = []
for _ in range(6):
    g = _rng.normal(0, 4.2, (H, W)).astype(np.float32)
    GRAIN.append((cv2.merge([np.clip(g, 0, 255).astype(np.uint8)] * 3), cv2.merge([np.clip(-g, 0, 255).astype(np.uint8)] * 3)))


def finish(frame, i):
    """Vignette and film grain on every output frame, so mixed sources share one texture (saturating cv2 ops)."""
    f = cv2.multiply(np.ascontiguousarray(frame), VIGNETTE, scale=1 / 255)
    up, down = GRAIN[i % len(GRAIN)]
    return cv2.subtract(cv2.add(f, up), down)


_shadows = {}


def fit(img, mode="cover", box=(W, H), bg=BG):
    """cover: fill the box, cropping; contain: whole image on a dark card with a soft shadow (cached per size)."""
    bw, bh = box
    h, w = img.shape[:2]
    if mode == "cover":
        s = max(bw / w, bh / h)
        r = cv2.resize(img, (math.ceil(w * s), math.ceil(h * s)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        y0, x0 = (r.shape[0] - bh) // 2, (r.shape[1] - bw) // 2
        return r[y0:y0 + bh, x0:x0 + bw]
    s = min(bw * 0.86 / w, bh * 0.84 / h)
    rw, rh = round(w * s), round(h * s)
    r = cv2.resize(img, (rw, rh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    x0, y0 = (bw - rw) // 2, (bh - rh) // 2
    if (box, rw, rh) not in _shadows:
        canvas = Image.new("RGB", (bw, bh), bg)
        shadow = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(shadow).rectangle((x0 + 10, y0 + 16, x0 + rw + 10, y0 + rh + 16), fill=150)
        canvas.paste((0, 0, 0), (0, 0), shadow.filter(ImageFilter.GaussianBlur(22)))
        _shadows[box, rw, rh] = np.asarray(canvas)
    out = _shadows[box, rw, rh].copy()
    out[y0:y0 + rh, x0:x0 + rw] = r
    return out


def load(path, amount=1.0, gain=1.0, lift=0.0, crop=None):
    im = np.asarray(Image.open(path).convert("RGB"))
    if crop:
        x, y, w, h = crop
        im = im[y:y + h, x:x + w]
    return grade(im, amount, gain, lift)


def ease(t):
    return t * t * (3 - 2 * t)


def kenburns(img, n, z0=1.0, z1=1.07, p0=(0, 0), p1=(0, 0)):
    """Slow push on an already-fitted W x H frame. p = pan in pixels at the end of the move."""
    for i in range(n):
        t = ease(i / max(n - 1, 1))
        z = z0 + (z1 - z0) * t
        cx = W / 2 + (p0[0] + (p1[0] - p0[0]) * t)
        cy = H / 2 + (p0[1] + (p1[1] - p0[1]) * t)
        m = np.float32([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]])
        yield cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


# ---------- video sources ----------

_ref = None


def editor_ok(full):
    global _ref
    if _ref is None:
        _ref = np.asarray(Image.open(EDITOR_REF).convert("RGB")).astype(np.int16)
    return all(np.abs(full[y:y + h, x:x + w].astype(np.int16) - _ref[y:y + h, x:x + w]).mean() < 6
               for x, y, w, h in EDITOR_PATCHES)


def _decode(path, start, secs, w, h, vf=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", path, "-t", f"{secs:.3f}"]
    cmd += (["-vf", vf] if vf else []) + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        raw = p.stdout.read(w * h * 3)
        if len(raw) < w * h * 3:
            break
        yield np.frombuffer(raw, np.uint8).reshape(h, w, 3)
    p.stdout.close()
    p.wait()


def video(path, start, n, speed=1.0, crop=None, mode="cover", amount=1.0, gain=1.0, editor=False, box=(W, H)):
    """n frames at FPS from path. editor=True: a desktop recording. Every source frame is checked against static
    editor UI, and a frame is used only if its neighbours within 0.4 s pass too (so fading overlays such as the task
    switcher never show); failing frames are replaced by the last good one."""
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height,r_frame_rate", "-of", "csv=p=0", path], capture_output=True, text=True)
    sw, sh, rate = info.stdout.strip().split(",")[:3]
    sw, sh = int(sw), int(sh)
    src_fps = eval(rate)  # "5/1" from ffprobe
    secs = n / FPS * speed + 0.5
    def prep(fr):
        if crop:
            x, y, w, h = crop
            fr = fr[y:y + h, x:x + w]
        return fit(grade(fr, amount, gain), mode, box)
    if not editor:
        last = None
        frames = _decode(path, start, secs, sw, sh, f"setpts=PTS/{speed},fps={FPS}")
        for _ in range(n):
            fr = next(frames, None)
            last = prep(fr) if fr is not None else last
            yield last if last is not None else np.zeros((box[1], box[0], 3), np.uint8)
        frames.close()
        return
    flags = [editor_ok(fr) for fr in _decode(path, start, secs, sw, sh)]
    r = max(1, round(0.4 * src_fps))
    good = [all(flags[max(0, i - r):i + r + 1]) for i in range(len(flags))]
    src = _decode(path, start, secs, sw, sh)
    idx, cur, last = -1, None, None
    for k in range(n):
        want = min(int(k / FPS * speed * src_fps), len(flags) - 1)
        while idx < want:
            cur = next(src, None)
            idx += 1
            if cur is not None and good[idx]:
                last = prep(cur)
        yield last if last is not None else np.zeros((box[1], box[0], 3), np.uint8)  # black until a good frame
    src.close()


# ---------- text ----------

def text_layer(items, size=(W, H)):
    """items: (text, font_key, px, (x, y), alpha, anchor). Returns the text cropped to its bounding box:
    (rgb float32, alpha float32 0..1, x0, y0), so compositing touches only those pixels."""
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for text, key, px, xy, a, anchor in items:
        d.text(xy, text, font=font(key, px), fill=INK + (int(255 * a),), anchor=anchor)
    arr = np.asarray(im)
    ys, xs = np.nonzero(arr[..., 3])
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return arr[y0:y1, x0:x1, :3].astype(np.float32), arr[y0:y1, x0:x1, 3:].astype(np.float32) / 255, x0, y0


def over(frame, layer, a, dy=0):
    """Composite a text layer at opacity a, shifted down by dy pixels."""
    if a <= 0:
        return frame
    rgb, al, x0, y0 = layer
    y0 += dy
    h, w = al.shape[:2]
    out = frame.copy()
    m = al * a
    out[y0:y0 + h, x0:x0 + w] = (out[y0:y0 + h, x0:x0 + w] * (1 - m) + rgb * m).astype(np.uint8)
    return out


def wrap(text, key, px, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if font(key, px).getlength(t) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur]


LOWER_SHADE = None


def lower_third(frames, n, title, sub=None, top=False):
    """Plex Sans label, bottom left (or top right when the shot has its own UI down there), fading in after 0.5 s and
    out 0.4 s before the end. No rules, no dots."""
    global LOWER_SHADE
    if LOWER_SHADE is None:  # a soft darkening of the bottom band only, for legibility
        LOWER_SHADE = (np.clip(np.arange(330, dtype=np.float32) / 330, 0, 1) * 0.62)[:, None, None]
    if top:
        items = [(title, "sans_m", 34, (W - 110, 130), 1.0, "rs")] + ([(sub, "sans", 26, (W - 110, 172), 0.72, "rs")] if sub else [])
    else:
        items = [(title, "sans_m", 34, (110, H - 150), 1.0, "ls")] + ([(sub, "sans", 26, (110, H - 108), 0.72, "ls")] if sub else [])
    layer = text_layer(items)
    for i, fr in enumerate(frames):
        a = min(1, max(0, (i - 15) / 12)) * min(1, max(0, (n - 12 - i) / 12))
        if a > 0:
            fr = fr.copy()
            if top:
                fr[:330] = (fr[:330] * (1 - LOWER_SHADE[::-1] * a)).astype(np.uint8)
            else:
                fr[H - 330:] = (fr[H - 330:] * (1 - LOWER_SHADE * a)).astype(np.uint8)
            fr = over(fr, layer, a)
        yield fr


# ---------- transitions ----------

def fbm(seed, scale=(270, 480)):
    rng = np.random.default_rng(seed)
    acc = np.zeros((H, W), np.float32)
    for o, amp in ((4, 0.5), (8, 0.25), (16, 0.15), (48, 0.1)):
        acc += amp * cv2.resize(rng.random((max(2, scale[0] * o // 64), max(2, scale[1] * o // 64))).astype(np.float32),
                                (W, H), interpolation=cv2.INTER_CUBIC)
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    return acc


SAND_FIELD = 0.6 * fbm(1) + 0.4 * ((xx / W) * 0.7 + (yy / H) * 0.3)
SAND_FIELD = ((SAND_FIELD - SAND_FIELD.min()) / (SAND_FIELD.max() - SAND_FIELD.min())).astype(np.float32)
SPECK = (np.random.default_rng(3).random((H, W)) > 0.45).astype(np.float32)


SPECK_K = (0.92 * (0.55 + 0.45 * SPECK)).astype(np.float32)


def t_sand(a, b, p):
    """Black-sand dissolve: B grows through a noisy front whose edge is a band of black grains."""
    t = ease(p) * 1.16 - 0.08
    d = SAND_FIELD - t
    m = np.clip(0.5 - d / 0.035, 0, 1)
    out = cv2.blendLinear(np.ascontiguousarray(a), np.ascontiguousarray(b), 1 - m, m)
    keep = 1 - np.exp(-(d / 0.03) ** 2) * SPECK_K
    return cv2.multiply(out, cv2.merge([(keep * 255).astype(np.uint8)] * 3), scale=1 / 255)


MX, MY = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))


def t_smear(a, b, p):
    """Vertical time-shift smear: a warm highlight streak sweeps left to right, B behind it, both smeared vertically
    near the streak."""
    x0 = -260 + ease(p) * (W + 520)
    dx = np.arange(W, dtype=np.float32) - x0
    near = np.exp(-(dx / 260) ** 2)
    shift = np.broadcast_to(near * 90, (H, W))
    a2 = cv2.remap(cv2.blur(a, (1, 41)), MX, MY - shift, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    b2 = cv2.remap(cv2.blur(b, (1, 41)), MX, MY + shift, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    w = np.ascontiguousarray(np.broadcast_to(near, (H, W)))
    a_ = cv2.blendLinear(np.ascontiguousarray(a), a2, 1 - w, w)
    b_ = cv2.blendLinear(np.ascontiguousarray(b), b2, 1 - w, w)
    side = np.ascontiguousarray(np.broadcast_to(1 / (1 + np.exp(np.clip(dx / 40, -60, 60))), (H, W)))  # 1 left: B
    out = cv2.blendLinear(a_, b_, 1 - side, side)
    glow = np.exp(-(dx / 14) ** 2) * 0.85 + np.exp(-(dx / 140) ** 2) * 0.22
    row = (glow[:, None] * np.float32([255, 238, 205])).clip(0, 255).astype(np.uint8)[None]
    return cv2.add(out, np.ascontiguousarray(np.broadcast_to(row, (H, W, 3))))


def t_glitch(a, b, p, seed=0):
    """A short slip: horizontal slices jump, a faint channel split, A gives way to B halfway."""
    rng = np.random.default_rng(int(p * 1000) + seed)
    src = (a if p < 0.5 else b).copy()
    out = src.copy()
    for _ in range(9):
        y0 = rng.integers(0, H - 40)
        h = rng.integers(8, 70)
        out[y0:y0 + h] = np.roll(src[y0:y0 + h], rng.integers(-90, 90), axis=1)
    out[..., 0] = np.roll(out[..., 0], 6, axis=1)
    out[..., 2] = np.roll(out[..., 2], -6, axis=1)
    k = 1 - 0.35 * math.sin(p * math.pi)
    return (out * k).astype(np.uint8)


def t_fade(a, b, p):
    """Dip through black."""
    if p < 0.5:
        return (a * (1 - ease(p * 2))).astype(np.uint8)
    return (b * ease(p * 2 - 1)).astype(np.uint8)


TRANS = {"sand": t_sand, "smear": t_smear, "glitch": t_glitch, "fade": t_fade}
TRANS_SFX = {"sand": [("SFX/Sand/SFX_Sand_Shift_0{}.wav", -9), ("SFX/Dream/SFX_Dream_Whoosh_0{}.wav", -17)],
             "smear": [("SFX/Dream/SFX_Dream_Whoosh_0{}.wav", -11)],
             "glitch": [("SFX/Dream/SFX_Dream_Glitch_0{}.wav", -15)],
             "fade": []}


# ---------- segments ----------

class Seg:
    def __init__(self, name, secs, gen, trans=("sand", 20), vo=None, chapter=None, sfx=()):
        self.name, self.n, self.gen, self.trans = name, round(secs * FPS), gen, trans
        self.vo, self.chapter, self.sfx = vo, chapter, list(sfx)


def still(path, secs, label=None, sub=None, mode="cover", z=(1.0, 1.07), pan=((0, 0), (0, 0)), top=False, **g):
    img = fit(load(path, **g), mode)
    def gen(n):
        fr = kenburns(img, n, z[0], z[1], pan[0], pan[1])
        return lower_third(fr, n, label, sub, top) if label else fr
    return secs, gen


def clip(path, start, secs, label=None, sub=None, **kw):
    def gen(n):
        fr = video(path, start, n, **kw)
        return lower_third(fr, n, label, sub) if label else fr
    return secs, gen


def sequence(paths, secs, hold_frac=0.6, label=None, sub=None, **g):
    """Stills that dissolve into each other through black sand (the cold open, the sand passes)."""
    imgs = [fit(load(p, **g)) for p in paths]
    def gen(n):
        per = n / len(imgs)
        def frames():
            for i in range(n):
                k = min(int(i / per), len(imgs) - 1)
                local = (i - k * per) / per
                z = 1.0 + 0.04 * (i / n)
                m = np.float32([[z, 0, W / 2 * (1 - z)], [0, z, H / 2 * (1 - z)]])
                cur = cv2.warpAffine(imgs[k], m, (W, H), borderMode=cv2.BORDER_REFLECT)
                if local > hold_frac and k + 1 < len(imgs):
                    nxt = cv2.warpAffine(imgs[k + 1], m, (W, H), borderMode=cv2.BORDER_REFLECT)
                    cur = t_sand(cur, nxt, (local - hold_frac) / (1 - hold_frac))
                yield cur
        return lower_third(frames(), n, label, sub) if label else frames()
    return secs, gen


def card(secs, lines, backdrop=None, dim=0.75, rise=True):
    """A title or text card: lines = [(text, font, px, (x, y), anchor, delay_frames)], revealed with a short rise."""
    base = np.full((H, W, 3), BG, np.uint8) if backdrop is None else (fit(load(backdrop, gain=0.9)) * (1 - dim)).astype(np.uint8)
    layers = [(text_layer([(t, k, px, xy, 1.0, anc)]), delay) for t, k, px, xy, anc, delay in lines]
    def gen(n):
        bg_frames = kenburns(base, n, 1.0, 1.04)
        for i, fr in enumerate(bg_frames):
            for layer, delay in layers:
                a = ease(min(1, max(0, (i - delay) / 16)))
                if a > 0:
                    fr = over(fr, layer, a, int((1 - a) * 18) if rise else 0)
            yield fr
    return secs, gen


def slide(secs, title, body, media=None, media_kind="image", **mkw):
    """Workflow slide: Cormorant title, Plex Sans body on the left, a still or footage panel on the right."""
    lines = [(title, "serif_r", 74, (130, 250), "ls", 4)]
    y = 340
    for i, ln in enumerate(wrap(body, "sans", 34, 700)):
        lines.append((ln, "sans", 34, (132, y), "ls", 16 + i * 5))
        y += 52
    _, text_gen = card(secs, lines)
    box = (820, 860)
    def gen(n):
        base = text_gen(n)
        if media is None:
            yield from base
            return
        if media_kind == "image":
            src = fit(load(media, **mkw), "contain", box)
            panel = (src for _ in range(n))
        elif media_kind == "video":
            panel = video(*media, n, mode="contain", box=box, **mkw)
        else:  # a callable that draws frame i
            panel = (media(i, n) for i in range(n))
        for i, (fr, pn) in enumerate(zip(base, panel)):
            a = ease(min(1, max(0, (i - 10) / 18)))
            x0, y0 = 1010, (H - box[1]) // 2 + int((1 - a) * 24)
            reg = fr[y0:y0 + box[1], x0:x0 + box[0]].astype(np.float32)
            fr = fr.copy()
            fr[y0:y0 + box[1], x0:x0 + box[0]] = (reg * (1 - a) + pn.astype(np.float32) * a).astype(np.uint8)
            yield fr
    return secs, gen


def lanes_panel(i, n):
    """The lane grid, revealing one lane every few frames."""
    names = ["UI", "Fonts", "Sand VFX", "Light shafts", "Mitered trims", "Fireplace", "Door and bedding",
             "Dream post-process", "Character", "Animations", "Carpet and props", "Wall art and decals",
             "Box-projected surfaces", "Graph tools plugin", "Sound"]
    im = Image.new("RGB", (820, 860), BG)
    d = ImageDraw.Draw(im)
    for k, name in enumerate(names):
        a = min(1, max(0, (i - 20 - k * 6) / 10))
        if a <= 0:
            continue
        col, row = k % 2, k // 2
        x, y = 30 + col * 400, 70 + row * 96
        d.rounded_rectangle((x, y, x + 370, y + 70), 10, fill=tuple(int(c * (0.10 + 0.08 * a)) for c in INK))
        d.text((x + 24, y + 35), name, font=font("sans_r", 28), fill=tuple(int(c * a) for c in INK), anchor="lm")
    return np.asarray(im)


def lock_panel(i, n):
    """One editor, one writer: lanes queue for the lock and enter one at a time."""
    names = ["Fireplace", "Light shafts", "UI", "Sand VFX", "Trims", "Sound"]
    im = Image.new("RGB", (820, 860), BG)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((420, 300, 790, 560), 16, outline=INK, width=3)
    d.text((605, 335), "Unreal Editor", font=font("sans_m", 30), fill=INK, anchor="mm")
    step = max(1, n // (len(names) + 1))
    k = min(i // step, len(names) - 1)
    d.rounded_rectangle((455, 400, 755, 470), 10, fill=(64, 58, 50))
    d.text((605, 435), names[k], font=font("sans_r", 28), fill=INK, anchor="mm")
    d.text((605, 515), "holds the lock", font=font("sans", 22), fill=(170, 160, 146), anchor="mm")
    for j, name in enumerate(names[k + 1:k + 6]):
        y = 300 + j * 86
        d.rounded_rectangle((30, y, 330, y + 66), 10, fill=(36, 33, 29))
        d.text((180, y + 33), name, font=font("sans", 26), fill=(200, 192, 178), anchor="mm")
    d.text((180, 255), "waiting", font=font("sans", 22), fill=(170, 160, 146), anchor="mm")
    return np.asarray(im)


def strip_panel(paths, labels):
    """Iteration strip: the same shot, round after round."""
    thumbs = [Image.fromarray(fit(load(p, gain=1.8), "cover", (500, 180))) for p in paths]
    def draw(i, n):
        im = Image.new("RGB", (820, 860), BG)
        d = ImageDraw.Draw(im)
        for k, (t, lab) in enumerate(zip(thumbs, labels)):
            a = min(1, max(0, (i - 15 - k * 14) / 12))
            if a <= 0:
                continue
            y = 40 + k * 205
            im.paste(Image.blend(Image.new("RGB", t.size, BG), t, a), (30, y))
            d.text((560, y + 90), lab, font=font("sans_r", 30), fill=tuple(int(c * a) for c in INK), anchor="lm")
        return np.asarray(im)
    return draw


# ---------- facts (counted, not invented) ----------

def day_facts():
    calls = sum(1 for ln in open(f"{S}/hayba-execution.log", encoding="utf-8", errors="replace") if ln.startswith("2026-"))
    crashes = 0
    for p in glob.glob(f"{S}/Logs/FoA*.log"):
        crashes += sum("LogWindows: Error: === Critical error: ===" in ln
                       for ln in open(p, encoding="utf-8-sig", errors="replace"))
    lux = json.load(open(f"{A}/lux3d/_state.json", encoding="utf-8"))
    return {"calls": calls, "crashes": crashes, "lux3d": sum(v.get("status") == "done" for v in lux.values())}


# ---------- the cut ----------

def build_segments(facts):
    st = f"{S}/Screenshots"
    d5 = f"{D}/2026-11-05/stills"
    shots = [f"{D}/videos/devlog01/work/itch/shot_{k}.jpg" for k in (1, 4, 5, 2, 3)]
    rec = lambda name: f"{REC}/editor_20261105_{name}.mp4"
    ed = dict(editor=True, crop=(4, 158, 1264, 830))      # the viewport, checked frame by frame
    panel = dict(editor=True, crop=(1380, 360, 520, 680))  # Hayba's tool-stream panel
    loop = f"{S}/Devlog/clock_loop.mp4"
    if os.path.exists(HERO_CLOCK):
        cold = clip(HERO_CLOCK, 0, 9.5, amount=1.0)
    elif os.path.exists(loop):  # the sand lane's clock: re-forms out of the pile (reversed), then dissolves again
        boom = f"{WORK}/clock_boomerang.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", loop, "-filter_complex", "[0]split[a][b];[a]reverse[r];"
                        "[r][b]concat=n=2:v=1", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", boom], check=True)
        cold = clip(boom, 0, 9.5, amount=1.0, gain=1.1)
    else:
        cold = sequence([f"{S}/SandClips/pass1/frame_00.png", f"{S}/SandClips/pass1/frame_02.png",
                         f"{S}/SandClips/pass1/frame_03.png", f"{S}/SandClips/pass2/frame_04.png"], 9, gain=2.3)
    segs = [
        Seg("cold_open", *cold, trans=("fade", 1), chapter="Cold open",
            vo="(Let the sand breathe. No narration for the first few seconds.)",
            sfx=[(0, "SFX/Sand/SFX_Sand_Trickle_Loop_01.wav", -16, 9.5), (0.2, "SFX/Dream/SFX_Dream_ReverseSwell_02.wav", -14, None),
                 (4.3, "SFX/Clock/SFX_Clock_Tick_Loop_01.wav", -20, 2.2), (4.9, "SFX/Sand/SFX_Sand_Burst_02.wav", -11, None),
                 (5.4, "SFX/Sand/SFX_Sand_PourHeavy_01.wav", -14, None)]),
        Seg("title", *card(6, [("The Nightmare", "serif", 168, (W // 2 - 40, 520), "ms", 6),
                               ("of Responsibility", "serif_i", 70, (W // 2 + 210, 600), "ms", 16),
                               ("Devlog #1", "sans", 32, (W // 2, 760), "ms", 30)]), trans=("sand", 30),
            sfx=[(0.6, "SFX/Dream/SFX_Dream_LowImpact_02.wav", -9, None)]),
        Seg("premise", *card(7, [("An ordinary morning.", "serif_r", 84, (150, 470), "ls", 6),
                                 ("Get dressed. Leave the house. Find a job.", "sans", 38, (154, 560), "ls", 22),
                                 ("Everything goes wrong in ways just plausible enough to accept.", "sans", 38,
                                  (154, 616), "ls", 34)], backdrop=f"{A}/storyboard/moods/C_photoreal.png", dim=0.8),
            trans=("sand", 22), chapter="The idea",
            vo="This is The Nightmare of Responsibility. It's about an ordinary morning: get dressed, leave the house, "
               "find a job. And everything goes wrong, in ways that are just plausible enough to accept."),
        Seg("story_f01", *still(f"{A}/storyboard/frames/F01.png", 4, "Concept art", "Storyboard, the phone menu"),
            trans=("smear", 16), vo="I boarded it first. The main menu is a phone: a calendar of failed days and "
                                    "four unticked tasks."),
        Seg("story_f03", *still(f"{A}/storyboard/frames/F03.png", 3.5, "Concept art", "The locked door", z=(1.06, 1.0)),
            trans=("smear", 16)),
        Seg("story_f06", *still(f"{A}/storyboard/frames/F06.png", 3.5, "Concept art", "The wardrobe falls"), trans=("smear", 16)),
        Seg("story_f08", *still(f"{A}/storyboard/frames/F08.png", 4, "Concept art", "An inside-out shirt, fought like a boss",
                                top=True),
            trans=("smear", 16), vo="Even getting dressed is a fight."),
        Seg("ai_header", *card(5, [("How I make games with AI", "serif", 112, (W // 2, 540), "ms", 6),
                                   ("The workflow behind this devlog", "sans", 32, (W // 2, 620), "ms", 22)]),
            trans=("sand", 24), chapter="How I make games with AI",
            sfx=[(0.3, "SFX/Dream/SFX_Dream_LowImpact_01.wav", -11, None)],
            vo="So how is a game like this made by basically one person? Here's my workflow."),
        Seg("ai_lanes", *slide(10, "Many agents, one director",
                               "Claude Code runs many agent lanes in parallel. Each lane owns one job, from the UI to the "
                               "sand effects to the sound.", lanes_panel, "draw"), trans=("smear", 18),
            vo="I use Claude Code to run many agent lanes at the same time. Each lane owns one job: the UI, the fonts, "
               "the sand, the light shafts, the trims, the sound."),
        Seg("ai_editor", *clip(rec("164415"), 366, 5, "Hayba", "Agents working in the live editor", speed=2, amount=0.55,
                               editor=True, crop=(0, 32, 1920, 1016)), trans=("glitch", 8)),
        Seg("ai_hayba", *slide(10, "Hayba drives the editor",
                               f"Hayba is my own MCP toolkit for Unreal. The agents edit the open editor through it, and "
                               f"every tool call shows up live. Day one logged more than {facts['calls'] // 100 * 100:,} calls.",
                               (rec("174420"), 94), "video", speed=3, amount=0.4, **panel), trans=("smear", 18),
            vo="They all work inside the live Unreal editor through Hayba, which is my own MCP toolkit. Every single "
               "tool call shows up in this stream, so I can watch exactly what each agent is doing."),
        Seg("ai_lux3d", *slide(9, "Lux3D makes the assets",
                               f"Aholo's Lux3D turns a prompt into a textured mesh or a Gaussian splat. "
                               f"{facts['lux3d']} generations so far, from the bedding to the sand clock.",
                               f"{S}/SandClips/pass2/frame_04.png", "image", gain=2.2), trans=("smear", 18),
            vo="The 3D assets come from Aholo's Lux3D. It turns a prompt into a textured mesh or a Gaussian splat. "
               "That alarm clock you saw at the start is a splat."),
        Seg("ai_lock", *slide(9, "One writer at a time",
                              "All the agents share one open editor. They queue for a single editor lock and follow "
                              "shared lane rules, so only one of them changes it at a time.", lock_panel, "draw"),
            trans=("smear", 18),
            vo="With that many agents in one editor, they have to take turns. There's a single editor lock and a set of "
               "lane rules everyone follows."),
        Seg("ai_review", *slide(10, "I direct and review every step",
                                "I set the direction, look at every result, and approve it or send it back. Most shots "
                                "went through several rounds.",
                                strip_panel([f"{st}/Dressing/Shot_Wide_v1.png", f"{st}/Dressing/Shot_Wide_v3.png",
                                             f"{st}/Dressing/Shot_Wide_final.png"],
                                            ["Round 1", "Round 3", "Final"]), "draw"),
            trans=("smear", 18),
            vo="And I'm the director. I set the look, I review every result, and I approve it or send it back. Most of "
               "what you'll see went through a few rounds like this."),
        Seg("prev_header", *card(5, [("Before this", "sans", 34, (W // 2, 470), "ms", 4),
                                     ("A Gift for the Unfinished Journey", "serif", 96, (W // 2, 580), "ms", 14)]),
            trans=("sand", 24), chapter="My previous game",
            sfx=[(0.3, "SFX/Dream/SFX_Dream_LowImpact_03.wav", -12, None)],
            vo="Before this, I made A Gift for the Unfinished Journey."),
        *[Seg(f"prev_{k}", *still(p, 3.2, "A Gift for the Unfinished Journey" if k == 0 else None, amount=0.45,
                                  z=(1.0, 1.06) if k % 2 else (1.06, 1.0)), trans=("smear", 14),
              vo="(Optional: a line on what you learned from it.)" if k == 0 else None) for k, p in enumerate(shots)],
        Seg("prev_key", *still(f"{D}/videos/devlog01/work/itch/shot_7.jpg", 4.5, amount=0.45), trans=("smear", 14)),
        Seg("build_header", *card(5, [("The build so far", "serif", 112, (W // 2, 540), "ms", 6),
                                      ("Day one, in the editor", "sans", 32, (W // 2, 620), "ms", 20)]),
            trans=("sand", 24), chapter="The build so far",
            sfx=[(0.3, "SFX/Dream/SFX_Dream_LowImpact_04.wav", -11, None)],
            vo="So here's what day one looked like."),
        Seg("room_top", *still(f"{d5}/1553_editor_FoA-Shot-TopDown.png", 3.5, "The bedroom", "First pass, from above", gain=1.1),
            trans=("sand", 20), vo="It started as an empty room."),
        Seg("room_v1", *still(f"{st}/Dressing/Shot_Wide_v1.png", 3.5, "Dressing, round one", gain=1.0), trans=("smear", 16)),
        Seg("room_live", *clip(rec("171420"), 1150, 5, "Dressing the walls", "Live in the editor", speed=4, amount=0.6, **ed),
            trans=("glitch", 8)),
        Seg("room_raw", *still(f"{S}/LookDev/raw_Shot_Wide.png", 3.5, "Textured, before the post-process", amount=0.5),
            trans=("smear", 16), vo="Real furniture, real textures, trims, a door, a fireplace."),
        Seg("room_fire", *clip(rec("171420"), 1626, 5, "Dressing the room", "Live in the editor", speed=3, amount=0.8, **ed),
            trans=("smear", 16)),
        Seg("shaft_before", *still(f"{S}/ShaftShots/light_before_window.png", 3.2, "Light shafts", "Before", gain=1.2),
            trans=("sand", 20), vo="Then the moonlight. Before, and after."),
        Seg("shaft_after", *still(f"{S}/ShaftShots/light_final_window.png", 3.8, "Light shafts", "After", gain=1.2),
            trans=("smear", 20)),
        Seg("shaft_motion", *clip(f"{S}/ShaftShots/shafts_motion.mp4", 0, 3.2, speed=0.95), trans=("smear", 14)),
        Seg("look_raw", *still(f"{S}/LookDev/raw_Shot_Wide.png", 2.6, "Look-dev", "No post-process", amount=0.2),
            trans=("sand", 20), chapter="Look-dev",
            vo="The look is where it becomes a nightmare. I tried four looks on the same room."),
        *[Seg(f"look_{k}", *still(f"{S}/LookDev/{k}_Shot_Wide.png", 2.4, "Look-dev", f"Look {k}", amount=0.0),
              trans=("glitch", 7)) for k in "ABCD"],
        Seg("look_loop", *clip(f"{S}/LookDev/anim/D.mp4", 0, 4.2, amount=0.0), trans=("glitch", 7)),
        Seg("sand_p1", *sequence([f"{S}/SandClips/pass1/frame_0{k}.png" for k in (0, 1, 2, 3)], 4.5,
                                 label="Black sand", sub="Pass one", gain=3.2), trans=("sand", 20), chapter="Sand and the character",
            vo="No particle systems for the hero effects. The sand is Gaussian splats, rendered as meshes. Pass one, "
               "then pass two.",
            sfx=[(0.5, "SFX/Sand/SFX_Sand_Pour_02.wav", -14, None)]),
        Seg("sand_p2", *sequence([f"{S}/SandClips/pass2/frame_0{k}.png" for k in (0, 2, 4)], 4.5,
                                 label="Black sand", sub="Pass two", gain=3.2), trans=("sand", 18),
            sfx=[(0.5, "SFX/Sand/SFX_Sand_Pour_03.wav", -14, None)]),
        *([Seg("sand_p3", *clip(f"{S}/Devlog/clock_loop.mp4", 0, 4.6, "Black sand", "The clock comes apart", gain=1.1),
               trans=("smear", 16), sfx=[(1.2, "SFX/Sand/SFX_Sand_PourHeavy_01.wav", -15, None)])]
          if os.path.exists(f"{S}/Devlog/clock_loop.mp4") else []),
        Seg("char_grid", *clip(f"{A}/character/v3/turntables/turntable_grid.mp4", 0, 6, "The Nightmare",
                               "Character variants", mode="contain", amount=0.6), trans=("sand", 20),
            vo="This is the Nightmare, the character you play. Four variants, side by side."),
        Seg("char_b", *clip(f"{A}/character/v3/turntables/turntable_B.mp4", 0, 5, mode="contain", amount=0.6),
            trans=("smear", 16)),
        Seg("char_hands", *still(f"{A}/character/v3/hands_sheet.png", 3.5, "Hand rig check", mode="contain"),
            trans=("smear", 16), vo="Checking the hands before rigging."),
        Seg("ui_type", *still(f"{S}/UIShots/WBP_MainMenu_v6.png", 3.5, "Main menu",
                              "Cormorant Garamond and IBM Plex", mode="contain"), trans=("sand", 20), chapter="UI, trims and graphs",
            vo="The type is Cormorant Garamond with IBM Plex."),
        Seg("ui_title", *still(f"{S}/UIShots/Title_option_B_r3.png", 3.5, "Title screen", mode="contain"), trans=("smear", 16)),
        Seg("ui_splash", *still(f"{S}/UIShots/Splash_HaybaCard.png", 3, "Boot splash", mode="contain"), trans=("smear", 16)),
        Seg("trim_base", *still(f"{S}/TrimShots/base_chimney_outside.png", 3.2, "Mitered trims", gain=0.8),
            trans=("sand", 20), vo="Mitered trims, so every corner actually meets."),
        Seg("trim_crown", *still(f"{S}/TrimShots/crown_chimney_outside.png", 3.2, gain=0.8), trans=("smear", 16)),
        Seg("graph_full", *still(f"{D}/showcase/graphs/M_PaintedWoodTrim/graph_20261105-1718.png", 3.6,
                                 "Material graphs", "Every group commented", mode="contain", amount=0.35),
            trans=("sand", 20),
            vo="And the graphs stay clean: grouped, commented, readable. Like a real team built them."),
        Seg("graph_crop", *still(f"{D}/showcase/crops/M_PaintedWoodTrim/graph_20261105-1718_g1.png", 3.6,
                                 mode="contain", amount=0.35), trans=("smear", 16)),
        Seg("lessons", *card(9, [("Lessons from day one", "serif", 96, (150, 420), "ls", 6),
                                 (f"Many agents writing to one editor crashed it {facts['crashes']} times.", "sans", 38,
                                  (154, 520), "ls", 24),
                                 ("The fix: one writer at a time, through a shared editor lock,", "sans", 38, (154, 590),
                                  "ls", 48),
                                 ("plus crash guards in Hayba.", "sans", 38, (154, 642), "ls", 52)]),
            trans=("sand", 24), chapter="Lessons and next time",
            vo=f"It wasn't smooth. With this many agents writing to one editor, it crashed {facts['crashes']} times "
               "on day one. The fix was simple: one writer at a time, through a shared lock, plus crash guards in Hayba."),
        Seg("next", *card(7, [("Next time", "serif", 96, (150, 450), "ls", 6),
                              ("A clothing RPG boss fight, a MetaHuman protagonist,", "sans", 38, (154, 550), "ls", 22),
                              ("and the intro cinematic.", "sans", 38, (154, 602), "ls", 28)],
                          backdrop=f"{A}/storyboard/frames/F08.png", dim=0.78), trans=("sand", 24),
            vo="Next time: the clothing boss fight, a MetaHuman protagonist, and the intro cinematic."),
        Seg("end", *card(10, [("The Nightmare", "serif", 120, (W // 2 - 30, 430), "ms", 4),
                              ("of Responsibility", "serif_i", 52, (W // 2 + 150, 490), "ms", 12),
                              ("Thanks for watching.", "sans", 36, (W // 2, 640), "ms", 26),
                              ("Subscribe for Devlog #2. Links are in the description.", "sans", 30, (W // 2, 700), "ms", 36),
                              ("zajalist.itch.io", "sans_m", 30, (W // 2, 760), "ms", 44)]), trans=("sand", 30),
            chapter="Thanks", vo="Thanks for watching. Subscribe if you want to see where this goes."),
    ]
    return segs


# ---------- render ----------

ENC_PIECE = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", "-g", "30", "-r", str(FPS)]


def open_piece(path):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", *ENC_PIECE, path], stdin=subprocess.PIPE)


def render(segs):
    os.makedirs(MEDIA, exist_ok=True)
    pieces, tail, gi, starts, marks = [], None, 0, [], []
    for i, seg in enumerate(segs):
        lin = seg.trans[1] if i else 0
        lout = segs[i + 1].trans[1] if i + 1 < len(segs) else 0
        assert seg.n > lin + lout, seg.name
        frames = iter(seg.gen(seg.n))
        start = sum(p[2] for p in pieces)
        starts.append(start)
        if lin:
            path = f"{MEDIA}/{len(pieces):03d}_trans_{seg.trans[0]}.mp4"
            w = open_piece(path)
            for k in range(lin):
                fr = TRANS[seg.trans[0]](tail[k], next(frames), (k + 1) / (lin + 1))
                w.stdin.write(finish(fr, gi).tobytes())
                gi += 1
            w.stdin.close(); w.wait()
            pieces.append((f"trans_{seg.trans[0]}", path, lin))
            marks.append((start, seg.trans[0]))
        path = f"{MEDIA}/{len(pieces):03d}_{seg.name}.mp4"
        w = open_piece(path)
        body = seg.n - lin - lout
        mid = None
        for k in range(body):
            fr = next(frames)
            if k == body // 2:
                mid = fr
            w.stdin.write(finish(fr, gi).tobytes())
            gi += 1
        w.stdin.close(); w.wait()
        pieces.append((seg.name, path, body))
        Image.fromarray(mid).resize((480, 270)).save(f"{WORK}/key_{i:02d}_{seg.name}.jpg", quality=88)
        tail = [next(frames) for _ in range(lout)]
        print(f"  {i + 1}/{len(segs)} {seg.name} ({seg.n} frames)", flush=True)
    return pieces, starts, marks


# ---------- audio ----------

SR = 48000


def load_wav(rel):
    sr, x = wavfile.read(f"{A}/audio/{rel}")
    x = x.astype(np.float32) / (32768.0 if x.dtype == np.int16 else (2 ** 31 if x.dtype == np.int32 else 1.0))
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    if sr != SR:
        g = math.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g, axis=0).astype(np.float32)
    return x


def mix_audio(segs, starts, marks, total_frames):
    n = int(total_frames / FPS * SR) + SR
    mixbuf = np.zeros((n, 2), np.float32)
    def place(rel, t, db, dur=None, fade=0.25):
        x = load_wav(rel)
        if dur:
            reps = int(math.ceil(dur * SR / len(x)))
            x = np.tile(x, (reps, 1))[:int(dur * SR)]
        f = min(len(x) // 2, int(fade * SR))
        if f:
            ramp = np.linspace(0, 1, f, dtype=np.float32)[:, None]
            x[:f] *= ramp
            x[-f:] *= ramp[::-1]
        s = int(t * SR)
        e = min(n, s + len(x))
        mixbuf[s:e] += x[:e - s] * (10 ** (db / 20))
    place("SFX/Ambience/SFX_Ambience_RoomTone_Loop_01.wav", 0, -24, total_frames / FPS, fade=2.5)
    rng = np.random.default_rng(11)
    for start, kind in marks:
        for rel, db in TRANS_SFX[kind]:
            if kind == "fade":
                continue
            place(rel.format(rng.integers(1, 5)), max(0, start / FPS - 0.15), db)
    for seg, st in zip(segs, starts):
        for t, rel, db, dur in seg.sfx:
            place(rel, st / FPS + t, db, dur, fade=0.6 if dur else 0.02)
    out_raw = f"{WORK}/mix_raw.wav"
    wavfile.write(out_raw, SR, np.clip(mixbuf, -1, 1))
    return out_raw


def measure(path):
    """Integrated loudness (LUFS) and true peak (dBTP) via ffmpeg's EBU R128 meter."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    tail = r[r.rindex("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))


def loudnorm(src, dst, target, codec_args):
    """Gain to the target, peaks held by a limiter, one corrective pass. ffmpeg's loudnorm undershoots on a sparse
    SFX bed (its gain is capped by the few loud whooshes), so this measures and limits explicitly."""
    gain, limit = 0.0, 0.80  # limiter ceiling as linear sample peak (about -1.9 dBFS); true peak lands near -1 dBTP
    for _ in range(6):
        i_now = (measure(src) if gain == 0 else measure(dst))[0]
        gain += target - i_now
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                        f"acompressor=threshold=-30dB:ratio=3:attack=6:release=180:makeup=1,volume={gain:.2f}dB,"
                        f"alimiter=limit={limit}:attack=4:release=80:level=false", "-ar", str(SR),
                        *codec_args, dst], check=True)
        i_out, tp = measure(dst)
        if tp > -1.0:
            limit *= 0.93
        if abs(i_out - target) < 0.3 and tp <= -1.0:
            break
    print(f"  {os.path.basename(dst)}: {i_out:.1f} LUFS, {tp:.1f} dBTP")


# ---------- deliverables ----------

def tc(frames):
    s = frames / FPS
    return f"{int(s // 60)}:{int(s % 60):02d}"


def write_vo(segs, starts, total):
    lines = ["FoA Devlog #1: voice-over beats", f"Total length {tc(total)} at {FPS} fps. Timecodes are where each beat "
             "starts; leave the first few seconds of the cold open silent.", ""]
    for seg, st in zip(segs, starts):
        if seg.chapter:
            lines.append(f"\n== {tc(st)}  {seg.chapter} ==")
        if seg.vo:
            lines.append(f"{tc(st)}  {seg.vo}")
    ch = [st for seg, st in zip(segs, starts) if seg.chapter] + [total]
    short = [(segs[[s.chapter for s in segs].index(c)].chapter, (b - a) / FPS) for c, a, b in
             zip([s.chapter for s in segs if s.chapter], ch, ch[1:]) if (b - a) / FPS < 10]
    if short:
        print(f"WARNING: YouTube ignores chapters when one is under 10 s: {short}")
    lines += ["", "YouTube chapters (paste into the description):"]
    lines += [f"{tc(st) if k else '0:00'} {seg.chapter}" for k, (seg, st) in
              enumerate((s, t) for s, t in zip(segs, starts) if s.chapter)]
    open(f"{OUT}/devlog01_vo_beats.txt", "w", encoding="utf-8").write("\n".join(lines) + "\n")


def write_fcpxml(pieces, total):
    res = ['<format id="r1" name="FFVideoFormat1080p30" frameDuration="1/30s" width="1920" height="1080"/>']
    spine, off = [], 0
    for k, (name, path, nfr) in enumerate(pieces):
        res.append(f'<asset id="a{k}" name="{os.path.basename(path)[:-4]}" src="file:///{path}" start="0s" '
                   f'duration="{nfr}/30s" hasVideo="1" format="r1"/>')
        audio = (f'<asset-clip ref="sfx" lane="-1" offset="0s" name="devlog01_sfx" duration="{total}/30s" '
                 f'audioRole="effects"/>') if k == 0 else ""
        spine.append(f'<asset-clip ref="a{k}" offset="{off}/30s" name="{os.path.basename(path)[:-4]}" '
                     f'duration="{nfr}/30s" start="0s" format="r1">{audio}</asset-clip>')
        off += nfr
    res.append(f'<asset id="sfx" name="devlog01_sfx" src="file:///{OUT}/devlog01_sfx.wav" start="0s" '
               f'duration="{total}/30s" hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000"/>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.8">\n<resources>\n'
           + "\n".join(res) + '\n</resources>\n<library>\n<event name="FoA Devlog 1">\n<project name="devlog01">\n'
           f'<sequence format="r1" duration="{total}/30s" tcStart="0s" tcFormat="NDF" audioLayout="stereo" '
           f'audioRate="48k">\n<spine>\n' + "\n".join(spine) + "\n</spine>\n</sequence>\n</project>\n</event>\n"
           "</library>\n</fcpxml>\n")
    open(f"{OUT}/devlog01.fcpxml", "w", encoding="utf-8").write(xml)


def contact_sheet(segs, starts):
    keys = sorted(glob.glob(f"{WORK}/key_*.jpg"))
    cols = 6
    rows = math.ceil(len(keys) / cols)
    sheet = Image.new("RGB", (480 * cols, 300 * rows), BG)
    d = ImageDraw.Draw(sheet)
    for k, p in enumerate(keys):
        x, y = (k % cols) * 480, (k // cols) * 300
        sheet.paste(Image.open(p), (x, y))
        i = int(os.path.basename(p)[4:6])
        d.text((x + 8, y + 276), f"{tc(starts[i])}  {segs[i].name}", font=font("sans_r", 18), fill=INK)
    sheet.save(f"{OUT}/contact_sheet.png")


def thumbnail():
    tw, th = 1280, 720
    clock = load(f"{S}/SandClips/pass2/frame_04.png", gain=2.6)
    z = th * 1.15 / clock.shape[0]
    m = np.float32([[z, 0, 970 - z * clock.shape[1] * 0.5], [0, z, th * 0.5 - z * clock.shape[0] * 0.55]])
    bg = cv2.warpAffine(clock, m, (tw, th), flags=cv2.INTER_CUBIC, borderValue=BG).astype(np.float32)
    ramp = np.clip(1 - np.arange(tw, dtype=np.float32) / (tw * 0.62), 0, 1)[None, :, None] * 0.9  # dark behind the text
    im = Image.fromarray((bg * (1 - ramp) + np.float32(BG) * ramp).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((70, 300), "The Nightmare", font=font("serif", 112), fill=INK, anchor="ls")
    d.text((250, 366), "of Responsibility", font=font("serif_i", 50), fill=INK, anchor="ls")
    d.text((72, 520), "Devlog #1", font=font("sans_sb", 92), fill=INK, anchor="ls")
    arr = np.asarray(im).astype(np.float32)
    vy, vx = np.mgrid[0:th, 0:tw].astype(np.float32)
    vig = (1 - 0.3 * (((vx - tw / 2) / (tw / 2)) ** 2 + ((vy - th / 2) / (th / 2)) ** 2)).clip(0.5, 1)[..., None]
    arr = np.clip(arr * vig + np.random.default_rng(5).normal(0, 3, (th, tw, 1)), 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(f"{OUT}/thumbnail.png")


def main():
    os.makedirs(WORK, exist_ok=True)
    facts = day_facts()
    print("facts", facts)
    thumbnail()
    segs = build_segments(facts)
    if "--preview" in sys.argv:
        return
    for p in glob.glob(f"{MEDIA}/*.mp4") + glob.glob(f"{WORK}/key_*.jpg"):
        os.remove(p)  # our own render output from a previous run
    pieces, starts, marks = render(segs)
    total = sum(p[2] for p in pieces)
    with open(f"{WORK}/concat.txt", "w", encoding="utf-8") as fh:
        fh.writelines(f"file '{p}'\n" for _, p, _ in pieces)
    raw = mix_audio(segs, starts, marks, total)
    loudnorm(raw, f"{OUT}/devlog01_sfx.wav", -20, ["-c:a", "pcm_s24le"])
    loudnorm(raw, f"{WORK}/mix_m14.wav", -14, ["-c:a", "pcm_s24le"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/concat.txt",
                    "-i", f"{WORK}/mix_m14.wav", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                    "-profile:v", "high", "-b:v", "18M", "-maxrate", "20M", "-bufsize", "40M", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-b:a", "320k", "-ar", str(SR), "-shortest", "-movflags", "+faststart",
                    f"{OUT}/devlog01_noVO.mp4"], check=True)
    write_vo(segs, starts, total)
    write_fcpxml(pieces, total)
    contact_sheet(segs, starts)
    print(f"done: {tc(total)} ({total} frames), {len(pieces)} pieces")


if __name__ == "__main__":
    main()
