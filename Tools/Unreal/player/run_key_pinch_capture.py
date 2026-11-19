"""Coordinator-cleared35s key capture. Refuses existing user PIE and always releases."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
if sys.argv[1:]!=['--run']:sys.exit('Run only after coordinator clears an exclusive PIE window: --run')
owner=os.environ.get('FOA_AGENT','clothing_key_capture');os.environ['HAYBA_AGENT_ID']=owner
token=h.lease_acquire(owner,['global'],ttl_s=40,wait_s=3);started=False
settings=Path('Saved/SaveGames/Settings.sav');original=settings.read_bytes() if settings.exists() else None
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token,timeout=12);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    path=Path('Saved/Integration/key_pinch_capture.json');boot=Path('Saved/Integration/key_pinch_bootstrap.json')
    path.unlink(missing_ok=True);boot.unlink(missing_ok=True)
    started=call('editor_start_pie').get('pie_started',False);assert started
    stamp=time.time();time.sleep(.5)
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_key_pinch_bootstrap.py',env={},resources=['global'])
    while time.time()-stamp<32:
        if boot.exists() and boot.stat().st_mtime>=stamp:
            state=json.loads(boot.read_text());assert state['reason']=='actual_FE_ready',state
        if path.exists() and path.stat().st_mtime>=stamp:
            try:result=json.loads(path.read_text())
            except (json.JSONDecodeError,PermissionError):time.sleep(.05);continue
            if result['status']=='complete':
                assert result['reason']=='captured_three_actual_key_poses',result
                assert len(result['rows'])==3 and all('Body' in row and 'Mesh' in row for row in result['rows']),result
                print(json.dumps(result,indent=1));break
        time.sleep(.2)
    else:raise TimeoutError('key pinch capture')
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if original is not None:settings.write_bytes(original)
            elif settings.exists():settings.unlink()
        print('Owned key PIE stopped and lease released')
