"""BP_Nightmare: the shadow figure that watches and stalks the player (never fights).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_nightmare.py FOA_STEP=asset|graphs
A plain Character (no template components) on ABP_FoAPlayer through the push model, Manny placeholder until SK_Hero.
Heavier than the player: anim rate 0.85, 85 cm/s, slow turns. Custom stencil 2 = the pp lane's tear glitch (TearAmount).
API (contract.md): Appear(Location, Yaw), Vanish(), StalkTo(Target). Stalking steers straight at the target (the bedroom
has no navmesh; shortcut: no obstacle avoidance, add a NavMeshBoundsVolume + AI MoveTo if it must path around furniture)."""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link, pin_in, value = graph_style.at, graph_style.box, graph_style.link, graph_style.pin_in, graph_style.value
P = "/Game/FoA/Characters/Player"
NM = P + "/BP_Nightmare"
MPC_DREAM = "/Game/FoA/PostProcess/MPC_Dream.MPC_Dream"
SAND_LIB = "/Game/FoA/VFX/Sand/BPL_SandFX"  # sandvfx lane function library
SAND_SCALE = "2.0"  # ~40 cm per unit
ABP_CLS = P + "/ABP_FoAPlayer.ABP_FoAPlayer_C"
EAL = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def bp_closed():
    bp = unreal.load_asset(NM)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    return bp


def step_vars():
    """Structural only (the asset itself comes from Hayba blueprint_create, parent /Script/Engine.Character)."""
    bp = bp_closed()
    real = BEL.get_basic_type_by_name("real")
    for name, t, default in (("StalkTarget", BEL.get_object_reference_type(unreal.Actor), ""),
                             ("bStalking", BEL.get_basic_type_by_name("bool"), "false"),
                             ("AcceptRadius", real, "90.0"), ("TurnSpeed", real, "1.2")):
        graph_style.ensure_variable(bp, name, t, default)
        BEL.set_blueprint_variable_category(bp, name, "Nightmare")
        BEL.set_blueprint_variable_instance_editable(bp, name, name in ("AcceptRadius", "TurnSpeed"))
    EAL.save_loaded_asset(bp, False)
    print("vars saved (compile with Hayba next)")


