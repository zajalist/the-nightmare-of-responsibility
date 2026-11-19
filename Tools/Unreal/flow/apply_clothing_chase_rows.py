"""Native save boundary for the completed chase's targeted table commit."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
path='/Game/FoA/Gameplay/DT_Interactions'
token=h.lease_acquire(owner,['asset:'+path],ttl_s=30,wait_s=3)
try:
    def call(name,**kw):
        r=h.call(name,kw,owner=owner,lease=token);assert r.get('ok'),r
        d=r.get('data',{});assert d.get('ok',True),d;return d
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    call('python_exec_file',path='P:/FoA/Tools/Unreal/flow/patch_clothing_chase_rows.py',env={},resources=['asset:'+path])
    print(call('asset_save',asset_paths=[path]))
finally:h.release(owner,token)
