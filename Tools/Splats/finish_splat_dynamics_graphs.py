"""Replay the prepared layouts and capture each graph under one asset lease."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

os.environ.update(FOA_AGENT='splat-vfx', HAYBA_AGENT_ID='splat-vfx', FOA_AREAS='/Game/FoA/Level2')
os.environ.pop('FOA_EXCLUSIVE', None)
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock
import hayba_call as h
from build_splat_dynamics import call, require_lease

OUT = Path('P:/FoA/Saved/Codex/splat_dynamics')


def inspect(step, **args):
    h.renew_all('splat-vfx', 90)
    subprocess.run([sys.executable, 'Tools/Unreal/ue_remote.py', 'Tools/Splats/splat_dynamics_inspect.py',
                    'SPLAT_INSPECT='+step, *[f'{k}={v}' for k, v in args.items()]], check=True)


def run():
    (OUT/'graph_runner.pid').write_text(str(os.getpid()))
    editor_lock.acquire('splat-vfx', areas=['/Game/FoA/Level2'], ttl=90, wait_s=900)
    try:
        require_lease()
        subprocess.run([sys.executable, 'Tools/Unreal/ue_remote.py', 'Tools/Splats/splat_dynamics_sanity.py'], check=True)
        inspect('close')
        for name in ['MF_SplatDynamics', 'M_SplatWorld_Lean', 'M_SplatCity_Lean']:
            plan = json.loads(Path('Saved/GraphLayout', name+'.json').read_text())
            for item in plan['calls']:
                call(item['name'], **item['args'])
            print('SPLAT graph layout', name, flush=True)
        for i in range(4):
            inspect('capture', SPLAT_GRAPH=i)
            time.sleep(2)
        inspect('close')
        inspect('stats')
    finally:
        editor_lock.release('splat-vfx')


if __name__ == '__main__':
    run()
