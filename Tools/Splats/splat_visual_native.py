"""Asset-only native preparation/receipt, called by apply_splat_visual.py inside its lease."""
import json
import os
from pathlib import Path
import unreal

assert os.environ.get('FOA_LEASE'),'Own asset lease required'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'PIE running'
paths=json.loads(os.environ['FOA_SPLAT_ASSETS']);phase=os.environ['FOA_SPLAT_PHASE']
out=Path('P:/FoA/Saved/Integration/splat_visual_20261112');out.mkdir(parents=True,exist_ok=True)
rows=[]
for path in paths:
    asset=unreal.load_asset(path)
    if phase=='prepare':
        if asset:unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
        continue
    assert asset,path
    row=dict(path=path,kind=asset.get_class().get_name())
    if isinstance(asset,unreal.StaticMesh):
        row.update(vertices=asset.get_num_vertices(0),triangles=asset.get_num_triangles(0),
                   bounds=str(asset.get_bounds()),material=asset.get_material(0).get_path_name())
    if isinstance(asset,unreal.Material):
        unreal.FoAGraphToolsLibrary.capture_graph_png(asset,'',str(out/'dark_sky_graph.png'),True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    rows.append(row)
if phase!='prepare':
    (out/(os.environ['FOA_SPLAT_LABEL']+'.json')).write_text(json.dumps(rows,indent=1))
    print(json.dumps(rows))
