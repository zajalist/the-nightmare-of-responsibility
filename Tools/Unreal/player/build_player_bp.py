"""BP_FoAPlayer (child of the template BP_ThirdPersonCharacter), its jog input, and GM_FoA.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_player_bp.py FOA_STEP=assets|components|graphs
Each step is short (editor-rules crash safety) and saves what it touched. Re-running a step rebuilds what it owns;
graphs also re-applies build_protagonist.py leader and build_cine_hook.py, which hang off what it rebuilds."""
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
BP_PATH, GM_PATH = P + "/BP_FoAPlayer", "/Game/FoA/Gameplay/GM_FoA"  # paths fixed by docs/mechanics/contract.md
IA_PATH, IMC_PATH = P + "/Input/IA_Jog", "/Game/Input/IMC_Default"  # the template controller adds IMC_Default
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
AT = unreal.AssetToolsHelpers.get_asset_tools()
WALK, JOG = 120.0, 260.0  # cm/s: slow bedroom walk, hesitant jog (UAL walk cycle is ~100, jog ~337)


def ptype(name):
    """Basic pin type by name. UE 5.8: 'real' is the float/double type ('float' and 'double' resolve to integer)."""
    return BEL.get_basic_type_by_name(name)


def save(*assets):
    for a in assets:
        EAL.save_loaded_asset(a, False)


