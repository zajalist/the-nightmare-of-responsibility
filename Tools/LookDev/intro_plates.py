"""Intro v3 plates (story lane, offline). Packs each panel into one RGBA texture for M_IntroPlate (hlsl/intro_plate.hlsl):
R = graded luminance, G = nearness (0 far, 1 near) from the real depth pass, B = luminance with the panel's light on,
A = figure matte. Sources: Tools/LookDev/capture_intro_v3.py passes in Saved/StoryShots/intro/src, plus the wake-up's own
PIE frame for the room (aligned to the capture by a SIFT homography, so the depth matches).
  python Tools/LookDev/intro_plates.py          -> Saved/StoryShots/intro/plates/T_IntroPlate_<Panel>.png + preview sheet
The panel list, lines and seconds here are what WBP_IntroStory gets (intro_widget_v3.py reads PANELS)."""
import os
import sys

os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
import cv2  # noqa: E402
import numpy as np  # noqa: E402

SRC = 'P:/FoA/Saved/StoryShots/intro/src'
OUT = 'P:/FoA/Saved/StoryShots/intro/plates'
FONT = 'P:/FoA-Assets/fonts/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf'
W, H = 2048, 1152
# name, line, seconds, grade (black point, white point, gamma), crop (centre x, centre y, zoom)
PANELS = [
    ('Room', "Seventeen days. Not that anyone's counting.", 5.0, (0.04, 0.80, 1.15), (0.5, 0.5, 1.0)),
    ('Phone', 'Mom made me a list.', 4.5, (0.03, 0.75, 1.25), (0.52, 0.52, 1.2)),
    ('Shirt', "It's a shirt. It's just a shirt.", 4.5, (0.05, 0.90, 1.2), (0.5, 0.5, 1.0)),
    ('Watcher', 'It never does anything. It just waits for me to give up.', 5.5, (0.05, 0.95, 1.3), (0.55, 0.5, 1.05)),
    ('Lunge', '', 1.6, (0.0, 0.55, 0.9), (0.55, 0.45, 1.0)),
]
TASKS = ['Wake up', 'Get dressed', 'Leave the house', 'Find a job']


def luma(bgr):
    return (bgr[..., :3].astype(np.float32) / 255.0) @ np.array([0.0722, 0.7152, 0.2126], np.float32)


def grade(y, g):
    lo, hi, gamma = g
    return np.clip((y - lo) / (hi - lo), 0, 1) ** gamma


def nearness(depth):
    d = np.log(np.clip(depth, 10, 1e5))
    lo, hi = np.percentile(d, 1), np.percentile(d, 99)
    n = np.clip((hi - d) / max(hi - lo, 1e-3), 0, 1)
    n = cv2.dilate(n, np.ones((9, 9), np.uint8))           # near edges win, so silhouettes never tear
    return cv2.GaussianBlur(n, (0, 0), 3)


def matte(name, shape):
    p = f'{SRC}/{name}_matte.exr'
    if not os.path.exists(p):
        return np.zeros(shape, np.float32)
    m = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    a = 1.0 - np.clip(m[..., 3], 0, 1)                      # SceneColor alpha is inverse coverage
    return cv2.GaussianBlur(cv2.resize(a, shape[::-1]), (0, 0), 1.2)


def room_color(shape):
    """The wake-up's PIE frame (the real teen asleep), warped onto the editor capture so its depth lines up."""
    pie = cv2.imread('P:/FoA/Saved/LookDev/intro_ingame/Game01_Sleep.png')
    cap = cv2.resize(cv2.imread(f'{SRC}/Room_color_ev-8.png'), (pie.shape[1], pie.shape[0]))
    clahe = cv2.createCLAHE(3.0, (8, 8))
    a, b = clahe.apply(cv2.cvtColor(pie, cv2.COLOR_BGR2GRAY)), clahe.apply(cv2.cvtColor(cap, cv2.COLOR_BGR2GRAY))
    sift = cv2.SIFT_create(8000)
    ka, da = sift.detectAndCompute(a, None)
    kb, db = sift.detectAndCompute(b, None)
    good = [x for x, y in cv2.BFMatcher().knnMatch(da, db, k=2) if x.distance < 0.75 * y.distance]
    hmat, inl = cv2.findHomography(np.float32([ka[g.queryIdx].pt for g in good]),
                                   np.float32([kb[g.trainIdx].pt for g in good]), cv2.RANSAC, 4.0)
    assert inl.sum() > 60, 'room alignment failed'
    return cv2.resize(cv2.warpPerspective(pie, hmat, (pie.shape[1], pie.shape[0])), shape[::-1], interpolation=cv2.INTER_CUBIC)


