"""Narrow LS_WakeUp repair: explicit animation source component and sleeping DNA eye closure.
Keeps actor transforms, visibility, cameras, timing, audio and existing body-animation parameters.
Run only after editor recovery and sleeping-face API compilation.
"""
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Never mutate during user PIE'
seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
player = next(b for b in seq.get_bindings() if str(b.get_display_name()) == 'Player')
template = unreal.MovieSceneBindingExtensions.get_object_template(player)
assert template
mesh = template.get_editor_property('Mesh')
assert mesh and 'Manny' in mesh.get_skeletal_mesh_asset().get_name(), 'Bind the Mannequin source, not a visible MH/clothing component'
children = [b for b in seq.get_bindings() if str(b.get_display_name()) == 'Animation source Mesh']
assert len(children) <= 1
target = children[0] if children else None
if not target:
    # A spawnable template has no World, so CreatePossessable returns an invalid GUID.
    # Build the component's relative locator from a temporary native Character, then
    # attach that locator to the real Player binding. No helper survives this authoring step.
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    temporary = actors.spawn_actor_from_class(unreal.Character, unreal.Vector(-50000, -50000, -50000))
    assert temporary
    temporary.set_actor_label('TMP_SleepBinding')
    try:
        component = temporary.get_editor_property('Mesh')
        assert component.get_name() == mesh.get_name() == 'CharacterMesh0'
        target = seq.add_possessable(component)
        parent = target.get_parent()
        target.set_parent(player)
        parent.remove()
    finally:
        assert actors.destroy_actor(temporary)
target.set_display_name('Animation source Mesh'); target.set_parent(player)
actor_tracks = [t for t in player.get_tracks() if isinstance(t, unreal.MovieSceneSkeletalAnimationTrack)]
assert len(actor_tracks) <= 1
if actor_tracks:
    old = actor_tracks[0]
    for t in list(target.get_tracks()):
        if isinstance(t, unreal.MovieSceneSkeletalAnimationTrack):
            target.remove_track(t)
    replacement = target.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    for original in old.get_sections():
        section = replacement.add_section()
        section.set_editor_property('params', original.get_editor_property('params'))
        # Set both bounds together. On an empty section, setting the lower bound
        # first can collapse it to zero before the upper bound exists.
        section.set_range(original.get_start_frame(), original.get_end_frame())
        section.set_row_index(original.get_row_index())
        section.set_editor_property('easing', original.get_editor_property('easing'))
        section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
    assert len(replacement.get_sections()) == len(old.get_sections())
    player.remove_track(old)
assert not any(isinstance(t, unreal.MovieSceneSkeletalAnimationTrack) for t in player.get_tracks())
assert any(isinstance(t, unreal.MovieSceneSkeletalAnimationTrack) for t in target.get_tracks())
# Repair earlier child bindings authored with separate lower/upper setters.
# These are the shipping wake timeline's original three non-overlapping phases.
fps=seq.get_display_rate().numerator/seq.get_display_rate().denominator
body_track=next(t for t in target.get_tracks() if isinstance(t,unreal.MovieSceneSkeletalAnimationTrack))
sections=list(body_track.get_sections()); assert len(sections)==3
by_anim={s.get_editor_property('params').animation.get_name():s for s in sections}
assert set(by_anim)=={'AS_FoA_Wake_Lying','AS_FoA_Wake_EdgeReach','MM_Idle'},by_anim
edge_start=19.7
edge_end=edge_start+by_anim['AS_FoA_Wake_EdgeReach'].get_editor_property('params').animation.get_play_length()
by_anim['AS_FoA_Wake_Lying'].set_range_seconds(0.0,edge_start)
by_anim['AS_FoA_Wake_EdgeReach'].set_range_seconds(edge_start,edge_end)
by_anim['MM_Idle'].set_range_seconds(edge_end-.4,seq.get_playback_end()/fps)
assert by_anim['AS_FoA_Wake_EdgeReach'].get_start_frame()==round(edge_start*fps)
assert by_anim['MM_Idle'].get_start_frame()>round(30*fps)
for track in list(player.get_tracks()):
    if isinstance(track, unreal.MovieSceneFloatTrack) and str(track.get_property_name()) == 'SleepEyeClosure':
        player.remove_track(track)
track = player.add_track(unreal.MovieSceneFloatTrack)
track.set_property_name_and_path('SleepEyeClosure', 'SleepEyeClosure')
section = track.add_section()
rate = seq.get_display_rate(); fps = rate.numerator / rate.denominator
end = seq.get_playback_end()
section.set_range(0, end); section.set_completion_mode(unreal.MovieSceneCompletionMode.RESTORE_STATE)
channel = section.get_all_channels()[0]
# Closed for the entire visible lying hold; open as the bed-edge pose starts.
for seconds, value in ((0.0, 1.0), (19.7, 1.0), (20.5, 0.0), (end / fps, 0.0)):
    channel.add_key(unreal.FrameNumber(round(seconds * fps)), value, interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
print('Saved LS_WakeUp: explicit source Mesh, original body sections retained, lying eyelids closed then open at bed edge')
