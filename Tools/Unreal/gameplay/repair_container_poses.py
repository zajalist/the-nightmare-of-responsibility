"""Typed transform-map fallback: installed Hayba actor writer does not support TMap."""
import json
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
targets = [a for a in actors if a.get_class().get_name() == 'BP_Container_C'
           and a.get_actor_label().startswith(('Wardrobe_', 'Commode_'))]
assert len(targets) == 7
rows = []
for actor in targets:
    poses = dict(actor.get_editor_property('Poses'))
    assert unreal.Name('Open') in poses
    before = str(poses)
    if unreal.Name('Closed') not in poses:
        poses[unreal.Name('Closed')] = unreal.Transform()
        actor.set_editor_property('Poses', poses)
    actual = actor.get_editor_property('Poses')
    assert unreal.Name('Closed') in actual and actual[unreal.Name('Open')] == poses[unreal.Name('Open')]
    rows.append(dict(actor=actor.get_actor_label(), before=before, after=str(actual)))
Path('P:/FoA/Saved/Integration/container_close_patch.json').write_text(json.dumps(rows, indent=2))
print('Verified Closed and preserved Open poses for', len(rows), 'containers; native level_save next')
