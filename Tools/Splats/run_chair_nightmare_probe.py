"""Bounded coordinator-cleared proof; stops only its own PIE session."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner=os.environ.get('FOA_AGENT','character');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'Existing PIE belongs to someone else'
lease=h.lease_acquire(owner,['global'],ttl_s=50,wait_s=3);started=False
def call(cmd,**params):
    r=h.call(cmd,params,owner=owner,lease=lease,timeout=15);assert r.get('ok'),r
    return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running'],'Existing PIE belongs to someone else'
    focused='--groom' in sys.argv
    out=Path('P:/FoA/Saved/CharacterShots/groom_pose/done.txt' if focused else 'P:/FoA/Saved/WorldShots/chair_nightmare/done.txt')
    out.unlink(missing_ok=True)
    call('editor_start_pie');started=True;time.sleep(.5)
    call('python_exec_file',path='P:/FoA/Tools/MPFB/ue_groom_pose_probe.py' if focused else 'P:/FoA/Tools/Splats/chair_nightmare_probe.py',env={},resources=['global'])
    deadline=time.monotonic()+32
    while not out.exists() and time.monotonic()<deadline:time.sleep(.2)
    assert out.exists(),'Proof timeout'
    r=json.loads(out.with_name('report.json' if focused else 'runtime.json').read_text());print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=1))
finally:
    if started:call('editor_stop_pie')
    h.release(owner,lease);print('Owned PIE stopped; lease released')
