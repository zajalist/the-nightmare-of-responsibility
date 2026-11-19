"""FoA QA harness (qa lane). The coordinator runs it to test the game itself; every check prints one PASS/FAIL line
with the measured number, and each run writes Saved/QA/<YYYYMMDD_HHMM>/report.md plus the images it measured.

  python Tools/QA/foa_qa.py logs [--log FILE] [--warn-threshold 10]
  python Tools/QA/foa_qa.py pie-smoke                  one EXCLUSIVE PIE burst (<= 52 s), only in a PIE window
  python Tools/QA/foa_qa.py checks DIR [--beats FILE] [--sand-mask PNG | --sand-region x0,y0,x1,y1]
  python Tools/QA/foa_qa.py perf [--csv frametimes.csv]
  python Tools/QA/foa_qa.py selftest                   every check on its RED and GREEN fixtures; exit 1 on mismatch
  python Tools/QA/foa_qa.py fixtures                   rebuild Tools/QA/fixtures from their sources

Frames in a checks DIR are routed by name: title*, menu* -> (b) title contrast; menu* -> (a) menu words;
wake* -> (c) no UI; any frame -> (d) when a sand mask or region is given; the sorted frames -> (e) with --beats;
frametimes.csv -> (f). Regions are fractions of the frame (x0, y0, x1, y1) in Tools/QA/layout.json.
"""
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
QA = os.path.join(ROOT, 'Tools', 'QA')
FIX = os.path.join(QA, 'fixtures')
OUTROOT = os.path.join(ROOT, 'Saved', 'QA')
LOGS = os.path.join(ROOT, 'Saved', 'Logs')
SHOTS = os.path.join(ROOT, 'Saved', 'Screenshots', 'WindowsEditor')
LAYOUT = json.load(open(os.path.join(QA, 'layout.json'), encoding='utf-8'))
T = LAYOUT['thresholds']
OWNER = 'qa'


# ---------------------------------------------------------------- shared

def run_dir():
    stamp = time.strftime('%Y%m%d_%H%M')
    d, i = os.path.join(OUTROOT, stamp), 2
    while os.path.exists(d):
        d, i = os.path.join(OUTROOT, f'{stamp}_{i}'), i + 1
    os.makedirs(d)
    return d


def write_report(d, title, lines):
    with open(os.path.join(d, 'report.md'), 'w', encoding='utf-8') as fh:
        fh.write(f'# {title}\n\n{time.strftime("%Y-%m-%d %H:%M")}\n\n' + '\n'.join(lines) + '\n')
    print('report:', os.path.join(d, 'report.md'))


def verdict(ok):
    return 'PASS' if ok else 'FAIL'


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255.0


def luma(a):
    return a @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def rel_lum(a):  # WCAG relative luminance from sRGB
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return luma(lin.astype(np.float32))


def box(a, r):
    h, w = a.shape[:2]
    return int(r[0] * w), int(r[1] * h), int(r[2] * w), int(r[3] * h)


def crop(a, r):
    x0, y0, x1, y1 = box(a, r)
    return a[y0:y1, x0:x1]


def save_dbg(d, name, img):
    if d is not None and img is not None:
        Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8)).save(os.path.join(d, name))


# ---------------------------------------------------------------- image checks (a)-(e)

