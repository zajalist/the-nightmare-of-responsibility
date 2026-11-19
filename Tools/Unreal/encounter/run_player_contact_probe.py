"""Own one bounded PIE burst and restore exact settings on every exit."""
import sys,os,json,time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
assert sys.argv[1:]==['--run'];owner='character_contact_proof';os.environ['HAYBA_AGENT_ID']=owner
assert not h.call('editor_get_state')['data']['pie_running'],'User PIE active'
token=h.lease_acquire(owner,['global'],ttl_s=35,wait_s=3);started=False
pref=Path('Saved/SaveGames/Settings.sav');old=pref.read_bytes() if pref.exists() else None
folder=Path('Saved/Integration/cinematic_audit/contact');folder.mkdir(exist_ok=True)
def call(cmd,**kw):
    r=h.call(cmd,kw,owner=owner,lease=token,timeout=10);assert r.get('ok'),r;return r.get('data',{})
try:
    assert not call('editor_get_state')['pie_running']
    for name in ('boot.json','report.json'): (folder/name).unlink(missing_ok=True)
    started=call('editor_start_pie').get('pie_started',False);assert started
    time.sleep(.4);call('python_exec_file',path='P:/FoA/Tools/Unreal/encounter/pie_player_contact_boot.py',env={},resources=['global'])
    deadline=time.monotonic()+24
    while time.monotonic()<deadline:
        if (folder/'boot.json').exists():
            result=json.loads((folder/'boot.json').read_text());print(result);assert result['error'] is None,result
            proof=json.loads((folder/'report.json').read_text());assert proof['error'] is None and proof['restored'],proof
            break
        time.sleep(.15)
    else:raise TimeoutError('Hair surface probe')
finally:
    try:
        if started:print('PIE_CLEANUP',call('editor_stop_pie'))
    finally:
        h.release(owner,token)
        if started:
            if old is not None:pref.write_bytes(old)
            elif pref.exists():pref.unlink()
        print('Hair proof lease released')
