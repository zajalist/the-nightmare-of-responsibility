"""Owned, bounded diagnostic only: shipping locomotion/visible sock poses, no asset edits.
Real FE bootstrap, ordinary movement input on a capsule-swept room lane. The existing
Director camera documents feet transiently; animation, speed, capsule/floor stay intact.
"""
import datetime,json,math,time
from pathlib import Path
import unreal

w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world();assert w
p=unreal.GameplayStatics.get_player_character(w,0);pc=unreal.GameplayStatics.get_player_controller(w,0)
def actor(path):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,'/Game/FoA/'+path))
d=actor('Gameplay/BP_BeatDirector.BP_BeatDirector_C');fe=actor('UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
gi=unreal.GameplayStatics.get_game_instance(w)
original=(str(gi.get_editor_property('SaveSlot')),set(gi.get_editor_property('Knowledge')),list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext',('FoA_QA_WalkContact',set(),[]))
folder=Path('P:/FoA/Saved/CharacterShots/walk_contact')/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');folder.mkdir(parents=True)
(folder/'frames').mkdir()
S=dict(start=time.time(),h=None,done=False,actions=set(),rows=[],frames=[],phase='boot',at=0,sample=0,shot=0,cam=None,config={})
v=lambda q:[q.x,q.y,q.z]
def xf(t):return dict(position=v(t.translation),rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=v(t.scale3d))
def hit_parts(hit):
    if isinstance(hit,tuple):hit=hit[1] if hit[0] else None
    return hit.to_tuple() if hit else None
def ground(pos):
    hit=hit_parts(unreal.SystemLibrary.line_trace_single(w,pos+unreal.Vector(0,0,25),pos-unreal.Vector(0,0,100),unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[p],unreal.DrawDebugTrace.NONE,True))
    if not hit or not hit[0]:return None
    # FHitResult tuple: blocking,penetrating,time,distance,location,impact_point,normal,impact_normal...
    owner=next((x for x in hit if isinstance(x,unreal.Actor)),None)
    return dict(point=v(hit[5]),normal=v(hit[7]),actor=owner.get_actor_label() if owner else None)
def finish(reason,error=None):
    if S['done']:return
    S['done']=True
    if S['h']:unreal.unregister_slate_post_tick_callback(S['h'])
    if S['cam']:
        pc.set_view_target_with_blend(p,0)
        old=S['camera_home'];S['cam'].set_world_location_and_rotation(old.translation,old.rotation.rotator(),False,True)
        S['cam'].set_field_of_view(S['camera_fov'])
        if not S['camera_active']:S['cam'].deactivate()
    gi.call_method('SetProofProgressContext',original)
    unreal.GameplayStatics.delete_game_in_slot('FoA_QA_WalkContact',0)
    result=dict(reason=reason,error=error,folder=str(folder),config=S['config'],rows=S['rows'],frames=S['frames'],
        limitation='Diagnostic side-view camera; ordinary AddMovementInput, not raw keyboard. Skin reconstruction must match mesh/reference; no automatic visual acceptance.')
    (folder/'capture.json').write_text(json.dumps(result))
    (folder.parent/'latest.json').write_text(json.dumps(dict(reason=reason,error=error,folder=str(folder))))
def setup():
    sock=next(c for c in p.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name()=='StartSocks')
    assert sock.is_visible(),'Normal starter socks not visible'
    assert sock.get_skeletal_mesh_asset().get_path_name().split('.')[0]=='/Game/FoA/Characters/Teen/Mesh/SK_Teen_Socks'
    S['sock']=sock;S['source']=p.get_editor_property('Mesh');movement=p.get_editor_property('character_movement')
    S['config']=dict(mesh=sock.get_skeletal_mesh_asset().get_path_name(),world=xf(sock.get_world_transform()),
        WalkSpeed=p.get_editor_property('WalkSpeed'),max_walk_speed=movement.get_editor_property('max_walk_speed'),
        acceleration=movement.get_editor_property('max_acceleration'),deceleration=movement.get_editor_property('braking_deceleration_walking'),
        ground_friction=movement.get_editor_property('ground_friction'),source_mesh=S['source'].get_skeletal_mesh_asset().get_path_name(),
        source_world=xf(S['source'].get_world_transform()),collision=[dict(name=c.get_name(),enabled=str(c.get_collision_enabled()),profile=str(c.get_collision_profile_name())) for c in p.get_components_by_class(unreal.PrimitiveComponent)])
    cap=p.get_editor_property('capsule_component');radius=cap.get_scaled_capsule_radius();half=cap.get_scaled_capsule_half_height()
    lane=None
    for y in (-60,20,90,145):
        start=unreal.Vector(220,y,half+3);end=unreal.Vector(-220,y,half+3)
        hit=hit_parts(unreal.SystemLibrary.capsule_trace_single_by_profile(w,start,end,radius,half,'Pawn',False,[p],unreal.DrawDebugTrace.NONE,True))
        if (not hit or not hit[0]) and ground(unreal.Vector(0,y,8)):
            lane=(start,end);break
    assert lane,'No unobstructed440cm room lane: do not accept wall-limited speed'
    S['config']['lane']=[v(q) for q in lane]
    assert p.teleport(lane[0],unreal.Rotator(pitch=0,yaw=180,roll=0))
    rotation=p.get_actor_rotation();assert abs(rotation.pitch)<.01 and abs(rotation.roll)<.01,rotation
    pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=180,roll=0));S['direction']=unreal.Vector(-1,0,0)
    S['cam']=d.get_editor_property('TopDownCamera');S['camera_home']=S['cam'].get_world_transform()
    S['camera_fov']=S['cam'].get_editor_property('field_of_view');S['camera_active']=S['cam'].is_active()
    S['cam'].activate(True);S['cam'].set_field_of_view(52)
    pc.set_view_target_with_blend(d,0)
    S['phase']='idle_start';S['at']=time.time();S['sample']=0;S['shot']=0
