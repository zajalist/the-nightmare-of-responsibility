"""Read-only: LS_WakeUp's bindings (name, kind, tracks, child bindings) and every level actor carrying an SK_Teen_Body
skeletal mesh, to find what renders the slapping arm in the Cam_Hit insert. Writes Saved/AnimShots/wake_bindings.json.
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/wake_bindings_probe.py FOA_AREAS=Cinematics"""
import json

import unreal

seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
out = dict(bindings=[], teen_actors=[])
for b in seq.get_bindings():
    tracks = []
    for t in b.get_tracks():
        secs = []
        for s in t.get_sections():
            row = dict(cls=s.get_class().get_name(), start=round(s.get_start_frame_seconds(), 2) if s.has_start_frame() else None,
                       end=round(s.get_end_frame_seconds(), 2) if s.has_end_frame() else None)
            if isinstance(s, unreal.MovieSceneSkeletalAnimationSection):
                a = s.get_editor_property('params').get_editor_property('animation')
                row['anim'] = a.get_path_name() if a else None
            secs.append(row)
        tracks.append(dict(cls=t.get_class().get_name(), name=str(t.get_display_name()), sections=secs))
    parent = b.get_parent()
    out['bindings'].append(dict(name=str(b.get_display_name()), parent=str(parent.get_display_name()) if parent and parent.get_id() != b.get_id() else None,
                                tracks=tracks))
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        m = c.get_skinned_asset()
        if m and 'Teen' in m.get_name():
            out['teen_actors'].append(dict(actor=a.get_actor_label(), cls=a.get_class().get_name(), comp=c.get_name(), mesh=m.get_name(),
                                           visible=c.is_visible(), hidden=a.is_hidden_ed()))
open('P:/FoA/Saved/AnimShots/wake_bindings.json', 'w').write(json.dumps(out, indent=1))
print('WAKE_BINDINGS', len(out['bindings']), 'bindings,', len(out['teen_actors']), 'teen components in the level')
