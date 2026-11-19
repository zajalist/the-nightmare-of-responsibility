"""Saves this lane's assets given as FOA_ASSETS (comma list of /Game paths), only those that are dirty.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/save_assets.py FOA_AREAS=/Game/FoA/Characters/Player FOA_ASSETS=/Game/...,..."""
import os

import unreal

for p in [x for x in os.environ.get("FOA_ASSETS", "").split(",") if x]:
    a = unreal.load_asset(p)
    print("SAVE", p, unreal.EditorAssetLibrary.save_loaded_asset(a, True))
