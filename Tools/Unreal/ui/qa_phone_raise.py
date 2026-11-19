"""Phone raise QA (main's spec, 2026-11-09): the view stays on the player camera while the phone comes up.
Per frame: (L) letterbox, black bands at both top and bottom (the phone CineCamera's aspect constraint);
(S) smear, sharpness (variance of the Laplacian) below SMEAR x the median of the frames before the raise;
at rest (R) readable, OCR (easyocr) at 960 px wide reads at least 2 of the phone's own words.
Red-proven on story's T0 frames: 00970/00971 SMEAR, all LETTERBOX; 00985 READABLE; calm 00965-00969 0 fails, NOT READABLE.
  python Tools/Unreal/ui/qa_phone_raise.py <sweep dir>                    raise = the first 'P' key in keys.json
  python Tools/Unreal/ui/qa_phone_raise.py <frames dir> --raise N [--crop x0,y0,x1,y1]   raise = frame index N
Red proof: story's T0 frames (SetViewTargetWithBlend to the phone camera) must FAIL L and S:
  python Tools/Unreal/ui/qa_phone_raise.py P:/FoA/Saved/StoryShots/t0_phone_frames --raise <first moving frame> --crop 8,138,1292,1014"""
import argparse
import bisect
import json
import os

import cv2
import numpy as np

SMEAR = 0.45      # a frame keeping under 45% of the resting sharpness is a smear
BAND = 0.03       # letterbox: >= 3% of the height black at both top and bottom
REST_S = 1.5      # the phone is at rest 1.5 s after the raise starts
WORDS = ('today', 'mom', 'career', 'day', 'leave', 'house', 'reminder', 'notes', 'messages', 'wake', 'job', 'phone', 'draft')

ap = argparse.ArgumentParser()
ap.add_argument('d')
ap.add_argument('--raise', dest='raise_i', type=int)
ap.add_argument('--crop')
ap.add_argument('--fps', type=float, default=0)
a = ap.parse_args()
fdir = os.path.join(a.d, 'frames') if os.path.isdir(os.path.join(a.d, 'frames')) else a.d
files = sorted(f for f in os.listdir(fdir) if f.lower().endswith('.png'))
times = None
if a.raise_i is None:  # sweep dir: frame times from shots.json, the raise from the first P key (as qa_frames.py)
    keys = json.load(open(os.path.join(a.d, 'keys.json')))
    shots = json.load(open(os.path.join(a.d, 'shots.json')))
    req = shots['requests']
    pairs = sorted(g - w for g, w in zip(shots.get('game_t', []), shots.get('req_wall', [])) if g is not None and w is not None)
    off = pairs[len(pairs) // 2] if pairs else 0.0
    files = [f for f in files if int(f[1:5]) - 1 < len(req) and req[int(f[1:5]) - 1] is not None]
    times = [shots['t0'] + req[int(f[1:5]) - 1] - off for f in files]
    p = next(k for k in keys['keys'] if k['key'] == 'P')
    a.raise_i = bisect.bisect_left(times, p['epoch'])
crop = [int(v) for v in a.crop.split(',')] if a.crop else None


def load(f):
    im = cv2.imread(os.path.join(fdir, f), cv2.IMREAD_GRAYSCALE)
    if crop:
        im = im[crop[1]:crop[3], crop[0]:crop[2]]
    return cv2.resize(im, (640, int(640 * im.shape[0] / im.shape[1])), interpolation=cv2.INTER_AREA)


def bands(im):
    w = im.shape[1]
    dark = (im[:, w // 20: -w // 20] < 6).mean(1) > 0.98
    top = next((i for i, v in enumerate(dark) if not v), len(dark))
    bot = next((i for i, v in enumerate(dark[::-1]) if not v), len(dark))
    return top / len(dark), bot / len(dark)


def sharp(im):
    t, b = bands(im)  # band edges (and their antialiased rows) are hard and hide a smeared picture (story 00971)
    t, b = int(t * len(im)) + 3 if t else 0, int(b * len(im)) + 3 if b else 0
    return float(cv2.Laplacian(im[t: len(im) - b], cv2.CV_64F).var())


fps = a.fps or (len(times) / (times[-1] - times[0]) if times else 30.0)
pre = [i for i in range(max(0, a.raise_i - int(fps)), a.raise_i) if load(files[i]).mean() > 8]  # no fades in the baseline
assert pre, 'no frames before the raise'
base_s = float(np.median([sharp(load(files[i])) for i in pre]))
window = range(a.raise_i, min(len(files), a.raise_i + int(fps * REST_S) + 1))
fails = []
for i in window:
    im = load(files[i])
    t, b = bands(im)
    black = im.mean() <= 8  # a fade, neither letterbox nor smear
    s = sharp(im) / base_s if not black else 1.0
    lb = t >= BAND and b >= BAND and not black
    sm = s < SMEAR
    if lb or sm:
        fails.append(files[i])
    print(f'{files[i]} +{(i - a.raise_i) / fps:4.2f}s  bands {t:.3f}/{b:.3f}{" LETTERBOX" if lb else ""}  sharp {s:.2f}{" SMEAR" if sm else ""}')
import easyocr  # noqa: E402  (slow import, only for the rest frame)
rest = cv2.imread(os.path.join(fdir, files[window[-1]]))
if crop:
    rest = rest[crop[1]:crop[3], crop[0]:crop[2]]
rest = cv2.resize(rest, (960, int(960 * rest.shape[0] / rest.shape[1])), interpolation=cv2.INTER_AREA)
words = [w for _, w, c in easyocr.Reader(['en'], gpu=False, verbose=False).readtext(rest) if c > 0.5]
hits = [w for w in words if any(k in w.lower() for k in WORDS)]
read = len(hits) >= 2
print(f'rest {files[window[-1]]}: OCR {words} -> phone words {hits}  {"READABLE" if read else "NOT READABLE"}')
from qa_phone_pages import pages  # noqa: E402  (same folder) exactly one phone page may draw (main, anim phone5)
lock, home, _ = pages(cv2.imread(os.path.join(fdir, files[window[-1]])), crop)
two = bool(lock and home)
print(f'pages at rest: lock {lock} | home {home}', 'TWO PAGES' if two else 'one page')
print(f'base sharpness {base_s:.0f} over {len(pre)} frames; {len(fails)} failing frames of {len(window)};',
      'PASS' if not fails and read and not two else 'FAIL')
