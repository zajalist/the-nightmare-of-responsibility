"""Story lane: run a pie_<name>.py driver (default pie_chase_final) in a bounded PIE (48 s) INSIDE the caller's editor_lock
EXCLUSIVE hold, relay its E requests with editor_pie_press_key, stop PIE, restore the settings save bytes.
  python Tools/Unreal/flow/run_chase_final.py [pie_topdown_exit]
The driver writes Saved/StoryShots/<name>.json and asks for keys in Saved/StoryShots/<name>_input.json."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

os.environ['HAYBA_AGENT_ID'] = owner = os.environ.get('FOA_AGENT','story')
os.environ['FOA_AGENT'] = os.environ['FOA_CALLER'] = owner
DRIVER = sys.argv[1] if len(sys.argv) > 1 else 'pie_chase_final'
NAME = DRIVER.removeprefix('pie_')
OUT = Path(f'P:/FoA/Saved/StoryShots/{NAME}.json')
INPUTS = Path(f'P:/FoA/Saved/StoryShots/{NAME}_input.json')
prefs = Path('P:/FoA/Saved/SaveGames/Settings.sav')
original = prefs.read_bytes() if prefs.exists() else None
save = Path('P:/FoA/Saved/SaveGames/FoA.sav')


def digest():
    return hashlib.sha256(save.read_bytes()).hexdigest() if save.exists() else None


before = digest()


def call(name, **args):
    r = h.call(name, args, owner=owner, timeout=20)
    assert r.get('ok'), r
    return r.get('data', {})


def cleanup(started):
    try:
        if started:
            call('python_exec_file', path='P:/FoA/Tools/Unreal/ui/pie_call.py',
                 env={'FOA_CALL': 'END', 'FOA_CALLER': owner}, resources=['global'])
            for _ in range(20):
                if not call('editor_get_state')['pie_running']:
                    break
                time.sleep(.2)
            assert not call('editor_get_state')['pie_running'], 'Owned PIE did not stop'
    finally:
        try:
            if original is not None:
                prefs.write_bytes(original)
            elif prefs.exists():
                prefs.unlink()
        finally:
            assert digest() == before, 'Player save changed during proof'


# The caller owns this global lease and remains responsible for releasing it.
token = os.environ.get('FOA_LEASE')
assert token and any('global' in resources for _, resources in h.leases_of(owner)), 'Caller story global lease required'
assert not call('editor_get_state')['pie_running'], 'PIE already running'
started = False
try:
    # BEGIN can reach the editor even when its transport response times out.
    started = True
    call('python_exec_file', path='P:/FoA/Tools/Unreal/ui/pie_call.py',
         env={'FOA_CALL': 'BEGIN', 'FOA_CALLER': owner}, resources=['global'])
    for _ in range(20):
        if call('editor_get_state')['pie_running']:
            break
        time.sleep(.2)
    assert call('editor_get_state')['pie_running'], 'PIE did not start'
    stamp = time.time()
    renewed = time.monotonic()
    call('python_exec_file', path=f'P:/FoA/Tools/Unreal/flow/{DRIVER}.py',
         env={'FOA_FOCUS_CASE': os.environ.get('FOA_FOCUS_CASE', 'boot')}, resources=['global'])
    sent = 0
    while time.time() - stamp < 48:
        if time.monotonic() - renewed >= 20:
            for candidate in token.split(';'):
                call('lease_renew', token=candidate, ttl_s=60)
            renewed = time.monotonic()
        if INPUTS.exists():
            try:
                req = json.loads(INPUTS.read_text())
            except (json.JSONDecodeError, PermissionError):
                req = {}
            if req.get('id', 0) > sent:
                print('INPUT', req['id'], json.dumps(call('editor_pie_press_key', key=req['key'], held_ms=400)), flush=True)
                sent = req['id']
        if OUT.exists() and OUT.stat().st_mtime >= stamp:
            try:
                rep = json.loads(OUT.read_text())
            except (json.JSONDecodeError, PermissionError):
                time.sleep(0.05)
                continue
            print('RESULT', rep['reason'])
            for row in rep['rows']:
                if row['kind'] != 'cmd':
                    print(json.dumps(row, default=str)[:300])
            break
        time.sleep(0.15)
    else:
        print('RESULT runner_timeout')
finally:
    cleanup(started)
    print('Owned PIE stopped; player save unchanged; settings restored; caller retains lease')
