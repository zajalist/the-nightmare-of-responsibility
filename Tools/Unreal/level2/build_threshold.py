"""Native Hayba graphs for new transition assets. One named step per scoped lease.
No story asset is edited. Runtime behavior is entirely Blueprint.
"""
import os
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import threshold_data as D
import hayba_call as h
import editor_lock
from build_drive import G, call, cls, GS, K, A, SL
from held_tool_graphs import Batch, inspect

BP=D.BP
HUD=D.ROOT+'/WBP_DreamThreshold'
STORY='/Game/FoA/Gameplay/BP_BeatDirector'
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
DREAM='/Game/FoA/PostProcess/BP_DreamDirector'
FX='/Game/FoA/Level2/Blueprints/BP_SplatFXDirector'
PHONE='/Game/FoA/UI/Game/BP_Phone'
JOURNEY='/Game/FoA/Level2/Journey/BP_L2Journey'
FRONT='/Game/FoA/UI/Framework/BP_FoAFrontEnd'
AUDIO='/Game/FoA/Audio/BP_RoomAudio'
MPC='/Game/FoA/Level2/Materials/MPC_L2'
ML='/Script/Engine.KismetMaterialLibrary:'
PC='/Script/Engine.Controller:'
CAM='/Script/Engine.PlayerCameraManager:'
LSP='/Script/LevelSequence.LevelSequencePlayer:'
MSP='/Script/MovieScene.MovieSceneSequencePlayer:'
LSA='/Script/LevelSequence.LevelSequenceActor'
ORIGIN='/Script/LevelSequence.DefaultLevelSequenceInstanceData'
FUNCS=['Begin','Watch','StartThreshold','OpenDoor','EnterDream','HideCard','StartPath','Step','BeginFall','PlayFall','Land','EndFade','Finish','Abort','RestoreRoom',
       'RestartFromRoad','ReplayFall','BeginEnding','EndingColour','EndGame','MuteTestFX','CleanupOwned','UnloadDream','UnloadCity']
FUNCS += ['ResetPath','StepPath','StartHeadache','StepBreath','FinishBreath','RecoverPath','RefreshPath','HidePath']
FUNCS += ['CheckCitySectors']

def ref(g,name,path,pin):
    actor=g.do(GS+'GetActorOfClass',ActorClass=cls(path))
    obj=g.cast(actor,cls(path),pin)
    g.setv(name,obj)
    return g.getv(name)

def external(g,name,value,target,path):
    r=g.ref();g.set(r,name,0,0,path);g.put(r,'self',target);g.put(r,name,value)
    g.chain(g.tail,r);g.tail=r

def timer(g,name,seconds,loop=False):
    g.do(SL+'K2_SetTimer',FunctionName=name,Time=seconds,bLooping=loop)

def fade(g,start,end,seconds,white=False):
    cm=g.f(GS+'GetPlayerCameraManager',PlayerIndex=0)
    g.do(CAM+'StartCameraFade',self=cm,FromAlpha=start,ToAlpha=end,Duration=seconds,
         Color='(R=1,G=1,B=1,A=1)' if white else '(R=0,G=0,B=0,A=1)',bShouldFadeAudio=False,bHoldWhenFinished=True)

def sequence(g,path,origin):
    reduced=g.math('Greater_DoubleDouble',A=g.do(ML+'GetScalarParameterValue',Collection='/Game/FoA/PostProcess/MPC_Dream',ParameterName='ReduceMotion'),B=.5)
    selected=g.math('SelectObject',A=path+'_ReducedMotion',B=path,bSelectA=reduced)
    asset=g.cast(selected,'/Script/LevelSequence.LevelSequence','Level Sequence')
    seq=g.do(LSP+'CreateLevelSequencePlayer',LevelSequence=asset,
             Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True,bPauseAtEnd=True)')
    actor=(seq[0],'OutActor')
    g.setv('Sequence',seq)
    g.setv('SequenceActor',actor)
    external(g,'bOverrideInstanceData',True,actor,LSA)
    r=g.ref();g.get(r,'DefaultInstanceData',0,0,LSA);g.put(r,'self',actor)
    data=g.cast((r,'DefaultInstanceData'),ORIGIN,'Default Level Sequence Instance Data')
    external(g,'TransformOriginActor',origin,data,ORIGIN)
    if path==D.LS:
        arr=g.ref();g.node(arr,'make_array',0,0);g.put(arr,'[0]',g.getv('Player'))
        g.do(LSA+':SetBindingByTag',self=actor,BindingTag='Player',Actors=(arr,'Array'),bAllowBindingsFromAsset=False)
    g.do(MSP+'Play',self=g.getv('Sequence'))

