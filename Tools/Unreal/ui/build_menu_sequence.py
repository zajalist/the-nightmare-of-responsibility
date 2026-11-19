"""LS_MainMenu_Camera: 24 s seamless loop for BP_MenuCamera (pose A -> B -> A, auto tangents flatten at both
extremes so the loop never hitches) + slow focus breathing. Also places a LevelSequenceActor (folder UI) that
BP_FoAFrontEnd plays when the menu opens. Run via ue_remote.py after setup_menu_camera.py."""
import os
import unreal

AT = unreal.AssetToolsHelpers.get_asset_tools()
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
FPS, SECONDS = 30, 24
END = FPS * SECONDS
PATH = '/Game/FoA/UI/Cinematics/LS_MainMenu_Camera'


def pose(env, default):
    return [float(x) for x in os.environ.get(env, default).split(',')]


A = pose('FOA_POSE_A', '-230,170,150,-6,-50')   # x, y, z, pitch, yaw
B = pose('FOA_POSE_B', '-150,90,140,-7,-51')
FOCUS = tuple(pose('FOA_FOCUS', '650,560'))       # focus subject distance from A and from B (cm)

actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
cam = actors['BP_MenuCamera']
seq = unreal.load_asset(PATH) or AT.create_asset('LS_MainMenu_Camera', '/Game/FoA/UI/Cinematics', unreal.LevelSequence,
                                                 unreal.LevelSequenceFactoryNew())
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
seq.set_display_rate(unreal.FrameRate(FPS, 1))
seq.set_playback_start(0)
seq.set_playback_end(END)
for b in list(seq.get_bindings()):   # rebuild from scratch: reruns stay idempotent
    b.remove()

# Camera transform: drift A -> B -> A
binding = seq.add_possessable(cam)
sec = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
sec.set_range(0, END)
ch = {c.get_name().split('_')[0]: c for c in sec.get_all_channels()}
KEYS = ((0, A), (END // 2, B), (END, A))
for name, idx in (('Location.X', 0), ('Location.Y', 1), ('Location.Z', 2), ('Rotation.Y', 3), ('Rotation.Z', 4)):
    c = ch.get(name) or next(v for k, v in ch.items() if k.startswith(name))
    for frame, p in KEYS:
        c.add_key(unreal.FrameNumber(frame), p[idx], interpolation=unreal.MovieSceneKeyInterpolation.AUTO)

# Focus breathing: two slow breaths per loop on the CineCamera's manual focus distance
cine_binding = seq.add_possessable(cam.get_cine_camera_component())
ftrack = cine_binding.add_track(unreal.MovieSceneFloatTrack)
ftrack.set_property_name_and_path('ManualFocusDistance', 'FocusSettings.ManualFocusDistance')
fsec = ftrack.add_section()
fsec.set_range(0, END)
fch = fsec.get_all_channels()[0]
for frame, dist in ((0, FOCUS[0]), (END // 4, FOCUS[0] * 0.92), (END // 2, FOCUS[1]), (3 * END // 4, FOCUS[1] * 1.06),
                    (END, FOCUS[0])):
    fch.add_key(unreal.FrameNumber(frame), dist, interpolation=unreal.MovieSceneKeyInterpolation.AUTO)
unreal.EditorAssetLibrary.save_asset(PATH, only_if_is_dirty=False)

# Sequence actor the front end plays (no auto play; loops forever)
sa = actors.get('LS_MainMenu_Camera') or EAS.spawn_actor_from_class(unreal.LevelSequenceActor, unreal.Vector(0, 0, 0))
sa.set_actor_label('LS_MainMenu_Camera')
sa.set_folder_path('UI')
sa.set_sequence(seq)
ps = sa.get_editor_property('playback_settings')
ps.set_editor_property('auto_play', False)
lc = ps.get_editor_property('loop_count')
lc.set_editor_property('value', -1)
ps.set_editor_property('loop_count', lc)
sa.set_editor_property('playback_settings', ps)
print('sequence', PATH, 'frames', END, 'channels', sorted(ch), '| actor', sa.get_actor_label())
