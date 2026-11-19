"""One explicit authoring step, never queued through maintenance or user play.
Examples: python .../threshold_run.py skeleton | sequences | Begin | Step | setup
No map switching, placement, saving the bedroom, PIE, or background process here.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal']
import threshold_data as D
import editor_lock
import hayba_call as h

def main():
    step=sys.argv[1]
    maintenance=Path('P:/FoA/Saved/FoA_editor.lock')
    if maintenance.exists():
        held=json.loads(maintenance.read_text())
        assert 'MAINTENANCE' not in held.get('owner','') or os.environ.get('FOA_AGENT','').startswith('main-'),held['owner']
    D.OWNER=os.environ.get('FOA_AGENT',D.OWNER)
    os.environ.update(FOA_AGENT=D.OWNER,HAYBA_AGENT_ID=D.OWNER,FOA_AREAS=D.ROOT)
    areas=[D.ROOT]
    if step=='colour':areas.append('/Game/FoA/Level2/M_SplatWorld_Lean')
    scripts={'sequences':'threshold_sequences.py','setup':'threshold_setup.py','probe':'threshold_probe.py'}
    assert step in scripts or step=='colour' or step in __import__('build_threshold').STEPS,step
    editor_lock.acquire(D.OWNER,wait_s=15,ttl=90,areas=[] if step=='sequences' else areas)
    try:
        assert h.leases_of(D.OWNER),'No live lease'
        state=h.call('editor_get_state',timeout=10)
        assert state.get('ok') and not state['data']['pie_running'],state
        if step in scripts:
            cmd=[sys.executable,'Tools/Unreal/ue_remote.py','Tools/Unreal/level2/'+scripts[step]]
        else:
            if step=='colour':
                subprocess.run([sys.executable,'Tools/Unreal/ue_remote.py','Tools/Unreal/level2/threshold_probe.py'],check=True,timeout=20)
            cmd=[sys.executable,'Tools/Unreal/level2/threshold_colour.py'] if step=='colour' else [sys.executable,'Tools/Unreal/level2/build_threshold.py',step]
        result=subprocess.run(cmd,timeout=55)
        assert result.returncode==0,('Step failed',step,result.returncode)
    finally:
        editor_lock.release(D.OWNER)

if __name__=='__main__':main()
