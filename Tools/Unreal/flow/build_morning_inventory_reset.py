"""Reset physical slots only at BeginMorning. Ordinary ResetHouse/cancel is unchanged."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
I='/Game/FoA/Gameplay/BPC_Inventory';IC=I+'.BPC_Inventory_C'
D='/Game/FoA/Gameplay/BP_BeatDirector';DC=D+'.BP_BeatDirector_C'
owner='clothing_search';os.environ['HAYBA_AGENT_ID']=owner
token=h.lease_acquire(owner,['asset:'+I,'asset:'+D],ttl_s=60,wait_s=3)
def call(name,**args):
    r=h.call(name,args,owner=owner,lease=token);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d;return d
def fresh(path,name):
    if not h.call('blueprint_inspect_graph',dict(path=path,graph_name=name),owner=owner).get('ok'):
        call('blueprint_add_function',path=path,function_name=name)
    nodes,_=inspect(path,name);entry=find(nodes,name);b=Batch(path,name)
    old=[n['node_id'] for n in nodes if n['node_id']!=entry and n['title']!='Return Node']
    if old:b.ops.append(dict(op='remove',node_ids=old))
    return b,entry
try:
    assert not call('editor_get_state')['pie_running'],'User PIE active'
    if not h.call('blueprint_inspect_graph',dict(path=I,graph_name='ClearPhysicalInventory'),owner=owner).get('ok'):
        call('blueprint_add_function',path=I,function_name='ClearPhysicalInventory')
    call('python_exec_file',path='P:/FoA/Tools/Unreal/flow/write_inventory_clear.py',env={},resources=['asset:'+I])
    compiled=call('blueprint_compile',path=I);assert compiled['error_count']==0,compiled
    print('ClearPhysicalInventory native compile',compiled)
    call('asset_save',asset_paths=[I])
    b,e=fresh(D,'ResetMorningInventory')
    b.fn('pawn','/Script/Engine.GameplayStatics:GetPlayerPawn',0,300,PlayerIndex=0)
    b.fn('bag','/Script/Engine.Actor:GetComponentByClass',300,300,ComponentClass=IC)
    b.link('pawn','ReturnValue','bag','self')
    b.node('cast','cast',600,0,class_path=IC);b.link('bag','ReturnValue','cast','Object')
    b.fn('reset',IC+':ClearPhysicalInventory',950,0);b.link('cast','AsBPC Inventory','reset','self')
    b.chain(e,'cast','reset');b.comment('Only a new morning empties the pockets',['pawn','bag','cast','reset']);b.run()
    nodes,edges=inspect(D,'BeginMorning')
    if not any(n['title']=='ResetMorningInventory' for n in nodes):
        e=find(nodes,'BeginMorning');edge=next(x for x in edges if x['from_node']==e and x['from_pin']=='then')
        b=Batch(D,'BeginMorning');b.fn('reset',DC+':ResetMorningInventory',-450,0)
        b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'reset');b.link('reset','then',edge['to_node'],edge['to_pin'])
        b.comment('Reset physical inventory for this morning',['reset']);b.run()
    print('Morning inventory reset saved; knowledge/notebook and same-day reset paths untouched')
finally:h.release(owner,token)
