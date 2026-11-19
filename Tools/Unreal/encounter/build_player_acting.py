"""Owned, non-looping source-mesh battle gestures. Native graphs; no input locks/timers.
Coordinator clearance required: --apply. Uses existing UAL_Interact and UAL_Hit_Chest.
"""
import datetime,hashlib,json,os,shutil,sys
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Gameplay/Encounter/BP_Encounter';C=P+'.BP_Encounter_C'
GS='/Script/Engine.GameplayStatics:';K='/Script/Engine.KismetMathLibrary:';KS='/Script/Engine.KismetSystemLibrary:';AN='/Script/Engine.AnimInstance:'
MOVE='/Game/FoA/Gameplay/Encounter/PDA_Move.PDA_Move_C'
norm=lambda s:''.join(s.lower().split())
def call(name,**args):
    r=h.call(name,args);assert r.get('ok'),r;return r.get('data',{})
def fresh(name,inputs=()):
    r=h.call('blueprint_inspect_graph',dict(path=P,graph_name=name))
    if not r.get('ok'):call('blueprint_add_function',path=P,function_name=name,inputs=list(inputs))
    nodes,edges=inspect(P,name)
    e=next(n['node_id'] for n in nodes if norm(n['title'])==norm(name))
    assert len([n for n in nodes if n['node_id']!=e and norm(n['title'])!='comment'])==0,('Already authored; do not rebuild',name)
    return Batch(P,name),e
def finish(b):
    b.comment('Owned battle movement',[o['ref'] for o in b.ops if 'ref' in o]);return b.run()
def player_anim(b):
    b.fn('pawn',GS+'GetPlayerCharacter',0,500,PlayerIndex=0)
    b.get('mesh','Mesh',300,500,'/Script/Engine.Character');b.link('pawn','ReturnValue','mesh','self')
    b.fn('anim','/Script/Engine.SkeletalMeshComponent:GetAnimInstance',600,500);b.link('mesh','Mesh','anim','self')
def prepend(graph,fn,pins=()):
    nodes,edges=inspect(P,graph)
    if any(norm(n['title'])==norm(fn) for n in nodes):return {'already_hooked':True}
    e=next(n['node_id'] for n in nodes if norm(n['title'])==norm(graph))
    outgoing=[x for x in edges if x['from_node']==e and x['from_pin']=='then'];assert len(outgoing)==1
    b=Batch(P,graph);b.fn('acting_hook',C+':'+fn,-300,-400)
    for pin in pins:b.link(e,pin,'acting_hook',pin)
    x=outgoing[0];b.cut(e,'then',x['to_node'],x['to_pin']);b.chain(e,'acting_hook');b.link('acting_hook','then',x['to_node'],x['to_pin'])
    result=b.run();_,after=inspect(P,graph)
    key=lambda x:(x['from_node'],x['from_pin'],x['to_node'],x['to_pin'])
    assert {key(x) for x in edges if x!=outgoing[0]}<={key(x) for x in after}
    return result
