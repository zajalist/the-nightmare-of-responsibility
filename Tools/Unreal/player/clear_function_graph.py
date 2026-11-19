"""Empties one Blueprint function graph (keeps its entry and result) so its Hayba graph batch can be rebuilt in place.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/clear_function_graph.py FOA_BP=... FOA_GRAPH=..."""
import os
import unreal
BEL = unreal.BlueprintEditorLibrary
bp = unreal.load_asset(os.environ['FOA_BP'])
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, os.environ['FOA_GRAPH'])
keep = ('K2Node_FunctionEntry', 'K2Node_FunctionResult')
for c in list(ed.list_comment_nodes()):
    ed.remove_comment_node(c)
dead = [n for n in ed.list_all_nodes() if n.get_class().get_name() not in keep]
if dead:
    ed.remove_nodes(dead)
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print('cleared', os.environ['FOA_GRAPH'], len(dead))
