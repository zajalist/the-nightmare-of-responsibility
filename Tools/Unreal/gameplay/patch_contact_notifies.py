"""Commit interaction rows at actual montage notifies; timers only cancel stale work."""
import os,sys,json
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
OWNER='clothing_search';TOKEN=None
BASE='/Game/FoA/Gameplay/BP_Interactable';INTER='/Game/FoA/Gameplay/BPC_Interactor'
AN='/Game/FoA/Gameplay/AN_FoA_InteractionContact'
BC=BASE+'.BP_Interactable_C';IC=INTER+'.BPC_Interactor_C'
K='/Script/Engine.KismetMathLibrary:';KS='/Script/Engine.KismetSystemLibrary:'
MONTAGES=['/Game/FoA/Characters/Player/Montages/'+n for n in ['AM_FoA_PickUp_Floor','AM_FoA_PickUp_Table','AM_FoA_OpenDrawer','AM_FoA_TryLockedHandle','AM_FoA_KneelScrewdriver']]

def call(name,**args):
    r=h.call(name,args,owner=OWNER,lease=TOKEN);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True) and not d.get('failed'),d
    return d

def fresh(path,graph):
    ns,es=inspect(path,graph);entry=find(ns,graph)
    b=Batch(path,graph);old=[n['node_id'] for n in ns if n['node_id']!=entry]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    return b,entry

def patch_begin():
    ns,es=inspect(BASE,'BeginPendingRow')
    if any(n['title']=='Set PendingContactActor' for n in ns):return
    active=find(ns,'Set bPendingRow');after=next(e for e in es if e['from_node']==active and e['from_pin']=='then')
    inter=find(ns,'GetInteractor');b=Batch(BASE,'BeginPendingRow')
    b.node('selfactor','self',600,1300)
    b.set('owner','PendingContactActor',750,0,IC);b.link(inter,'Interactor','owner','self');b.link('selfactor','self','owner','PendingContactActor')
    b.cut(active,'then',after['to_node'],after['to_pin']);b.chain(active,'owner');b.link('owner','then',after['to_node'],after['to_pin'])
    timer=find(ns,'Set Timer by Function Name') if any(n['title']=='Set Timer by Function Name' for n in ns) else next(n['node_id'] for n in ns if any(p.get('default_value')=='FinishPendingRow' for p in n.get('pins',[])))
    delay=next(e for e in es if e['to_node']==timer and e['to_pin']=='Time')
    duration=next(n['node_id'] for n in ns if n['title'] in ('GetPlayLength','Get Play Length'))
    b.fn('watchdog',K+'Add_DoubleDouble',2700,1300,B=.2);b.link(duration,'ReturnValue','watchdog','A')
    b.cut(delay['from_node'],delay['from_pin'],timer,'Time');b.link('watchdog','ReturnValue',timer,'Time')
    b.run()

def clear_owner(b,ref,x):
    b.fn(ref+'inter',BC+':GetInteractor',x,600)
    b.set(ref,'PendingContactActor',x,0,IC);b.link(ref+'inter','Interactor',ref,'self')

def contact():
    b,e=fresh(BASE,'OnPendingContact')
    b.get('active','bPendingRow',0,300);b.get('montage','PendingMontage',0,500)
    b.fn('same',K+'EqualEqual_ObjectObject',300,500);b.link(e,'Animation','same','A');b.link('montage','PendingMontage','same','B')
    b.fn('valid',K+'BooleanAND',600,300);b.link('active','bPendingRow','valid','A');b.link('same','ReturnValue','valid','B')
    b.node('guard','branch',900,0);b.link('valid','ReturnValue','guard','Condition');b.chain(e,'guard')
    b.set('off','bPendingRow',1200,0);b.pin('off','bPendingRow',False)
    b.fn('timer',KS+'K2_ClearTimer',1500,0,FunctionName='FinishPendingRow')
    clear_owner(b,'clearowner',1800)
    b.fn('resume',IC+':SetSuspended',2100,0,bSuspended=False);b.link('clearownerinter','Interactor','resume','self')
    b.get('row','PendingRow',2100,500);b.fn('commit',BC+':CommitInteractionRow',2400,0);b.link('row','PendingRow','commit','Row')
    b.chain('guard','off','timer','clearowner','resume','commit');b.run()
    b,e=fresh(BASE,'FinishPendingRow');b.fn('cancel',BC+':CancelPendingRow',300,0,bRestoreScan=True);b.chain(e,'cancel');b.run()
    ns,es=inspect(BASE,'CancelPendingRow')
    if not any(n['title']=='Set PendingContactActor' for n in ns):
        off=find(ns,'Set bPendingRow');after=next(x for x in es if x['from_node']==off and x['from_pin']=='then')
        b=Batch(BASE,'CancelPendingRow');clear_owner(b,'clearowner',1000)
        b.cut(off,'then',after['to_node'],after['to_pin']);b.chain(off,'clearowner');b.link('clearowner','then',after['to_node'],after['to_pin']);b.run()

