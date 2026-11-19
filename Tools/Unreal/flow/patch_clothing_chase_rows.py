"""Final targeted table commit: six chase rows; preserve every existing lane row."""
import json,sys
from pathlib import Path
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/gameplay')
from data_rows import row,GRAB_FLOOR
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
table=unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')
before=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
backup=Path('P:/FoA/Saved/Integration/clothing_chase_rows_before.json')
if not backup.exists():backup.write_text(json.dumps(before,indent=1))
added=[]
for state,event,prompt in [('ChaseOne','ClothingReachOne','Catch the shirt'),
    ('ChaseTwo','ClothingReachTwo','Reach for the shirt again'),('ChaseFinal','ClothingReachFinal','Grab the shirt')]:
    added.append(dict(row('Shirt',state,'Use',nxt='ChaseMoving',prompt=prompt,event=event,montage=GRAB_FLOOR),Name='Chase_'+state+'_Use'))
    added.append(dict(row('Shirt',state,'Look',prompt='Look at the shirt'),Name='Chase_'+state+'_Look'))
kept=[dict(r) for r in before if not r['Name'].startswith('Chase_')]
for r in kept:
    if r['Event']=='ClothingUnhooked':r['Line']=''
    if r['Interactable']=='Bed' and r['State']=='ClothingFreed':
        r['Line']='It is loose now.' if r['Verb']=='Use' else 'Nothing underneath now.'
expected=added+kept
assert unreal.DataTableFunctionLibrary.fill_data_table_from_json_string(table,json.dumps(expected))
after=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(table))
assert len(after)==len(expected)
for want,got in zip(expected,after):
    for key,value in want.items():
        if key in ('Prompt','Line') and value and (want['Name'].startswith('Chase_') or
            (want['Interactable']=='Bed' and want['State']=='ClothingFreed' and key=='Line')):
            assert value in got[key].replace('\\',''),(want['Name'],key)
        elif key=='Montage' and value=='':assert got[key] in ('','None')
        else:assert got[key]==value,(want['Name'],key,value,got[key])
Path('P:/FoA/Saved/Integration/clothing_chase_rows_applied.json').write_text(json.dumps(dict(
    row_count=len(after),new_rows=[r['Name'] for r in added],preserved_rows=len(kept),early_give=False),indent=1))
print('Chase rows verified; pending native save',len(after))
