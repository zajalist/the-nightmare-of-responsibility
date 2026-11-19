"""Native L2 journey graphs. Build one named step per scoped editor lease.

StartJourney stores the original pawn. ResumeRun keeps notes and attempts. Abort
is safe before a return to title; no method calls the L1 day-reset/save workflow.
"""
import os
import sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal','P:/FoA/Tools/Unreal/player']
import journey_data as D
import drive_data
import stop_set_data as S
import build_drive as b
from build_drive import G, call, cls, GS, A, SL
from build_threshold import external
import hayba_call as h
import editor_lock

BP,HUD=D.BP,D.HUD
CAR=b.CAR
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
THRESHOLD='/Game/FoA/Level2/Transition/BP_DreamThreshold'
ENCOUNTER='/Game/FoA/Gameplay/Encounter/BP_Encounter'
GI='/Game/FoA/Gameplay/GI_FoA'
MERGE=D.ROOT+'/BP_L2Merge'
AUDIO='/Game/FoA/Audio/BP_RoomAudio'
DEBUG='/Game/FoA/UI/Game/WBP_Debug'
INSPECT='/Game/FoA/UI/Game/BP_ItemInspect'
STOPSET=S.BP
GRADE='/Game/FoA/PostProcess/BP_DreamDirector'
POST='/Script/Engine.PostProcessComponent'
DREAM_MATERIALS='/Game/FoA/PostProcess/MPC_Dream'
SIGNATURES={name:[] for name in ('StartJourney','ResumeRun','EnterCar','Confirm','ConfirmEdit','RestartRun',
    'StartFinale','FinaleWon','FinaleLost','Submit','Abort','ReleaseEncounter','InitializeMerge','ReleaseMerge','ShowWriter','DebugNextStep','EnableConfirm','DisableConfirm')}
SIGNATURES.update(Arrive=[('StopIndex','int')],RefreshEmployability=[('Progress','int')])
SIGNATURES['ApplyMerge']=[('Amount','float')]
SIGNATURES['SetMusic']=[('Track','name')]
SIGNATURES['SetCVHudOpacity']=[('Opacity','float')]
for _name in ('ActivateCar','StageStop','UseStop','StopActionFinished','AdvanceStopDialogue','PreviewRejection',
              'EndMergePreview','ReturnToCar','FinishReturnToCar','ReleaseStop','ReapplyStageView','RetryDraft','RetryWithoutTiming',
              'ShowCVPaper','OpenCVPaper','CheckCVPaper','ReleaseCVPaper'):
    SIGNATURES[_name]=[]

def skeleton():
    for path,widget in ((HUD,True),(BP,False)):
        if not h.call('blueprint_get_info',{'path':path}).get('ok'):
            if widget:call('ui_create_widget',path=D.ROOT,name='WBP_L2Journey')
            else:call('blueprint_create',package_path=path,name='BP_L2Journey',parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=HUD)
    if 'Refresh' not in info['functions']:
        call('blueprint_add_function',path=HUD,function_name='Refresh',inputs=[dict(name=n,type='text') for n in ('Title','Body','Hint','Progress')])
    call('blueprint_compile',path=HUD);call('asset_save',asset_paths=[HUD])
    info=call('blueprint_get_info',path=BP);have={v['name'] for v in info['variables']}
    variables=[('Phase','int','0'),('Stop','int','0'),('Employability','int','0'),('RoadAttempts','int','0'),
       ('Assisted','bool','false'),('Submitted','bool','false'),('FinaleComplete','bool','false'),
       ('Car','object:'+cls(CAR),''),('Player','object:'+cls(PLAYER),''),('Threshold','object:'+cls(THRESHOLD),''),
       ('Encounter','object:'+cls(ENCOUNTER),''),('HUD','object:'+cls(HUD),''),('Game','object:'+cls(GI),''),
       ('Merge','object:/Script/Engine.Actor',''),('StopSet','object:'+cls(STOPSET),''),
       ('CVPaper','object:'+cls(INSPECT),''),('CVPostProcess','struct:/Script/Engine.PostProcessSettings',''),('CVPriorEcho','float','0'),
       ('StopBusy','bool','false'),('StopActionDone','bool','false'),('StopActionState','int','0'),('StopView','int','0')]
    variables += [('EncounterHome','transform',''),('StreetTransform','transform','')]
    variables += [('Edited'+str(i),'bool','false') for i in range(3)]
    for name,typ,value in variables:
        if name not in have:call('blueprint_add_variable',path=BP,variable_name=name,variable_type=typ,default_value=value,category='Journey')
    for name,inputs in SIGNATURES.items():
        if name not in info['functions']:
            call('blueprint_add_function',path=BP,function_name=name,inputs=[dict(name=n,type=t) for n,t in inputs])
    if 'StopCamera' not in {c['name'] for c in info.get('components',[])}:
        call('blueprint_add_component',path=BP,component_name='StopCamera',component_class_path='/Script/Engine.CameraComponent')
    call('blueprint_compile',path=BP);call('asset_save',asset_paths=[BP])

