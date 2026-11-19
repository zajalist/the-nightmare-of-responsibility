"""Guard the short component refresh/compile/spawnable sequence with one lease."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner='character_groom'
resources=['asset:/Game/FoA/Characters/Player','asset:/Game/FoA/Cinematics/LS_WakeUp','asset:/Game/FoA/Characters/Teen/Hair']
assert not h.call('editor_get_state',owner=owner)['data']['pie_running']
token=h.lease_acquire(owner,resources,ttl_s=90,wait_s=10)
def call(command,params):
    r=h.call(command,params,owner=owner,lease=token,timeout=45);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d
    return d
try:
    for phase in ('blueprint','spawnable'):
        result=call('python_exec_file',{'path':'P:/FoA/Tools/MPFB/ue_activate_groom.py',
            'env':{'FOA_GROOM_PHASE':phase},'resources':resources})
        print(result.get('output',''))
        if phase=='blueprint':
            result=call('blueprint_compile',{'path':'/Game/FoA/Characters/Player/BP_FoAPlayer'})
            assert result.get('error_count',0)==0,result
            print('GROOM_PLAYER_COMPILE',result)
    call('asset_save',{'asset_paths':['/Game/FoA/Characters/Player/BP_FoAPlayer','/Game/FoA/Cinematics/LS_WakeUp']})
finally:h.release(owner,token)
