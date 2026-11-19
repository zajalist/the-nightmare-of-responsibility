"""Face lane media from a pie_face_shots.py run (plain Python + PIL + ffmpeg, outside the editor).
  python Tools/Unreal/face/face_sheet.py sheet <run> [labels...]   -> Saved/FaceShots/<run>/sheet_<run>.png
      each still next to the user's reference, cropped around his head (projected head from shots.json when known)
  python Tools/Unreal/face/face_sheet.py gif <run> <prefix> [fps]  -> Saved/FaceShots/<run>/<prefix>.gif
  python Tools/Unreal/face/face_sheet.py pair <runA> <runB> [labels...] -> Saved/FaceShots/<runB>/pair_<runA>_<runB>.png
  python Tools/Unreal/face/face_sheet.py avatar <runA> <runB> [views...] -> Saved/FaceShots/avatar/avatar_<runA>_<runB>.png
      clean_<view> frames (blur weight 0) of both runs side by side, cropped to his upper body"""
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('P:/FoA/Saved/FaceShots')
REF = Path('C:/Users/Admin/Pictures/Screenshots/Screenshot 2026-11-07 232701.png')
LABELS = ['close_front', 'close_34', 'close_profile', 'mid_34', 'tps_34back', 'far_front', 'back', 'topdown']
FONT = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 22)
CELL = 420


def shots(run):
    p = ROOT / run / 'shots.json'
    return {s['label']: s for s in json.loads(p.read_text())['shots']} if p.exists() else {}


def crop(img, info, zoom=True, k=3.0):
    """Square crop around the projected head (k head radii each side), else the whole frame."""
    h = (info or {}).get('head_px')
    if zoom and h:
        x, y, r = h
        half = max(40, k * r)
        box = (int(x - half), int(y - half), int(x + half), int(y + half))
        img = img.crop(box)
    img.thumbnail((CELL, CELL))
    return img


