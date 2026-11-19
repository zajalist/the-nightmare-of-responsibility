"""Rescans the player lane's folders after an editor restart (the registry may not list newer folders until then).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/rescan.py"""
import unreal

import os
PATHS = [p for p in os.environ.get("FOA_PATHS", "/Game/FoA/Characters/Player").split(",") if p]  # one short run per folder
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(PATHS, True)
for p in PATHS:
    print(p, len(unreal.EditorAssetLibrary.list_assets(p, recursive=True)))
