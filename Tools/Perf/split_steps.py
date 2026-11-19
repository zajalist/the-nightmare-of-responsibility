"""Re-split a cooked steps run (cooked_driver.py --plan steps) into its step windows and print the table.
  python Tools/Perf/split_steps.py P:/FoA/Saved/Perf/cooked/<run>
GPU own = the sum of the game's own GPU passes (GPU/* incl. Unaccounted). It is the cost to judge: the frame's GPU time
also includes whatever another process (the shared editor) ran on the same GPU in between, shown as the gap."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cooked_driver import split_csv  # noqa: E402

run = Path(sys.argv[1])
wins = [r for r in json.loads((run / 'driver.json').read_text()) if r['kind'] == 'window']
csv = next((run / 'csv').glob('run_q*.csv'))
preset = csv.stem.split('_q')[-1]
rows = [dict(r, preset=preset) for r in split_csv(csv, run / 'game.log', wins)]
(run / 'steps.json').write_text(json.dumps(rows, indent=1))
out = [f'# cooked steps {run.name} (preset {preset})', '',
       '| step | frames | GPU own p50 | GPU own p95 | GPU frame p50 | gap | GT p50 | Frame p50 | hitches > 33 ms | top passes (ms) |',
       '|---|---|---|---|---|---|---|---|---|---|']
for r in rows:
    s = r['stats']
    g = lambda k, q='p50': s.get(k, {}).get(q, '')  # noqa: E731
    gap = round(g('GPUTime') - g('GPUOwn'), 2) if g('GPUTime') != '' and g('GPUOwn') != '' else ''
    top = ', '.join(f'{k} {v}' for k, v in list(s.get('gpu_top', {}).items())[:4])
    out.append(f"| {r['moment']} | {r['frames']} | {g('GPUOwn')} | {g('GPUOwn', 'p95')} | {g('GPUTime')} | {gap} | "
               f"{g('GameThreadTime')} | {g('FrameTime')} | {r['hitches']} | {top} |")
md = '\n'.join(out) + '\n'
(run / 'summary.md').write_text(md)
print(md)
