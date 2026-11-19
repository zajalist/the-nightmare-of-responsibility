"""Change one live search row, preserving every other table row and field."""
import json
from pathlib import Path
import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
table=unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
original=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
rows=json.loads(json.dumps(original))
matched=[r for r in rows if r['Interactable']=='Bed' and r['State']=='ClothingSnag' and r['Verb']=='Use' and r['Item']=='None']
assert len(matched)==1,matched
matched[0]['Event']='ClothingTryUnhook';matched[0]['Line']=''
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table,json.dumps(rows))
observed=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
assert observed==rows,'DataTable readback differs'
changed=[r['Name'] for a,r in zip(original,observed) if a!=r]
assert len(changed)<=1,changed
Path('P:/FoA/Saved/Integration/clothing_hanger_row_verified.json').write_text(json.dumps(dict(changed=changed,row=matched[0],preserved_rows=len(rows)-1),indent=1))
print('Pending native save',table.get_path_name(),'changed',changed,'preserved',len(rows)-1)
