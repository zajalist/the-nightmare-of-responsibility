"""Opens asset editors in the running editor (Hayba's asset_open_editor is blocked by its Python policy).
  python Tools/Unreal/ue_remote.py Tools/Unreal/open_asset.py FOA_ASSETS=/Game/FoA/Materials/M_LightShaft,/Game/FoA/UI/WBP_X
Asset editors open as tabs in the main window here, so then screenshot it with
  powershell -File Tools/Capture/capture_window.ps1 -Title "FoA - Unreal Editor" -Out P:/FoA/Saved/GraphShots/<name>.png"""
import os

import unreal

paths = [p.strip() for p in os.environ.get("FOA_ASSETS", "").split(",") if p.strip()]
assets = [unreal.load_asset(p) for p in paths]
missing = [p for p, a in zip(paths, assets) if a is None]
opened = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([a for a in assets if a])
print("opened", [p for p, a in zip(paths, assets) if a], "missing", missing, "ok", opened)
