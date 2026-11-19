"""One reusable runtime stage with real ticket/shelf/bed actions; native Blueprint logic."""
import json
import os
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).parent),'P:/FoA/Tools/Unreal']
import stop_set_data as D
import interview_data as I
from build_drive import G,call,cls,A,SC,SL,GS
import hayba_call as h
import editor_lock

BP=D.BP
PLAYER='/Game/FoA/Characters/Player/BP_FoAPlayer'
JOURNEY='/Game/FoA/Level2/Journey/BP_L2Journey'
SK='/Script/Engine.SkeletalMeshComponent:'
SIG={'Configure':[('Index','int'),('Player','object:'+cls(PLAYER)),('Journey','object:/Script/Engine.Actor')],
     'ShowView':[('View','int')],'UseAction':[],'ActionStep':[],'ClearPose':[],'Restore':[],'StagePlayer':[],'PrepareFinale':[],
     'PrepareInterview':[],'ShowStopSplats':[],'ResetInterviewSplats':[]}

def vec(v):return ','.join(map(str,v))
def asset(p):return p+'.'+p.rsplit('/',1)[-1]
def selfref(g):
    r=g.ref();g.node(r,'self',0,0);return r,'self'
def world(g,position):return g.math('TransformLocation',T=g.f(A+'GetTransform'),Location=vec(position))
def move_player(g,position,yaw):
    g.do(A+'K2_SetActorLocationAndRotation',self=g.getv('Player'),NewLocation=world(g,position),NewRotation='0,'+str(yaw)+',0',bSweep=False,bTeleport=True)
def anim(g):return g.f(SK+'GetAnimInstance',self=g.getv('Mesh',g.getv('Player'),PLAYER))
def timer(g,name,seconds,loop=False):g.do(SL+'K2_SetTimer',FunctionName=name,Time=seconds,bLooping=loop)

def skeleton():
    if not h.call('blueprint_get_info',{'path':BP}).get('ok'):call('blueprint_create',package_path=BP,name='BP_L2StopSet',parent_class_path='/Script/Engine.Actor')
    info=call('blueprint_get_info',path=BP);variables={v['name'] for v in info['variables']}
    for name,typ,val in [('Index','int','0'),('Player','object:'+cls(PLAYER),''),('Journey','object:/Script/Engine.Actor',''),
                         ('ActionRunning','bool','false'),('ActionDone','bool','false'),('ActionStarted','float','0'),('Seated','bool','false'),('TicketTaken','bool','false'),
                         ('PoseMontage','object:/Script/Engine.AnimMontage','')]:
        if name not in variables:call('blueprint_add_variable',path=BP,variable_name=name,variable_type=typ,default_value=val,category='Stop set')
    for name,inputs in SIG.items():
        if name not in info['functions']:call('blueprint_add_function',path=BP,function_name=name,inputs=[dict(name=n,type=t) for n,t in inputs])
    specs=[('Root','SceneComponent')]+[(n,'SceneComponent') for n in D.GROUPS]
    specs += [(n,'SceneComponent') for n,_ in D.EXTRA_GROUPS]
    specs += [(row[0],'StaticMeshComponent') for row in D.MESHES]+[(row[0],'TextRenderComponent') for row in D.SIGNS]
    specs += [(row[0],'SkeletalMeshComponent') for row in D.FIGURES]+[('StageCamera','CameraComponent')]
    specs += [(name+part,'SkeletalMeshComponent') for name in D.STAFF for part in ('Face','Suit')]
    specs += [(row[0],'RectLightComponent') for row in D.LIGHTS]
    specs += [('InterviewBackdrop','StaticMeshComponent'),('InterviewSky','StaticMeshComponent'),
              ('InterviewBody','SkeletalMeshComponent'),('InterviewFace','SkeletalMeshComponent'),
              ('InterviewSuit','SkeletalMeshComponent')]
    existing={c['name'] for c in info.get('components',[])}
    if any(row.get('path')=='components' for row in info.get('_truncated',[])):
        # GetInfo is transport-capped at 50 entries; this stage owns 54 components.
        # Read every SCS handle before deciding a rerun needs another component.
        script='\n'.join(('import unreal, json',f'bp=unreal.load_asset({BP!r})',
            'lib=unreal.SubobjectDataBlueprintFunctionLibrary',
            'sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)',
            'handles=sub.k2_gather_subobject_data_for_blueprint(bp)',
            'print(json.dumps([str(lib.get_variable_name(lib.get_data(x))) for x in handles]))'))
        existing=set(json.loads(call('python_run',script=script)['stdout'].strip()))
    for name,kind in specs:
        if name not in existing:call('blueprint_add_component',path=BP,component_name=name,component_class_path='/Script/Engine.'+kind)
    call('blueprint_compile',path=BP);call('asset_save',asset_paths=[BP])

