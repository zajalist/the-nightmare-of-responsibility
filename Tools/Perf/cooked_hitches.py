"""Hitches in a cooked steps run: every frame over a threshold, with wall time, which step window it fell in, game
thread, GPU, level streaming and the PSO precache misses logged within half a second of it.
  python Tools/Perf/cooked_hitches.py P:/FoA/Saved/Perf/cooked/<run> [--ms 33]"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cooked_driver import log_epoch  # noqa: E402
from perf_run import read_csv  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('run')
ap.add_argument('--ms', type=float, default=33)
a = ap.parse_args()
run = Path(a.run)
lines = (run / 'game.log').read_text(encoding='utf-8', errors='replace').splitlines()
start = next(log_epoch(l) for l in lines if l.endswith('t.MaxFPS = "0"'))
pso = [log_epoch(l) for l in lines if 'PSOPrecacheState: Missed' in l]
wins = [r for r in json.loads((run / 'driver.json').read_text()) if r['kind'] == 'window']
cols = read_csv(next((run / 'csv').glob('run_q*.csv')))
ft = cols['FrameTime']
t, rows = start, []
for i, ms in enumerate(ft):
    t += ms / 1000
    if i and ms > a.ms:
        step = next((w['name'] for w in wins if w['t0'] - 6 <= t <= w['t1']), '-')
        get = lambda k: round(cols[k][i], 1) if k in cols and i < len(cols[k]) else None  # noqa: E731
        rows.append(dict(frame=i, utc=datetime.fromtimestamp(t, timezone.utc).strftime('%H:%M:%S.%f')[:-3], ms=round(ms),
                         near_step=step, gt=get('GameThreadTime'), gpu=get('GPUTime'),
                         making_visible=get('LevelStreaming/NumLevelsMakingVisible') if 'LevelStreaming/NumLevelsMakingVisible' in cols else None,
                         async_loading=get('Exclusive/GameThread/AsyncLoading'),
                         pso_missed_near=sum(1 for p in pso if p and abs(p - t) < 0.5)))
print(f'{len(rows)} frames over {a.ms} ms of {len(ft)}; PSO precache misses in the log: {len(pso)}')
for r in rows:
    print(r)
