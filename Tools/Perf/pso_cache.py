"""Build the bundled PSO cache from cooked-game recordings.
  python Tools/Perf/pso_cache.py --build P:/FoA-Builds/<Development build> [--shk <dir with *.shk>]
1. Recordings: cooked_driver.py --plan steps --logpso writes <build>/Windows/FoA/Saved/CollectedPSOs/*.rec.upipelinecache.
2. Stable shader keys: the cook of that build (pack.sh sets NeedsShaderStableKeys in the pack mirror) writes
   P:/FoA-PackMirror/Saved/Cooked/Windows/FoA/Metadata/PipelineCaches/*.shk. A later cook overwrites them, so they are
   copied next to the recordings first (--shk keeps an earlier copy).
3. ShaderPipelineCacheTools expand (an editor commandlet on the pack mirror, never on P:/FoA) turns recordings and
   keys into P:/FoA/Build/Windows/PipelineCaches/PSO_FoA_PCD3D_SM6.spc, which the next package bundles as
   FoA_PCD3D_SM6.stable.upipelinecache. Build/ is gitignored: the file lives on disk for packaging.
The commandlet exits 1 because the project's Hayba startup script can't import in the pack mirror (Hayba is left out
of it on purpose); success is judged from its log line 'Generated N stable PSOs' and the .spc file."""
import argparse
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

CMD = r'C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
MIRROR_SHK = Path('P:/FoA-PackMirror/Saved/Cooked/Windows/FoA/Metadata/PipelineCaches')
OUT = Path('P:/FoA/Build/Windows/PipelineCaches/PSO_FoA_PCD3D_SM6.spc')

ap = argparse.ArgumentParser()
ap.add_argument('--build', required=True)
ap.add_argument('--shk', help='folder with ShaderStableInfo-*-PCD3D_SM6.shk (default: copy them from the pack mirror)')
a = ap.parse_args()
work = Path('P:/FoA/Saved/Perf/pso') / datetime.now().strftime('%Y%m%d_%H%M')
work.mkdir(parents=True, exist_ok=True)
shk = Path(a.shk) if a.shk else work / 'shk'
if not a.shk:
    shk.mkdir(exist_ok=True)
    for f in MIRROR_SHK.glob('*.shk'):
        shutil.copy2(f, shk / f.name)
recs = sorted((Path(a.build) / 'Windows/FoA/Saved/CollectedPSOs').glob('*PCD3D_SM6*.rec.upipelinecache'))
keys = sorted(shk.glob('*PCD3D_SM6.shk'))
assert recs, 'no PSO recordings in the build'
assert keys, f'no SM6 stable shader keys in {shk}'
spc = work / OUT.name
log = work / 'expand.log'
subprocess.run([CMD, 'P:/FoA-PackMirror/FoA.uproject', '-run=ShaderPipelineCacheTools', 'expand',
                *map(str, recs), *map(str, keys), str(spc), '-unattended', '-nopause', f'-abslog={log}'],
               capture_output=True)
text = log.read_text(encoding='utf-8', errors='replace')
m = re.search(r'Generated (\d+) stable PSOs', text)
assert m and spc.exists() and spc.stat().st_size > 0, f'expand failed, see {log}'
OUT.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(spc, OUT)
loaded = re.findall(r'Loaded (\d+) PSOs total', text)
print(f'{len(recs)} recordings ({loaded[-1] if loaded else "?"} PSOs) + {len(keys)} key files -> {m.group(1)} stable PSOs, '
      f'{OUT.stat().st_size / 1024:.0f} KB at {OUT}')
