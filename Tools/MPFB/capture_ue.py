"""Run a bounded teen capture with its actor lease held through asynchronous cleanup."""
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import editor_lock
import hayba_call as hc

OWNER = 'character_capture'
assert not hc.call('editor_get_state',owner=OWNER)['data']['pie_running'], 'Wait for PIE to stop'
args = dict(a.split('=', 1) for a in sys.argv[1:])
out = Path(args.get('FOA_OUT', 'P:/FoA/Saved/CharacterShots/mpfb/ue'))
done = out / ('_' + args.get('FOA_OUTFIT', 'wake') + '_done.txt')
token = hc.lease_acquire(OWNER, editor_lock.actor_keys(new_prefixes=['TMP_rlchar_']), ttl_s=60, wait_s=20)
try:
    started = time.time()
    env = dict(os.environ, FOA_AGENT=OWNER, HAYBA_AGENT_ID=OWNER, FOA_AREAS='', FOA_ACTORS='', FOA_ACTORS_NEW='')
    subprocess.run([sys.executable, 'Tools/Unreal/ue_remote.py', 'Tools/MPFB/ue_capture_teen.py', *sys.argv[1:]],
                   env=env, check=True, timeout=30)
    while not (done.exists() and done.stat().st_mtime >= started):
        assert time.time() - started < 40, 'Capture cleanup did not complete in 40 seconds'
        time.sleep(.2)
    assert done.read_text()=='done','Capture callback failed; inspect editor log'
    print('Capture and cleanup completed:', done)
finally:
    hc.release(OWNER, token)
