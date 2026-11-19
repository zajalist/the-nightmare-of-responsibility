"""Coordinator-cleared <=45s owned PIE, exact preferences restoration and guaranteed release."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
if sys.argv[1:]!=['--run']:sys.exit('Requires coordinator-cleared exclusive window: --run')
owner=os.environ.get('FOA_AGENT','character_screw_contact');os.environ['HAYBA_AGENT_ID']=owner
token=h.lease_acquire(owner,['global'],ttl_s=48,wait_s=3);started=False
settings=Path('Saved/SaveGames/Settings.sav');original=settings.read_bytes() if settings.exists() else None
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token,timeout=12);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    path=Path('Saved/Integration/screwdriver_contact_final.json');boot=Path('Saved/Integration/screwdriver_bootstrap.json')
    path.unlink(missing_ok=True);boot.unlink(missing_ok=True)
    started=call('editor_start_pie').get('pie_started',False);assert started
    stamp=time.time();time.sleep(.5)
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_screwdriver_bootstrap.py',env={},resources=['global'])
    while time.time()-stamp<44:
        if boot.exists():
            try:state=json.loads(boot.read_text())
            except (json.JSONDecodeError,PermissionError):time.sleep(.05);continue
            assert state['reason']=='actual_FE_ready',state
        if path.exists():
            try:result=json.loads(path.read_text())
            except (json.JSONDecodeError,PermissionError):time.sleep(.05);continue
            if result['status']=='complete':
                print(json.dumps(result.get('checks'),indent=1));print(result['folder'])
                assert result['reason']=='four_screws_contact_and_release_passed',result['reason'];break
        time.sleep(.2)
    else:raise TimeoutError('screwdriver contact proof')
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if original is not None:settings.write_bytes(original)
            elif settings.exists():settings.unlink()
        print('Owned screwdriver PIE stopped and lease released')
