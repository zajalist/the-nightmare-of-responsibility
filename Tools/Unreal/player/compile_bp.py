"""Compiles and saves Blueprints / AnimBlueprints (Hayba blueprint_compile is preferred when the Hayba tools are up).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/compile_bp.py FOA_BPS=/Game/A,/Game/B"""
import os

import unreal


def run():
    for path in [p.strip() for p in os.environ["FOA_BPS"].split(",") if p.strip()]:
        bp = unreal.load_asset(path)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
        ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
        print(path, "compiled:", ok)


run()
