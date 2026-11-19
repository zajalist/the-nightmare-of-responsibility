"""Read-only graph audit/capture after the native build, under an asset lease."""
import json
from pathlib import Path
import unreal

ROOT='/Game/FoA/Level2/Journey'
OUT=Path('P:/FoA/Saved/Codex/l2_journey/graphs')
OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for name in ('BP_L2Journey','WBP_L2Journey','BP_L2Merge'):
    bp=unreal.load_asset(ROOT+'/'+name)
    assert bp and bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE,name
    for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
        editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
        rows.append(dict(asset=name,graph=graph.get_name(),nodes=len(editor.list_all_nodes()) if editor else 0))
        unreal.FoAGraphToolsLibrary.capture_graph_png(bp,graph.get_name(),str(OUT/(name+'_'+graph.get_name()+'.png')),True)
(OUT.parent/'graph_audit.json').write_text(json.dumps(rows,indent=2))
print('JOURNEY audit',len(rows),'graphs',sum(row['nodes'] for row in rows),'nodes')
