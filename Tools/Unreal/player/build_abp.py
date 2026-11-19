"""Extends ABP_FoAPlayer (a duplicate of the template ABP_Unarmed; the template itself stays untouched).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_abp.py FOA_STEP=vars|events|states|animgraph|pins
Kept from the template: Idle (MM_Idle: the breathing idle), Jump/Fall/Land, Slot 'DefaultSlot', foot-IK control rig.
Added: walk/jog blend spaces, Jog + TurnInPlace states, inertialized starts/stops, head look-at toward interactables."""
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import importlib  # noqa: E402

import graph_style  # noqa: E402

importlib.reload(graph_style)  # the editor's Python keeps modules cached across runs
at = graph_style.at
box = graph_style.box
link = graph_style.link
pin_in = graph_style.pin_in
pin_out = graph_style.pin_out
value = graph_style.value

P = "/Game/FoA/Characters/Player"
ABP = P + "/ABP_FoAPlayer"
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
LOOK_BONE = "neck_02"  # rotating the upper neck carries the head with it: reads as a look, not a broken neck


def ptype(name):
    """Basic pin type by name. UE 5.8: 'real' is the float/double type ('float' and 'double' resolve to integer)."""
    return BEL.get_basic_type_by_name(name)


def abp():
    a = unreal.load_asset(ABP)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
    return a


def finish(a, tag):
    EAL.save_loaded_asset(a, False)
    print(tag, "saved (compile with Hayba anim_blueprint_compile next)")


def graph(a, name):
    return next(g for g in BEL.list_graphs(a) if g.get_name() == name)


def nodes_titled(ed, prefix):
    return [n for n in ed.list_all_nodes() if BEL.get_node_title(n).startswith(prefix)]


def make(ed, entry, x, y):
    return at(ed.create_node_from_name(entry, unreal.Vector2D(x, y), []), x, y)


def step_vars():
    a = abp()
    have = set(BEL.list_member_variable_names(a, False))
    for name, t in (("IsJogging", ptype("bool")), ("LookAtLocation", BEL.get_struct_type(unreal.Vector.static_struct())),
                    ("LookAtWeight", ptype("real")), ("LookAtAlpha", ptype("real")), ("YawRate", ptype("real")),
                    ("LastYaw", ptype("real")), ("FootIKEnabled", ptype("bool"))):
        graph_style.ensure_variable(a, name, t, "true" if name == "FootIKEnabled" else "")
        BEL.set_blueprint_variable_category(a, name, "FoA")
    finish(a, "vars")


