"""Bounded 35-second PIE proof of live timers, gaze scene, repeated stages and reset.
Coordinator owns starting/stopping PIE. This script never starts or stops it.
"""
import json
import time
import unreal
OUT='P:/FoA/Saved/WorldShots/pie_room_takeover.json'
S={'start':time.time(),'i':0,'log':[],'handle':None,'done':False,'aim':None,'next_sample':0,'next_shot':0,'boot_start':time.time(),'boot_phase':0,'ready':False,'skip_sent':False}

def world():return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def one(w,c):return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,c))
def room(w):return one(w,'/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C')
def fe(w):return one(w,'/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
def director(w):return one(w,'/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
def pawn(w):return unreal.GameplayStatics.get_player_pawn(w,0)
def pc(w):return unreal.GameplayStatics.get_player_controller(w,0)
def log(kind,**values):S['log'].append({'t':round(time.time()-S['start'],3),'kind':kind,**values})

def snapshot(w):
    a=room(w);p=pawn(w);c=pc(w)
    parts={x.get_name():x for x in a.get_components_by_class(unreal.StaticMeshComponent)}
    inter=p.get_component_by_class(unreal.load_class(None,'/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
    d=director(w);seq=d.get_editor_property('SeqPlayer')
    owners={'beat':d.get_editor_property('BeatIndex'),'wake_done':d.get_editor_property('bWakeDone'),
      'sequence':seq.get_name() if seq else None,'sequence_playing':seq.is_playing() if seq else False,
      'frontend_gameplay':fe(w).get_editor_property('bInGameplay'),'frontend_waking':fe(w).get_editor_property('bWaking'),
      'headache':d.get_editor_property('bHeadacheActive'),'wardrobe_transition':d.get_editor_property('bWardrobeTransition'),
      'rollover':d.get_editor_property('bRollingOver')}
    hud=fe(w).get_editor_property('HUD')
    blink=hud.get_editor_property('Brd_HeadacheTop').get_editor_property('render_transform').scale.y if hud else 0
    reduce=unreal.MaterialLibrary.get_scalar_parameter_value(w,unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream'),'ReduceMotion')
    manager=unreal.GameplayStatics.get_player_camera_manager(w,0)
    return {'camera_location':list(manager.get_camera_location().to_tuple()),'pawn_location':list(p.get_actor_location().to_tuple()),'reduce_motion':reduce,'blink_height':blink,'peak_blink_height':S.get('headache_max_blink',0),'owners':owners,'stage':a.get_editor_property('Stage'),'progress':round(a.get_editor_property('StageProgress'),4),
        'scare_plays':a.get_editor_property('ScarePlays'),'painting_seen':a.get_editor_property('bPaintingSeen'),
        'dwell':a.get_editor_property('LookDwell'),'visible':[n for n,v in parts.items() if v.is_visible()],
        'view':c.get_view_target().get_class().get_name(),'move_ignored':c.is_move_input_ignored(),
        'look_ignored':c.is_look_input_ignored(),'cinematic':p.get_editor_property('bCinematic'),
        'locked':p.get_editor_property('bInteractionLocked'),'line':str(inter.get_editor_property('FullLine'))}

def aim(w,position,target,fov=None):
    pc(w).set_view_target_with_blend(pawn(w),0)
    S['aim']=(unreal.Vector(*position),unreal.Vector(*target))
    camera=pawn(w).get_component_by_class(unreal.CameraComponent)
    if 'camera_fov' not in S:S['camera_fov']=(camera,camera.get_editor_property('field_of_view'))
    camera.set_field_of_view(S['camera_fov'][1] if fov is None else fov)
    update_aim(w)

def update_aim(w):
    if not S['aim']:return
    position,target=S['aim'];p=pawn(w)
    # The camera manager caches last frame's view; repeatedly correcting against
    # it can accumulate teleports. Use the actual attached component transform.
    camera=p.get_component_by_class(unreal.CameraComponent)
    delta=position-camera.get_world_location()
    if delta.length()>1:p.set_actor_location(p.get_actor_location()+delta,False,True)
    pc(w).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(position,target))

def begin(w):
    # Fixture-only: put the actual wardrobe on its authored fallen pose, without
    # reporting gameplay events or restarting the door transition cinematic.
    wardrobe=director(w).get_editor_property('Wardrobe')
    wardrobe.call_method('ApplyState',('Fallen',True))
    a=room(w);a.call_method('Reset');a.call_method('SetStage',(1,))
    aim(w,(125,-50,170),(290,260,50));log('begin',**snapshot(w))

def clue_view(w,name):
    a=room(w)
    eye=a.get_editor_property('ClueView'+name).get_world_location()
    focus=a.get_editor_property('ClueFocus'+name).get_world_location()
    camera=director(w).get_editor_property('TopDownCamera');assert camera,'Missing authored inspection camera'
    actor=camera.get_owner()
    if 'inspection_camera' not in S:
        S['inspection_camera']=(camera,camera.get_world_transform(),camera.get_editor_property('field_of_view'),[(c,c.is_active()) for c in actor.get_components_by_class(unreal.CameraComponent)])
    S['aim']=None
    for c in actor.get_components_by_class(unreal.CameraComponent):c.set_active(c.get_name()==camera.get_name(),True)
    camera.set_world_location_and_rotation(eye,unreal.MathLibrary.find_look_at_rotation(eye,focus),False,True)
    camera.set_field_of_view(50)
    pc(w).set_view_target_with_blend(actor,0)
    log('inspection_camera',name=name,component=camera.get_path_name(),active=camera.is_active(),
        component_position=list(camera.get_world_location().to_tuple()),find_camera=actor.get_editor_property('bFindCameraComponentWhenViewTarget'))

def clue_shot(w,name):
    unreal.SystemLibrary.execute_console_command(w,f'Shot showui -nosuffix filename="P:/FoA/Saved/WorldShots/clothing_clue_{name}.png"')
    log('clue_'+name,**snapshot(w))

def expect(w,label,predicate):
    state=snapshot(w);log(label,**state);assert predicate(state),f'{label}: {state}'

def headache(w):
    S['headache_max_blink']=0
    S['aim']=None;pc(w).set_view_target_with_blend(pawn(w),0)
    d=director(w);d.call_method('PollStoryMoment');d.call_method('TryStoryMoment')
    assert d.get_editor_property('StoryPlayer'),'Story moment did not cache its actual player'
    # Walking to the painting can naturally trigger Beat2's headache earlier.
    # Finish that owned cycle before testing a fresh cycle's blink peak.
    d.call_method('EndHeadache');d.call_method('StartHeadache');log('headache_started',**snapshot(w))

def stage(w,n):room(w).call_method('SetStage',(n,));log('set_stage',n=n)

def finish(error=None):
    if S['done']:return
    S['done']=True
    unreal.unregister_slate_post_tick_callback(S['handle'])
    if 'camera_fov' in S:
        camera,fov=S['camera_fov'];camera.set_field_of_view(fov)
    if 'inspection_camera' in S:
        camera,transform,fov,active=S['inspection_camera'];camera.set_world_transform(transform,False,True)
        camera.set_field_of_view(fov)
        for c,value in active:c.set_active(value)
    if world() and room(world()):room(world()).call_method('Reset')
    log('complete' if error is None else 'failed',error=error)
    with open(OUT,'w') as f:json.dump(S['log'],f,indent=1)
    unreal.log('Room takeover proof '+('PASS' if error is None else error))

PLAN=[
    (5.0,begin),
    (5.1,lambda w:clue_view(w,'Wardrobe')),
    (5.6,lambda w:clue_shot(w,'wardrobe')),
    (6.0,lambda w:aim(w,(125,-50,170),(290,260,50))),
    (6.5,lambda w:expect(w,'growth_between',lambda s:0<s['progress']<1)),
    (8.6,lambda w:expect(w,'stage1_settled',lambda s:s['progress']==1)),
    (8.7,lambda w:(stage(w,2),clue_view(w,'Desk'))),
    (9.4,lambda w:clue_shot(w,'desk')),
    (10.3,lambda w:expect(w,'scare_visible',lambda s:s['scare_plays']==1 and 'ScareSuit' in s['visible'])),
    (11.3,lambda w:expect(w,'scare_ended',lambda s:'ScareSuit' not in s['visible'])),
    (11.4,lambda w:(stage(w,2),stage(w,1))),
    (12.0,lambda w:aim(w,(-220,208,165.2),(-373.6,208,165.2))),
    (14.2,lambda w:expect(w,'gaze_scene',lambda s:s['painting_seen'] and 'PaintingLeak' in s['visible'] and s['scare_plays']==1 and not s['move_ignored'] and not s['look_ignored'])),
    (17.5,lambda w:expect(w,'gaze_scene_ended',lambda s:s['painting_seen'] and 'PaintingLeak' not in s['visible'])),
    (17.6,lambda w:(stage(w,3),clue_view(w,'Bed'))),
    (17.9,lambda w:clue_shot(w,'bed')),
    (18.0,headache),
    (19.3,lambda w:expect(w,'headache_blink',lambda s:s['owners']['headache'] and (s['peak_blink_height']==0 if s['reduce_motion']>.5 else s['peak_blink_height']>.25) and s['move_ignored'] and s['look_ignored'])),
    (22.5,lambda w:expect(w,'headache_released',lambda s:not s['owners']['headache'] and s['blink_height']==0 and not s['move_ignored'] and not s['look_ignored'])),
    (21.0,lambda w:expect(w,'stage3_persistent',lambda s:s['stage']==3 and s['progress']==3 and 'WardrobeBank' in s['visible'] and 'DeskBank' in s['visible'] and 'ClueSnaggedShirt' in s['visible'])),
    (21.1,lambda w:stage(w,4)),
    (24.5,lambda w:expect(w,'no_duplicate_stage4_scare',lambda s:s['stage']==4 and s['scare_plays']==1)),
    (24.6,lambda w:stage(w,5)),
    (28.0,lambda w:expect(w,'stage5_persistent',lambda s:s['progress']==5 and 'SouthWallClimb' in s['visible'] and 'ClueSnaggedShirt' not in s['visible'])),
    (28.1,lambda w:(aim(w,(125,-50,170),(290,260,50)),room(w).call_method('Reset'))),
    (28.3,lambda w:expect(w,'reset_cleared',lambda s:s['stage']==0 and s['progress']==0 and not set(s['visible'])-{'VaseIntact'} and not s['painting_seen'])),
    (28.4,lambda w:stage(w,2)),
    (28.7,lambda w:room(w).call_method('Reset')),
    (31.5,lambda w:expect(w,'pending_scare_cancelled',lambda s:s['stage']==0 and s['scare_plays']==0 and not set(s['visible'])-{'VaseIntact'} and not s['painting_seen'])),
]
PLAN.sort(key=lambda item:item[0])

def tick(dt):
    try:
        if S['done']:return
        w=world();assert w,'PIE ended before proof completed'
        if not S['ready']:
            age=time.time()-S['boot_start'];host=fe(w);d=director(w)
            if S['boot_phase']==0 and age>.3:host.call_method('OnSplashFinished');S['boot_phase']=1
            elif S['boot_phase']==1 and age>.9:host.call_method('OnTitleConfirmed');S['boot_phase']=2
            elif S['boot_phase']==2 and age>1.5:host.call_method('WakeUp');S['boot_phase']=3
            if S['boot_phase']>=3:
                story=host.get_editor_property('Story')
                if story and story.is_in_viewport() and not story.get_editor_property('bDone'):story.call_method('Finish')
                seq=d.get_editor_property('SeqPlayer')
                if host.get_editor_property('bInGameplay') and seq and not d.get_editor_property('bWakeDone') and not S['skip_sent']:
                    d.call_method('SkipWakeUp');S['skip_sent']=True
                if S['skip_sent'] and d.get_editor_property('bWakeDone') and d.get_editor_property('BeatIndex')==1:
                    S['ready']=True;S['start']=time.time()-5;log('real_wake_released',**snapshot(w))
            if age>14:finish('Real wake sequence did not release within fixture window')
            return
        t=time.time()-S['start']
        update_aim(w)
        if 'headache_max_blink' in S and t<20:
            hud=fe(w).get_editor_property('HUD')
            height=hud.get_editor_property('Brd_HeadacheTop').get_editor_property('render_transform').scale.y
            S['headache_max_blink']=max(S['headache_max_blink'],height)
        if S['i']<len(PLAN) and t>=PLAN[S['i']][0]:
            PLAN[S['i']][1](w);S['i']+=1
        if t>5 and t>=S['next_sample']:
            log('sample',**snapshot(w));S['next_sample']=t+.5
        if (9<t<17 or 18.2<t<19.4) and t>=S['next_shot']:
            unreal.SystemLibrary.execute_console_command(w,f'Shot showui -nosuffix filename="P:/FoA/Saved/WorldShots/room_takeover_pie_{int(t*10):04d}.png"');S['next_shot']=t+.5
        if S['i']==len(PLAN):finish()
        if t>38:finish('timeout')
    except Exception as ex:finish(str(ex))

S['handle']=unreal.register_slate_post_tick_callback(tick)
