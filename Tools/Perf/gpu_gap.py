"""Contention check for a cooked steps run: per window, GPU frame time p50 against the sum of this frame's own GPU
passes (every GPU/* column, including Unaccounted). A large gap means the GPU was busy with another process (the
shared editor) during the window, so its GPU time is inflated.
  python Tools/Perf/gpu_gap.py P:/FoA/Saved/Perf/cooked/<run> [step names ...]"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cooked_driver import log_epoch  # noqa: E402
from perf_run import read_csv  # noqa: E402

run = Path(sys.argv[1])
only = set(sys.argv[2:])
lines = (run / 'game.log').read_text(encoding='utf-8', errors='replace').splitlines()
start = next(log_epoch(l) for l in lines if l.endswith('t.MaxFPS = "0"'))
wins = [r for r in json.loads((run / 'driver.json').read_text()) if r['kind'] == 'window']
cols = read_csv(next((run / 'csv').glob('run_q*.csv')))
gpu_cols = [k for k in cols if k.startswith('GPU/')]
t, ends = start, []
for ms in cols['FrameTime']:
    t += ms / 1000
    ends.append(t)
for w in wins:
    if only and w['name'] not in only:
        continue
    idx = [i for i, e in enumerate(ends) if w['t0'] <= e <= w['t1']]
    if not idx:
        continue
    total = statistics.median(cols['GPUTime'][i] for i in idx)
    own = statistics.median(sum(cols[k][i] for k in gpu_cols if i < len(cols[k])) for i in idx)
    print(f"{w['name']:18} GPU p50 {total:6.2f}  own passes {own:6.2f}  gap {total - own:6.2f}")
