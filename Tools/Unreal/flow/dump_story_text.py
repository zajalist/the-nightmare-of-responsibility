"""Read-only: dump every player-visible line the story lane audits to Saved/StoryShots/text_dump.json.
  $env:FOA_AREAS='/Game/FoA/Gameplay/Encounter'; python Tools/Unreal/ue_remote.py Tools/Unreal/flow/dump_story_text.py"""
import json
import unreal

out = {}
for t in ('DT_Interactions', 'DT_Items'):
    table = unreal.load_asset('/Game/FoA/Gameplay/' + t)
    out[t] = json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table)) if table else None
gi = unreal.load_asset('/Game/FoA/Gameplay/GI_FoA')
cdo = unreal.get_default_object(gi.generated_class())
out['NotebookLines'] = {str(k): str(v) for k, v in dict(cdo.get_editor_property('NotebookLines')).items()}


def props(path):
    a = unreal.load_asset(path)
    if not a:
        return None
    row = {}
    for name in ('Objective', 'BeatId', 'DisplayName', 'Narration', 'TelegraphLine', 'IntroLine', 'WinLine', 'LoseLine',
                 'VictoryLine', 'StatusLabel', 'Description', 'Hint'):
        try:
            row[name] = str(a.get_editor_property(name))
        except Exception:  # noqa: BLE001  (property absent on this class)
            pass
    return row


out['Beats'] = {f'T{i}': props(f'/Game/FoA/Gameplay/Beats/DA_Beat_T{i}') for i in range(11)}
reg = unreal.AssetRegistryHelpers.get_asset_registry()
out['Encounter'] = {}
for d in reg.get_assets_by_path('/Game/FoA/Gameplay/Encounter/Data', False):
    p = str(d.package_name)
    out['Encounter'][p.rsplit('/', 1)[-1]] = props(p)
open('P:/FoA/Saved/StoryShots/text_dump.json', 'w', encoding='utf-8').write(json.dumps(out, indent=1, ensure_ascii=False))
print('dumped', {k: len(v or {}) for k, v in out.items()})
