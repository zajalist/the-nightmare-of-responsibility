"""Starts/stops are one-shots: don't wrap a completed stop back to a moving pose."""
import unreal
bp=unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
for state in ('Start','Stop'):
    graph=next(g for g in unreal.BlueprintEditorLibrary.list_graphs(bp)
        if g.get_name()==state and g.get_class().get_name()=='AnimationStateGraph')
    for editor_node in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes():
        if editor_node.get_class().get_name()!='AnimGraphNode_SequenceEvaluator':continue
        node=editor_node.get_editor_property('node')
        print(state,editor_node.get_name(),'was_looping',node.get_editor_property('should_loop'))
        node.set_editor_property('should_loop',False)
        editor_node.set_editor_property('node',node)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Four distance evaluators nonlooping; native compile required')
