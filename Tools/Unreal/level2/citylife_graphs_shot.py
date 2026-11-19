"""City life lane: graph captures of BP_L2CityLife (one graph per run: CL_GRAPH=Tend|Step|Setup|HideAll|EventGraph).
Writes Saved/GraphShots/citylife_<graph>.png about 1.5 s later. Run citylife_graphs_shot.py CL_GRAPH=close afterwards:
it closes the editor, compiles and saves, so the capture never leaves the Blueprint dirty."""
import os

import unreal

BP = '/Game/FoA/Level2/CityLife/BP_L2CityLife'
bp = unreal.EditorAssetLibrary.load_asset(BP)
graph = os.environ['CL_GRAPH']
if graph == 'close':
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    print('closed, compiled, saved', bp.get_editor_property('status'))
else:
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp, graph, f'P:/FoA/Saved/GraphShots/citylife_{graph}.png', True)
    print('capture requested', graph)