def widget():
    if 'Txt_Title' not in str(call('ui_query',path=HUD)):
        children=[{'class':'Border','name':'Page','slot_props':{'position':[24,64],'size':[680,630]},
            'properties':{'BrushColor':[.015,.015,.015,.94]}}]
        for name,size,y,height in [('Progress',22,88,36),('Title',42,140,64),('Body',27,228,340),('Hint',23,612,54)]:
            children.append({'class':'TextBlock','name':'Txt_'+name,'slot_props':{'position':[56,y],'size':[616,height]},
              'properties':{'Text':'','AutoWrapText':True,'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI',
                'TypefaceFontName':'SemiBold','Size':size},'ColorAndOpacity':{'SpecifiedColor':[.96,.96,.96,1]}}})
        call('ui_build_tree',widget_blueprint_path=HUD,parent_widget_name='RootCanvas',tree=children)
        for name in ('Title','Body','Hint','Progress'):call('ui_set_variable',widget_blueprint_path=HUD,widget_name='Txt_'+name,is_variable=True)
        call('ui_compile_widget',widget_blueprint_path=HUD)
    g=G(HUD,'Refresh')
    for name in ('Title','Body','Hint','Progress'):
        value=g.arg(name)
        if name=='Body':
            value=g.f('/Script/Engine.KismetTextLibrary:Conv_TextToString',InText=value)
            value=g.f('/Script/Engine.KismetStringLibrary:Replace',SourceString=value,From='\n\n',To='\n')
            value=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=value)
        g.do('/Script/UMG.TextBlock:SetText',self=g.getv('Txt_'+name),InText=value)
    g.finish()

def widget_layout():
    anchor=dict(anchors_min=[0,1],anchors_max=[0,1],alignment=[0,1],auto_size=False)
    call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Page',
         slot_props=dict(anchor,position=[24,-24],size=[620,430]))
    for name,y,height,size in [('Progress',-410,28,20),('Title',-350,50,32),('Body',-104,230,24),('Hint',-42,50,21)]:
        call('ui_set_widget_properties',widget_blueprint_path=HUD,widget_name='Txt_'+name,
             slot_props=dict(anchor,position=[48,y],size=[572,height]),
             properties={'Font':{'FontObject':'/Game/FoA/UI/Fonts/F_FoA_UI.F_FoA_UI','TypefaceFontName':'SemiBold','Size':size}})
    call('ui_compile_widget',widget_blueprint_path=HUD);call('ui_save_widget',widget_blueprint_path=HUD)

def debug_help():
    call('ui_set_widget_properties',widget_blueprint_path=DEBUG,widget_name='Txt_Controls',properties={
        'Text':'F6  Next step in Levels 1 and 2\nSkipping uses separate debug progress.\nHold Space  Skip intro\nP  Phone     Hold Ctrl  Crouch     E  Interact'})
    call('ui_compile_widget',widget_blueprint_path=DEBUG)
    call('ui_save_widget',widget_blueprint_path=DEBUG)

def me(g):
    r=g.ref();g.node(r,'self',0,0);return r,'self'

def find(g,var,path,pin):
    actor=g.do(GS+'GetActorOfClass',ActorClass=cls(path))
    value=g.cast(actor,cls(path),pin);g.setv(var,value)

def phase(g,value):
    gate=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=value));g.side(gate);return gate

def text(g,title,body,hint='Enter or gamepad Y to continue'):
    score=g.f('/Script/Engine.KismetStringLibrary:Conv_IntToString',InInt=g.getv('Employability'))
    label=g.f('/Script/Engine.KismetStringLibrary:Concat_StrStr',A='Employability ',B=score)
    label=g.f('/Script/Engine.KismetTextLibrary:Conv_StringToText',InString=label)
    g.do(cls(HUD)+':Refresh',self=g.getv('HUD'),Title=title,Body=body,Hint=hint,Progress=label)
    absent=g.branch(g.math('Not_PreBool',A=g.f('/Script/UMG.UserWidget:IsInViewport',self=g.getv('HUD'))));g.side(absent)
    g.do('/Script/UMG.UserWidget:AddToViewport',self=g.getv('HUD'),ZOrder=25)

def cinematic(g,enabled):
    g.do(cls(PLAYER)+':SetCinematic',self=g.getv('Player'),bEnable=enabled)
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    if enabled:
        g.do('/Script/Engine.Controller:SetIgnoreMoveInput',self=pc,bNewMoveInput=True)
        g.do('/Script/Engine.Controller:SetIgnoreLookInput',self=pc,bNewLookInput=True)
    else:
        g.do('/Script/Engine.Controller:ResetIgnoreMoveInput',self=pc)
        g.do('/Script/Engine.Controller:ResetIgnoreLookInput',self=pc)


def stage_colour(g,amount):
    actor=g.do(GS+'GetActorOfClass',ActorClass=cls(GRADE))
    grade=g.cast(actor,cls(GRADE),'BP Dream Director')
    g.do(cls(GRADE)+':SetColorReveal',self=grade,Amount=amount,BlendSeconds=.35)

def merge_call(g,function,**pins):
    target=g.cast(g.getv('Merge'),cls(MERGE),'BP L2Merge')
    g.do(cls(MERGE)+':'+function,self=target,**pins)

def stop_call(g,function,**pins):
    return g.do(cls(STOPSET)+':'+function,self=g.getv('StopSet'),**pins)

def stop_timer(g,name,seconds):
    g.do(SL+'K2_SetTimer',FunctionName=name,Time=seconds,bLooping=False)

def stop_fade(g,start,end,seconds):
    g.do('/Script/Engine.PlayerCameraManager:StartCameraFade',self=g.f(GS+'GetPlayerCameraManager',PlayerIndex=0),
         FromAlpha=start,ToAlpha=end,Duration=seconds,Color='(R=0,G=0,B=0,A=1)',bShouldFadeAudio=False,bHoldWhenFinished=end==1)

def stop_ready(g):
    ready=g.branch(g.math('Not_PreBool',A=g.getv('StopBusy')));g.side(ready)

