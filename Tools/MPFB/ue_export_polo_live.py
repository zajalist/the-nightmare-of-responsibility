"""Read only: actual imported LOD0 geometry/skin for source comparison."""
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
task=unreal.AssetExportTask()
task.object=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Polo')
task.filename='P:/FoA/Saved/Integration/cinematic_audit/underarm_weights_candidate/live_polo.fbx'
task.automated=True;task.prompt=False;task.replace_identical=True
options=unreal.FbxExportOption();options.level_of_detail=False;options.export_morph_targets=False
task.options=options
assert unreal.Exporter.run_asset_export_task(task)
print('Live Polo LOD0 exported')
