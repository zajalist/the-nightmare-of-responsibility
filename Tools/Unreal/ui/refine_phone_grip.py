"""Keep the physical grip below the screen; label the portable action correctly."""
import sys,json
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Game/BP_Phone';W='/Game/FoA/UI/Game/WBP_Phone'
assert not h.call('editor_get_state')['data']['pie_running']
owner=h.agent_id();lease=h.lease_acquire(owner,['asset:'+P,'asset:'+W],ttl_s=30,wait_s=3)
try:
    fit=json.loads(Path('P:/FoA/Saved/UIShots/phone_grip_fit.json').read_text())
    nodes,_=inspect(P,'OpenPhone');position=next(n['node_id'] for n in nodes if n['title'].replace(' ','')=='SetActorRelativeLocation')
    b=Batch(P,'OpenPhone');b.pin(position,'NewRelativeLocation','(X=%0.9f,Y=%0.9f,Z=%0.9f)'%tuple(fit['relative_location']));b.run()
    nodes,edges=inspect(W,'Refresh');branch=find(nodes,'Branch');director=find(nodes,'Get Director')
    old=next(e for e in edges if e['to_node']==branch and e['to_pin']=='Condition')
    b=Batch(W,'Refresh');b.get('awake','bWakeDone',3300,550,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C');b.link(director,'Director','awake','self')
    b.fn('away','/Script/Engine.KismetMathLibrary:BooleanOR',3500,500);b.link(old['from_node'],old['from_pin'],'away','A');b.link('awake','bWakeDone','away','B')
    b.cut(old['from_node'],old['from_pin'],branch,'Condition');b.link('away','ReturnValue',branch,'Condition');b.comment('Portable phone action',['awake','away']);b.run()
finally:h.release(owner,lease)
