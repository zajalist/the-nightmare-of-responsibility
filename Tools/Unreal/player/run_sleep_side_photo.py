"""Own one bounded photo session, leave user PIE alone, always release the lease."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner=os.environ.get('FOA_AGENT','sleep-side-photo');lease=h.lease_acquire(owner,['global'],ttl_s=45,wait_s=3);started=False
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=lease,timeout=10);assert r.get('ok'),r
    return r.get('data',{})
try:
    state=call('editor_get_state');assert not state['pie_running'],'User PIE active'
    assert not [p for p in state.get('dirty_packages',[]) if '/Maps/' not in p],state
    call('editor_start_pie');started=True;time.sleep(.4);stamp=time.time()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_sleep_side_photo.py',env={},resources=['global'])
    f=Path('P:/FoA/Saved/CharacterShots/sleep_side/latest.json');deadline=time.time()+27
    while time.time()<deadline:
        if f.exists() and f.stat().st_mtime>=stamp:
            result=json.loads(f.read_text());print(json.dumps(result,indent=1));break
        time.sleep(.2)
    else:raise TimeoutError('side photo')
finally:
    if started:call('editor_stop_pie')
    h.release(owner,lease);print('GLOBAL RELEASED; photo only, no FPS/priority changes')
