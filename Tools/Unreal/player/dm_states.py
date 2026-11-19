"""Anim lane: the Start and Stop states of ABP_FoAPlayer's Locomotion machine (re-runnable, edits in place).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/dm_states.py FOA_STEP=states|wire
states  Start = Blend Poses by bool (IsJogging) over Sequence Evaluators on the GASP relaxed walk / run start clips, bound
        to SetupStart (on become relevant) and UpdateStart (on update). Stop = the same over the walk / run stop clips,
        bound to UpdateStop. The functions come from dm_graphs.py functions.
wire    after a reload: bActiveValue <- IsJogging in both states."""
import os

import unreal

ABP = "/Game/FoA/Characters/Player/ABP_FoAPlayer"
CLIPS = {"Start": ("AS_GASP_M_Relaxed_Run_Start_F_Lfoot", "AS_GASP_M_Relaxed_Walk_Start_F_Lfoot"),
         "Stop": ("AS_GASP_M_Relaxed_Run_Stop_F_Lfoot", "AS_GASP_M_Relaxed_Walk_Stop_F_Lfoot")}
BIND = {"Start": (("become_relevant_function", "SetupStart"), ("update_function", "UpdateStart")),
        "Stop": (("become_relevant_function", "SetupStop"),("update_function", "UpdateStop"),)}
EAL, BEL, BGE, PIN = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary


def closed(asset):
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    return asset


def state_graph(a, name):
    return next(g for g in BEL.list_graphs(a) if g.get_class().get_name() == "AnimationStateGraph" and g.get_name() == name)


def member(name):
    ref = unreal.MemberReference()
    ref.import_text(f'(MemberName="{name}",bSelfContext=True)')
    return ref


def step_states():
    a = closed(unreal.load_asset(ABP))
    for state, clips in CLIPS.items():
        ed = BGE.get_graph_editor(state_graph(a, state))
        for n in ed.list_all_nodes():
            if not BEL.get_node_title(n).startswith("Output Animation Pose"):
                ed.remove_nodes([n])
        out = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
        BEL.set_node_pos(out, unreal.IntPoint(0, 0))
        blend = ed.create_node_from_name("Animation|Blends|BlendPosesbybool", unreal.Vector2D(-320, 0), [])
        BEL.set_node_pos(blend, unreal.IntPoint(-320, 0))
        n = blend.get_editor_property("node")
        n.set_editor_property("blend_time", [0.3, 0.3])
        blend.set_editor_property("node", n)
        for i, clip in enumerate(clips):  # BlendPose_0 = jog (True), BlendPose_1 = walk
            ev = ed.create_node_from_name(f"Animation|Sequences|Evaluate'{clip}'", unreal.Vector2D(-760, -120 + i * 260), [])
            assert ev, clip
            BEL.set_node_pos(ev, unreal.IntPoint(-760, -120 + i * 260))
            runtime=ev.get_editor_property('node');runtime.set_editor_property('should_loop',False);ev.set_editor_property('node',runtime)
            for prop, fn in BIND[state]:
                ev.set_editor_property(prop, member(fn))
            assert PIN.try_create_connection(BEL.find_output_pin(ev, "Pose"), BEL.find_input_pin(blend, f"BlendPose_{i}"))
        assert PIN.try_create_connection(BEL.find_output_pin(blend, "Pose"), BEL.find_input_pin(out, "Result"))
        j = ed.add_get_member_variable_node("IsJogging", "")
        BEL.set_node_pos(j, unreal.IntPoint(-560, 260))
        assert PIN.try_create_connection(BEL.find_output_pin(j, "IsJogging"), BEL.find_input_pin(blend, "bActiveValue"))
    EAL.save_loaded_asset(a, False)
    print("states: Start and Stop evaluators bound to", {k: [f for _, f in v] for k, v in BIND.items()})


TURNS = ["AS_GASP_M_Relaxed_Stand_Turn_090_L", "AS_GASP_M_Relaxed_Stand_Turn_090_R",
         "AS_GASP_M_Relaxed_Stand_Turn_180_L", "AS_GASP_M_Relaxed_Stand_Turn_180_R"]  # TurnIndex 0..3


