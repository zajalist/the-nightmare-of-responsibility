"""Read-only inventory called by validate_level_integration inside its lease."""
import json
import os
from pathlib import Path
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
from validate_level_integration import ROOT,OUT,BLUEPRINTS,SEQUENCES,EXISTS_ONLY

label=os.environ['FOA_VALIDATION_LABEL'];assert label in ('before','after')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert editor.get_game_world() is None,'No PIE allowed'
world=editor.get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
core={name:[a.get_actor_label() for a in actors if a.get_class().get_name()==name]
      for name in ('BP_BeatDirector_C','BP_Encounter_C','PlayerStart')}
rows=[dict(path=path,exists=unreal.EditorAssetLibrary.does_asset_exist(path),
           on_disk=(ROOT/('Content'+path[5:]+'.uasset')).is_file())
      for path in (*BLUEPRINTS,*SEQUENCES,*EXISTS_ONLY)]
result=dict(pie_running=False,world=world.get_path_name(),actor_count=len(actors),essential_actors=core,
            temporary_actors=[a.get_actor_label() for a in actors if a.get_actor_label().startswith('TMP')],
            dirty_maps=sorted(p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
            dirty_assets=sorted(p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
            assets=rows)
OUT.mkdir(parents=True,exist_ok=True)
(OUT/(label+'.json')).write_text(json.dumps(result,indent=2))
print(json.dumps(result))