def step_events():
    """Push model: pawns (BP_FoAPlayer, BP_Nightmare) set IsJogging / LookAtLocation / LookAtWeight on this instance;
    the update only eases the look-at in and out and measures the capsule's turn rate. No cast to a pawn class."""
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "EventGraph")
    for n in ed.list_all_nodes():  # re-runnable: this step's nodes all sit below the template groups
        if BEL.get_node_pos(n).y >= 900:
            ed.remove_nodes([n])
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c).startswith("FoA:"):
            ed.remove_comment_node(c)
    seq = nodes_titled(ed, "Sequence")[0]
    PINL = unreal.BlueprintGraphPinLibrary
    free_pins = [q for q in BEL.list_output_pins(seq) if not PINL.list_connected_pins(q)]
    if not free_pins:  # re-runs reuse the spare pin instead of growing the Sequence
        ed.add_node_pin(seq)
        free_pins = [BEL.list_output_pins(seq)[-1]]
    then_last = free_pins[0]
    upd = next(n for n in ed.list_all_nodes() if BEL.get_node_title(n).replace(" ", "") == "EventBlueprintUpdateAnimation")
    X, Y = -400, 1000
    cur = at(ed.add_get_member_variable_node("LookAtAlpha", ""), X, Y + 180)
    w = at(ed.add_get_member_variable_node("LookAtWeight", ""), X, Y + 260)
    interp = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:FInterpTo"), X + 260, Y + 180)
    s_a = at(ed.add_set_member_variable_node("LookAtAlpha", ""), X + 560, Y)
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(then_last, BEL.find_execute_pin(s_a)), "sequence -> look-at ease"
    link(cur, "LookAtAlpha", interp, "Current")
    link(w, "LookAtWeight", interp, "Target")
    link(upd, "DeltaTimeX", interp, "DeltaTime")
    value(interp, "InterpSpeed", "3.0")  # ~0.3 s ease: the head drifts toward things, never snaps
    link(interp, "ReturnValue", s_a, "LookAtAlpha")
    box(ed, "FoA: look-at ease", "Pawns push LookAtLocation/LookAtWeight; the head weight eases toward it here.", [cur, w, interp, s_a], "look")
    # Yaw rate (deg/s) for turn-in-place: how fast the capsule spins while the feet are idle.
    g_c = at(ed.add_get_member_variable_node("Character", ""), X + 560, Y + 220)
    rot = at(ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation"), X + 780, Y + 220)
    brk = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakRotator"), X + 1020, Y + 220)
    last = at(ed.add_get_member_variable_node("LastYaw", ""), X + 1020, Y + 400)
    sub = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"), X + 1260, Y + 260)
    norm = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis"), X + 1480, Y + 260)
    safe = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:FMax"), X + 1480, Y + 420)
    div = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"), X + 1720, Y + 300)
    s_rate = at(ed.add_set_member_variable_node("YawRate", ""), X + 1960, Y)
    s_last = at(ed.add_set_member_variable_node("LastYaw", ""), X + 2240, Y)
    link(s_a, None, s_rate, None)
    link(s_rate, None, s_last, None)
    link(g_c, "Character", rot, "self")
    link(rot, "ReturnValue", brk, "InRot")
    link(brk, "Yaw", sub, "A")
    link(last, "LastYaw", sub, "B")
    link(sub, "ReturnValue", norm, "Angle")
    link(upd, "DeltaTimeX", safe, "A")
    value(safe, "B", "0.0001")
    link(norm, "ReturnValue", div, "A")
    link(safe, "ReturnValue", div, "B")
    link(div, "ReturnValue", s_rate, "YawRate")
    link(brk, "Yaw", s_last, "LastYaw")
    box(ed, "FoA: turn rate", "Capsule yaw speed in deg/s, read by the TurnInPlace transitions.",
        [g_c, rot, brk, last, sub, norm, safe, div, s_rate, s_last], "anim")
    finish(a, "events")
    # This hook only inserts a runtime initialization setter; it never stages an AnimInstance CDO.
    import runpy
    runpy.run_path('P:/FoA/Tools/Unreal/player/apply_locomotion_root_motion.py', run_name='__main__')


def state_graph(a, name):
    return next(g for g in BEL.list_graphs(a) if g.get_class().get_name() == "AnimationStateGraph" and g.get_name() == name)


def fill_state(a, name, bs_name, speed_var=None, fixed_speed=None):
    """State = one blend space player whose X (Speed) is GroundSpeed, or a constant for the turn shuffle."""
    ed = BGE.get_graph_editor(state_graph(a, name))
    for n in ed.list_all_nodes():
        if not BEL.get_node_title(n).startswith("Output Animation Pose"):
            ed.remove_nodes([n])
    result = nodes_titled(ed, "Output Animation Pose")[0]
    at(result, 0, 0)
    player = make(ed, f"Animation|BlendSpaces|BlendspacePlayer'{bs_name}'", -320, -16)
    link(player, "Pose", result, "Result")
    members = [player]
    if speed_var:
        g = at(ed.add_get_member_variable_node(speed_var, ""), -560, 40)
        link(g, speed_var, player, "X")
        members.append(g)
    else:
        value(player, "X", str(fixed_speed))
    box(ed, name, f"{bs_name} driven by {speed_var or f'a fixed {fixed_speed} cm/s shuffle'}.", members + [result], "anim")


def step_states():
    a = abp()
    names = {g.get_name() for g in BEL.list_graphs(a) if g.get_class().get_name() == "AnimationStateGraph"}
    print("states present:", sorted(names), "(add Jog / TurnInPlace with Hayba anim_blueprint_add_state first)")
    fill_state(a, "Walk / Run", "BS_FoA_Walk", speed_var="GroundSpeed")
    for name, bs, var, fixed in (("Jog", "BS_FoA_Jog", "GroundSpeed", None), ("TurnInPlace", "BS_FoA_Walk", None, 70)):
        if name in names:
            fill_state(a, name, bs, var, fixed)
    # Starts and stops: no dedicated clips exist, so inertial blending carries the momentum across.
    for g in BEL.list_graphs(a):
        if g.get_class().get_name() == "AnimationTransitionGraph":
            t = g.get_outer()
            t.set_editor_property("logic_type", unreal.TransitionLogicType.TLT_INERTIALIZATION)
            t.set_editor_property("crossfade_duration", 0.35)
    finish(a, "states")


def step_animgraph():
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "AnimGraph")
    title = {n: BEL.get_node_title(n) for n in ed.list_all_nodes()}
    for n, t in title.items():
        if t.startswith(("Inertialization", "Local To Component", "Component To Local", "Look At")):
            ed.remove_nodes([n])
    title = {n: BEL.get_node_title(n) for n in ed.list_all_nodes()}
    find = lambda pre: next(n for n, t in title.items() if t.startswith(pre))  # noqa: E731
    loco, save_pose, slot, rig = find("Locomotion"), find("Save cached pose"), find("Slot 'DefaultSlot'"), find("Control Rig")
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c).startswith("FoA:"):
            ed.remove_comment_node(c)
    # Locomotion -> Inertialization -> cached pose (the inertial transitions need this node downstream).
    lx, ly = BEL.get_node_pos(loco).x, BEL.get_node_pos(loco).y
    inert = make(ed, "Animation|Misc.|Inertialization", lx + 220, ly)
    at(save_pose, lx + 480, ly + 16)
    link(loco, "Pose", inert, "Source")
    link(inert, "Pose", save_pose, "Pose")
    # Slot -> LocalToComponent -> LookAt(neck_02) -> ComponentToLocal -> foot-IK control rig.
    sx, sy = BEL.get_node_pos(slot).x, BEL.get_node_pos(slot).y
    for n, dx in ((rig, 1200),):
        at(n, sx + dx, sy)
    l2c = make(ed, "Animation|ConvertSpaces|LocalToComponent", sx + 240, sy)
    look = make(ed, "Animation|SkeletalControls|LookAt", sx + 460, sy)
    c2l = make(ed, "Animation|ConvertSpaces|ComponentToLocal", sx + 900, sy)
    link(slot, "Pose", l2c, "LocalPose")
    link(l2c, "ComponentPose", look, "ComponentPose")
    link(look, "Pose", c2l, "ComponentPose")
    link(c2l, "Pose", rig, "Source")
    configure_look(look)
    alpha = at(ed.add_get_member_variable_node("LookAtAlpha", ""), sx + 240, sy + 200)
    link(alpha, "LookAtAlpha", look, "Alpha")
    foot_ik_gate(ed)
    box(ed, "FoA: inertial locomotion", "Inertialization lets the locomotion transitions carry momentum (stand-in for start/stop clips).", [loco, inert, save_pose], "anim")
    box(ed, "FoA: head look-at", f"Ease {LOOK_BONE} toward the nearest interactable (BP_FoAPlayer.UpdateLookAt), clamp 45 deg.",
        [l2c, look, c2l, alpha], "look")
    if 'ToolHandWeight' in [str(n) for n in BEL.list_member_variable_names(a)]:
        import runpy
        previous_phase = os.environ.get('FOA_PHASE')
        try:
            os.environ['FOA_PHASE'] = 'graph'
            runpy.run_path('P:/FoA/Tools/Unreal/player/build_tool_hand_ik.py', run_name='__main__')
        finally:
            if previous_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = previous_phase
    finish(a, "animgraph")