def baseline(g):
    g.own('ApplyMerge',Amount=g.math('Multiply_DoubleDouble',A=g.math('Conv_IntToDouble',InInt=g.getv('Employability')),B=.01))

def mapping(g,enabled):
    pc=g.f(GS+'GetPlayerController',PlayerIndex=0)
    sub=g.f('/Script/Engine.SubsystemBlueprintLibrary:GetLocalPlayerSubSystemFromPlayerController',
          PlayerController=pc,Class='/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem')
    sub=g.cast(sub,'/Script/EnhancedInput.EnhancedInputLocalPlayerSubsystem','Enhanced Input Local Player Subsystem')
    args=dict(self=sub,MappingContext=drive_data.ROOT+'/Input/IMC_L2Drive.IMC_L2Drive')
    if enabled:args['Priority']=2
    g.do('/Script/EnhancedInput.EnhancedInputSubsystemInterface:'+('AddMappingContext' if enabled else 'RemoveMappingContext'),**args)
    g.do(A+('EnableInput' if enabled else 'DisableInput'),PlayerController=pc)

def enable_confirm():
    g=G(BP,'EnableConfirm');mapping(g,True);g.finish()

def disable_confirm():
    g=G(BP,'DisableConfirm');mapping(g,False);g.finish()

def start():
    g=G(BP,'StartJourney');phase(g,0)
    pawn=g.f(GS+'GetPlayerPawn',PlayerIndex=0);pawn=g.cast(pawn,cls(PLAYER),'BP Fo APlayer');g.setv('Player',pawn)
    find(g,'Car',CAR,'BP L2Car');find(g,'Threshold',THRESHOLD,'BP Dream Threshold')
    find(g,'Encounter',ENCOUNTER,'BP Encounter')
    g.setv('EncounterHome',g.f(A+'GetTransform',self=g.getv('Encounter')))
    game=g.f(GS+'GetGameInstance');game=g.cast(game,cls(GI),'GI Fo A');g.setv('Game',game)
    external(g,'Journey',me(g),g.getv('Car'),cls(CAR))
    r=g.ref();g.node(r,'create_widget',0,0);g.put(r,'Class',cls(HUD));g.put(r,'OwningPlayer',g.f(GS+'GetPlayerController',PlayerIndex=0))
    g.chain(g.tail,r);g.tail=r;g.setv('HUD',(r,'ReturnValue'))
    g.own('InitializeMerge');g.own('ResumeRun');g.finish()

def resume():
    g=G(BP,'ResumeRun')
    g.own('ReleaseCVPaper')
    g.setv('Phase',1);g.own('EnableConfirm');cinematic(g,False)
    merge_call(g,'SetVisible',Visible=True)
    g.own('ApplyMerge',Amount=0)
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False)
    g.own('FormStreetSand')  # level2 2026-11-18: the sand crow on Queen Street (build_l2_stop_sand.py)
    text(g,'Queen Street','Dad left the car. Queen Market is hiring. Check what’s on your C.V. before you drive over.','Enter or Y to read the C.V.')
    g.finish()

def enter_car():
    g=G(BP,'EnterCar')
    stop_ready(g);g.own('CrumbleStreetSand')
    staged=g.branch(g.f(SL+'IsValid',Object=g.getv('StopSet')));g.side(staged);g.own('ReturnToCar')
    g.side(staged,False);g.own('ActivateCar');g.finish()

def activate_car():
    g=G(BP,'ActivateCar')
    g.own('ReleaseCVPaper')
    g.setv('Phase',3);g.own('DisableConfirm')
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    cinematic(g,False)
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=True)
    merge_call(g,'SetVisible',Visible=False)
    external(g,'Employability',g.getv('Employability'),g.getv('Car'),cls(CAR))
    g.do(cls(CAR)+':Activate',self=g.getv('Car'),Index=g.getv('Stop'))
    # Keep the raw C.V. shortcut on the controller while the car owns drive input.
    g.do(A+'EnableInput',PlayerController=g.f(GS+'GetPlayerController',PlayerIndex=0))
    stage_colour(g,0.);g.finish()

def arrive(all_jobs=False):
    g=G(BP,'Arrive');phase(g,3)
    if all_jobs:
        from job_route import BOSS,BOSS_MINIMUM
        index=g.arg('StopIndex')
        inside=g.math('InRange_IntInt',Value=index,Min=0,Max=BOSS,InclusiveMin=True,InclusiveMax=True)
        ordinary=g.math('Less_IntInt',A=index,B=BOSS)
        qualified=g.math('GreaterEqual_IntInt',A=g.getv('Employability'),B=BOSS_MINIMUM)
        allowed=g.math('BooleanAND',A=inside,B=g.math('BooleanOR',A=ordinary,B=qualified))
        valid=g.branch(allowed);g.side(valid);g.setv('Stop',index)
    else:
        valid=g.branch(g.math('EqualEqual_IntInt',A=g.arg('StopIndex'),B=g.getv('Stop')));g.side(valid)
    g.setv('Phase',4);g.setv('StopBusy',True);g.setv('StopActionDone',False);g.setv('StopActionState',0)
    at=g.f(A+'K2_GetActorLocation',self=g.getv('Car'))
    at=g.math('Add_VectorVector',A=at,B='0,-300,'+str(92-getattr(drive_data,'VEHICLE_ROOT_LIFT',65)))
    # level2 2026-11-18: he stands facing the way the car arrived; BP_FoAPlayer clamps first-person yaw to +-60 deg
    # of the body, so the body has to turn with the view (BeginJob sets the control yaw to the car's too)
    heading=g.math('BreakRotator',InRot=g.f(A+'K2_GetActorRotation',self=g.getv('Car')))
    facing=g.math('MakeRotator',Roll=0,Pitch=0,Yaw=(heading[0],'Yaw'))
    g.setv('StreetTransform',g.math('MakeTransform',Location=at,Rotation=facing,Scale='1,1,1'))
    stop_fade(g,0,1,S.FADE_SECONDS);stop_timer(g,'StageStop',S.FADE_SECONDS+.05);g.finish()

