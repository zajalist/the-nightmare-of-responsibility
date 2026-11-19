"""Apply visually compared defaults through the existing typed MPC helper and native property/save tools."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/Unreal'))
import hayba_call as hc

OWNER = 'codex-clarity'
BP = '/Game/FoA/PostProcess/BP_DreamDirector'
MPC = '/Game/FoA/PostProcess/MPC_Dream'
os.environ.update(FOA_AGENT=OWNER, HAYBA_AGENT_ID=OWNER, FOA_AREAS='PostProcess')
token = hc.lease_acquire(OWNER, ['asset:' + BP, 'asset:' + MPC, 'actor:DreamDirector'], ttl_s=60, wait_s=10)


def call(name, **params):
    reply = hc.call(name, params, owner=OWNER, lease=token, timeout=15)
    assert reply.get('ok'), reply
    return reply.get('data', {})


try:
    assert not call('editor_get_state')['pie_running']
    subprocess.run([sys.executable, str(ROOT / 'Tools/Unreal/ue_remote.py'),
                    str(ROOT / 'Tools/Unreal/integration/refine_clarity_defaults.py')], cwd=ROOT, check=True)
    actor = next(a for a in call('actor_list', class_filter='BP_DreamDirector_C')['actors'] if a['label'] == 'DreamDirector')
    for path in (BP + '.Default__BP_DreamDirector_C',
                 '/Game/FoA/Maps/L_Tutorial_Bedroom.L_Tutorial_Bedroom:PersistentLevel.' + actor['id']):
        call('object_set_property', path=path, properties={'BaseEcho': .08})
        actual = call('object_get_property', path=path, names=['BaseEcho'])
        assert abs(float(actual['properties']['BaseEcho']) - .08) < .0001, actual
    saved = call('asset_save', asset_paths=[BP, MPC])
    assert saved.get('saved_count') == 2 and not saved.get('failed'), saved
    print('Restrained gameplay lens/echo defaults saved; menu and story APIs retained')
finally:
    hc.release(OWNER, token)
