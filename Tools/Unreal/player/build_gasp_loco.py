"""Anim lane: GASP "Relaxed" locomotion in ABP_FoAPlayer (re-runnable, edits in place).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_gasp_loco.py FOA_STEP=<step>
loops     Walk / Run = Blend Poses by bool (IsJogging, 0.3 s) between the GASP relaxed walk (170 cm/s native) and relaxed
          run (386 cm/s native) loops, both in sync group Loco (their L/R markers keep the feet in phase across the blend).
looppins  after a package reload: PlayRate pins <- WalkPlayRate / JogPlayRate, bActiveValue <- IsJogging.
rates     EventGraph: WalkPlayRate = GroundSpeed / 170 and JogPlayRate = GroundSpeed / 386, clamped 0.5..1 (MapRangeClamped
          through the origin); Stride Warping takes up whatever the clamp leaves.
tired     the AS_FoA_Add_Tired additive over locomotion and idle, by TiredWeight (0.7).
move      BP_FoAPlayer CharacterMovement: a heavy start (300 cm/s2) and a gliding stop (about 28 cm from a walk,
          about 1 m from a jog) instead of a dead stop in under 0.2 s."""
import os

import unreal

P = "/Game/FoA/Characters/Player"
ABP = P + "/ABP_FoAPlayer"
WALK, RUN = "AS_GASP_M_Relaxed_Walk_Loop_F", "AS_GASP_M_Relaxed_Run_Loop_F"
WALK_NATIVE, RUN_NATIVE = 170.0, 386.0
EAL, BEL, BGE, PIN = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary


def closed(asset):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    return asset


def state_graph(a, name):
    return next(g for g in BEL.list_graphs(a) if g.get_class().get_name() == "AnimationStateGraph" and g.get_name() == name)


def show_pin(node, prop):
    pins = []
    for q in node.get_editor_property("show_pin_for_properties"):
        if str(q.get_editor_property("property_name")) == prop:
            q.set_editor_property("show_pin", True)
        pins.append(q)
    node.set_editor_property("show_pin_for_properties", pins)


def step_loops():
    a = closed(unreal.load_asset(ABP))
    ed = BGE.get_graph_editor(state_graph(a, "Walk / Run"))
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Animation Pose"):
            ed.remove_nodes([n])
    out = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
    BEL.set_node_pos(out, unreal.IntPoint(0, 0))
    blend = ed.create_node_from_name("Animation|Blends|BlendPosesbybool", unreal.Vector2D(-320, 0), [])
    assert blend, "BlendPosesbybool"
    BEL.set_node_pos(blend, unreal.IntPoint(-320, 0))
    n = blend.get_editor_property("node")
    n.set_editor_property("blend_time", [0.3, 0.3])
    blend.set_editor_property("node", n)
    players = {}
    for i, clip in enumerate((RUN, WALK)):  # True pose = jog, False pose = walk
        p = ed.create_node_from_name(f"Animation|Sequences|Play'{clip}'", unreal.Vector2D(-760, -120 + i * 260), [])
        assert p, clip
        BEL.set_node_pos(p, unreal.IntPoint(-760, -120 + i * 260))
        show_pin(p, "PlayRate")
        node = p.get_editor_property("node")  # sync settings live on the runtime node in 5.x
        node.set_editor_property("group_name", "Loco")
        node.set_editor_property("method", unreal.AnimSyncMethod.SYNC_GROUP)
        p.set_editor_property("node", node)
        players[clip] = p
    assert PIN.try_create_connection(BEL.find_output_pin(players[RUN], "Pose"), BEL.find_input_pin(blend, "BlendPose_0"))
    assert PIN.try_create_connection(BEL.find_output_pin(players[WALK], "Pose"), BEL.find_input_pin(blend, "BlendPose_1"))
    assert PIN.try_create_connection(BEL.find_output_pin(blend, "Pose"), BEL.find_input_pin(out, "Result"))
    EAL.save_loaded_asset(a, False)
    print("loops: Blend by IsJogging", WALK, RUN, "sync group Loco (run FOA_STEP=looppins next)")