def step_assets():
    ia = unreal.load_asset(IA_PATH) or AT.create_asset("IA_Jog", P + "/Input", unreal.InputAction, unreal.InputAction_Factory())
    imc = unreal.load_asset(IMC_PATH)
    mapped = {(m.get_editor_property("action"), str(m.get_editor_property("key").get_editor_property("key_name")))
              for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")}
    for key in ("LeftShift", "Gamepad_LeftThumbstick"):  # hold to jog
        if (ia, key) not in mapped:
            k = unreal.Key()
            k.set_editor_property("key_name", key)
            imc.map_key(ia, k)
    save(ia, imc)
    bp = unreal.load_asset(BP_PATH) or BEL.create_blueprint_asset_with_parent(
        BP_PATH, EAL.load_blueprint_class("/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"))
    vtypes = {"WalkSpeed": ptype("real"), "JogSpeed": ptype("real"),
              "bIsJogging": ptype("bool"), "bTopDownView": ptype("bool"), "bCinematic": ptype("bool"),
              "bInteractionLocked": ptype("bool"),
              "LookAtTarget": BEL.get_struct_type(unreal.Vector.static_struct()),
              "LookAtWeight": ptype("real"), "LookAtRadius": ptype("real"),
              "LookAtTag": ptype("name"), "SandRadius": ptype("real"),
              "SandOverlayMID": BEL.get_object_reference_type(unreal.MaterialInstanceDynamic)}
    defaults = {"WalkSpeed": str(WALK), "JogSpeed": str(JOG), "LookAtRadius": "260.0", "LookAtTag": "Interactable",
                "SandRadius": "60.0"}
    for name, t in vtypes.items():
        graph_style.ensure_variable(bp, name, t, defaults.get(name, ""))
        cat = ("FoA|Movement" if "Speed" in name or "Jog" in name else "FoA|Camera" if "TopDown" in name or "Cinematic" in name
               else "FoA|Sand" if "Sand" in name else "FoA|Look At")
        BEL.set_blueprint_variable_category(bp, name, cat)
        BEL.set_blueprint_variable_instance_editable(bp, name, name in ("WalkSpeed", "JogSpeed", "LookAtRadius", "LookAtTag", "SandRadius"))
    save(bp)  # compile with Hayba blueprint_compile next (no Python compiles: editor-rules 20:42)
    print("assets ok (compile with Hayba next):", IA_PATH, IMC_PATH, BP_PATH)


def step_components():
    bp = unreal.load_asset(BP_PATH)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}

    def template(name):
        return lib.get_object_for_blueprint(lib.get_data(by_name[name]), bp)

    # Gameplay stays at eye height; authored scenes own their separate cameras.
    import set_camera
    importlib.reload(set_camera)
    boom = template("CameraBoom")
    for k, v in set_camera.BOOM.items():
        boom.set_editor_property(k, v)
    template("FollowCamera").set_editor_property("field_of_view", set_camera.FOV)
    template("FollowCamera").set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    template("FollowCamera").set_editor_property("use_pawn_control_rotation", True)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("jump_max_count", 0)
    cm = cdo.get_editor_property("character_movement")
    cm.set_editor_property("orient_rotation_to_movement", False)
    for k, v in (("max_walk_speed", WALK), ("max_acceleration", 520.0), ("braking_deceleration_walking", 420.0),
                 ("ground_friction", 6.0), ("rotation_rate", unreal.Rotator(roll=0.0, pitch=0.0, yaw=270.0)),
                 ("min_analog_walk_speed", 15.0)):
        cm.set_editor_property(k, v)
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("skeletal_mesh_asset", unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"))
    mesh.set_editor_property("anim_class", EAL.load_blueprint_class(P + "/ABP_FoAPlayer"))
    save(bp)
    print("components ok:", sorted(by_name))


def palette(ed, *needles):
    """Exact palette entry containing every needle (shortest match): for nodes with no direct API (input events...)."""
    hits = [str(a) for a in ed.list_available_nodes([]) if all(n in str(a) for n in needles)]
    assert hits, f"no palette node with {needles}"
    return min(hits, key=len)


def make(ed, entry, x, y):
    return at(ed.create_node_from_name(entry, unreal.Vector2D(x, y), []), x, y)


def call(ed, path, x, y):
    n = ed.add_call_function_node(path)
    assert n and BEL.get_node_title(n), f"empty call node (bad function path?): {path}"
    return at(n, x, y)


self_call = graph_style.self_call


def get(ed, var, x, y, cls=""):
    return at(ed.add_get_member_variable_node(var, cls), x, y)


def setv(ed, var, x, y, cls=""):
    return at(ed.add_set_member_variable_node(var, cls), x, y)


def fresh_function(bp, name):
    return graph_style.function_graph(bp, name)[0]


def entry_node(ed):
    return unreal.BlueprintGraphPinLibrary.get_owning_node(ed.find_graph_entry_pin())


def step_graphs():
    bp = unreal.load_asset(BP_PATH)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    me = bp.generated_class().get_path_name()
    real, boolean = ptype("real"), ptype("bool")

    # PushAnimState: the AnimBP never casts to a pawn class; pawns push their jog + look-at state into it.
    abp_cls = P + "/ABP_FoAPlayer.ABP_FoAPlayer_C"
    ed = fresh_function(bp, "PushAnimState")
    e = at(entry_node(ed), 0, 0)
    g_mesh = get(ed, "Mesh", 0, 200)
    inst = call(ed, "/Script/Engine.SkeletalMeshComponent:GetAnimInstance", 220, 200)
    cast = make(ed, palette(ed, "CastToABP_FoAPlayer"), 480, 0)
    s1 = setv(ed, "IsJogging", 800, 0, abp_cls)
    s2 = setv(ed, "LookAtLocation", 1100, 0, abp_cls)
    s3 = setv(ed, "LookAtWeight", 1400, 0, abp_cls)
    s4 = setv(ed, "FootIKEnabled", 2000, 0, abp_cls)
    g1, g2, g3 = get(ed, "bIsJogging", 800, 220), get(ed, "LookAtTarget", 1100, 220), get(ed, "LookAtWeight", 1400, 220)
    g4 = get(ed, "bCinematic", 1400, 300)
    interaction = get(ed, "bInteractionLocked", 1400, 480)
    authored = call(ed, "/Script/Engine.KismetMathLibrary:BooleanOR", 1700, 300)
    nocine = call(ed, "/Script/Engine.KismetMathLibrary:Not_PreBool", 2000, 300)
    link(g_mesh, "Mesh", inst, "self")
    link(e, None, cast, None)
    link(inst, "ReturnValue", cast, "Object")
    as_pin = next(p for p in BEL.list_output_pins(cast) if str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)).startswith("As"))
    for prev, node, getter, var in ((cast, s1, g1, "IsJogging"), (s1, s2, g2, "LookAtLocation"), (s2, s3, g3, "LookAtWeight")):
        link(prev, None, node, None)
        link(getter, str(unreal.BlueprintGraphPinLibrary.get_pin_name(BEL.list_output_pins(getter)[0])), node, var)
        assert unreal.BlueprintGraphPinLibrary.try_create_connection(as_pin, pin_in(node, "self")), "anim instance target"
    link(s3, None, s4, None)
    link(g4, "bCinematic", authored, "A")
    link(interaction, "bInteractionLocked", authored, "B")
    link(authored, "ReturnValue", nocine, "A")
    link(nocine, "ReturnValue", s4, "FootIKEnabled")
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(as_pin, pin_in(s4, "self")), "anim instance target"
    box(ed, "Push anim state", "Jog flag, look-at target and foot-IK gate (off in cinematics) into ABP_FoAPlayer.",
        [e, g_mesh, inst, cast, s1, s2, s3, s4, g1, g2, g3, g4, interaction, authored, nocine], "anim")
    me_push = me + ":PushAnimState"

    # SetJogging(bJog): the hesitant jog is a held input; speed swaps between the two gaits.
    ed = graph_style.function_graph(bp, "SetJogging", [("bJog", boolean)])[0]
    e = at(entry_node(ed), 0, 0)
    s_jog = setv(ed, "bIsJogging", 260, 0)
    sel = call(ed, "/Script/Engine.KismetMathLibrary:SelectFloat", 260, 160)
    g_jog, g_walk = get(ed, "JogSpeed", 20, 160), get(ed, "WalkSpeed", 20, 240)
    g_cm = get(ed, "CharacterMovement", 300, 320)
    s_max = setv(ed, "MaxWalkSpeed", 560, 0, "/Script/Engine.CharacterMovementComponent")
    link(e, None, s_jog, None)
    link(e, "bJog", s_jog, "bIsJogging")
    link(e, "bJog", sel, "bPickA")
    link(g_jog, "JogSpeed", sel, "A")
    link(g_walk, "WalkSpeed", sel, "B")
    link(s_jog, None, s_max, None)
    link(sel, "ReturnValue", s_max, "MaxWalkSpeed")
    link(g_cm, "CharacterMovement", s_max, "self")
    box(ed, "Jog toggle", "Held jog input picks JogSpeed or WalkSpeed (the 10 Hz anim push carries the jog flag).", [e, s_jog, sel, g_jog, g_walk, g_cm, s_max], "state")

    # SetTopDownView(bEnable): player-side half of the top-down beats. mech_flow's BP_BeatDirector blends the view to
    # its own camera; this freezes look input and zeroes the control yaw so stick-up stays screen-up.
    ed = graph_style.function_graph(bp, "SetTopDownView", [("bEnable", boolean)])[0]
    e = at(entry_node(ed), 0, 0)
    s_td = setv(ed, "bTopDownView", 260, 0)
    ctrl = call(ed, "/Script/Engine.Pawn:GetController", 260, 200)
    ign = call(ed, "/Script/Engine.Controller:SetIgnoreLookInput", 560, 0)
    rot = call(ed, "/Script/Engine.Controller:SetControlRotation", 880, 0)
    for x, y in ((e, s_td), (s_td, ign), (ign, rot)):
        link(x, None, y, None)
    link(e, "bEnable", s_td, "bTopDownView")
    link(e, "bEnable", ign, "bNewLookInput")
    link(ctrl, "ReturnValue", ign, "self")
    link(ctrl, "ReturnValue", rot, "self")
    zero = call(ed, "/Script/Engine.KismetMathLibrary:MakeRotator", 600, 200)  # by-ref pin: must be wired
    link(zero, "ReturnValue", rot, "NewRotation")
    box(ed, "Top-down controls", "Called with the director's view blend: freeze look input, zero control yaw (screen-relative moves).",
        [e, s_td, ctrl, ign, rot, zero], "camera")

    # PlayInteraction(Montage): plays an interaction, holds movement input until it ends.
    ed = graph_style.function_graph(bp, "PlayInteraction", [("Montage", BEL.get_object_reference_type(unreal.AnimMontage))])[0]
    e = at(entry_node(ed), 0, 0)
    hold = graph_style.self_call(ed, "SetInteractionLocked", 260, 0)
    play = call(ed, "/Script/Engine.Character:PlayAnimMontage", 580, 0)
    timer = call(ed, "/Script/Engine.KismetSystemLibrary:K2_SetTimer", 900, 0)
    link(e, None, hold, None)
    value(hold, "bEnable", "true")
    link(hold, None, play, None)
    link(e, "Montage", play, "AnimMontage")
    link(play, None, timer, None)
    link(play, "ReturnValue", timer, "Time")
    value(timer, "FunctionName", "EndInteraction")
    box(ed, "Play interaction", "", [e, hold, play, timer], "anim")

    ed = fresh_function(bp, "EndInteraction")
    e = at(entry_node(ed), 0, 0)
    reset = graph_style.self_call(ed, "SetInteractionLocked", 260, 0)
    value(reset, "bEnable", "false")
    link(e, None, reset, None)
    box(ed, "End interaction", "", [e, reset], "anim")

    # UpdateLookAt (10 Hz timer): nearest tagged interactable in reach and in front -> head look-at target.
    ed = fresh_function(bp, "UpdateLookAt")
    e = at(entry_node(ed), 0, 0)
    tag = get(ed, "LookAtTag", 0, 220)
    allt = call(ed, "/Script/Engine.GameplayStatics:GetAllActorsWithTag", 220, 220)
    me_loc = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 220, 380)
    near = call(ed, "/Script/Engine.GameplayStatics:FindNearestActor", 520, 220)
    bounds = call(ed, "/Script/Engine.Actor:GetActorBounds", 820, 380)
    to_t = call(ed, "/Script/Engine.KismetMathLibrary:Subtract_VectorVector", 1080, 380)
    dirn = call(ed, "/Script/Engine.KismetMathLibrary:Normal", 1300, 380)
    fwd = call(ed, "/Script/Engine.Actor:GetActorForwardVector", 1300, 520)
    dot = call(ed, "/Script/Engine.KismetMathLibrary:Dot_VectorVector", 1520, 420)
    infront = call(ed, "/Script/Engine.KismetMathLibrary:Greater_DoubleDouble", 1740, 420)
    radius = get(ed, "LookAtRadius", 820, 220)
    inreach = call(ed, "/Script/Engine.KismetMathLibrary:Less_DoubleDouble", 1080, 220)
    both = call(ed, "/Script/Engine.KismetMathLibrary:BooleanAND", 1960, 260)
    branch = at(ed.add_branch_node(), 2200, 0)
    s_tgt = setv(ed, "LookAtTarget", 2460, -120)
    s_on = setv(ed, "LookAtWeight", 2760, -120)
    s_off = setv(ed, "LookAtWeight", 2460, 120)
    link(tag, "LookAtTag", allt, "Tag")
    link(allt, "OutActors", near, "ActorsToCheck")
    link(me_loc, "ReturnValue", near, "Origin")
    link(near, "ReturnValue", bounds, "self")
    link(bounds, "Origin", to_t, "A")
    link(me_loc, "ReturnValue", to_t, "B")
    link(to_t, "ReturnValue", dirn, "A")
    link(dirn, "ReturnValue", dot, "A")
    link(fwd, "ReturnValue", dot, "B")
    link(dot, "ReturnValue", infront, "A")
    value(infront, "B", "0.25")
    link(near, "Distance", inreach, "A")
    link(radius, "LookAtRadius", inreach, "B")
    link(inreach, "ReturnValue", both, "A")
    link(infront, "ReturnValue", both, "B")
    # P21: no tagged actor -> FindNearestActor returns None; gate on IsValid before anything reads it (pure
    # GetActorBounds/dot only evaluate on the True path), else 1900 errors per 45 s of PIE.
    has = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", 820, 80)
    gate = at(ed.add_branch_node(), 1960, 0)
    link(near, "ReturnValue", has, "Object")
    link(has, "ReturnValue", gate, "Condition")
    link(e, None, allt, None)
    link(allt, None, gate, None)  # FindNearestActor is pure
    link(gate, "Then", branch, None)
    link(both, "ReturnValue", branch, "Condition")
    link(branch, "Then", s_tgt, None)
    link(bounds, "Origin", s_tgt, "LookAtTarget")
    link(s_tgt, None, s_on, None)
    value(s_on, "LookAtWeight", "1.0")
    link(branch, "Else", s_off, None)
    link(gate, "Else", s_off, None)
    value(s_off, "LookAtWeight", "0.0")
    push2 = self_call(ed, "PushAnimState", 3060, 0)
    link(s_on, None, push2, None)
    link(s_off, None, push2, None)
    box(ed, "Find look-at target", "Nearest actor tagged LookAtTag (default 'Interactable'), within LookAtRadius and in front (dot > 0.25).",
        [tag, allt, me_loc, near, has, bounds, to_t, dirn, fwd, dot, infront, radius, inreach, both], "look")
    box(ed, "Publish to the AnimBP", "", [e, gate, branch, s_tgt, s_on, s_off, push2], "look")

    # UpdatePlayerPos (30 Hz): feet position + radius into MPC_Dream.PlayerPos; the sand material crawls toward it.
    ed = graph_style.function_graph(bp, "UpdatePlayerPos")[0]
    e = at(entry_node(ed), 0, 0)
    loc = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 0, 200)
    cap = get(ed, "CapsuleComponent", 0, 360)
    half = call(ed, "/Script/Engine.CapsuleComponent:GetScaledCapsuleHalfHeight", 240, 360)
    brk = call(ed, "/Script/Engine.KismetMathLibrary:BreakVector", 240, 200)
    feet = call(ed, "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble", 480, 300)
    rad = get(ed, "SandRadius", 480, 440)
    col = call(ed, "/Script/Engine.KismetMathLibrary:MakeColor", 720, 200)
    setv4 = call(ed, "/Script/Engine.KismetMaterialLibrary:SetVectorParameterValue", 980, 0)
    link(e, None, setv4, None)
    link(loc, "ReturnValue", brk, "InVec")
    link(cap, "CapsuleComponent", half, "self")
    link(brk, "Z", feet, "A")
    link(half, "ReturnValue", feet, "B")
    link(brk, "X", col, "R")
    link(brk, "Y", col, "G")
    link(feet, "ReturnValue", col, "B")
    link(rad, "SandRadius", col, "A")
    link(col, "ReturnValue", setv4, "ParameterValue")
    value(setv4, "Collection", "/Game/FoA/PostProcess/MPC_Dream.MPC_Dream")
    value(setv4, "ParameterName", "PlayerPos")
    if "UpdateFaceMaskPose" in [str(n) for n in BEL.list_graph_names(bp)]:
        face_pose = graph_style.self_call(ed, "UpdateFaceMaskPose", 1320, 0)
        link(setv4, None, face_pose, None)
        box(ed, "Face follows the pose", "", [face_pose], "util")
    if "UpdateSleepEyes" in [str(n) for n in BEL.list_graph_names(bp)]:
        eyes = graph_style.self_call(ed, "UpdateSleepEyes", 1600, 0)
        link(face_pose if "UpdateFaceMaskPose" in [str(n) for n in BEL.list_graph_names(bp)] else setv4, None, eyes, None)
        box(ed, "Sleeping eyelids follow the sequence", "", [eyes], "util")
    box(ed, "Feet position for the sand", "MPC_Dream.PlayerPos = feet xyz (capsule bottom) + SandRadius in W, read by the sand WPO.",
        [e, loc, cap, half, brk, feet, rad, col, setv4], "util")
    # SetSandOverlay(Amount): the sandvfx grain layer creeping up from the feet, as an overlay on body + garments.
    ed = graph_style.function_graph(bp, "SetSandOverlay", [("Amount", ptype("real"))])[0]
    e = at(entry_node(ed), 0, 0)
    mid_g = get(ed, "SandOverlayMID", 0, 220)
    has = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", 240, 220)
    br = at(ed.add_branch_node(), 480, 0)
    load = call(ed, "/Script/Engine.KismetSystemLibrary:LoadAsset_Blocking", 760, 120)
    value(load, "Asset", "/Game/FoA/VFX/Sand/M_SandOverlay.M_SandOverlay")
    cast = make(ed, palette(ed, "CastToMaterialInterface"), 1040, 120)
    mk = call(ed, "/Script/Engine.KismetMaterialLibrary:CreateDynamicMaterialInstance", 1340, 120)
    s_mid = setv(ed, "SandOverlayMID", 1640, 120)
    link(e, None, br, None)
    link(mid_g, "SandOverlayMID", has, "Object")
    link(has, "ReturnValue", br, "Condition")
    link(br, "Else", load, None)
    link(load, None, cast, None)
    link(load, "ReturnValue", cast, "Object")
    link(cast, None, mk, None)
    as_pin = next(p for p in BEL.list_output_pins(cast) if str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)).startswith("As"))
    assert unreal.BlueprintGraphPinLibrary.try_create_connection(as_pin, pin_in(mk, "Parent")), "overlay parent"
    link(mk, None, s_mid, None)
    link(mk, "ReturnValue", s_mid, "SandOverlayMID")
    box(ed, "Overlay material (once)", "Load the sandvfx M_SandOverlay and make one dynamic instance; skipped if not shipped yet.",
        [mid_g, has, br, load, cast, mk, s_mid], "util")
    mid2 = get(ed, "SandOverlayMID", 1900, 260)
    setp_ = call(ed, "/Script/Engine.MaterialInstanceDynamic:SetScalarParameterValue", 2160, 0)
    value(setp_, "ParameterName", "Amount")
    body = get(ed, "Body", 2440, 260)
    ov = call(ed, "/Script/Engine.MeshComponent:SetOverlayMaterial", 2700, 0)
    slots = ("StartOutfit", "Shirt", "Trousers", "Socks", "Tie", "Suit")
    ovs, gets = [], []
    for i, slot in enumerate(slots):  # fixed slots chained (no ForEach macro, editor-rules 19:40)
        gets.append(get(ed, slot, 3000 + i * 300, 260))
        ovs.append(call(ed, "/Script/Engine.MeshComponent:SetOverlayMaterial", 3000 + i * 300, 0))
    link(br, "Then", setp_, None)
    link(s_mid, None, setp_, None)
    link(mid2, "SandOverlayMID", setp_, "self")
    link(e, "Amount", setp_, "Value")
    link(setp_, None, ov, None)
    link(body, "Body", ov, "self")
    link(mid2, "SandOverlayMID", ov, "NewOverlayMaterial")  # Amount 0 = no grains (sandvfx), so it can stay on
    prev = ov
    for g_slot, o, slot in zip(gets, ovs, slots):
        link(prev, None, o, None)
        link(g_slot, slot, o, "self")
        link(mid2, "SandOverlayMID", o, "NewOverlayMaterial")
        prev = o
    face = get(ed, "Face", 5000, 260)
    full = call(ed, "/Script/Engine.KismetMathLibrary:Greater_DoubleDouble", 5000, 440)
    value(full, "B", 0.85)
    link(e, "Amount", full, "A")
    face_gate = at(ed.add_branch_node(), 5300, 0)
    face_on = call(ed, "/Script/Engine.MeshComponent:SetOverlayMaterial", 5600, -80)
    face_off = call(ed, "/Script/Engine.MeshComponent:SetOverlayMaterial", 5600, 340)
    link(prev, None, face_gate, None)
    link(full, "ReturnValue", face_gate, "Condition")
    link(face_gate, "Then", face_on, None); link(face_gate, "Else", face_off, None)
    for n in (face_on, face_off):
        link(face, "Face", n, "self")
    link(mid2, "SandOverlayMID", face_on, "NewOverlayMaterial")
    box(ed, "Apply sand overlay", "",
        [mid2, setp_, body, ov] + gets + ovs, "util")
    box(ed, "Cinematic face sand", "", [face, full, face_gate, face_on, face_off], "util")
    # SetCinematic(bEnable): for LS_WakeUp and other sequences driving the mesh: no look-at scan, no foot IK.
    ed = graph_style.function_graph(bp, "SetCinematic", [("bEnable", ptype("bool"))])[0]
    e = at(entry_node(ed), 0, 0)
    s_c = setv(ed, "bCinematic", 260, 0)
    stop_jump = call(ed, "/Script/Engine.Character:StopJumping", 100, -180)
    br = at(ed.add_branch_node(), 540, 0)
    pause = call(ed, "/Script/Engine.KismetSystemLibrary:K2_PauseTimer", 820, -120)
    value(pause, "FunctionName", "UpdateLookAt")
    zero = setv(ed, "LookAtWeight", 1120, -120)
    value(zero, "LookAtWeight", "0.0")
    resume = call(ed, "/Script/Engine.KismetSystemLibrary:K2_UnPauseTimer", 820, 140)
    value(resume, "FunctionName", "UpdateLookAt")
    push = self_call(ed, "PushAnimState", 1420, 0)
    link(e, None, stop_jump, None)
    link(stop_jump, None, s_c, None)
    link(e, "bEnable", s_c, "bCinematic")
    link(s_c, None, br, None)
    link(e, "bEnable", br, "Condition")
    link(br, "Then", pause, None)
    link(pause, None, zero, None)
    link(zero, None, push, None)
    link(br, "Else", resume, None)
    link(resume, None, push, None)
    box(ed, "Cinematic mode", "On: pause the look-at scan, zero the head weight, foot IK off (via PushAnimState). Off: resume.",
        [e, s_c, br, pause, zero, resume, push], "camera")
    # Event graph: input context + jog events + look-at timer.
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for n in list(ed.list_all_nodes()):
        if BEL.get_node_title(n).startswith(("Event BeginPlay", "EnhancedInputAction IA_Jog", "Set Jogging", "Add Mapping Context",
                                             "Get EnhancedInputLocalPlayerSubsystem", "Cast To PlayerController", "Get Controller",
                                             "Set Timer by Function Name")):
            ed.remove_nodes([n])
    for c in list(ed.list_comment_nodes()):
        if unreal.BlueprintEditorLibrary.get_comment_text(c) in ("Player setup", "Jog input"):
            ed.remove_comment_node(c)
    X, Y = 0, 1400  # below the template's input groups
    begin = at(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(X, Y)), X, Y)
    timer = call(ed, "/Script/Engine.KismetSystemLibrary:K2_SetTimer", X + 320, Y)
    link(begin, None, timer, None)
    value(timer, "FunctionName", "UpdateLookAt")
    value(timer, "Time", "0.1")
    value(timer, "bLooping", "true")
    t2 = call(ed, "/Script/Engine.KismetSystemLibrary:K2_SetTimer", X + 640, Y)
    link(timer, None, t2, None)
    value(t2, "FunctionName", "UpdatePlayerPos")
    value(t2, "Time", "0.0333")
    value(t2, "bLooping", "true")
    box(ed, "Player setup", "Start the 10 Hz look-at scan (the jog key lives in IMC_Default, added by the template controller).",
        [begin, timer, t2], "input")
    jog = make(ed, palette(ed, "IA_Jog"), X, Y + 420)
    on = self_call(ed, "SetJogging", X + 360, Y + 400)
    off = self_call(ed, "SetJogging", X + 360, Y + 560)
    link(jog, "Started", on, None)
    value(on, "bJog", "true")
    link(jog, "Completed", off, None)
    value(off, "bJog", "false")
    box(ed, "Jog input", "Hold Shift / L3 to jog; release to walk.", [jog, on, off], "input")
    save(bp)
    # This step rebuilds BeginPlay and SetCinematic, which other builders hang off: re-apply them here so a rerun
    # cannot drop them (the outfit/garment Leader Pose on the MetaHuman Body + the bStartCinematic gate, and
    # SetCinematic's BPC_Interactor.SetSuspended hook).
    for script, step in (("build_protagonist.py", "leader"), ("build_cine_hook.py", None)):
        saved = os.environ.get("FOA_STEP")
        if step:
            os.environ["FOA_STEP"] = step
        try:
            path = "P:/FoA/Tools/Unreal/player/" + script
            exec(compile(open(path, encoding="utf-8").read(), path, "exec"), {"__name__": "__main__", "__file__": path})
        finally:
            os.environ["FOA_STEP"] = saved or ""
    print("graphs ok, dependents re-applied (compile with Hayba blueprint_compile next)")


{"assets": step_assets, "components": step_components, "graphs": step_graphs}[os.environ.get("FOA_STEP", "assets")]()
