"""Print the biggest columns of one or more perf CSVs (mean ms), grouped by prefix.
  python Tools/Perf/csv_top.py <csv> [<csv> ...] [--prefix Exclusive/GameThread/] [--n 15]"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from perf_run import read_csv  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('csv', nargs='+')
ap.add_argument('--prefix', action='append', default=[])
ap.add_argument('--n', type=int, default=15)
a = ap.parse_args()
prefixes = a.prefix or ['GPU/', 'Exclusive/GameThread/', 'Exclusive/RenderThread/', '']
for path in a.csv:
    cols = read_csv(path)
    print(f'== {Path(path).name} ({len(cols.get("FrameTime", []))} frames)')
    for pre in prefixes:
        items = [(k, statistics.mean(v)) for k, v in cols.items() if k.startswith(pre) and v and
                 (pre or '/' not in k)]
        items.sort(key=lambda kv: -kv[1])
        print(f'  [{pre or "top-level"}] ' + ', '.join(f'{k[len(pre):]} {v:.2f}' for k, v in items[:a.n]))