def step_looppins():
    a = closed(unreal.load_asset(ABP))
    pkg = a.get_outermost()
    assert pkg.get_name() not in [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()], "unsaved ABP"
    unreal.EditorLoadingAndSavingUtils.reload_packages([pkg])  # reconstructs the players: PlayRate pins appear
    a = closed(unreal.load_asset(ABP))
    ed = BGE.get_graph_editor(state_graph(a, "Walk / Run"))
    nodes = list(ed.list_all_nodes())
    blend = next(n for n in nodes if n.get_class().get_name() == "AnimGraphNode_BlendListByBool")
    for clip, var, y in ((WALK, "WalkPlayRate", 220), (RUN, "JogPlayRate", -160)):
        p = next(n for n in nodes if clip in str(BEL.get_node_title(n)))
        old = [n for n in nodes if str(BEL.get_node_title(n)).replace(" ", "") == "Get" + var]
        g = old[0] if old else ed.add_get_member_variable_node(var, "")
        BEL.set_node_pos(g, unreal.IntPoint(-1000, y))
        assert PIN.try_create_connection(BEL.find_output_pin(g, var), BEL.find_input_pin(p, "PlayRate")), var
    old = [n for n in nodes if str(BEL.get_node_title(n)).replace(" ", "") == "GetIsJogging"]
    j = old[0] if old else ed.add_get_member_variable_node("IsJogging", "")
    BEL.set_node_pos(j, unreal.IntPoint(-560, 260))
    assert PIN.try_create_connection(BEL.find_output_pin(j, "IsJogging"), BEL.find_input_pin(blend, "bActiveValue"))
    EAL.save_loaded_asset(a, False)
    print("looppins: PlayRate <- WalkPlayRate / JogPlayRate, Active <- IsJogging")


def step_rates():
    import sys
    sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
    import importlib
    import graph_style
    importlib.reload(graph_style)
    a = closed(unreal.load_asset(ABP))
    graph_style.ensure_variable(a, "JogPlayRate", BEL.get_basic_type_by_name("real"), "1.0")
    BEL.set_blueprint_variable_category(a, "JogPlayRate", "FoA")
    eg = BGE.get_graph_editor_by_name(a, "EventGraph")
    maps = [n for n in eg.list_all_nodes() if str(BEL.get_node_title(n)).replace(" ", "") == "MapRangeClamped"]
    sets = {str(BEL.get_node_title(n)).replace(" ", ""): n for n in eg.list_all_nodes()}
    walk_map = next(m for m in maps if any("WalkPlayRate" in str(BEL.get_node_title(PIN.get_owning_node(q)))
                                           for q in PIN.list_connected_pins(BEL.find_output_pin(m, "ReturnValue"))))
    for pin, v in zip(("InRangeA", "InRangeB", "OutRangeA", "OutRangeB"), (WALK_NATIVE * 0.5, WALK_NATIVE, 0.5, 1.0)):
        PIN.set_pin_value(BEL.find_input_pin(walk_map, pin), str(v))
    if "SetJogPlayRate" not in sets:
        st_walk = sets["SetWalkPlayRate"]
        pos = BEL.get_node_pos(st_walk)
        g = eg.add_get_member_variable_node("GroundSpeed", "")
        BEL.set_node_pos(g, unreal.IntPoint(pos.x - 520, pos.y + 330))
        m = eg.add_call_function_node("/Script/Engine.KismetMathLibrary:MapRangeClamped")
        BEL.set_node_pos(m, unreal.IntPoint(pos.x - 300, pos.y + 290))
        st = eg.add_set_member_variable_node("JogPlayRate", "")
        BEL.set_node_pos(st, unreal.IntPoint(pos.x + 260, pos.y))
        nxt = list(PIN.list_connected_pins(BEL.find_then_pin(st_walk)))
        PIN.break_pin_links(BEL.find_then_pin(st_walk))
        assert PIN.try_create_connection(BEL.find_then_pin(st_walk), BEL.find_execute_pin(st))
        for q in nxt:
            assert PIN.try_create_connection(BEL.find_then_pin(st), q)
        assert PIN.try_create_connection(BEL.find_output_pin(g, "GroundSpeed"), BEL.find_input_pin(m, "Value"))
        assert PIN.try_create_connection(BEL.find_output_pin(m, "ReturnValue"), BEL.find_input_pin(st, "JogPlayRate"))
        graph_style.box(eg, "Jog cadence", "", [g, m, st], "anim")
    else:
        m = next(x for x in maps if x is not walk_map)
    for pin, v in zip(("InRangeA", "InRangeB", "OutRangeA", "OutRangeB"), (RUN_NATIVE * 0.5, RUN_NATIVE, 0.5, 1.0)):
        PIN.set_pin_value(BEL.find_input_pin(m, pin), str(v))
    EAL.save_loaded_asset(a, False)
    print("rates: WalkPlayRate = speed/170, JogPlayRate = speed/386, clamped 0.5..1")


