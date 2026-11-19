"""Coordinator-cleared owned <=35s PIE window; exact preferences restored on every exit."""
import json,os,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
assert sys.argv[1:]==['--run'],'Requires an explicit root-coordinated slot'
owner='room_walk_contact';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=45,wait_s=3);started=False;result=None
pref=Path('Saved/SaveGames/Settings.sav');saved=pref.read_bytes() if pref.exists() else None
def call(cmd,**args):
    r=h.call(cmd,args,owner=owner,lease=token,timeout=10);assert r.get('ok'),r;return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running']
    started=call('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.4);stamp=time.time()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_walk_contact.py',env={},resources=['global'])
    output=Path('Saved/CharacterShots/walk_contact/latest.json')
    while time.time()-stamp<33:
        if output.exists() and output.stat().st_mtime>=stamp:
            try:result=json.loads(output.read_text())
            except (ValueError,PermissionError):time.sleep(.1);continue
            print(json.dumps(result),flush=True);break
        time.sleep(.15)
    else:raise TimeoutError('Walking contact capture')
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if saved is not None:pref.write_bytes(saved)
            elif pref.exists():pref.unlink()
        print('WALK CONTACT GLOBAL RELEASED',flush=True)
assert result and result['reason']=='captured_requires_contact_and_visual_review',result
subprocess.run([sys.executable,'Tools/Unreal/player/analyze_walk_contact.py',result['folder']],check=True)
