"""Frame-time table from a CsvProfiler capture (world lane perf proof).
  python Tools/Lux3D/csv_frames.py Saved/WorldShots/perf/<run>.csv [--from-event "<substring>"] [--to-event "<substring>"]
Prints median / p95 / p99 / max and the count of frames over 16.6, 33.3 and 50 ms for FrameTime, GameThreadTime,
RenderThreadTime and GPUTime (whichever columns exist), between two CSV events (default: the whole capture)."""
import argparse
import csv

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('csv')
ap.add_argument('--from-event', default='')
ap.add_argument('--to-event', default='')
a = ap.parse_args()
rows = list(csv.reader(open(a.csv, encoding='utf-8', errors='replace')))
if rows[-1] and rows[-1][0] == '[HasHeaderRowAtEnd]':   # stats added mid-capture: the full header is the last-but-one row
    head, body = rows[-2], rows[1:-2]
else:
    head, body = rows[0], rows[1:]
data = [r for r in body if len(r) >= head.index('FrameTime') + 1]
ncol = len(head)
data = [r + [''] * (ncol - len(r)) for r in data]   # early rows lack the late columns (left blank)
ev = head.index('EVENTS') if 'EVENTS' in head else None
lo, hi = 0, len(data)
if ev is not None and a.from_event:
    lo = next((i for i, r in enumerate(data) if a.from_event in r[ev]), 0)
if ev is not None and a.to_event:
    hi = next((i for i, r in enumerate(data) if i > lo and a.to_event in r[ev]), len(data))
data = data[lo:hi]
print(f'frames {len(data)} ({a.from_event or "start"} -> {a.to_event or "end"})')
print(f'{"stat":18s} {"median":>7s} {"p95":>7s} {"p99":>7s} {"max":>7s} {">16.6":>6s} {">33.3":>6s} {">50":>5s}')
for col in ('FrameTime', 'GameThreadTime', 'RenderThreadTime', 'RHIThreadTime', 'GPUTime'):
    if col not in head:
        continue
    v = np.array([float(r[head.index(col)] or 0) for r in data])
    if not v.size:
        continue
    print(f'{col:18s} {np.median(v):7.2f} {np.percentile(v, 95):7.2f} {np.percentile(v, 99):7.2f} {v.max():7.2f} '
          f'{(v > 16.6).sum():6d} {(v > 33.3).sum():6d} {(v > 50).sum():5d}')