def step_turn():
    """Turn in place: the update calls UpdateTurnInPlace (dm_graphs.py turn); Rotate Root Bone (RootYawOffset) sits between
    the Locomotion machine and its cached pose; the Turn state (added with Hayba anim_blueprint_add_state) plays the
    turn clip TurnIndex picks."""
    a = closed(unreal.load_asset(ABP))
    # 1. per-frame call on a fresh pin of the update's Sequence
    eg = BGE.get_graph_editor_by_name(a, "EventGraph")
    nodes = list(eg.list_all_nodes())
    if not [n for n in nodes if str(BEL.get_node_title(n)).replace(" ", "") == "UpdateTurnInPlace"]:
        upd = next(n for n in nodes if "BlueprintUpdateAnimation" in str(BEL.get_node_title(n)).replace(" ", ""))
        seq = next(n for n in nodes if str(BEL.get_node_title(n)) == "Sequence")
        free = [q for q in BEL.list_output_pins(seq) if not PIN.list_connected_pins(q)]
        if not free:
            eg.add_node_pin(seq)
            free = [q for q in BEL.list_output_pins(seq) if not PIN.list_connected_pins(q)]
        call = eg.add_call_function_node(ABP + ".ABP_FoAPlayer_C:UpdateTurnInPlace")
        assert call, "UpdateTurnInPlace call"
        pos = BEL.get_node_pos(seq)
        BEL.set_node_pos(call, unreal.IntPoint(pos.x + 400, pos.y + 900))
        assert PIN.try_create_connection(free[0], BEL.find_execute_pin(call))
        assert PIN.try_create_connection(BEL.find_output_pin(upd, "DeltaTimeX"), BEL.find_input_pin(call, "DeltaSeconds"))
    # 2. Rotate Root Bone after the Locomotion machine
    ag = BGE.get_graph_editor_by_name(a, "AnimGraph")
    nodes = list(ag.list_all_nodes())
    if not [n for n in nodes if n.get_class().get_name() == "AnimGraphNode_RotateRootBone"]:
        sm = next(n for n in nodes if n.get_class().get_name() == "AnimGraphNode_StateMachine" and "Locomotion" in str(BEL.get_node_title(n)))
        out = BEL.find_output_pin(sm, "Pose")
        after = list(PIN.list_connected_pins(out)); assert len(after) == 1
        pos = BEL.get_node_pos(sm)
        rot = ag.create_node_from_name(next(str(e) for e in ag.list_available_nodes([]) if str(e).replace(" ", "").endswith("|RotateRootBone")),
                                       unreal.Vector2D(pos.x + 300, pos.y), [])
        assert rot, "RotateRootBone"
        PIN.break_pin_links(out)
        assert PIN.try_create_connection(out, BEL.find_input_pin(rot, "BasePose"))
        assert PIN.try_create_connection(BEL.find_output_pin(rot, "Pose"), after[0])
        nxt = PIN.get_owning_node(after[0]); np_ = BEL.get_node_pos(nxt)
        BEL.set_node_pos(rot, unreal.IntPoint(pos.x + 300, pos.y))
        BEL.set_node_pos(nxt, unreal.IntPoint(np_.x + 300, np_.y))
        g = ag.add_get_member_variable_node("RootYawOffset", "")
        BEL.set_node_pos(g, unreal.IntPoint(pos.x + 60, pos.y + 180))
        assert PIN.try_create_connection(BEL.find_output_pin(g, "RootYawOffset"), BEL.find_input_pin(rot, "Yaw"))
    # 3. the Turn state: Blend Poses by int (TurnIndex) over the four turn clips
    ed = BGE.get_graph_editor(state_graph(a, "Turn"))
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Animation Pose"):
            ed.remove_nodes([n])
    out = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith("Output Animation Pose"))
    BEL.set_node_pos(out, unreal.IntPoint(0, 0))
    blend = ed.create_node_from_name("Animation|Blends|BlendPosesbyint", unreal.Vector2D(-320, 0), [])
    assert blend, "BlendPosesbyint"
    BEL.set_node_pos(blend, unreal.IntPoint(-320, 0))
    n = blend.get_editor_property("node")
    n.set_editor_property("blend_time", [0.2] * len(TURNS))
    n.set_editor_property("blend_pose", [unreal.PoseLink() for _ in TURNS])  # four pose pins after the reload
    blend.set_editor_property("node", n)
    assert PIN.try_create_connection(BEL.find_output_pin(blend, "Pose"), BEL.find_input_pin(out, "Result"))
    EAL.save_loaded_asset(a, False)
    print("turn: update call, Rotate Root Bone(RootYawOffset), Turn blend (run FOA_STEP=turnpins next)")


