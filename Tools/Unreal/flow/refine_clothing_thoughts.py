"""Narrow saved-graph patch: clear the old thought when the new shot starts."""
import os,sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/flow','P:/FoA/Tools/Unreal/player']
from build_clothing_inspection import P,C,call,h,build_clear_narration,SHOTS
from held_tool_graphs import Batch,inspect,find
os.environ['HAYBA_AGENT_ID']='clothing_search'
assert not call('editor_get_state')['pie_running']
token=h.lease_acquire('clothing_search',['asset:'+P],ttl_s=60,wait_s=3);os.environ['FOA_LEASE']=token
try:
    if not h.call('blueprint_inspect_graph',dict(path=P,graph_name='ClearClothingNarration')).get('ok'):
        call('blueprint_add_function',path=P,function_name='ClearClothingNarration')
    build_clear_narration()
    ns,es=inspect(P,'TryClothingInspection')
    if not any(n['title']=='ClearClothingNarration' for n in ns):
        active=find(ns,'Set bClothingInspection');edge=next(x for x in es if x['from_node']==active and x['from_pin']=='then')
        b=Batch(P,'TryClothingInspection');b.cut(active,'then',edge['to_node'],edge['to_pin'])
        b.fn('clearold',C+':ClearClothingNarration',2550,0);b.chain(active,'clearold');b.link('clearold','then',edge['to_node'],edge['to_pin']);b.run()
    ns,_=inspect(P,'QueueClothingWardrobe')
    node=next(n for n in ns if any(p.get('default_value','').startswith('A thread caught') for p in n.get('pins',[])))
    b=Batch(P,'QueueClothingWardrobe');b.pin(node['node_id'],'InString',SHOTS[0][2]);b.run()
    ns,_=inspect(P,'QueueClothingBed')
    node=next(n for n in ns if any(p['name']=='InString' for p in n.get('pins',[])))
    b=Batch(P,'QueueClothingBed');b.pin(node['node_id'],'InString',SHOTS[2][2]);b.run()
finally:h.release('clothing_search',token);os.environ.pop('FOA_LEASE',None)
