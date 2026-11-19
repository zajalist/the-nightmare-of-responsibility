"""Editor-only structural audit and graph captures, under the Drive asset lease."""
import json
import os
from pathlib import Path
import sys
import unreal
sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
import drive_data as D

OUT=Path('P:/FoA/Saved/Codex/l2_drive/graphs');OUT.mkdir(parents=True,exist_ok=True)
BEL=unreal.BlueprintEditorLibrary;GE=unreal.BlueprintGraphEditor
rows=[]
for name in ('BP_L2Car','BP_L2RoadNetwork','BP_Meteor','WBP_L2Drive'):
    bp=unreal.load_asset(D.ROOT+'/'+name);assert bp,name
    assert bp.get_editor_property('status') in (unreal.BlueprintStatus.BS_UP_TO_DATE,unreal.BlueprintStatus.BS_UP_TO_DATE_WITH_WARNINGS),(name,bp.get_editor_property('status'))
    for graph in BEL.list_graphs(bp):
        ed=GE.get_graph_editor(graph)
        row=dict(asset=name,graph=graph.get_name(),nodes=len(ed.list_all_nodes()) if ed else 0)
        rows.append(row)
        if os.environ.get('FOA_CAPTURE_ASSET')==name:
            unreal.FoAGraphToolsLibrary.capture_graph_png(bp,graph.get_name(),str(OUT/(name+'_'+graph.get_name()+'.png')),True)
assert sum(x['nodes'] for x in rows)>100,'Only skeletons exist'
(OUT.parent/'graph_audit.json').write_text(json.dumps(rows,indent=1))
print('DRIVE audit',len(rows),'graphs',sum(x['nodes'] for x in rows),'nodes')
