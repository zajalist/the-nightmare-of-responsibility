"""Print the profilegpu dumps in a game log as an indented tree, keeping events above a threshold.
  python Tools/Perf/profilegpu.py <game.log> [--which N] [--min 0.15] [--depth 6]
Each dump has a graphics table and, when async compute ran, a second table (Lumen, VSM page work, TSR prep run
there on this GPU; on GPUs without useful async compute, such as Pascal, that time adds to the frame).
--which: 0-based dump index (perf_driver logs one per (moment, preset) in GPUDUMP order); default all."""
import argparse
import re

ap = argparse.ArgumentParser()
ap.add_argument('log')
ap.add_argument('--which', type=int, action='append')
ap.add_argument('--min', type=float, default=0.15)
ap.add_argument('--depth', type=int, default=6)
a = ap.parse_args()

tables, labels, pending = [], {}, None  # tables: [frame, rows]
for line in open(a.log, encoding='utf-8', errors='replace'):
    m = re.search(r'\[perf\] .*"kind": "profilegpu", "moment": "([^"]+)", "preset": (\d+)', line)
    if m:
        pending = f'{m.group(1)} q{m.group(2)}'
    m = re.search(r'GPU Profile for Frame (\d+)', line)
    if m and pending:
        labels[m.group(1)] = pending
        pending = None
    if '┃' not in line:
        continue
    parts = line.split('┃')
    if len(parts) < 4:
        continue
    excl, incl, name = parts[1], parts[2], parts[3]
    t_in = re.search(r'([\d.]+) ms', incl)
    if not t_in:
        continue
    t_ex = re.search(r'([\d.]+) ms', excl)
    body = name.rstrip()
    stripped = body.lstrip(' ')
    label = stripped.strip('" ')
    if label == '<root>':
        tables.append([None, []])
    if not tables:
        continue
    fm = re.match(r'Frame (\d+)$', label)
    if fm:  # the async table also lists the previous frame's tail: keep the last frame it names
        tables[-1][0] = fm.group(1)
    depth = (len(body) - len(stripped)) // 3  # the tree indents 3 spaces per level
    tables[-1][1].append((depth, float(t_in.group(1)), float(t_ex.group(1)) if t_ex else 0.0,
                          incl.split('│')[0].strip(), label))

frames = []
for frame, rows in tables:
    if frame not in [f for f, _ in frames]:
        frames.append((frame, []))
    dict(frames)[frame].append(rows)
for i, (frame, group) in enumerate(frames):
    if a.which and i not in a.which:
        continue
    print(f'== dump {i}: {labels.get(frame, "?")} (frame {frame})')
    for rows in sorted(group, key=lambda r: r[0][3] in ('0', '')):  # graphics (draws > 0) first
        print('  -- async compute (overlaps graphics on this GPU)' if rows[0][3] in ('0', '') else '  -- graphics')
        base = min((r[0] for r in rows), default=0)
        for depth, t_in, t_ex, draws, name in rows:
            if t_in >= a.min and depth - base <= a.depth:
                print(f'  {"  " * (depth - base)}{t_in:7.3f} ms (self {t_ex:.3f}, draws {draws})  {name[:100]}')