def step_turnpins():
    a = closed(unreal.load_asset(ABP))
    pkg = a.get_outermost()
    assert pkg.get_name() not in [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()], "unsaved ABP"
    unreal.EditorLoadingAndSavingUtils.reload_packages([pkg])  # reconstructs the blend: four BlendPose pins
    a = closed(unreal.load_asset(ABP))
    ed = BGE.get_graph_editor(state_graph(a, "Turn"))
    blend = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == "AnimGraphNode_BlendListByInt")
    for i, clip in enumerate(TURNS):
        p = ed.create_node_from_name(f"Animation|Sequences|Play'{clip}'", unreal.Vector2D(-760, -300 + i * 200), [])
        assert p, clip
        BEL.set_node_pos(p, unreal.IntPoint(-760, -300 + i * 200))
        node = p.get_editor_property("node")
        node.set_editor_property("loop_animation", False)
        p.set_editor_property("node", node)
        assert PIN.try_create_connection(BEL.find_output_pin(p, "Pose"), BEL.find_input_pin(blend, f"BlendPose_{i}")), i
    t = ed.add_get_member_variable_node("TurnIndex", "")
    BEL.set_node_pos(t, unreal.IntPoint(-560, 420))
    assert PIN.try_create_connection(BEL.find_output_pin(t, "TurnIndex"), BEL.find_input_pin(blend, "ActiveChildIndex"))
    EAL.save_loaded_asset(a, False)
    print("turnpins: Turn state over", TURNS)


def step_rules():
    """Transition rules. The transitions come from Hayba anim_blueprint_add_transition, whose ids are passed in
    FOA_RULES as id:Var pairs (Var 'auto' = by the clip's time remaining, 0.25 s), e.g.
    AnimStateTransitionNode_5:WantsTurn,AnimStateTransitionNode_6:ShouldMove,AnimStateTransitionNode_7:auto"""
    a = closed(unreal.load_asset(ABP))
    rules = dict(x.split(":") for x in os.environ["FOA_RULES"].split(","))
    done = []
    for g in BEL.list_graphs(a):
        if g.get_class().get_name() != "AnimationTransitionGraph":
            continue
        tn = g.get_outer()
        key = tn.get_name()
        if key not in rules or tn.get_outer().get_name() != "Locomotion":
            continue
        var = None if rules[key] == "auto" else rules[key]
        tn.set_editor_property("logic_type", unreal.TransitionLogicType.TLT_INERTIALIZATION)
        tn.set_editor_property("crossfade_duration", 0.25)
        if var is None:
            tn.set_editor_property("automatic_rule_based_on_sequence_player_in_state", True)
            tn.set_editor_property("automatic_rule_trigger_time", 0.25)
        else:
            ed = BGE.get_graph_editor(g)
            result = next(n for n in ed.list_all_nodes() if n.get_class().get_name() == "AnimGraphNode_TransitionResult")
            pin = BEL.find_input_pin(result, "bCanEnterTransition")
            if not PIN.list_connected_pins(pin):
                negate = var.startswith('!')
                var = var.lstrip('!')
                v = ed.add_get_member_variable_node(var, "")
                pos = BEL.get_node_pos(result)
                BEL.set_node_pos(v, unreal.IntPoint(pos.x - 260, pos.y))
                source = BEL.find_output_pin(v, var)
                if negate:
                    inv = ed.add_call_function_node('/Script/Engine.KismetMathLibrary:Not_PreBool')
                    BEL.set_node_pos(inv, unreal.IntPoint(pos.x - 130, pos.y))
                    assert PIN.try_create_connection(source, BEL.find_input_pin(inv, 'A'))
                    source = BEL.find_output_pin(inv, 'ReturnValue')
                assert PIN.try_create_connection(source, pin), key
        done.append(key)
    EAL.save_loaded_asset(a, False)
    print("rules", done)


{"states": step_states, "turn": step_turn, "turnpins": step_turnpins, "rules": step_rules}[os.environ["FOA_STEP"]]()