def glyphs(a, region):
    """OCR-free text detector: high-contrast blobs of glyph size that sit side by side on one line.
    Returns (glyph count in lines of >= 3, debug crop with the counted glyphs boxed)."""
    H = a.shape[0]
    c = crop(a, region)
    g = luma(c)
    k = max(3, int(0.05 * H)) | 1
    bg = cv2.blur(g, (k, k))
    best, best_boxes = 0, []
    for pol in (g - bg, bg - g):  # light text on dark, then dark text on light
        n, _, st, _ = cv2.connectedComponentsWithStats((pol > T['glyph_contrast']).astype(np.uint8), connectivity=8)
        cand = [tuple(int(v) for v in st[i][:4]) for i in range(1, n)
                if T['glyph_h'][0] * H <= st[i][3] <= T['glyph_h'][1] * H and 0.08 * st[i][3] <= st[i][2] <= 3 * st[i][3]
                and 0.1 <= st[i][4] / float(st[i][2] * st[i][3]) <= 0.9]
        parent = list(range(len(cand)))

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i, (x, y, w, h) in enumerate(cand):
            for j in range(i + 1, len(cand)):
                x2, y2, w2, h2 = cand[j]
                overlap = min(y + h, y2 + h2) - max(y, y2)
                gap = max(x2 - (x + w), x - (x2 + w2))
                if overlap >= 0.5 * min(h, h2) and gap <= 1.5 * max(h, h2) and max(h, h2) <= 3 * min(h, h2):
                    parent[root(i)] = root(j)
        groups = Counter(root(i) for i in range(len(cand)))
        boxes = [cand[i] for i in range(len(cand)) if groups[root(i)] >= 3]
        if len(boxes) > best:
            best, best_boxes = len(boxes), boxes
    dbg = c.copy()
    for x, y, w, h in best_boxes:
        cv2.rectangle(dbg, (x, y), (x + w, y + h), (0.2, 1.0, 0.2), 1)
    return best, dbg


def check_menu_words(a, region, dbg=None, tag='a'):
    n, img = glyphs(a, region)
    save_dbg(dbg, f'{tag}_menu_words.png', img)
    return n >= T['menu_min_glyphs'], f'glyphs={n} (need >= {T["menu_min_glyphs"]})'


def check_title_contrast(a, region, dbg=None, tag='b'):
    """Worst glyph-to-local-background luminance ratio over vertical strips of the title region (WCAG formula).
    A strip counts when it holds something as bright as the title's text; glyph = its 99th pct, background = median."""
    H = a.shape[0]
    c = crop(a, region)
    Y = rel_lum(c)
    text_y = float(np.percentile(Y, 99.5))
    sw = max(4, int(T['strip_w'] * H))
    worst, wx, used = 99.0, 0, 0
    for x in range(0, Y.shape[1] - sw // 2, sw):
        s = Y[:, x:x + sw]
        hi = float(np.percentile(s, 99))
        if hi < 0.6 * text_y:
            continue
        used += 1
        r = (hi + 0.05) / (float(np.median(s)) + 0.05)
        if r < worst:
            worst, wx = r, x
    img = c.copy()
    cv2.rectangle(img, (wx, 0), (wx + sw, img.shape[0] - 1), (1.0, 0.2, 0.2), 2)
    save_dbg(dbg, f'{tag}_title_contrast.png', img)
    if not used:
        return False, 'contrast=n/a (no title-bright pixels in region)'
    return worst >= T['title_min_contrast'], f'min contrast={worst:.2f}:1 over {used} strips (need >= {T["title_min_contrast"]}:1)'


def check_no_ui(a, regions, dbg=None, tag='c'):
    n, parts = 0, []
    for name, r in regions.items():
        k, img = glyphs(a, r)
        n += k
        parts.append(f'{name}={k}')
        save_dbg(dbg, f'{tag}_no_ui_{name}.png', img)
    return n < T['no_ui_max_glyphs'], f'glyphs={n} ({", ".join(parts)}; need < {T["no_ui_max_glyphs"]})'


def check_sand(a, mask, dbg=None, tag='d'):
    m = mask if mask.shape == a.shape[:2] else cv2.resize(mask.astype(np.uint8), (a.shape[1], a.shape[0]),
                                                          interpolation=cv2.INTER_NEAREST) > 0
    y = luma(a)[m]
    ch = (a.max(2) - a.min(2))
    colored = int((ch[m] > T['sand_chroma']).sum())
    frac = colored / max(1, int(m.sum()))
    img = a.copy()
    img[m & (ch > T['sand_chroma'])] = (1, 0, 0)
    cnt, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, cnt, -1, (0.2, 1, 0.2), 1)
    save_dbg(dbg, f'{tag}_sand.png', img)
    ok = y.mean() <= T['sand_max_luma'] and frac <= T['sand_max_chroma_frac']
    return ok, (f'mean luma={y.mean():.3f} (<= {T["sand_max_luma"]}), chroma px={colored} = {frac:.2%} of {int(m.sum())} '
                f'(<= {T["sand_max_chroma_frac"]:.1%})')


