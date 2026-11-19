"""Throwaway fixtures for testing delete_assets.py / move_assets.py: two material instances under
/Game/FoA/TMP_cleanup, the child parented to the parent (so the parent has a referencer). Idempotent.

  $env:FOA_AGENT='cleanup'; python Tools/Unreal/ue_remote.py Tools/Cleanup/selftest_assets.py FOA_AREAS=/Game/FoA/TMP_cleanup
Delete them afterwards with delete_assets.py (that is the test).
"""
import unreal

FOLDER = "/Game/FoA/TMP_cleanup"


def make(name, parent_path):
    path = f"{FOLDER}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        print("CLEANUP selftest exists", path)
        return
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi = tools.create_asset(name, FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, unreal.load_asset(parent_path))
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    print("CLEANUP selftest created", path, "parent", parent_path)


make("TMP_cleanup_MI_Parent", "/Engine/EngineMaterials/WorldGridMaterial")
make("TMP_cleanup_MI_Child", f"{FOLDER}/TMP_cleanup_MI_Parent")
