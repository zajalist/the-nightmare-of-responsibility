"""Exclusive map-switch runner. No caller can bypass dirty-map checks or stop another owner's PIE."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal']
import drive_data as D
import hayba_call as h
import editor_lock

OUT=Path('P:/FoA/Saved/Codex/l2_drive');OUT.mkdir(parents=True,exist_ok=True)
D.OWNER=os.environ.get('FOA_AGENT','main-level2-drive-proof')
os.environ.update(FOA_AGENT=D.OWNER,HAYBA_AGENT_ID=D.OWNER,FOA_CALLER=D.OWNER,FOA_EXCLUSIVE='1')


def run(script,*args):
    editor_lock.hc.renew_all(D.OWNER,70)
    assert any('global' in [r.lower() for r in res] for _,res in h.leases_of(D.OWNER)),'EXCLUSIVE lost'
    p=subprocess.run([sys.executable,'Tools/Unreal/integration/run_read.py',script,*args],capture_output=True,text=True,timeout=60)
    print(p.stdout[-3500:],flush=True)
    assert p.returncode==0,(p.returncode,p.stderr[-1500:])


def mapstep(step):run('Tools/Unreal/level2/drive_map.py','FOA_DRIVE_MAP='+step)


def release_inputs():
    errors=[]
    for key in ('W','A','D','S','Q','Enter','SpaceBar'):
        try:
            result=h.call('editor_pie_press_key',{'key':key,'event':'released'},timeout=5)
            assert result.get('ok'),result
        except Exception as exc:errors.append((key,repr(exc)))
    return errors


def end_pie():
    errors=release_inputs()
    try:run('Tools/Unreal/level2/drive_proof.py','FOA_DRIVE_PROOF=STOP')
    finally:run('Tools/Unreal/ui/pie_call.py','FOA_CALL=END')
    assert not errors,('Input release failed; PIE still ended',errors)


def save_hashes():
    folder=Path('P:/FoA/Saved/SaveGames')
    return {name:hashlib.sha256((folder/name).read_bytes()).hexdigest() if (folder/name).exists() else None
            for name in ('FoA.sav','Settings.sav')}


def main():
    mode=sys.argv[1]
    assert mode in ('build','proof','video'),mode
    assert Path('P:/FoA/Content'+D.CITY[5:]+'.umap').exists(),'City not saved yet; poll offline and wait'
    (OUT/'burst_pid.txt').write_text(str(os.getpid()))
    editor_lock.acquire(D.OWNER,wait_s=5,ttl=70)
    switched=pie=False;t0=time.monotonic()
    before=save_hashes()
    log=Path('P:/FoA/Saved/Logs/FoA.log');log_start=log.stat().st_size
    try:
        state=h.call('editor_get_state',timeout=20)['data'];assert not state['pie_running'],'PIE already active'
        dirty=[p for p in state['dirty_packages'] if '/Maps/' in p]
        assert not dirty,('Coordinator must resolve dirty map packages',dirty)
        mapstep('before');switched=True;mapstep('open')
        if mode=='build':mapstep('build')
        else:
            preflight=Path('P:/FoA/Saved/QA/preflight.json')
            preflight.unlink(missing_ok=True)
            run('Tools/QA/preflight_blueprints.py')
            pre=json.loads(preflight.read_text())
            assert pre['ok'],('Blueprint preflight failed; PIE not started',pre['failures'])
            done=OUT/('video_done.json' if mode=='video' else 'proof_done.json')
            if done.exists():done.unlink()
            (OUT/'input_request.json').unlink(missing_ok=True)
            pie=True;run('Tools/Unreal/ui/pie_call.py','FOA_CALL=BEGIN')
            run('Tools/Unreal/level2/drive_proof.py','FOA_DRIVE_PROOF='+('VIDEO' if mode=='video' else 'PROOF'))
            renew=time.monotonic();sent=0;proof_start=time.monotonic()
            while not done.exists() and time.monotonic()-proof_start<45:
                request=OUT/'input_request.json'
                if request.exists():
                    try:message=json.loads(request.read_text())
                    except (json.JSONDecodeError,PermissionError):message={}
                    if message.get('id',0)>sent:
                        for event in message['events']:
                            result=h.call('editor_pie_press_key',event,timeout=5)
                            assert result.get('ok') and result.get('data',{}).get('dispatched'),result
                        sent=message['id']
                time.sleep(.02)
                if time.monotonic()-renew>20:
                    h.renew_all(D.OWNER,70);renew=time.monotonic()
                    assert any('global' in [r.lower() for r in res] for _,res in h.leases_of(D.OWNER))
            end_pie();pie=False
            assert done.exists(),'Free-drive proof exceeded45s outer budget'
            result=json.loads(done.read_text())
            assert result['reason']=='passed',(result['reason'],result.get('error'))
    finally:
        try:
            try:
                if pie:
                    end_pie()
            finally:
                if switched:
                    state=h.call('editor_get_state',timeout=10)
                    assert state.get('ok') and not state.get('data',{}).get('pie_running',True),'PIE must stop before map return'
                    mapstep('back')
        finally:
            try:editor_lock.release(D.OWNER)
            finally:
                assert save_hashes()==before,'Player saves changed during free-drive proof'
                segment=log.read_bytes()[log_start:].decode('utf-8',errors='replace')
                (OUT/'free_drive_pie.log').write_text(segment,encoding='utf-8')
                print('DRIVE hold seconds',round(time.monotonic()-t0,2))
                assert 'Blueprint Runtime Error' not in segment and 'Accessed None' not in segment,'Free-drive Blueprint runtime error'


if __name__=='__main__':main()