def components():
    call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/stop_set_setup.py',env={},resources=['asset:'+BP])

def configure():
    g=G(BP,'Configure');g.setv('Player',g.arg('Player'));g.setv('Journey',g.arg('Journey'));g.setv('Index',g.arg('Index'))
    g.setv('ActionDone',False);g.setv('ActionRunning',False);g.setv('TicketTaken',False)
    for i,name in enumerate(D.GROUPS):
        show=g.math('EqualEqual_IntInt',A=g.arg('Index'),B=i)
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=show,bPropagateToChildren=True)
    for name in ('InterviewBody','InterviewFace','InterviewSuit'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=True)
    inverse=g.math('InvertTransform',T=g.f(A+'GetTransform',self=g.getv('Player')))
    for name,parent,at,yaw in D.FIGURES:
        clip=I.IDLE if name in D.STAFF else D.SIT
        g.do(SK+'PlayAnimation',self=g.getv(name),NewAnimToPlay=asset(clip),bLooping=True)
        g.do(SK+'SetPlayRate',self=g.getv(name),Rate=1.)
        if name in D.STAFF:
            target=g.math('MakeTransform',Location=world(g,(at[0],at[1],at[2]+92)),Rotation='0,'+str(yaw)+',0',Scale='1,1,1')
            for component,leader in ((name,'Body'),(name+'Face','Face')):
                source=g.f(SC+'K2_GetComponentToWorld',self=g.getv(leader,g.getv('Player'),PLAYER))
                local=g.math('ComposeTransforms',A=source,B=inverse)
                pose=g.math('ComposeTransforms',A=local,B=target)
                g.do(SC+'K2_SetWorldTransform',self=g.getv(component),NewTransform=pose,bSweep=False,bTeleport=True)
            for component in (name+'Face',name+'Suit'):
                g.do('/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent',self=g.getv(component),
                     NewLeaderBoneComponent=g.getv(name),bForceUpdate=True,bInFollowerShouldTickPose=False)
    g.own('StagePlayer');g.own('ShowView',View=0);g.own('ShowStopSplats');g.finish()


def stop_splats(finale=False):
    g=G(BP,'ResetInterviewSplats' if finale else 'ShowStopSplats')
    backdrop=g.getv('InterviewBackdrop')
    g.do(SC+'K2_SetRelativeLocation',self=backdrop,NewLocation=vec(I.BACKDROP) if finale else '1050,420,-50',bSweep=False,bTeleport=True)
    g.do(SC+'K2_SetRelativeRotation',self=backdrop,NewRotation='0,0,0' if finale else '0,180,0',bSweep=False,bTeleport=True)
    g.do(SC+'SetRelativeScale3D',self=backdrop,NewScale3D='1,1,1' if finale else '1.4,3.6,1.9')
    if not finale:
        g.do('/Script/Engine.PrimitiveComponent:SetCustomPrimitiveDataFloat',self=backdrop,DataIndex=1,Value=1.)
        for name in ('BackWall','FrontWall','WallLeft','WallRight','Ceiling','InterviewBackdrop','InterviewSky'):
            g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=name.startswith('Interview'),bPropagateToChildren=True)
    g.finish()


def wire_stop_splats():
    # The live set has hand-authored staff components. Keep its existing graphs.
    from build_drive import Batch, inspect
    info=call('blueprint_get_info',path=BP)
    for name in ('ShowStopSplats','ResetInterviewSplats'):
        if name not in info['functions']:call('blueprint_add_function',path=BP,function_name=name)
    call('blueprint_compile',path=BP)
    stop_splats();stop_splats(True)
    for graph,name,previous in (('Configure','ShowStopSplats','ShowView'),
                                ('PrepareInterview','ResetInterviewSplats','PrepareInterview')):
        nodes,edges=inspect(BP,graph)
        compact=lambda n:n['title'].split('\n')[0].replace(' ','')
        if any(compact(node)==name for node in nodes):continue
        old=next(node['node_id'] for node in nodes if compact(node)==previous)
        outgoing=[edge for edge in edges if edge['from_node']==old and edge['from_pin']=='then']
        assert len(outgoing)<=1,(graph,outgoing)
        patch=Batch(BP,graph)
        patch.fn('splats',cls(BP)+':'+name,0,-800)
        for edge in outgoing:
            patch.cut(old,'then',edge['to_node'],edge['to_pin'])
            patch.link('splats','then',edge['to_node'],edge['to_pin'])
        patch.chain(old,'splats')
        patch.comment('Interview splat setting',['splats']);patch.run()