def phone_screen(y, a):
    """The phone wakes. Draws the device over its matte: a black body with a metal rim, a rounded lit screen (status bar,
    camera dot, home bar, the list), and the screen's glow on the nightstand. Returns (dark, lit) luminance."""
    from PIL import Image, ImageDraw, ImageFont
    cnt = max(cv2.findContours((a > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0], key=cv2.contourArea)
    hull = cv2.convexHull(cnt)
    quad = cv2.approxPolyDP(hull, 0.04 * cv2.arcLength(hull, True), True).reshape(-1, 2).astype(np.float32)
    if len(quad) != 4:
        quad = cv2.boxPoints(cv2.minAreaRect(cnt)).astype(np.float32)
    c = quad.mean(0)
    quad = c + (quad - c) * 0.97                             # the device face, just inside the matte
    q = quad[np.argsort(np.arctan2(quad[:, 1] - c[1], quad[:, 0] - c[0]))]
    edges = [(q[i], q[(i + 1) % 4]) for i in range(4)]
    longest = max(range(4), key=lambda i: np.linalg.norm(edges[i][1] - edges[i][0]) + np.linalg.norm(edges[(i + 2) % 4][1] - edges[(i + 2) % 4][0]))
    e1, e2 = edges[longest], edges[(longest + 2) % 4]        # landscape: the text runs along the long sides
    top, bottom = (e1, e2) if (e1[0][1] + e1[1][1]) < (e2[0][1] + e2[1][1]) else (e2, e1)
    tl, tr = sorted(top, key=lambda v: v[0])
    bl, br = sorted(bottom, key=lambda v: v[0])
    cw, ch, bez = 1200, 560, 46
    def face(lit_on):
        img = Image.new('L', (cw, ch), 0)
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle((0, 0, cw - 1, ch - 1), 78, fill=7, outline=70 if lit_on else 34, width=5)   # body and rim
        sx0, sy0, sx1, sy1 = bez, bez - 8, cw - bez, ch - bez + 8
        if lit_on:
            grad = Image.linear_gradient('L').resize((sx1 - sx0, sy1 - sy0)).point(lambda v: int(206 - v * 0.16))
            m = Image.new('L', grad.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, grad.size[0] - 1, grad.size[1] - 1), 40, fill=255)
            img.paste(grad, (sx0, sy0), m)
            small, mid, big = (ImageFont.truetype(FONT, s) for s in (34, 54, 84))
            dr.text((sx0 + 44, sy0 + 18), '6:42', fill=50, font=small)
            dr.rounded_rectangle((sx1 - 98, sy0 + 28, sx1 - 50, sy0 + 50), 5, outline=60, width=3)
            dr.rectangle((sx1 - 95, sy0 + 31, sx1 - 80, sy0 + 47), fill=60)
            dr.text((sx0 + 44, sy0 + 78), 'Today', fill=34, font=big)
            for k, t in enumerate(TASKS):
                x, yy = sx0 + 44 + (k % 2) * 520, sy0 + 210 + (k // 2) * 110
                dr.rounded_rectangle((x, yy + 12, x + 44, yy + 56), 9, outline=58, width=5)
                dr.text((x + 72, yy), t, fill=36, font=mid)
            dr.rounded_rectangle((cw / 2 - 110, sy1 - 30, cw / 2 + 110, sy1 - 20), 5, fill=90)            # home bar
        dr.ellipse((14, ch / 2 - 9, 32, ch / 2 + 9), fill=2, outline=40 if lit_on else 20, width=2)  # camera
        return np.asarray(img, np.float32) / 255.0
    hm = cv2.getPerspectiveTransform(np.float32([[0, 0], [cw, 0], [cw, ch], [0, ch]]), np.float32([tl, tr, br, bl]))
    alpha = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(alpha).rounded_rectangle((0, 0, cw - 1, ch - 1), 78, fill=255)
    mask = cv2.GaussianBlur(cv2.warpPerspective(np.asarray(alpha, np.float32) / 255.0, hm, y.shape[::-1]), (0, 0), 0.8)
    screen = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(screen).rounded_rectangle((bez, bez - 8, cw - bez, ch - bez + 8), 40, fill=255)
    smask = cv2.warpPerspective(np.asarray(screen, np.float32) / 255.0, hm, y.shape[::-1])
    glow = cv2.GaussianBlur(smask, (0, 0), 0.5 * np.sqrt(smask.sum() + 1)) * 3.2
    dark = y * (1 - mask) + cv2.warpPerspective(face(False), hm, y.shape[::-1], flags=cv2.INTER_AREA) * mask
    lit = np.clip(y * (1 + 1.6 * glow) + 0.06 * glow, 0, 1)
    lit = lit * (1 - mask) + cv2.warpPerspective(face(True), hm, y.shape[::-1], flags=cv2.INTER_AREA) * mask
    return dark, lit


def sandy_edges(y, a, seed=11):
    """Black sand at the figure's edge: grains bitten out of the outline, clumps clinging just outside it."""
    rng = np.random.default_rng(seed)
    hard = (a > 0.5).astype(np.uint8)
    band_out = cv2.dilate(hard, np.ones((25, 25), np.uint8)) - hard
    band_in = hard - cv2.erode(hard, np.ones((13, 13), np.uint8))
    n = cv2.GaussianBlur(rng.random(y.shape).astype(np.float32), (0, 0), 2.4)
    n = (n - n.min()) / (n.max() - n.min() + 1e-6)
    cling = (band_out > 0) & (n > 0.6)
    bite = (band_in > 0) & (n < 0.32)
    out = y.copy()
    out[cling] = out[cling] * 0.12
    shade = cv2.GaussianBlur(y, (0, 0), 6)
    out[bite] = shade[bite] * 0.8
    a2 = a.copy()
    a2[cling] = 1.0
    a2[bite] = 0.0
    return out, a2


def build(name, line, secs, g, crop):
    depth = cv2.imread(f'{SRC}/{name}_depth.exr', cv2.IMREAD_UNCHANGED)[..., 2]
    shape = depth.shape
    a = matte(name, shape)
    color = room_color(shape) if name == 'Room' else cv2.imread(f'{SRC}/{name}_color.png')
    lit_src = f'{SRC}/{name}_lit.png'  # the shirt's pass with its soft front fill: pale, collar and buttons readable
    if name == 'Shirt' and os.path.exists(lit_src):  # the lit shirt through its matte, over the moonlit room
        a3 = cv2.resize(a, (color.shape[1], color.shape[0]))[..., None]
        color = (color * (1 - a3) + cv2.imread(lit_src) * a3).astype(np.uint8)
    y = grade(luma(color), g)
    if name in ('Watcher', 'Lunge'):                         # the figure is black sand: a rim, and a grainy outline
        y = y * (1 - a) + a * (y * 0.10 + np.clip(y - 0.6, 0, 1) * 0.7)
        y, a = sandy_edges(y, a)
    if name == 'Shirt':                                      # the good shirt is pale in the moonlight
        y = y * (1 - a) + a * np.clip(y, 0, 1) ** 0.6
    if name == 'Phone':
        y, lit = phone_screen(y * 0.85, a)
    else:
        lit = y.copy()
    n = nearness(depth)
    cx, cy, z = crop
    hh, ww = shape
    w2, h2 = ww / z, hh / z
    x0 = int(np.clip(cx * ww - w2 / 2, 0, ww - w2))
    y0 = int(np.clip(cy * hh - h2 / 2, 0, hh - h2))
    chans = [cv2.resize(ch[y0:y0 + int(h2), x0:x0 + int(w2)], (W, H), interpolation=cv2.INTER_AREA) for ch in (y, n, lit, a)]
    rgba = np.dstack(chans)
    os.makedirs(OUT, exist_ok=True)
    out = f'{OUT}/T_IntroPlate_{name}.png'
    cv2.imwrite(out, (np.clip(rgba[..., [2, 1, 0, 3]], 0, 1) * 255 + 0.5).astype(np.uint8))  # PNG is BGRA
    return rgba


def preview(rgba, idx, t, secs):
    """A rough Python port of the shader's grade and light, for the contact sheet (motion is judged in engine)."""
    light = {1: float(np.clip((t - 0.55) / 0.4, 0, 1)), 4: 1.0}.get(idx, 0.5)
    lum = rgba[..., 0] * (1 - light) + rgba[..., 2] * light
    lum = lum * lum * (3 - 2 * lum) * 0.35 + lum * 0.65
    yy, xx = np.mgrid[0:H, 0:W]
    v = np.hypot((xx / W - 0.5), (yy / H - 0.5) * 0.85)
    lum = lum * (1 - 0.55 * np.clip(v * 1.35, 0, 1) ** 2.2)
    return (np.clip(lum, 0, 1) * 235).astype(np.uint8)


if __name__ == '__main__':
    names = sys.argv[1:] or [p[0] for p in PANELS]
    tiles = []
    for i, (name, line, secs, g, crop) in enumerate(PANELS):
        if name not in names:
            continue
        rgba = build(name, line, secs, g, crop)
        for t in ((0.3, secs * 0.6) if name == 'Phone' else (secs * 0.6,)):
            im = cv2.cvtColor(cv2.resize(preview(rgba, i, t, secs), (960, 540)), cv2.COLOR_GRAY2BGR)
            if line:
                from PIL import Image, ImageDraw, ImageFont
                pil = Image.fromarray(im)
                f = ImageFont.truetype(FONT, 30)
                wdt = ImageDraw.Draw(pil).textlength(line, font=f)
                ImageDraw.Draw(pil).text(((960 - wdt) / 2, 540 - 92), line, fill=(236, 238, 240), font=f)
                im = np.asarray(pil)
            tiles.append(im)
        print(name, 'mean R %.2f near %.2f lit %.2f matte %.3f' % tuple(rgba[..., k].mean() for k in range(4)))
    while len(tiles) % 2:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(f'{OUT}/plates_preview.jpg', np.vstack([np.hstack(tiles[k:k + 2]) for k in range(0, len(tiles), 2)]))
    print('sheet', f'{OUT}/plates_preview.jpg')
