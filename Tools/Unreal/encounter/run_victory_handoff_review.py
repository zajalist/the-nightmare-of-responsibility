"""Own a bounded outcome test and restore the user's exact preference bytes."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h

assert sys.argv[1:] == ['--run']
owner = 'main:presentation'
os.environ['HAYBA_AGENT_ID'] = owner
assert not h.call('editor_get_state')['data']['pie_running'], 'User PIE active'
token = h.lease_acquire(owner, ['global'], ttl_s=90, wait_s=3)
prefs = Path('Saved/SaveGames/Settings.sav')
old = prefs.read_bytes() if prefs.exists() else None
out = Path('Saved/EncounterCaptures/outcomes_proof.json')
started = False

def call(command, **params):
    result = h.call(command, params, owner=owner, lease=token, timeout=12)
    assert result.get('ok'), result
    return result.get('data', {})

try:
    assert not call('editor_get_state')['pie_running']
    started = call('editor_start_pie').get('pie_started', False)
    assert started
    time.sleep(.5)
    stamp = time.time()
    call('python_exec_file', path='P:/FoA/Tools/Unreal/encounter/pie_outcomes_proof.py',
         env={'FOA_OUTCOME_MODE': 'win', 'FOA_CAP': '70'}, resources=['global'])
    while time.time() - stamp < 76:
        if out.exists() and out.stat().st_mtime >= stamp:
            try:
                result = json.loads(out.read_text())
            except (ValueError, PermissionError):
                time.sleep(.1)
                continue
            print(json.dumps(result, indent=1), flush=True)
            assert result['reason'] == 'win_complete', result
            break
        time.sleep(.2)
    else:
        raise TimeoutError('Victory handoff proof timed out')
finally:
    try:
        if started:
            call('editor_stop_pie')
    finally:
        h.release(owner, token)
        if started:
            if old is not None:
                prefs.write_bytes(old)
            else:
                prefs.unlink(missing_ok=True)
        print('Owned outcome test ended; preferences restored and global lease released')