def stage_stop(all_jobs=False):
    g=G(BP,'StageStop');phase(g,4)
    busy=g.branch(g.getv('StopBusy'));g.side(busy)
    condition=(g.math('Less_IntInt',A=g.getv('Stop'),B=3) if all_jobs else
               g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=0))
    job=g.branch(condition);g.side(job);g.own('BeginJob');g.side(job,False)
    g.do(cls(CAR)+':Deactivate',self=g.getv('Car'));g.own('ReleaseStop')
    transform=g.math('MakeTransform',Location=','.join(map(str,S.ORIGIN)),Scale='1,1,1')
    spawned=g.do(GS+'BeginDeferredActorSpawnFromClass',ActorClass=cls(STOPSET),SpawnTransform=transform,CollisionHandlingOverride='AlwaysSpawn')
    spawned=g.do(GS+'FinishSpawningActor',Actor=spawned,SpawnTransform=transform)
    actor=g.cast(spawned,cls(STOPSET),'BP L2Stop Set');g.setv('StopSet',actor)
    stop_call(g,'Configure',Index=2 if all_jobs else g.getv('Stop'),Player=g.getv('Player'),Journey=me(g))
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False)
    cinematic(g,True);g.setv('StopBusy',False);g.setv('StopActionState',1);g.setv('StopView',0);g.own('EnableConfirm')
    merge_call(g,'SetVisible',Visible=True)
    baseline(g)
    if all_jobs:g.setv('Phase',11);g.own('StartFinale')
    else:stop_fade(g,1,0,.35);g.own('BeginStopContact');stage_colour(g,.82)
    g.finish()

def use_stop():
    g=G(BP,'UseStop')
    conversation=g.branch(g.math('Greater_IntInt',A=g.getv('DialogueMode'),B=0));g.side(conversation)
    g.own('DialogueConfirm');g.side(conversation,False)
    phase(g,4);stop_ready(g)
    ready=g.branch(g.math('BooleanAND',A=g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=1),B=g.math('Not_PreBool',A=g.getv('StopActionDone'))));g.side(ready)
    g.setv('StopBusy',True);g.setv('StopActionState',2)
    g.setv('StopView',g.math('SelectInt',A=3,B=1,bPickA=g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=2)))
    stop_call(g,'UseAction')
    for i,row in enumerate(D.SCENES):
        br=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(br)
        text(g,D.STOPS[i]['place'],row['acting'],'');g.side(br,False)
    g.finish()

def stop_action_finished():
    g=G(BP,'StopActionFinished');phase(g,4)
    ready=g.branch(g.math('BooleanAND',A=g.getv('StopBusy'),B=g.getv('ActionDone',g.getv('StopSet'),STOPSET)));g.side(ready)
    g.setv('StopBusy',False);g.setv('StopActionDone',True);g.setv('StopActionState',3)
    g.setv('StopView',g.math('SelectInt',A=3,B=0,bPickA=g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=2)))
    g.own('ReapplyStageView')
    g.own('FinishStopContact')
    g.finish()

def advance_stop_dialogue():
    g=G(BP,'AdvanceStopDialogue');phase(g,4);stop_ready(g)
    ready=g.branch(g.getv('StopActionDone'));g.side(ready)
    review=g.branch(g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=10));g.side(review)
    g.setv('Phase',5);baseline(g)
    for i,row in enumerate(D.STOPS):
        br=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(br)
        text(g,'Revise C.V.',row['truth']+'\n\nBecomes\n'+row['revision'],'Enter or gamepad Y to confirm this revision');g.side(br,False)
    g.side(review,False)
    for i,row in enumerate(D.SCENES):
        stop=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(stop)
        for j in range(len(row['dialogue'])):
            line=g.branch(g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=3+j));g.side(line)
            if j+1<len(row['dialogue']):
                g.setv('StopActionState',4+j);text(g,D.STOPS[i]['place'],row['dialogue'][j+1])
            else:g.own('PreviewRejection')
            g.side(line,False)
        g.side(stop,False)
    g.finish()

def preview_rejection():
    g=G(BP,'PreviewRejection');phase(g,4)
    g.setv('StopActionState',10);g.setv('StopBusy',True);g.setv('StopView',2);g.own('ReapplyStageView')
    amount=g.math('Multiply_DoubleDouble',A=g.math('Conv_IntToDouble',InInt=g.math('Add_IntInt',A=g.getv('Stop'),B=1)),B=.2)
    g.own('ApplyMerge',Amount=amount)
    stop_timer(g,'EndMergePreview',S.PREVIEW_SECONDS)
    for i,row in enumerate(D.SCENES):
        br=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(br)
        text(g,D.STOPS[i]['place'],row['rejection'],'');g.side(br,False)
    g.finish()

def end_merge_preview():
    g=G(BP,'EndMergePreview');phase(g,4)
    done=g.branch(g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=10));g.side(done)
    baseline(g);g.setv('StopBusy',False)
    for i,row in enumerate(D.SCENES):
        br=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(br)
        text(g,D.STOPS[i]['place'],row['rejection'],'Enter or gamepad Y to review the C.V.');g.side(br,False)
    g.finish()

