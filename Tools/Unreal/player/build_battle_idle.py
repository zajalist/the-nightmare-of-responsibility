"""Fill the new Battle state after Hayba adds it; the sequence-player operation has no typed Hayba tool yet.
Run with ue_remote.py, FOA_AREAS=Characters. Public BP_FoAPlayer.SetBattle(bEnable) pushes IsBattle.
"""
import unreal

P = "/Game/FoA/Characters/Player"
bp = unreal.load_asset(P + "/ABP_FoAPlayer")
clip = unreal.load_asset(P + "/Anims/UAL/UAL_Idle_Loop")
assert bp and clip and bp.get_editor_property("target_skeleton") == clip.get_editor_property("skeleton")
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
graph = next(g for g in BEL.list_graphs(bp) if g.get_class().get_name() == "AnimationStateGraph"
             and g.get_name() == "Battle")
ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
result = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
players = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "AnimGraphNode_SequencePlayer"]
assert len(players) <= 1, "Battle state has unexpected content; inspect before modifying"
player = players[0] if players else ed.create_node_from_name(
    "Animation|Sequences|Play'UAL_Idle_Loop'", unreal.Vector2D(-320, 0), [])
node = player.get_editor_property("node")
node.set_editor_property("sequence", clip)
node.set_editor_property("play_rate", 1.0)
player.set_editor_property("node", node)
assert PIN.try_create_connection(BEL.find_output_pin(player, "Pose"), BEL.find_input_pin(result, "Result"))
assert player.get_editor_property("node").get_editor_property("sequence") == clip
rules = 0
for transition_graph in BEL.list_graphs(bp):
    if transition_graph.get_class().get_name() != "AnimationTransitionGraph":
        continue
    transition = transition_graph.get_outer()
    if transition.get_outer().get_name() != "Locomotion" or transition.get_name() not in (
            "AnimStateTransitionNode_1", "AnimStateTransitionNode_3", "AnimStateTransitionNode_4"):
        continue
    ted = unreal.BlueprintGraphEditor.get_graph_editor(transition_graph)
    output = next(n for n in ted.list_all_nodes() if n.get_class().get_name() == "AnimGraphNode_TransitionResult")
    enabled = next((n for n in ted.list_all_nodes() if BEL.get_node_title(n) == "Get IsBattle"), None)
    enabled = enabled or ted.add_get_member_variable_node("IsBattle", "")
    gate_pin = BEL.find_output_pin(enabled, "IsBattle")
    if transition.get_name() == "AnimStateTransitionNode_4":
        invert = next((n for n in ted.list_all_nodes() if BEL.get_node_title(n) == "NOT Boolean"), None)
        invert = invert or ted.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
        assert PIN.try_create_connection(gate_pin, BEL.find_input_pin(invert, "A"))
        gate_pin = BEL.find_output_pin(invert, "ReturnValue")
    assert PIN.try_create_connection(gate_pin, BEL.find_input_pin(output, "bCanEnterTransition"))
    rules += 1
assert rules == 3, "Expected the three Hayba-created Battle transitions"
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print("Battle: upright neutral idle, 1x rate, beneath the action montage slot")
