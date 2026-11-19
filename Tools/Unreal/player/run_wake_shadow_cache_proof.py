"""Natural wake A/B: disable only VSM cache, then restore its exact prior runtime value."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
assert sys.argv[1:]==['--run'];owner='character_shadow_proof';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=60,wait_s=3);started=False;prior=None;data=None
pref=Path('Saved/SaveGames/Settings.sav');saved=pref.read_bytes() if pref.exists() else None
def call(cmd,**args):
    r=h.call(cmd,args,owner=owner,lease=token,timeout=10);assert r.get('ok'),r;return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running']
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/qa_shadow_cache_value.py',env={'FOA_SHADOW_VALUE':'0'},resources=['global'])
    prior=json.loads(Path('Saved/Integration/cinematic_audit/shadow_cache_value.json').read_text())['prior']
    started=call('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.3);stamp=time.time()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_wake_handoff_capture.py',env={},resources=['global'])
    path=Path('Saved/CharacterShots/wake_handoff/latest.json');deadline=time.monotonic()+44
    while time.monotonic()<deadline:
        if path.exists() and path.stat().st_mtime>=stamp:
            data=json.loads(path.read_text());assert data['reason']=='natural_wake_handoff_passed',data['reason'];print(data['folder']);break
        time.sleep(.15)
    else:raise TimeoutError('Natural wake cache comparison')
finally:
    try:
        try:
            if started:print('PIE_STOP',call('editor_stop_pie'))
        finally:
            if prior is not None:
                call('python_exec_file',path='P:/FoA/Tools/Unreal/player/qa_shadow_cache_value.py',env={'FOA_SHADOW_VALUE':str(prior)},resources=['global'])
                restored=json.loads(Path('Saved/Integration/cinematic_audit/shadow_cache_value.json').read_text())['actual'];assert restored==prior
                receipt=dict(prior=prior,comparison=0,restored=restored,folder=data['folder'] if data else None)
                Path('Saved/Integration/cinematic_audit/wake_shadow_cache.json').write_text(json.dumps(receipt,indent=2));print(receipt)
    finally:
        h.release(owner,token)
        if started:
            if saved is not None:pref.write_bytes(saved)
            elif pref.exists():pref.unlink()
        print('SHADOW PROOF GLOBAL RELEASED')
