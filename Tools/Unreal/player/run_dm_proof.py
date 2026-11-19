"""One <=45s locomotion proof in an agreed PIE window, preserving user-owned PIE."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h
owner = os.environ.get('FOA_AGENT','anim')
proof_script = os.environ.get('FOA_PROOF_SCRIPT','P:/FoA/Tools/Unreal/player/anim_pie.py')
proof_name = 'dm_smoke' if Path(proof_script).stem == 'anim_pie' else Path(proof_script).stem
os.environ['FOA_AGENT'] = owner
lease = h.lease_acquire(owner, ['global'], ttl_s=55, wait_s=3)
started = False
states=[]
stamp = time.time()
log=Path('P:/FoA/Saved/Logs/FoA.log')
log_offset=log.stat().st_size
def call(cmd, **params):
    r = h.call(cmd, params, owner=owner, lease=lease, timeout=12)
    assert r.get('ok'), r
    return r.get('data', {})
try:
    assert not call('editor_get_state')['pie_running']
    call('editor_start_pie'); started = True
    time.sleep(.5)
    call('python_exec_file', path=proof_script, env={'FOA_PLAN':'loco','FOA_IDLE':'3','FOA_TEEN_QA':'1','FOA_NO_SHOTS':os.environ.get('FOA_NO_SHOTS','0')}, resources=['global'])
    while time.time() - stamp < 40:
        time.sleep(.1 if proof_name=='dm_smoke' else 1)
        if not call('editor_get_state')['pie_running']:
            break
        target=Path('P:/FoA/Saved/AnimShots/dm_runtime_target.json')
        if proof_name=='dm_smoke' and target.exists() and target.stat().st_mtime>=stamp:
            response=h.call('anim_instance_get_state',json.loads(target.read_text()),owner=owner,lease=lease,timeout=5)
            states.append(dict(at=time.time()-stamp,ok=response.get('ok'),data=response.get('data'),error=response.get('error')))
finally:
    try:
        if started:
            call('editor_stop_pie')
    finally:
        h.release(owner, lease)
    dest = Path('P:/FoA/Saved/AnimShots/dm_live') / time.strftime('%Y%m%d_%H%M%S',time.localtime(stamp)); dest.mkdir(parents=True,exist_ok=True)
    captured=0
    for shot in Path('P:/FoA/Saved/Screenshots/WindowsEditor').glob('ScreenShot*.png'):
        if shot.stat().st_mtime >= stamp:
            shot.rename(dest / shot.name)
            captured+=1
    print('DM proof captured', captured, 'new frames', round(time.time()-stamp,1), 'seconds')
with log.open('rb') as stream:
    stream.seek(log_offset);events=stream.read().decode('utf-8',errors='replace')
errors=[line for line in events.splitlines() if '[anim] error' in line]
errors+=sorted(set(line.split('LogSequenceEvaluatorLibrary: ',1)[1] for line in events.splitlines()
                   if 'LogSequenceEvaluatorLibrary: Warning:' in line))
errors+=sorted(set(line for line in events.splitlines() if 'UniformIndexable' in line and 'Warning:' in line))
if proof_name=='dm_smoke':
    for i,row in enumerate(states):
        if row['ok']:continue
        if i==len(states)-1 and 'no live PIE worlds' in str(row.get('error')) and '[anim] done' in events:
            row['classification']='query_raced_successful_script_shutdown'
        else:errors.append('Native state query failed: '+str(row.get('error')))
    names={r['data'].get('state_name') for r in states if r['ok'] and r['data']}
    missing={'Start','Walk / Run','Stop','Idle'}-names
    if missing:errors.append('Missing observed native states: '+str(sorted(missing)))
    (dest/'native_states.json').write_text(json.dumps(states,indent=1))
result=dict(passed='[anim] done' in events and not errors, errors=errors, elapsed=time.time()-stamp,
            no_screenshots=os.environ.get('FOA_NO_SHOTS')=='1',frames=captured,directory=str(dest))
result['proof_script']=proof_script
Path('P:/FoA/Saved/AnimShots/'+proof_name+'_latest.json').write_text(json.dumps(result,indent=1))
Path('P:/FoA/Saved/AnimShots/'+proof_name+'_events.txt').write_text('\n'.join(line for line in events.splitlines() if '[anim]' in line))
assert result['passed'],result