def sample(t):
    sock=S['sock'];a=S['source'].get_anim_instance();velocity=p.get_velocity()
    bones=[]
    for name in ('calf_l','foot_l','ball_l','calf_r','foot_r','ball_r'):
        bones.append(dict(name=name,**xf(sock.get_socket_transform(name,unreal.RelativeTransformSpace.RTS_COMPONENT))))
    S['rows'].append(dict(t=t,phase=S['phase'],position=v(p.get_actor_location()),velocity=v(velocity),
        speed=math.hypot(velocity.x,velocity.y),ground_speed=a.get_editor_property('GroundSpeed'),
        root_mode=str(a.get_editor_property('RootMotionMode')),root_yaw=a.get_editor_property('RootYawOffset'),
        cinematic=p.get_editor_property('bCinematic'),locked=p.get_editor_property('bInteractionLocked'),actor_rotation=str(p.get_actor_rotation()),
        montage=str(a.get_current_active_montage()),world=xf(sock.get_world_transform()),bones=bones,
        ground={side:ground(sock.get_socket_location('ball_'+side)) for side in ('l','r')}))
def tick(dt):
    try:
        now=time.time();t=now-S['start']
        if t>29:return finish('timeout')
        if S['phase']=='boot':
            screen=fe.get_editor_property('Screen')
            if screen and screen.is_in_viewport():
                for prop,action in [('SplashClass','OnSplashFinished'),('TitleClass','OnTitleConfirmed'),('MainMenuClass','WakeUp')]:
                    if screen.get_class()==fe.get_editor_property(prop) and action not in S['actions']:
                        S['actions'].add(action);fe.call_method(action,());return
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport() and 'story' not in S['actions']:
                S['actions'].add('story');story.call_method('Finish',());return
            if fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and 'skip' not in S['actions']:
                S['actions'].add('skip');d.call_method('SkipWakeUp',());return
            if d.get_editor_property('bWakeDone') and pc.get_view_target()==p and not p.get_editor_property('bCinematic') and not p.get_editor_property('bInteractionLocked'):
                unreal.SystemLibrary.pause_timer(d,'PollStoryMoment');unreal.SystemLibrary.clear_timer(d,'TryStoryMoment');setup()
            return
        elapsed=now-S['at'];phase=S['phase']
        if phase=='idle_start' and elapsed>1:S['phase']='walk_out';S['at']=now
        elif phase=='walk_out' and elapsed>3.2:S['phase']='stop_out';S['at']=now
        elif phase=='stop_out' and elapsed>1.3:
            S['phase']='turn_idle';S['at']=now;S['direction']=unreal.Vector(1,0,0);pc.set_control_rotation(unreal.Rotator(pitch=0,yaw=0,roll=0))
        elif phase=='turn_idle' and elapsed>1:S['phase']='walk_back';S['at']=now
        elif phase=='walk_back' and elapsed>3.2:S['phase']='stop_back';S['at']=now
        elif phase=='stop_back' and elapsed>1.5:return finish('captured_requires_contact_and_visual_review')
        if S['phase'].startswith('walk'):p.add_movement_input(S['direction'],1)
        pos=p.get_actor_location();eye=pos+unreal.Vector(-50,155,-38);aim=pos+unreal.Vector(0,0,-58)
        rotation=p.get_actor_rotation();assert abs(rotation.pitch)<.01 and abs(rotation.roll)<.01,rotation
        S['cam'].set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,aim),False,True)
        if now>=S['sample']:sample(t);S['sample']=now+1/30
        if now>=S['shot']:
            index=len(S['frames']);name='f%04d.bmp'%index;S['frames'].append(dict(t=t,phase=S['phase'],file=name))
            unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(folder/'frames'/name)+' -nosuffix',pc);S['shot']=now+.25
    except Exception as error:finish('error',repr(error))
S['h']=unreal.register_slate_post_tick_callback(tick)