def movement(g,enabled):
    p=g.getv('Player')
    g.do(cls(PLAYER)+':SetCinematic',self=p,bEnable=not enabled)
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',p)
    component=(r,'CharacterMovement')
    g.do('/Script/Engine.CharacterMovementComponent:SetMovementMode',self=component,NewMovementMode='MOVE_Walking' if enabled else 'MOVE_None')
    g.do(A+'SetActorEnableCollision',self=p,bNewActorEnableCollision=enabled)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    if enabled:
        g.do(PC+'ResetIgnoreMoveInput',self=pc);g.do(PC+'ResetIgnoreLookInput',self=pc)
        g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=pc,NewViewTarget=p,BlendTime=0)

def color(g,amount,seconds):
    g.do(cls(DREAM)+':SetColorReveal',self=g.getv('Grade'),Amount=amount,BlendSeconds=seconds)

def music(g,state):
    external(g,'MusicOverride',state,g.getv('Audio'),cls(AUDIO))

def fx(g,start_offset,radius,centre):
    now=g.f(GS+'GetTimeSeconds')
    external(g,'EventStartTime',g.math('Subtract_DoubleDouble',A=now,B=start_offset),g.getv('Splat'),cls(FX))
    external(g,'SandRadius',radius,g.getv('Splat'),cls(FX))
    external(g,'SandCentre',centre,g.getv('Splat'),cls(FX))

def skeleton():
    if not h.call('blueprint_get_info',{'path':HUD}).get('ok'):
        call('ui_create_widget',path=D.ROOT,name='WBP_DreamThreshold')
    wi=call('blueprint_get_info',path=HUD)
    if 'Refresh' not in wi['functions']:
        call('blueprint_add_function',path=HUD,function_name='Refresh',inputs=[dict(name=n,type='text') for n in ('Title','Hint')])
    if 'RefreshPath' not in wi['functions']:
        call('blueprint_add_function',path=HUD,function_name='RefreshPath',inputs=[dict(name=n,type=t) for n,t in
             [('Thought','text'),('Hint','text'),('Progress','float'),('ShowMeter','bool'),('Active','bool')]])
    call('blueprint_compile',path=HUD);call('asset_save',asset_paths=[HUD])
    if not h.call('blueprint_get_info',{'path':BP}).get('ok'):
        call('blueprint_create',package_path=BP,name='BP_DreamThreshold',parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=BP)
    have={v['name'] for v in info['variables']}
    variables=[('Phase','int','0'),('Age','float','0'),('ReadyAge','float','0'),
      ('OldWalkSpeed','float','200'),('Replay','bool','false'),('Player','object:'+cls(PLAYER),''),('Story','object:'+cls(STORY),''),
      ('Grade','object:'+cls(DREAM),''),('Phone','object:'+cls(PHONE),''),('Splat','object:'+cls(FX),''),
      ('Audio','object:'+cls(AUDIO),''),
      ('Stream','object:/Script/Engine.LevelStreamingDynamic',''),('Sequence','object:/Script/LevelSequence.LevelSequencePlayer',''),
      ('SequenceActor','object:/Script/LevelSequence.LevelSequenceActor',''),('Journey','object:'+cls(JOURNEY),''),
      ('DriveRoad','object:/Script/Engine.Actor',''),('DriveCar','object:/Script/Engine.Actor',''),('DriveMeteor','object:/Script/Engine.Actor',''),
      ('CityStream','object:/Script/Engine.LevelStreamingDynamic',''),('CityReady','bool','false'),('HUD','object:'+cls(HUD),'')]
    variables += [('RouteBeat','int','0'),('BreathState','int','0'),('BreathAge','float','0'),
                  ('ReleaseAge','float','0'),('BreathArmed','bool','false')]
    for n,t,v in variables:
        if n not in have:call('blueprint_add_variable',path=BP,variable_name=n,variable_type=t,default_value=v,category='Threshold')
    for n in FUNCS:
        if n not in info['functions']:
            inputs=[dict(name='Delta',type='float')] if n in ('Step','StepPath') else [dict(name='Index',type='int')] if n in ('MuteTestFX','CleanupOwned') else []
            if n=='StepBreath':inputs=[dict(name='Delta',type='float'),dict(name='Down',type='bool')]
            call('blueprint_add_function',path=BP,function_name=n,inputs=inputs)
    cs={c['name'] for c in info.get('components',[])}
    for n,t in [('Root','SceneComponent'),('Floor','StaticMeshComponent'),('RouteGuide','SceneComponent'),
                ('GuideBed','StaticMeshComponent'),('GuideExit','TextRenderComponent')]+[('Guide'+str(i),'StaticMeshComponent') for i in range(len(D.GUIDE_Y))]:
        if n not in cs:call('blueprint_add_component',path=BP,component_name=n,component_class_path='/Script/Engine.'+t)
    call('blueprint_compile',path=BP);call('asset_save',asset_paths=[BP])