def stage_player():
    g=G(BP,'StagePlayer')
    for i,at in enumerate(D.ENTRY):
        br=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Index'),B=i));g.side(br)
        move_player(g,at,D.ENTRY_YAW[i]);g.side(br,False)
    g.finish()

def show_view():
    g=G(BP,'ShowView')
    for i,(at,rotation) in D.CAMERAS.items():
        br=g.branch(g.math('EqualEqual_IntInt',A=g.arg('View'),B=i));g.side(br)
        views=(D.STOP_CAMERAS if i==0 else D.WRITER_CAMERAS).items() if i in (0,2) else [(None,(at,rotation))]
        for stop,(position,angle) in views:
            if stop is not None:
                stop_branch=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Index'),B=stop));g.side(stop_branch)
            g.do(SC+'K2_SetRelativeLocation',self=g.getv('StageCamera'),NewLocation=vec(position),bSweep=False,bTeleport=True)
            g.do(SC+'K2_SetRelativeRotation',self=g.getv('StageCamera'),NewRotation=vec(angle),bSweep=False,bTeleport=True)
            g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewViewTarget=selfref(g),BlendTime=.25)
            if stop is not None:g.side(stop_branch,False)
        g.side(br,False)
    g.finish()

def use_action():
    g=G(BP,'UseAction')
    allowed=g.math('Not_PreBool',A=g.math('BooleanOR',A=g.getv('ActionRunning'),B=g.getv('ActionDone')))
    br=g.branch(allowed);g.side(br);g.setv('ActionRunning',True);g.setv('ActionStarted',g.f(GS+'GetTimeSeconds'))
    office=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Index'),B=2));g.side(office)
    g.setv('Seated',True)
    g.do('/Script/Engine.CharacterMovementComponent:DisableMovement',self=g.getv('CharacterMovement',g.getv('Player'),PLAYER))
    pose=g.do('/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage',self=anim(g),Asset=asset(D.SIT),SlotNodeName='DefaultSlot',
              BlendInTime=.3,BlendOutTime=.25,InPlayRate=1,LoopCount=999,BlendOutTriggerTime=-1,InTimeToStartMontageAt=0)
    g.setv('PoseMontage',pose);g.own('ShowView',View=3);timer(g,'ActionStep',.05,True)
    g.side(office,False)
    g.do('/Script/Engine.Character:PlayAnimMontage',self=g.getv('Player'),AnimMontage=asset(D.PICKUP),InPlayRate=1)
    g.own('ShowView',View=1);timer(g,'ActionStep',.05,True);g.finish()

def action_step():
    g=G(BP,'ActionStep');running=g.branch(g.getv('ActionRunning'));g.side(running)
    age=g.math('Subtract_DoubleDouble',A=g.f(GS+'GetTimeSeconds'),B=g.getv('ActionStarted'))
    office=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Index'),B=2));g.side(office)
    blend=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=age,B=.45),Min=0,Max=1)
    location=g.math('VLerp',A=world(g,D.ENTRY[2]),B=world(g,D.SEATED),Alpha=blend)
    rotation=g.math('RLerp',A='0,90,0',B='0,-90,0',Alpha=blend,bShortestPath=True)
    g.do(A+'K2_SetActorLocationAndRotation',self=g.getv('Player'),NewLocation=location,NewRotation=rotation,bSweep=False,bTeleport=True)
    grocery=g.branch(g.math('EqualEqual_IntInt',A=g.getv('Index'),B=1));g.side(grocery)
    g.link(office,'else',grocery,'execute')
    for i,roll in enumerate(D.LABEL_ROLL):
        alpha=g.math('FClamp',Value=g.math('Divide_DoubleDouble',A=g.math('Subtract_DoubleDouble',A=age,B=D.LABEL_DELAY+D.LABEL_SPACING*i),B=D.LABEL_BLEND),Min=0,Max=1)
        angle=g.math('Multiply_DoubleDouble',A=roll,B=g.math('Subtract_DoubleDouble',A=1,B=alpha))
        rotation=g.math('MakeRotator',Roll=angle)
        g.do(SC+'K2_SetRelativeRotation',self=g.getv('Label'+str(i)),NewRotation=rotation,bSweep=False,bTeleport=True)
    take=g.math('BooleanAND',A=g.math('EqualEqual_IntInt',A=g.getv('Index'),B=0),
        B=g.math('BooleanAND',A=g.math('GreaterEqual_DoubleDouble',A=age,B=.6),B=g.math('Not_PreBool',A=g.getv('TicketTaken'))))
    ticket=g.branch(take);g.side(ticket);g.link(grocery,'else',ticket,'execute')
    g.do(SC+'K2_AttachToComponent',self=g.getv('Ticket'),Parent=g.getv('Body',g.getv('Player'),PLAYER),SocketName='hand_r',
         LocationRule='SnapToTarget',RotationRule='SnapToTarget',ScaleRule='KeepWorld',bWeldSimulatedBodies=False)
    g.do(SC+'K2_SetRelativeLocation',self=g.getv('Ticket'),NewLocation='4,0,0',bSweep=False,bTeleport=True)
    g.setv('TicketTaken',True)
    done=g.branch(g.math('GreaterEqual_DoubleDouble',A=age,B=D.ACTION_SECONDS));g.link(ticket,'else',done,'execute');g.side(done)
    g.setv('ActionRunning',False);g.setv('ActionDone',True);g.do(SL+'K2_ClearTimer',FunctionName='ActionStep')
    journey=g.cast(g.getv('Journey'),cls(JOURNEY),'BP L2Journey')
    g.do(cls(JOURNEY)+':StopActionFinished',self=journey);g.finish()