def return_to_car():
    g=G(BP,'ReturnToCar');g.setv('Phase',3);g.setv('StopBusy',True);g.own('DisableConfirm')
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    stop_fade(g,0,1,S.FADE_SECONDS);stop_timer(g,'FinishReturnToCar',S.FADE_SECONDS+.05);g.finish()

def finish_return_to_car():
    g=G(BP,'FinishReturnToCar');phase(g,3)
    busy=g.branch(g.getv('StopBusy'));g.side(busy)
    g.own('ReleaseStop')
    g.do(A+'K2_SetActorTransform',self=g.getv('Player'),NewTransform=g.getv('StreetTransform'),bSweep=False,bTeleport=True)
    g.own('ActivateCar');stop_fade(g,1,0,.35);g.finish()

def release_stop():
    g=G(BP,'ReleaseStop')
    for name in ('StageStop','FinishReturnToCar','EndMergePreview'):g.do(SL+'K2_ClearTimer',FunctionName=name)
    g.setv('StopBusy',False);g.setv('StopActionState',0);g.setv('StopActionDone',False)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('StopSet')));g.side(valid)
    stop_call(g,'Restore');g.do(A+'K2_DestroyActor',self=g.getv('StopSet'));g.finish()

def reapply_stage_view():
    g=G(BP,'ReapplyStageView')
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('StopSet')));g.side(valid)
    stop_call(g,'ShowView',View=g.getv('StopView'))
    g.side(valid,False)
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewViewTarget=g.getv('Player'),BlendTime=.2)
    g.finish()

def confirm():
    g=G(BP,'Confirm')
    stop_ready(g)
    conversation=g.branch(g.math('Greater_IntInt',A=g.getv('DialogueMode'),B=0));g.side(conversation)
    g.own('DialogueConfirm');g.side(conversation,False)
    br=phase(g,1);g.own('ShowCVPaper')
    g.side(br,False);br=phase(g,2);g.own('ReleaseCVPaper');g.own('EnterCar')
    g.side(br,False);br=phase(g,4);g.own('AdvanceStopDialogue')
    g.side(br,False);br=phase(g,5);g.own('ConfirmEdit')
    g.side(br,False);br=phase(g,7);g.own('RetryDraft')
    g.side(br,False);br=phase(g,8);g.own('Submit')
    g.side(br,False);br=phase(g,11)
    done=g.branch(g.getv('Edited2'));g.side(done);g.own('StartFinale')
    g.side(done,False);g.own('EnterCar')
    g.finish()

def show_cv_paper():
    g=G(BP,'ShowCVPaper');stop_ready(g)
    active=g.math('InRange_IntInt',Value=g.getv('Phase'),Min=1,Max=11)
    allowed=g.branch(g.math('BooleanAND',A=active,B=g.math('Not_PreBool',A=g.getv('PhoneSession'))));g.side(allowed)
    intro=phase(g,1)
    g.setv('Phase',2)
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    # Both branches reach the same inspector, while an in-progress interaction keeps its phase.
    found=g.do(GS+'GetActorOfClass',ActorClass=cls(INSPECT))
    g.link(intro,'else',found[0],'execute')
    exists=g.branch(g.f(SL+'IsValid',Object=found));g.side(exists)
    typed=g.cast(found,cls(INSPECT),'BP Item Inspect')
    closed=g.branch(g.math('Not_PreBool',A=g.getv('bOpen',typed,INSPECT)));g.side(closed)
    g.setv('CVPaper',typed);g.own('OpenCVPaper')
    g.side(exists,False)
    transform=g.math('MakeTransform',Scale='1,1,1')
    actor=g.do(GS+'BeginDeferredActorSpawnFromClass',ActorClass=cls(INSPECT),SpawnTransform=transform,CollisionHandlingOverride='AlwaysSpawn')
    actor=g.do(GS+'FinishSpawningActor',Actor=actor,SpawnTransform=transform)
    typed=g.cast(actor,cls(INSPECT),'BP Item Inspect');g.setv('CVPaper',typed);g.own('OpenCVPaper')
    g.finish()


