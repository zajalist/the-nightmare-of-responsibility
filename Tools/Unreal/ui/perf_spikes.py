"""Spike table for a measuring sweep (sweep_intro.py <dir> perf).
  python Tools/Unreal/ui/perf_spikes.py <sweep dir> [--log Saved/Logs/FoA.log]
Reads <dir>/frametimes.csv (wall t since the recorder armed, ms, PIE time) and <dir>/shots.json (t0 epoch), cuts the run's
segment out of the editor log into <dir>/run_log.txt, and writes <dir>/spikes.md: every frame over 50 ms with its PIE time,
the matching `stat dumphitches` tree's biggest self-time stats, and the log lines logged around it (shader or PSO
compiles, GC, package loads, texture streaming, Blueprint errors). Percentiles come from QA check (f) itself."""
import csv
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, 'P:/FoA/Tools/QA')
import foa_qa  # noqa: E402

HITCH_MS = 50.0
NEAR_S = 0.35
TAGS = re.compile(r'Shader|PSO|Pipeline|Garbage|GC |LoadPackage|Flush|Streaming|Texture|Async|Compil|Hitch|Error|Warning|'
                  r'Accessed None|Blueprint', re.I)
STAMP = re.compile(r'^\[(\d{4})\.(\d\d)\.(\d\d)-(\d\d)\.(\d\d)\.(\d\d):(\d{3})\]')


def stamp(line):
    m = STAMP.match(line)
    if not m:
        return None
    y, mo, d, h, mi, s, ms = (int(v) for v in m.groups())
    return dt.datetime(y, mo, d, h, mi, s, ms * 1000, tzinfo=dt.timezone.utc).timestamp()


def main(d, log_path):
    t0 = json.load(open(os.path.join(d, 'shots.json')))['t0']
    rows = list(csv.DictReader(open(os.path.join(d, 'frametimes.csv'), encoding='utf-8')))
    frames = [(t0 + float(r['t']), float(r['ms']), float(r['pie_t'])) for r in rows]
    if not frames:
        print('no frames'); return
    a, b = frames[0][0] - 2, frames[-1][0] + 2
    seg, last = [], None
    for ln in open(log_path, encoding='utf-8', errors='replace'):
        e = stamp(ln)
        last = e if e is not None else last
        if last is not None and a <= last <= b:
            seg.append((last, ln.rstrip('\n')))
    with open(os.path.join(d, 'run_log.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(ln for _, ln in seg))
    hitch_log = os.path.join(d, 'run_log.txt')
    _, causes_all = foa_qa.dumphitches(hitch_log)
    ok, msg = foa_qa.check_frametime(os.path.join(d, 'frametimes.csv'))
    out = [f'# Frame-time spikes, {os.path.basename(d)}', '', f'QA (f): {"PASS" if ok else "FAIL"}, {msg}', '',
           'In-editor PIE: editor Slate and the editor viewport share the game thread, so absolute numbers run high; '
           'the spikes are what matter.', '',
           '| PIE s | ms | hitch tree, biggest self times | log around it |', '|---|---|---|---|']
    spikes = [f for f in frames if f[1] > HITCH_MS]
    for wall, ms, pie in spikes:
        near = [ln for e, ln in seg if abs(e - wall) <= NEAR_S and TAGS.search(ln) and 'LogHaybaMCP' not in ln]
        tree = hitch_tree(seg, wall)
        notes = '; '.join(re.sub(r'^\[[^\]]*\]\[[^\]]*\]', '', n)[:110] for n in near[:4]) or 'nothing logged'
        out.append(f'| {pie:.2f} | {ms:.0f} | {tree or "no dump"} | {notes.replace("|", "/")} |')
    out += ['', f'{len(spikes)} frames over {HITCH_MS:.0f} ms of {len(frames)}.', '',
            'Self time summed over every hitch dump in the run:', '']
    out += [f'- {name}: {v:.1f} ms' for name, v in causes_all.most_common(15)]
    open(os.path.join(d, 'spikes.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('\n'.join(out[:60]))


def hitch_tree(seg, wall):
    """The `stat dumphitches` block logged closest after this frame: its 4 biggest self-time stats."""
    best = None
    for i, (e, ln) in enumerate(seg):
        if 0 <= e - wall <= 0.6 and re.search(r'Thread Hitch \d+, Frame \d+', ln):
            best = i
            break
    if best is None:
        return ''
    selfs, stack = [], []
    for e, ln in seg[best + 1:best + 400]:
        if 'LogStats:' not in ln or re.search(r'Thread Hitch', ln):
            if re.search(r'Thread Hitch', ln):
                break
            continue
        body = ln.split('LogStats:', 1)[1]
        m = re.match(r'(\s*)([\d.]+)ms \(\s*\d+\)\s+-\s+(.*)', body)
        if not m:
            continue
        depth, ms, name = len(m.group(1)), float(m.group(2)), m.group(3).split(' - ')[0].strip()
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if name == 'Self' and stack and not re.search(r'wait|idle|FrameTime|Thread_|GameThread', stack[-1][1], re.I):
            selfs.append((ms, stack[-1][1]))
        stack.append((depth, name))
    selfs.sort(reverse=True)
    return ', '.join(f'{n[:40]} {v:.0f}' for v, n in selfs[:4])


if __name__ == '__main__':
    lp = sys.argv[sys.argv.index('--log') + 1] if '--log' in sys.argv else 'P:/FoA/Saved/Logs/FoA.log'
    main(sys.argv[1], lp)