def step_move():
    bp = closed(unreal.load_asset(P + "/BP_FoAPlayer"))
    cm = unreal.get_default_object(bp.generated_class()).get_editor_property("character_movement")
    for k, v in (("max_acceleration", 300.0), ("braking_deceleration_walking", 200.0), ("use_separate_braking_friction", True),
                 ("braking_friction", 0.6), ("braking_friction_factor", 2.0)):
        cm.set_editor_property(k, v)
    EAL.save_loaded_asset(bp, False)
    print("move", {k: cm.get_editor_property(k) for k in ("max_walk_speed", "max_acceleration", "braking_deceleration_walking",
                                                          "use_separate_braking_friction", "braking_friction", "ground_friction")})


def step_tired():
    """Apply Additive (AS_FoA_Add_Tired, bake_tired.py) by TiredWeight between Rotate Root Bone and the Locomotion cached
    pose: every locomotion and idle clip gets his slump; montages and the battle stance are untouched."""
    import sys
    sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
    import importlib
    import graph_style
    importlib.reload(graph_style)
    a = closed(unreal.load_asset(ABP))
    graph_style.ensure_variable(a, "TiredWeight", BEL.get_basic_type_by_name("real"), "0.7")
    BEL.set_blueprint_variable_category(a, "TiredWeight", "FoA")
    ag = BGE.get_graph_editor_by_name(a, "AnimGraph")
    nodes = list(ag.list_all_nodes())
    for n in [n for n in nodes if n.get_class().get_name() == "AnimGraphNode_ApplyAdditive"]:
        if not PIN.list_connected_pins(BEL.find_output_pin(n, "Pose")):  # a half-built leftover: rebuild it
            ag.remove_nodes([n])
    nodes = list(ag.list_all_nodes())
    if not [n for n in nodes if n.get_class().get_name() == "AnimGraphNode_ApplyAdditive"]:
        rot = next(n for n in nodes if n.get_class().get_name() == "AnimGraphNode_RotateRootBone")
        out = BEL.find_output_pin(rot, "Pose")
        after = list(PIN.list_connected_pins(out)); assert len(after) == 1
        pos = BEL.get_node_pos(rot)
        add = ag.create_node_from_name("Animation|Blends|ApplyAdditive", unreal.Vector2D(pos.x + 300, pos.y), [])
        assert add, "ApplyAdditive"
        entry = [str(e) for e in ag.list_available_nodes([]) if "AS_FoA_Add_Tired" in str(e)]
        assert entry, "AS_FoA_Add_Tired is not in the AnimGraph palette"
        ev = ag.create_node_from_name(min(entry, key=lambda e: ("Evaluate" not in e, len(e))), unreal.Vector2D(pos.x, pos.y + 260), [])
        assert ev, "AS_FoA_Add_Tired"
        PIN.break_pin_links(out)
        assert PIN.try_create_connection(out, BEL.find_input_pin(add, "Base"))
        assert PIN.try_create_connection(BEL.find_output_pin(ev, "Pose"), BEL.find_input_pin(add, "Additive"))
        assert PIN.try_create_connection(BEL.find_output_pin(add, "Pose"), after[0])
        nxt = PIN.get_owning_node(after[0]); np_ = BEL.get_node_pos(nxt)
        BEL.set_node_pos(add, unreal.IntPoint(pos.x + 300, pos.y)); BEL.set_node_pos(ev, unreal.IntPoint(pos.x, pos.y + 260))
        BEL.set_node_pos(nxt, unreal.IntPoint(np_.x + 300, np_.y))
        g = ag.add_get_member_variable_node("TiredWeight", "")
        BEL.set_node_pos(g, unreal.IntPoint(pos.x + 60, pos.y + 420))
        assert PIN.try_create_connection(BEL.find_output_pin(g, "TiredWeight"), BEL.find_input_pin(add, "Alpha"))
    EAL.save_loaded_asset(a, False)
    print("tired: Apply Additive AS_FoA_Add_Tired by TiredWeight after Rotate Root Bone")


{"loops": step_loops, "looppins": step_looppins, "rates": step_rates, "move": step_move, "tired": step_tired}[os.environ["FOA_STEP"]]()
