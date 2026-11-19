"""Bounded readback of the saved shirt placement and targeted interaction data."""
import json
from pathlib import Path
import unreal
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
director=actors['BeatDirector'];expected=json.loads(Path('P:/FoA/Saved/Integration/clothing_clear_spot.json').read_text())['spot']
spot=list(director.get_editor_property('ClothingShirtSpot').to_tuple());assert max(abs(a-b) for a,b in zip(spot,expected))<.001
rows=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')))
fallback=next(r for r in rows if r['Interactable']=='Bed' and r['State']=='ClothingSnag' and r['Verb']=='Use' and r['Item']=='None')
assert fallback['Event']=='ClothingTryUnhook' and fallback['NextState']=='None' and not fallback['Line']
closed=next(r for r in rows if r['Interactable']=='WardrobeDoor' and r['State']=='Open' and r['Verb']=='Use')
assert closed['NextState']=='Closed'
out=dict(shirt_spot=spot,row_count=len(rows),hanger_fallback=fallback['Name'],closet_close_row=closed['Name'],
         shirt_morning_state=str(actors['Shirt_T7'].get_editor_property('State')),runtime_verified=False)
Path('P:/FoA/Saved/Integration/clothing_access_verified.json').write_text(json.dumps(out,indent=1))
print('CLOTHING_ACCESS_READBACK',json.dumps(out))