def widget():
    if 'Txt_Title' not in str(call('ui_query',path=HUD)):
        children=[]
        for name,size,anchor,color in [('Title',60,.5,[.025,.02,.02,1]),('Hint',26,.88,[.94,.94,.94,1])]:
            children.append({'class':'TextBlock','name':'Txt_'+name,
                'slot_props':{'anchors_min':[.5,anchor],'anchors_max':[.5,anchor],
                              'alignment':[.5,.5],'position':[0,0],'size':[900,90]},
                'properties':{'Text':'','Justification':'Center','Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                              'TypefaceFontName':'SemiBold','Size':size},'ColorAndOpacity':{'SpecifiedColor':color}}})
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=children)
        for name in ('Title','Hint'):call('ui_set_variable',widget_blueprint_path=HUD,widget_name='Txt_'+name,is_variable=True)
        call('ui_compile_widget',widget_blueprint_path=HUD)
    g=G(HUD,'Refresh')
    for name in ('Title','Hint'):g.do('/Script/UMG.TextBlock:SetText',self=g.getv('Txt_'+name),InText=g.arg(name))
    g.finish()
    for name,anchor in [('Title',.5),('Hint',.88)]:
        result=call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Txt_'+name,
            slot_props={'anchors_min':[.5,anchor],'anchors_max':[.5,anchor],
                        'alignment':[.5,.5],'position':[0,0],'size':[900,90]})
        assert not result.get('unknown_slot_props') and not result.get('rejected_properties'),result
    call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Txt_Hint',
         properties={'ShadowOffset':{'X':1,'Y':2},'ShadowColorAndOpacity':[0,0,0,1]})
    call('ui_compile_widget',widget_blueprint_path=HUD);call('asset_save',asset_paths=[HUD])

def text(g,title='',hint=''):
    g.do(cls(HUD)+':Refresh',self=g.getv('HUD'),Title=title,Hint=hint)

def begin():
    g=G(BP,'Begin')
    ref(g,'Player',PLAYER,'BP Fo APlayer');ref(g,'Story',STORY,'BP Beat Director')
    ref(g,'Grade',DREAM,'BP Dream Director');ref(g,'Phone',PHONE,'BP Phone')
    ref(g,'Audio',AUDIO,'BP Room Audio')
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',g.getv('Player'))
    c=(r,'CharacterMovement')
    r=g.ref();g.get(r,'MaxWalkSpeed',0,0,'/Script/Engine.CharacterMovementComponent');g.put(r,'self',c)
    g.setv('OldWalkSpeed',(r,'MaxWalkSpeed'))
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    r=g.ref();g.node(r,'create_widget',0,0);g.put(r,'Class',cls(HUD));g.put(r,'OwningPlayer',pc)
    g.chain(g.tail,r);g.tail=r;g.setv('HUD',(r,'ReturnValue'))
    g.do('/Script/UMG.UserWidget:AddToViewport',self=g.getv('HUD'),ZOrder=30)
    timer(g,'Watch',.2,True)
    g.finish()

def watch():
    g=G(BP,'Watch')
    beat=g.getv('BeatIndex',g.getv('Story'),STORY)
    closed=g.math('Not_PreBool',A=g.getv('bOpen',g.getv('Phone'),PHONE))
    idle=g.math('Not_PreBool',A=g.getv('bCinematic',g.getv('Player'),PLAYER))
    at=g.f(A+'K2_GetActorLocation',self=g.getv('Player'))
    door=g.f(A+'K2_GetActorLocation',self=g.getv('DoorFrame',g.getv('Story'),STORY))
    nearby=g.math('Less_DoubleDouble',A=g.math('Vector_Distance2D',V1=at,V2=door),B=200)
    ready=g.math('BooleanAND',A=g.math('EqualEqual_IntInt',A=beat,B=10),B=g.math('BooleanAND',A=g.math('BooleanAND',A=closed,B=idle),B=nearby))
    b=g.branch(ready);g.side(b)
    g.setv('ReadyAge',g.math('Add_DoubleDouble',A=g.getv('ReadyAge'),B=.2))
    wait=g.branch(g.math('GreaterEqual_DoubleDouble',A=g.getv('ReadyAge'),B=1));g.side(wait);g.own('StartThreshold')
    g.side(b,False);g.setv('ReadyAge',0);g.finish()

