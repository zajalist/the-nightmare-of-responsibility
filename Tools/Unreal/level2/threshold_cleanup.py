"""Remove the superseded threshold-only animation experiment after native sequencing is verified."""
import unreal
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
bp=unreal.load_asset('/Game/FoA/Level2/Transition/BP_DreamThreshold')
for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
    if graph.get_name()=='CrossDoor':continue
    editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
    assert not any(str(unreal.BlueprintEditorLibrary.get_node_title(n))=='CrossDoor' for n in editor.list_all_nodes())
unreal.BlueprintEditorLibrary.remove_function_graph(bp,'CrossDoor')
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Removed unused CrossDoor function; native sequence owns animation')
