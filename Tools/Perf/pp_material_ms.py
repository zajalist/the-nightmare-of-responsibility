"""atmosphere lane: the post-process material lines of every profilegpu dump in a perf_run game log, per moment.
  python Tools/Perf/pp_material_ms.py <run dir> [<run dir> ...]
perf_driver logs a 'profilegpu' row (moment, preset) right before each dump; the dump's
"PostProcessMaterial WxH Material=M_..." rows give each post material's GPU ms (inclusive column)."""
import json
import re
import sys
from pathlib import Path

ROW = re.compile(r'([0-9.]+) ms ┃\s+PostProcessMaterial (\d+x\d+) Material=(M_\w+)')
TAG = re.compile(r'\[perf\] (\{.*"kind": "profilegpu".*\})')


def dumps(run):
    out, moment = [], None
    for line in (Path(run) / 'game.log').read_text(encoding='utf-8', errors='replace').splitlines():
        t = TAG.search(line)
        if t:
            e = json.loads(t.group(1))
            moment = f"{e['moment']} q{e['preset']}"
            out.append([moment, {}])
            continue
        m = ROW.search(line)
        if m and out:
            out[-1][1].setdefault(m.group(3), float(m.group(1)))
    return out


if __name__ == '__main__':
    for run in sys.argv[1:]:
        print(Path(run).name)
        for moment, mats in dumps(run):
            print(f'  {moment:22s}', '  '.join(f'{k} {v:.3f}' for k, v in sorted(mats.items())))
