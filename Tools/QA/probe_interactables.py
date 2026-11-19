"""qa lane, read-only: dump every placed BP_Interactable (label, class, location, state, rows) and the beat data to
Saved/QA/interactables.json, so the playtest plans target the level as it is today. Editor world only; writes nothing
to /Game.  python Tools/Unreal/integration/run_read.py Tools/QA/probe_interactables.py"""
import json

import unreal

w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
base = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
out = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, base):
    o, e = a.get_actor_bounds(False)
    row = dict(label=a.get_actor_label(), cls=a.get_class().get_name(), loc=[round(v) for v in o.to_tuple()],
               ext=[round(v) for v in e.to_tuple()], hidden=a.is_hidden_ed())
    for k in ('InteractionKey', 'State', 'MorningState', 'RequiredStages', 'ShortcutFlags', 'HiddenStates'):
        try:
            v = a.get_editor_property(k)
            row[k] = str(v) if not isinstance(v, (int, float, bool)) else v
        except Exception as ex:  # property missing on this class
            row[k] = f'n/a {ex}'[:80]
    try:
        row['Rows'] = [r.export_text() for r in a.get_editor_property('Rows')]
    except Exception as ex:
        row['Rows'] = f'n/a {ex}'[:120]
    out.append(row)
d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
beats = []
for b in d.get_editor_property('Beats') if d else []:
    beats.append({k: str(b.get_editor_property(k)) for k in ('Id',) } | {'text': b.export_text()[:1500] if hasattr(b, 'export_text') else ''})
json.dump(dict(interactables=sorted(out, key=lambda r: r['label']), beats=beats),
          open('P:/FoA/Saved/QA/interactables.json', 'w', encoding='utf-8'), indent=1)
print('interactables', len(out), 'beats', len(beats))
