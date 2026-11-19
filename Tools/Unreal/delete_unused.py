"""Delete assets that nothing references (lean-content rule). Run alone, inside the editor lock:

  python Tools/Unreal/ue_remote.py Tools/Unreal/delete_unused.py FOA_ASSETS=/Game/A/X,/Game/B/Y

Closes their editors, skips any asset that still has referencers, never force-deletes.
"""
import os
import unreal


def run():
    eal = unreal.EditorAssetLibrary
    for path in filter(None, os.environ["FOA_ASSETS"].split(",")):
        if not eal.does_asset_exist(path):
            print("FOA_DELETE missing", path)
            continue
        pkg = path.split(".")[0]  # registry, not EAL: EAL's referencer call returned [] for in-use assets (11-09)
        refs = [str(r) for r in (unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(
            pkg, unreal.AssetRegistryDependencyOptions()) or []) if str(r) != pkg]
        if refs:
            print("FOA_DELETE kept (referenced)", path, refs)
            continue
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(path))
        print("FOA_DELETE", path, eal.delete_asset(path))


run()
