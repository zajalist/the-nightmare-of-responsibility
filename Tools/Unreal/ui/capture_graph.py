"""One graph -> PNG via FoAGraphTools (async: the PNG lands a few ticks later). FOA_ASSET, FOA_GRAPH ('' = material), FOA_PNG."""
import os
import unreal

asset = unreal.load_asset(os.environ['FOA_ASSET'])
unreal.FoAGraphToolsLibrary.capture_graph_png(asset, os.environ.get('FOA_GRAPH', ''), os.environ['FOA_PNG'], True)
print('capture requested', os.environ['FOA_PNG'])
