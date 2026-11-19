"""Native scoped integration of the reachable pickup and one targeted interaction row."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
table='/Game/FoA/Gameplay/DT_Interactions';level='/Game/FoA/Maps/L_Tutorial_Bedroom'
token=h.lease_acquire(owner,['asset:'+table,'world:'+level],ttl_s=45,wait_s=5)
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token,timeout=15);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d
    return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    spot=json.loads(Path('Saved/Integration/clothing_clear_spot.json').read_text());assert spot['obstruction'] is None
    candidates=call('actor_list',class_filter='BP_BeatDirector_C')['actors'];assert len(candidates)==1,candidates
    vector='('+','.join(k+'='+str(v) for k,v in zip(('X','Y','Z'),spot['spot']))+')'
    print(call('actor_set_properties',actor_id=candidates[0]['id'],properties={'ClothingShirtSpot':vector}))
    print(call('python_exec_file',path='P:/FoA/Tools/Unreal/flow/patch_clothing_hanger_row.py',env={},resources=['asset:'+table]))
    print(call('asset_save',asset_paths=[table]))
    print(call('level_save',path=level))
finally:h.release(owner,token)
