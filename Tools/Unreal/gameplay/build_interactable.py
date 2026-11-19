"""BP_Interactable (base) and the presets of its four children. Runs INSIDE the editor:
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/build_interactable.py FOA_STEP=components|graphs|children
The base does all the work, so puzzles are data, not classes:
  BeginPlay      copies the DT_Interactions rows whose Interactable = InteractionKey, attaches Carried actors to the
                 Pivot, remembers the morning State and shows it.
  Interact       Resolve(Verb, HeldItem) -> ApplyRow: new State, narration, Give, UseUp, montage, beat event, OnUsed.
  SetState       ApplyState (HiddenStates hide the actor; Poses move the Pivot, animated with MoveComponentTo) and
                 sends Interact(Notify, NewState) to every Linked actor. A finished move sends Notify(Arrived) to self.
  GetPrompt / CanInteract read the same rows, so the prompt always names what Use will do.
Children only change defaults: BP_Pickup hides when Hidden or Taken, BP_Container opens by its per-instance Poses,
BP_Door starts Locked, BP_Topple falls with an accelerating (ease-in only) move and then blocks the doorway."""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/gameplay")
import gp  # noqa: E402

importlib.reload(gp)
G, T, KSL, KML, KAL, GS = gp.G, gp.T, gp.KSL, gp.KML, gp.KAL, gp.GS
EAL, BEL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary
DTI = gp.D + "/DT_Interactions.DT_Interactions"
GI = gp.D + "/GI_FoA"
SANDFX = "/Game/FoA/VFX/Sand/BPL_SandFX"  # sandvfx lane; the burst call is compiled in only once it exists


def step_components():
    bp = gp.asset("BP_Interactable")
    gp.close(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    by_name = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
    for name, cls, parent in (("Pivot", unreal.SceneComponent, "DefaultSceneRoot"),
                              ("Mesh", unreal.StaticMeshComponent, "Pivot")):
        if name not in by_name:
            h, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(
                parent_handle=by_name[parent], new_class=cls, blueprint_context=bp))
            assert not str(fail), fail
            sds.rename_subobject(h, name)
            by_name[name] = h
    BEL.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("tags", ["Interactable"])  # the player lane's look-at scan uses this tag
    gp.save(bp)
    print("components", sorted(by_name))


