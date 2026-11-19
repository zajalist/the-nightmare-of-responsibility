"""Frame-time distribution over all measured windows of a cooked steps run: p50/p95/p99 and the share of frames over
16.7 ms (60 fps) and 33 ms. FrameTime is the whole frame on this machine, so it is the CPU-or-GPU-bound result here.
  python Tools/Perf/route_frames.py <run dir>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cooked_driver import log_epoch  # noqa: E402
from perf_run import read_csv  # noqa: E402

run = Path(sys.argv[1])
lines = (run / 'game.log').read_text(encoding='utf-8', errors='replace').splitlines()
start = next(log_epoch(l) for l in lines if l.endswith('t.MaxFPS = "0"'))
wins = [r for r in json.loads((run / 'driver.json').read_text()) if r['kind'] == 'window']
ft = read_csv(next((run / 'csv').glob('run_q*.csv')))['FrameTime']
t, ends = start, []
for ms in ft:
    t += ms / 1000
    ends.append(t)
idx = sorted({i for w in wins for i, e in enumerate(ends) if w['t0'] <= e <= w['t1']})
v = sorted(ft[i] for i in idx)
n = len(v)
p = lambda q: round(v[min(n - 1, int(q * (n - 1)))], 2)  # noqa: E731
over = sum(x > 16.7 for x in v)
print(f'{n} frames in {len(wins)} windows: p50 {p(.5)} ms, p95 {p(.95)}, p99 {p(.99)}, '
      f'over 16.7 ms {over} ({100 * over / n:.2f}%), over 33 ms {sum(x > 33 for x in v)}')
