"""Remove ONLY the four unreferenced transient imports from the stack-path probe."""
import os
import unreal
assert os.environ.get('FOA_LEASE')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
for name in ('B0137028_00','B0137029_00','B0137030_00','B0137031_00'):
    path='/Game/FoA/Level2/City/Meshes/'+name
    asset=unreal.load_asset(path)
    if not asset:continue
    assert asset.get_path_name()==path+'.'+name
    assert not unreal.EditorAssetLibrary.find_package_referencers_for_asset(path,True),path
    assert unreal.load_asset(path+'/StaticMeshes/'+name),'Used canonical asset missing'
    assert unreal.EditorAssetLibrary.delete_asset(path),path
    print('Removed own unreferenced import',path)
