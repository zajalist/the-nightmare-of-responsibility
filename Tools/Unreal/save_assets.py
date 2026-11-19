"""Save named assets (Hayba asset_save stand-in until the native one is installed).

  FOA_AREAS=<the assets' area or /Game paths> python Tools/Unreal/ue_remote.py Tools/Unreal/save_assets.py FOA_ASSETS=/Game/A,/Game/B
"""
import os
import unreal

for p in filter(None, os.environ["FOA_ASSETS"].split(",")):
    print("FOA_SAVE", p, unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False))
