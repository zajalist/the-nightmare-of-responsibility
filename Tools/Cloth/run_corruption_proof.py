"""Coordinator-owned cloth/smoke regression, bounded to 35 seconds."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner=os.environ.get('FOA_AGENT','main:finish');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'Existing PIE is not ours'
lease=h.lease_acquire(owner,['global'],ttl_s=45,wait_s=3);started=False
prefs=Path('Saved/SaveGames/Settings.sav');original=prefs.read_bytes() if prefs.exists() else None
out=Path('Saved/ClothShots/runtime/report.json')
def call(cmd,**args):
    r=h.call(cmd,args,owner=owner,lease=lease,timeout=12);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User started PIE while waiting'
    out.unlink(missing_ok=True)
    started=call('editor_start_pie').get('pie_started',False);assert started
    clock_report=Path('Saved/Integration/clock_runtime.json')
    clock_report.unlink(missing_ok=True)
    call('python_exec_file',path='P:/FoA/Tools/Unreal/gameplay/pie_clock_tick.py',env={},resources=['global'])
    call('python_exec_file',path='P:/FoA/Tools/Cloth/pie_corruption_proof.py',env={},resources=['global'])
    deadline=time.monotonic()+35
    while not out.exists() and time.monotonic()<deadline:time.sleep(.2)
    assert out.exists(),'Cloth proof timeout'
    data=json.loads(out.read_text());assert data['error'] is None,data
    clock=json.loads(clock_report.read_text());assert clock['error'] is None,clock
    print(json.dumps({'error':data['error'],'shots':data['shots'],'samples':len(data['rows']),
                      'peak':max(r['pulse'] for r in data['rows']),'smoke_seen':any(r['smoke'] for r in data['rows'])}))
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        try:
            if started:
                if original is not None:prefs.write_bytes(original)
                elif prefs.exists():prefs.unlink()
        finally:h.release(owner,lease)
