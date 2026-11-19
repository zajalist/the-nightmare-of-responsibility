"""Coordinator-cleared, bounded PIE burst. Stops only the PIE this harness starts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner='room-takeover'
os.environ['HAYBA_AGENT_ID']=owner
vase='--vase' in sys.argv
clues='--clues' in sys.argv
out=Path('P:/FoA/Saved/WorldShots/'+('pie_vase_boss.json' if vase else 'pie_clue_lighting.json' if clues else 'pie_room_takeover.json'))
assert not h.call('editor_get_state')['data']['pie_running'],'Existing PIE belongs to someone else'
token=h.lease_acquire(owner,['global'],ttl_s=75,wait_s=20)
prefs=Path('P:/FoA/Saved/SaveGames/Settings.sav')
original_prefs=prefs.read_bytes() if prefs.exists() else None
started=False
try:
    assert not h.call('editor_get_state')['data']['pie_running'],'PIE started while waiting for the lease'
    if out.exists():out.unlink()
    reply=h.call('editor_start_pie',{},owner=owner,lease=token);assert reply.get('ok'),reply
    started=True;t=time.time()
    time.sleep(2)
    probe='Tools/Splats/'+('pie_vase_boss.py' if vase else 'pie_clue_lighting.py' if clues else 'pie_room_takeover.py')
    p=subprocess.run([sys.executable,'Tools/Unreal/integration/run_read.py',probe],capture_output=True,text=True,timeout=15)
    print(p.stdout,p.stderr,flush=True);assert p.returncode==0
    while not out.exists() and time.time()-t<(28 if vase else 42):time.sleep(.5)
    assert out.exists(),'Proof timeout'
    events=json.loads(out.read_text())
    print(json.dumps([e for e in events if e['kind']!='sample'],indent=1),flush=True)
    assert events[-1]['kind']=='complete',events[-1]
finally:
    if started:print('Stopped owned PIE:',h.call('editor_stop_pie',{},owner=owner,lease=token).get('ok'),flush=True)
    if started:
        if original_prefs is not None:prefs.write_bytes(original_prefs)
        elif prefs.exists():prefs.unlink()
        print('Restored pre-test settings exactly',flush=True)
    h.release(owner,token)
