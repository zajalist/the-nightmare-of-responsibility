"""Two directions for the battle command UI (user 2026-11-10: "the whole battle UI is a bit boring"), as offline stills over
a real fight frame (Saved/EncounterCaptures/battle_commands_held.png, the old UI blurred out). Directional only: the
build is UMG with the sand materials (M_UI_SandText, MF_UI_SandShape), proven in PIE.
  python Tools/Unreal/ui/battle_mockups.py      -> Saved/UIShots/aaa/battle_mock/A_sand_glyphs.png, B_torn_cards.png
Rules held: monochrome, Darker Grotesque + IBM Plex Mono, no separators, dots, divider lines or eyebrow labels; costs as
pips; descriptions only on focus; everything inside a 5% safe frame at 16:9 (and the 16:10 crop is drawn as a check)."""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

SRC = 'P:/FoA/Saved/EncounterCaptures/battle_commands_held.png'
OUT = 'P:/FoA/Saved/UIShots/aaa/battle_mock'
FD = 'P:/FoA-Assets/fonts'
W, H = 1600, 900
INK = (226, 221, 208)
DIM = (150, 146, 136)


def font(face, size):
    path = {'semi': f'{FD}/DarkerGrotesque/DarkerGrotesque-SemiBold.ttf', 'med': f'{FD}/DarkerGrotesque/DarkerGrotesque-Medium.ttf',
            'xb': f'{FD}/DarkerGrotesque/DarkerGrotesque-ExtraBold.ttf', 'mono': f'{FD}/IBMPlexMono/IBMPlexMono-Regular.ttf',
            'monom': f'{FD}/IBMPlexMono/IBMPlexMono-Medium.ttf'}[face]
    return ImageFont.truetype(path, size)


def plate():
    """The fight frame with the old UI erased: crop the PIE chrome, blur and sink the old panels."""
    im = Image.open(SRC).convert('RGB').crop((3, 36, 1283, 756)).resize((W, H), Image.LANCZOS)
    k = W / 1280
    soft = im.filter(ImageFilter.GaussianBlur(70)).point(lambda v: int(v * 0.8))
    m = Image.new('L', (W, H), 0)  # feathered masks, so the erased panels leave no rectangles
    for x0, y0, x1, y1 in ((20, 45, 1040, 150), (20, 130, 330, 495), (20, 485, 830, 765), (1050, 555, 1270, 690)):
        ImageDraw.Draw(m).rectangle(tuple(int(v * k) for v in (x0, y0 - 36, x1, y1 - 36)), fill=255)
    im = Image.composite(soft, im, m.filter(ImageFilter.GaussianBlur(28)))
    # the scene sinks toward the bottom (the old panels were the only contrast there)
    grad = Image.linear_gradient('L').resize((W, H)).point(lambda v: int(max(0, v - 90) * 1.6))
    black = Image.new('RGB', (W, H), (6, 6, 5))
    im = Image.composite(black, im, grad.point(lambda v: min(220, v)))
    return im.convert('RGBA')


def sand_text(base, xy, text, fnt, alpha=1.0, trail=0, lift=0, seed=1, anchor='la'):
    """Text built from grains: a solid core, a ragged grain edge, and (focus) grains blown to the right as a trail."""
    rnd = random.Random(seed)
    mask = Image.new('L', base.size, 0)
    ImageDraw.Draw(mask).text((xy[0], xy[1] - lift), text, font=fnt, fill=255, anchor=anchor)
    bbox = mask.getbbox()
    if not bbox:
        return
    core = mask.filter(ImageFilter.MinFilter(3)) if fnt.size > 30 else mask
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), core)
    grains = Image.new('L', base.size, 0)
    gp = grains.load()
    ep = edge.load()
    for y in range(max(0, bbox[1] - 3), min(base.size[1], bbox[3] + 3)):
        for x in range(max(0, bbox[0] - 3), min(base.size[0], bbox[2] + 3)):
            if ep[x, y] and rnd.random() < 0.38:
                gp[x, y] = rnd.randint(120, 255)
    for _ in range(int(trail)):  # the sand trail, streaming right and slightly down from the word's tail
        x = rnd.uniform(bbox[0] + (bbox[2] - bbox[0]) * 0.5, bbox[2])
        y = rnd.uniform(bbox[1], bbox[3])
        d = rnd.expovariate(1 / 38)
        px, py = int(x + d), int(y + d * 0.12 + rnd.uniform(-2, 2))
        if 0 <= px < base.size[0] and 0 <= py < base.size[1]:
            gp[px, py] = int(255 * max(0.15, 1 - d / 160))
    a = ImageChops.lighter(core, grains).point(lambda v: int(v * alpha))
    layer = Image.new('RGBA', base.size, INK + (0,))
    layer.putalpha(a)
    base.alpha_composite(layer)


