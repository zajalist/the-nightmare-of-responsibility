"""A destroyed world must unregister before any gameplay API reads it."""
import importlib.util
from pathlib import Path
import sys
import types

world=object();state={'world':world,'valid':True,'reads':0,'removed':[]}
def game_time(w):
    assert state['valid']
    state['reads']+=1
    return 1
fake=types.SimpleNamespace(UnrealEditorSubsystem=object,
    get_editor_subsystem=lambda _:types.SimpleNamespace(get_game_world=lambda:state['world']),
    SystemLibrary=types.SimpleNamespace(is_valid=lambda w:state['valid']),
    GameplayStatics=types.SimpleNamespace(get_real_time_seconds=game_time),
    register_slate_post_tick_callback=lambda fn:17,
    unregister_slate_post_tick_callback=lambda h:state['removed'].append(h),log=lambda message:None)
sys.modules['unreal']=fake
spec=importlib.util.spec_from_file_location('guard',Path(__file__).with_name('proof_guard.py'))
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
s={};assert guard.arm(s,lambda dt:None,'test');assert guard.live(s) is world
reads=state['reads'];state['valid']=False
assert guard.live(s) is None and state['reads']==reads and state['removed']==[17]
assert not guard.arm({},lambda dt:None,'invalid')
guard.done(s);assert state['removed']==[17]
print('Destroyed-world guard and idempotent cleanup pass')
