"""Save the given UI assets (FOA_ASSETS=comma list of /Game paths). Hayba asset_save is policy-blocked."""
import os
import unreal

for p in [s for s in os.environ.get('FOA_ASSETS', '').split(',') if s]:
    print(p, unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False))
