"""Mark evaluator time mutable so thread-safe distance matching can write it at runtime."""
import json
from pathlib import Path
import unreal
bp=unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
paths=[]
for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
    if graph.get_name() not in ('Start','Stop') or graph.get_class().get_name()!='AnimationStateGraph':continue
    for node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes():
        if node.get_class().get_name()!='AnimGraphNode_SequenceEvaluator':continue
        paths.append(node.get_path_name())
assert len(paths)==4,paths
Path('P:/FoA/Saved/AnimShots/dm_evaluator_paths.json').write_text(json.dumps(paths))
print('Four evaluator paths exported for native AlwaysDynamicProperties setter')
