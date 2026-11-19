"""Read a sweep (sweep_intro.py) frame by frame: luma timeline with key presses, automatic flags, contact sheets.
  python Tools/Unreal/ui/analyze_sweep.py <sweep dir>
Flags (frame numbers are 1-based, as in frames/fNNNN.png; t = frame / fps):
  FLASH   a one- or two-frame jump in mean luma that comes straight back (a popped widget, a wrong frame)
  GREY    a frame meant to be black (max luma < 0.12) whose median sits above pure black (UI black drawn grey)
  FADEIN  each rise from black (mean < 0.01) to visible content: two FADEINs inside one card = a double fade
Writes timeline.png, sheet_NN.png (10 fps, 60 thumbnails each) and flags.txt in the sweep dir."""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw


def main(d):
    fs = sorted(glob.glob(os.path.join(d, 'frames', 'f*.png')))
    meta = json.load(open(os.path.join(d, 'keys.json')))
    fps, t_rec = meta['fps'], meta['record_started_at']
    shots = json.load(open(os.path.join(d, 'shots.json')))
    req = shots['requests']  # real request times (the rate varies)
    with open(os.path.join(d, 'state.txt'), 'w', encoding='utf-8') as fh:  # the recorder's once-a-second probe
        for e in shots.get('state', []):
            fh.write(json.dumps(e) + chr(10))
    tm = lambda i: req[i] if i < len(req) else (i + 1) / fps  # noqa: E731
    mean, med, mx = [], [], []
    for f in fs:
        a = np.asarray(Image.open(f).convert('L').resize((320, 180))).astype(np.float32) / 255
        mean.append(float(a.mean())); med.append(float(np.median(a))); mx.append(float(np.percentile(a, 99.5)))
    mean = np.array(mean)
    flags = []
    for i in range(1, len(mean) - 2):
        for w in (1, 2):
            jump_in, jump_out = mean[i] - mean[i - 1], mean[i + w] - mean[i + w - 1]
            if abs(jump_in) > 0.03 and abs(jump_out) > 0.03 and np.sign(jump_in) != np.sign(jump_out) \
                    and abs(mean[i + w] - mean[i - 1]) < 0.4 * abs(jump_in):
                flags.append((i + 1, 'FLASH', f'{w} frame(s): mean {mean[i - 1]:.3f} -> {mean[i]:.3f} -> {mean[i + w]:.3f}'))
    for i, (m, md, x) in enumerate(zip(mean, med, mx)):
        if x < 0.12 and md > 0.012:
            flags.append((i + 1, 'GREY', f'median {md:.3f} (black should be < 0.012), max {x:.3f}'))
    dark = mean < 0.01
    for i in range(1, len(mean)):
        if dark[i - 1] and not dark[i]:
            flags.append((i + 1, 'FADEIN', f'from black at t={(i + 1) / fps + t_rec:.2f} s (PIE time)'))
    flags.sort()
    with open(os.path.join(d, 'flags.txt'), 'w', encoding='utf-8') as fh:
        for fr, kind, msg in flags:
            fh.write(f'f{fr:04d} t={tm(fr - 1):6.2f}s {kind:6s} {msg}\n')
    # timeline
    Wd, Hd = 1600, 220
    img = Image.new('RGB', (Wd, Hd), 'black')
    dr = ImageDraw.Draw(img)
    n = len(mean)
    pts = [(int(i * (Wd - 1) / max(1, n - 1)), int(Hd - 20 - mean[i] * (Hd - 40) / max(0.01, mean.max()))) for i in range(n)]
    dr.line(pts, fill=(230, 230, 230))
    for k in meta['keys']:
        x = int(((k['t'] - t_rec) * fps) * (Wd - 1) / max(1, n - 1))
        dr.line([(x, 0), (x, Hd)], fill=(255, 80, 80)); dr.text((x + 2, 2), k['key'], fill=(255, 80, 80))
    for fr, kind, _ in flags:
        if kind != 'GREY':
            x = int((fr - 1) * (Wd - 1) / max(1, n - 1))
            dr.line([(x, Hd - 18), (x, Hd)], fill=(80, 255, 80) if kind == 'FADEIN' else (255, 220, 0))
    img.save(os.path.join(d, 'timeline.png'))
    # contact sheets at 10 fps
    step = max(1, fps // 10)
    picks = list(range(0, n, step))
    for s in range(0, len(picks), 60):
        sheet = Image.new('RGB', (10 * 160, 6 * 102), 'black')
        sd = ImageDraw.Draw(sheet)
        for j, i in enumerate(picks[s:s + 60]):
            th = Image.open(fs[i]).convert('RGB').resize((160, 90))
            sheet.paste(th, ((j % 10) * 160, (j // 10) * 102))
            sd.text(((j % 10) * 160 + 2, (j // 10) * 102 + 90), f'f{i + 1:04d} {tm(i):.1f}s', fill=(255, 90, 90))
        sheet.save(os.path.join(d, f'sheet_{s // 60:02d}.png'))
    print(len(fs), 'frames,', len(flags), 'flags ->', os.path.join(d, 'flags.txt'))


if __name__ == '__main__':
    main(sys.argv[1])
