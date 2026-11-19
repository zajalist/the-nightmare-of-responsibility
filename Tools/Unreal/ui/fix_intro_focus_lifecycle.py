"""Cancel delayed intro focus before handing input back to gameplay."""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal');import hayba_call as h
sys.path.insert(0,'P:/FoA/Tools/Unreal/player');from held_tool_graphs import Batch,inspect,find
P='/Game/FoA/UI/Intro/WBP_IntroStory';owner='clothing_search'
os.environ['HAYBA_AGENT_ID']=owner
token=h.lease_acquire(owner,['asset:'+P],ttl_s=90,wait_s=3);os.environ['FOA_LEASE']=token
try:
    assert not h.call('editor_get_state')['data']['pie_running']
    for graph,entry_title in [('Finish','Finish'),('EventGraph','Event Destruct')]:
        ns,es=inspect(P,graph)
        if any(n['title']=='Clear Timer by Function Name' and any(p.get('default_value')=='FocusSkip' for p in n['pins']) for n in ns):continue
        e=find(ns,entry_title);edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
        b=Batch(P,graph);b.fn('clear_focus','/Script/Engine.KismetSystemLibrary:K2_ClearTimer',-300,-300,FunctionName='FocusSkip')
        b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'clear_focus');b.link('clear_focus','then',edge['to_node'],edge['to_pin'])
        b.comment('Cancel pending intro focus before leaving',[e,'clear_focus']);b.run()
    ns,es=inspect(P,'FocusSkip')
    if not any(n['title']=='IsInViewport' for n in ns):
        e=find(ns,'FocusSkip');edge=next(x for x in es if x['from_node']==e and x['from_pin']=='then')
        b=Batch(P,'FocusSkip');b.get('done','bDone',-1000,300)
        b.fn('unfinished','/Script/Engine.KismetMathLibrary:Not_PreBool',-750,300);b.link('done','bDone','unfinished','A')
        b.fn('onscreen','/Script/UMG.UserWidget:IsInViewport',-1000,500)
        b.fn('active','/Script/Engine.KismetMathLibrary:BooleanAND',-500,300)
        b.link('unfinished','ReturnValue','active','A');b.link('onscreen','ReturnValue','active','B')
        b.node('guard','branch',-250,0);b.link('active','ReturnValue','guard','Condition')
        b.cut(e,'then',edge['to_node'],edge['to_pin']);b.chain(e,'guard');b.link('guard','then',edge['to_node'],edge['to_pin'])
        b.comment('Only the active story can take keyboard focus',[e,'done','unfinished','onscreen','active','guard']);b.run()
finally:
    h.release(owner,token);os.environ.pop('FOA_LEASE',None)