def tile(img, caption):
    t = Image.new('RGB', (CELL, CELL + 34), (18, 18, 18))
    t.paste(img, ((CELL - img.width) // 2, (CELL - img.height) // 2))
    ImageDraw.Draw(t).text((8, CELL + 4), caption, fill=(230, 230, 230), font=FONT)
    return t


def sheet(run, labels):
    info = shots(run)
    labels = [l for l in (labels or LABELS) if (ROOT / run / f'{l}.png').exists()]
    ref = Image.open(REF).convert('RGB')
    ref.thumbnail((CELL, CELL))
    rows = []
    for l in labels:
        img = Image.open(ROOT / run / f'{l}.png').convert('RGB')
        row = Image.new('RGB', (CELL * 3, CELL + 34), (18, 18, 18))
        row.paste(tile(ref, 'reference'), (0, 0))
        row.paste(tile(crop(img.copy(), info.get(l), False), l + ' (full frame)'), (CELL, 0))
        row.paste(tile(crop(img, info.get(l)), l + ' (head crop)'), (CELL * 2, 0))
        rows.append(row)
    out = Image.new('RGB', (CELL * 3, (CELL + 34) * len(rows)), (18, 18, 18))
    for i, r in enumerate(rows):
        out.paste(r, (0, i * (CELL + 34)))
    path = ROOT / run / f'sheet_{run}.png'
    out.save(path)
    print(path)


def pair(a, b, labels):
    ia, ib = shots(a), shots(b)
    labels = [l for l in (labels or LABELS) if (ROOT / a / f'{l}.png').exists() and (ROOT / b / f'{l}.png').exists()]
    out = Image.new('RGB', (CELL * 2, (CELL + 34) * len(labels)), (18, 18, 18))
    for i, l in enumerate(labels):
        out.paste(tile(crop(Image.open(ROOT / a / f'{l}.png').convert('RGB'), ia.get(l)), f'{l} {a}'), (0, i * (CELL + 34)))
        out.paste(tile(crop(Image.open(ROOT / b / f'{l}.png').convert('RGB'), ib.get(l)), f'{l} {b}'), (CELL, i * (CELL + 34)))
    path = ROOT / b / f'pair_{a}_{b}.png'
    out.save(path)
    print(path)


def body_crop(img, info):
    h = (info or {}).get('head_px')
    if h:
        x, y, r = h
        img = img.crop((int(x - 3.2 * r), int(y - 1.6 * r), int(x + 3.2 * r), int(y + 5.4 * r)))
    img.thumbnail((CELL, int(CELL * 1.1)))
    return img


def avatar(a, b, views):
    ia, ib = shots(a), shots(b)
    views = views or ['mid_34', 'far_front', 'tps_34back', 'back', 'close_34']
    H = int(CELL * 1.1) + 34
    out = Image.new('RGB', (CELL * 2, H * len(views)), (18, 18, 18))
    d = ImageDraw.Draw(out)
    for i, v in enumerate(views):
        for j, (run, info) in enumerate(((a, ia), (b, ib))):
            img = body_crop(Image.open(ROOT / run / f'clean_{v}.png').convert('RGB'), info.get(v))
            out.paste(img, (j * CELL + (CELL - img.width) // 2, i * H))
            d.text((j * CELL + 8, i * H + H - 32), f'{v} {"before" if j == 0 else "after"} ({run})', fill=(230, 230, 230), font=FONT)
    path = ROOT / 'avatar' / f'avatar_{a}_{b}.png'
    path.parent.mkdir(exist_ok=True)
    out.save(path)
    print(path)


def overlay(run, views):
    """Per view: the blurred still, the clean still, and the clean still with the blur weight (mask review frame,
    red channel) tinted red, cropped around his head, next to the reference: the face/hair mask proof."""
    import numpy as np
    info = shots(run)
    views = views or ['close_front', 'close_34', 'close_profile', 'mid_34', 'far_front']
    ref = Image.open(REF).convert('RGB')
    ref.thumbnail((CELL, CELL))
    out = Image.new('RGB', (CELL * 4, (CELL + 34) * len(views)), (18, 18, 18))
    for i, v in enumerate(views):
        blur = Image.open(ROOT / run / f'{v}.png').convert('RGB')
        clean = Image.open(ROOT / run / f'clean_{v}.png').convert('RGB')
        m = np.asarray(Image.open(ROOT / run / f'mask_{v}.png').convert('RGB')).astype(np.float32)[..., 0:1] / 255.0
        c = np.asarray(clean).astype(np.float32)
        tinted = c * (1 - 0.6 * m) + np.array([255.0, 40.0, 40.0]) * 0.6 * m
        ov = Image.fromarray(tinted.clip(0, 255).astype(np.uint8))
        for j, (im, cap) in enumerate(((ref, 'reference'), (crop(blur, info.get(v)), v + ' blurred'),
                                       (crop(clean, info.get(v)), 'clean'), (crop(ov, info.get(v)), 'blur weight in red'))):
            out.paste(tile(im if j else ref, cap), (j * CELL, i * (CELL + 34)))
    path = ROOT / run / f'overlay_{run}.png'
    out.save(path)
    print(path)


A_NAME = os.environ.get('FOA_A_NAME', 'v8 (live)')  # captions: live material (v8_ frames), preview (v10_ frames)
B_NAME = os.environ.get('FOA_B_NAME', 'v10')


def compare(run, views):
    """v8 (live) against v10 (preview) in the same frozen pose, next to the reference, plus the v10 blur weight in
    red over the clean frame: the before-install review sheet."""
    import numpy as np
    info = shots(run)
    views = views or ['close_front', 'close_34', 'close_profile', 'closeup']
    ref = Image.open(REF).convert('RGB')
    ref.thumbnail((CELL, CELL))
    out = Image.new('RGB', (CELL * 4, (CELL + 34) * len(views)), (18, 18, 18))
    for i, v in enumerate(views):
        clean = np.asarray(Image.open(ROOT / run / f'clean_{v}.png').convert('RGB')).astype(np.float32)
        m = np.asarray(Image.open(ROOT / run / f'mask_{v}.png').convert('RGB')).astype(np.float32)[..., 0:1] / 255.0
        ov = Image.fromarray((clean * (1 - 0.6 * m) + np.array([255.0, 40.0, 40.0]) * 0.6 * m).clip(0, 255).astype(np.uint8))
        cells = [(ref, 'reference'), (crop(Image.open(ROOT / run / f'v8_{v}.png').convert('RGB'), info.get('v8_' + v), k=1.7), v + ' ' + A_NAME),
                 (crop(Image.open(ROOT / run / f'v10_{v}.png').convert('RGB'), info.get('v10_' + v), k=1.7), v + ' ' + B_NAME),
                 (crop(ov, info.get('v10_' + v), k=1.7), B_NAME.split()[0] + ' blur weight (red)')]
        for j, (im, cap) in enumerate(cells):
            out.paste(tile(im, cap), (j * CELL, i * (CELL + 34)))
    path = ROOT / run / f'compare_{run}.png'
    out.save(path)
    print(path)


def gif(run, prefix, fps=10):
    src = ROOT / run
    out = src / f'{prefix}.gif'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', str(src / f'{prefix}_%03d.png'),
                    '-vf', 'scale=640:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer',
                    str(out)], check=True)
    print(out)


if __name__ == '__main__':
    cmd, run, *rest = sys.argv[1:]
    if cmd == 'sheet':
        sheet(run, rest)
    elif cmd == 'gif':
        gif(run, rest[0], int(rest[1]) if len(rest) > 1 else 10)
    elif cmd == 'pair':
        pair(run, rest[0], rest[1:])
    elif cmd == 'avatar':
        avatar(run, rest[0], rest[1:])
    elif cmd == 'overlay':
        overlay(run, rest)
    elif cmd == 'compare':
        compare(run, rest)
