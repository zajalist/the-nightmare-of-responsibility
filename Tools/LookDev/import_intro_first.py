"""Import only the absent texture into Hayba's empty failed-load package; no existing asset overwrite."""
import unreal,os
from pathlib import Path
name='T_Intro_Game01_Sleep';p='/Game/FoA/UI/Intro/Textures/'+name
assert not unreal.EditorAssetLibrary.does_asset_exist(p)
assert unreal.find_object(None,p+'.'+name) is None
assert not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor()
t=unreal.AssetImportTask();t.set_editor_property('filename',str(Path(os.environ['TEMP'])/'hayba-asset-connectors'/'intro_resume'/'textures'/(name+'.png')))
for k,v in [('destination_path','/Game/FoA/UI/Intro/Textures'),('destination_name',name),('automated',True),('replace_existing',False),('save',True)]:t.set_editor_property(k,v)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
assert unreal.EditorAssetLibrary.does_asset_exist(p)
print('Imported actual sleeping-player PIE texture')
