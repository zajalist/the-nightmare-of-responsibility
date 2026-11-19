"""Observe the actual wake cameras and normal release; never replace the camera or pose."""
import datetime,json,time
from pathlib import Path
import unreal
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
fe=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
d=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
root=Path('P:/FoA/Saved/CharacterShots/wake_handoff');folder=root/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True,exist_ok=True)
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_WakeReview',set(),[]))
S=dict(start=time.monotonic(),phase=0,h=None,rows=[],shots=set(),last_sample=0,exit=None,wake_started=False,story=False,done=False)
def vector(v):return [v.x,v.y,v.z]
def sample(t,seq_seconds):
    cm=p.get_editor_property('CharacterMovement');loc=p.get_actor_location()
    row=dict(t=t,sequence=seq_seconds,location=vector(loc),velocity=vector(p.get_velocity()),
        yaw=p.get_actor_rotation().yaw,ignored=pc.is_move_input_ignored(),done=d.get_editor_property('bWakeDone'),
        look_ignored=pc.is_look_input_ignored(),cinematic=p.get_editor_property('bCinematic'),
        camera=vector(pc.player_camera_manager.get_camera_location()),camera_rotation=pc.player_camera_manager.get_camera_rotation().export_text(),
        view=pc.get_view_target().get_class().get_name(),falling=cm.is_falling())
    try:
        floor=cm.get_editor_property('current_floor');hit=floor.get_editor_property('hit_result').to_tuple()
        row.update(floor_dist=floor.get_editor_property('floor_dist'),floor_impact=vector(hit[5]),floor_blocking=hit[0])
    except Exception as e:row['floor_read_error']=str(e)
    S['rows'].append(row)
def shot(label):
    body=p.get_editor_property('Body')
    def xf(t):return dict(position=vector(t.translation),rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=vector(t.scale3d))
    bones=[]
    for i in range(body.get_num_bones()):
        n=body.get_bone_name(i);bones.append(dict(name=str(n),**xf(body.get_socket_transform(n,unreal.RelativeTransformSpace.RTS_COMPONENT))))
    (folder/(label+'_body_pose.json')).write_text(json.dumps(dict(mesh=body.get_skeletal_mesh_asset().get_path_name(),space='component',world=xf(body.get_world_transform()),bones=bones)))
    if label in ('wake_exit','wake_released'):
        dream=unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
        nightmare=unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C'))
        authored={'tear_amount':unreal.MaterialLibrary.get_scalar_parameter_value(w,dream,'TearAmount')}
        if nightmare:
            location=nightmare.get_actor_location();authored['nightmare_world']=vector(location)
            authored['nightmare_actor']=nightmare.get_path_name()
            authored['nightmare_stencil']=nightmare.mesh.get_editor_property('custom_depth_stencil_value')
            try:authored['nightmare_screen']=str(unreal.GameplayStatics.project_world_to_screen(pc,location+unreal.Vector(0,0,120),False))
            except Exception as exc:authored['projection_error']=str(exc)
        (folder/(label+'_authored_tear.json')).write_text(json.dumps(authored,indent=2))
        components=[]
        for component in p.get_components_by_class(unreal.PrimitiveComponent):
            row={'name':component.get_name(),'class':component.get_class().get_name(),'world':xf(component.get_world_transform()),'tick':component.is_component_tick_enabled()}
            for name in ('visible','hidden_in_game','cast_shadow','cast_hidden_shadow','bounds_scale','shadow_cache_invalidation_behavior'):
                try:row[name]=str(component.get_editor_property(name))
                except Exception as exc:row[name]={'unavailable':str(exc)}
            if isinstance(component,unreal.SkeletalMeshComponent):
                row['bones']={str(component.get_bone_name(i)):xf(component.get_socket_transform(component.get_bone_name(i),unreal.RelativeTransformSpace.RTS_COMPONENT)) for i in range(component.get_num_bones())}
            components.append(row)
        (folder/(label+'_shadow_components.json')).write_text(json.dumps(components))
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/(label+'.png'))+' -nosuffix',pc)
    S['shots'].add(label)
def finish(reason):
    if S['done']:return
    S['done']=True
    unreal.unregister_slate_post_tick_callback(S['h'])
    gi.call_method('SetProofProgressContext',original)
    unreal.GameplayStatics.delete_game_in_slot('FoA_QA_WakeReview',0)
    result=dict(reason=reason,folder=str(folder),rows=S['rows'],shots=list(S['shots']))
    (folder/'evidence.json').write_text(json.dumps(result,indent=1));(root/'latest.json').write_text(json.dumps(result,indent=1))
def tick(dt):
    try:
        t=time.monotonic()-S['start']
        if t>43:return finish('time_cap')
        if S['phase']==0 and t>.3:fe.call_method('OnSplashFinished',());S['phase']=1
        elif S['phase']==1 and t>1:fe.call_method('OnTitleConfirmed',());S['phase']=2
        elif S['phase']==2 and t>1.8:fe.call_method('WakeUp',());S['phase']=3
        if S['phase']<3:return
        story=fe.get_editor_property('Story')
        if story and story.is_in_viewport() and not S['story']:
            story.call_method('Finish',());S['story']=True;return
        seq=d.get_editor_property('SeqPlayer');seconds=0
        if seq:
            q=seq.get_current_time();seconds=(q.time.frame_number.value+q.time.sub_frame)*q.rate.denominator/q.rate.numerator
            if not d.get_editor_property('bWakeDone'):S['wake_started']=True
        if t-S['last_sample']>.10:sample(t,seconds);S['last_sample']=t
        if S['wake_started'] and not d.get_editor_property('bWakeDone'):
            for at,label in ((2,'sleep_wide'),(8,'sleep_close'),(13,'alarm'),(22,'bed_edge'),(29,'standing_transition')):
                if seconds>at and label not in S['shots']:shot(label)
        if S['wake_started'] and d.get_editor_property('bWakeDone'):
            if S['exit'] is None:S['exit']=t
            e=t-S['exit']
            for at,label in ((.15,'wake_exit'),(.8,'wake_released')):
                if e>at and label not in S['shots']:shot(label)
            if e>1.2:
                assert S['story'] and 'sleep_close' in S['shots']
                assert pc.get_view_target()==p and not p.get_editor_property('bCinematic')
                assert not pc.is_move_input_ignored() and not pc.is_look_input_ignored()
                assert not p.character_movement.is_falling() and p.get_actor_location().z>25
                return finish('natural_wake_handoff_passed')
    except Exception as e:S['rows'].append(dict(error=repr(e)));finish('error')
S['h']=unreal.register_slate_post_tick_callback(tick)