def motion_energy(frames):
    prev, e = None, []
    for f in frames:
        g = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        g = cv2.GaussianBlur(cv2.resize(g, (320, max(1, 320 * g.shape[0] // g.shape[1]))).astype(np.float32) / 255, (5, 5), 0)
        if prev is not None:
            e.append(float(np.abs(g - prev).mean()))
        prev = g
    return e


def check_motion(frames, beats, dbg=None, tag='e'):
    """Energy of pair i (frames i -> i+1) sits at t = (i + 1) / fps. Noise floor: the beat file's, else 3x the median
    of the quietest quarter of non-duplicate pairs (editor recordings repeat frames)."""
    e = motion_energy(frames)
    fps = float(beats['fps'])
    nz = sorted(v for v in e if v > 1e-5)
    floor = beats.get('noise_floor') or max(T['motion_min_floor'], 3 * float(np.median(nz[:max(1, len(nz) // 4)])))
    res, ok = [], True
    for h in beats['holds']:
        w = h.get('window', 0.3)
        vals = [v for i, v in enumerate(e) if abs((i + 1) / fps - h['t']) <= w]
        m = float(np.mean(vals)) if vals else float('inf')
        ok &= m <= floor
        res.append(f'{h["name"]}@{h["t"]}s={m:.4f}')
    if dbg is not None and e:
        W, Hh, top = 600, 160, max(e)
        img = np.zeros((Hh, W, 3), np.float32)
        pts = np.array([[int(i * (W - 1) / max(1, len(e) - 1)), int(Hh - 1 - v / top * (Hh - 10))] for i, v in enumerate(e)])
        cv2.polylines(img, [pts], False, (1, 1, 1), 1)
        fy = int(Hh - 1 - floor / top * (Hh - 10))
        cv2.line(img, (0, fy), (W - 1, fy), (0.2, 1, 0.2), 1)
        for h in beats['holds']:
            x = int((h['t'] * fps - 1) * (W - 1) / max(1, len(e) - 1))
            cv2.line(img, (x, 0), (x, Hh - 1), (1, 0.3, 0.3), 1)
        save_dbg(dbg, f'{tag}_motion.png', img)
    return ok, f'noise floor={floor:.4f}; holds: ' + ', '.join(res)


# ---------------------------------------------------------------- (f) frame time

def frame_stats(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8')))
    ms = np.array([float(r['ms']) for r in rows if r.get('near_shot', '0') != '1'], np.float64)
    shot_rows = sum(1 for r in rows if r.get('near_shot', '0') == '1')
    hitches = [(r.get('t'), float(r['ms'])) for r in rows if r.get('near_shot', '0') != '1' and float(r['ms']) > T['hitch_ms']]
    return ms, shot_rows, hitches


def check_frametime(path):
    ms, shot_rows, hitches = frame_stats(path)
    if not len(ms):
        return False, 'no frames'
    p50, p95, p99 = (float(np.percentile(ms, q)) for q in (50, 95, 99))
    ok = p95 <= T['p95_max_ms'] and len(hitches) <= T['max_hitches']
    return ok, (f'p50={p50:.1f} ms p95={p95:.1f} ms p99={p99:.1f} ms hitches>{T["hitch_ms"]:.0f}ms={len(hitches)} over '
                f'{len(ms)} frames ({shot_rows} screenshot frames excluded; need p95 <= {T["p95_max_ms"]} ms, '
                f'hitches <= {T["max_hitches"]})')


# ---------------------------------------------------------------- checks DIR

def sand_mask_from(args, shape):
    if '--sand-mask' in args:
        return load(args[args.index('--sand-mask') + 1])[..., 0] > 0.5
    if '--sand-region' in args or LAYOUT.get('sand'):
        r = [float(v) for v in args[args.index('--sand-region') + 1].split(',')] if '--sand-region' in args else LAYOUT['sand']
        m = np.zeros(shape, bool)
        x0, y0, x1, y1 = box(np.zeros(shape), r)
        m[y0:y1, x0:x1] = True
        return m
    return None


def run_checks(folder, args, out):
    lines, fails = [], 0
    frames = sorted(glob.glob(os.path.join(folder, '*.png')))
    R = LAYOUT['regions']

    def add(code, name, ok, msg):
        nonlocal fails
        fails += not ok
        lines.append(f'- {verdict(ok)} ({code}) {name}: {msg}')
    for f in frames:
        base = os.path.basename(f)
        stem = os.path.splitext(base)[0]
        kind = re.sub(r'^\d+_', '', base).split('_')[0].lower()
        a = None
        if kind in ('menu', 'title', 'wake'):
            a = load(f)
        if kind == 'menu':
            add('a', f'menu words {base}', *check_menu_words(a, R['menu'], out, stem + '_a'))
        if kind in ('menu', 'title'):
            add('b', f'title contrast {base}', *check_title_contrast(a, R['title'], out, stem + '_b'))
        if kind == 'wake':
            add('c', f'no UI during cinematic {base}', *check_no_ui(a, {'title': R['title'], 'menu': R['menu']}, out, stem + '_c'))
        if frames and ('--sand-mask' in args or '--sand-region' in args or LAYOUT.get('sand')):
            a = load(f) if a is None else a
            add('d', f'sand is black {base}', *check_sand(a, sand_mask_from(args, a.shape[:2]), out, stem + '_d'))
    if not ('--sand-mask' in args or '--sand-region' in args or LAYOUT.get('sand')):
        lines.append('- SKIP (d) sand is black: no sand mask or region given (--sand-mask / --sand-region / layout.json "sand")')
    if '--beats' in args:
        beats = json.load(open(args[args.index('--beats') + 1], encoding='utf-8'))
        seq = sorted(glob.glob(os.path.join(folder, beats.get('glob', '*.png'))))
        add('e', f'motion settles ({len(seq)} frames)', *check_motion(seq, beats, out))
    else:
        lines.append('- SKIP (e) motion settles: no --beats file given')
    ft = os.path.join(folder, 'frametimes.csv')
    if os.path.exists(ft):
        add('f', 'frame time', *check_frametime(ft))
    else:
        lines.append('- SKIP (f) frame time: no frametimes.csv in the folder')
    return lines, fails


# ---------------------------------------------------------------- logs

STAMP = re.compile(r'^\[[^\]]*\]\[\s*\d+\]')


def norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'\d+', '#', s.strip()))[:300]


def scan_log(lines):
    r = {k: Counter() for k in ('bp_errors', 'accessed_none', 'ensures', 'warnings', 'errors')}
    for ln in lines:
        body = STAMP.sub('', ln).strip()
        if 'Blueprint Runtime Error:' in body:
            r['bp_errors'][norm(body.split('Blueprint Runtime Error:', 1)[1])] += 1
        elif 'Accessed None' in body:
            r['accessed_none'][norm(body[body.index('Accessed None'):])] += 1
        if 'Ensure condition failed:' in body and not body.startswith('EnsureFailed'):
            r['ensures'][norm(body.split('Ensure condition failed:', 1)[1].split('[File:')[0])] += 1
        m = re.match(r'(\w+): Warning: (.*)', body)
        if m:
            r['warnings'][norm(f'{m.group(1)}: {m.group(2)}')] += 1
        m = re.match(r'(\w+): Error: (.*)', body)
        if m and 'Blueprint Runtime Error' not in body and 'Ensure condition failed' not in body:
            r['errors'][norm(f'{m.group(1)}: {m.group(2)}')] += 1
    return r


def pie_sessions(lines):
    out, cur = [], None
    for ln in lines:
        if 'PIE: Created PIE world' in ln:
            cur = []
            out.append(cur)
        elif 'Shutting down PIE' in ln:
            cur = None
        elif cur is not None:
            cur.append(ln)
    return out


def logs_section(lines, label, warn_threshold, prev=None):
    r = scan_log(lines)
    out, fails = [f'### {label}', ''], 0
    over = {k: v for k, v in r['warnings'].items() if v >= warn_threshold}
    for key, name, n in (('bp_errors', 'Blueprint runtime errors', len(r['bp_errors'])),
                         ('accessed_none', '"Accessed None"', len(r['accessed_none'])),
                         ('ensures', 'ensures', len(r['ensures'])),
                         ('warnings', f'warnings repeated >= {warn_threshold}x', len(over))):
        total = sum((over if key == 'warnings' else r[key]).values())
        fails += n > 0
        delta = ''
        if prev is not None:
            p = {norm(k): v for k, v in prev.get(key, {}).items()}  # older runs may have used an older normalisation
            p = {k: v for k, v in p.items() if v >= warn_threshold} if key == 'warnings' else p
            delta = f' (previous run: {len(p)} unique; {len(set((over if key == "warnings" else r[key])) - set(p))} new, {len(set(p) - set((over if key == "warnings" else r[key])))} gone)'
        out.append(f'- {verdict(n == 0)} {name}: {n} unique, {total} total{delta}')
    for key, name in (('bp_errors', 'Blueprint runtime errors'), ('accessed_none', 'Accessed None'), ('ensures', 'Ensures')):
        if r[key]:
            out += ['', f'{name} (count, message):', '']
            out += [f'    {v:5d}  {k}' + ('   [NEW]' if prev is not None and k not in prev.get(key, {}) else '')
                    for k, v in r[key].most_common(25)]
    if over:
        out += ['', f'Warnings repeated >= {warn_threshold}x:', ''] + [f'    {v:5d}  {k}' for k, v in sorted(over.items(), key=lambda kv: -kv[1])[:25]]
    if prev is not None:
        gone = [k for k in prev.get('bp_errors', {}) if k not in r['bp_errors']]
        if gone:
            out += ['', 'Blueprint runtime errors gone since the previous run:', ''] + [f'    {k}' for k in gone[:25]]
    if r['errors']:
        out += ['', 'Other errors (top 10):', ''] + [f'    {v:5d}  {k}' for k, v in r['errors'].most_common(10)]
    return out + [''], fails, {k: dict(v) for k, v in r.items()}


def previous(name):
    for d in sorted(glob.glob(os.path.join(OUTROOT, '2*')), reverse=True):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return json.load(open(p, encoding='utf-8')), d
    return None, None


def cmd_logs(args):
    thr = int(args[args.index('--warn-threshold') + 1]) if '--warn-threshold' in args else T['warn_threshold']
    path = args[args.index('--log') + 1] if '--log' in args else os.path.join(LOGS, 'FoA.log')
    prev, prev_dir = previous('logs.json')
    d = run_dir()
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    sessions = pie_sessions(lines)
    out = [f'Log: `{path}` ({len(lines)} lines, modified {time.strftime("%H:%M", time.localtime(os.path.getmtime(path)))}); '
           f'{len(sessions)} PIE sessions. Previous run: ' + (f'`{prev_dir}`' if prev_dir else 'none'), '']
    sec, fails, whole = logs_section(lines, 'Whole log (since this editor started)', thr, prev and prev.get('whole'))
    out += sec
    last = None
    if sessions:
        sec, f2, last = logs_section(sessions[-1], f'Last PIE session ({len(sessions[-1])} lines)', thr, prev and prev.get('last_pie'))
        out += sec
        fails += f2
    json.dump({'log': path, 'whole': whole, 'last_pie': last}, open(os.path.join(d, 'logs.json'), 'w', encoding='utf-8'), indent=1)
    print('\n'.join(out))
    write_report(d, 'QA logs', out)
    return 1 if fails else 0


# ---------------------------------------------------------------- perf

def dumphitches(path):
    """Aggregate `stat dumphitches` blocks: per hitch, every named stat's self time (its 'Self' child); idle/wait
    stats skipped. Returns (hitch frame ms list, Counter of self ms by stat name)."""
    hitch_ms, causes = [], Counter()
    stack = []
    for ln in open(path, encoding='utf-8', errors='replace'):
        if 'LogStats:' not in ln:
            continue
        body = ln.split('LogStats:', 1)[1].rstrip('\n')
        m = re.search(r'Thread Hitch \d+, Frame \d+\s+([\d.]+)ms', body)
        if m:
            hitch_ms.append(float(m.group(1)))
            stack = []
            continue
        m = re.match(r'(\s*)([\d.]+)ms \(\s*\d+\)\s+-\s+(.*)', body)
        if not m:
            continue
        depth, ms, name = len(m.group(1)), float(m.group(2)), m.group(3).split(' - ')[0].strip()
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if name == 'Self' and stack:
            parent = stack[-1][1]
            if not re.search(r'wait|idle|FrameTime|Thread_|GameThread', parent, re.I):
                causes[parent] += ms
        stack.append((depth, name))
    return hitch_ms, causes


def perf_lines(ft_path):
    out = []
    if ft_path and os.path.exists(ft_path):
        ok, msg = check_frametime(ft_path)
        out.append(f'- {verdict(ok)} (f) frame time `{ft_path}`: {msg}')
        _, _, hitches = frame_stats(ft_path)
        if hitches:
            out += ['', 'Hitches (t s, ms):', ''] + [f'    {t:>7}  {ms:7.1f}' for t, ms in hitches[:30]]
    else:
        out.append('- SKIP (f) frame time: no frametimes.csv (run pie-smoke first)')
    perf = os.path.join(ROOT, 'Saved', 'Perf')
    for p in sorted(glob.glob(os.path.join(perf, 'hitch_*.txt')) + glob.glob(os.path.join(perf, 'hitch_*.log'))):
        hm, causes = dumphitches(p)
        if not hm:
            continue
        out += ['', f'`stat dumphitches` in `{p}` ({time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p)))}): '
                f'{len(hm)} hitches, median {np.median(hm):.0f} ms, max {max(hm):.0f} ms. Top causes by summed self time:', '']
        out += [f'    {ms:9.1f} ms  {name}' for name, ms in causes.most_common(12)]
    traces = glob.glob(os.path.join(perf, '*.utrace'))
    if traces:
        out += ['', 'Insights traces (open in UnrealInsights; not parsed here):', '']
        out += [f'    {p} ({os.path.getsize(p) / 1e6:.0f} MB)' for p in traces]
    csvs = sorted(glob.glob(os.path.join(ROOT, 'Saved', 'Profiling', 'CSV', '*.csv')), key=os.path.getmtime)
    if csvs:
        rows = list(csv.reader(open(csvs[-1], encoding='utf-8', errors='replace')))
        if rows and 'FrameTime' in rows[0]:
            i = rows[0].index('FrameTime')
            v = np.array([float(r[i]) for r in rows[1:] if len(r) > i and re.match(r'^[\d.]+$', r[i])])
            if len(v):
                out += ['', f'CSV profiler `{csvs[-1]}`: {len(v)} frames, p50 {np.percentile(v, 50):.1f} ms, '
                        f'p95 {np.percentile(v, 95):.1f} ms, p99 {np.percentile(v, 99):.1f} ms, hitches>{T["hitch_ms"]:.0f}ms {(v > T["hitch_ms"]).sum()}']
    return out


def cmd_perf(args):
    ft = args[args.index('--csv') + 1] if '--csv' in args else None
    if not ft:
        cands = sorted(glob.glob(os.path.join(OUTROOT, '2*', 'frametimes.csv')))
        ft = cands[-1] if cands else None
    d = run_dir()
    out = perf_lines(ft)
    print('\n'.join(out))
    write_report(d, 'QA perf', out)
    return 0


# ---------------------------------------------------------------- pie-smoke

def cmd_pie_smoke(args):
    sys.path.insert(0, os.path.join(ROOT, 'Tools', 'Unreal'))
    import editor_lock
    os.environ['HAYBA_AGENT_ID'] = os.environ['FOA_AGENT'] = OWNER
    d = run_dir()
    frames_dir = os.path.join(d, 'frames')
    os.makedirs(frames_dir)
    while True:
        editor_lock.acquire(OWNER, wait_s=2400, ttl=90)  # EXCLUSIVE; waits for the PIE window by itself
        if editor_lock.in_exclusive_window(time.time() + 10):
            break
        editor_lock.release(OWNER)  # granted at the window's very end: ue_remote's own check would stall
        time.sleep(30)
    before = set(glob.glob(os.path.join(SHOTS, 'ScreenShot*.png')))  # after the wait: the editor may have restarted
    log_path = os.path.join(LOGS, 'FoA.log')
    log_off = os.path.getsize(log_path)
    t0 = time.time()
    try:
        env = dict(os.environ, FOA_EXCLUSIVE='1')
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'Tools', 'Unreal', 'ue_remote.py'),
                            os.path.join(QA, 'pie_drive.py'), f'QA_OUT={d.replace(os.sep, "/")}', 'QA_CAP=52'],
                           env=env, capture_output=True, text=True, timeout=60)
        print(r.stdout.strip()[-400:], r.stderr.strip()[-400:])
        done = os.path.join(d, 'done.json')
        while not os.path.exists(done) and time.time() - t0 < 56:
            time.sleep(0.5)
        if not os.path.exists(done):
            subprocess.run([sys.executable, os.path.join(ROOT, 'Tools', 'Unreal', 'ue_remote.py'),
                            os.path.join(QA, 'pie_drive.py'), 'QA_CMD=END'], env=env, timeout=30)
        time.sleep(1.0)
    finally:
        editor_lock.release(OWNER)
    held = time.time() - t0
    time.sleep(2.0)  # the last Shot writes its PNG a frame or two later
    shots = json.load(open(os.path.join(d, 'shots.json'))) if os.path.exists(os.path.join(d, 'shots.json')) else []
    new = sorted(set(glob.glob(os.path.join(SHOTS, 'ScreenShot*.png'))) - before)
    os.makedirs(os.path.join(frames_dir, 'raw'))
    for i, (s, f) in enumerate(zip(shots, new)):
        name = f'{i:02d}_{s["name"]}.png'
        shutil.copy(f, os.path.join(frames_dir, 'raw', name))  # the whole editor window, for audit
        im, vp = Image.open(f), s.get('vp')
        if vp:
            # shortcut: assumes the editor window is maximized on a monitor the size of the shot (absolute -> window
            # pixels by modulo); upgrade to the window's own position if a crop ever shows editor chrome
            x, y = vp[0] % im.width, vp[1] % im.height
            im = im.crop((x, y, min(im.width, x + vp[2]), min(im.height, y + vp[3])))
        else:
            name = name.replace('.png', '_UNCROPPED.png')
        im.save(os.path.join(frames_dir, name))
    if os.path.exists(os.path.join(d, 'frametimes.csv')):
        shutil.copy(os.path.join(d, 'frametimes.csv'), frames_dir)
    done = json.load(open(os.path.join(d, 'done.json'))) if os.path.exists(os.path.join(d, 'done.json')) else {'reason': 'NO done.json'}
    with open(log_path, encoding='utf-8', errors='replace') as fh:
        fh.seek(log_off)
        burst_log = fh.read().splitlines()
    out = [f'One EXCLUSIVE PIE burst: driver ended with `{done["reason"]}` at {done.get("t", "?")} s; EXCLUSIVE held '
           f'{held:.0f} s. Shots requested {len(shots)}, screenshot files {len(new)}. Frames: `{frames_dir}`.',
           'Input: the title any-key and the menu start are driven by calling BP_FoAFrontEnd.OnTitleConfirmed and '
           '.WakeUp (the handlers those inputs call); no OS key events are injected.',
           f'Frames are `Shot showui` window captures cropped to the PIE viewport rect {shots[0].get("vp") if shots else None} '
           '(absolute px); the uncropped captures are in frames/raw.',
           'Frame times are the editor slate tick in PIE (all lanes connected), not a packaged build.', '',
           '## Beats', ''] + [f'- {s["name"]} at {s["t"]} s: phase {s["phase"]}, screen {s.get("screen")}, '
                              f'gameplay {s.get("in_gameplay")}, wake cine {s.get("wake_cine")}, beat {s.get("beat")}'
                              for s in shots]
    out += ['', '## Checks', '']
    lines, fails = run_checks(frames_dir, args, d)
    out += lines
    sec, f2, _ = logs_section(burst_log, f'Log during this burst ({len(burst_log)} lines)', T['warn_threshold'])
    out += ['', '## Log'] + [''] + sec
    out += ['## Perf', ''] + perf_lines(os.path.join(d, 'frametimes.csv'))
    print('\n'.join(out))
    write_report(d, 'QA pie-smoke', out)
    return 1 if fails + f2 else 0


def cmd_checks(args):
    d = run_dir()
    lines, fails = run_checks(args[0], args[1:], d)
    print('\n'.join(lines))
    write_report(d, f'QA checks on {args[0]}', lines)
    return 1 if fails else 0


# ---------------------------------------------------------------- selftest + fixtures

def cmd_selftest(args):
    spec = json.load(open(os.path.join(FIX, 'fixtures.json'), encoding='utf-8'))
    d = run_dir()
    out, bad = [], 0
    for i, fx in enumerate(spec):
        c, tag = fx['check'], f'{i:02d}_{fx["check"]}'
        if c == 'a':
            ok, msg = check_menu_words(load(os.path.join(FIX, fx['img'])), fx['region'], d, tag)
        elif c == 'b':
            ok, msg = check_title_contrast(load(os.path.join(FIX, fx['img'])), fx['region'], d, tag)
        elif c == 'c':
            ok, msg = check_no_ui(load(os.path.join(FIX, fx['img'])), fx['regions'], d, tag)
        elif c == 'd':
            ok, msg = check_sand(load(os.path.join(FIX, fx['img'])), load(os.path.join(FIX, fx['mask']))[..., 0] > 0.5, d, tag)
        elif c == 'e':
            beats = json.load(open(os.path.join(FIX, fx['beats']), encoding='utf-8'))
            ok, msg = check_motion(sorted(glob.glob(os.path.join(FIX, fx['seq'], '*.png'))), beats, d, tag)
        else:
            ok, msg = check_frametime(os.path.join(FIX, fx['csv']))
        got = verdict(ok)
        match = got == fx['expect']
        bad += not match
        what = fx.get('img') or fx.get('beats') or fx.get('csv')
        out.append(f'{"ok  " if match else "MISMATCH"} ({c}) {what:<34} expect {fx["expect"]:<4} got {got:<4} {msg}')
    out.append(f'selftest: {len(spec) - bad}/{len(spec)} fixtures behave as expected' + ('' if not bad else f'; {bad} MISMATCH'))
    print('\n'.join(out))
    write_report(d, 'QA selftest', ['```'] + out + ['```'])
    return 1 if bad else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    cmds = {'logs': cmd_logs, 'pie-smoke': cmd_pie_smoke, 'checks': cmd_checks, 'perf': cmd_perf, 'selftest': cmd_selftest}
    if a and a[0] == 'fixtures':
        import make_fixtures  # same folder
        sys.exit(make_fixtures.main())
    if not a or a[0] not in cmds:
        sys.exit(__doc__)
    sys.exit(cmds[a[0]](a[1:]))
