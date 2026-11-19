"""New sequence assets only. Run under the Transition asset lease.
Uses story's track helpers without executing its builder or editing its sequences.
All threshold transforms are relative to the real runtime DoorFrame.
"""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
import threshold_data as D
_source=open('P:/FoA/Tools/Unreal/flow/build_battle_intro.py',encoding='utf-8').read().rsplit('\nmain()',1)[0]
exec(_source)

def fresh(name, seconds):
    global END
    END=seconds
    path=D.ROOT+'/'+name
    seq=unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(name,D.ROOT,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
    LSB.close_level_sequence()
    LSB.open_level_sequence(seq)
    LSB.set_lock_camera_cut_to_viewport(False)
    for b in list(seq.get_bindings()):
        if b.is_valid(): b.remove()
    for t in list(seq.get_tracks()): seq.remove_track(t)
    seq.set_display_rate(unreal.FrameRate(FPS,1))
    seq.set_playback_start_seconds(0)
    seq.set_playback_end_seconds(seconds)
    return seq

def save(seq, cams):
    cuts(seq,cams)
    assert not any(t.get_class().get_name()=='MovieSceneControlRigParameterTrack'
                   for b in seq.get_bindings() for t in b.get_tracks()),'Unkeyed rig would override the player animation'
    LSB.close_level_sequence()
    assert EAL.save_loaded_asset(seq,False)
    print('THRESHOLD sequence',seq.get_path_name(),len(seq.get_bindings()),'bindings',END,'seconds')

def threshold(reduced=False):
    seq=fresh('LS_DreamThreshold'+('_ReducedMotion' if reduced else ''),D.THRESHOLD_SECONDS)
    # Room side is frame-local -X. The camera and pawn follow the real relocated doorway.
    cams=[camera(seq,'Approach',[(0,(-330,100,150),(-140,0,135)),(3,(-210,70,155),(-65,0,135))],32,(0,3))]
    keys=[(t,(-distance,0,150),(0,0,150)) for t,_,distance in D.dolly_keys()]
    if reduced: keys=[(3,(-240,0,155),(0,0,135)),(6.7,(-240,0,155),(0,0,135))]
    b,span=camera(seq,'Perspective',keys,24,(3,6.7))
    tpl=unreal.MovieSceneBindingExtensions.get_object_template(b)
    # Reuse the wake-up repair's locator pattern: templates have no World.
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    temp=actors.spawn_actor_from_class(unreal.CineCameraActor,unreal.Vector(-50000,-50000,-50000))
    temp.set_actor_label('TMP_threshold_lens')
    try:
        cb=seq.add_possessable(temp.get_cine_camera_component())
        parent=cb.get_parent();cb.set_parent(b)
        if parent.is_valid():parent.remove()
    finally:
        assert actors.destroy_actor(temp)
    track=cb.add_track(unreal.MovieSceneFloatTrack)
    track.set_property_name_and_path('CurrentFocalLength','CurrentFocalLength')
    section=track.add_section();section.set_range_seconds(3,6.7)
    for t,f,_ in D.dolly_keys(): key(section.get_all_channels()[0],t,32 if reduced else f,LIN)
    cams.append((b,span))
    cams.append(camera(seq,'Crossing',[(6.7,(-240,0,155),(0,0,135)),(9,(-240,0,155),(0,0,135))],32,(6.7,9)))
    if reduced:
        for camera_binding,_ in cams:
            for camera_track in list(camera_binding.get_tracks()):
                if isinstance(camera_track,unreal.MovieScene3DTransformTrack): camera_binding.remove_track(camera_track)
            transform_track(camera_binding,[(0,(-240,0,155),(*rot_to((-240,0,155),(0,0,135)),0))],LIN)
    pb=player(seq,[(0,(-210,0,92),(0,0,0)),(3,(-65,0,92),(0,0,0)),(6.7,(-65,0,92),(0,0,0)),(9,(75,0,92),(0,0,0))],
              [('UAL_Walk_Formal_Loop',0,3),('UAL_Idle_Loop',3,6.7),('UAL_Walk_Formal_Loop',6.7,9)])
    for track in list(pb.get_tracks()):
        if track.get_class().get_name() == 'MovieScene3DTransformTrack':pb.remove_track(track)
    transform_track(pb,[(0,(-210,0,92),(0,0,0)),(3,(-65,0,92),(0,0,0)),
                       (6.7,(-65,0,92),(0,0,0)),(9,(75,0,92),(0,0,0))],LIN,keep=True)
    sec=seq.add_track(unreal.MovieSceneFadeTrack).add_section()
    sec.set_range_seconds(0,END);sec.set_completion_mode(unreal.MovieSceneCompletionMode.KEEP_STATE)
    sec.set_editor_property('fade_color',unreal.LinearColor(1,1,1,1))
    fade_keys=[(0,0),(7.6,0),(9,1)] if reduced else [(0,0),(3,0),(3.2,.9),(3.65,.12),(6.7,0),(8.3,0),(8.8,1),(9,1)]
    for t,v in fade_keys:
        key(sec.get_all_channels()[0],t,v,LIN)
    audio(seq,[(MS+'Sand/S_Sand_Shift',3.1,1.2,.65),(MS+'Breath/S_Breath_Effort',6.7,1,.45)])
    save(seq,cams)

def fall(reduced=False):
    seq=fresh('LS_DreamFall'+('_ReducedMotion' if reduced else ''),D.FALL_SECONDS)
    cams=[camera(seq,'FirstPersonFall',[(0,(0,0,65),(40,0,-80)),(1.2,(0,0,45),(0,20,-220)),
           (2.5,(0,0,-160),(0,10,-650)),(4.1,(0,0,-900),(0,0,-1500))],22,(0,4.2)),
          camera(seq,'OppositeHemisphere',[(4.2,(0,0,18),(15,0,150)),(5.2,(0,0,18),(15,0,150)),
           (6.2,(0,0,52),(100,0,60)),(8,(0,0,160),(400,0,155))],24,(4.2,8))]
    if reduced:
        for camera_binding,span in cams:
            for camera_track in list(camera_binding.get_tracks()):
                if isinstance(camera_track,unreal.MovieScene3DTransformTrack): camera_binding.remove_track(camera_track)
            position=(0,0,65) if span[0]==0 else (0,0,160)
            look=(100,0,65) if span[0]==0 else (400,0,155)
            transform_track(camera_binding,[(span[0],position,(*rot_to(position,look),0))],LIN)
    fade(seq,[(0,0),(1,0),(3.8,1),(4.2,1)] if reduced else [(0,0),(2.8,0),(4.0,1),(4.2,1)])
    fade_track=next(t for t in seq.get_tracks() if t.get_class().get_name()=='MovieSceneFadeTrack')
    fade_track.get_sections()[0].set_range_seconds(0,4.2)
    audio(seq,[(MS+'Sand/S_Sand_Shift',0,1.2,.8),(MS+'Breath/S_Breath_Effort',5.2,1.1,.6)])
    save(seq,cams)

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
threshold()
fall()
threshold(True)
fall(True)
