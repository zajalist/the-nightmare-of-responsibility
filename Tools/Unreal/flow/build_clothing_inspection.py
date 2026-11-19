"""Three brief physical clue shots, using the director camera and owned input holds.

Safe to prepare offline. Run only in a coordinator-cleared non-PIE asset window.
No Player graph, sequence, actor transform, or wardrobe transition is rebuilt.
"""
import os,sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
sys.path.insert(0,'P:/FoA/Tools/Unreal/player')
from build_clothing_search import P,C,ROOM,BASE,INTER,K,GS,KS,call,fresh,finish,prepend
import hayba_call as h
from held_tool_graphs import Batch,inspect,find
SC='/Script/Engine.SceneComponent:'
PC='/Script/Engine.PlayerController:'
CTRL='/Script/Engine.Controller:'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
SHOTS=[('SearchWardrobeClue','Wardrobe',
        'A thread, caught on the wood. It goes toward the desk.'),
       ('SearchDeskClue','Desk',
        'One of its buttons. And drag marks, to the bed.'),
       ('SearchBedClue','Bed',
        'Too far back. I need something long.')]

def timer(b,ref,name,seconds,loop=False,x=0):
    b.fn(ref,KS+'K2_SetTimer',x,0,FunctionName=name,Time=seconds,bLooping=str(loop).lower())

def clear(b,ref,name,x=0):b.fn(ref,KS+'K2_ClearTimer',x,0,FunctionName=name)

def controller(b):b.fn('pc',GS+'GetPlayerController',0,600,PlayerIndex=0)

def build_clear_narration():
    fe='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
    hud='/Game/FoA/UI/Game/WBP_HUD.WBP_HUD_C'
    b,e=fresh('ClearClothingNarration')
    b.fn('fe',GS+'GetActorOfClass',300,0,ActorClass=fe)
    b.fn('validfe',KS+'IsValid',300,300);b.link('fe','ReturnValue','validfe','Object')
    b.node('found','branch',600,0);b.link('validfe','ReturnValue','found','Condition');b.chain(e,'fe','found')
    b.get('hud','HUD',900,300,fe);b.link('fe','ReturnValue','hud','self')
    b.node('shown','cast',900,0,class_path=hud);b.link('hud','HUD','shown','Object');b.chain('found','shown')
    b.fn('clear',hud+':ClearNarration',1500,0);b.link('shown','AsWBP HUD','clear','self');b.chain('shown','clear')
    finish(b,'Clear the previous thought before a new visual discovery')

