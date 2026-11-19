"""Read-only comparison against the pre-QA furniture record. Report differences; never reset user transforms."""
import json
import re

import unreal

ROOT = 'P:/FoA/Saved/Integration/'
with open(ROOT + 'wake_actors_actual.json', encoding='utf-8') as f:
    baseline = {row['label']: row for row in json.load(f)}
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert editor.get_game_world() is None, 'Inspect the editor after PIE releases'
world = editor.get_editor_world()
actors = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)}


def values(value):
    return [float(n) for n in re.findall(r'=[ ]*(-?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?)', value)]


def compare(label, before, after):
    old, new = values(before), values(after)
    assert len(old) == len(new) == 10, (label, before, after)
    return max(abs(a - b) for a, b in zip(old, new)) < 0.001


rows, differences = [], []
for label, previous in baseline.items():
    actor = actors.get(label)
    assert actor, label
    transform = actor.get_actor_transform().export_text()
    same = compare(label, previous['transform'], transform)
    if not same:
        differences.append(label + '.ActorTransform')
    components = {c.get_name(): c for c in actor.get_components_by_class(unreal.StaticMeshComponent)}
    meshes = []
    for old in previous['meshes']:
        component = components.get(old['name'])
        assert component, (label, old['name'])
        current = component.get_world_transform().export_text()
        unchanged = compare(label, old['transform'], current)
        if not unchanged:
            differences.append(label + '.' + old['name'])
        meshes.append(dict(name=old['name'], transform=current, unchanged=unchanged,
                           collision=str(component.get_collision_enabled()), visible=component.is_visible()))
    rows.append(dict(label=label, transform=transform, unchanged=same, meshes=meshes,
                     hidden=actor.hidden, collision=actor.get_actor_enable_collision()))
result = dict(result='PASS' if not differences else 'CHANGED', differences=differences, actors=rows)
with open(ROOT + 'editor_layout_verified.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
print('EDITOR LAYOUT', result['result'], differences)
