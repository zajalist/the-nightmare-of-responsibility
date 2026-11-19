"""Generate animated bounds with the FBX importer's non-modal automatic physics path."""
import unreal,json
from pathlib import Path
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder='/Game/FoA/Characters/Teen/Mesh'
body=unreal.load_asset(folder+'/SK_Teen_Body')
assert body and not body.physics_asset,'Use this only when Body has no physics asset'
component=unreal.SkeletalMeshComponent();component.set_skeletal_mesh_asset(body)
before=[component.get_ref_pose_transform(i).export_text() for i in range(component.get_num_bones())]
ui=unreal.FbxImportUI();ui.import_mesh=True;ui.import_as_skeletal=True
ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=unreal.FBXImportType.FBXIT_SKELETAL_MESH
ui.import_animations=False;ui.import_materials=False;ui.import_textures=False;ui.create_physics_asset=True;ui.skeleton=body.skeleton
ui.skeletal_mesh_import_data.import_uniform_scale=1
task=unreal.AssetImportTask();task.filename='P:/FoA-Assets/character/mpfb/export/teen_cm/SK_Teen_Body.fbx'
task.destination_path=folder;task.destination_name='TMP_Teen_Bounds';task.automated=True;task.save=False;task.options=ui
task.factory=unreal.FbxFactory()  # Explicit factory bypasses Interchange, which ignores FbxImportUI physics creation.
if unreal.load_asset(folder+'/TMP_Teen_Bounds'):
    assert unreal.EditorAssetLibrary.delete_asset(folder+'/TMP_Teen_Bounds')
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
temporary=unreal.load_asset(folder+'/TMP_Teen_Bounds');assert temporary
physics=temporary.physics_asset;assert physics,'Fresh importer did not generate physics'
assert unreal.AssetToolsHelpers.get_asset_tools().rename_assets([unreal.AssetRenameData(physics,folder,'PA_Teen_Body')])
body.set_editor_property('physics_asset',physics)
temporary.set_editor_property('physics_asset',None)
# Consolidating only this new temporary mesh rewrites the protected physics preview soft reference.
assert unreal.EditorAssetLibrary.consolidate_assets(body,[temporary])
component.set_skeletal_mesh_asset(body)
after=[component.get_ref_pose_transform(i).export_text() for i in range(component.get_num_bones())]
assert before==after,'Physics creation changed the existing reference pose'
for asset in (physics,body,body.skeleton):assert unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False)
report={'body':body.get_path_name(),'physics_asset':physics.get_path_name(),'reference_unchanged':True}
Path('P:/FoA/Saved/CharacterShots/mpfb/body_physics_bounds.json').write_text(json.dumps(report,indent=2))
print('BODY_BOUNDS_CREATED',json.dumps(report))
