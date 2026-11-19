"""Coordinator-only bounded PIE; refuses existing user PIE and restores preference bytes."""
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
if sys.argv[1:] != ['--run']:
    sys.exit('Held during manual pose editing. Pass --run only in a coordinator-cleared PIE window.')
owner=os.environ.get('FOA_AGENT','clothing_proof');os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
sky_first=os.environ.get('FOA_SKY_FIRST')=='1'
token=h.lease_acquire(owner,['global'],ttl_s=140 if sky_first else 100,wait_s=3);started=False
prefs=Path('Saved/SaveGames/Settings.sav');original=prefs.read_bytes() if prefs.exists() else None
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token,timeout=15);assert r.get('ok'),r
    return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    started=call('editor_start_pie').get('pie_started',False)
    assert started,'PIE was not started by this proof'
    time.sleep(.5);stamp=time.time()
    inputs=Path('Saved/Integration/clothing_input_request.json');inputs.unlink(missing_ok=True)
    sent=0
    call('python_exec_file',path='P:/FoA/Tools/Unreal/gameplay/pie_clothing_search.py',env={'FOA_SKY_FIRST':str(int(sky_first)), 'FOA_INPUT_DIAG':os.environ.get('FOA_INPUT_DIAG','0'),'FOA_EXTRACT_DIAG':os.environ.get('FOA_EXTRACT_DIAG','0'),'FOA_CAMERA_ONLY':os.environ.get('FOA_CAMERA_ONLY','0')},resources=['global'])
    path=Path('Saved/Integration/'+('clothing_camera_final_proof.json' if os.environ.get('FOA_CAMERA_ONLY')=='1' else 'clothing_scanner_proof.json'))
    while time.time()-stamp<(124 if sky_first else 90):
        if inputs.exists():
            try:request=json.loads(inputs.read_text())
            except (json.JSONDecodeError,PermissionError):request={}
            if request.get('id',0)>sent:
                assert request['key']=='E'
                dispatch={'waiting_for_os_key':True} if sky_first and request['id']==1 else call('editor_pie_press_key',key=request['key'],held_ms=750)
                print('INPUT',request['id'],json.dumps(dispatch),flush=True)
                sent=request['id']
        if path.exists() and path.stat().st_mtime>=stamp:
            try:report=json.loads(path.read_text())
            except (json.JSONDecodeError,PermissionError):time.sleep(.05);continue
            summary={k:v for k,v in report.items() if k not in ('trace','input_trace')}
            print(json.dumps(summary,indent=1))
            expected='extraction_camera_candidates_captured' if os.environ.get('FOA_EXTRACT_DIAG')=='1' else ('input_route_passed' if os.environ.get('FOA_INPUT_DIAG')=='1' else 'real_input_shirt_chase_vase_and_battle_passed')
            if os.environ.get('FOA_CAMERA_ONLY')=='1':expected='final_camera_shots_captured'
            assert report['reason']==expected,summary
            break
        time.sleep(.2)
    else:raise TimeoutError('clothing proof')
finally:
    try:
        if started:call('editor_stop_pie')
    finally:
        h.release(owner,token)
        if started:
            if original is not None:prefs.write_bytes(original)
            elif prefs.exists():prefs.unlink()
        print('Proof cleanup finished; global lease released')
