"""Keep the body visible in first person and restore the head for authored cameras."""
import sys
sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h
from held_tool_graphs import Batch, inspect, find

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
F = 'UpdateFirstPersonVisibility'
GS = '/Script/Engine.GameplayStatics:'
K = '/Script/Engine.KismetMathLibrary:'


def run():
    assert not h.call('editor_get_state')['data']['pie_running']
    existing=h.call('blueprint_inspect_graph',dict(path=P,graph_name=F))
    if existing.get('ok') and any(norm_title(n['title']) not in (norm_title(F),'returnnode','comment')
                                  for n in existing.get('data',{}).get('nodes',[])):
        print('Existing first-person camera preserved, including all runtime extensions. '
              'Use patch_interaction_camera.py for a missing interaction look hook; apply other updates as scoped patches.')
        return
    owner = h.agent_id()
    token = h.lease_acquire(owner, ['asset:'+P], ttl_s=90, wait_s=30)
    try:
        added=h.call('blueprint_add_variable',dict(path=P,variable_name='FPViewRotation',variable_type='rotator',default_value='0,0,0',instance_editable=False,update_existing=True,category='Camera'))
        assert added.get('ok'),added
        added=h.call('blueprint_add_variable',dict(path=P,variable_name='bBattleActive',variable_type='bool',default_value='false',instance_editable=False,update_existing=True,category='Camera'))
        assert added.get('ok'),added
        init='AttachFirstPersonCamera'
        if not h.call('blueprint_inspect_graph',dict(path=P,graph_name=init)).get('ok'):
            assert h.call('blueprint_add_function',dict(path=P,function_name=init))['ok']
        nodes,_=inspect(P,init);entry=find(nodes,init)
        b=Batch(P,init);old=[n['node_id'] for n in nodes if n['node_id']!=entry]
        if old:b.ops.append(dict(op='remove',node_ids=old))
        b.get('camera','FollowCamera',0,300);b.get('head','Face',0,500)
        b.fn('attach','/Script/Engine.SceneComponent:K2_AttachToComponent',400,0,SocketName='head',
             LocationRule='KeepRelative',RotationRule='KeepWorld',ScaleRule='KeepWorld',bWeldSimulatedBodies=False)
        b.link('camera','FollowCamera','attach','self');b.link('head','Face','attach','Parent')
        # Same teen head-space landmark used by UpdateFaceMaskPose; it survives head animation and retargeting.
        b.fn('eye','/Script/Engine.SceneComponent:K2_SetRelativeLocation',800,0,
             NewLocation='0,-3.530588955620998,11.768322164387774',bSweep=False,bTeleport=True)
        b.link('camera','FollowCamera','eye','self')
        b.fn('absolute','/Script/Engine.SceneComponent:SetAbsolute',1100,0,bNewAbsoluteLocation=False,bNewAbsoluteRotation=True,bNewAbsoluteScale=True)
        b.link('camera','FollowCamera','absolute','self');b.chain(entry,'attach','eye','absolute')
        b.fn('manager',GS+'GetPlayerCameraManager',1100,600,PlayerIndex=0)
        b.set('minpitch','ViewPitchMin',1400,0,'/Script/Engine.PlayerCameraManager');b.pin('minpitch','ViewPitchMin',-65)
        b.set('maxpitch','ViewPitchMax',1700,0,'/Script/Engine.PlayerCameraManager');b.pin('maxpitch','ViewPitchMax',65)
        for ref in ('minpitch','maxpitch'):b.link('manager','ReturnValue',ref,'self')
        b.chain('absolute','minpitch','maxpitch')
        b.comment('Follow animated teen head',[o['ref'] for o in b.ops if 'ref' in o]);b.run()
        nodes,edges=inspect(P,'EventGraph')
        if not any(n['title'].replace(' ','')==init for n in nodes):
            entry=find(nodes,'Event BeginPlay')
            after=[x for x in edges if x['from_node']==entry and x['from_pin']=='then']
            assert after,'Preserve the player BeginPlay chain'
            b=Batch(P,'EventGraph');b.fn('attachfp',P+'.BP_FoAPlayer_C:'+init,-300,-500)
            for x in after:
                b.cut(entry,'then',x['to_node'],x['to_pin']);b.link('attachfp','then',x['to_node'],x['to_pin'])
            b.chain(entry,'attachfp');b.comment('First person camera',['attachfp']);b.run()
        if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=F)).get('ok'):
            assert h.call('blueprint_add_function', dict(path=P, function_name=F))['ok']
        nodes, _ = inspect(P, F)
        e = find(nodes, F)
        b = Batch(P, F)
        old = [n['node_id'] for n in nodes if n['node_id'] != e]
        if old: b.ops.append(dict(op='remove', node_ids=old))
        b.fn('pc', GS+'GetPlayerController', 0, 300, PlayerIndex=0)
        b.fn('view', '/Script/Engine.PlayerController:GetViewTarget', 240, 300)
        b.link('pc','ReturnValue','view','self')
        b.node('self','self',0,500)
        b.fn('direct',K+'EqualEqual_ObjectObject',500,300)
        b.link('view','ReturnValue','direct','A');b.link('self','self','direct','B')
        b.fn('parent','/Script/Engine.Actor:GetAttachParentActor',500,500)
        b.link('view','ReturnValue','parent','self')
        b.fn('phone',K+'EqualEqual_ObjectObject',760,500)
        b.link('parent','ReturnValue','phone','A');b.link('self','self','phone','B')
        b.fn('inside',K+'BooleanOR',1040,300)
        b.link('direct','ReturnValue','inside','A');b.link('phone','ReturnValue','inside','B')
        b.set('remember','bCameraClose',1040,0)
        b.link('inside','ReturnValue','remember','bCameraClose');b.chain(e,'remember')
        b.get('cine','bCinematic',0,900);b.get('interact','bInteractionLocked',0,1050)
        b.fn('authored',K+'BooleanOR',300,900)
        b.link('cine','bCinematic','authored','A');b.link('interact','bInteractionLocked','authored','B')
        b.get('battleowned','bBattleActive',300,1250)
        b.fn('authored_battle',K+'BooleanOR',600,1150);b.link('authored','ReturnValue','authored_battle','A');b.link('battleowned','bBattleActive','authored_battle','B')
        b.fn('free',K+'Not_PreBool',600,900);b.link('authored_battle','ReturnValue','free','A')
        b.set('yaw','bUseControllerRotationYaw',1300,0,'/Script/Engine.Pawn')
        b.link('self','self','yaw','self')
        b.link('free','ReturnValue','yaw','bUseControllerRotationYaw');b.chain('remember','yaw')
        b.get('camera','FollowCamera',1300,1250)
        b.fn('look','/Script/Engine.Controller:GetControlRotation',1050,1250);b.link('pc','ReturnValue','look','self')
        # The capsule can turn before the animated torso, or stay fixed during an interaction.
        b.get('body','Body',1500,1500)
        for side in ('l','r'):
            b.fn('shoulder'+side,'/Script/Engine.SceneComponent:GetSocketLocation',1750,1500+(side=='r')*200,InSocketName='upperarm_'+side)
            b.link('body','Body','shoulder'+side,'self')
        b.fn('across',K+'Subtract_VectorVector',2000,1500)
        b.link('shoulderr','ReturnValue','across','A');b.link('shoulderl','ReturnValue','across','B')
        b.fn('forward',K+'Cross_VectorVector',2250,1500,B='0,0,1');b.link('across','ReturnValue','forward','A')
        b.fn('torso',K+'MakeRotFromX',2500,1500);b.link('forward','ReturnValue','torso','X')
        b.fn('delta',K+'NormalizedDeltaRotator',2750,1500)
        b.link('look','ReturnValue','delta','A');b.link('torso','ReturnValue','delta','B')
        for ref,source in (('angles','look'),('relative','delta'),('torsoangles','torso')):
            b.fn(ref,K+'BreakRotator',3000,1500+('angles','relative','torsoangles').index(ref)*200)
            b.link(source,'ReturnValue',ref,'InRot')
        b.fn('pitchsigned',K+'NormalizeAxis',3250,1500);b.link('angles','Pitch','pitchsigned','Angle')
        b.fn('pitchlimit',K+'FClamp',3500,1500,Min=-65,Max=65);b.link('pitchsigned','ReturnValue','pitchlimit','Value')
        b.fn('yawlimit',K+'FClamp',3250,1700,Min=-60,Max=60);b.link('relative','Yaw','yawlimit','Value')
        b.fn('yawworld',K+'Add_DoubleDouble',3500,1700)
        b.link('torsoangles','Yaw','yawworld','A');b.link('yawlimit','ReturnValue','yawworld','B')
        b.fn('bounded',K+'MakeRotator',3750,1500,Roll=0)
        b.link('pitchlimit','ReturnValue','bounded','Pitch');b.link('yawworld','ReturnValue','bounded','Yaw')
        b.fn('freeview',K+'MakeRotator',3750,1800,Roll=0)
        b.link('pitchlimit','ReturnValue','freeview','Pitch');b.link('angles','Yaw','freeview','Yaw')
        b.fn('chosen',K+'SelectRotator',4050,1500)
        b.link('bounded','ReturnValue','chosen','A');b.link('freeview','ReturnValue','chosen','B');b.link('authored','ReturnValue','chosen','bPickA')
        # Never feed delayed turn-in-place shoulders back into free mouse yaw. Snapshot once before the setter.
        b.set('viewrotation','FPViewRotation',1550,0);b.link('chosen','ReturnValue','viewrotation','FPViewRotation')
        b.node('firstperson','branch',1850,0);b.link('direct','ReturnValue','firstperson','Condition');b.chain('yaw','viewrotation','firstperson')
        b.fn('limitcontrol','/Script/Engine.Controller:SetControlRotation',2150,0)
        b.link('pc','ReturnValue','limitcontrol','self');b.link('viewrotation','Output_Get','limitcontrol','NewRotation');b.chain('firstperson','limitcontrol')
        b.fn('lookcamera','/Script/Engine.SceneComponent:K2_SetWorldRotation',2450,0,bSweep=False,bTeleport=True)
        b.link('camera','FollowCamera','lookcamera','self');b.link('viewrotation','Output_Get','lookcamera','NewRotation');b.chain('limitcontrol','lookcamera')
        b.link('firstperson','else','lookcamera','execute')
        b.fn('visible',K+'Not_PreBool',1300,300);b.link('inside','ReturnValue','visible','A')
        last = 'lookcamera'
        for i, part in enumerate(('Face','Hair','Eyebrows')):
            b.get(part,part,2750+i*300,500)
            b.fn(part+'show','/Script/Engine.SceneComponent:SetVisibility',2750+i*300,0,bPropagateToChildren=False)
            b.link(part,part,part+'show','self');b.link('visible','ReturnValue',part+'show','bNewVisibility')
            b.chain(last,part+'show');last=part+'show'
        b.comment('First person visibility',[o['ref'] for o in b.ops if 'ref' in o]);b.run()
        nodes, edges = inspect(P,'EventGraph')
        tick=find(nodes,'Event Tick')
        hooked=[n for n in nodes if n['title'].replace(' ','')==F]
        if not hooked:
            assert not [x for x in edges if x['from_node']==tick and x['from_pin']=='then'], 'Preserve existing Tick work'
            b=Batch(P,'EventGraph');b.fn('visibility',P+'.BP_FoAPlayer_C:'+F,300,3600)
            b.chain(tick,'visibility');b.comment('Gameplay head visibility',['visibility']);b.run()
        nodes,edges=inspect(P,'EventGraph')
        assert any(x['from_node']==tick and x['from_pin']=='then' for x in edges)
        for fn,flag in (('SetCinematic','bCinematic'),('SetInteractionLocked','bInteractionLocked')):
            nodes,edges=inspect(P,fn)
            if any(n['title'].replace(' ','')==F for n in nodes):continue
            setter=find(nodes,'Set '+flag)
            after=[x for x in edges if x['from_node']==setter and x['from_pin']=='then']
            b=Batch(P,fn)
            b.fn('orientation',P+'.BP_FoAPlayer_C:'+F,1000,-350)
            for x in after:
                b.cut(setter,'then',x['to_node'],x['to_pin'])
                b.link('orientation','then',x['to_node'],x['to_pin'])
            b.chain(setter,'orientation');b.comment('Authored pose ownership',['orientation']);b.run()
        r=h.call('blueprint_set_defaults',dict(path=P,properties={'JumpMaxCount':0,'bUseControllerRotationYaw':False}))
        assert r.get('ok') and not r.get('data',{}).get('failed'),r
        from patch_interaction_camera import apply_missing
        apply_missing()
        assert h.call('asset_save',dict(asset_paths=[P]))['ok']
    finally:
        h.release(owner,token)


def norm_title(title):return title.replace(' ','').replace('_','').lower()


if __name__=='__main__':run()
