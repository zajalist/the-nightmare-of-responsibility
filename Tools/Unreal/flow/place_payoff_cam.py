"""Story lane (main's plan (a), 2026-11-09): place the T9 hero-shot camera in L_Tutorial_Bedroom once. A CineCameraActor
labelled and tagged PayoffCam, focus Disable (no depth of field), 21 mm. BP_BeatDirector.PayoffShot finds it by tag and
moves it from the pawn's transform each time, so this placement only has to be sane (the T8 PlayerMark framing).
Idempotent: an existing PayoffCam is updated, never duplicated. Saves the level.
  $env:FOA_AREAS='none'; $env:FOA_ACTORS='PayoffCam'; $env:FOA_ACTORS_NEW='PayoffCam'
  python Tools/Unreal/ue_remote.py Tools/Unreal/flow/place_payoff_cam.py"""
import unreal

LABEL = 'PayoffCam'
LOC = unreal.Vector(-95.6, 54.0, 55.0)  # pawn space (155.6,-109,-37) from the T8 PlayerMark (60,-55,92) yaw 180
AIM = unreal.Vector(60.0, -55.0, 115.0)
FOCAL = 21.0

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'PIE running'
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
rot = unreal.MathLibrary.find_look_at_rotation(LOC, AIM)
found = [a for a in eas.get_all_level_actors() if a.get_actor_label() == LABEL]
assert len(found) <= 1, found
cam = found[0] if found else eas.spawn_actor_from_class(unreal.CineCameraActor, LOC, rot)
assert isinstance(cam, unreal.CineCameraActor), cam
cam.set_actor_label(LABEL)
cam.set_actor_location_and_rotation(LOC, rot, False, True)
cam.set_editor_property('tags', [unreal.Name(LABEL)])
cam.set_folder_path('Story')
comp = cam.get_cine_camera_component()
focus = comp.get_editor_property('focus_settings')
focus.set_editor_property('focus_method', unreal.CameraFocusMethod.DISABLE)
comp.set_editor_property('focus_settings', focus)
comp.set_editor_property('current_focal_length', FOCAL)
assert comp.get_editor_property('focus_settings').get_editor_property('focus_method') == unreal.CameraFocusMethod.DISABLE
assert abs(comp.get_editor_property('current_focal_length') - FOCAL) < 0.01
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
print('PayoffCam', 'updated' if found else 'placed', cam.get_actor_location(), cam.get_actor_rotation(), FOCAL, 'mm, focus off')