def start():
    g=G(BP,'StartThreshold')
    gate=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=0));g.side(gate)
    g.setv('Phase',1);g.setv('Age',0)
    music(g,'Dream')
    g.do(SL+'K2_ClearTimer',FunctionName='Watch')
    g.do(SL+'K2_ClearTimer',Object=g.getv('Story'),FunctionName='CheckWalkedOut')
    g.do(cls(STORY)+':SetStoryHUDHidden',self=g.getv('Story'),Hidden=True)
    movement(g,False)
    stream=g.do('/Script/Engine.LevelStreamingDynamic:LoadLevelInstance',LevelName=D.DREAM_MAP,Location=','.join(map(str,D.OFFSET)),Rotation='0,0,0')
    g.setv('Stream',stream)
    okay=g.branch((stream[0],'bOutSuccess'));g.side(okay)
    sequence(g,D.LS,g.getv('DoorFrame',g.getv('Story'),STORY))
    timer(g,'OpenDoor',3)
    timer(g,'EnterDream',D.THRESHOLD_SECONDS)
    g.side(okay,False);g.own('Abort');g.finish()


def opendoor():
    g=G(BP,'OpenDoor')
    door=g.getv('Door',g.getv('Story'),STORY)
    target=g.cast(door,'/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C','BP Interactable')
    g.do('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C:Interact',self=target,Verb='Notify',HeldItem='Open')
    g.finish()

def enter(job_look=False):
    g=G(BP,'EnterDream')
    loaded=g.branch(g.f('/Script/Engine.LevelStreaming:IsLevelVisible',self=g.getv('Stream')));g.side(loaded)
    g.do(MSP+'Stop',self=g.getv('Sequence'))
    g.do(A+'K2_DestroyActor',self=g.getv('SequenceActor'))
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation=','.join(map(str,D.ENTRY)),bSweep=False,bTeleport=True)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=pc,NewViewTarget=g.getv('Player'),BlendTime=0)
    g.do(PC+'SetControlRotation',self=pc,NewRotation=g.math('MakeRotator',Yaw=90))
    # the body too: while still cinematic the first-person view is clamped around the body's facing (coordinator 2026-11-18)
    g.do(A+'K2_SetActorRotation',self=g.getv('Player'),NewRotation=g.math('MakeRotator',Yaw=90),bTeleportPhysics=True)
    g.do(A+'K2_SetActorLocation',NewLocation=','.join(map(str,D.OFFSET)),bSweep=False,bTeleport=True)
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled',self=g.getv('Floor'),NewType='QueryAndPhysics')
    ref(g,'Splat',FX,'BP Splat FXDirector')
    fx(g,8,1500,f'(R={D.OFFSET[0]},G={D.OFFSET[1]},B=0,A=0)')
    color(g,1,3)
    if job_look:external(g,'BlendWeight',1.,g.getv('L2DreamMotion'),'/Script/Engine.PostProcessComponent')
    text(g,title='Day one.')
    fade(g,1,0,2,True)
    g.setv('Phase',2);g.setv('Age',0)
    timer(g,'HideCard',1.2);timer(g,'StartPath',D.ASSEMBLY_SECONDS)
    g.side(loaded,False)
    timed=g.branch(g.math('Greater_DoubleDouble',A=g.getv('Age'),B=25));g.side(timed);g.own('Abort')
    g.side(timed,False);timer(g,'EnterDream',.2)
    g.finish()

def hidecard():
    g=G(BP,'HideCard');text(g);g.finish()

def path():
    g=G(BP,'StartPath')
    movement(g,True)
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',g.getv('Player'))
    c=(r,'CharacterMovement')
    external(g,'MaxWalkSpeed',D.PATH_SPEED,c,'/Script/Engine.CharacterMovementComponent')
    g.setv('Phase',3);g.setv('Age',0)
    g.own('ResetPath')
    for n,v in [('Torment',0),('ShakeAge',0),('TormentGoal',.15)]:g.setv(n,v)
    g.do('/Script/Engine.SceneComponent:SetVisibility',self=g.getv('RouteGuide'),bNewVisibility=True,bPropagateToChildren=True)
    g.do('/Script/Engine.AudioComponent:Play',self=g.getv('DreadAudio'),StartTime=0)
    g.own('Think',Line='Colour. Since when.',Seconds=3.5)
    text(g);g.own('RefreshPath')
    city=g.do('/Script/Engine.LevelStreamingDynamic:LoadLevelInstance',LevelName=D.CITY_MAP,Location='0,0,0',Rotation='0,0,0')
    g.setv('CityStream',city)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=g.getv('CityStream'),bInShouldBeVisible=False)
    g.finish()

