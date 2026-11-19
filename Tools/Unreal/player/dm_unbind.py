"""Clears the anim node function bindings on the Start / Stop evaluators (until Hayba can make thread-safe node functions)."""
import unreal
BEL, BGE = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor
a = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
n_cleared = 0
for g in BEL.list_graphs(a):
    if g.get_class().get_name() == 'AnimationStateGraph' and g.get_name() in ('Start', 'Stop'):
        for n in BGE.get_graph_editor(g).list_all_nodes():
            if n.get_class().get_name() == 'AnimGraphNode_SequenceEvaluator':
                for p in ('update_function', 'become_relevant_function', 'initial_update_function'):
                    n.set_editor_property(p, unreal.MemberReference()); n_cleared += 1
unreal.EditorAssetLibrary.save_loaded_asset(a, False)
print('unbound', n_cleared)