def foot_ik_gate(ed):
    """Foot IK off during cinematics (SetCinematic on the pawn): the template's NOT IsFalling now ANDs with FootIKEnabled."""
    title = {n: BEL.get_node_title(n) for n in ed.list_all_nodes()}
    not_f = next(n for n, t in title.items() if t.startswith("NOT Boolean"))
    out = BEL.find_output_pin(not_f, "ReturnValue")
    targets = list(unreal.BlueprintGraphPinLibrary.list_connected_pins(out))
    if targets and BEL.get_node_title(unreal.BlueprintGraphPinLibrary.get_owning_node(targets[0])) != "AND Boolean":
        nx, ny = BEL.get_node_pos(not_f).x, BEL.get_node_pos(not_f).y
        both = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND"), nx + 180, ny + 80)
        fik = at(ed.add_get_member_variable_node("FootIKEnabled", ""), nx - 40, ny + 160)
        unreal.BlueprintGraphPinLibrary.break_pin_links(out)
        link(not_f, "ReturnValue", both, "A")
        link(fik, "FootIKEnabled", both, "B")
        for t in targets:
            assert unreal.BlueprintGraphPinLibrary.try_create_connection(BEL.find_output_pin(both, "ReturnValue"), t), "AND -> rig enable"
        box(ed, "FoA: foot IK gate", "Foot IK only when grounded and not in a cinematic (FootIKEnabled, pushed by the pawn).",
            [not_f, both, fik], "anim")