def step():
    g=G(BP,'Step')
    g.setv('Age',g.math('Add_DoubleDouble',A=g.getv('Age'),B=g.arg('Delta')))
    b=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=3));g.side(b)
    g.own('StepPath',Delta=g.arg('Delta'));g.finish()

def beginfall():
    g=G(BP,'BeginFall')
    normal=g.math('BooleanAND',A=g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=3),B=path_complete(g))
    # F6 isolates this exact context; ordinary QA_Play must earn both breaths.
    gi='/Game/FoA/Gameplay/GI_FoA'
    game=g.cast(g.f(GS+'GetGameInstance'),cls(gi),'GI Fo A')
    debug=g.f('/Script/Engine.KismetStringLibrary:EqualEqual_StrStr',A=g.getv('SaveSlot',game,gi),B='FoA_QA_DebugSkip')
    debug=g.math('BooleanAND',A=debug,B=g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=3))
    normal=g.math('BooleanOR',A=normal,B=debug)
    replay=g.math('BooleanAND',A=g.getv('Replay'),B=g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=2))
    gate=g.branch(g.math('BooleanOR',A=normal,B=replay));g.side(gate)
    g.own('HidePath');g.setv('Phase',4);g.setv('Age',0)
    text(g)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CityStream')));g.side(valid)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=g.getv('CityStream'),bInShouldBeVisible=True)
    g.own('PlayFall')
    g.side(valid,False)
    city=g.do('/Script/Engine.LevelStreamingDynamic:LoadLevelInstance',LevelName=D.CITY_MAP,Location='0,0,0',Rotation='0,0,0')
    g.setv('CityStream',city)
    g.own('PlayFall');g.finish()


def playfall():
    g=G(BP,'PlayFall')
    g.do(A+'SetActorTickEnabled',self=g.getv('Splat'),bEnabled=True)
    movement(g,False)
    # The downward camera starts inside the capsule. The fall is a POV shot.
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=True)
    loc=g.f(A+'K2_GetActorLocation',self=g.getv('Player'))
    g.do(A+'K2_SetActorLocation',NewLocation=loc,bSweep=False,bTeleport=True)
    fx(g,4,320,g.math('Conv_VectorToLinearColor',InVec=loc))
    color(g,0,3)
    g.do(cls(STORY)+':SetStoryHUDHidden',self=g.getv('Story'),Hidden=True)
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled',self=g.getv('Floor'),NewType='NoCollision')
    selfnode=g.ref();g.node(selfnode,'self',0,0)
    sequence(g,D.FALL,(selfnode,'self'))
    timer(g,'Land',4.2)
    g.finish()

def land():
    g=G(BP,'Land')
    g.setv('Phase',5)
    g.do(MSP+'Pause',self=g.getv('Sequence'))
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CityStream')));g.side(valid)
    ready=g.branch(g.f('/Script/Engine.LevelStreaming:IsLevelVisible',self=g.getv('CityStream')));g.side(ready)
    sectors=None
    if D.CITY_MAP.endswith('/L_L2_CityStream'):
        g.own('CheckCitySectors');sectors=g.branch(g.getv('CityReady'));g.side(sectors)
    else:g.setv('CityReady',True)
    g.do(A+'SetActorTickEnabled',self=g.getv('Splat'),bEnabled=False)
    g.do(A+'K2_SetActorLocation',NewLocation='9000,0,-63',bSweep=False,bTeleport=True)
    text(g)
    g.do(MSP+'Play',self=g.getv('Sequence'))
    fade(g,1,0,.6)
    timer(g,'EndFade',2.8);timer(g,'Finish',3.8)
    if sectors:
        g.side(sectors,False);fade(g,1,1,.1)
        text(g,title='Queen Street')  # level2: a place card, no loading notice
        timed=g.branch(g.math('Greater_DoubleDouble',A=g.getv('Age'),B=D.CITY_LAND_TIMEOUT));g.side(timed)
        g.do(SL+'PrintString',InString='City sectors were not ready before the landing timeout.',bPrintToScreen=False,bPrintToLog=True)
        g.own('Abort');g.side(timed,False);timer(g,'Land',.2)
    g.side(ready,False)
    fade(g,1,1,.1)
    text(g,title='Queen Street')  # level2: a place card, no loading notice
    timed=g.branch(g.math('Greater_DoubleDouble',A=g.getv('Age'),B=D.CITY_LAND_TIMEOUT));g.side(timed);g.own('Abort')
    g.side(timed,False);timer(g,'Land',.2)
    g.side(valid,False);g.own('Abort')
    g.finish()

