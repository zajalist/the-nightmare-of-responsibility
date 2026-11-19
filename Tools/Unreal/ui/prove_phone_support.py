"""Coordinator-authorized short PIE burst, always stopped and released in finally."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as hc


def main():
    owner=os.environ.get('FOA_AGENT','phone_resume');os.environ['HAYBA_AGENT_ID']=owner;os.environ['FOA_AGENT']=owner
    assert not hc.call('editor_get_state')['data']['pie_running'],'User PIE active'
    token=hc.lease_acquire(owner,['global'],ttl_s=90,wait_s=3)
    env=dict(os.environ,FOA_LEASE=token,FOA_EXCLUSIVE='1')
    log=[]
    started=False
    settings=Path('Saved/SaveGames/Settings.sav');original=settings.read_bytes() if settings.exists() else None
    def command(name,**params):
        result=hc.call(name,params,owner=owner,lease=token,timeout=15)
        log.append([name,result]);assert result.get('ok'),result
        return result.get('data',{})
    def probe(phase):
        p=subprocess.run([sys.executable,'Tools/Unreal/ue_remote.py','Tools/Unreal/ui/phone_support_probe.py','PHONE_PHASE='+phase],
                         env=env,capture_output=True,text=True,timeout=12)
        log.append(['probe_'+phase,p.stdout,p.stderr]);assert p.returncode==0,p.stdout+p.stderr
        if phase in ('cleanup','clear_failed_proof'):return {}
        return json.loads(Path('Saved/UIShots/phone_pie_'+phase+'.json').read_text())
    try:
        assert not command('editor_get_state')['pie_running']
        probe('clear_failed_proof')
        started=command('editor_start_pie').get('pie_started',False)
        assert started,'PIE was not started by this proof'
        time.sleep(1.5)
        probe('setup');time.sleep(.4)
        probe('title');time.sleep(.5)
        probe('start')
        deadline=time.time()+16;skipped=False;story_finished=False
        while time.time()<deadline:
            state=probe('observe')
            if state['story_visible'] and not story_finished:
                probe('story');story_finished=True
            elif state['gameplay'] and state['sequence_started'] and not state['wake_done'] and not skipped:
                probe('wake');skipped=True
            elif state['wake_done'] and state['beat']==1 and state['view']=='BP_FoAPlayer_C':break
            time.sleep(.25)
        else:raise TimeoutError('Actual front-end wake did not reach free gameplay')
        probe('ready')
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_hint_after.png',show_ui=True)
        command('editor_pie_press_key',key='P');time.sleep(1.5)
        opened=probe('open');assert opened['open'] and opened['ignored_move'] and opened['cinematic'],opened
        time.sleep(.6)
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_support_normal.png',show_ui=True)
        command('editor_pie_press_key',key='Right');time.sleep(2.3)
        probe('message')
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_support_messages_settled.png',show_ui=True)
        probe('contact');time.sleep(.6)
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_support_contact.png',show_ui=True)
        probe('support_side');time.sleep(.6)
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_support_side_focused.png',show_ui=True)
        probe('support_back');time.sleep(.6)
        command('editor_pie_screenshot',filename='P:/FoA/Saved/UIShots/phone_support_back_focused.png',show_ui=True)
        probe('restore_contact')
        command('editor_pie_press_key',key='P');time.sleep(.6)
        closed=probe('closed');assert not closed['open'] and not closed['ignored_move'] and not closed['ignored_look'] and not closed['cinematic'],closed
    finally:
        try:
            if started:
                try:probe('cleanup')
                finally:command('editor_stop_pie')
        finally:
            hc.release(owner,token)
            if started:
                if original is not None:settings.write_bytes(original)
                elif settings.exists():settings.unlink()
            Path('Saved/UIShots/phone_support_proof_log.json').write_text(json.dumps(log,indent=2))
    print('Phone PIE stopped and lease released')


if __name__=='__main__':
    if sys.argv[1:]!=['--run']:
        sys.exit('Phone proof is held until widget binding verification; pass --run after coordinator clearance.')
    main()