def main():
    os.environ['HAYBA_AGENT_ID']='clothing_search'
    assert not call('editor_get_state')['pie_running']
    token=h.lease_acquire('clothing_search',['asset:'+P],ttl_s=240,wait_s=3)
    try:
        for name,typ,value in [('bClothingInspection','bool','false'),('ClothingInspectionAttempts','int','0'),
            ('ClothingInspectionDuration','float','1.6'),('bClothingContactShot','bool','false'),
            ('bClothingCameraWasActive','bool','true'),
            ('ClothingInspectionHome','transform',''),('ClothingInspectionFOV','float','90'),
            ('ClothingInspectionView','vector',''),('ClothingInspectionFocus','vector',''),
            ('ClothingInspectionReturn','object:/Script/Engine.Actor',''),('ClothingInspectionLine','text','')]:
            call('blueprint_add_variable',path=P,variable_name=name,variable_type=typ,default_value=value,
                 category='Clothing discovery',update_existing=True)
        names=['TryClothingInspection','FinishClothingInspection','CancelClothingInspection','ClearClothingNarration']+['QueueClothing'+s[1] for s in SHOTS]
        for name in names:
            if not h.call('blueprint_inspect_graph',dict(path=P,graph_name=name)).get('ok'):
                call('blueprint_add_function',path=P,function_name=name)
        build_clear_narration()

        for graph,clue,line in SHOTS:
            b,e=fresh('QueueClothing'+clue)
            b.fn('cancel',C+':CancelClothingInspection',250,0)
            b.fn('room',GS+'GetActorOfClass',500,0,ActorClass=ROOM)
            b.fn('valid',KS+'IsValid',500,250);b.link('room','ReturnValue','valid','Object')
            b.node('found','branch',750,0);b.link('valid','ReturnValue','found','Condition')
            b.chain(e,'cancel','room','found')
            last='found'
            for i,part in enumerate(('View','Focus')):
                var='Clue'+part+clue;ref=part.lower();x=1000+i*750
                b.get(ref,var,x,300,ROOM);b.link('room','ReturnValue',ref,'self')
                b.fn(ref+'world',SC+'K2_GetComponentLocation',x+250,300);b.link(ref,var,ref+'world','self')
                b.set(ref+'save','ClothingInspection'+part,x+500,0)
                b.link(ref+'world','ReturnValue',ref+'save','ClothingInspection'+part)
                b.chain(last,ref+'save');last=ref+'save'
            b.fn('text','/Script/Engine.KismetTextLibrary:Conv_StringToText',2500,300,InString=line)
            b.set('line','ClothingInspectionLine',2500,0);b.link('text','ReturnValue','line','ClothingInspectionLine')
            b.set('attempts','ClothingInspectionAttempts',2800,0);b.pin('attempts','ClothingInspectionAttempts',0)
            b.set('duration','ClothingInspectionDuration',2900,0);b.pin('duration','ClothingInspectionDuration',1.6)
            b.set('contact','bClothingContactShot',3000,0);b.pin('contact','bClothingContactShot','false')
            timer(b,'wait','TryClothingInspection',.1,True,3100)
            b.chain(last,'line','attempts','duration','contact','wait');finish(b,'Wait for the interaction to finish before inspecting')

        b,e=fresh('TryClothingInspection');controller(b)
        b.get('attempts','ClothingInspectionAttempts',0,300)
        b.fn('plus',K+'Add_IntInt',250,300,B=1);b.link('attempts','ClothingInspectionAttempts','plus','A')
        b.set('count','ClothingInspectionAttempts',250,0);b.link('plus','ReturnValue','count','ClothingInspectionAttempts')
        b.fn('bounded',K+'LessEqual_IntInt',500,300,B=30);b.link('plus','ReturnValue','bounded','A')
        b.node('time','branch',500,0);b.link('bounded','ReturnValue','time','Condition');b.chain(e,'count','time')
        b.fn('cancel',C+':CancelClothingInspection',750,-300);b.link('time','else','cancel','execute')
        b.fn('pawn',GS+'GetPlayerPawn',750,500,PlayerIndex=0)
        b.node('cast','cast',750,0,class_path=PLAYER);b.link('pawn','ReturnValue','cast','Object');b.chain('time','cast')
        for i,var in enumerate(('bCinematic','bInteractionLocked')):
            b.get(var,var,1000,300+i*150,PLAYER);b.link('cast','AsBP Fo APlayer',var,'self')
        b.get('contact','bClothingContactShot',1000,950)
        b.fn('ordinary',K+'Not_PreBool',1300,950);b.link('contact','bClothingContactShot','ordinary','A')
        b.fn('locked',K+'BooleanAND',1550,950);b.link('ordinary','ReturnValue','locked','A');b.link('bInteractionLocked','bInteractionLocked','locked','B')
        b.fn('busy',K+'BooleanOR',1300,300);b.link('bCinematic','bCinematic','busy','A');b.link('locked','ReturnValue','busy','B')
        b.fn('free',K+'Not_PreBool',1550,300);b.link('busy','ReturnValue','free','A')
        b.fn('view',PC+'GetViewTarget',1000,650);b.link('pc','ReturnValue','view','self')
        b.fn('ownview',K+'EqualEqual_ObjectObject',1300,650);b.link('view','ReturnValue','ownview','A');b.link('pawn','ReturnValue','ownview','B')
        b.fn('ready',K+'BooleanAND',1800,300);b.link('free','ReturnValue','ready','A');b.link('ownview','ReturnValue','ready','B')
        b.node('safe','branch',1800,0);b.link('ready','ReturnValue','safe','Condition');b.chain('cast','safe')
        clear(b,'stopwait','TryClothingInspection',2100)
        b.set('active','bClothingInspection',2400,0);b.pin('active','bClothingInspection','true')
        b.fn('clearold',C+':ClearClothingNarration',2550,0)
        b.set('return','ClothingInspectionReturn',2700,0);b.link('view','ReturnValue','return','ClothingInspectionReturn')
        b.get('camera','TopDownCamera',2100,500)
        b.fn('home',SC+'GetRelativeTransform',2400,500);b.link('camera','TopDownCamera','home','self')
        b.get('fov','FieldOfView',2400,700,'/Script/Engine.CameraComponent');b.link('camera','TopDownCamera','fov','self')
        b.set('savehome','ClothingInspectionHome',3000,0);b.link('home','ReturnValue','savehome','ClothingInspectionHome')
        b.set('savefov','ClothingInspectionFOV',3300,0);b.link('fov','FieldOfView','savefov','ClothingInspectionFOV')
        b.fn('wasactive','/Script/Engine.ActorComponent:IsActive',2700,850);b.link('camera','TopDownCamera','wasactive','self')
        b.set('saveactive','bClothingCameraWasActive',3400,0);b.link('wasactive','ReturnValue','saveactive','bClothingCameraWasActive')
        b.fn('activate','/Script/Engine.ActorComponent:Activate',3500,0,bReset='false');b.link('camera','TopDownCamera','activate','self')
        b.fn('cin',C+':PlayerCinematic',3600,0,Enable='true')
        b.fn('move',CTRL+'SetIgnoreMoveInput',3900,0,bNewMoveInput='true');b.link('pc','ReturnValue','move','self')
        b.fn('look',CTRL+'SetIgnoreLookInput',4200,0,bNewLookInput='true');b.link('pc','ReturnValue','look','self')
        b.get('where','ClothingInspectionView',3300,500);b.get('focus','ClothingInspectionFocus',3300,700)
        b.fn('aim',K+'FindLookAtRotation',3600,500);b.link('where','ClothingInspectionView','aim','Start');b.link('focus','ClothingInspectionFocus','aim','Target')
        b.fn('place',SC+'K2_SetWorldLocationAndRotation',4500,0,bSweep='false',bTeleport='true')
        b.link('camera','TopDownCamera','place','self');b.link('where','ClothingInspectionView','place','NewLocation');b.link('aim','ReturnValue','place','NewRotation')
        b.fn('zoom','/Script/Engine.CameraComponent:SetFieldOfView',4800,0,InFieldOfView=50);b.link('camera','TopDownCamera','zoom','self')
        b.node('self','self',4800,500)
        b.fn('show',PC+'SetViewTargetWithBlend',5100,0,BlendTime=.2,bLockOutgoing='true');b.link('pc','ReturnValue','show','self');b.link('self','self','show','NewViewTarget')
        timer(b,'finish','FinishClothingInspection',1.6,False,5400)
        b.get('duration','ClothingInspectionDuration',5100,700);b.link('duration','ClothingInspectionDuration','finish','Time')
        b.chain('safe','stopwait','active','clearold','return','savehome','savefov','saveactive','activate','cin','move','look','place','zoom','show')
        if h.call('blueprint_inspect_graph',dict(path=P,graph_name='OnClothingCameraReady')).get('ok'):
            b.fn('action',C+':OnClothingCameraReady',5250,0)
            b.get('stillactive','bClothingInspection',5250,900)
            b.node('actionguard','branch',5350,0);b.link('stillactive','bClothingInspection','actionguard','Condition')
            b.chain('show','action','actionguard','finish')
        else:b.chain('show','finish')
        finish(b,'Show the physical clue before the thought')

        b,e=fresh('CancelClothingInspection');controller(b)
        if h.call('blueprint_inspect_graph',dict(path=P,graph_name='AbortClothingChase')).get('ok'):
            b.fn('abort',C+':AbortClothingChase',0,-300);b.chain(e,'abort');e='abort'
        clear(b,'wait','TryClothingInspection',250);clear(b,'finish','FinishClothingInspection',500)
        b.get('active','bClothingInspection',500,300);b.node('owned','branch',750,0);b.link('active','bClothingInspection','owned','Condition')
        b.chain(e,'wait','finish','owned')
        b.set('off','bClothingInspection',1000,0);b.pin('off','bClothingInspection','false')
        b.get('return','ClothingInspectionReturn',1000,300)
        b.fn('view',PC+'GetViewTarget',1000,600);b.link('pc','ReturnValue','view','self');b.node('self','self',1000,800)
        b.fn('ours',K+'EqualEqual_ObjectObject',1300,600);b.link('view','ReturnValue','ours','A');b.link('self','self','ours','B')
        # GetViewTarget can still be the outgoing pawn during the 0.2s blend.
        # Restore that case too, otherwise Cancel would leave a pending camera cut.
        b.fn('outgoing',K+'EqualEqual_ObjectObject',1300,800);b.link('view','ReturnValue','outgoing','A');b.link('return','ClothingInspectionReturn','outgoing','B')
        b.fn('ourblend',K+'BooleanOR',1600,800);b.link('ours','ReturnValue','ourblend','A');b.link('outgoing','ReturnValue','ourblend','B')
        b.node('viewguard','branch',1300,0);b.link('ourblend','ReturnValue','viewguard','Condition')
        b.fn('restoreview',PC+'SetViewTargetWithBlend',1600,-150,BlendTime=0);b.link('pc','ReturnValue','restoreview','self');b.link('return','ClothingInspectionReturn','restoreview','NewViewTarget')
        b.get('camera','TopDownCamera',1600,500);b.get('home','ClothingInspectionHome',1600,700)
        b.fn('restore',SC+'K2_SetRelativeTransform',1900,0,bTeleport='true');b.link('camera','TopDownCamera','restore','self');b.link('home','ClothingInspectionHome','restore','NewTransform')
        b.get('fov','ClothingInspectionFOV',1900,500)
        b.fn('zoom','/Script/Engine.CameraComponent:SetFieldOfView',2200,0);b.link('camera','TopDownCamera','zoom','self');b.link('fov','ClothingInspectionFOV','zoom','InFieldOfView')
        b.get('wasactive','bClothingCameraWasActive',2200,700);b.node('activeguard','branch',2350,0);b.link('wasactive','bClothingCameraWasActive','activeguard','Condition')
        b.fn('deactivate','/Script/Engine.ActorComponent:Deactivate',2500,-200);b.link('camera','TopDownCamera','deactivate','self')
        b.fn('move',CTRL+'SetIgnoreMoveInput',2500,0,bNewMoveInput='false');b.link('pc','ReturnValue','move','self')
        b.fn('look',CTRL+'SetIgnoreLookInput',2800,0,bNewLookInput='false');b.link('pc','ReturnValue','look','self')
        b.fn('cin',C+':PlayerCinematic',3100,0,Enable='false')
        b.chain('owned','off','viewguard','restoreview','restore','zoom','activeguard','move','look','cin');b.link('viewguard','else','restore','execute')
        b.link('activeguard','else','deactivate','execute');b.chain('deactivate','move')
        finish(b,'Release only the camera and input holds acquired by this inspection')

        b,e=fresh('FinishClothingInspection')
        b.get('active','bClothingInspection',0,300);b.node('owned','branch',250,0);b.link('active','bClothingInspection','owned','Condition');b.chain(e,'owned')
        b.fn('cancel',C+':CancelClothingInspection',500,0)
        b.get('bed','SearchBed',500,300);b.fn('inter',BASE+':GetInteractor',750,300);b.link('bed','SearchBed','inter','self')
        b.get('line','ClothingInspectionLine',750,500)
        b.fn('thought',INTER+':Narrate',1000,0);b.link('inter','Interactor','thought','self');b.link('line','ClothingInspectionLine','thought','Line')
        if h.call('blueprint_inspect_graph',dict(path=P,graph_name='FinishClothingChaseShot')).get('ok'):
            b.get('chase','bClothingChaseActive',250,500);b.node('which','branch',400,0);b.link('chase','bClothingChaseActive','which','Condition')
            b.fn('action',C+':FinishClothingChaseShot',650,-300);b.chain('owned','which','action');b.link('which','else','cancel','execute');b.chain('cancel','thought')
        else:b.chain('owned','cancel','thought')
        finish(b,'The thought follows the completed visual discovery')

        for graph,clue,_ in SHOTS:
            ns,es=inspect(P,graph)
            if any(n['title']=='QueueClothing'+clue for n in ns):continue
            node=find(ns,'SetStage');assert not any(x['from_node']==node and x['from_pin']=='then' for x in es)
            b=Batch(P,graph);b.fn('inspect',C+':QueueClothing'+clue,5100,0);b.chain(node,'inspect');b.run()
        for graph in ('ResetClothingSearch','BeginMorning','FreezeForRollover'):
            prepend(graph,'CancelClothingInspection')
        # QA B2 (2026-11-10): the HUD hide/restore (SetStoryHUDHidden), the fade-hidden return (ReturnClothingInspection,
        # bClothingReturnDip, HandoffFadeUp at the end of FinishClothingInspection) are layered on these graphs by
        # Tools/Unreal/flow/patch_chase_cutaway.py (idempotent): run it after this rebuild.
        print('Clothing inspection camera and cancellation compiled/saved. Apply targeted line patch before runtime proof; then patch_chase_cutaway.py.')
    finally:h.release('clothing_search',token)

if __name__=='__main__':main()
