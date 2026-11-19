"""Measured shirt seam meets the existing reach. Existing flight timer owns every update.
No actor translation, hand IK, rig, sleep or furniture changes. --apply is coordinated.
"""
import json,sys,os,datetime,shutil
from pathlib import Path
sys.path[:0]=['P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch,inspect
G='/Game/FoA/Gameplay/Encounter/BP_Garment';GC=G+'.BP_Garment_C'
E='/Game/FoA/Gameplay/Encounter/BP_Encounter';EC=E+'.BP_Encounter_C'
PC='/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
K='/Script/Engine.KismetMathLibrary:';SC='/Script/Engine.SceneComponent:'
KS='/Script/Engine.KismetSystemLibrary:';GS='/Script/Engine.GameplayStatics:'
SK='/Script/Engine.SkinnedMeshComponent:'
norm=lambda x:''.join(x.lower().split())
GEOMETRY=json.loads(Path('P:/FoA/Saved/Integration/cinematic_audit/shirt_contact_geometry.json').read_text())
ANCHOR=GEOMETRY['skin_anchor']
def call(cmd,**kw):
    r=h.call(cmd,kw);assert r.get('ok'),r;return r.get('data',{})
def fresh(p,name,inputs=()):
    info=h.call('blueprint_inspect_graph',dict(path=p,graph_name=name))
    if not info.get('ok'):call('blueprint_add_function',path=p,function_name=name,inputs=list(inputs))
    ns,es=inspect(p,name);entry=next(n['node_id'] for n in ns if norm(n['title'])==norm(name))
    assert len([n for n in ns if n['node_id']!=entry and norm(n['title'])!='comment'])==0,('Already authored',name)
    return Batch(p,name),entry
def done(b):
    b.comment('Measured seam contact',[o['ref'] for o in b.ops if 'ref' in o]);return b.run()
def hook(p,graph,function,at_end=False):
    ns,es=inspect(p,graph)
    if any(norm(n['title'])==norm(function) for n in ns):return
    if at_end:
        source=next(n['node_id'] for n in ns if norm(n['title']).startswith('setactorrotation'))
        assert not any(e['from_node']==source and e['from_pin']=='then' for e in es)
        b=Batch(p,graph);b.fn('contact_hook',GC+':'+function,3900,0);b.chain(source,'contact_hook')
    else:
        source=next(n['node_id'] for n in ns if norm(n['title'])==norm(graph))
        outgoing=[e for e in es if e['from_node']==source and e['from_pin']=='then'];assert len(outgoing)==1
        b=Batch(p,graph);b.fn('contact_hook',(GC if p==G else EC)+':'+function,-450,-300)
        edge=outgoing[0];b.cut(source,'then',edge['to_node'],edge['to_pin']);b.chain(source,'contact_hook');b.link('contact_hook','then',edge['to_node'],edge['to_pin'])
    b.run()
def build():
    for name,kind in [('bPlayerContact','bool'),('PlayerContactAt','double'),('PlayerContactHome','vector'),('PlayerContactHand','object:/Script/Engine.SkeletalMeshComponent')]:
        call('blueprint_add_variable',path=G,variable_name=name,variable_type=kind,category='Contact',update_existing=True)
    call('blueprint_add_variable',path=E,variable_name='ContactGarment',variable_type='object:'+GC,category='Encounter|Animation',update_existing=True)
    if not os.environ.get('FOA_CONTACT_RESUME'):
        # Restore only the owned body offset, before attack/equip/encounter cleanup.
        b,e=fresh(G,'StopPlayerContact');b.get('active','bPlayerContact',0,250);b.node('guard','branch',280,0);b.link('active','bPlayerContact','guard','Condition');b.chain(e,'guard')
        b.get('body','Body',300,300);b.get('home','PlayerContactHome',600,300)
        b.fn('restore',SC+'K2_SetRelativeLocation',600,0,bSweep=False,bTeleport=True);b.link('body','Body','restore','self');b.link('home','PlayerContactHome','restore','NewLocation')
        b.set('off','bPlayerContact',900,0);b.pin('off','bPlayerContact','false');b.set('clear','PlayerContactHand',1200,0);b.chain('guard','restore','off','clear');done(b)
        b,e=fresh(G,'StartPlayerContact',[dict(name='HandMesh',type='object:/Script/Engine.SkeletalMeshComponent')])
        b.fn('stop',GC+':StopPlayerContact',250,0);b.chain(e,'stop')
        b.get('rig','Rig',0,450);b.fn('mesh',SK+'GetSkinnedAsset',250,450);b.link('rig','Rig','mesh','self')
        b.fn('shirt',K+'EqualEqual_ObjectObject',550,450,B='/Game/FoA/Characters/Garments/SK_Garment_Shirt.SK_Garment_Shirt');b.link('mesh','ReturnValue','shirt','A')
        b.fn('valid',KS+'IsValid',250,650);b.link(e,'HandMesh','valid','Object');b.fn('both',K+'BooleanAND',800,450);b.link('shirt','ReturnValue','both','A');b.link('valid','ReturnValue','both','B')
        b.node('guard','branch',550,0);b.chain('stop','guard');b.link('both','ReturnValue','guard','Condition')
        b.get('body','Body',800,700);b.get('loc','RelativeLocation',1100,700,'/Script/Engine.SceneComponent');b.link('body','Body','loc','self')
        b.set('home','PlayerContactHome',850,0);b.link('loc','RelativeLocation','home','PlayerContactHome')
        b.fn('time',GS+'GetTimeSeconds',1100,450);b.set('at','PlayerContactAt',1150,0);b.link('time','ReturnValue','at','PlayerContactAt')
        b.set('hand','PlayerContactHand',1450,0);b.link(e,'HandMesh','hand','PlayerContactHand')
        b.set('on','bPlayerContact',1750,0);b.pin('on','bPlayerContact','true');b.chain('guard','home','at','hand','on');done(b)
    b,e=fresh(G,'StepPlayerContact');b.get('active','bPlayerContact',0,250);b.node('guard','branch',250,0);b.link('active','bPlayerContact','guard','Condition');b.chain(e,'guard')
    b.fn('now',GS+'GetTimeSeconds',0,500);b.get('at','PlayerContactAt',0,650);b.fn('elapsed',K+'Subtract_DoubleDouble',280,500);b.link('now','ReturnValue','elapsed','A');b.link('at','PlayerContactAt','elapsed','B')
    b.fn('expired',K+'GreaterEqual_DoubleDouble',550,500,B=1.3);b.link('elapsed','ReturnValue','expired','A');b.node('time_guard','branch',550,0);b.link('expired','ReturnValue','time_guard','Condition');b.chain('guard','time_guard')
    b.fn('stop',GC+':StopPlayerContact',850,-170);b.chain('time_guard','stop')
    b.get('hand','PlayerContactHand',550,750);b.fn('valid',KS+'IsValid',850,750);b.link('hand','PlayerContactHand','valid','Object');b.node('hand_guard','branch',850,100);b.link('valid','ReturnValue','hand_guard','Condition');b.link('time_guard','else','hand_guard','execute');b.link('hand_guard','else','stop','execute')
    b.fn('rise',K+'Divide_DoubleDouble',550,1000,B=.42);b.link('elapsed','ReturnValue','rise','A')
    b.fn('remain',K+'Subtract_DoubleDouble',550,1200,A=1.3);b.link('elapsed','ReturnValue','remain','B');b.fn('fall',K+'Divide_DoubleDouble',850,1200,B=.45);b.link('remain','ReturnValue','fall','A')
    b.fn('min',K+'FMin',1150,1000);b.link('rise','ReturnValue','min','A');b.link('fall','ReturnValue','min','B')
    b.fn('clamp',K+'FClamp',1450,1000,Min=0,Max=1);b.link('min','ReturnValue','clamp','Value')
    b.fn('ease',K+'FInterpEaseInOut',1750,1000,A=0,B=1,Exponent=2);b.link('clamp','ReturnValue','ease','Alpha')
    b.get('rig','Rig',850,1500);previous=None
    for i,row in enumerate(ANCHOR):
        y=1500+i*310;s='socket'+str(i);p='point'+str(i);w='weighted'+str(i)
        b.fn(s,SC+'GetSocketTransform',1150,y,InSocketName=row['bone'],TransformSpace='RTS_World');b.link('rig','Rig',s,'self')
        b.fn(p,K+'TransformLocation',1450,y,Location=','.join(str(v) for v in row['local']));b.link(s,'ReturnValue',p,'T')
        b.fn(w,K+'Multiply_VectorFloat',1750,y,B=row['weight']);b.link(p,'ReturnValue',w,'A')
        if previous:
            add='sum'+str(i);b.fn(add,K+'Add_VectorVector',2050+i*250,y);b.link(previous,'ReturnValue',add,'A');b.link(w,'ReturnValue',add,'B');previous=add
        else:previous=w
    b.fn('tip_socket',SC+'GetSocketTransform',1150,600,InSocketName='index_03_l',TransformSpace='RTS_World');b.link('hand','PlayerContactHand','tip_socket','self')
    b.fn('target',K+'TransformLocation',1450,600,Location=','.join(str(v) for v in GEOMETRY['fingertip']['local']));b.link('tip_socket','ReturnValue','target','T')
    b.get('body','Body',2050,0);b.get('home','PlayerContactHome',2050,300)
    b.fn('parent',SC+'GetAttachParent',2350,300);b.link('body','Body','parent','self')
    b.fn('parent_world',SC+'K2_GetComponentToWorld',2650,300);b.link('parent','ReturnValue','parent_world','self')
    b.fn('home_world',K+'TransformLocation',2950,300);b.link('parent_world','ReturnValue','home_world','T');b.link('home','PlayerContactHome','home_world','Location')
    b.fn('current',SC+'K2_GetComponentLocation',2350,600);b.link('body','Body','current','self')
    b.fn('to_hand',K+'Subtract_VectorVector',2950,600);b.link('target','ReturnValue','to_hand','A');b.link(previous,'ReturnValue','to_hand','B')
    b.fn('goal',K+'Add_VectorVector',3250,600);b.link('current','ReturnValue','goal','A');b.link('to_hand','ReturnValue','goal','B')
    b.fn('blend',K+'VLerp',3550,300);b.link('home_world','ReturnValue','blend','A');b.link('goal','ReturnValue','blend','B');b.link('ease','ReturnValue','blend','Alpha')
    b.fn('place',SC+'K2_SetWorldLocation',3850,100,bSweep=False,bTeleport=True);b.link('body','Body','place','self');b.link('blend','ReturnValue','place','NewLocation');b.chain('hand_guard','place');done(b)
    # Encounter owns the contact garment just as it owns its dynamic montage.
    b,e=fresh(E,'ClearPlayerContact');b.get('garment','ContactGarment',0,300);b.fn('valid',KS+'IsValid',300,300);b.link('garment','ContactGarment','valid','Object');b.node('guard','branch',300,0);b.link('valid','ReturnValue','guard','Condition');b.chain(e,'guard')
    b.fn('stop',GC+':StopPlayerContact',600,0);b.link('garment','ContactGarment','stop','self');b.set('clear','ContactGarment',900,0);b.chain('guard','stop','clear');b.link('guard','else','clear','execute');done(b)
    b,e=fresh(E,'BeginPlayerContact');b.fn('target',EC+':TargetGarment',0,300);b.fn('valid',KS+'IsValid',300,300);b.link('target','Garment','valid','Object');b.node('guard','branch',300,0);b.link('valid','ReturnValue','guard','Condition');b.chain(e,'guard')
    b.fn('pawn',GS+'GetActorOfClass',300,600,ActorClass=PC);b.get('hand','Body',600,600,PC);b.link('pawn','ReturnValue','hand','self')
    b.set('own','ContactGarment',600,0);b.link('target','Garment','own','ContactGarment')
    b.fn('start',GC+':StartPlayerContact',900,0);b.link('target','Garment','start','self');b.link('hand','Body','start','HandMesh');b.chain('guard','pawn','own','start');done(b)
    hook(G,'StepBattleMotion','StepPlayerContact',True)
    for graph in ('StopBattleMotion','KickBattleMotion'):hook(G,graph,'StopPlayerContact')
    hook(E,'ClearBattleActing','ClearPlayerContact')
    ns,es=inspect(E,'PlayBattleReach');source=next(n['node_id'] for n in ns if norm(n['title'])=='setbattleactinganim')
    assert not any(x['from_node']==source and x['from_pin']=='then' for x in es)
    b=Batch(E,'PlayBattleReach');b.fn('contact',EC+':BeginPlayerContact',2100,0);b.chain(source,'contact');b.run()
if __name__=='__main__':
    assert sys.argv[1:]==['--apply'];os.environ['HAYBA_AGENT_ID']='character_contact'
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire('character_contact',['asset:'+G,'asset:'+E],ttl_s=120,wait_s=3)
    try:
        backup=Path('Saved/Backups/player_contact')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');backup.mkdir(parents=True)
        for p in (G,E):shutil.copy2('Content'+p.removeprefix('/Game')+'.uasset',backup/(p.rsplit('/',1)[1]+'.uasset'))
        build();Path('Saved/Integration/cinematic_audit/player_contact_apply.json').write_text(json.dumps(dict(backup=str(backup),anchor=ANCHOR),indent=2))
    finally:h.release('character_contact',token)
