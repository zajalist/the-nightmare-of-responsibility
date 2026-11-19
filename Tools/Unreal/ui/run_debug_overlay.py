"""Coordinator-only40s owned PIE. Refuses user PIE; preserves Settings.sav bytes."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
if sys.argv[1:]!=['--run']:sys.exit('Wait for coordinator PIE clearance; use --run')
owner=os.environ.get('FOA_AGENT','clothing_ui_proof');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=50,wait_s=3);started=False
settings=Path('Saved/SaveGames/Settings.sav');original=settings.read_bytes() if settings.exists() else None
def call(name,**kw):
    r=h.call(name,kw,owner=owner,lease=token,timeout=12);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    root=Path('Saved/PresentationReview');out=root/'debug_runtime.json';request=root/'debug_input.json'
    request.unlink(missing_ok=True);out.unlink(missing_ok=True)
    started=call('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.5);stamp=time.time();sent=0;axis=None
    call('python_exec_file',path='P:/FoA/Tools/Unreal/ui/pie_debug_overlay.py',env={},resources=['global'])
    while time.time()-stamp<40:
        if request.exists():
            try:msg=json.loads(request.read_text())
            except (json.JSONDecodeError,PermissionError):msg={}
            if msg.get('id',0)>sent:
                for event in msg['events']:
                    if 'axis' in event:axis=(event['key'],event['axis'],time.time()+event['seconds'])
                    else:call('editor_pie_press_key',**event)
                sent=msg['id']
        if axis:
            # Decide once: a slow native call can cross expiry after sending 1.
            # Always deliver the explicit zero before dropping the owned axis.
            expired=time.time()>=axis[2]
            call('editor_pie_axis',key=axis[0],value=0 if expired else axis[1])
            if expired:axis=None
        if out.exists():
            result=json.loads(out.read_text());print(json.dumps(result,indent=1))
            assert result['reason']=='debug_real_f9_preservation_passed',result
            break
        time.sleep(.05)
    else:raise TimeoutError('context presentation proof')
finally:
    try:
        if started:
            for key in ('F9','P','Q'):call('editor_pie_press_key',key=key,event='released')
            call('editor_pie_axis',key='Gamepad_RightX',value=0)
            call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if original is None:settings.unlink(missing_ok=True)
            else:settings.write_bytes(original)
        print('Owned debug PIE stopped; lease released')