def endfade():
    g=G(BP,'EndFade');fade(g,0,1,1);g.finish()

def finish():
    g=G(BP,'Finish');fade(g,1,1,0);g.do(MSP+'Stop',self=g.getv('Sequence'))
    g.do(A+'K2_DestroyActor',self=g.getv('SequenceActor'))
    g.setv('Phase',6)
    music(g,'City')
    g.own('MuteTestFX',Index=0)
    for name,value in [('SandRadius',0),('SandProgress',0),('AmbientIntensity',.8)]:
        g.do(ML+'SetScalarParameterValue',Collection=MPC,ParameterName=name,ParameterValue=value)
    color(g,0,.05)
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',g.getv('Player'))
    external(g,'MaxWalkSpeed',g.getv('OldWalkSpeed'),(r,'CharacterMovement'),'/Script/Engine.CharacterMovementComponent')
    g.do('/Script/Engine.SceneComponent:K2_SetWorldLocation',self=g.getv('Floor'),NewLocation='30000,0,-78',bSweep=False,bTeleport=True)
    g.do('/Script/Engine.SceneComponent:SetWorldScale3D',self=g.getv('Floor'),NewScale='600,600,.3')
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled',self=g.getv('Floor'),NewType='QueryAndPhysics')
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation='9000,-250,32',bSweep=False,bTeleport=True)
    g.do(PC+'SetControlRotation',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewRotation=g.math('MakeRotator',Yaw=0))
    movement(g,True)
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False)
    fade(g,1,0,.8)
    replay=g.branch(g.getv('Replay'));g.side(replay)
    g.do(cls(JOURNEY)+':ResumeRun',self=g.getv('Journey'))
    g.side(replay,False)
    for var,name in [('DriveRoad','BP_L2RoadNetwork'),('DriveMeteor','BP_Meteor'),('DriveCar','BP_L2Car')]:
        g.setv(var,spawn(g,'/Game/FoA/Level2/Drive/'+name))
    g.do(A+'K2_SetActorLocation',self=g.getv('DriveCar'),NewLocation='9300,-100,-63',bSweep=False,bTeleport=True)
    journey=spawn(g,JOURNEY)
    journey=g.cast(journey,cls(JOURNEY),'BP L2Journey');g.setv('Journey',journey)
    g.do(cls(JOURNEY)+':StartJourney',self=g.getv('Journey'))
    g.finish()


def spawn(g,path):
    transform=g.math('MakeTransform',Location='0,0,0',Rotation='0,0,0',Scale='1,1,1')
    actor=g.do(GS+'BeginDeferredActorSpawnFromClass',ActorClass=cls(path),SpawnTransform=transform,CollisionHandlingOverride='AlwaysSpawn')
    return g.do(GS+'FinishSpawningActor',Actor=actor,SpawnTransform=transform)


def mute_fx():
    g=G(BP,'MuteTestFX')
    actors=g.do(GS+'GetAllActorsOfClass',ActorClass=cls(FX));array=(actors[0],'OutActors')
    r=g.ref();g.node(r,'macro',0,0,macro_name='ForEachLoop');g.put(r,'Array',array)
    g.link(g.tail,'then',r,'Exec');g.tail=r;g._side='LoopBody'
    g.do(A+'SetActorTickEnabled',self=(r,'Array Element'),bEnabled=False)
    g.do(A+'DisableInput',self=(r,'Array Element'),PlayerController=g.f(GS+'GetPlayerController',PlayerIndex=0))
    g.finish()


def check_city_sectors():
    from city_streaming import threshold_ready
    threshold_ready()