def step_footik():
    a = abp()
    foot_ik_gate(BGE.get_graph_editor_by_name(a, "AnimGraph"))
    finish(a, "footik")


def show_look_pin(look):
    """Expose LookAtLocation as a pin. Iterating the array yields copies, so build a new list and assign it."""
    pins = []
    for p in look.get_editor_property("show_pin_for_properties"):
        if str(p.get_editor_property("property_name")) == "LookAtLocation":
            p.set_editor_property("show_pin", True)
        pins.append(p)
    look.set_editor_property("show_pin_for_properties", pins)


def bone(name):
    b = unreal.BoneReference()  # 5.8: struct constructors take no keyword arguments
    b.set_editor_property("bone_name", name)
    return b


def step_stride():
    """Stride Warping (Lyra's approach) between Main States and the slot: Graph mode reads the walk clip's root motion
    and shortens or lengthens the stride to the capsule's GroundSpeed, so a play rate that is a little off never
    slides the feet. Montages (after the slot) are not warped. Re-runnable."""
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "AnimGraph")
    PINL = unreal.BlueprintGraphPinLibrary
    for sw in nodes_titled(ed, "Stride Warping"):  # drop the old group: the warp and its two space converters
        near = [PINL.get_owning_node(q) for p_ in BEL.list_input_pins(sw) + BEL.list_output_pins(sw)
                for q in PINL.list_connected_pins(p_)]
        # The scale conversion belongs to this group, including its speed getter.
        divisions = [n for n in near if BEL.get_node_title(n) in ("Divide", "float / float", "double / double")]
        for n in divisions:
            near.extend(PINL.get_owning_node(q) for p_ in BEL.list_input_pins(n)
                        for q in PINL.list_connected_pins(p_))
        ed.remove_nodes(list(set([n for n in near if BEL.get_node_title(n).startswith(("Local To Component", "Component To Local", "Get GroundSpeed"))] + divisions + [sw])))
    for c in list(ed.list_comment_nodes()):
        if BEL.get_comment_text(c) == "FoA: stride warping":
            ed.remove_comment_node(c)
    title = {n: BEL.get_node_title(n) for n in ed.list_all_nodes()}
    main = next(n for n, t in title.items() if t.startswith("Main States"))
    slot = next(n for n, t in title.items() if t.startswith("Slot 'DefaultSlot'"))
    mx, my = BEL.get_node_pos(main).x, BEL.get_node_pos(main).y
    l2c = make(ed, "Animation|ConvertSpaces|LocalToComponent", mx + 220, my + 260)
    sw = make(ed, "Animation|SkeletalControls|StrideWarping", mx + 440, my + 260)
    c2l = make(ed, "Animation|ConvertSpaces|ComponentToLocal", mx + 760, my + 260)
    spd = at(ed.add_get_member_variable_node("GroundSpeed", ""), mx + 220, my + 420)
    component_speed = stride_component_speed(ed, spd, mx + 440, my + 460)
    link(main, "Pose", l2c, "LocalPose")
    link(l2c, "ComponentPose", sw, "ComponentPose")
    link(sw, "Pose", c2l, "ComponentPose")
    link(c2l, "Pose", slot, "Source")
    node = sw.get_editor_property("node")
    node.set_editor_property("mode", unreal.WarpingEvaluationMode.GRAPH)
    feet = []
    for side in ("l", "r"):
        f = unreal.StrideWarpingFootDefinition()
        f.set_editor_property("ik_foot_bone", bone(f"ik_foot_{side}"))
        f.set_editor_property("fk_foot_bone", bone(f"foot_{side}"))
        f.set_editor_property("thigh_bone", bone(f"thigh_{side}"))
        feet.append(f)
    node.set_editor_property("foot_definitions", feet)
    node.set_editor_property("pelvis_bone", bone("pelvis"))
    node.set_editor_property("ik_foot_root_bone", bone("ik_foot_root"))
    clamp = node.get_editor_property("stride_scale_modifier")
    for k, v in (("clamp_result", True), ("clamp_min", 0.5), ("clamp_max", 1.1)):
        clamp.set_editor_property(k, v)
    node.set_editor_property("stride_scale_modifier", clamp)
    sw.set_editor_property("node", node)
    shown = [str(PINL.get_pin_name(q)) for q in BEL.list_input_pins(sw)]
    if "LocomotionSpeed" in shown:
        link(component_speed, "ReturnValue", sw, "LocomotionSpeed")
    else:  # expose it like the look-at pin: show it now, wire it after a reload (FOA_STEP=stridepin)
        pins = []
        for q in sw.get_editor_property("show_pin_for_properties"):
            if str(q.get_editor_property("property_name")) == "LocomotionSpeed":
                q.set_editor_property("show_pin", True)
            pins.append(q)
        sw.set_editor_property("show_pin_for_properties", pins)
    box(ed, "FoA: stride warping", "", [l2c, sw, c2l, spd, component_speed], "anim")
    sync_foot_targets(ed)
    finish(a, f"stride (pins {shown})")


