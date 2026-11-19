"""BPC_Interactor: finds the best interactable every 0.1 s (timer, no Tick), drives the prompt and the focus highlight,
and runs the player's Interact and CycleVerb input. Runs INSIDE the editor (rebuilds its graphs in place):
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/build_interactor.py
Dispatchers (UI lane binds them):
  OnFocusChanged(Target: Actor, Prompt: Text, Verbs: Name array, VerbIndex: int)   None/empty = nothing in focus
  OnNarration(Line: Text)                                                         one sincere line after an action
Called by interactables: Narrate(Line), PlayMontage(Montage soft ref), Report(Event).  GetFocusedActor() for look-at.
Focus highlight: custom depth stencil 3 on the target's primitives (the post-process lane draws the soft rim)."""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay")
import gp  # noqa: E402

importlib.reload(gp)
G, T, KSL, KML, KAL, GS, KTL = gp.G, gp.T, gp.KSL, gp.KML, gp.KAL, gp.GS, gp.KTL
EAL, BEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary


def build():
    bp = gp.asset("BPC_Interactor")
    gp.close(bp)
    inv_cls = gp.gen("BPC_Inventory")
    name, text, real, boolean, integer = T("name"), T("text"), T("real"), T("bool"), T("int")
    gp.ensure_vars(bp, [("Reach", real, "170.0", True), ("Radius", real, "18.0", True),
                        ("FullLine", text, "Four things already. One person can only carry so much before breakfast.",
                         True)], "Interactor")
    gp.ensure_vars(bp, [("Target", T(unreal.Actor), "", False), ("Prompt", text, "", False),
                        ("Verb", name, "Look", False), ("Verbs", BEL.get_array_type(name), "", False),
                        ("bLookMode", boolean, "false", False), ("Inventory", T(inv_cls), "", False)],
                   "Interactor|State")
    gp.ensure_dispatcher(bp, "OnFocusChanged", [("Target", T(unreal.Actor)), ("Prompt", text),
                                                ("Verbs", BEL.get_array_type(name)), ("VerbIndex", integer)])
    gp.ensure_dispatcher(bp, "OnNarration", [("Line", text)])
    gp.ensure_dispatcher(bp, "OnBeatEvent", [("Event", name)])
    BEL.compile_blueprint(bp)
    inv = inv_cls.get_path_name()
    me = bp.generated_class().get_path_name()
    if "PlayMontage" in [str(n) for n in BEL.list_graph_names(bp)]:  # one-time: replaced by PlayRowMontage (typed soft ref)
        BEL.remove_function_graph(bp, "PlayMontage")
        BEL.compile_blueprint(bp)
    SIGS = {  # every function signature, declared up front so graphs can call each other in any order
        "GetFocusedActor": gp.sig([], [("Target", T(unreal.Actor))], pure=True),
        "Narrate": gp.sig([("Line", text)], []),
        "PlayRowMontage": gp.sig([], []),  # its soft-ref input is typed from a real pin below
        "Report": gp.sig([("Event", name)], []),
        "Highlight": gp.sig([("Actor", T(unreal.Actor)), ("bOn", boolean)], []),
        "FindBest": gp.sig([], [("Best", T(unreal.Actor))],
                           locals_=[("BestActor", T(unreal.Actor), ""), ("BestCost", real, "1000000.0"),
                                    ("Index", integer, "0")]),
        "SetFocus": gp.sig([("NewTarget", T(unreal.Actor))], []),
        "Refresh": gp.sig([("bForce", boolean)], []),
        "Interact": gp.sig([], []),
        "CycleVerb": gp.sig([], []),
        "Scan": gp.sig([], []),
        "SetSuspended": gp.sig([("bSuspended", boolean)], []),
    }
    gp.declare(bp, SIGS)

    # ---- GetFocusedActor (pure) ----
    g = G.function(bp, "GetFocusedActor", **SIGS["GetFocusedActor"])
    e = g.entry(0, 0)
    r = g.ret(300, 0)
    g.link(e, None, r, None)
    g.link(g.get("Target", 60, 140), "", r, "Target")
    g.box("Focused actor", "What the player is looking at (the player lane aims the head at it).", g.nodes, "data")

    # ---- Narrate ----
    g = G.function(bp, "Narrate", **SIGS["Narrate"])
    e = g.entry(0, 0)
    empty = g.call(KTL + ":TextIsEmpty", 240, 160)
    g.link(e, "Line", empty, "InText")
    br = g.branch(480, 0)
    g.link(e, None, br, None)
    g.link(empty, "ReturnValue", br, "Condition")
    say = g.pal(740, 40, "Call", "OnNarration")
    g.link(br, "Else", say, None)
    g.link(e, "Line", say, "Line")
    g.box("Narrate", "One sincere line for the HUD subtitle; empty lines (state-only rows) say nothing.", g.nodes, "out")

    # ---- PlayMontage (soft ref, so a missing AM_FoA_* never breaks a compile) ----
    g = G.function(bp, "PlayRowMontage", **SIGS["PlayRowMontage"])
    e = g.entry(0, 0)
    valid = g.call(KSL + ":IsValidSoftObjectReference", 240, 180)
    if "Montage" not in [str(gp.PIN.get_pin_name(p)) for p in BEL.list_output_pins(e)]:
        # Python cannot build a Soft Object (Object) pin type, so copy it from this node's input.
        g.ed.add_graph_input_parameter("Montage", gp.PIN.get_pin_type(g.pin(valid, "SoftObjectReference", False)))
    g.link(e, "Montage", valid, "SoftObjectReference")
    br = g.branch(500, 0)
    g.link(e, None, br, None)
    g.link(valid, "ReturnValue", br, "Condition")
    load = g.call(KSL + ":LoadAsset_Blocking", 740, 0)
    g.link(e, "Montage", load, "Asset")
    g.link(br, "Then", load, None)
    as_m = g.pal(1020, 0, "Cast To AnimMontage")
    g.link(load, None, as_m, None)
    g.link(load, "ReturnValue", as_m, "Object")
    owner = g.call("/Script/Engine.ActorComponent:GetOwner", 1020, 220)
    # No Blueprint class here: casting to BP_FoAPlayer made a load cycle with the character that owns this component
    # ("Custom Property List Not Initialized" on every map load). Engine Character plays; the host locks input.
    as_p = g.pal(1320, 0, "Cast To Character")
    play = g.call("/Script/Engine.Character:PlayAnimMontage", 1640, 0)
    g.link(as_p, gp.cast_out(as_p), play, "self")
    g.link(as_m, gp.cast_out(as_m), play, "AnimMontage")
    g.link(as_m, None, as_p, None)
    g.link(owner, "ReturnValue", as_p, "Object")
    g.link(as_p, None, play, None)
    lock = g.pal(1960, 0, "InteractionHost", "LockForInteraction", "Message")
    g.link(owner, "ReturnValue", lock, "self")
    g.link(play, "ReturnValue", lock, "Seconds")
    g.link(g.get("Target", 1640, 260), "", lock, "Target")  # the focused interactable: the host turns onto it
    g.link(play, None, lock, None)
    g.box("Play the interaction montage", "", g.nodes, "fx")

    # ---- Report: the one hand-off to the flow lane ----
    g = G.function(bp, "Report", **SIGS["Report"])
    e = g.entry(0, 0)
    some = g.call(KML + ":NotEqual_NameName", 240, 160, B="None")
    g.link(e, "Event", some, "A")
    br = g.branch(480, 0)
    g.link(e, None, br, None)
    g.link(some, "ReturnValue", br, "Condition")
    # A dispatcher, not a call: BP_BeatDirector references BP_FoAPlayer, which owns this component, so a direct
    # call made a load cycle. The director binds OnBeatEvent once at BeginPlay and forwards it to ReportEvent.
    fire = g.pal(740, 40, "Call", "OnBeatEvent")
    g.link(br, "Then", fire, None)
    g.link(e, "Event", fire, "Event")
    g.box("Report a beat event", "", g.nodes, "out")

    # ---- Highlight(Actor, bOn): custom depth stencil 3 ----
    g = G.function(bp, "Highlight", **SIGS["Highlight"])
    e = g.entry(0, 0)
    ok = g.call(KSL + ":IsValid", 240, 160)
    g.link(e, "Actor", ok, "Object")
    br = g.branch(460, 0)
    g.link(e, None, br, None)
    g.link(ok, "ReturnValue", br, "Condition")
    mesh = g.call("/Script/Engine.Actor:GetComponentByClass", 700, 200,
                  ComponentClass="/Script/Engine.StaticMeshComponent")
    g.link(e, "Actor", mesh, "self")
    depth = g.call("/Script/Engine.PrimitiveComponent:SetRenderCustomDepth", 1300, 0)
    stencil = g.call("/Script/Engine.PrimitiveComponent:SetCustomDepthStencilValue", 1600, 0)
    three = g.call(KML + ":SelectInt", 1340, 240, A=3, B=0)
    g.link(e, "bOn", three, "bPickA")
    g.link(e, "bOn", depth, "bValue")
    g.link(three, "ReturnValue", stencil, "Value")
    g.link(mesh, "ReturnValue", depth, "self")
    g.link(mesh, "ReturnValue", stencil, "self")
    g.link(br, "Then", mesh, None) if g.impure(mesh) else None
    g.flow(br, mesh, depth, stencil) if not g.impure(mesh) else g.flow(mesh, depth, stencil)
    g.box("Focus highlight", "Custom stencil 3 on the focused actor's mesh; the dream post-process draws it as a soft "
          "rim (1 or 4+ keep colour, 2 is the tear glitch).", g.nodes, "fx")

    # ---- FindBest: camera-forward sphere sweep, lowest angle + distance cost wins ----
    g = G.function(bp, "FindBest", **SIGS["FindBest"])
    e = g.entry(0, 0)
    cam = g.call(GS + ":GetPlayerCameraManager", 0, 200, PlayerIndex=0)
    cam_loc = g.call("/Script/Engine.PlayerCameraManager:GetCameraLocation", 260, 200)
    cam_rot = g.call("/Script/Engine.PlayerCameraManager:GetCameraRotation", 260, 300)
    g.link(cam, "ReturnValue", cam_loc, "self")
    g.link(cam, "ReturnValue", cam_rot, "self")
    fwd = g.call(KML + ":GetForwardVector", 520, 300)
    g.link(cam_rot, "ReturnValue", fwd, "InRot")
    owner = g.call("/Script/Engine.ActorComponent:GetOwner", 0, 420)
    pawn_loc = g.call("/Script/Engine.Actor:K2_GetActorLocation", 240, 420)
    g.link(owner, "ReturnValue", pawn_loc, "self")
    back = g.call(KML + ":Vector_Distance", 520, 420)
    g.link(cam_loc, "ReturnValue", back, "V1")
    g.link(pawn_loc, "ReturnValue", back, "V2")
    length = g.call(KML + ":Add_DoubleDouble", 760, 420)
    g.link(back, "ReturnValue", length, "A")
    g.link(g.get("Reach", 560, 520), "", length, "B")
    ray = g.call(KML + ":Multiply_VectorFloat", 980, 300)
    g.link(fwd, "ReturnValue", ray, "A")
    g.link(length, "ReturnValue", ray, "B")
    end = g.call(KML + ":Add_VectorVector", 1200, 240)
    g.link(cam_loc, "ReturnValue", end, "A")
    g.link(ray, "ReturnValue", end, "B")
    types = g.pal(1200, 420, "Make Array")
    trace = g.call(KSL + ":SphereTraceMultiForObjects", 1460, 0, bTraceComplex=True, bIgnoreSelf=True)
    g.link(types, "Array", trace, "ObjectTypes")
    g.ed.add_node_pin(types)
    g.val(types, "[0]", "ObjectTypeQuery1")  # WorldStatic (converted props)
    g.val(types, "[1]", "ObjectTypeQuery2")  # WorldDynamic (Blueprint meshes)
    g.link(cam_loc, "ReturnValue", trace, "Start")
    g.link(end, "ReturnValue", trace, "End")
    g.link(g.get("Radius", 1240, 560), "", trace, "Radius")
    # A direct visible surface wins; the forgiving sweep still handles near misses.
    direct = g.call(KSL + ":LineTraceSingleForObjects", 1000, -650, bTraceComplex=True, bIgnoreSelf=True)
    for pin, node, output in (("Start", cam_loc, "ReturnValue"), ("End", end, "ReturnValue"), ("ObjectTypes", types, "Array")):
        g.link(node, output, direct, pin)
    g.link(e, None, direct, None)
    g.link(direct, None, trace, None)
    direct_hit = g.call(GS + ":BreakHitResult", 1400, -650)
    g.link(direct, "OutHit", direct_hit, "Hit")
    g.box("Camera-forward sweep", "From the camera through the player and Reach beyond it, every WorldStatic and "
          "WorldDynamic hit (complex collision, so small Lux3D pickups count).", list(g.nodes), "event")
    first = len(g.nodes)
    start, more, elem, step = g.loop(trace, "OutHits", 1760, 0)
    g.link(trace, None, start, None)
    hit = g.call(GS + ":BreakHitResult", 1800, 700)
    g.link(elem, "Item", hit, "Hit")
    is_i = g.call(KSL + ":DoesImplementInterface", 2140, 260, Interface=gp.BPI)
    g.link(hit, "HitActor", is_i, "TestObject")
    dist = g.call(KML + ":Vector_Distance", 2140, 400)
    g.link(pawn_loc, "ReturnValue", dist, "V1")
    g.link(hit, "ImpactPoint", dist, "V2")
    near = g.call(KML + ":LessEqual_DoubleDouble", 2380, 400)
    g.link(dist, "ReturnValue", near, "A")
    g.link(g.get("Reach", 2160, 520), "", near, "B")
    rel = g.call(KML + ":Subtract_VectorVector", 2140, 640)
    g.link(hit, "ImpactPoint", rel, "A")
    g.link(pawn_loc, "ReturnValue", rel, "B")
    ahead_dot = g.call(KML + ":Dot_VectorVector", 2380, 640)
    g.link(rel, "ReturnValue", ahead_dot, "A")
    g.link(fwd, "ReturnValue", ahead_dot, "B")
    ahead = g.call(KML + ":Greater_DoubleDouble", 2600, 640, B=0.0)
    g.link(ahead_dot, "ReturnValue", ahead, "A")
    aim = g.call(KML + ":Subtract_VectorVector", 2140, 800)
    g.link(hit, "ImpactPoint", aim, "A")
    g.link(cam_loc, "ReturnValue", aim, "B")
    aim_n = g.call(KML + ":Normal", 2380, 800)
    g.link(aim, "ReturnValue", aim_n, "A")
    cosang = g.call(KML + ":Dot_VectorVector", 2600, 800)
    g.link(aim_n, "ReturnValue", cosang, "A")
    g.link(fwd, "ReturnValue", cosang, "B")
    deg = g.call(KML + ":DegAcos", 2820, 800)
    g.link(cosang, "ReturnValue", deg, "A")
    frac = g.call(KML + ":Divide_DoubleDouble", 2600, 960)
    g.link(dist, "ReturnValue", frac, "A")
    g.link(g.get("Reach", 2380, 1000), "", frac, "B")
    weigh = g.call(KML + ":Multiply_DoubleDouble", 2820, 960, B=5.0)
    g.link(frac, "ReturnValue", weigh, "A")
    cost = g.call(KML + ":Add_DoubleDouble", 3040, 860)
    g.link(deg, "ReturnValue", cost, "A")
    g.link(weigh, "ReturnValue", cost, "B")
    exact = g.call(KML + ":EqualEqual_ObjectObject", 2820, 1200)
    g.link(direct_hit, "HitActor", exact, "A")
    g.link(hit, "HitActor", exact, "B")
    bonus = g.call(KML + ":SelectFloat", 3040, 1200, A=180.0, B=0.0)
    g.link(exact, "ReturnValue", bonus, "bPickA")
    ray_cost = g.call(KML + ":Subtract_DoubleDouble", 3260, 1200)
    g.link(cost, "ReturnValue", ray_cost, "A")
    g.link(bonus, "ReturnValue", ray_cost, "B")
    better = g.call(KML + ":Less_DoubleDouble", 3260, 860)
    g.link(ray_cost, "ReturnValue", better, "A")
    g.link(g.lget("BestCost", 3040, 1000), "", better, "B")
    every = g.call(KML + ":BooleanAND", 3480, 300)
    for _ in range(2):
        g.ed.add_node_pin(every)
    g.link(is_i, "ReturnValue", every, "A")
    g.link(near, "ReturnValue", every, "B")
    g.link(ahead, "ReturnValue", every, "C")
    g.link(better, "ReturnValue", every, "D")
    br = g.branch(3700, 0)
    g.link(more, "Then", br, None)
    g.link(every, "ReturnValue", br, "Condition")
    g.link(br, "Else", step, None)
    s_best = g.lset("BestActor", 3940, 0)
    g.link(hit, "HitActor", s_best, "BestActor")
    s_cost = g.lset("BestCost", 4200, 0)
    g.link(ray_cost, "ReturnValue", s_cost, "BestCost")
    g.link(br, "Then", s_best, None)
    g.chain(s_best, s_cost)
    g.link(s_cost, None, step, None)
    g.box("Score every hit", "Keep interactables within Reach of the player and in front of them; cost = degrees off "
          "the camera ray + 5 x distance / Reach, lowest wins (aim first, nearness breaks ties).",
          g.nodes[first:], "logic")
    r = g.ret(2400, -260)
    g.link(more, "Else", r, None)
    g.link(g.lget("BestActor", 1560, -180), "", r, "Best")
    g.box("Result", "None when nothing interactable is in reach.", g.nodes[-2:], "data")

    # ---- SetFocus(NewTarget): highlight swap ----
    g = G.function(bp, "SetFocus", **SIGS["SetFocus"])
    e = g.entry(0, 0)
    same = g.call(KML + ":EqualEqual_ObjectObject", 240, 160)
    g.link(e, "NewTarget", same, "A")
    g.link(g.get("Target", 20, 220), "", same, "B")
    br = g.branch(480, 0)
    g.link(e, None, br, None)
    g.link(same, "ReturnValue", br, "Condition")
    off = g.selfcall("Highlight", 740, 0, bOn=False)
    g.link(g.get("Target", 520, 200), "", off, "Actor")
    s_t = g.set("Target", 1040, 0)
    g.link(e, "NewTarget", s_t, "Target")
    s_l = g.set("bLookMode", 1300, 0, value=False)
    on = g.selfcall("Highlight", 1560, 0, bOn=True)
    g.link(e, "NewTarget", on, "Actor")
    ref = g.selfcall("Refresh", 1860, 0, bForce=True)
    g.link(br, "Else", off, None)
    g.chain(off, s_t, s_l, on, ref)
    g.box("Change focus", "Only on a new target: move the stencil highlight, reset to the action verb, re-send the "
          "prompt.", g.nodes, "state")

    # ---- Refresh(bForce): verbs, prompt, OnFocusChanged ----
    g = G.function(bp, "Refresh", **SIGS["Refresh"])
    e = g.entry(0, 0)
    held = g.call(inv + ":GetHeld", 0, 240)
    g.link(g.get("Inventory", -220, 260), "", held, "self")
    can_take = g.msg("CanInteract", 260, 0)
    g.link(g.get("Target", 20, 400), "", can_take, "self")
    g.val(can_take, "Verb", "Take")
    g.link(held, "Item", can_take, "HeldItem")
    can_use = g.msg("CanInteract", 560, 0)
    g.link(g.get("Target", 340, 400), "", can_use, "self")
    g.val(can_use, "Verb", "Use")
    g.link(held, "Item", can_use, "HeldItem")
    g.chain(e, can_take, can_use)
    use_or = g.call(KML + ":SelectName", 860, 240, A="Use", B="None")
    g.link(can_use, gp.ret_pin(can_use), use_or, "bPickA")
    primary = g.call(KML + ":SelectName", 1080, 240, A="Take")
    g.link(use_or, "ReturnValue", primary, "B")
    g.link(can_take, gp.ret_pin(can_take), primary, "bPickA")
    g.box("Which verbs?", "Take, else Use (the held item, or the bare hand), and Look always.", list(g.nodes), "logic")
    first = len(g.nodes)
    clear = g.call(KAL + ":Array_Clear", 1360, 0)
    g.link(g.get("Verbs", 1160, 100), "", clear, "TargetArray")
    has_t = g.call(KSL + ":IsValid", 1360, 200)
    g.link(g.get("Target", 1160, 260), "", has_t, "Object")
    b_t = g.branch(1620, 0)
    g.link(has_t, "ReturnValue", b_t, "Condition")
    some = g.call(KML + ":NotEqual_NameName", 1620, 220, B="None")
    g.link(primary, "ReturnValue", some, "A")
    b_p = g.branch(1860, 0)
    g.link(some, "ReturnValue", b_p, "Condition")
    add_p = g.call(KAL + ":Array_Add", 2100, -40)
    g.link(g.get("Verbs", 1900, -120), "", add_p, "TargetArray")
    g.link(primary, "ReturnValue", add_p, "NewItem")
    add_l = g.call(KAL + ":Array_Add", 2380, 120)
    g.link(g.get("Verbs", 2180, 240), "", add_l, "TargetArray")
    g.val(add_l, "NewItem", "Look")  # after the array link types the wildcard
    g.link(can_use, None, clear, None)
    g.chain(clear, b_t)
    g.link(b_t, "Then", b_p, None)
    g.link(b_p, "Then", add_p, None)
    g.link(add_p, None, add_l, None)
    g.link(b_p, "Else", add_l, None)
    g.box("Verb list", "[Take or Use, Look], or [Look]; empty when nothing is in focus.", g.nodes[first:], "state")
    first = len(g.nodes)
    lookish = g.call(KML + ":BooleanOR", 2660, 260)
    g.link(g.get("bLookMode", 2440, 300), "", lookish, "A")
    no_p = g.call(KML + ":EqualEqual_NameName", 2440, 400, B="None")
    g.link(primary, "ReturnValue", no_p, "A")
    g.link(no_p, "ReturnValue", lookish, "B")
    verb = g.call(KML + ":SelectName", 2880, 260, A="Look")
    g.link(primary, "ReturnValue", verb, "B")
    g.link(lookish, "ReturnValue", verb, "bPickA")
    s_v = g.set("Verb", 3120, 0)
    g.link(verb, "ReturnValue", s_v, "Verb")
    prompt = g.msg("GetPrompt", 3380, 0)
    g.link(g.get("Target", 3180, 200), "", prompt, "self")
    same = g.call(KTL + ":EqualEqual_TextText", 3640, 200)
    g.link(prompt, gp.ret_pin(prompt), same, "A")
    g.link(g.get("Prompt", 3420, 320), "", same, "B")
    changed = g.call(KML + ":Not_PreBool", 3860, 200)
    g.link(same, "ReturnValue", changed, "A")
    send = g.call(KML + ":BooleanOR", 4080, 200)
    g.link(changed, "ReturnValue", send, "A")
    g.link(e, "bForce", send, "B")
    b_s = g.branch(4300, 0)
    g.link(send, "ReturnValue", b_s, "Condition")
    s_p = g.set("Prompt", 4540, 0)
    g.link(prompt, gp.ret_pin(prompt), s_p, "Prompt")
    idx = g.call(KML + ":SelectInt", 4540, 220, A=1, B=0)
    look_idx = g.call(KML + ":BooleanAND", 4320, 340)
    g.link(g.get("bLookMode", 4100, 360), "", look_idx, "A")
    g.link(some, "ReturnValue", look_idx, "B")
    g.link(look_idx, "ReturnValue", idx, "bPickA")
    fire = g.pal(4800, 0, "Call", "OnFocusChanged")
    g.link(g.get("Target", 4580, 380), "", fire, "Target")
    g.link(s_p, "Output_Get", fire, "Prompt")
    g.link(g.get("Verbs", 4580, 460), "", fire, "Verbs")
    g.link(idx, "ReturnValue", fire, "VerbIndex")
    g.link(add_l, None, s_v, None)
    g.link(b_t, "Else", s_v, None)
    g.chain(s_v, prompt, b_s)
    g.link(b_s, "Then", s_p, None)
    g.chain(s_p, fire)
    g.box("Prompt out", "The current verb (Look in look mode or when there is no action), the target's own sentence, "
          "and OnFocusChanged when it changed or a refresh is forced.", g.nodes[first:], "out")

    # ---- Interact / CycleVerb / Scan ----
    g = G.function(bp, "Interact", **SIGS["Interact"])
    e = g.entry(0, 0)
    ok = g.call(KSL + ":IsValid", 220, 180)
    g.link(g.get("Target", 0, 220), "", ok, "Object")
    br = g.branch(460, 0)
    g.link(e, None, br, None)
    g.link(ok, "ReturnValue", br, "Condition")
    take = g.call(KML + ":EqualEqual_NameName", 460, 200, B="Take")
    g.link(g.get("Verb", 260, 300), "", take, "A")
    full = g.call(inv + ":IsFull", 460, 340)
    g.link(g.get("Inventory", 260, 400), "", full, "self")
    refuse = g.call(KML + ":BooleanAND", 700, 240)
    g.link(take, "ReturnValue", refuse, "A")
    g.link(full, "bFull", refuse, "B")
    br2 = g.branch(940, 0)
    g.link(br, "Then", br2, None)
    g.link(refuse, "ReturnValue", br2, "Condition")
    say = g.selfcall("Narrate", 1200, -140)
    g.link(g.get("FullLine", 1000, -60), "", say, "Line")
    act = g.msg("Interact", 1200, 60)
    g.link(g.get("Target", 980, 200), "", act, "self")
    g.link(g.get("Verb", 980, 280), "", act, "Verb")
    held = g.call(inv + ":GetHeld", 980, 380)
    g.link(g.get("Inventory", 760, 420), "", held, "self")
    g.link(held, "Item", act, "HeldItem")
    ref = g.selfcall("Refresh", 1520, 0, bForce=False)
    g.link(br2, "Then", say, None)
    g.link(br2, "Else", act, None)
    g.link(say, None, ref, None)
    g.link(act, None, ref, None)
    g.box("Interact", "Send the current verb and held item to the target; a full inventory politely refuses a Take.",
          g.nodes, "event")

    g = G.function(bp, "CycleVerb", **SIGS["CycleVerb"])
    e = g.entry(0, 0)
    flip = g.call(KML + ":Not_PreBool", 240, 160)
    g.link(g.get("bLookMode", 20, 200), "", flip, "A")
    s = g.set("bLookMode", 460, 0)
    g.link(flip, "ReturnValue", s, "bLookMode")
    ref = g.selfcall("Refresh", 720, 0, bForce=True)
    g.chain(e, s, ref)
    g.box("Cycle verb", "Toggle between the action verb and Look.", g.nodes, "event")

    g = G.function(bp, "Scan", **SIGS["Scan"])
    e = g.entry(0, 0)
    best = g.selfcall("FindBest", 240, 0)
    focus = g.selfcall("SetFocus", 520, 0)
    g.link(best, "Best", focus, "NewTarget")
    ref = g.selfcall("Refresh", 820, 0, bForce=False)
    g.chain(e, best, focus, ref)
    g.box("Scan (every 0.1 s)", "Find the best target, move the focus, refresh the prompt.", g.nodes, "event")

    # ---- SetSuspended(bSuspended): cinematics (BP_FoAPlayer.SetCinematic) pause the scan and drop the focus ----
    g = G.function(bp, "SetSuspended", **SIGS["SetSuspended"])
    e = g.entry(0, 0)
    br = g.branch(240, 0)
    g.link(e, None, br, None)
    g.link(e, "bSuspended", br, "Condition")
    pause = g.call(KSL + ":K2_PauseTimer", 480, -120, FunctionName="Scan")
    clear = g.selfcall("SetFocus", 800, -120)
    ref = g.selfcall("Refresh", 1100, -120, bForce=True)
    resume = g.call(KSL + ":K2_UnPauseTimer", 480, 140, FunctionName="Scan")
    g.link(br, "Then", pause, None)
    g.chain(pause, clear, ref)
    g.link(br, "Else", resume, None)
    g.box("Suspend for cinematics", "", g.nodes, "event")

    # ---- Event graph: start the scan timer, route input ----
    g = G(bp).clear()
    begin = g.event("ReceiveBeginPlay", 0, 0)
    owner = g.call("/Script/Engine.ActorComponent:GetOwner", 0, 200)
    find_inv = g.call("/Script/Engine.Actor:GetComponentByClass", 260, 200, ComponentClass=inv_cls.get_path_name())
    g.link(owner, "ReturnValue", find_inv, "self")
    s_inv = g.set("Inventory", 560, 0)
    g.link(find_inv, "ReturnValue", s_inv, "Inventory")
    timer = g.call(KSL + ":K2_SetTimer", 840, 0, FunctionName="Scan", Time=0.1, bLooping=True)
    g.flow(begin, find_inv, s_inv, timer)
    g.box("Start", "Find the player's inventory and scan for targets 10 times a second (a timer, not Tick).",
          g.nodes, "event")
    first = len(g.nodes)
    ia = g.pal(0, 420, "Input", "IA_Interact")
    do = g.selfcall("Interact", 360, 420)
    g.link(ia, "Started", do, None)
    ib = g.pal(0, 640, "Input", "IA_CycleVerb")
    cy = g.selfcall("CycleVerb", 360, 640)
    g.link(ib, "Started", cy, None)
    g.box("Input", "E or gamepad face bottom uses the prompt's verb; Q or face top cycles Look and the action.",
          g.nodes[first:], "event")

    pacing_gi = gp.asset('GI_FoA')
    if pacing_gi and 'CanReportInteractionEvent' in [str(n) for n in BEL.list_graph_names(pacing_gi)]:
        import runpy
        from pathlib import Path
        previous_phase = os.environ.get('FOA_PHASE')
        try:
            os.environ['FOA_PHASE'] = 'report_hook'
            runpy.run_path(str(Path(__file__).with_name('build_interaction_pacing.py')), run_name='__main__')
        finally:
            if previous_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = previous_phase
    ok = BEL.compile_blueprint(bp)
    gp.save(bp)
    graphs = ["EventGraph", "Scan", "SetSuspended", "FindBest", "SetFocus", "Refresh", "Interact", "CycleVerb", "Highlight",
              "Narrate", "PlayRowMontage", "Report", "GetFocusedActor"]
    print("BPC_Interactor compiled", ok, "errors", [(n, G(bp, n).errors()) for n in graphs if G(bp, n).errors()])
    print("shots", gp.capture(bp, graphs, "BPC_Interactor"))


build()