def restart_road():
    g=G(BP,'RestartFromRoad');g.setv('Replay',True)
    g.own('ResetPath');g.setv('Phase',2)
    music(g,'Dream')
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation=','.join(map(str,D.ENTRY)),bSweep=False,bTeleport=True)
    movement(g,False)
    attempt=g.getv('RoadAttempts',g.getv('Journey'),JOURNEY)
    day=g.math('Add_IntInt',A=attempt,B=1)
    label=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=day)
    label=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A='Day ',B=label)
    label=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A=label,B='.')
    title=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=label)
    text(g,title=title);fade(g,1,1,.1,True);timer(g,'ReplayFall',1.2)
    g.finish()

def replay_fall():
    g=G(BP,'ReplayFall');fade(g,1,0,.3,True);g.own('BeginFall');g.finish()


def begin_ending():
    g=G(BP,'BeginEnding');g.setv('Phase',7)
    music(g,'Dream')
    movement(g,False);fade(g,0,1,.8);timer(g,'EndingColour',1);g.finish()


def ending_colour():
    g=G(BP,'EndingColour');g.setv('Phase',8)
    # The stop camera sits behind the pawn; keep both inside Dream A's front wall.
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation=f'{D.OFFSET[0]},{D.OFFSET[1]+100},92',bSweep=False,bTeleport=True)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    g.do(PC+'SetControlRotation',self=pc,NewRotation=g.math('MakeRotator',Yaw=90))
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=pc,NewViewTarget=g.getv('Player'),BlendTime=0)
    g.do(cls(JOURNEY)+':ApplyMerge',self=g.getv('Journey'),Amount=1)
    g.do(cls(JOURNEY)+':ShowWriter',self=g.getv('Journey'))
    color(g,1,3);fade(g,1,0,2)
    text(g,hint='Application received.')
    timer(g,'EndFade',9);timer(g,'EndGame',10);g.finish()


def endgame():
    g=G(BP,'EndGame');text(g)
    front=g.do(GS+'GetActorOfClass',ActorClass=cls(FRONT))
    front=g.cast(front,cls(FRONT),'BP Fo AFront End')
    g.do(cls(FRONT)+':EndOfLevel',self=front);g.finish()

def abort():
    g=G(BP,'Abort');g.setv('Phase',-1)
    for name in FUNCS:g.do(SL+'K2_ClearTimer',FunctionName=name)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Sequence')));g.side(valid)
    g.do(MSP+'Stop',self=g.getv('Sequence'))
    g.do(A+'K2_DestroyActor',self=g.getv('SequenceActor'));g.own('RestoreRoom')
    g.side(valid,False);g.own('RestoreRoom');g.finish()

def restore(job_ending=False):
    g=G(BP,'RestoreRoom')
    if job_ending:g.own('RestoreWakeLook')
    g.own('ResetPath')
    music(g,'None')
    r=g.ref();g.get(r,'CharacterMovement',0,0,'/Script/Engine.Character');g.put(r,'self',g.getv('Player'))
    external(g,'MaxWalkSpeed',g.getv('OldWalkSpeed'),(r,'CharacterMovement'),'/Script/Engine.CharacterMovementComponent')
    g.do('/Script/Engine.PrimitiveComponent:SetCollisionEnabled',self=g.getv('Floor'),NewType='NoCollision')
    text(g)
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    frame=g.getv('DoorFrame',g.getv('Story'),STORY)
    xf=g.f(A+'GetTransform',self=frame)
    loc=g.math('TransformLocation',T=xf,Location='-140,0,92')
    g.do(A+'K2_SetActorLocation',self=g.getv('Player'),NewLocation=loc,bSweep=False,bTeleport=True)
    movement(g,True)
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False)
    fade(g,1,0,.4)
    color(g,0,.05)
    g.do(cls(STORY)+':SetStoryHUDHidden',self=g.getv('Story'),Hidden=False)
    journey=g.branch(g.f(SL+'IsValid',Object=g.getv('Journey')));g.side(journey)
    g.do(cls(JOURNEY)+':Abort',self=g.getv('Journey'));g.own('CleanupOwned',Index=0)
    g.side(journey,False);g.own('CleanupOwned',Index=0)
    g.finish()


def cleanup_owned():
    g=G(BP,'CleanupOwned')
    item=g.getv('Journey')
    for i,name in reversed(list(enumerate(('DriveCar','DriveMeteor','DriveRoad')))):
        item=g.math('SelectObject',A=g.getv(name),B=item,bSelectA=g.math('EqualEqual_IntInt',A=g.arg('Index'),B=i))
    valid=g.branch(g.math('Less_IntInt',A=g.arg('Index'),B=4));g.side(valid)
    exists=g.branch(g.f(SL+'IsValid',Object=item));g.side(exists)
    actor=g.cast(item,'/Script/Engine.Actor','Actor')
    g.do(A+'K2_DestroyActor',self=actor)
    g.own('CleanupOwned',Index=g.math('Add_IntInt',A=g.arg('Index'),B=1))
    g.side(exists,False);g.own('CleanupOwned',Index=g.math('Add_IntInt',A=g.arg('Index'),B=1))
    g.side(valid,False);g.own('UnloadDream');g.finish()


