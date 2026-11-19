"""Root-coordinated normal wake proof; always stop owned PIE and release."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
assert sys.argv[1:]==['--run'],'Pass --run only for a coordinator-owned review'
owner='character_underarm_probe';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=60,wait_s=3);started=False
prefs=Path('Saved/SaveGames/Settings.sav');original=prefs.read_bytes() if prefs.exists() else None
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token,timeout=10);assert r.get('ok'),r
    return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    started=call('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.3);stamp=time.time()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_underarm_normal_probe.py',env={},resources=['global'])
    f=Path('P:/FoA/Saved/CharacterShots/wake_handoff/latest.json');deadline=time.time()+48
    while time.time()<deadline:
        if f.exists() and f.stat().st_mtime>=stamp:
            data=json.loads(f.read_text());print(json.dumps(dict(reason=data['reason'],folder=data['folder'],shots=data['shots'])))
            assert data['reason']=='underarm_normal_probe_passed',data['reason'];break
        time.sleep(.15)
    else:raise TimeoutError('normal wake proof')
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if original is not None:prefs.write_bytes(original)
            elif prefs.exists():prefs.unlink()
        print('PIE STOPPED; GLOBAL RELEASED')

