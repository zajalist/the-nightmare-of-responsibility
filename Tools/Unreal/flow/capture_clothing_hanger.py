"""Off-screen graph evidence after the final native compile; no graph mutation."""
import unreal
bp=unreal.load_asset('/Game/FoA/Gameplay/BP_BeatDirector')
for graph in ('UpdateClothingHanger','ClearClothingHanger'):
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp,graph,'P:/FoA/Saved/GraphShots/'+graph+'.png',True)