def sync_foot_targets(ed):
    """Retargeted GASP clips have static IK tracks; derive targets before stride/ground IK."""
    pins = unreal.BlueprintGraphPinLibrary
    sw = nodes_titled(ed, "Stride Warping")[0]
    copies = [n for n in ed.list_all_nodes() if n.get_class().get_name() == 'AnimGraphNode_CopyBone'
              and str(n.get_editor_property('node').get_editor_property('target_bone').get_editor_property('bone_name')) in ('ik_foot_l','ik_foot_r')]
    upstream = pins.list_connected_pins(pin_in(sw, 'ComponentPose'))[0]
    while pins.get_owning_node(upstream) in copies:
        upstream = pins.list_connected_pins(pin_in(pins.get_owning_node(upstream), 'ComponentPose'))[0]
    pos = BEL.get_node_pos(sw)
    previous = upstream
    for i, side in enumerate(('l','r')):
        n = next((n for n in copies if str(n.get_editor_property('node').get_editor_property('target_bone').get_editor_property('bone_name')) == 'ik_foot_'+side), None)
        if n is None:
            n = make(ed, 'Animation|SkeletalControls|CopyBone', pos.x-560+i*280, pos.y-320)
        assert n, 'CopyBone palette node'
        data = n.get_editor_property('node')
        for k,v in (('source_bone',bone('foot_'+side)),('target_bone',bone('ik_foot_'+side)),
                    ('copy_translation',True),('copy_rotation',True),('copy_scale',False),
                    ('control_space',unreal.BoneControlSpace.BCS_COMPONENT_SPACE)):
            data.set_editor_property(k,v)
        n.set_editor_property('node',data)
        for key in ('bCopyTranslation','bCopyRotation'):
            value(n,key,'true')
        assert pins.try_create_connection(previous,pin_in(n,'ComponentPose'))
        previous=pin_out(n,'Pose')
    assert pins.try_create_connection(previous,pin_in(sw,'ComponentPose'))


def step_syncfeet():
    a=abp()
    sync_foot_targets(BGE.get_graph_editor_by_name(a,'AnimGraph'))
    finish(a,'animated foot targets')


def stride_component_speed(ed, spd, x, y):
    """Stride root delta is in component cm; GroundSpeed is world cm/s."""
    cdo = unreal.get_default_object(unreal.load_asset(P + "/BP_FoAPlayer").generated_class())
    scale = cdo.get_editor_property("Mesh").get_editor_property("relative_scale3d")
    assert scale.x > 0 and max(scale.x, scale.y, scale.z)-min(scale.x, scale.y, scale.z) < 1e-5
    pinlib = unreal.BlueprintGraphPinLibrary
    connected = [pinlib.get_owning_node(q) for p_ in BEL.list_output_pins(spd)
                 for q in pinlib.list_connected_pins(p_)]
    div = next((n for n in connected if BEL.get_node_title(n) in ("Divide", "float / float", "double / double")), None)
    if div is None:
        div = at(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Divide_DoubleDouble"), x, y)
        link(spd, "GroundSpeed", div, "A")
    # Final Teen retarget lengthens planted-foot travel 10.3%; calibrated from live world-space feet.
    value(div, "B", str(scale.x * 1.103))
    return div


def step_stridepin():
    """After a reload the warp shows LocomotionSpeed: wire GroundSpeed to it (clean package only, see step_pins)."""
    pkg = abp().get_outermost()
    dirty = [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    assert pkg.get_name() not in dirty, f"{pkg.get_name()} has unsaved edits: fix and save first"
    unreal.EditorLoadingAndSavingUtils.reload_packages([pkg])
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "AnimGraph")
    sw = nodes_titled(ed, "Stride Warping")[0]
    spd = next(n for n in nodes_titled(ed, "Get GroundSpeed"))
    pos = BEL.get_node_pos(spd)
    div = stride_component_speed(ed, spd, pos.x + 220, pos.y)
    link(div, "ReturnValue", sw, "LocomotionSpeed")
    finish(a, "stridepin")


def step_lookpin():
    """Repair: expose the LookAtLocation pin and drop getters a failed 'pins' run left behind; then run 'pins'."""
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "AnimGraph")
    for n in nodes_titled(ed, "Get LookAtLocation"):
        if not any(unreal.BlueprintGraphPinLibrary.list_connected_pins(q) for q in BEL.list_output_pins(n)):
            ed.remove_nodes([n])
    show_look_pin(nodes_titled(ed, "Look At")[0])
    finish(a, "lookpin")


