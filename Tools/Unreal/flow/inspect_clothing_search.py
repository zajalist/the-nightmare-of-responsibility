"""Read back saved references, priority rows and the reachable shirt location; capture new graphs."""
import json
from pathlib import Path
import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
d=next(a for a in actors.values() if a.get_class().get_name()=='BP_BeatDirector_C')
rows=json.loads(unreal.DataTableFunctionLibrary.export_data_table_to_json_string(unreal.load_asset('/Game/FoA/Gameplay/DT_Interactions')))
search=[r for r in rows if r['Name'].startswith('Search_')]
assert len(search)==19 and rows[:19]==search
refs={n:d.get_editor_property(n).get_actor_label() for n in ('SearchWardrobe','SearchDesk','SearchBed','SearchShirt')}
spot=d.get_editor_property('ClothingShirtSpot')
assert -375<spot.x<375 and -300<spot.y<300
result=dict(references=refs,shirt_spot=spot.to_tuple(),shirt_home=actors['Shirt_T7'].get_actor_transform().export_text(),
            states={n:str(actors[n].get_editor_property('State')) for n in ('Wardrobe','Desk','Bed','Shirt_T7')},row_count=len(rows),priority_rows=len(search))
Path('P:/FoA/Saved/Integration/clothing_search_config.json').write_text(json.dumps(result,indent=2))
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_BeatDirector')
for graph in ('StartClothingSearch','SearchWardrobeClue','SearchDeskClue','SearchBedClue','FreeClothing','HandleClothingSearch','CanReportClothingEvent','ResetClothingSearch'):
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp,graph,'P:/FoA/Saved/GraphShots/BP_BeatDirector_'+graph+'.png',True)
print('CLOTHING_CONFIG_VERIFIED',json.dumps(result))
