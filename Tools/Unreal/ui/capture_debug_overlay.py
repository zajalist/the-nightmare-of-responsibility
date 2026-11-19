"""Offscreen native graph evidence for the read-only debug overlay."""
import unreal,json
from pathlib import Path
counts={}
for path,graphs in [('/Game/FoA/UI/Framework/BP_FoAFrontEnd',('ToggleDebugPanel','CloseDebugPanel')),('/Game/FoA/UI/Game/WBP_Debug',('EventGraph','RefreshDebug','RefreshStory','RefreshInteraction','RefreshCamera','RefreshLocks','RefreshInventory','RefreshBattle'))]:
    bp=unreal.load_asset(path)
    for name in graphs:
        unreal.FoAGraphToolsLibrary.capture_graph_png(bp,name,'P:/FoA/Saved/GraphShots/Debug_'+name+'.png',True)
        g=unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp,name)
        counts[path+':'+name]=len(g.list_all_nodes())
Path('P:/FoA/Saved/Integration/debug_graph_counts.json').write_text(json.dumps(counts,indent=2))
