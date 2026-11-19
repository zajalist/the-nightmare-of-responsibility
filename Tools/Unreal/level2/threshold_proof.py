"""Bounded L1→L2 fixture: real frontend boot, T10, then native transition.
Dream walking uses actual W/E at normal speed. The job case fixtures only the
earned dream exit, then uses real input for the drive and job hunt.
"""
import json
import os
from pathlib import Path
import sys
import time
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import threshold_data,importlib
importlib.reload(threshold_data)
sys.path.insert(0,'P:/FoA/Tools/Unreal/flow')
import proof_save
OUT=Path('P:/FoA/Saved/Codex/dream_transition')
OUT.mkdir(parents=True,exist_ok=True)
CASE=os.environ.get('FOA_JOURNEY_CASE','transition')
PAD=CASE=='job_gamepad'
SHIFT_VISUAL=CASE=='job_shift_visual'
HEADLESS=os.environ.get('FOA_PROOF_HEADLESS')=='1'
JOB_CASE=CASE in ('job','job_campaign','job_ending','job_gamepad','job_shift_visual')
REALTIME=os.environ.get('FOA_PROOF_REALTIME')=='1'
CV_FAILURE_RUNS=int(os.environ.get('FOA_CV_FAILURE_RUNS','2'))
CV_MOUSE=os.environ.get('FOA_CV_MOUSE','1')=='1'
assert CV_FAILURE_RUNS in (0,1,2)
BUDGET=threshold_data.proof_budget(CASE,REALTIME)
RESULT=OUT/('proof.json' if CASE=='transition' else 'proof_'+CASE+'.json')
INPUT=OUT/('input_'+CASE+'.json')
INPUT.unlink(missing_ok=True)
UES=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w=UES.get_game_world();assert w
ctx=proof_save.isolate(w)
s=dict(start=time.monotonic(),phase=0,rows=[],seen=set(),done=False,handle=None,next=0,shots=set(),entered={})
if PAD or SHIFT_VISUAL:
    import gamepad_route_proof as controller
    importlib.reload(controller)
    s['pad']=controller.Gamepad(unreal,w)

def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w,unreal.load_class(None,path+'.'+path.rsplit('/',1)[1]+'_C'))

def publish(path, value):
    pending=path.with_suffix('.pending')
    pending.write_text(json.dumps(value,indent=1,default=str))
    pending.replace(path)

def request_input(args):
    s['input_id']=s.get('input_id',0)+1
    publish(INPUT,dict(args,id=s['input_id']))

def request_interview_click(index):
    hud=s['journey'].get_editor_property('InterviewHUD')
    assert unreal.SystemLibrary.is_valid(hud) and index in (0,1,2)
    label=str(hud.get_editor_property('Txt_Answer'+str(index)).get_text())
    assert label.strip(),'Click must target a visible authored answer'
    request_input(dict(kind='click',match=label,prefer_type='SButton'))
    s['rows'].append(dict(kind='actual_mouse_choice',index=index,text=label))

def drive_input(key,down):
    assert not s.get('drive_pending'),'Serialize driving input requests'
    request_input(dict(key=key,event='pressed' if down else 'released'))
    s['drive_pending']=(key,down,time.monotonic())


def job_key(key,elapsed):
    if PAD or SHIFT_VISUAL:
        enter=controller.PARK if s['phase']==7 or s.get('job_state')=='closing_cv' else controller.ACCEPT
        key={'Enter':enter,'Up':'Gamepad_DPad_Up','Down':'Gamepad_DPad_Down',
             'C':controller.CV,'E':controller.CANCEL}.get(key,key)
        assert key.startswith('Gamepad_')
        s['pad'].set(key,1)
        s['pad_release']=(key,elapsed+.13)
    else:request_input(dict(key=key,event='pressed_and_released',held_ms=90))
    s['rows'].append(dict(kind='job_input',key=key,t=round(elapsed,2)))
    s['next']=max(s['next'],elapsed+(.42 if PAD or SHIFT_VISUAL else 1.15))


def job_shot(name,pc):
    if HEADLESS:
        s['rows'].append(dict(kind='ui_state_checked',name=name,t=round(time.monotonic()-s['start'],2)))
        return
    prefix='minigame' if SHIFT_VISUAL else 'gamepad' if PAD else 'job'
    path=OUT/f'{prefix}_{name}.png'
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+path.as_posix()+' -nosuffix',pc)
    s['rows'].append(dict(kind='job_capture',name=name,path=str(path)))

def audio_snapshot():
    room=actor('/Game/FoA/Audio/BP_RoomAudio')
    if not unreal.SystemLibrary.is_valid(room):return {'missing':True}
    result={}
    try:
        result['state']=str(room.get_editor_property('MusicState'))
        result['tracks']={str(key):sound.get_path_name() if sound else None
            for key,sound in room.get_editor_property('Tracks').items() if str(key) in ('Dream','City')}
        for name in ('Music','Music2'):
            component=room.get_editor_property(name)
            if not unreal.SystemLibrary.is_valid(component):
                result[name]={'missing':True};continue
            sound=component.get_editor_property('Sound')
            result[name]={'sound':sound.get_path_name() if sound else None,'playing':component.is_playing()}
    except Exception as exc:result['error']=repr(exc)
    return result

def capture_stop_hold(stops,pc,elapsed):
    """Let Slate paint before Shot, then keep input idle while it is saved."""
    if stops.state not in ('action_hold','revision_hold'):return False
    name=f"stop_{s['journey'].get_editor_property('Stop')}_{stops.state}"
    if name in s['shots']:return False
    if s.get('stop_capture_pending')!=name:
        s['stop_capture_pending']=name
        s['next']=elapsed+.3
        return True
    stage=s['journey'].get_editor_property('StopSet')
    assert unreal.SystemLibrary.is_valid(stage) and pc.get_view_target()==stage,'Stop capture has wrong view target'
    path=OUT/(name+'.png')
    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(path).replace('\\','/')+' -nosuffix',pc)
    s['rows'].append(dict(kind='stop_capture',path=str(path),state=stops.state,
        snapshot=stops.snapshot(),view_target=stage.get_path_name()))
    s['shots'].add(name)
    s['stop_capture_pending']=None
    stops.after=max(stops.after,time.monotonic()+.4)
    s['next']=elapsed+.4
    return True


