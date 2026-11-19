"""Door-tool lane: capture one Blueprint graph to Saved/GraphShots/doortool_<graph>.png (FoAGraphTools).
  FOA_AREAS=Gameplay python Tools/Unreal/ue_remote.py Tools/Unreal/doortool/graph_shot.py FOA_ASSET=/Game/FoA/Gameplay/BP_Door FOA_GRAPH=RefreshDoorTool
The PNG appears about 1.5 s after the run; compile and save the Blueprint afterwards (opening it can leave it dirty)."""
import os

import unreal

asset = unreal.load_asset(os.environ['FOA_ASSET'])
graph = os.environ['FOA_GRAPH']
unreal.FoAGraphToolsLibrary.capture_graph_png(asset, graph, 'P:/FoA/Saved/GraphShots/doortool_%s.png' % graph, True)
print('CAPTURE requested', graph)
