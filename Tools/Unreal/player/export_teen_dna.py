"""Persist matching face/body rig DNA from the saved Creator bulk data."""
import unreal

root = "/Game/FoA/Characters/Protagonist/Teen"
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
character = unreal.load_asset("/Game/FoA/Characters/Protagonist/Faces/MHC_Face_N")
assert character
params = unreal.MetaHumanDNAExportParams()
params.project_path = root + "/Built_N/DNA"
params.dna_head = True
params.dna_body = True
params.overwrite_existing_assets = True
unreal.MetaHumanCharacterExportBlueprintLibrary.export_dna(character, params)
for part, mesh_path in (("Head", "/MHC_Face_N_Head"), ("Body", "/Body/MHC_Face_N_Body")):
    dna = unreal.load_asset(params.project_path + "/MHC_Face_N_" + part)
    assert dna and dna.get_class().get_name() == "DNA", part
    assert unreal.EditorAssetLibrary.save_loaded_asset(dna, False)
    mesh = unreal.load_asset(root + "/Built_N" + mesh_path)
    assert mesh, mesh_path
    wrapper = next(d for d in mesh.get_editor_property("asset_user_data") if d.get_class().get_name() == "DNAAssetUserData")
    wrapper.set_editor_property("dna_asset", dna)
    assert wrapper.get_editor_property("dna_asset") == dna
    assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
    print("TEEN actual rig DNA exported/saved/wired", part, dna.get_path_name())