def open_cv_paper(all_jobs=False):
    g=G(BP,'OpenCVPaper');paper=g.getv('CVPaper')
    # Reuse the paused 3D turntable, bypassing first-pickup suppression on retries.
    g.do(cls(INSPECT)+':Open',self=paper,Item='L2CVPaper')
    widget=g.getv('Widget',paper,INSPECT)
    opened=g.branch(g.math('BooleanAND',A=g.getv('bOpen',paper,INSPECT),B=g.f(SL+'IsValid',Object=widget)));g.side(opened)
    g.own('SetCVHudOpacity',Opacity=0)
    from job_cv import apply_print
    apply_print(g,paper,range(1,8) if all_jobs else (1,))
    post=g.getv('PP',paper,INSPECT)
    settings=g.ref();g.get(settings,'Settings',0,0,POST);g.put(settings,'self',post)
    g.setv('CVPostProcess',(settings,'Settings'))
    echo=g.do(b.ML+'GetScalarParameterValue',Collection=DREAM_MATERIALS,ParameterName='EchoStrength')
    g.setv('CVPriorEcho',echo)
    g.do(b.ML+'SetScalarParameterValue',Collection=DREAM_MATERIALS,ParameterName='EchoStrength',ParameterValue=0)
    # At 35 cm, the shared turntable's wide aperture bleeds background into the tiny print.
    external(g,'Settings','(bOverride_AutoExposureBias=True,AutoExposureBias=-0.7,bOverride_VignetteIntensity=True,VignetteIntensity=0.6,'
             'bOverride_DepthOfFieldFocalDistance=True,DepthOfFieldFocalDistance=35.0,bOverride_DepthOfFieldFstop=True,DepthOfFieldFstop=16.0,'
             'bOverride_MotionBlurAmount=True,MotionBlurAmount=0,bOverride_FilmGrainIntensity=True,FilmGrainIntensity=0)',post,POST)
    external(g,'Yaw',-3,paper,cls(INSPECT));external(g,'Pitch',0,paper,cls(INSPECT))
    scale=g.math('Multiply_DoubleDouble',A=g.getv('Scale',paper,INSPECT),B=2.25)
    external(g,'Scale',scale,paper,cls(INSPECT))
    # The resume is printed on the mesh; the existing widget supplies only controls.
    for name in ('Txt_ItemName','Txt_ItemLine'):
        g.do('/Script/UMG.Widget:SetVisibility',self=g.getv(name,widget,'/Game/FoA/UI/Game/WBP_ItemInspect'),InVisibility='Collapsed')
    hint=g.getv('Txt_Hint',widget,'/Game/FoA/UI/Game/WBP_ItemInspect')
    g.do('/Script/UMG.Widget:SetRenderTranslation',self=hint,Translation='(X=0,Y=64)')
    g.do('/Script/UMG.TextBlock:SetColorAndOpacity',self=hint,InColorAndOpacity='(SpecifiedColor=(R=1,G=1,B=1,A=1))')
    g.do('/Script/UMG.TextBlock:SetShadowOffset',self=hint,InShadowOffset='(X=1,Y=1)')
    g.do('/Script/UMG.TextBlock:SetShadowColorAndOpacity',self=hint,InShadowColorAndOpacity='(R=0,G=0,B=0,A=1)')
    g.do(cls(INSPECT)+':TickStep',self=paper)
    # This game-time timer resumes only after the turntable unpauses on close.
    g.do(SL+'K2_SetTimer',FunctionName='CheckCVPaper',Time=.1,bLooping=True)
    g.side(opened,False);g.setv('CVPaper','');phase(g,2);g.setv('Phase',1)
    text(g,'Queen Street','The C.V. could not be opened.','Enter or gamepad Y to try again')
    g.finish()


def check_cv_paper():
    g=G(BP,'CheckCVPaper')
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CVPaper')));g.side(valid)
    closed=g.branch(g.math('Not_PreBool',A=g.getv('bOpen',g.getv('CVPaper'),INSPECT)));g.side(closed)
    g.do(SL+'K2_ClearTimer',FunctionName='CheckCVPaper');restore_cv_post(g);g.setv('CVPaper','')
    g.own('SetCVHudOpacity',Opacity=1)
    phase(g,2)
    text(g,'Queen Street','Look for the HIRING sign at Queen Market.','Enter or gamepad Y to get in the car')
    g.finish()


def release_cv_paper():
    g=G(BP,'ReleaseCVPaper');g.do(SL+'K2_ClearTimer',FunctionName='CheckCVPaper')
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('CVPaper')));g.side(valid)
    g.do(cls(INSPECT)+':Finish',self=g.getv('CVPaper'));restore_cv_post(g);g.setv('CVPaper','')
    g.own('SetCVHudOpacity',Opacity=1)
    g.finish()


def restore_cv_post(g):
    external(g,'Settings',g.getv('CVPostProcess'),g.getv('PP',g.getv('CVPaper'),INSPECT),POST)
    g.do(b.ML+'SetScalarParameterValue',Collection=DREAM_MATERIALS,ParameterName='EchoStrength',ParameterValue=g.getv('CVPriorEcho'))


def cv_hud_opacity():
    g=G(BP,'SetCVHudOpacity')
    car=g.getv('Car');previous=None
    for widget in (g.getv('HUD'),g.getv('InterviewHUD'),g.getv('HUD',car,CAR)):
        gate=g.branch(g.f(SL+'IsValid',Object=widget))
        if previous:g.link(previous,'else',gate,'execute')
        g.side(gate)
        g.do('/Script/UMG.Widget:SetRenderOpacity',self=widget,InOpacity=g.arg('Opacity'))
        previous=gate
    drive=phase(g,3);g.link(previous,'else',drive,'execute')
    opening=g.branch(g.math('Less_DoubleDouble',A=g.arg('Opacity'),B=.5));g.side(opening)
    for name in ('Throttle','BrakeHeld'):external(g,name,False,car,cls(CAR))
    g.finish()


def confirm_edit():
    g=G(BP,'ConfirmEdit');phase(g,5)
    ready=g.branch(g.math('BooleanAND',A=g.getv('StopActionDone'),B=g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=10)));g.side(ready)
    for i,row in enumerate(D.STOPS):
        stop=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Stop'),B=i));g.side(stop)
        fresh=g.branch(g.math('Not_PreBool',A=g.getv('Edited'+str(i))));g.side(fresh)
        g.setv('Edited'+str(i),True);g.setv('Employability',(i+1)*20)
        g.own('ApplyMerge',Amount=(i+1)*.2)
        g.do(cls(GI)+':Learn',self=g.getv('Game'),Flag=row['flag'])
        if i<2:g.setv('Stop',i+1)
        g.setv('Phase',11)
        text(g,'Revision saved.',row['revision'],'Enter or gamepad Y to '+('go to the interview' if i==2 else 'drive to the next address'))
        g.side(stop,False)
    g.finish()