def unload(name,var,nextfn=None):
    g=G(BP,name)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv(var)));g.side(valid)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeVisible',self=g.getv(var),bInShouldBeVisible=False)
    g.do('/Script/Engine.LevelStreaming:SetShouldBeLoaded',self=g.getv(var),bInShouldBeLoaded=False)
    if nextfn:g.own(nextfn)
    else:g.do(A+'K2_DestroyActor')
    g.side(valid,False)
    if nextfn:g.own(nextfn)
    else:g.do(A+'K2_DestroyActor')
    g.finish()

def events():
    ns,_=inspect(BP,'EventGraph')
    assert not any(n['title']=='Transition lifecycle' for n in ns),'Already authored'
    b=Batch(BP,'EventGraph')
    if ns:b.ops.append(dict(op='remove',node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event',ref='begin',event_name='ReceiveBeginPlay',x=0,y=0))
    b.fn('start',cls(BP)+':Begin',300,0);b.chain('begin','start')
    b.ops.append(dict(op='add_event',ref='tick',event_name='ReceiveTick',x=0,y=600))
    b.fn('step',cls(BP)+':Step',300,600);b.chain('tick','step');b.link('tick','DeltaSeconds','step','Delta')
    b.comment('Transition lifecycle',['begin','start','tick','step']);b.run()

STEPS={'skeleton':skeleton,'widget':widget,'Begin':begin,'Watch':watch,'StartThreshold':start,'OpenDoor':opendoor,'EnterDream':enter,'HideCard':hidecard,'StartPath':path,
       'Step':step,'BeginFall':beginfall,'PlayFall':playfall,'Land':land,'EndFade':endfade,'Finish':finish,'Abort':abort,'RestoreRoom':restore,'events':events,
       'MuteTestFX':mute_fx,'RestartFromRoad':restart_road,'ReplayFall':replay_fall,'BeginEnding':begin_ending,'EndingColour':ending_colour,'EndGame':endgame,
       'CleanupOwned':cleanup_owned,'UnloadDream':lambda:unload('UnloadDream','Stream','UnloadCity'),'UnloadCity':lambda:unload('UnloadCity','CityStream')}
STEPS['CheckCitySectors']=check_city_sectors

import threshold_walk_graphs as walk
STEPS.update(walk.bind(globals()))
path_complete=walk.path_complete
def dream_skeleton():
    """dreamroom lane: the torment's variables, functions and components, added only when missing (no rebuilds)."""
    info=call('blueprint_get_info',path=BP)
    have={v['name'] for v in info['variables']}
    for n,t,v in walk.VARIABLES:
        if n not in have:call('blueprint_add_variable',path=BP,variable_name=n,variable_type=t,default_value=v,category='Dream')
    for n,inputs in walk.FUNCTIONS.items():
        if n not in info['functions']:  # the info list can omit graphs; an existing one is refused, never duplicated
            r=h.call('blueprint_add_function',{'path':BP,'function_name':n,'inputs':[dict(name=a,type=t) for a,t in inputs]})
            assert r.get('ok') or 'already exists' in str(r.get('error')),r
    cs={c['name'] for c in info.get('components',[])}
    for n,t in walk.COMPONENTS+[(f[0],'StaticMeshComponent') for f in D.FEARS]:
        if n not in cs:call('blueprint_add_component',path=BP,component_name=n,component_class_path='/Script/Engine.'+t)
    call('blueprint_compile',path=BP);call('asset_save',asset_paths=[BP])


STEPS['dream_skeleton']=dream_skeleton
STEPS['walk_widget']=lambda:walk.widget()
STEPS['walk_padding']=lambda:walk.padding()
STEPS['walk_components']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/threshold_walk_setup.py',env={},resources=['asset:'+BP])

if __name__=='__main__':
    os.environ.update(FOA_AGENT=D.OWNER,HAYBA_AGENT_ID=D.OWNER)
    assert h.leases_of(D.OWNER),'Acquire Transition lease first'
    assert not call('editor_get_state')['pie_running'],'No edits during PIE'
    STEPS[sys.argv[1]]()
