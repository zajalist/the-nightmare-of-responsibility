"""Targeted live DT/notebook patch after the inspection graphs have compiled."""
import json
from pathlib import Path
import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
table=unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
original=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
rows=json.loads(json.dumps(original))
events={'ClothingWardrobeSearched','ClothingDeskSearched','ClothingBedSearched'}
chase='BeginClothingToss' in [str(n) for n in unreal.BlueprintEditorLibrary.list_graph_names(unreal.load_asset('/Game/FoA/Gameplay/BP_BeatDirector'))]
changed=[]
for row in rows:
    if row['Event'] in events:
        row['Line']='';changed.append(row['Name'])
    elif row['Interactable']=='Bed' and row['State']=='ClothingSnag' and row['Verb']=='Look':
        row['Line']='Too far back. I need something long.';row['Prompt']='Inspect the shirt';changed.append(row['Name'])
    elif row['Interactable']=='Bed' and row['State']=='ClothingSnag' and row['Verb']=='Use' and row['Item']=='None':
        row['Prompt']='Reach for the shirt';changed.append(row['Name'])
    elif row['Event']=='ClothingUnhooked':
        row['Line']='' if chase else "Easy. Don't tear it. There. It's free.";changed.append(row['Name'])
assert len(changed)==6,changed
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table,json.dumps(rows))
observed=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
assert len(observed)==len(rows)
for expected,actual in zip(rows,observed):
    for key,value in expected.items():
        if key in ('Line','Prompt') and expected['Name'] in changed and value:
            # UE wraps newly imported FText in a stable NSLOCTEXT identity.
            assert value in actual[key].replace('\\',''),(expected['Name'],actual[key])
        else:assert actual[key]==value,(expected['Name'],key,value,actual[key])
gi=unreal.load_asset('/Game/FoA/Gameplay/GI_FoA');cdo=unreal.get_default_object(gi.generated_class())
notes=dict(cdo.get_editor_property('NotebookLines'))
notes[unreal.Name('Knows.ClothingSnag')]=unreal.Text("Shirt's under the bed. Use the hanger.")
cdo.set_editor_property('NotebookLines',notes)
Path('P:/FoA/Saved/Integration/clothing_discovery_lines.json').write_text(json.dumps(dict(changed=changed,preserved_rows=len(rows)-len(changed)),indent=1))
print('Pending native DT + GI save',changed)