def restart(job_hunt=False):
    g=G(BP,'RestartRun');phase(g,3)
    g.own('ReleaseCVPaper')
    if job_hunt:
        g.do(cls(CAR)+':Deactivate',self=g.getv('Car'))
        g.setv('RoadAttempts',g.math('Add_IntInt',A=g.getv('RoadAttempts'),B=1))
        g.own('ActivateCar');stop_fade(g,1,0,.8);g.finish();return
    g.setv('Phase',10)
    g.do(cls(CAR)+':Deactivate',self=g.getv('Car'));g.own('DisableConfirm');g.own('ReleaseStop')
    for name,value in [('Stop',0),('Employability',0),('Submitted',False),('FinaleComplete',False),('Assisted',False)]+[('Edited'+str(i),False) for i in range(3)]:g.setv(name,value)
    g.own('ApplyMerge',Amount=0)
    g.setv('RoadAttempts',g.math('Add_IntInt',A=g.getv('RoadAttempts'),B=1))
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False)
    g.do(cls(THRESHOLD)+':RestartFromRoad',self=g.getv('Threshold'));g.finish()

def finale():
    from build_interview import start_interview
    start_interview()

def finale_won():
    g=G(BP,'FinaleWon');phase(g,6);g.own('InterviewWon');g.finish()

def finale_lost():
    g=G(BP,'FinaleLost');phase(g,6);g.own('InterviewLost');g.finish()

def retry_draft():
    g=G(BP,'RetryDraft');phase(g,7);g.setv('Assisted',False);g.own('StartFinale');g.finish()

def retry_without_timing():
    g=G(BP,'RetryWithoutTiming');active=phase(g,6);g.own('ToggleDialogueNotes')
    g.side(active,False);phase(g,7)
    conversation=g.branch(g.math('EqualEqual_IntInt',A=g.getv('DialogueMode'),B=3));g.side(conversation)
    g.own('DialogueSelect',Index=1);g.own('DialogueConfirm')
    g.side(conversation,False);g.setv('Assisted',True);g.own('StartFinale');g.finish()

def refresh_employability():
    g=G(BP,'RefreshEmployability');phase(g,6)
    progress=g.math('Clamp',Value=g.arg('Progress'),Min=0,Max=12)
    value=g.math('Divide_IntInt',A=g.math('Multiply_IntInt',A=progress,B=40),B=12)
    g.setv('Employability',g.math('Add_IntInt',A=60,B=value))
    g.own('ApplyMerge',Amount=g.math('Multiply_DoubleDouble',A=g.math('Conv_IntToDouble',InInt=g.getv('Employability')),B=.01));g.finish()

def apply_merge():
    g=G(BP,'ApplyMerge')
    amount=g.math('FClamp',Value=g.arg('Amount'),Min=.06,Max=1)
    g.do(cls(PLAYER)+':SetSandOverlay',self=g.getv('Player'),Amount=amount)
    valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Merge')));g.side(valid)
    merge_call(g,'SetAmount',Amount=g.arg('Amount'))
    g.finish()

def initialize_merge():
    g=G(BP,'InitializeMerge');missing=g.branch(g.math('Not_PreBool',A=g.f(SL+'IsValid',Object=g.getv('Merge'))));g.side(missing)
    transform=g.f(A+'GetTransform',self=g.getv('Player'))
    spawned=g.do(GS+'BeginDeferredActorSpawnFromClass',ActorClass=cls(MERGE),SpawnTransform=transform,CollisionHandlingOverride='AlwaysSpawn')
    g.setv('Merge',spawned)
    g.do(GS+'FinishSpawningActor',Actor=g.getv('Merge'),SpawnTransform=transform)
    merge_call(g,'Initialize',Player=g.getv('Player'));g.finish()

def release_merge():
    g=G(BP,'ReleaseMerge');valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Merge')));g.side(valid)
    merge_call(g,'Restore')
    g.do(A+'K2_DestroyActor',self=g.getv('Merge'));g.finish()

def set_music():
    g=G(BP,'SetMusic');actor=g.do(GS+'GetActorOfClass',ActorClass=cls(AUDIO))
    valid=g.branch(g.f(SL+'IsValid',Object=actor));g.side(valid)
    audio=g.cast(actor,cls(AUDIO),'BP Room Audio')
    external(g,'MusicOverride',g.arg('Track'),audio,cls(AUDIO))
    g.do(cls(AUDIO)+':UpdateMusic',self=audio);g.finish()

def show_writer():
    g=G(BP,'ShowWriter')
    staged=g.branch(g.f(SL+'IsValid',Object=g.getv('StopSet')));g.side(staged)
    g.setv('StopView',2);stop_call(g,'ShowView',View=2)
    g.side(staged,False)
    camera=g.math('Add_VectorVector',A=g.f(A+'K2_GetActorLocation',self=g.getv('Player')),B='250,-220,120')
    g.do(A+'K2_SetActorLocationAndRotation',NewLocation=camera,NewRotation='-12,128,0',bSweep=False,bTeleport=True)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView',self=g.getv('StopCamera'),InFieldOfView=65)
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewViewTarget=me(g),BlendTime=.35)
    g.finish()

