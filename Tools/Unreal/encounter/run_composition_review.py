"""Own only this bounded PIE run; restore exact preferences and stop on every exit."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
assert sys.argv[1:]==['--run']
owner='main:presentation';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=65,wait_s=3);started=False
prefs=Path('Saved/SaveGames/Settings.sav');old=prefs.read_bytes() if prefs.exists() else None
out=Path('Saved/PresentationReview/battle_runtime.json');req=out.with_name('battle_input.json')
def c(cmd,**kw):
    r=h.call(cmd,kw,owner=owner,lease=token,timeout=12);assert r.get('ok'),r
    return r.get('data',{})
try:
    assert not c('editor_get_state')['pie_running']
    out.unlink(missing_ok=True);req.unlink(missing_ok=True)
    started=c('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.5);stamp=time.time()
    c('python_exec_file',path='P:/FoA/Tools/Unreal/encounter/pie_composition_review.py',env={},resources=['global'])
    sent=0
    while time.time()-stamp<60:
        if req.exists():
            try:r=json.loads(req.read_text())
            except (ValueError,PermissionError):r={}
            if r.get('id',0)>sent:
                print('input',r,c('editor_pie_press_key',key=r['key'],held_ms=70),flush=True);sent=r['id']
        if out.exists():
            try:r=json.loads(out.read_text())
            except (ValueError,PermissionError):time.sleep(.05);continue
            print(json.dumps({'reason':r['reason'],'screens':r['screens'],'last':r['rows'][-3:]},indent=1))
            assert r['reason']=='battle_presentation_and_native_input_passed',r['reason'];break
        time.sleep(.12)
    else:raise TimeoutError('Battle review timed out')
finally:
    try:
        if started:c('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if old is not None:prefs.write_bytes(old)
            elif prefs.exists():prefs.unlink()
        print('Owned review ended; lease released')