def clear_pose():
    g=G(BP,'ClearPose');valid=g.branch(g.f(SL+'IsValid',Object=g.getv('Player')));g.side(valid)
    g.do('/Script/Engine.Character:StopAnimMontage',self=g.getv('Player'),AnimMontage=asset(D.PICKUP))
    seated=g.branch(g.getv('Seated'));g.side(seated)
    g.do('/Script/Engine.Character:StopAnimMontage',self=g.getv('Player'),AnimMontage=g.getv('PoseMontage'))
    g.do('/Script/Engine.CharacterMovementComponent:SetMovementMode',self=g.getv('CharacterMovement',g.getv('Player'),PLAYER),NewMovementMode='MOVE_Walking')
    g.setv('Seated',False);g.finish()

def prepare_finale():
    g=G(BP,'PrepareFinale');g.own('ClearPose');g.own('ShowView',View=2);g.finish()


def prepare_interview():
    g=G(BP,'PrepareInterview');g.own('ResetInterviewSplats');g.own('ClearPose')
    for name,value in (('SandRadius',0),('SandProgress',0),('AmbientIntensity',0),('TargetBuilding',-1)):
        g.do('/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue',Collection='/Game/FoA/Level2/Materials/MPC_L2.MPC_L2',ParameterName=name,ParameterValue=value)
    g.do('/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue',Collection='/Game/FoA/Level2/Materials/MPC_L2.MPC_L2',ParameterName='Wind',ParameterValue=g.math('MakeColor',R=0,G=0,B=0,A=0))
    for index,value in ((0,0),(1,1)):
        g.do('/Script/Engine.PrimitiveComponent:SetCustomPrimitiveDataFloat',self=g.getv('InterviewBackdrop'),DataIndex=index,Value=value)
    g.do(A+'K2_SetActorLocationAndRotation',NewLocation=vec(I.ORIGIN),NewRotation='0,0,0',bSweep=False,bTeleport=True)
    for name in ('Career','Grocery','BackWall','FrontWall','WallLeft','WallRight','Ceiling','Floor'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=True)
    g.do(SC+'SetVisibility',self=g.getv('Office'),bNewVisibility=True,bPropagateToChildren=True)
    for name in ('OfficeBed','OfficeBedding','Receptionist','OfficeDressing','OfficeNoLift','OfficeChair'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=True)
    # Keep the existing invisible colliding floor. Reposition reused desk/paper
    # through relative translation, retaining their fitted mesh scale/pivot.
    delta=tuple(I.DESK[i]-(300,0,0)[i] for i in range(3))
    for name in ('OfficeDesk','OfficePaper'):
        g.do(SC+'K2_AddLocalOffset',self=g.getv(name),DeltaLocation=vec(delta),bSweep=False,bTeleport=True)
    for name in ('InterviewBackdrop','InterviewSky','InterviewBody','InterviewFace','InterviewSuit'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=True,bPropagateToChildren=True)
    # The interviewer owns its relaxed idle. Player combat state must never
    # drive this character; the matching Teen face follows its own body.
    g.do('/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent',self=g.getv('InterviewBody'),
         bForceUpdate=True,bInFollowerShouldTickPose=False)
    g.do(SK+'PlayAnimation',self=g.getv('InterviewBody'),NewAnimToPlay=asset(I.IDLE),bLooping=True)
    g.do(SK+'SetPlayRate',self=g.getv('InterviewBody'),Rate=1.)
    g.do('/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent',self=g.getv('InterviewFace'),
         NewLeaderBoneComponent=g.getv('InterviewBody'),bForceUpdate=True,bInFollowerShouldTickPose=False)
    g.do('/Script/Engine.SkinnedMeshComponent:SetLeaderPoseComponent',self=g.getv('InterviewSuit'),
         NewLeaderBoneComponent=g.getv('InterviewBody'),bForceUpdate=True,bInFollowerShouldTickPose=False)
    for component in ('InterviewBody','InterviewFace'):
        g.do('/Script/Engine.MeshComponent:SetScalarParameterValueOnMaterials',self=g.getv(component),ParameterName='Amount',ParameterValue=1.)
    move_player(g,I.PLAYER,I.PLAYER_YAW)
    # Body inherits CharacterMesh0's scale/offset. Reconstruct each live Teen
    # surface relative to the capsule instead of copying only its direct parent
    # transform (which would float or shrink this separate silhouette).
    inverse=g.math('InvertTransform',T=g.f(A+'GetTransform',self=g.getv('Player')))
    target=g.math('MakeTransform',Location=world(g,(I.INTERVIEWER[0],I.INTERVIEWER[1],I.INTERVIEWER[2]+92)),Rotation='0,0,0',Scale='1,1,1')
    for component,leader in (('InterviewBody','Body'),('InterviewFace','Face')):
        source=g.f(SC+'K2_GetComponentToWorld',self=g.getv(leader,g.getv('Player'),PLAYER))
        local=g.math('ComposeTransforms',A=source,B=inverse)
        pose=g.math('ComposeTransforms',A=local,B=target)
        g.do(SC+'K2_SetWorldTransform',self=g.getv(component),NewTransform=pose,bSweep=False,bTeleport=True)
    camera,rotation=I.CAMERA
    g.do(SC+'K2_SetRelativeLocation',self=g.getv('StageCamera'),NewLocation=vec(camera),bSweep=False,bTeleport=True)
    g.do(SC+'K2_SetRelativeRotation',self=g.getv('StageCamera'),NewRotation=vec(rotation),bSweep=False,bTeleport=True)
    g.do('/Script/Engine.CameraComponent:SetFieldOfView',self=g.getv('StageCamera'),InFieldOfView=58.)
    g.do('/Script/Engine.PlayerController:SetViewTargetWithBlend',self=g.f(GS+'GetPlayerController',PlayerIndex=0),NewViewTarget=selfref(g),BlendTime=0)
    g.finish()

