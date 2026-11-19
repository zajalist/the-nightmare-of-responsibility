"""Read-only before/after proof that applying AgX preserves the authored PP stack."""
import json
import os
from pathlib import Path
import unreal

phase = os.environ.get('FOA_AGX_SNAPSHOT', 'before')
assert phase in ('before', 'after')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert world.get_game_world() is None, 'Do not snapshot a play session'
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
result = {}
for actor in actors:
    if isinstance(actor, unreal.PostProcessVolume):
        result[actor.get_path_name()] = {
            'settings': actor.get_editor_property('settings').export_text(),
            **{key: actor.get_editor_property(key) for key in
               ('enabled', 'unbound', 'priority', 'blend_weight', 'blend_radius')},
        }
    for camera in actor.get_components_by_class(unreal.CameraComponent):
        result[camera.get_path_name()] = {
            'settings': camera.get_editor_property('post_process_settings').export_text(),
            'weight': camera.get_editor_property('post_process_blend_weight'),
        }
assert any('PostProcessVolume' in path for path in result), 'Missing authored PP volume'
out = Path('P:/FoA/Saved/Integration/agx')
out.mkdir(parents=True, exist_ok=True)
target = out / (phase + '.json')
if phase == 'before':
    assert not target.exists(), 'Keep the original baseline; archive it before a new run'
else:
    original = json.loads((out / 'before.json').read_text())
    assert original == result, 'Post-process settings changed across the restart'
target.write_text(json.dumps(result, indent=2))
print('AGX_PP_SNAPSHOT', phase, 'entries', len(result), 'unchanged' if phase == 'after' else 'recorded')