def configure_look(look):
    """LookAt on neck_02: forward axis measured from the ref pose, sinusoidal 0.5 s ease, 45 deg clamp,
    LookAtLocation exposed as a pin (the pin appears after the package reload in step 'pins')."""
    ref = unreal.AnimPoseExtensions.get_reference_pose(unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin"))
    q = unreal.AnimPoseExtensions.get_bone_pose(ref, LOOK_BONE, unreal.AnimPoseSpaces.WORLD).rotation
    axes = {"X": unreal.Vector(1, 0, 0), "Y": unreal.Vector(0, 1, 0), "Z": unreal.Vector(0, 0, 1)}
    fwd = unreal.Vector(0, 1, 0)  # the mannequin faces +Y in component space
    best = max(((k, s) for k in axes for s in (1, -1)), key=lambda ks: q.rotate_vector(axes[ks[0]] * ks[1]).dot(fwd))
    node = look.get_editor_property("node")
    bone = unreal.BoneReference()  # 5.8: struct constructors take no keyword arguments
    bone.set_editor_property("bone_name", LOOK_BONE)
    node.set_editor_property("bone_to_modify", bone)
    ax = node.get_editor_property("look_at_axis")
    ax.set_editor_property("axis", axes[best[0]] * best[1])
    # FAxis.bInLocalSpace defaults to true; 5.8 Python does not expose it under any name we tried
    node.set_editor_property("look_at_axis", ax)
    node.set_editor_property("look_at_clamp", 45.0)  # subtle: the head leads, the body stays put
    node.set_editor_property("interpolation_type", unreal.InterpolationBlend.SINUSOIDAL)
    node.set_editor_property("interpolation_time", 0.5)
    look.set_editor_property("node", node)
    show_look_pin(look)
    print("look axis", best)


def step_pins():
    """After a reload the LookAt node shows its LookAtLocation pin: wire the variable to it."""
    pkg = abp().get_outermost()
    dirty = [x.get_name() for x in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    # A dirty package makes reload_packages raise a modal "reload modified assets?" prompt that freezes the editor
    # for every lane (07:39 stall): never reload unsaved edits.
    assert pkg.get_name() not in dirty, f"{pkg.get_name()} has unsaved edits (a failed step?): fix and save first"
    unreal.EditorLoadingAndSavingUtils.reload_packages([pkg])  # reconstructs nodes -> new pin
    a = abp()
    ed = BGE.get_graph_editor_by_name(a, "AnimGraph")
    look = nodes_titled(ed, "Look At")[0]
    lx, ly = BEL.get_node_pos(look).x, BEL.get_node_pos(look).y
    g = at(ed.add_get_member_variable_node("LookAtLocation", ""), lx - 220, ly + 280)
    link(g, "LookAtLocation", look, "LookAtLocation")
    finish(a, "pins")


try:
    {"vars": step_vars, "events": step_events, "states": step_states, "animgraph": step_animgraph, "pins": step_pins,
     "footik": step_footik, "lookpin": step_lookpin, "stride": step_stride, "stridepin": step_stridepin,
     "syncfeet": step_syncfeet}[os.environ["FOA_STEP"]]()
except Exception as e:  # Hayba truncates long traceback lines: name the failure on short lines
    import traceback
    for fr in traceback.extract_tb(e.__traceback__)[-2:]:
        print("AT", fr.lineno, fr.line)
    print("ERR", type(e).__name__, str(e)[:300])
    raise