def restore():
    g=G(BP,'Restore');g.setv('ActionRunning',False);g.do(SL+'K2_ClearTimer',FunctionName='ActionStep');g.own('ClearPose')
    for name in ('InterviewBody','InterviewFace','InterviewSuit'):
        g.do(SC+'SetVisibility',self=g.getv(name),bNewVisibility=False,bPropagateToChildren=True)
    g.do(SK+'Stop',self=g.getv('InterviewBody'));g.finish()

GRAPHS={'Configure':configure,'StagePlayer':stage_player,'ShowView':show_view,'UseAction':use_action,'ActionStep':action_step,
        'ClearPose':clear_pose,'PrepareFinale':prepare_finale,'PrepareInterview':prepare_interview,'Restore':restore}
STEPS={'skeleton':skeleton,'components':components,**GRAPHS}
STEPS.update(ShowStopSplats=stop_splats,ResetInterviewSplats=lambda:stop_splats(True),wire_stop_splats=wire_stop_splats)
STEPS['interview_components']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/interview_stage_setup.py',env={},resources=['asset:'+BP])
STEPS['interview_idle']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/interview_idle_setup.py',env={},resources=['asset:'+BP,'asset:'+I.IDLE])
STEPS['interview_suit']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/interview_suit_setup.py',env={},resources=['asset:'+BP])
STEPS['stock_labels']=lambda:call('python_exec_file',path='P:/FoA/Tools/Unreal/level2/stock_labels_setup.py',env={},resources=['asset:'+BP])
if __name__=='__main__':
    owner=os.environ.get('FOA_AGENT','main-level2-stops');os.environ['FOA_AGENT']=os.environ['HAYBA_AGENT_ID']=owner
    editor_lock.acquire(owner,wait_s=5,ttl=180,areas=[BP])
    try:
        assert not call('editor_get_state')['pie_running'];STEPS[sys.argv[1]]()
    finally:
        result=call('blueprint_compile',path=BP);assert not result.get('error_count'),result
        call('asset_save',asset_paths=[BP]);editor_lock.release(owner)
