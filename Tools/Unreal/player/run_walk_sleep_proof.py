"""One owned <=50s proof using the existing real front-end boot and shipping character sequence."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
owner='metahuman-walk-sleep-qa'
lease=hc.lease_acquire(owner,['global'],ttl_s=60,wait_s=5)
started=False
begin=time.time()


def call(name,**args):
    r=hc.call(name,args,owner=owner,lease=lease,timeout=10)
    assert r.get('ok') and r.get('data',{}).get('ok',True),r
    return r.get('data',{})


def wait(path,stamp,seconds):
    f=Path(path); end=min(time.time()+seconds,begin+47)
    while time.time()<end:
        if f.exists() and f.stat().st_mtime>=stamp:
            try: d=json.loads(f.read_text())
            except (json.JSONDecodeError,PermissionError): d={}
            if d.get('reason'): return d
        time.sleep(.15)
    raise TimeoutError(path)


try:
    state=call('editor_get_state'); assert not state['pie_running'],'User PIE is already active'
    assert not [p for p in state.get('dirty_packages',[]) if '/Maps/' not in p],state
    call('editor_start_pie'); started=True
    time.sleep(.5)
    stamp=time.time()
    call('python_exec_file',path='P:/FoA/Tools/Unreal/player/pie_walk_sleep_capture.py',env={'FOA_COLD_BOOT':'1'},resources=['global'])
    result=wait('P:/FoA/Saved/CharacterShots/walk_sleep/latest.json',stamp,31)
    print(json.dumps(result,indent=1))
finally:
    if started: call('editor_stop_pie')
    hc.release(owner,lease)
    print('GLOBAL RELEASED, owned proof elapsed',round(time.time()-begin,2))
