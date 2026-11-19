"""Commit delayed clue text only after every camera graph and hook exists."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import inspect
owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
D='/Game/FoA/Gameplay/BP_BeatDirector'
paths=['/Game/FoA/Gameplay/DT_Interactions','/Game/FoA/Gameplay/GI_FoA']
token=h.lease_acquire(owner,['asset:'+p for p in paths],ttl_s=45,wait_s=3)
def call(name,**kw):
    r=h.call(name,kw,owner=owner,lease=token);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    for graph,clue in [('SearchWardrobeClue','Wardrobe'),('SearchDeskClue','Desk'),('SearchBedClue','Bed')]:
        ns,_=inspect(D,graph);assert any(n['title']=='QueueClothing'+clue for n in ns),(graph,'missing hook')
    for graph in ('TryClothingInspection','CancelClothingInspection','FinishClothingInspection'):
        ns,es=inspect(D,graph);assert len(ns)>5 and es,(graph,'not built')
    call('python_exec_file',path='P:/FoA/Tools/Unreal/flow/patch_clothing_discovery_lines.py',env={},resources=['asset:'+p for p in paths])
    print(call('asset_save',asset_paths=paths))
finally:h.release(owner,token)