def pips(d, x, y, n, of, size=7, gap=5, lit=INK):
    for i in range(of):  # filled = cost; hollow = the rest of a 3-pip scale
        box = (x + i * (size + gap), y, x + i * (size + gap) + size, y + size)
        if i < n:
            d.rectangle(box, fill=lit)
        else:
            d.rectangle(box, outline=DIM)


def halo(base, box, alpha=150, blur=40):
    """The soft T_UI_SoftDot plate under text (the HUD's subtitle language), never a box."""
    m = Image.new('L', base.size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    layer = Image.new('RGBA', base.size, (0, 0, 0, 0))
    layer.putalpha(m)
    base.alpha_composite(layer)


def safe(d):
    """5% safe frame at 16:9 and the 16:10 crop, as faint guides for review (not part of the UI)."""
    d.rectangle((int(W * .05), int(H * .05), int(W * .95), int(H * .95)), outline=(255, 70, 70, 70))
    c = int((W - H * 1.6) / 2)
    d.rectangle((c, 0, W - c, H - 1), outline=(70, 160, 255, 70))


def resources(base, d, x, y):
    """Composure and Resolve as sand columns (an hourglass read): grains settle to the level, numbers in Plex Mono."""
    for i, (name, val, top) in enumerate((('Composure', 100, 100), ('Resolve', 40, 100))):
        cx = x + i * 92
        h = 150
        lvl = int(h * val / top)
        rnd = random.Random(i + 7)
        px = base.load()
        for _ in range(1400 if lvl else 0):
            gx = cx + rnd.uniform(0, 14) + rnd.gauss(0, 0.8)
            gy = y + h - rnd.uniform(0, lvl) ** 1.0
            if 0 <= int(gx) < W and 0 <= int(gy) < H:
                px[int(gx), int(gy)] = INK + (255,)
        d.text((cx + 7, y + h + 14), str(val), font=font('monom', 22), fill=INK, anchor='ma')
        d.text((cx + 7, y + h + 42), name, font=font('med', 22), fill=DIM, anchor='ma')


def direction_a():
    """A: Sand glyphs. The commands are words of sand on an arc under him; the focused one lifts out of the arc,
    sharpens and trails grains; its line and its cost pips sit under it only while it is focused. The garment's
    intent forms in sand beside the shirt."""
    im = plate()
    d = ImageDraw.Draw(im, 'RGBA')
    halo(im, (260, 640, 1340, 960), alpha=170, blur=60)
    cmds = [('Find armhole', 0), ('Button up', 1), ('Deep breath', 0), ('Check mirror', 1), ('Items', 0), ('Try to leave', 0)]
    focus = 1
    xs = [330 + i * 188 for i in range(len(cmds))]
    for i, (name, cost) in enumerate(cmds):
        f = font('semi', 50 if i == focus else 32)
        sand_text(im, (xs[i], 800), name, f, alpha=1.0 if i == focus else 0.5, trail=900 if i == focus else 0,
                  lift=34 if i == focus else 0, seed=i, anchor='mm')
        if cost and i != focus:
            pips(d, int(xs[i] - 23), 830, cost, 3, size=7, gap=6, lit=DIM)
    fx = xs[focus]
    pips(d, int(fx - 23), 812, 1, 3, size=9, gap=7)
    d.text((fx, 700), 'Fasten one button. Perfect timing counts twice.', font=font('mono', 20), fill=INK, anchor='mm')
    # the intent, formed beside the shirt (it reads as the shirt's thought, not a menu row)
    sand_text(im, (900, 300), 'tightens the collar', font('med', 30), alpha=0.85, trail=260, seed=31)
    d.text((900, 340), 'next turn', font=font('mono', 17), fill=DIM)
    # targets: the garments' names only, the current one in full ink; no panel, no box
    for i, (name, cur) in enumerate((('A sock', 0), ('The trousers', 0), ('The shirt, inside out', 1), ('The tie', 0), ('A sock', 0))):
        d.text((96, 120 + i * 40), name, font=font('semi' if cur else 'med', 26 if cur else 22), fill=INK if cur else DIM)
    resources(im, d, 1330, 560)
    d.text((W / 2, 852), 'Left Right  choose      A  act      Tab  change target', font=font('med', 20), fill=DIM, anchor='mm')
    return im, d


def glyph_draw(gd, x, y, kind, r, col):
    """Line glyphs drawn, not typed (Darker Grotesque has no symbols): sleeve, button, breath, mirror, pocket, door, claw."""
    w = 4
    if kind == 'sleeve':
        gd.line((x - r, y + r * .6, x + r * .7, y - r * .7), fill=col, width=w)
        gd.line((x + r * .7, y - r * .7, x + r * .1, y - r * .75), fill=col, width=w)
        gd.line((x + r * .7, y - r * .7, x + r * .65, y - r * .1), fill=col, width=w)
    elif kind == 'button':
        gd.ellipse((x - r, y - r, x + r, y + r), outline=col, width=w)
        for dx, dy in ((-.3, -.3), (.3, -.3), (-.3, .3), (.3, .3)):
            gd.ellipse((x + dx * r - 4, y + dy * r - 4, x + dx * r + 4, y + dy * r + 4), fill=col)
    elif kind == 'breath':
        for k in range(3):
            pts = [(x - r + t * 2 * r / 20, y - r * .5 + k * r * .5 + math.sin(t / 20 * math.tau) * r * .18) for t in range(21)]
            gd.line(pts, fill=col, width=w - 1)
    elif kind == 'mirror':
        gd.ellipse((x - r * .7, y - r, x + r * .7, y + r), outline=col, width=w)
        gd.chord((x - r * .7, y - r, x + r * .7, y + r), 90, 270, fill=col)
    elif kind == 'pocket':
        gd.rectangle((x - r * .8, y - r * .6, x + r * .8, y + r * .8), outline=col, width=w)
        gd.line((x - r * .8, y - r * .1, x + r * .8, y - r * .1), fill=col, width=w - 1)
    elif kind == 'door':
        gd.rectangle((x - r * .6, y - r, x + r * .6, y + r), outline=col, width=w)
        gd.line((x + r * .1, y, x + r * 1.2, y), fill=col, width=w)
        gd.line((x + r * 1.2, y, x + r * .8, y - r * .35), fill=col, width=w)
    elif kind == 'claw':
        for k in (-1, 0, 1):
            gd.arc((x - r + k * r * .5, y - r, x + r + k * r * .5, y + r), 200, 300, fill=col, width=w)


def card(base, d, x, y, w, h, name, glyph, cost, focus, tilt, seed):
    """A tall sand-edged card: dark grain body, eroded edge (no outline), the name across its foot."""
    layer = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    m = Image.new('L', layer.size, 0)
    ImageDraw.Draw(m).rectangle((30, 30, 30 + w, 30 + h), fill=255)
    rnd = random.Random(seed)
    mp = m.load()
    for _ in range(int((w + h) * 9)):  # erode the edge into grains
        side = rnd.randrange(4)
        t = rnd.random()
        ex, ey = [(30 + t * w, 30), (30 + t * w, 30 + h), (30, 30 + t * h), (30 + w, 30 + t * h)][side]
        ex += rnd.gauss(0, 4)
        ey += rnd.gauss(0, 4)
        if 0 <= int(ex) < layer.size[0] and 0 <= int(ey) < layer.size[1]:
            mp[int(ex), int(ey)] = 0 if rnd.random() < 0.6 else 255
    body = Image.new('RGBA', layer.size, (18, 17, 15, 255) if focus else (12, 12, 11, 225))
    noise = Image.effect_noise(layer.size, 26).convert('L')
    body = Image.composite(body, Image.new('RGBA', layer.size, (34, 33, 30, 255)), noise.point(lambda v: 255 if v < 140 else 0))
    body.putalpha(ImageChops.multiply(m, Image.new('L', layer.size, 255 if focus else 215)))
    gd = ImageDraw.Draw(body)
    glyph_draw(gd, 30 + w / 2, 30 + h * 0.38, glyph, 34 if focus else 28, INK if focus else DIM)
    nf = font('semi', 30 if focus else 25)
    gd.text((30 + w / 2, 30 + h - 46), name, font=nf, fill=INK if focus else DIM, anchor='mm')
    if cost:
        pips(gd, int(30 + w / 2 - 24), 50, cost, 3, size=9, gap=6, lit=INK if focus else DIM)
    body = body.rotate(tilt, resample=Image.BICUBIC, expand=True)
    base.alpha_composite(body, (int(x - body.size[0] / 2), int(y - body.size[1] / 2)))


def direction_b():
    """B: Torn cards. The commands are a low hand of sand-edged cards; the focused one rises, straightens and grows,
    the rest settle and dim; its line shows over the hand only on focus. The garment's intent is its own card,
    pinned beside the shirt."""
    im = plate()
    d = ImageDraw.Draw(im, 'RGBA')
    cmds = [('Find armhole', 'sleeve', 0), ('Button up', 'button', 1), ('Deep breath', 'breath', 0), ('Check mirror', 'mirror', 1),
            ('Items', 'pocket', 0), ('Try to leave', 'door', 0)]
    focus = 1
    n = len(cmds)
    cw, ch = 150, 196
    for i, (name, glyph, cost) in sorted(enumerate(cmds), key=lambda t: t[0] == focus):
        off = i - (n - 1) / 2
        x = W / 2 + off * 168
        y = 735 + abs(off) ** 1.6 * 7 - (52 if i == focus else 0)
        card(im, d, x, y, cw + (26 if i == focus else 0), ch + (34 if i == focus else 0), name, glyph, cost,
             i == focus, 0 if i == focus else -off * 4.5, seed=i)
    halo(im, (430, 500, 1170, 600), alpha=140, blur=40)
    d.text((W / 2, 552), 'Fasten one button. Perfect timing counts twice.', font=font('mono', 21), fill=INK, anchor='mm')
    # the garment's intent card, small, pinned by the shirt
    card(im, d, 1010, 330, 110, 150, 'next turn', 'claw', 0, False, 6, seed=40)
    d.text((1010, 432), 'tightens the collar', font=font('med', 22), fill=INK, anchor='mm')
    for i, (name, cur) in enumerate((('A sock', 0), ('The trousers', 0), ('The shirt, inside out', 1), ('The tie', 0), ('A sock', 0))):
        d.text((96, 120 + i * 40), name, font=font('semi' if cur else 'med', 26 if cur else 22), fill=INK if cur else DIM)
    resources(im, d, 1330, 560)
    return im, d


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (('A_sand_glyphs', direction_a), ('B_torn_cards', direction_b)):
        im, d = fn()
        im.convert('RGB').save(f'{OUT}/{name}.png')
        g = im.copy()
        safe(ImageDraw.Draw(g, 'RGBA'))
        g.convert('RGB').save(f'{OUT}/{name}_guides.png')
        print('wrote', f'{OUT}/{name}.png')