def finish(reason,error=None):
    if s['done']:return
    s['done']=True
    close_errors=[]
    try:unreal.unregister_slate_post_tick_callback(s['handle'])
    except Exception as exc:close_errors.append(dict(proof='callback',error=repr(exc)))
    for name in ('cv','debug','stops','phone','paper','walk','pad'):
        try:
            if s.get(name):s[name].close()
        except Exception as exc:close_errors.append(dict(proof=name,error=repr(exc)))
    if close_errors:reason,error='close_error',dict(original_reason=reason,errors=close_errors)
    try:
        if UES.get_game_world()==w and unreal.SystemLibrary.is_valid(w):
            unreal.GameplayStatics.set_global_time_dilation(w,1)
            proof_save.restore(w,ctx)
    except Exception as exc:
        reason,error='restore_error',repr(exc)
    publish(RESULT,dict(reason=reason,error=error,case=CASE,rows=s['rows'],seen=sorted(s['seen'])))
    print('THRESHOLD_PROOF',reason,error)

def tick(dt):
    try:
        if s['done']:return
        if UES.get_game_world()!=w or not unreal.SystemLibrary.is_valid(w):return finish('world_changed')
        elapsed=time.monotonic()-s['start']
        if (PAD or SHIFT_VISUAL) and s.get('pad_release') and elapsed>=s['pad_release'][1]:
            s['pad'].release_key(s.pop('pad_release')[0])
            s['next']=max(s['next'],elapsed+.10)
            return
        if s.get('logged_phase')!=s['phase']:
            s['logged_phase']=s['phase']
            publish(OUT/('progress_'+CASE+'.json'),dict(phase=s['phase'],elapsed=elapsed,done=s['done']))
        if elapsed>BUDGET:return finish('timeout')
        d=actor('/Game/FoA/Gameplay/BP_BeatDirector');fe=actor('/Game/FoA/UI/Framework/BP_FoAFrontEnd')
        p=actor('/Game/FoA/Characters/Player/BP_FoAPlayer');pc=unreal.GameplayStatics.get_player_controller(w,0)
        missing=[name for name,obj in (('director',d),('frontend',fe),('pawn',p),('controller',pc))
                 if not unreal.SystemLibrary.is_valid(obj)]
        if missing:
            if s['phase']==0 and elapsed>8:return finish('missing_boot_actors',missing)
            return
        if elapsed<s['next']:return
        if s['phase'] in (7,9) or (s['phase']==8 and CASE!='cleanup'):
            if not all(unreal.SystemLibrary.is_valid(s[k]) for k in ('journey','th')):
                return finish('case_actor_destroyed')
        if JOB_CASE and s['phase']==0:
            unreal.GameplayStatics.set_game_paused(w,False)
            library=unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary'))
            for widget in library.call_method('GetAllWidgetsOfClass',(w,unreal.UserWidget,True)):
                widget.remove_from_parent()
            library.call_method('SetInputMode_GameOnly',(pc,True))
            pc.set_editor_property('show_mouse_cursor',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
            d.call_method('OpenTheDoor')
            th=actor('/Game/FoA/Level2/Transition/BP_DreamThreshold');assert th,'Native threshold was not spawned'
            th.call_method('StartThreshold')
            s.update(phase=6,next=elapsed+.3)
            s['rows'].append(dict(kind='bedroom_boot_fixture',earned=False,t=round(elapsed,2)));return
        if s['phase']==0:fe.call_method('OnSplashFinished');s.update(phase=1,next=elapsed+.2)
        elif s['phase']==1:fe.call_method('OnTitleConfirmed');s.update(phase=2,next=elapsed+.2)
        elif s['phase']==2:fe.call_method('WakeUp');s['phase']=3
        elif s['phase']==3:
            story=fe.get_editor_property('Story')
            if story and story.is_in_viewport():story.call_method('Finish')
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp');s['phase']=4
        elif s['phase']==4 and d.get_editor_property('bWakeDone') and not p.get_editor_property('bCinematic'):
            fe.call_method('ClosePhone')
            s['walk_speed']=p.get_editor_property('character_movement').get_editor_property('max_walk_speed')
            p.call_method('Equip',('Suit',))
            p.call_method('SetBootsWorn',(True,))
            if CASE=='cinematic_reduced':
                unreal.MaterialLibrary.set_scalar_parameter_value(w,unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream'),'ReduceMotion',1)
            d.call_method('EnterBeat',(10,))
            p.teleport(unreal.Vector(240,87.5,92),unreal.Rotator(0,0,0))
            s.update(phase=5,next=elapsed+1)
        elif s['phase']==5:
            s['phase']=6
        elif s['phase']==6:
            th=actor('/Game/FoA/Level2/Transition/BP_DreamThreshold')
            if not th:
                if s['seen']:return finish('transition_despawned')
                return
            if JOB_CASE and unreal.GameplayStatics.is_game_paused(w):
                unreal.GameplayStatics.set_game_paused(w,False)
                s['rows'].append(dict(kind='deferred_menu_unpaused',t=round(elapsed,2)))
            phase=th.get_editor_property('Phase');s['seen'].add(phase)
            if PAD and elapsed>=s.get('pad_report_at',0):
                publish(OUT/('progress_'+CASE+'.json'),dict(phase=6,dream_phase=phase,age=th.get_editor_property('Age'),elapsed=elapsed))
                s['pad_report_at']=elapsed+2
            s['entered'].setdefault(phase,elapsed)
            if phase==0 and not s.get('closed_fixture_phone'):
                phone=th.get_editor_property('Phone')
                if unreal.SystemLibrary.is_valid(phone) and phone.get_editor_property('bOpen'):
                    fe.call_method('ClosePhone')
                    s['closed_fixture_phone']=True
            if phase==0 and elapsed-s['entered'][phase]>6:
                door=d.get_editor_property('DoorFrame')
                phone=th.get_editor_property('Phone')
                return finish('threshold_not_started',dict(beat=d.get_editor_property('BeatIndex'),
                    ready_age=th.get_editor_property('ReadyAge'),gameplay=fe.get_editor_property('bInGameplay'),
                    door=door.get_actor_location().to_tuple() if unreal.SystemLibrary.is_valid(door) else None,
                    pawn=p.get_actor_location().to_tuple(),cinematic=p.get_editor_property('bCinematic'),
                    phone_open=phone.get_editor_property('bOpen') if unreal.SystemLibrary.is_valid(phone) else None))
            walk_pending=s.get('walk') and not s['walk'].done
            fast=(not REALTIME and CASE not in ('transition','cinematic','cinematic_reduced')
                  and phase<6 and phase!=3 and not walk_pending)
            unreal.GameplayStatics.set_global_time_dilation(w,3 if fast else 1)
            if CASE=='early_cleanup' and phase==1 and th.get_editor_property('Age')>1:
                th.call_method('Abort');s.update(phase=15,next=elapsed+.5);return
            if CASE=='animation_probe' and phase==1 and th.get_editor_property('Age')>2:
                sequences=[]
                for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.LevelSequenceActor):
                    sp=a.get_editor_property('SequencePlayer');seq=a.get_sequence()
                    sequences.append(dict(actor=a.get_name(),sequence=str(seq),playing=sp.is_playing() if sp else None))
                source=p.get_editor_property('mesh')
                s['rows'].append(dict(sequences=sequences,mode=str(source.get_editor_property('animation_mode')),
                    animation=str(source.get_editor_property('animation_data'))))
                return finish('animation_probe')
            if JOB_CASE and not PAD and phase==3 and not s.get('job_fixture'):
                if th.get_editor_property('Age')<threshold_data.PATH_MIN+1:return
                # Start the approved job proof at the city, independent of the long walk smoke test.
                set_int=unreal.get_default_object(unreal.SystemLibrary)
                set_int.call_method('SetIntPropertyByName',(th,'RouteBeat',2))
                th.call_method('HidePath')
                p.set_actor_location(unreal.Vector(*threshold_data.EXIT),False,True)
                th.call_method('BeginFall')
                assert th.get_editor_property('Phase')==4,('Could not start city handoff',
                    th.get_editor_property('RouteBeat'),th.get_editor_property('BreathState'),
                    p.get_actor_location().to_tuple(),th.get_editor_property('Age'))
                s['job_fixture']=True;s['rows'].append(dict(kind='dream_exit_fixture',earned=False,t=round(elapsed,2)))
                return
            if phase==3 and not s.get('walk'):
                sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
                import threshold_walk_proof
                importlib.reload(threshold_walk_proof)
                s['walk']=(controller.GamepadWalk(w,th,s['pad'],unreal) if PAD else
                           threshold_walk_proof.create_walk_proof(w,th,request_input,cap_seconds=min(35,BUDGET-2-elapsed)))
            if s.get('walk') and not s.get('walk_recorded'):
                walk=s['walk'];walk.tick(dt)
                # Continue through Phase4 until W release is acknowledged. Nothing
                # else may overwrite the single input mailbox during that handoff.
                if walk.done:
                    s['walk_recorded']=True
                    s['rows'].append(dict(t=round(elapsed,2),phase=phase,kind='walk_result',result=walk.result))
                    if not walk.result['passed']:return finish('walk_failed',walk.result)
                elif not HEADLESS and walk.state in ('preheld','held_full','second_hold') and walk.state not in s['shots']:
                    s['shots'].add(walk.state)
                    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/('walk_'+walk.state+'.png')).replace('\\','/')+' -nosuffix',pc)
            loc=p.get_actor_location();camera=pc.player_camera_manager.get_camera_location()
            row=dict(t=round(elapsed,2),phase=phase,age=th.get_editor_property('Age'),
                position=loc.to_tuple(),camera=camera.to_tuple(),view=pc.get_view_target().get_name(),
                cinematic=p.get_editor_property('bCinematic'),move_ignored=pc.is_move_input_ignored(),fov=pc.player_camera_manager.get_fov_angle(),
                route_beat=th.get_editor_property('RouteBeat'),breath_state=th.get_editor_property('BreathState'))
            if phase in (4,5,6):
                row['pawn_hidden']=p.get_editor_property('hidden')
                assert bool(row['pawn_hidden'])==(phase!=6),('Player body visibility during camera handoff',row)
            if not s['rows'] or elapsed-s['rows'][-1]['t']>.5:
                row['audio']=audio_snapshot();s['rows'].append(row)
                if CASE.startswith('cinematic') and phase==1:
                    row['meshes']=[]
                    for mesh in p.get_components_by_class(unreal.SkeletalMeshComponent):
                        instance=mesh.get_anim_instance()
                        row['meshes'].append(dict(name=mesh.get_name(),asset=str(mesh.get_editor_property('skeletal_mesh_asset')),
                            mode=str(mesh.get_editor_property('animation_mode')),anim=str(instance),
                            leader=str(mesh.get_editor_property('leader_pose_component')),tick=str(mesh.get_editor_property('visibility_based_anim_tick_option')),
                            wrist=mesh.get_socket_location('hand_r').to_tuple(),visible=mesh.is_visible()))
            if not HEADLESS and phase not in s['shots'] and elapsed-s['entered'][phase]>.7:
                s['shots'].add(phase)
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/f'phase{phase}.png').replace('\\','/')+' -nosuffix',pc)
            if CASE.startswith('cinematic'):
                for shot_phase,age in [(1,2.8),(1,4.8),(1,7.5),(1,8.9),(2,1.5),(3,5),(3,15),(3,29),(4,2),(5,6.8)]:
                    name=f'{CASE}_{shot_phase}_{age}'
                    if phase==shot_phase and th.get_editor_property('Age')>=age and name not in s['shots']:
                        s['shots'].add(name)
                        unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/(name+'.png')).replace('\\','/')+' -nosuffix',pc)
            if phase==6 and elapsed-s['entered'][phase]>1:
                assert s.get('job_fixture') or (s.get('walk') and s['walk'].done and s['walk'].result['passed']),'Arrival without earned input proof'
                if CASE in ('job_campaign','job_ending','job_gamepad'):
                    assert th.get_editor_property('L2DreamMotion').get_editor_property('blend_weight')==1
                journey=th.get_editor_property('Journey')
                if not unreal.SystemLibrary.is_valid(journey):return
                row['journey_phase']=journey.get_editor_property('Phase')
                row['audio']=audio_snapshot()
                row['control_back']=not row['cinematic'] and not row['move_ignored'] and pc.get_view_target()==p
                s['rows'].append(row)
                if not row['control_back']:return finish('arrival_control_failed')
                if CASE.startswith('cinematic'):
                    wrists=[m['wrist'][0]-r['position'][0] for r in s['rows'] if r.get('phase')==1 and .5<r['age']<2.8
                            for m in r.get('meshes',[]) if m['name']=='CharacterMesh0']
                    assert len(wrists)>=3 and max(wrists)-min(wrists)>2,('Frozen cinematic animation',wrists)
                    views=[r for r in s['rows'] if r.get('phase')==1 and .5<r['age']<8]
                    lens=[r['fov'] for r in views]
                    if CASE=='cinematic_reduced':
                        assert max(lens)-min(lens)<.1,('Reduced-motion lens moved',lens)
                        assert all(sum((a-b)**2 for a,b in zip(r['camera'],views[0]['camera']))<.1 for r in views),'Reduced-motion camera moved'
                    else:assert max(lens)-min(lens)>20,('Dolly lens did not animate',lens)
                if CASE in ('transition','cinematic','cinematic_reduced'):return finish('arrived')
                s.update(phase=7,journey=journey,th=th,case_started=elapsed,initial_day=unreal.GameplayStatics.get_game_instance(w).get_editor_property('DayCount'))
            if phase<0:return finish('transition_aborted')
        elif s['phase']==7:
            journey=s['journey'];th=s['th']
            if JOB_CASE:
                assert journey.get_editor_property('Phase')==1
                library=unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary'))
                for prop in ('SplashClass','TitleClass','MainMenuClass'):
                    widget_class=fe.get_editor_property(prop)
                    if widget_class:
                        for widget in library.call_method('GetAllWidgetsOfClass',(w,widget_class,True)):
                            widget.remove_from_parent()
                library.call_method('SetInputMode_GameOnly',(pc,True))
                pc.set_editor_property('show_mouse_cursor',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                if not unreal.SystemLibrary.is_valid(fe.get_editor_property('HUD')):
                    fe.call_method('EnterGameplay')
                    fe.get_editor_property('HUD').remove_from_parent()
                if CASE=='job_ending':
                    merge=journey.get_editor_property('Merge')
                    merge.call_method('SetVisible',(True,));journey.call_method('ApplyMerge',(1.,))
                    assert not merge.get_editor_property('hidden')
                    journey.get_editor_property('HUD').remove_from_parent()
                    s['rows'].append(dict(kind='post_interview_fixture',t=round(elapsed,2)))
                    th.call_method('BeginEnding');s.update(phase=26,next=elapsed+.4);return
                if SHIFT_VISUAL:
                    journey.call_method('Confirm')
                    journey.call_method('Confirm')
                    s.update(phase=28,job_index=0,next=elapsed+.75)
                    return
                job_key('Enter',elapsed);s.update(phase=24,job_state='opening_cv');return
            if CASE=='streaming':
                import city_streaming_proof
                importlib.reload(city_streaming_proof)
                journey.call_method('Confirm');journey.call_method('Confirm')
                unreal.GameplayStatics.set_global_time_dilation(w,1)
                s.update(streaming=city_streaming_proof.CityStreamingProof(w,journey,request_input),phase=21)
                return
            if CASE=='shockwave':
                import shockwave_proof
                importlib.reload(shockwave_proof)
                journey.call_method('Confirm');journey.call_method('Confirm')
                unreal.GameplayStatics.set_global_time_dilation(w,1)
                s.update(shockwave=shockwave_proof.ShockwaveProof(w,journey),phase=20)
                return
            if CASE=='paper':
                import cv_paper_proof
                importlib.reload(cv_paper_proof)
                s.update(paper=cv_paper_proof.PaperProof(w,journey,request_input,
                    cap_seconds=min(20,BUDGET-2-elapsed)),phase=19)
                return
            if CASE=='debug':
                sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
                import journey_debug_proof
                importlib.reload(journey_debug_proof)
                s.update(debug=journey_debug_proof.create_journey_debug_proof(w,journey,request_input),phase=14)
                return
            if CASE in ('stops','cv','ending','reset','phone'):
                sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
                import journey_stop_proof
                importlib.reload(journey_stop_proof)
                s.update(stops=journey_stop_proof.create_stop_proof(w,journey,
                    request_input=request_input if CASE=='stops' else None,
                    through_stop=0 if CASE in ('reset','phone') else 2,finish_in_car=CASE=='reset',
                    cap_seconds=min(36 if CASE in ('stops','ending') else 26,BUDGET-2-elapsed)),phase=16)
                if CASE=='cv':unreal.GameplayStatics.set_global_time_dilation(w,3)
                return
            if CASE=='cleanup':
                journey.call_method('Confirm');journey.call_method('Confirm')
                assert unreal.GameplayStatics.get_player_pawn(w,0)!=p
                fe.call_method('ReturnToTitle');s.update(phase=8,next=elapsed+1,cleanup_started=elapsed)
            elif CASE=='drive':
                journey.call_method('Confirm');journey.call_method('Confirm')
                s['drive_mode']='cruise';drive_input('W',True)
                s.update(phase=8,next=elapsed+.3)
        elif s['phase']==8:
            if CASE=='cleanup':
                sectors=unreal.load_class(None,'/Game/FoA/Level2/City/Expanded/BP_City2Sector.BP_City2Sector_C')
                visible_city=[a.get_actor_label() for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.StaticMeshActor)
                              if a.get_actor_label().startswith('CityDense_')]
                if unreal.GameplayStatics.get_all_actors_of_class(w,sectors) or visible_city:
                    assert elapsed-s['cleanup_started']<8,('Streamed city remained after leaving Level 2',visible_city[:6])
                    s['next']=elapsed+.2;return
                assert actor('/Game/FoA/Level2/Transition/BP_DreamThreshold') is None
                assert actor('/Game/FoA/Level2/Journey/BP_L2Journey') is None
                assert actor('/Game/FoA/Level2/Drive/BP_L2Car') is None
                assert unreal.GameplayStatics.get_player_pawn(w,0)==p
                assert not fe.get_editor_property('bInGameplay')
                return finish('cleanup_passed')
            journey=s['journey'];car=journey.get_editor_property('Car')
            if not unreal.SystemLibrary.is_valid(car):return finish('car_destroyed')
            if PAD:
                index=s.get('job_index',0);get=journey.get_editor_property
                if elapsed>=s.get('pad_report_at',0):
                    publish(OUT/('progress_'+CASE+'.json'),dict(phase=8,elapsed=elapsed,job=index,
                        waypoint=s['drive'].point,position=car.get_actor_location().to_tuple(),speed=car.get_editor_property('Speed')))
                    s['pad_report_at']=elapsed+2
                if s.get('pad_park') is not None:
                    if get('Phase')==4 and not get('StopBusy') and get('DialogueMode')==4:
                        s.update(phase=24,job_state='working',pad_park=None,next=elapsed+.5)
                    elif index==3 and get('Phase')==6:
                        s.update(phase=25,pad_park=None,next=elapsed+.5)
                    else:assert elapsed-s['pad_park']<10,('Y did not park',index,get('Phase'))
                    return
                if s['drive'].tick(elapsed):
                    road=car.get_editor_property('Road');label=road.get_editor_property(f'JobBoardText{index}')
                    assert label.is_visible() and ('INTERVIEW' if index==3 else 'HIRING') in str(label.get_editor_property('text'))
                    job_shot(f'gamepad_sign_{index}',pc)
                    job_key(controller.PARK,elapsed);s['pad_park']=elapsed
                return
            if CASE=='reset':
                if journey.get_editor_property('Phase')==1:
                    assert journey.get_editor_property('Employability')==0
                    assert journey.get_editor_property('RoadAttempts')==1
                    assert unreal.GameplayStatics.get_game_instance(w).get_editor_property('DayCount')==s['initial_day']
                    assert unreal.GameplayStatics.get_player_pawn(w,0)==p
                    return finish('road_reset_passed')
            if CASE=='drive' or JOB_CASE:
                meteor=car.get_editor_property('Meteor')
                if not unreal.SystemLibrary.is_valid(meteor):return finish('meteor_destroyed')
                if s.get('drive_pending'):
                    key,down,sent=s['drive_pending'];native_key=unreal.Key();native_key.set_editor_property('key_name',key)
                    if pc.is_input_key_down(native_key)!=down:
                        assert time.monotonic()-sent<4,('Driving input not acknowledged',key,down)
                        return
                    s['rows'].append(dict(kind='drive_input_ack',key=key,down=down,t=round(elapsed,2)))
                    s['drive_pending']=None
                distance=(car.get_actor_location()-car.get_editor_property('Destination')).length()
                speed=float(car.get_editor_property('Speed'))
                if elapsed-s['case_started']>4 and not s.get('drive_shot'):
                    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'driving.png').replace('\\','/')+' -nosuffix',pc)
                    s['drive_shot']=True
                mode=s['drive_mode']
                if mode=='brace_release':
                    drive_input('SpaceBar',False);s['drive_mode']='cruise';return
                if mode=='cruise' and distance<=1000:
                    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'driving_approaching.png').replace('\\','/')+' -nosuffix',pc)
                    drive_input('W',False);s['drive_mode']='brake_start';return
                if mode=='brake_start':
                    drive_input('S',True);s['drive_mode']='braking';return
                if mode=='braking' and speed<100:
                    drive_input('S',False);s['drive_mode']='parking_wait';return
                if mode=='parking_wait' and car.get_editor_property('NearDestination'):
                    if not s.get('parking_shot'):
                        if JOB_CASE:
                            road=car.get_editor_property('Road')
                            labels={component.get_name():component for component in road.get_components_by_class(unreal.TextRenderComponent)}
                            label=labels.get('JobBoardText0') or road.get_editor_property('DestinationLabel')
                            assert label.is_visible() and 'HIRING' in str(label.get_editor_property('text'))
                            job_shot('01_hiring',pc)
                        else:unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'driving_parking_ready.png').replace('\\','/')+' -nosuffix',pc)
                        s.update(parking_shot=True,next=elapsed+.3);return
                    request_input(dict(key='Enter',event='pressed_and_released',held_ms=90))
                    s.update(drive_mode='park_requested',drive_park_at=elapsed)
                    s['rows'].append(dict(kind='actual_parking_requested',distance=distance,speed=speed));return
                if mode=='park_requested' and journey.get_editor_property('Phase')==3:
                    assert elapsed-s['drive_park_at']<4,'Actual Enter did not park';return
                if mode=='cruise' and meteor.get_editor_property('Active') and 2.1<meteor.get_editor_property('Age')<2.4 and not s.get('braced'):
                    s['braced']=True;drive_input('SpaceBar',True);s['drive_mode']='brace_release';return
                if journey.get_editor_property('Phase')==4 and not journey.get_editor_property('StopBusy'):
                    assert s.get('drive_park_at') is not None,'Arrival was not earned through actual Enter'
                    assert car.get_editor_property('HitsResolved')>=1,'No road hazard resolved'
                    assert not car.get_editor_property('Active') and not meteor.get_editor_property('Active'),'Staged arrival retained road activity'
                    if JOB_CASE:
                        assert journey.get_editor_property('DialogueMode')==4,'Employer conversation did not open'
                        s.update(phase=24,job_state='working',next=elapsed+.55);return
                    assert journey.get_editor_property('DialogueMode')==1,'New contact dialogue did not open'
                    s['rows'].append(dict(kind='drive_arrival',composure=car.get_editor_property('Composure'),outcome=str(car.get_editor_property('LastOutcome')),audio=audio_snapshot()))
                    return finish('drive_passed')
        elif s['phase']==28:
            from job_route import DESTINATIONS
            journey=s['journey'];car=journey.get_editor_property('Car')
            assert journey.get_editor_property('Phase')==3 and car.get_editor_property('Active')
            index=s['job_index']
            car.teleport(unreal.Vector(*DESTINATIONS[index]),unreal.Rotator())
            car.call_method('CheckDestination')
            assert car.get_editor_property('NearDestination') and car.get_editor_property('ArrivalJob')==index
            car.call_method('Continue')
            s['rows'].append(dict(kind='visual_job_parking_fixture',job=index))
            s.update(phase=24,job_state='working',job_time_card=False,job_dialogue_shot=False,
                     job_shift_shot=False,next=elapsed+.8)
        elif s['phase']==24:
            import job_hunt_data as jobs
            if not s.get('job_data_loaded'):
                importlib.reload(jobs)
                s['job_data_loaded']=True
            journey=s['journey'];phase=journey.get_editor_property('Phase');get=journey.get_editor_property
            paused=unreal.GameplayStatics.is_game_paused(w);paper=get('CVPaper');state=s['job_state']
            index=s.get('job_index',0);job=jobs.JOBS[index]
            captures=('job','dispatch','northline')[index]
            if PAD:
                marker=(index,state,phase,get('DialogueMode'),get('JobBeat'),get('JobOrder'),get('DialogueSelected'))
                if marker!=s.get('pad_flow'):
                    s['pad_flow'],s['pad_flow_at']=marker,elapsed
                    s['rows'].append(dict(kind='gamepad_ui',state=marker,t=round(elapsed,2)))
                    publish(OUT/('progress_'+CASE+'.json'),dict(phase=24,elapsed=elapsed,state=marker))
                changed_at=s.setdefault('pad_flow_at',elapsed)
                if elapsed-changed_at>8:return finish('gamepad_ui_stalled',dict(state=marker,
                    paused=paused,ready=get('DialogueReady'),held=get('DialogueHeld')))
            if state=='opening_cv':
                if paused and unreal.SystemLibrary.is_valid(paper):
                    assert paper.get_editor_property('ItemMesh').get_editor_property('static_mesh').get_name()=='SM_L2CVPaper'
                    if not HEADLESS:
                        if elapsed-s.setdefault('cv_intro_visible',elapsed)<.7:return
                        job_shot('initial_cv',pc)
                    if PAD:
                        mpc=unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
                        values={name:str(unreal.MaterialLibrary.get_vector_parameter_value(w,mpc,name))
                                for name in ('LensLook','FilmLook','RetroMix')}
                        assert s['th'].get_editor_property('L2DreamMotion').get_editor_property('blend_weight')==1
                        s['rows'].append(dict(kind='cv_look',values=values))
                    job_key('E',elapsed);s['job_state']='closing_cv'
            elif state=='closing_cv':
                if not paused and paper is None and phase==2:
                    job_key('Enter',elapsed);s['job_state']='getting_in'
            elif state=='getting_in':
                if phase==3 and get('Car').get_editor_property('Active'):
                    s.update(phase=8,drive_mode='cruise',case_started=elapsed)
                    if PAD:s['drive']=controller.Drive(get('Car'),s['pad'],0,elapsed,s['rows'])
                    else:drive_input('W',True)
            elif state=='working':
                mode=get('DialogueMode');beat=get('JobBeat');order=get('JobOrder')
                if mode==jobs.TIME_SKIP:
                    if not s.get('job_time_card'):
                        assert get('JobTimeCard').is_in_viewport() and not get('InterviewHUD').is_in_viewport()
                        job_shot('03_time_skip' if index==0 else captures+'_time_skip',pc);s['job_time_card']=True
                    return
                if not get('DialogueReady'):return
                hud=get('InterviewHUD');assert hud.is_in_viewport()
                if mode==jobs.PITCH:
                    if not s.get('job_dialogue_shot'):
                        assert str(hud.get_editor_property('Txt_Speaker').get_text())==job.employer
                        job_shot('02_employer' if index==0 else captures+'_employer',pc);s['job_dialogue_shot']=True
                    desired=job.pitch[beat].points.index(2) if beat<2 else 0
                    if beat==2:assert get('JobTrust')>=jobs.HIRE_SCORE
                elif mode==jobs.SHIFT:
                    assert s.get('job_time_card'),'Shift started without a visible time skip'
                    if not s.get('job_shift_shot'):
                        from shift_minigame_data import TITLES
                        actual=str(hud.get_editor_property('Txt_Speaker').get_text())
                        assert actual==TITLES[index],(actual,TITLES[index])
                        if not HEADLESS:
                            age=unreal.GameplayStatics.get_time_seconds(w)-get('ShiftStarted')
                            if age<(.8 if index==1 else .35):return
                        job_shot('04_shift' if index==0 else captures+'_shift',pc);s['job_shift_shot']=True
                    from shift_minigame_data import RECIPES, PACKED, BAYS, LEDGER, PERIOD, WINDOW_START, WINDOW_END
                    if index==0:
                        desired=next(i for i,count in enumerate(RECIPES[order]) if get(PACKED[i])<count)
                    elif index==1:
                        desired=BAYS[order]
                        if get('DialogueSelected')==desired:
                            age=unreal.GameplayStatics.get_time_seconds(w)-get('ShiftStarted')
                            beat_position=(age/PERIOD)%1
                            if not WINDOW_START+.035<=beat_position<=WINDOW_END-.09:return
                    else:
                        count=get('LedgerCount');target=LEDGER[order][1]
                        desired=0 if count>target else 1 if count<target else 2
                elif mode==jobs.RESULT:
                    mask=s.get('job_mask',0)|(1<<index);s['job_mask']=mask
                    assert get('JobWon') and get(f'Edited{index}') and get('Employability')==jobs.CV_PER_JOB*mask.bit_count()
                    job_shot('05_result' if index==0 else captures+'_result',pc);s['job_state']='earned_cv';job_key('C',elapsed);return
                else:raise AssertionError(('Unexpected job mode',mode))
                selected=get('DialogueSelected')
                job_key('Down' if selected<desired else 'Up' if selected>desired else 'Enter',elapsed)
            elif state=='earned_cv':
                if paused and unreal.SystemLibrary.is_valid(paper):
                    if elapsed-s.setdefault('cv_visible',elapsed)<.7:return
                    s.pop('cv_visible')
                    mesh=paper.get_editor_property('ItemMesh').get_editor_property('static_mesh')
                    assert mesh.get_name()==f'SM_JobRecord{s["job_mask"]}',mesh.get_name()
                    job_shot('06_cv' if index==0 else captures+'_cv',pc);job_key('E',elapsed);s['job_state']='put_away'
            elif state=='put_away':
                if not paused and paper is None:
                    assert get('InterviewHUD').get_render_opacity()==1 and get('JobWon')
                    job_key('Enter',elapsed);s['job_state']='back_in_car'
            elif state=='back_in_car' and phase==3 and get('Car').get_editor_property('Active'):
                if SHIFT_VISUAL:
                    if index==2:return finish('job_shift_visual_passed')
                    s.update(phase=28,job_index=index+1,next=elapsed+.6)
                    return
                if CASE=='job':
                    assert get('Employability')==jobs.CV_PER_JOB
                    return finish('job_passed')
                import job_route
                car=get('Car');road=car.get_editor_property('Road')
                if PAD:
                    assert road.get_editor_property('JobBoardText3').is_visible()==(index>=1)
                    s.update(phase=8,job_index=index+1,drive=controller.Drive(car,s['pad'],index+1,elapsed,s['rows']),
                             job_time_card=False,job_dialogue_shot=False,job_shift_shot=False)
                    return
                target={0:2,2:1,1:job_route.BOSS}[index]
                assert road.get_editor_property('JobBoardText3').is_visible()==(index!=0)
                yaw=-90 if target==2 else 0
                car.teleport(unreal.Vector(*job_route.DESTINATIONS[target]),unreal.Rotator(0,yaw,0))
                car.call_method('CheckDestination')
                assert car.get_editor_property('NearDestination') and car.get_editor_property('ArrivalJob')==target
                s['rows'].append(dict(kind='travel_position_fixture',job=target,t=round(elapsed,2)))
                job_key('Enter',elapsed)
                if target!=job_route.BOSS:
                    s.update(job_state='working',job_index=target,job_time_card=False,job_dialogue_shot=False,job_shift_shot=False)
                else:s.update(phase=25,boss_started=elapsed)
        elif s['phase']==25:
            import job_boss_data as boss
            journey=s['journey'];get=journey.get_editor_property
            if get('Phase')==9:
                s.update(phase=26,next=elapsed+.55);return
            if get('DialogueMode')!=3 or not get('DialogueReady') or get('StopBusy'):return
            if not s.get('boss_shot'):
                assert get('InterviewComposure')==boss.STARTING_COMPOSURE
                job_shot('boss',pc);s['boss_shot']=True
            dialogue_state=get('DialogueState')
            if dialogue_state in (1,3):
                if dialogue_state==3:assert get('FinaleComplete') and get('Employability')==100
                job_key('Enter',elapsed);return
            assert dialogue_state==0,'Boss failed on best-evidence path'
            step=get('DialogueStep');section=boss.SECTIONS[step//2]
            row=section if step%2==0 else section['followups'][get('DialoguePrior')]
            choice=min(range(3),key=lambda i:row['choices'][i]['cost']);selected=get('DialogueSelected')
            job_key('Down' if selected<choice else 'Up' if selected>choice else 'Enter',elapsed)
        elif s['phase']==26:
            th=s['th']
            if unreal.SystemLibrary.is_valid(th) and th.get_editor_property('WakeActive'):
                grade=th.get_editor_property('WakeGrade')
                assert unreal.SystemLibrary.is_valid(grade) and not grade.get_editor_property('enabled')
                sand=th.get_editor_property('WakeSandTargets')
                assert sand and all(actor.get_editor_property('hidden') for actor in sand)
                assert p.get_editor_property('hidden') and s['journey'].get_editor_property('Merge').get_editor_property('hidden')
                assert th.get_editor_property('L2DreamMotion').get_editor_property('blend_weight')==0
                credits=th.get_editor_property('WakeCredits')
                if not s.get('wake_shot'):
                    if not s.get('wake_wait'):s['wake_wait']=True;s['next']=elapsed+2.45;return
                    job_shot('real_wake',pc);s['wake_shot']=True
                if unreal.SystemLibrary.is_valid(credits) and credits.is_in_viewport():
                    if not s.get('credits_started'):s['credits_started']=elapsed
                    if elapsed-s['credits_started']>4:
                        assert credits.get_editor_property('CreditNames').get_editor_property('render_transform').translation.y<0
                        job_shot('rolling_credits',pc);s.update(phase=27,credits=credits,next=elapsed+.5)
        elif s['phase']==27:
            credits=s['credits']
            if (not unreal.SystemLibrary.is_valid(credits) or not credits.is_in_viewport()) and not actor('/Game/FoA/Level2/Transition/BP_DreamThreshold'):
                assert not fe.get_editor_property('bInGameplay'),'Credits did not return to title'
                return finish({'job_ending':'job_ending_passed','job_gamepad':'job_gamepad_passed'}.get(CASE,'job_campaign_passed'))
        elif s['phase']==9:
            journey=s['journey']
            assert journey.get_editor_property('Phase')==11
            assert journey.get_editor_property('Employability')==60
            if not s.get('stops_shot'):
                shot=OUT/'stops60.png'
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(shot).replace('\\','/')+' -nosuffix',pc)
                s['rows'].append(dict(kind='stops_60_capture',path=str(shot),employability=60,audio=audio_snapshot()))
                s.update(stops_shot=True,next=elapsed+.3)
            else:return finish('stops_passed')
        elif s['phase']==10:
            cv=s['cv']
            if s.get('review_interview') in ('opening','closing'):
                assert elapsed-s['review_interview_at']<5,'Interview C.V. did not open or close'
                journey=s['journey'];paper=journey.get_editor_property('CVPaper')
                hud=journey.get_editor_property('InterviewHUD')
                assert journey.get_editor_property('Phase')==6
                paused=unreal.GameplayStatics.is_game_paused(w)
                if s['review_interview']=='opening' and paused and unreal.SystemLibrary.is_valid(paper):
                    mesh=paper.get_editor_property('ItemMesh').get_editor_property('static_mesh')
                    assert mesh.get_name()=='SM_CVRevision3' and hud.get_render_opacity()==0
                    s['rows'].append(dict(kind='actual_interview_cv_open',revision=mesh.get_path_name()))
                    unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'paper_revision3_in_interview.png').replace('\\','/')+' -nosuffix',pc)
                    request_input(dict(key='E',event='pressed_and_released',held_ms=100))
                    s.update(review_interview='closing',next=elapsed+.65)
                elif s['review_interview']=='closing' and not paused and paper is None:
                    assert hud.get_render_opacity()==1
                    s.update(review_interview='done')
                return
            tag=cv.capture_tag
            if tag and tag not in s['shots'] and time.monotonic()>=cv.after-.15:
                s['shots'].add(tag)
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/('interview_'+tag+'.png')).replace('\\','/')+' -nosuffix',pc)
                if tag=='question_0_0' and 'review_interview' not in s:
                    request_input(dict(key='C',event='pressed_and_released',held_ms=100))
                    s.update(review_interview='opening',review_interview_at=elapsed)
                s['next']=elapsed+.25
                return
            cv.tick(dt)
            if s['cv'].done:
                s['rows'].append(dict(kind='cv_result',result=s['cv'].result))
                if not s['cv'].result['passed']:return finish('cv_failed',s['cv'].result)
                s['cv'].close();return finish('cv_passed')
        elif s['phase']==15:
            assert actor('/Game/FoA/Level2/Transition/BP_DreamThreshold') is None
            assert p.get_editor_property('character_movement').get_editor_property('max_walk_speed')==s['walk_speed']
            assert not p.get_editor_property('bCinematic') and not pc.is_move_input_ignored()
            assert pc.get_view_target()==p and p.get_actor_location().z>70
            return finish('early_cleanup_passed')
        elif s['phase']==16:
            stops=s['stops']
            if capture_stop_hold(stops,pc,elapsed):return
            stops.tick(dt)
            if capture_stop_hold(stops,pc,elapsed):return
            if stops.done:
                s['rows'].append(dict(kind='stop_result',result=stops.result))
                if not stops.result['passed']:return finish('stops_failed',stops.result)
                stops.close();journey=s['journey']
                if CASE=='stops':s.update(phase=9,next=elapsed+.8)
                elif CASE=='reset':
                    os.environ['FOA_JOURNEY_PROOF']='reset'
                    exec(Path('P:/FoA/Tools/Unreal/level2/journey_proof.py').read_text(),{})
                    s.update(phase=8,next=elapsed+.3)
                elif CASE=='cv':
                    unreal.GameplayStatics.set_global_time_dilation(w,1)
                    sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
                    import interview_proof
                    importlib.reload(interview_proof)
                    s.update(cv=interview_proof.create_interview_proof(w,journey,request_input,
                        request_click=request_interview_click if CV_MOUSE else None,failure_runs=CV_FAILURE_RUNS,
                        cap_seconds=min(85,BUDGET-2-elapsed)),phase=10)
                elif CASE=='phone':
                    import phone_progress_proof
                    importlib.reload(phone_progress_proof)
                    s.update(phone=phone_progress_proof.PhoneProof(w,journey,request_input=request_input),phase=17)
                else:
                    journey.call_method('Confirm')
                    s.update(phase=18)
        elif s['phase']==21:
            streaming=s['streaming'];streaming.tick()
            if streaming.done:
                s['rows'].append(dict(kind='streaming_result',result=streaming.result))
                s.update(phase=22,next=elapsed+.3)
        elif s['phase']==22:
            import shockwave_proof
            importlib.reload(shockwave_proof)
            s.update(shockwave=shockwave_proof.ShockwaveProof(w,s['journey']),phase=20)
        elif s['phase']==20:
            wave=s['shockwave'];wave.tick()
            if wave.done:
                s['rows'].append(dict(kind='shockwave_result',result=wave.result))
                return finish('streaming_passed' if CASE=='streaming' else 'shockwave_passed')
        elif s['phase']==19:
            paper=s['paper'];paper.tick(dt)
            if paper.done:
                s['rows'].append(dict(kind='paper_result',result=paper.result))
                if not paper.result['passed']:return finish('paper_failed',paper.result)
                request_input(dict(key='C',event='pressed_and_released',held_ms=100))
                s.update(phase=23,next=elapsed+.75,review_started=elapsed,review_open=False)
        elif s['phase']==23:
            journey=s['journey'];car=journey.get_editor_property('Car')
            assert elapsed-s['review_started']<6,'Driving C.V. shortcut did not open or close'
            assert journey.get_editor_property('Phase')==3 and car.get_editor_property('Active')
            assert unreal.GameplayStatics.get_player_pawn(w,0)==car
            paper=journey.get_editor_property('CVPaper');paused=unreal.GameplayStatics.is_game_paused(w)
            if not s['review_open'] and paused and unreal.SystemLibrary.is_valid(paper):
                assert paper.get_editor_property('bOpen')
                assert paper.get_editor_property('ItemMesh').get_editor_property('static_mesh').get_name()=='SM_L2CVPaper'
                s['rows'].append(dict(kind='actual_driving_cv_open',key='C',paused=paused))
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'paper_while_driving.png').replace('\\','/')+' -nosuffix',pc)
                request_input(dict(key='E',event='pressed_and_released',held_ms=100))
                s.update(review_open=True,next=elapsed+.5)
            elif s['review_open'] and not paused and paper is None:
                s['rows'].append(dict(kind='actual_driving_cv_closed',key='E',paused=paused))
                return finish('paper_passed')
        elif s['phase']==18:
            journey=s['journey']
            if journey.get_editor_property('Phase')==6 and not journey.get_editor_property('StopBusy') and journey.get_editor_property('DialogueReady'):
                # Ending-only outcome fixture; the cv case independently earns all
                # six answers through physical keyboard/controller requests.
                journey.call_method('InterviewWon')
                s['rows'].append(dict(kind='ending_outcome_fixture',method='InterviewWon',actual_interview_proof=False))
                s.update(next=elapsed+.4)
            elif journey.get_editor_property('Phase')==8 and journey.get_editor_property('DialogueReady'):
                journey.call_method('DialogueRelease');journey.call_method('Confirm');s.update(phase=12)
        elif s['phase']==17:
            phone=s['phone'];phone.tick(dt)
            if phone.state not in s['shots'] and time.monotonic()>=phone.next-.15:
                s['shots'].add(phone.state)
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/('phone_'+phone.state+'.png')).replace('\\','/')+' -nosuffix',pc)
            if phone.done:
                s['rows'].append(dict(kind='phone_result',result=phone.result))
                return finish('phone_passed' if phone.result['passed'] else 'phone_failed',None if phone.result['passed'] else phone.result)
        elif s['phase']==14:
            s['debug'].tick(dt)
            if s['debug'].done:
                s['rows'].append(dict(kind='debug_result',result=s['debug'].result))
                return finish('debug_passed' if s['debug'].result['passed'] else 'debug_failed')
        elif s['phase']==12:
            th=actor('/Game/FoA/Level2/Transition/BP_DreamThreshold')
            if th and th.get_editor_property('Phase')==8:s.setdefault('ending_entered',elapsed)
            if th and th.get_editor_property('Phase')==8 and elapsed-s['ending_entered']>2.5 and not s.get('ending_shot'):
                unreal.SystemLibrary.execute_console_command(w,'Shot showui filename='+str(OUT/'ending_contract.png').replace('\\','/')+' -nosuffix',pc)
                s['rows'].append(dict(kind='ending_view',player=p.get_actor_location().to_tuple(),camera=pc.player_camera_manager.get_camera_location().to_tuple(),view=pc.get_view_target().get_name()))
                s['ending_shot']=True
            if th is None:
                assert not fe.get_editor_property('bInGameplay')
                assert actor('/Game/FoA/Level2/Journey/BP_L2Journey') is None
                assert actor('/Game/FoA/Level2/Drive/BP_L2Car') is None
                credits=fe.get_editor_property('Overlay')
                assert unreal.SystemLibrary.is_valid(credits) and credits.is_in_viewport()
                assert 'Credits' in credits.get_class().get_name()
                s['rows'].append(dict(kind='ending_complete',credits=credits.get_class().get_name(),day=unreal.GameplayStatics.get_game_instance(w).get_editor_property('DayCount')))
                assert unreal.GameplayStatics.get_game_instance(w).get_editor_property('DayCount')==s['initial_day']
                return finish('ending_passed')
    except Exception as exc:finish('error',repr(exc))
s['handle']=unreal.register_slate_post_tick_callback(tick)
print('Threshold proof scheduled')