def build():
    for name,kind in [('BattleActingMontage','object:/Script/Engine.AnimMontage'),('BattleActingAnim','object:/Script/Engine.AnimInstance')]:
        call('blueprint_add_variable',path=P,variable_name=name,variable_type=kind,category='Encounter|Animation',update_existing=True)
    b,e=fresh('ClearBattleActing')
    b.get('montage','BattleActingMontage',0,300);b.get('anim','BattleActingAnim',0,500)
    b.fn('valid_m',KS+'IsValid',300,300);b.link('montage','BattleActingMontage','valid_m','Object')
    b.fn('valid_a',KS+'IsValid',300,500);b.link('anim','BattleActingAnim','valid_a','Object')
    b.fn('both',K+'BooleanAND',600,300);b.link('valid_m','ReturnValue','both','A');b.link('valid_a','ReturnValue','both','B')
    b.node('guard','branch',900,0);b.link('both','ReturnValue','guard','Condition');b.chain(e,'guard')
    b.fn('stop',AN+'Montage_Stop',1200,0,InBlendOutTime=.12);b.link('anim','BattleActingAnim','stop','self');b.link('montage','BattleActingMontage','stop','Montage')
    b.set('clear','BattleActingMontage',1500,0)
    b.set('clear_anim','BattleActingAnim',1800,0)
    b.chain('guard','stop','clear','clear_anim');b.link('guard','else','clear','execute');finish(b)
    for name,clip,rate,blend in [('PlayBattleReach','UAL_Interact',1.4,.14),('PlayBattleFlinch','UAL_Hit_Chest',1.,.045)]:
        b,e=fresh(name);b.get('active','bActive',0,250);b.node('active_guard','branch',300,0);b.link('active','bActive','active_guard','Condition');b.chain(e,'active_guard')
        b.fn('clear',C+':ClearBattleActing',600,0);b.chain('active_guard','clear');player_anim(b)
        b.fn('valid',KS+'IsValid',900,500);b.link('anim','ReturnValue','valid','Object');b.node('guard','branch',900,0);b.link('valid','ReturnValue','guard','Condition');b.chain('clear','guard')
        b.fn('play',AN+'PlaySlotAnimationAsDynamicMontage',1200,0,Asset='/Game/FoA/Characters/Player/Anims/UAL/'+clip+'.'+clip,
             SlotNodeName='DefaultSlot',BlendInTime=blend,BlendOutTime=.16,InPlayRate=rate,LoopCount=1,BlendOutTriggerTime=-1,InTimeToStartMontageAt=0)
        b.link('anim','ReturnValue','play','self');b.chain('guard','play')
        b.set('owned','BattleActingMontage',1500,0);b.link('play','ReturnValue','owned','BattleActingMontage')
        b.set('source','BattleActingAnim',1800,0);b.link('anim','ReturnValue','source','BattleActingAnim');b.chain('play','owned','source');finish(b)
    b,e=fresh('PlayBattleAction')
    b.get('move','PendingMove',0,300);b.fn('valid',KS+'IsValid',300,300);b.link('move','PendingMove','valid','Object')
    b.node('guard','branch',600,0);b.link('valid','ReturnValue','guard','Condition');b.chain(e,'guard')
    for i,name in enumerate(('ComposureDelta','ResolveDelta')):
        b.get(name,name,600,300+i*180,MOVE);b.link('move','PendingMove',name,'self')
        b.fn(name+'_heal',K+'Greater_IntInt',900,300+i*180,B=0);b.link(name,name,name+'_heal','A')
    b.fn('restore',K+'BooleanOR',1200,300);b.link('ComposureDelta_heal','ReturnValue','restore','A');b.link('ResolveDelta_heal','ReturnValue','restore','B')
    b.node('physical','branch',1500,0);b.link('restore','ReturnValue','physical','Condition');b.chain('guard','physical')
    b.fn('reach',C+':PlayBattleReach',1800,150);b.link('physical','else','reach','execute');finish(b)
    b,e=fresh('ReactToBattleImpact',[dict(name='Who',type='object:/Script/Engine.Actor'),dict(name='Amount',type='int')])
    b.fn('pawn',GS+'GetPlayerPawn',0,300,PlayerIndex=0);b.fn('hero',K+'EqualEqual_ObjectObject',300,300);b.link(e,'Who','hero','A');b.link('pawn','ReturnValue','hero','B')
    b.fn('damage',K+'Less_IntInt',300,500,B=0);b.link(e,'Amount','damage','A')
    b.fn('hit',K+'BooleanAND',600,300);b.link('hero','ReturnValue','hit','A');b.link('damage','ReturnValue','hit','B')
    b.node('guard','branch',900,0);b.link('hit','ReturnValue','guard','Condition');b.chain(e,'guard')
    b.fn('flinch',C+':PlayBattleFlinch',1200,0);b.chain('guard','flinch');finish(b)
    return dict(action=prepend('ApplyPlayerMove','PlayBattleAction'),impact=prepend('PresentImpact','ReactToBattleImpact',('Who','Amount')),cleanup=prepend('EndEncounter','ClearBattleActing'))
if __name__=='__main__':
    assert sys.argv[1:]==['--apply'],'Prepare only; --apply requires coordinator clearance'
    owner=os.environ.get('FOA_AGENT','character_acting');os.environ['HAYBA_AGENT_ID']=owner
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire(owner,['asset:'+P],ttl_s=90,wait_s=3)
    try:
        backup=Path('P:/FoA/Saved/Backups/battle_acting')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
        shutil.copy2('P:/FoA/Content/FoA/Gameplay/Encounter/BP_Encounter.uasset',backup/'BP_Encounter.uasset')
        protected=['Content/FoA/Cinematics/LS_WakeUp_ManualPose.uasset','Content/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying.uasset','Content/FoA/Characters/Player/BP_FoAPlayer.uasset']
        hashes=lambda:{p:hashlib.sha256(Path('P:/FoA',p).read_bytes()).hexdigest() for p in protected}
        before=hashes();hooks=build();assert hashes()==before
        compiled=call('blueprint_compile',path=P,save=True);assert compiled['error_count']==0 and compiled['saved'],compiled
        Path('P:/FoA/Saved/Integration/cinematic_audit/battle_acting.json').write_text(json.dumps(dict(backup=str(backup),protected=before,hooks=hooks,compile=compiled),indent=2))
    finally:h.release(owner,token)