def step_graphs():
    bp = gp.asset("BP_Interactable")
    gp.close(bp)
    row_t = T(unreal.load_asset(gp.D + "/S_Interaction"))
    name, real, boolean = T("name"), T("real"), T("bool")
    actors = BEL.get_array_type(T(unreal.Actor))
    names = BEL.get_array_type(name)
    poses = BEL.get_map_type(name, T(unreal.Transform))
    gp.ensure_vars(bp, [("InteractionKey", name, "None", True), ("State", name, "Idle", True),
                        ("HiddenStates", names, "", True), ("Poses", poses, "", True),
                        ("Carried", actors, "", True), ("Linked", actors, "", True),
                        ("MoveTime", real, "0.6", True), ("bEaseOut", boolean, "true", True),
                        ("StateSounds", BEL.get_map_type(name, T(unreal.SoundBase)), "", True),
                        ("BurstStates", BEL.get_map_type(name, real), "", True)], "Interactable")
    gp.ensure_vars(bp, [("Rows", BEL.get_array_type(row_t), "", False), ("MorningState", name, "None", False),
                        ("PivotGoal", T(unreal.Transform), "", False)], "Interactable|State")
    gp.ensure_dispatcher(bp, "OnUsed", [("Interactable", T(unreal.Actor)), ("Verb", name), ("NewState", name)])
    BEL.compile_blueprint(bp)
    inter = gp.gen("BPC_Interactor").get_path_name()
    inv = gp.gen("BPC_Inventory").get_path_name()
    SIGS = {  # every function signature, declared up front so graphs can call each other in any order
        "GetInteractor": gp.sig([], [("Interactor", T(gp.gen("BPC_Interactor")))], pure=True),
        "Knows": gp.sig([("Flag", name)], [("bKnows", boolean)], pure=True),
        "FindRow": gp.sig([("Verb", name), ("Item", name)], [("bFound", boolean), ("Row", row_t)], pure=True,
                          locals_=[("Index", T("int"), "0")]),
        "Resolve": gp.sig([("Verb", name), ("Held", name)], [("bFound", boolean), ("Row", row_t)], pure=True),
        "ApplyState": gp.sig([("NewState", name), ("bInstant", boolean)], []),
        "SetState": gp.sig([("NewState", name), ("bInstant", boolean)], [], locals_=[("Index", T("int"), "0")]),
        "ApplyRow": gp.sig([("Row", row_t)], []),
        "LoadRows": gp.sig([], [], locals_=[("Index", T("int"), "0")]),
        "AttachCarried": gp.sig([], [], locals_=[("Index", T("int"), "0")]),
        "PlayFeedback": gp.sig([("NewState", name)], []),
    }
    gp.declare(bp, SIGS, events=["AnimatePivot"])

    def brk(g, x, y, src_node, src_pin):
        b = g.pal(x, y, "Break", "S_Interaction")
        g.link(src_node, src_pin, b, "S_Interaction")
        return b

    def f(b, field):
        return gp.find_pin_name(b, field)

    # ---- GetInteractor (pure) ----
    g = G.function(bp, "GetInteractor", **SIGS["GetInteractor"])
    e = g.entry(0, 0)
    pawn = g.call(GS + ":GetPlayerPawn", 0, 160, PlayerIndex=0)
    comp = g.call("/Script/Engine.Actor:GetComponentByClass", 240, 160, ComponentClass=inter)
    g.link(pawn, "ReturnValue", comp, "self")
    r = g.ret(540, 0)
    g.flow(e, comp, r)
    g.link(comp, "ReturnValue", r, "Interactor")
    g.box("Player's interactor", "Narration, montages, beat events and the inventory all go through it.", g.nodes,
          "data")

    # ---- Knows(Flag) (pure): knowledge-gated rows ----
    g = G.function(bp, "Knows", **SIGS["Knows"])
    e = g.entry(0, 0)
    none = g.call(KML + ":EqualEqual_NameName", 240, 160, B="None")
    g.link(e, "Flag", none, "A")
    br = g.branch(460, 0)
    g.link(e, None, br, None)
    g.link(none, "ReturnValue", br, "Condition")
    yes = g.ret(720, -120)
    g.val(yes, "bKnows", True)
    g.link(br, "Then", yes, None)
    no = g.ret_new(1300, 200)
    g.val(no, "bKnows", False)
    if EAL.does_asset_exist(GI):
        gi = g.call(GS + ":GetGameInstance", 480, 320)
        cast = g.pal(720, 120, "Cast To GI_FoA")
        g.link(gi, "ReturnValue", cast, "Object")
        g.link(br, "Else", cast, None)
        has = g.call(unreal.load_asset(GI).generated_class().get_path_name() + ":HasKnowledge", 1000, 300)
        g.link(cast, gp.cast_out(cast), has, "self")
        g.link(e, "Flag", has, "Flag")
        known = g.ret_new(1300, 0)
        g.flow(cast, has, known)
        g.link(has, gp.ret_pin(has), known, "bKnows")
        g.link(cast, "CastFailed", no, None)
        how = "No flag, or GI_FoA.HasKnowledge(Flag)."
    else:
        g.link(br, "Else", no, None)
        how = "Until GI_FoA exists, only rows with no flag match (day one)."
    g.box("Knowledge gate", "A row's Requires flag. " + how, g.nodes, "data")

    # ---- FindRow(Verb, Item) (pure): first matching row ----
    g = G.function(bp, "FindRow", **SIGS["FindRow"])
    e = g.entry(0, 0)
    start, more, elem, step = g.loop(g.get("Rows", 20, 200), "", 240, 0)
    g.link(e, None, start, None)
    b = brk(g, 900, 260, elem, "Item")
    st_eq = g.call(KML + ":EqualEqual_NameName", 1240, 160)
    g.link(b, f(b, "State"), st_eq, "A")
    g.link(g.get("State", 1040, 120), "", st_eq, "B")
    st_any = g.call(KML + ":EqualEqual_NameName", 1240, 280, B="None")
    g.link(b, f(b, "State"), st_any, "A")
    st_ok = g.call(KML + ":BooleanOR", 1460, 200)
    g.link(st_eq, "ReturnValue", st_ok, "A")
    g.link(st_any, "ReturnValue", st_ok, "B")
    v_eq = g.call(KML + ":EqualEqual_NameName", 1240, 400)
    g.link(b, f(b, "Verb"), v_eq, "A")
    g.link(e, "Verb", v_eq, "B")
    i_eq = g.call(KML + ":EqualEqual_NameName", 1240, 520)
    g.link(b, f(b, "Item"), i_eq, "A")
    g.link(e, "Item", i_eq, "B")
    knows = g.selfcall("Knows", 1240, 640)
    g.link(b, f(b, "Requires"), knows, "Flag")
    match = g.call(KML + ":BooleanAND", 1700, 300)
    for _ in range(2):
        g.ed.add_node_pin(match)
    for pin, src in (("A", st_ok), ("B", v_eq), ("C", i_eq), ("D", knows)):
        g.link(src, gp.ret_pin(src), match, pin)
    hit = g.branch(1940, 0)
    g.link(more, "Then", hit, None)
    g.link(match, "ReturnValue", hit, "Condition")
    g.link(hit, "Else", step, None)
    g.box("First matching row", "Walk Rows in order: State matches (or the row says None for any state), same Verb, "
          "same Item, Requires flag known. Row order in DT_Interactions is the priority.", list(g.nodes), "logic")
    first = len(g.nodes)
    found = g.ret(2200, -100)
    g.val(found, "bFound", True)
    g.link(hit, "Then", found, None)
    g.link(elem, "Item", found, "Row")
    none = g.ret_new(2200, 200)
    g.val(none, "bFound", False)
    g.link(more, "Else", none, None)
    g.box("Result", "The first match, or bFound false once every row is checked.", g.nodes[first:], "data")

    # ---- Resolve(Verb, Held) (pure): exact item first, then the bare hand ----
    g = G.function(bp, "Resolve", **SIGS["Resolve"])
    e = g.entry(0, 0)
    exact = g.selfcall("FindRow", 240, 180)
    g.link(e, "Verb", exact, "Verb")
    g.link(e, "Held", exact, "Item")
    bare = g.selfcall("FindRow", 240, 360, Item="None")
    g.link(e, "Verb", bare, "Verb")
    br = g.branch(520, 0)
    g.link(e, None, br, None)
    g.link(exact, "bFound", br, "Condition")
    r1 = g.ret(780, -80)
    g.link(br, "Then", r1, None)
    g.link(exact, "bFound", r1, "bFound")
    g.link(exact, "Row", r1, "Row")
    r2 = g.ret_new(780, 160)
    g.link(br, "Else", r2, None)
    g.link(bare, "bFound", r2, "bFound")
    g.link(bare, "Row", r2, "Row")
    g.box("Resolve", "The held item's own row (including a specific wrong-item line), else the bare-hand row.",
          g.nodes, "logic")

    # ---- ApplyState(NewState, bInstant): overridable; visibility and pivot pose ----
    g = G.function(bp, "ApplyState", **SIGS["ApplyState"])
    e = g.entry(0, 0)
    hide = g.call(KAL + ":Array_Contains", 240, 180)
    g.link(g.get("HiddenStates", 20, 220), "", hide, "TargetArray")
    g.link(e, "NewState", hide, "ItemToFind")
    s_h = g.call("/Script/Engine.Actor:SetActorHiddenInGame", 480, 0)
    g.link(hide, "ReturnValue", s_h, "bNewHidden")
    show = g.call(KML + ":Not_PreBool", 480, 220)
    g.link(hide, "ReturnValue", show, "A")
    s_c = g.call("/Script/Engine.Actor:SetActorEnableCollision", 760, 0)
    g.link(show, "ReturnValue", s_c, "bNewActorEnableCollision")
    g.chain(e, s_h, s_c)
    g.box("Visibility", "HiddenStates hide the actor and switch off its collision (a pickup still in its drawer, "
          "or taken).", list(g.nodes), "state")
    first = len(g.nodes)
    pose = g.call("/Script/Engine.BlueprintMapLibrary:Map_Find", 1040, 200)
    g.link(g.get("Poses", 820, 240), "", pose, "TargetMap")
    g.link(e, "NewState", pose, "Key")
    has = g.branch(1300, 0)
    g.link(s_c, None, has, None)
    g.link(pose, "ReturnValue", has, "Condition")
    inst = g.branch(1540, 0)
    g.link(has, "Then", inst, None)
    g.link(e, "bInstant", inst, "Condition")
    snap = g.call("/Script/Engine.SceneComponent:K2_SetRelativeTransform", 1800, -120)
    g.link(g.get("Pivot", 1580, -200), "", snap, "self")
    g.link(pose, "Value", snap, "NewTransform")
    s_goal = g.set("PivotGoal", 1800, 140)
    g.link(pose, "Value", s_goal, "PivotGoal")
    anim = g.selfcall("AnimatePivot", 2080, 140)
    g.link(inst, "Then", snap, None)
    g.link(inst, "Else", s_goal, None)
    g.chain(s_goal, anim)
    g.box("Pivot pose", "If this state has a pose (drawer out, door swung, wardrobe down), snap to it on load or "
          "reset, or animate there.", g.nodes[first:], "fx")

    # ---- SetState(NewState, bInstant) ----
    g = G.function(bp, "SetState", **SIGS["SetState"])
    e = g.entry(0, 0)
    real_s = g.call(KML + ":NotEqual_NameName", 240, 160, B="None")
    g.link(e, "NewState", real_s, "A")
    new_s = g.call(KML + ":NotEqual_NameName", 240, 280)
    g.link(e, "NewState", new_s, "A")
    g.link(g.get("State", 20, 320), "", new_s, "B")
    ok = g.call(KML + ":BooleanAND", 480, 200)
    g.link(real_s, "ReturnValue", ok, "A")
    g.link(new_s, "ReturnValue", ok, "B")
    br = g.branch(700, 0)
    g.link(e, None, br, None)
    g.link(ok, "ReturnValue", br, "Condition")
    s = g.set("State", 940, 0)
    g.link(e, "NewState", s, "State")
    ap = g.selfcall("ApplyState", 1200, 0)
    g.link(e, "NewState", ap, "NewState")
    g.link(e, "bInstant", ap, "bInstant")
    g.link(br, "Then", s, None)
    g.chain(s, ap)
    g.box("Change state", "Ignore None and the current state; show the new one.", list(g.nodes), "state")
    first = len(g.nodes)
    start, more, elem, step = g.loop(g.get("Linked", 1300, 200), "", 1480, 0)
    fb = g.selfcall("PlayFeedback", 1200, 260)
    g.link(e, "NewState", fb, "NewState")
    g.link(ap, None, fb, None)
    g.link(fb, None, start, None)
    tell = g.msg("Interact", 2260, 0)
    g.link(more, "Then", tell, None)
    g.link(elem, "Item", tell, "self")
    g.val(tell, "Verb", "Notify")
    g.link(e, "NewState", tell, "HeldItem")
    g.link(tell, None, step, None)
    g.box("Tell linked actors", "Each Linked actor gets Interact(Notify, NewState): a drawer reveals its pickup, the "
          "door's HandleOff topples the wardrobe.", g.nodes[first:], "out")

    # ---- PlayFeedback(NewState): sound and sand burst on a played (not reset) state change ----
    g = G.function(bp, "PlayFeedback", **SIGS["PlayFeedback"])
    e = g.entry(0, 0)
    here = g.call("/Script/Engine.Actor:K2_GetActorLocation", 240, 360)
    snd = g.call("/Script/Engine.BlueprintMapLibrary:Map_Find", 240, 180)
    g.link(g.get("StateSounds", 20, 220), "", snd, "TargetMap")
    g.link(e, "NewState", snd, "Key")
    b1 = g.branch(520, 0)
    g.link(e, None, b1, None)
    g.link(snd, "ReturnValue", b1, "Condition")
    play = g.call(GS + ":PlaySoundAtLocation", 780, -40)
    g.link(snd, "Value", play, "Sound")
    g.link(here, "ReturnValue", play, "Location")
    g.link(b1, "Then", play, None)
    g.box("State sound", "", list(g.nodes), "fx")
    first = len(g.nodes)
    burst = g.call("/Script/Engine.BlueprintMapLibrary:Map_Find", 1100, 180)
    g.link(g.get("BurstStates", 880, 220), "", burst, "TargetMap")
    g.link(e, "NewState", burst, "Key")
    b2 = g.branch(1340, 0)
    g.link(play, None, b2, None)
    g.link(b1, "Else", b2, None)
    g.link(burst, "ReturnValue", b2, "Condition")
    if EAL.does_asset_exist(SANDFX):
        sand = g.call(unreal.load_asset(SANDFX).generated_class().get_path_name() + ":SpawnSandBurst", 1600, -40)
        g.link(here, "ReturnValue", sand, "Location")
        g.link(burst, "Value", sand, "Scale")
        g.link(b2, "Then", sand, None)
    g.box("Sand burst", "", g.nodes[first:], "fx")

    # ---- ApplyRow(Row) ----
    g = G.function(bp, "ApplyRow", **SIGS["ApplyRow"])
    e = g.entry(0, 0)
    b = brk(g, 0, 200, e, "Row")
    me = g.selfcall("GetInteractor", 280, 520)
    s = g.selfcall("SetState", 360, 0, bInstant=False)
    g.link(b, f(b, "NextState"), s, "NewState")
    say = g.call(inter + ":Narrate", 640, 0)
    g.link(me, "Interactor", say, "self")
    g.link(b, f(b, "Line"), say, "Line")
    bag = g.get("Inventory", 640, 520, inter)
    g.link(me, "Interactor", bag, "self")
    give = g.call(inv + ":Add", 920, 0)
    g.link(bag, "Inventory", give, "self")
    g.link(b, f(b, "Give"), give, "Item")
    spend = g.call(inv + ":UseUp", 1200, 0)
    g.link(bag, "Inventory", spend, "self")
    g.link(b, f(b, "Item"), spend, "Item")
    anim = g.call(inter + ":PlayRowMontage", 1480, 0)
    g.link(me, "Interactor", anim, "self")
    g.link(b, f(b, "Montage"), anim, "Montage")
    rep = g.call(inter + ":Report", 1760, 0)
    g.link(me, "Interactor", rep, "self")
    g.link(b, f(b, "Event"), rep, "Event")
    used = g.pal(2040, 0, "Call", "OnUsed")
    g.link(g.pal(1820, 260, "Get a reference to self"), "", used, "Interactable")
    g.link(b, f(b, "Verb"), used, "Verb")
    g.link(g.get("State", 1820, 360), "", used, "NewState")
    g.chain(e, s, say, give, spend, anim, rep, used)
    g.box("Apply a row", "New state, the narration line, Give (Take), UseUp (the key snaps into KeyStub), the "
          "montage, the beat event for BP_BeatDirector, then OnUsed for anyone listening.", g.nodes, "state")

    # ---- interface: GetPrompt, CanInteract ----
    g = G(bp, "GetPrompt").clear()
    e = g.entry(0, 0)
    me = g.selfcall("GetInteractor", 0, 200)
    ok = g.call(KSL + ":IsValid", 0, 360)  # no player pawn (a sequence's spawned pawn, an MRQ render): no prompt
    g.link(me, "Interactor", ok, "Object")
    br = g.branch(260, -160)
    g.link(e, None, br, None)
    g.link(ok, "ReturnValue", br, "Condition")
    verb = g.get("Verb", 260, 160, inter)
    g.link(me, "Interactor", verb, "self")
    bag = g.get("Inventory", 260, 280, inter)
    g.link(me, "Interactor", bag, "self")
    held = g.call(inv + ":GetHeld", 500, 280)
    g.link(bag, "Inventory", held, "self")
    res = g.selfcall("Resolve", 740, 160)
    g.link(verb, "Verb", res, "Verb")
    g.link(held, "Item", res, "Held")
    b = brk(g, 1000, 160, res, "Row")
    r = g.ret(1300, 0)
    g.link(br, "Then", r, None)
    g.link(b, f(b, "Prompt"), r, "Prompt")
    none = g.ret_new(1300, -200)  # after g.ret: it reuses the first return node it finds
    g.link(br, "Else", none, None)
    g.box("Prompt", "The row the player's current verb and held item would run, as a full sentence.", g.nodes, "out")

    g = G(bp, "CanInteract").clear()
    e = g.entry(0, 0)
    res = g.selfcall("Resolve", 260, 160)
    g.link(e, "Verb", res, "Verb")
    g.link(e, "HeldItem", res, "Held")
    r = g.ret(560, 0)
    g.link(e, None, r, None)
    g.link(res, "bFound", r, "bCanInteract")
    g.box("Can interact", "True when a row answers this verb with this item or the bare hand.", g.nodes, "out")

    # ---- event graph ----
    g = G(bp).clear()
    begin = g.event("ReceiveBeginPlay", 0, 0)
    load = g.selfcall("LoadRows", 260, 0)
    s_m = g.set("MorningState", 520, 0)
    g.link(g.get("State", 300, 180), "", s_m, "MorningState")
    att = g.selfcall("AttachCarried", 800, 0)
    ap = g.selfcall("ApplyState", 1080, 0, bInstant=True)
    g.link(g.get("State", 860, 180), "", ap, "NewState")
    g.chain(begin, load, s_m, att, ap)
    g.box("Begin play", "Load this actor's rows, remember the morning, let Carried actors ride the Pivot (contents "
          "of a drawer, doors of a wardrobe), show the state.", g.nodes, "event")
    first = len(g.nodes)
    ev = g.event("Interact", 0, 600)
    res = g.selfcall("Resolve", 260, 760)
    g.link(ev, "Verb", res, "Verb")
    g.link(ev, "HeldItem", res, "Held")
    br = g.branch(560, 600)
    g.link(ev, None, br, None)
    g.link(res, "bFound", br, "Condition")
    ar = g.selfcall("ApplyRow", 820, 600)
    g.link(br, "Then", ar, None)
    g.link(res, "Row", ar, "Row")
    g.box("Interact (BPI_Interactable)", "Look, Take, Use and Notify all run the matching row.", g.nodes[first:],
          "event")
    first = len(g.nodes)
    rs = g.event("ResetForNewDay", 0, 1000)
    s_s = g.set("State", 300, 1000)
    g.link(g.get("MorningState", 80, 1160), "", s_s, "State")
    ap2 = g.selfcall("ApplyState", 580, 1000, bInstant=True)
    g.link(s_s, "Output_Get", ap2, "NewState")
    g.chain(rs, s_s, ap2)
    g.box("Reset for a new day", "Back to the morning state and pose; what the player learned lives in GI_FoA.",
          g.nodes[first:], "event")
    first = len(g.nodes)
    ap_ev = g.custom("AnimatePivot", 0, 1360)
    parts = g.call(KML + ":BreakTransform", 260, 1520)
    g.link(g.get("PivotGoal", 40, 1540), "", parts, "InTransform")
    move = g.call(KSL + ":MoveComponentTo", 560, 1360, bEaseIn=True, bForceShortestRotationPath=True)
    g.link(g.get("Pivot", 340, 1300), "", move, "Component")
    g.link(parts, "Location", move, "TargetRelativeLocation")
    g.link(parts, "Rotation", move, "TargetRelativeRotation")
    g.link(g.get("bEaseOut", 340, 1680), "", move, "bEaseOut")
    g.link(g.get("MoveTime", 340, 1760), "", move, "OverTime")
    g.link(ap_ev, None, move, "Move")
    done = g.msg("Interact", 900, 1360)
    g.link(g.pal(700, 1560, "Get a reference to self"), "", done, "self")
    g.val(done, "Verb", "Notify")
    g.val(done, "HeldItem", "Arrived")
    g.link(move, None, done, None)
    g.box("Animate the pivot", "Ease to PivotGoal over MoveTime (the topple eases in only, like a fall), then tell "
          "itself Notify(Arrived) so a row can react to the landing.", g.nodes[first:], "fx")

    # ---- LoadRows: this actor's rows from DT_Interactions ----
    g = G.function(bp, "LoadRows", **SIGS["LoadRows"])
    e = g.entry(0, 0)
    clear = g.call(KAL + ":Array_Clear", 240, 0)
    g.link(g.get("Rows", 40, 160), "", clear, "TargetArray")
    names = g.call("/Script/Engine.DataTableFunctionLibrary:GetDataTableRowNames", 520, 0, Table=DTI)
    start, more, elem, step = g.loop(names, "OutRowNames", 800, 0)
    g.flow(e, clear, names, start)
    row = g.pal(1560, 0, "Get Data Table Row")
    g.val(row, "DataTable", DTI)
    g.link(elem, "Item", row, "RowName")
    g.link(more, "Then", row, None)
    b = brk(g, 1560, 260, row, "ReturnValue")
    mine = g.call(KML + ":EqualEqual_NameName", 1880, 260)
    g.link(b, f(b, "Interactable"), mine, "A")
    g.link(g.get("InteractionKey", 1660, 420), "", mine, "B")
    br = g.branch(2120, 0)
    g.link(mine, "ReturnValue", br, "Condition")
    add = g.call(KAL + ":Array_Add", 2360, 0)
    g.link(g.get("Rows", 2140, 160), "", add, "TargetArray")
    g.link(row, "ReturnValue", add, "NewItem")
    g.link(row, "then", br, None)
    g.link(row, "RowNotFound", step, None)
    g.link(br, "Then", add, None)
    g.link(br, "Else", step, None)
    g.link(add, None, step, None)
    g.box("Load my rows", "Copy the DT_Interactions rows for InteractionKey once, at BeginPlay; the 10 Hz prompt "
          "queries then stay on a short local array.", g.nodes, "data")

    # ---- AttachCarried: actors that ride the Pivot ----
    g = G.function(bp, "AttachCarried", **SIGS["AttachCarried"])
    e = g.entry(0, 0)
    start, more, elem, step = g.loop(g.get("Carried", 20, 200), "", 240, 0)
    g.link(e, None, start, None)
    att = g.call("/Script/Engine.Actor:K2_AttachToComponent", 1000, 0, LocationRule="KeepWorld",
                 RotationRule="KeepWorld", ScaleRule="KeepWorld")
    g.link(elem, "Item", att, "self")
    g.link(g.get("Pivot", 780, 160), "", att, "Parent")
    g.link(more, "Then", att, None)
    g.link(att, None, step, None)
    g.box("Carry", "Attach each Carried actor to the Pivot, keeping its world placement, so it moves with the drawer "
          "or falls with the wardrobe.", g.nodes, "state")

    # Preserve the wardrobe-only rattle and pending-motion cancellation on a source rebuild.
    import runpy
    from pathlib import Path
    runpy.run_path(str(Path(__file__).with_name('wardrobe_rattle.py')))
    # The progression/contact helper is already declared on a configured project; retain it after a full rebuild.
    if 'CanApplyProgressionRow' in [str(n) for n in BEL.list_graph_names(bp)]:
        previous_phase = os.environ.get('FOA_PHASE')
        try:
            for pacing_phase in ('contact', 'guard'):
                os.environ['FOA_PHASE'] = pacing_phase
                runpy.run_path(str(Path(__file__).with_name('build_interaction_pacing.py')), run_name='__main__')
            if 'IsDressingBlocked' in [str(n) for n in BEL.list_graph_names(bp)]:
                os.environ['FOA_PHASE'] = 'prompt'
                runpy.run_path(str(Path(__file__).with_name('build_boot_pacing.py')), run_name='__main__')
        finally:
            if previous_phase is None:
                os.environ.pop('FOA_PHASE', None)
            else:
                os.environ['FOA_PHASE'] = previous_phase
    ok = BEL.compile_blueprint(bp)
    gp.save(bp)
    graphs = ["EventGraph", "LoadRows", "AttachCarried", "PlayFeedback", "FindRow", "Resolve", "ApplyRow", "SetState", "ApplyState", "GetPrompt",
              "CanInteract", "GetInteractor", "Knows"]
    print("BP_Interactable compiled", ok, "errors", [(n, G(bp, n).errors()) for n in graphs if G(bp, n).errors()])
    print("shots", gp.capture(bp, graphs, "BP_Interactable"))


def step_children():
    presets = {  # class defaults; instances override Poses, Carried, Linked and InteractionKey
        "BP_Pickup": dict(State="Available", HiddenStates=["Hidden", "Taken"]),
        "BP_Container": dict(State="Closed"),
        "BP_Door": dict(State="Locked", InteractionKey="Door", MoveTime=1.2),
        "BP_Topple": dict(State="Standing", InteractionKey="Wardrobe", MoveTime=0.85, bEaseOut=False),
    }
    for cls, values in presets.items():
        bp = gp.asset(cls)
        BEL.compile_blueprint(bp)
        cdo = unreal.get_default_object(bp.generated_class())
        for k, v in values.items():
            cdo.set_editor_property(k, v)
        gp.save(bp)
        print(cls, {k: cdo.get_editor_property(k) for k in values})


{"components": step_components, "graphs": step_graphs,
 "children": step_children}[os.environ.get("FOA_STEP", "graphs")]()
