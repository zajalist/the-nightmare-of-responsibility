"""Temporary Teen animation copies for repeatable cloth before/after captures."""
import unreal
E=unreal.EditorAssetLibrary
root='/Game/FoA/Characters/Teen/_QA'
clips=['/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_EdgeReach',
       '/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying',
       '/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle']
inputs=unreal.IKRetargetBatchOperationInputs()
for key,value in (
    ('assets_to_retarget',[E.find_asset_data(p) for p in clips]),
    ('source_mesh',unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple')),
    ('target_mesh',unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')),
    ('ik_retarget_asset',unreal.load_asset('/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_Teen')),
    ('target_path',root),('include_referenced_assets',False),('overwrite_existing_files',True)):
    assert value is not None,key
    inputs.set_editor_property(key,value)
out=unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
assert len(out)==3,out
for data in out:E.save_loaded_asset(data.get_asset(),False)
print('CLOTH_QA_POSES',[str(x.asset_name) for x in out])
