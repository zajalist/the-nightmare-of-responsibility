"""Texture streaming budget at route points of a cooked steps run (cooked_driver.py --plan steps).
  python Tools/Perf/streaming_budget.py <run dir> [step names ...]
Per window (median): the streaming pool the engine gives streamed textures, what they want, the cached extra, the
non-streaming mips, the share of wanted data loaded (100 = nothing starved, i.e. not over budget) and this game's own
video memory (GPUMem/LocalUsedMB is per process; the budget column is what Windows grants it on this shared card)."""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cooked_driver import log_epoch  # noqa: E402
from perf_run import read_csv  # noqa: E402

run = Path(sys.argv[1])
only = sys.argv[2:]
lines = (run / 'game.log').read_text(encoding='utf-8', errors='replace').splitlines()
start = next(log_epoch(l) for l in lines if l.endswith('t.MaxFPS = "0"'))
wins = [r for r in json.loads((run / 'driver.json').read_text()) if r['kind'] == 'window']
cols = read_csv(next((run / 'csv').glob('run_q*.csv')))
t, ends = start, []
for ms in cols['FrameTime']:
    t += ms / 1000
    ends.append(t)
keys = ['TextureStreaming/StreamingPool', 'TextureStreaming/WantedMips', 'TextureStreaming/CachedMips',
        'TextureStreaming/NonStreamingMips', 'TextureStreaming/DesiredDataLoadedPercent', 'GPUMem/LocalUsedMB',
        'GPUMem/LocalBudgetMB']
print('step'.ljust(16) + ''.join(k.split('/')[1][:14].rjust(15) for k in keys) + '   min loaded %')
for w in wins:
    if only and w['name'] not in only:
        continue
    idx = [i for i, e in enumerate(ends) if w['t0'] <= e <= w['t1']]
    if not idx:
        continue
    med = [statistics.median(cols[k][i] for i in idx if i < len(cols[k])) if k in cols else float('nan') for k in keys]
    low = min(cols['TextureStreaming/DesiredDataLoadedPercent'][i] for i in idx)
    print(w['name'].ljust(16) + ''.join(f'{v:15.0f}' for v in med) + f'{low:15.0f}')
