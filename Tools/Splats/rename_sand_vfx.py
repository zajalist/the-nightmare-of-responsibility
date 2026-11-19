"""Moves the night mare splat mesh to its contract path (docs/mechanics/contract.md), in its own run as editor-rules.md
requires (never rename in the run that imported or edited the asset). Leaves the Interchange leftovers in place.
  python Tools/Unreal/ue_remote.py Tools/Splats/rename_sand_vfx.py
"""
import unreal


def run():
    EAL = unreal.EditorAssetLibrary
    src = "/Game/FoA/VFX/Splats/Meshes/_import_SM_TheNightMare/SM_TheNightMare/StaticMeshes/SM_TheNightMare"
    dst = "/Game/FoA/VFX/Splats/Meshes/SM_TheNightMare"
    if EAL.does_asset_exist(dst):
        print("already at", dst)
    elif EAL.does_asset_exist(src):
        print("referencers", EAL.find_package_referencers_for_asset(src))
        print("renamed", EAL.rename_asset(src, dst))
    else:
        print("missing", src)


run()
