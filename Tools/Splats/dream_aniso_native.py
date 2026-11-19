"""Native clone/capture only, under the parent-granted stopped-editor asset lease."""
import os
from pathlib import Path
import unreal
assert os.environ.get('FOA_LEASE')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
source='/Game/FoA/Level2/M_SplatWorld_Lean';target='/Game/FoA/Level2/M_SplatWorld_Aniso'
step=os.environ['FOA_SPLAT_ANISO_STEP']
if step=='clone':
    asset=unreal.load_asset(target) or unreal.EditorAssetLibrary.duplicate_asset(source,target)
    assert asset
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
else:
    asset=unreal.load_asset(target);assert asset
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    out=Path('P:/FoA/Saved/Integration/splat_visual_20261112/dream_aniso_graph.png')
    if hasattr(unreal,'FoAGraphToolsLibrary'):
        unreal.FoAGraphToolsLibrary.capture_graph_png(asset,'',str(out),True)
        print('Aniso saved and graph capture requested',target)
    else:print('Aniso saved; graph capture unavailable: FoAGraphTools plugin was skipped by this editor')