def debug_next_step():
    g=G(BP,'DebugNextStep')
    stop_ready(g)
    allowed=g.math('BooleanAND',A=g.math('Greater_IntInt',A=g.getv('Phase'),B=0),
        B=g.math('BooleanAND',A=g.math('NotEqual_IntInt',A=g.getv('Phase'),B=9),B=g.math('NotEqual_IntInt',A=g.getv('Phase'),B=10)))
    ready=g.branch(allowed);g.side(ready)
    game=g.getv('Game')
    g.do(cls(GI)+':SetProofProgressContext',self=game,Slot='FoA_QA_DebugSkip',
         Known=g.getv('Knowledge',game,GI),Lines=g.getv('Notebook',game,GI))
    g.own('DialogueRelease')
    paper=phase(g,1);g.setv('Phase',2)
    text(g,'Queen Street','The Career Center is ahead.','Enter or gamepad Y to get in the car')
    g.side(paper,False)
    driving=phase(g,3)
    g.own('Arrive',StopIndex=g.getv('Stop'))
    g.side(driving,False)
    battle=phase(g,6);g.own('InterviewWon')
    g.side(battle,False)
    action=g.branch(g.math('BooleanAND',A=g.math('EqualEqual_IntInt',A=g.getv('Phase'),B=4),B=g.math('EqualEqual_IntInt',A=g.getv('StopActionState'),B=1)))
    g.side(action);g.own('UseStop');g.side(action,False);g.own('Confirm');g.finish()

def submit():
    g=G(BP,'Submit');phase(g,8)
    ready=g.branch(g.math('BooleanAND',A=g.getv('FinaleComplete'),B=g.math('Not_PreBool',A=g.getv('Submitted'))));g.side(ready)
    g.setv('Submitted',True);g.setv('Phase',9);g.own('DisableConfirm')
    g.own('ReleaseDialogue')
    g.do(cls(GI)+':Learn',self=g.getv('Game'),Flag='Knows.L2CVSent')
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    g.own('ReleaseStop')
    g.do(cls(THRESHOLD)+':BeginEnding',self=g.getv('Threshold'));g.finish()

def abort():
    g=G(BP,'Abort');g.own('ReleaseCVPaper');gate=g.branch(g.math('Greater_IntInt',A=g.getv('Phase'),B=0));g.side(gate)
    g.setv('Phase',0);g.own('ReleaseDialogue');g.own('DisableConfirm')
    g.do(cls(CAR)+':Deactivate',self=g.getv('Car'));g.own('ReleaseEncounter');g.own('ReleaseStop')
    g.do('/Script/UMG.Widget:RemoveFromParent',self=g.getv('HUD'))
    g.do(A+'SetActorHiddenInGame',self=g.getv('Player'),bNewHidden=False);cinematic(g,False)
    g.own('ApplyMerge',Amount=0)
    g.own('ReleaseMerge')
    g.finish()

def release_encounter():
    g=G(BP,'ReleaseEncounter');valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Encounter')));g.side(valid)
    g.do(cls(ENCOUNTER)+':AbortLevel2CV',self=g.getv('Encounter'))
    g.do(A+'K2_SetActorTransform',self=g.getv('Encounter'),NewTransform=g.getv('EncounterHome'),bSweep=False,bTeleport=True)
    g.finish()

GRAPHS={'StartJourney':start,'ResumeRun':resume,'EnterCar':enter_car,'Arrive':arrive,'Confirm':confirm,
  'ConfirmEdit':confirm_edit,'RestartRun':restart,'StartFinale':finale,'FinaleWon':finale_won,
  'FinaleLost':finale_lost,'RefreshEmployability':refresh_employability,'Submit':submit,'Abort':abort,
  'InitializeMerge':initialize_merge,'ReleaseMerge':release_merge,'ApplyMerge':apply_merge,
  'SetMusic':set_music,'ShowWriter':show_writer,'DebugNextStep':debug_next_step,
  'ReleaseEncounter':release_encounter,'EnableConfirm':enable_confirm,'DisableConfirm':disable_confirm}
GRAPHS.update(ActivateCar=activate_car,StageStop=stage_stop,UseStop=use_stop,StopActionFinished=stop_action_finished,
    AdvanceStopDialogue=advance_stop_dialogue,PreviewRejection=preview_rejection,EndMergePreview=end_merge_preview,
    ReturnToCar=return_to_car,FinishReturnToCar=finish_return_to_car,ReleaseStop=release_stop,ReapplyStageView=reapply_stage_view,
    RetryDraft=retry_draft,RetryWithoutTiming=retry_without_timing)
GRAPHS.update(ShowCVPaper=show_cv_paper,OpenCVPaper=open_cv_paper,CheckCVPaper=check_cv_paper,ReleaseCVPaper=release_cv_paper)
GRAPHS['SetCVHudOpacity']=cv_hud_opacity
STEPS={'skeleton':skeleton,'widget':widget,'widget_layout':widget_layout,'debug_help':debug_help,**GRAPHS}
for _step in ('events','notes'):
    STEPS[_step]=lambda step=_step:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/journey_setup.py',
        env={'FOA_JOURNEY_SETUP':step},resources=['asset:'+D.ROOT,'asset:'+GI])

if __name__=='__main__':
    D.OWNER=os.environ.get('FOA_AGENT',D.OWNER)
    os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=D.OWNER
    editor_lock.acquire(D.OWNER,wait_s=300,ttl=180,areas=[D.ROOT,drive_data.ROOT]+([GI] if sys.argv[1]=='notes' else [])+([DEBUG] if sys.argv[1]=='debug_help' else []))
    try:
        assert not call('editor_get_state')['pie_running']
        STEPS[sys.argv[1]]()
    finally:
        for path in (BP,HUD):
            if Path('P:/FoA/Content'+path[5:]+'.uasset').exists():
                result=h.call('blueprint_compile',{'path':path})
                assert result.get('ok') and not result.get('data',{}).get('error_count'),result
        editor_lock.release(D.OWNER)