def step_defaults():
    """CDO writes LAST, after the final Hayba compile; save without compiling (editor-rules 20:42)."""
    bp = bp_closed()
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    mesh = cdo.get_editor_property("mesh")
    # The Mannequin itself: ABP_FoAPlayer is authored on its skeleton. A compatible-skeleton mesh (SK_Hero) plays the
    # clips with the wrong arm reference (the A-pose glide the player had); retarget it like the player if it replaces this.
    for k, v in (("skeletal_mesh_asset", unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")),
                 ("anim_class", EAL.load_blueprint_class(P + "/ABP_FoAPlayer")), ("global_anim_rate_scale", 0.85),
                 ("render_custom_depth", True), ("custom_depth_stencil_value", 2),
                 ("relative_location", unreal.Vector(0.0, 0.0, -89.0)), ("relative_rotation", unreal.Rotator(roll=0.0, pitch=0.0, yaw=-90.0))):
        mesh.set_editor_property(k, v)
    sand = unreal.load_asset('/Game/FoA/Materials/MI_DarkSand_Black')
    assert sand
    for index in range(mesh.get_num_materials()):
        mesh.set_material(index, sand)
    cm = cdo.get_editor_property("character_movement")
    for k, v in (("max_walk_speed", 85.0), ("max_acceleration", 300.0), ("braking_deceleration_walking", 300.0),
                 ("orient_rotation_to_movement", True), ("rotation_rate", unreal.Rotator(roll=0.0, pitch=0.0, yaw=120.0))):
        cm.set_editor_property(k, v)
    EAL.save_loaded_asset(bp, False)
    print("defaults saved (compiling afterwards keeps them: the python311 GC crash behind the old rule is fixed)")


def fn(bp, name, params=()):
    ed, e = graph_style.function_graph(bp, name, params)
    return ed, at(e, 0, 0)


def call(ed, path, x, y):
    n = ed.add_call_function_node(path)
    assert n and BEL.get_node_title(n), f"empty call node (bad function path?): {path}"
    return at(n, x, y)


def palette(ed, *needles):
    hits = [str(a) for a in ed.list_available_nodes([]) if all(n in str(a) for n in needles)]
    assert hits, f"no palette node with {needles}"
    return min(hits, key=len)


def step_graphs():
    bp = bp_closed()
    vec = BEL.get_struct_type(unreal.Vector.static_struct())
    real = BEL.get_basic_type_by_name("real")
    # SpawnSandBurst(Location) and the tear pulse (pp lane's TearAmount on stencil 2).
    ed, e = fn(bp, "SpawnSandBurst", [("Location", vec)])
    # sandvfx: BPL_SandFX.SpawnSandBurst(Location, Scale) from a pooled manager. Wired only if the library exists at
    # build time; until then this stays an empty, commented function (re-run this step once sandvfx ships it).
    lib = unreal.load_asset(SAND_LIB)
    members = [e]
    if lib:
        burst = call(ed, lib.generated_class().get_path_name() + ":SpawnSandBurst", 300, 0)
        link(e, None, burst, None)
        link(e, "Location", burst, "Location")
        value(burst, "Scale", SAND_SCALE)
        members.append(burst)
    box(ed, "Black-sand burst", "sandvfx BPL_SandFX.SpawnSandBurst" + ("" if lib else " (not shipped yet: no-op; re-run to wire)"), members, "util")
    for name, amount in (("TearPulse", "1.0"), ("EndTear", "0.0")):
        ed, e = fn(bp, name)
        tear = call(ed, "/Script/Engine.KismetMaterialLibrary:SetScalarParameterValue", 280, 0)
        value(tear, "Collection", MPC_DREAM)
        value(tear, "ParameterName", "TearAmount")
        value(tear, "ParameterValue", amount)
        link(e, None, tear, None)
        members = [e, tear]
        if name == "TearPulse":
            t = call(ed, "/Script/Engine.KismetSystemLibrary:K2_SetTimer", 600, 0)
            value(t, "FunctionName", "EndTear")
            value(t, "Time", "0.45")
            link(tear, None, t, None)
            members.append(t)
        box(ed, "Tear glitch" if name == "TearPulse" else "Tear off", "MPC_Dream.TearAmount tears stencil-2 pixels (pp lane).", members, "look")
    EAL.save_loaded_asset(bp, False)
    print("helpers saved (compile with Hayba, then FOA_STEP=api)")


def step_api():
    bp = bp_closed()
    vec = BEL.get_struct_type(unreal.Vector.static_struct())
    real = BEL.get_basic_type_by_name("real")
    # Appear(Location, Yaw) / Vanish(): through black sand with a tear.
    ed, e = fn(bp, "Appear", [("Location", vec), ("Yaw", real)])
    rot = call(ed, "/Script/Engine.KismetMathLibrary:MakeRotator", 240, 220)
    place = call(ed, "/Script/Engine.Actor:K2_SetActorLocationAndRotation", 520, 0)
    show = call(ed, "/Script/Engine.Actor:SetActorHiddenInGame", 840, 0)
    coll = call(ed, "/Script/Engine.Actor:SetActorEnableCollision", 1120, 0)
    burst = graph_style.self_call(ed, "SpawnSandBurst", 1400, 0)
    tear = graph_style.self_call(ed, "TearPulse", 1700, 0)
    link(e, "Yaw", rot, "Yaw")
    link(e, "Location", place, "NewLocation")
    link(rot, "ReturnValue", place, "NewRotation")
    value(show, "bNewHidden", "false")
    value(coll, "bNewActorEnableCollision", "true")
    link(e, "Location", burst, "Location")
    for a, b in ((e, place), (place, show), (show, coll), (coll, burst), (burst, tear)):
        link(a, None, b, None)
    box(ed, "Appear", "Place, reveal, collide, black-sand burst and a tear pulse.", [e, rot, place, show, coll, burst, tear], "state")
    ed, e = fn(bp, "Vanish")
    loc = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 240, 220)
    burst = graph_style.self_call(ed, "SpawnSandBurst", 260, 0)
    tear = graph_style.self_call(ed, "TearPulse", 560, 0)
    stop = at(ed.add_set_member_variable_node("bStalking", ""), 840, 0)
    hide = call(ed, "/Script/Engine.Actor:SetActorHiddenInGame", 1120, 0)
    coll = call(ed, "/Script/Engine.Actor:SetActorEnableCollision", 1400, 0)
    link(loc, "ReturnValue", burst, "Location")
    value(stop, "bStalking", "false")
    value(hide, "bNewHidden", "true")
    value(coll, "bNewActorEnableCollision", "false")
    for a, b in ((e, burst), (burst, tear), (tear, stop), (stop, hide), (hide, coll)):
        link(a, None, b, None)
    box(ed, "Vanish", "Black-sand burst, tear pulse, stop stalking, hide, stop colliding.", [e, loc, burst, tear, stop, hide, coll], "state")
    ed, e = fn(bp, "StalkTo", [("Target", BEL.get_object_reference_type(unreal.Actor))])
    s_t = at(ed.add_set_member_variable_node("StalkTarget", ""), 280, 0)
    s_on = at(ed.add_set_member_variable_node("bStalking", ""), 560, 0)
    link(e, None, s_t, None)
    link(e, "Target", s_t, "StalkTarget")
    link(s_t, None, s_on, None)
    value(s_on, "bStalking", "true")
    box(ed, "Stalk to", "Walk (slowly) toward Target until within AcceptRadius.", [e, s_t, s_on], "state")
    # Tick: stalk, then watch the player (head look-at pushed into the AnimBP; body turns while standing).
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    for n in list(ed.list_all_nodes()):
        ed.remove_nodes([n])
    for c in list(ed.list_comment_nodes()):
        ed.remove_comment_node(c)
    tick = at(BEL.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 0)), 0, 0)
    seq = at(ed.create_node_from_name(palette(ed, "Utilities|FlowControl|Sequence"), unreal.Vector2D(240, 0), []), 240, 0)
    link(tick, None, seq, None)
    # stalk group (row 0)
    st = at(ed.add_get_member_variable_node("bStalking", ""), 420, 140)
    br = at(ed.add_branch_node(), 640, 0)
    tgt = at(ed.add_get_member_variable_node("StalkTarget", ""), 640, 220)
    tl = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 860, 220)
    ml = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 860, 340)
    dv = call(ed, "/Script/Engine.KismetMathLibrary:Subtract_VectorVector", 1080, 260)
    flat = call(ed, "/Script/Engine.KismetMathLibrary:VSizeXY", 1300, 320)
    rad = at(ed.add_get_member_variable_node("AcceptRadius", ""), 1300, 420)
    far = call(ed, "/Script/Engine.KismetMathLibrary:Greater_DoubleDouble", 1520, 340)
    br2 = at(ed.add_branch_node(), 1740, 0)
    dirn = call(ed, "/Script/Engine.KismetMathLibrary:Normal", 1520, 220)
    move = call(ed, "/Script/Engine.Pawn:AddMovementInput", 2000, -40)
    arrive = at(ed.add_set_member_variable_node("bStalking", ""), 2000, 120)
    link(seq, "then_0", br, None)
    link(st, "bStalking", br, "Condition")
    link(br, "Then", br2, None)
    link(tgt, "StalkTarget", tl, "self")
    link(tl, "ReturnValue", dv, "A")
    link(ml, "ReturnValue", dv, "B")
    link(dv, "ReturnValue", flat, "A")
    link(flat, "ReturnValue", far, "A")
    link(rad, "AcceptRadius", far, "B")
    link(far, "ReturnValue", br2, "Condition")
    link(dv, "ReturnValue", dirn, "A")
    link(br2, "Then", move, None)
    link(dirn, "ReturnValue", move, "WorldDirection")
    link(br2, "Else", arrive, None)
    value(arrive, "bStalking", "false")
    box(ed, "Stalk", "While stalking, steer straight at StalkTarget; stop inside AcceptRadius.",
        [st, br, tgt, tl, ml, dv, flat, rad, far, br2, dirn, move, arrive], "state")
    # watch group (row 1): push look-at into the AnimBP, turn the body toward the player when standing
    Y = 700
    pawn = call(ed, "/Script/Engine.GameplayStatics:GetPlayerPawn", 420, Y + 200)
    pl = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 660, Y + 200)
    head = call(ed, "/Script/Engine.KismetMathLibrary:Add_VectorVector", 900, Y + 200)
    up = call(ed, "/Script/Engine.KismetMathLibrary:MakeVector", 660, Y + 300)  # +65 cm: eye height above the pawn's centre
    value(up, "Z", "65.0")
    link(up, "ReturnValue", head, "B")
    g_mesh = at(ed.add_get_member_variable_node("Mesh", ""), 420, Y + 380)
    inst = call(ed, "/Script/Engine.SkeletalMeshComponent:GetAnimInstance", 660, Y + 380)
    cast = at(ed.create_node_from_name(palette(ed, "CastToABP_FoAPlayer"), unreal.Vector2D(900, Y), []), 900, Y)
    s_loc = at(ed.add_set_member_variable_node("LookAtLocation", ABP_CLS), 1200, Y)
    s_w = at(ed.add_set_member_variable_node("LookAtWeight", ABP_CLS), 1480, Y)
    link(seq, "then_1", cast, None)
    link(pawn, "ReturnValue", pl, "self")
    link(pl, "ReturnValue", head, "A")
    link(g_mesh, "Mesh", inst, "self")
    link(inst, "ReturnValue", cast, "Object")
    as_pin = next(p for p in BEL.list_output_pins(cast) if str(unreal.BlueprintGraphPinLibrary.get_pin_name(p)).startswith("As"))
    link(cast, None, s_loc, None)
    link(head, "ReturnValue", s_loc, "LookAtLocation")
    link(s_loc, None, s_w, None)
    value(s_w, "LookAtWeight", "1.0")
    for n in (s_loc, s_w):
        assert unreal.BlueprintGraphPinLibrary.try_create_connection(as_pin, pin_in(n, "self")), "anim instance target"
    box(ed, "Watch the player", "Head look-at on the player's head, pushed into ABP_FoAPlayer every tick.",
        [pawn, pl, up, head, g_mesh, inst, cast, s_loc, s_w], "look")
    Y2 = 1260
    st2 = at(ed.add_get_member_variable_node("bStalking", ""), 420, Y2 + 140)
    br3 = at(ed.add_branch_node(), 660, Y2)
    me_loc = call(ed, "/Script/Engine.Actor:K2_GetActorLocation", 660, Y2 + 220)
    face = call(ed, "/Script/Engine.KismetMathLibrary:FindLookAtRotation", 900, Y2 + 220)
    cur = call(ed, "/Script/Engine.Actor:K2_GetActorRotation", 900, Y2 + 380)
    interp = call(ed, "/Script/Engine.KismetMathLibrary:RInterpTo", 1180, Y2 + 260)
    spd = at(ed.add_get_member_variable_node("TurnSpeed", ""), 1180, Y2 + 460)
    brk = call(ed, "/Script/Engine.KismetMathLibrary:BreakRotator", 1440, Y2 + 260)
    yaw_only = call(ed, "/Script/Engine.KismetMathLibrary:MakeRotator", 1660, Y2 + 260)
    setrot = call(ed, "/Script/Engine.Actor:K2_SetActorRotation", 1900, Y2)
    if len(BEL.list_output_pins(seq)) < 3:  # a fresh Sequence has two outputs
        ed.add_node_pin(seq)
    link(seq, "then_2", br3, None)
    link(st2, "bStalking", br3, "Condition")
    link(br3, "Else", setrot, None)
    link(me_loc, "ReturnValue", face, "Start")
    link(pl, "ReturnValue", face, "Target")
    link(cur, "ReturnValue", interp, "Current")
    link(face, "ReturnValue", interp, "Target")
    link(tick, "DeltaSeconds", interp, "DeltaTime")
    link(spd, "TurnSpeed", interp, "InterpSpeed")
    link(interp, "ReturnValue", brk, "InRot")
    link(brk, "Yaw", yaw_only, "Yaw")
    link(yaw_only, "ReturnValue", setrot, "NewRotation")
    box(ed, "Face the player", "Standing still, the body slowly turns to the player (the AnimBP shuffles its feet in TurnInPlace).",
        [st2, br3, me_loc, face, cur, interp, spd, brk, yaw_only, setrot], "anim")
    box(ed, "Tick", "Stalk, watch, face: in that order every frame.", [tick, seq], "util")
    EAL.save_loaded_asset(bp, False)
    print("nightmare graphs saved (compile with Hayba next)")


{"vars": step_vars, "graphs": step_graphs, "api": step_api, "defaults": step_defaults}[os.environ["FOA_STEP"]]()