def notify():
    ns,_=inspect(AN,'Received_Notify')
    e=next(n['node_id'] for n in ns if any(p['name']=='MeshComp' and p['direction']=='output' for p in n.get('pins',[])))
    ret=next(n['node_id'] for n in ns if any(p['name']=='ReturnValue' and p['direction']=='input' for p in n.get('pins',[])))
    b=Batch(AN,'Received_Notify');old=[n['node_id'] for n in ns if n['node_id'] not in (e,ret)]
    if old:b.ops.append(dict(op='remove',node_ids=old))
    b.fn('owner','/Script/Engine.ActorComponent:GetOwner',0,300);b.link(e,'MeshComp','owner','self')
    b.fn('component','/Script/Engine.Actor:GetComponentByClass',300,300,ComponentClass=IC);b.link('owner','ReturnValue','component','self')
    b.node('inter','cast',600,0,class_path=IC);b.link('component','ReturnValue','inter','Object');b.chain(e,'inter')
    b.get('target','PendingContactActor',900,300,IC);b.link('inter','AsBPC Interactor','target','self')
    b.node('actor','cast',1200,0,class_path=BC);b.link('target','PendingContactActor','actor','Object');b.chain('inter','actor')
    b.fn('contact',BC+':OnPendingContact',1500,0);b.link('actor','AsBP Interactable','contact','self');b.link(e,'Animation','contact','Animation');b.chain('actor','contact')
    b.pin(ret,'ReturnValue',True);b.chain('contact',ret)
    b.link('inter','CastFailed',ret,'execute');b.link('actor','CastFailed',ret,'execute');b.run()

def main():
    global TOKEN
    os.environ['HAYBA_AGENT_ID']=OWNER
    assert not call('editor_get_state')['pie_running']
    assets=[BASE,INTER,AN]+MONTAGES
    TOKEN=h.lease_acquire(OWNER,['asset:'+p for p in assets],ttl_s=180,wait_s=3);os.environ['FOA_LEASE']=TOKEN
    try:
        call('python_exec_file',path='P:/FoA/Tools/Unreal/gameplay/contact_notify_assets.py',env={'FOA_CONTACT_PHASE':'declare'},resources=['asset:'+AN])
        call('blueprint_add_variable',path=INTER,variable_name='PendingContactActor',variable_type='object:/Script/Engine.Actor',category='Interaction',update_existing=True)
        call('blueprint_compile',path=INTER,save=True)
        info=call('blueprint_get_info',path=BASE)
        if 'OnPendingContact' not in info['functions']:
            call('blueprint_add_function',path=BASE,function_name='OnPendingContact',inputs=[dict(name='Animation',type='object:/Script/Engine.AnimSequenceBase')])
        contact();patch_begin();notify()
        call('python_exec_file',path='P:/FoA/Tools/Unreal/gameplay/contact_notify_assets.py',env={'FOA_CONTACT_PHASE':'markers'},resources=['asset:'+p for p in MONTAGES])
        call('asset_save',asset_paths=assets)
        Path('P:/FoA/Saved/Integration/contact_notify_applied.json').write_text(json.dumps(dict(saved=True,assets=assets,runtime_verified=False),indent=1))
    finally:h.release(OWNER,TOKEN);os.environ.pop('FOA_LEASE',None)
if __name__=='__main__':main()
