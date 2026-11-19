"""Apply only the door's resistance and status graphs, after a fresh no-PIE check."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h

owner = 'clothing_search'
os.environ['HAYBA_AGENT_ID'] = owner
asset = '/Game/FoA/Gameplay/BP_Door'
token = h.lease_acquire(owner, ['asset:' + asset], ttl_s=60, wait_s=3)
log = []

def call(name, **args):
    r = h.call(name, args, owner=owner, lease=token, timeout=30)
    log.append([name, r])
    assert r.get('ok'), r
    d = r.get('data', {}); assert d.get('ok', True), d
    return d

try:
    for phase in ('motion', 'refresh'):
        assert not call('editor_get_state')['pie_running'], 'User PIE active'
        result = call('python_exec_file', path='P:/FoA/Tools/Unreal/gameplay/build_door_tools.py',
                      env={'FOA_PHASE': phase}, resources=['asset:' + asset])
        print(phase, json.dumps(result))
        compiled = call('blueprint_compile', path=asset)
        assert compiled.get('compiled', True) and not compiled.get('num_errors', compiled.get('error_count', 0)), compiled
        print('compile', compiled)
        call('asset_save', asset_paths=[asset])
finally:
    h.release(owner, token)
    Path('Saved/Integration/rusted_key_apply.json').write_text(json.dumps(log, indent=1))
