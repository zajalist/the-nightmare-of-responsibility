"""Bound animation lag in first person; never bound free mouse yaw to lagging shoulders."""
import sys
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
from first_person_graphs import run
A='/Game/FoA/Characters/Player/ABP_FoAPlayer';K='/Script/Engine.KismetMathLibrary:'
assert not h.call('editor_get_state')['data']['pie_running']
if not any(flag in sys.argv for flag in ('--tighten','--controller')):run()
owner=h.agent_id();lease=h.lease_acquire(owner,['asset:'+A],ttl_s=45,wait_s=5)
try:
    nodes,edges=inspect(A,'UpdateTurnInPlace')
    setter=find(nodes,'Set RootYawOffset');char=find(nodes,'Get Character')
    pick=next(e['from_node'] for e in edges if e['to_node']==setter and e['to_pin']=='RootYawOffset')
    held=next(e for e in edges if e['to_node']==pick and e['to_pin']=='A')
    byid={n['node_id']:n for n in nodes}
    if '--controller' in sys.argv:
        chooser=held['from_node']
        owned=next(e['from_node'] for e in edges if e['to_node']==chooser and e['to_pin']=='bPickA')
        view=next(e['from_node'] for e in edges if e['to_node']==owned and e['to_pin']=='A')
        pc=next(e['from_node'] for e in edges if e['to_node']==view and e['to_pin']=='self')
        assert byid[view]['title'].replace(' ','')=='GetViewTarget',byid[view]
        b=Batch(A,'UpdateTurnInPlace')
        b.fn('local','/Script/Engine.Pawn:IsLocallyControlled',1000,1650);b.link(char,'Character','local','self')
        b.get('yaw','bUseControllerRotationYaw',1300,1900,'/Script/Engine.Pawn');b.link(char,'Character','yaw','self')
        b.fn('free',K+'BooleanAND',1600,1650);b.link('local','ReturnValue','free','A');b.link('yaw','bUseControllerRotationYaw','free','B')
        b.cut(owned,'ReturnValue',chooser,'bPickA');b.link('free','ReturnValue',chooser,'bPickA')
        b.ops.append(dict(op='remove',node_ids=[pc,view,owned]))
        b.comment('Local free camera body catch-up',['local','yaw','free']);b.run();sys.exit(0)
    if '--tighten' in sys.argv:
        chooser=held['from_node'];limited=next(e for e in edges if e['to_node']==chooser and e['to_pin']=='A')
        assert byid[limited['from_node']]['title']=='Clamp (Float)',byid[limited['from_node']]['title']
        b=Batch(A,'UpdateTurnInPlace');b.pin(limited['from_node'],'Min',-45);b.pin(limited['from_node'],'Max',45)
        b.fn('settle',K+'FInterpTo',1950,2100,Target=0,InterpSpeed=8)
        b.link(limited['from_node'],'ReturnValue','settle','Current');b.link(find(nodes,'UpdateTurnInPlace'),'DeltaSeconds','settle','DeltaTime')
        b.cut(limited['from_node'],'ReturnValue',chooser,'A');b.link('settle','ReturnValue',chooser,'A')
        b.comment('Settle first person torso',['settle']);b.run();sys.exit(0)
    assert byid[held['from_node']]['title']=='NormalizeAxis','Already patched or unexpected turn graph'
    b=Batch(A,'UpdateTurnInPlace')
    b.fn('local','/Script/Engine.Pawn:IsLocallyControlled',1000,1650);b.link(char,'Character','local','self')
    b.get('yaw','bUseControllerRotationYaw',1300,1900,'/Script/Engine.Pawn');b.link(char,'Character','yaw','self')
    b.fn('owned',K+'BooleanAND',1600,1650);b.link('local','ReturnValue','owned','A');b.link('yaw','bUseControllerRotationYaw','owned','B')
    b.fn('limit',K+'FClamp',1600,1900,Min=-45,Max=45);b.link(held['from_node'],held['from_pin'],'limit','Value')
    b.fn('settle',K+'FInterpTo',1950,2100,Target=0,InterpSpeed=8);b.link('limit','ReturnValue','settle','Current');b.link(find(nodes,'UpdateTurnInPlace'),'DeltaSeconds','settle','DeltaTime')
    b.fn('choose',K+'SelectFloat',1950,1700);b.link('settle','ReturnValue','choose','A');b.link(held['from_node'],held['from_pin'],'choose','B');b.link('owned','ReturnValue','choose','bPickA')
    b.cut(held['from_node'],held['from_pin'],pick,'A');b.link('choose','ReturnValue',pick,'A')
    b.comment('First person body catch-up',['local','yaw','owned','limit','settle','choose']);b.run()
finally:h.release(owner,lease)
