"""BP_DreamDirector: the actor that plays MPC_Dream over time (post-process lane). Runs INSIDE the open editor:
  for N in 1 2 3 4 [5]: python Tools/Unreal/ue_remote.py Tools/Unreal/build_dream_director.py FOA_STAGE=N
                    then Hayba blueprint_compile + asset_save on /Game/FoA/PostProcess/BP_DreamDirector
  Never compiles from Python (editor-rules). Place the DreamDirector actor afterwards with Hayba (folder Lighting).

  BeginPlay          remembers the gameplay look (FilmLook, LensLook, EchoShape) from MPC_Dream
  Tick               MenuBlend eases to its target; Breath = 0.5 + 0.5 sin(2 pi t / BreathPeriod);
                     EchoStrength = BaseEcho x (0.8..1.2 with the breath) x lerp(1, MenuEchoBoost, MenuBlend);
                     while MenuBlend > 0 the three look vectors lerp from the gameplay look to the Menu* look
  MenuGlitch         while in menu mode: a 0.08 s glitch flicker, re-armed every 6-12 s (timer)
Contract API (docs/mechanics/contract.md; callers GetActorOfClass and skip quietly if absent):
  TriggerGlitchBurst(Strength 0..1, Seconds)  GlitchAmount = Strength, MoshAmount = 0.6 x Strength, tier baseline after Seconds
  SetTier(Tier 0 Plausible / 1 Suspicious / 2 Open)  baseline GlitchAmount 0 / 0.08 / 0.16 and InkBoil 0 / 0.35 / 0.7
  SetMenuMode(Enabled)  in over ~1 s, out over ~2.5 s; hue at its tutorial value; MenuGlitch flickers every 6-12 s
  SetHueDrift(Amount 0..1)   SetEchoStrength(Amount 0..1)
  SetStyleMode(Mode 0 Real / 1 Pixel / 2 Dither / 3 CRT, BlendSeconds)   PulseStyle(Mode, Seconds)
  StartStyleCycle(Interval)   StopStyleCycle()     T8 battle styles via MPC RetroMix (x pixel, y dither, z CRT, w wipe)
  SetShiftStreak(Length, Angle, Intensity)   PulseShiftStreak(Intensity, Seconds)   SetLetterbox(Enabled, Seconds)
                     Hail Mary highlight streaks (MPC ShiftStreak) and 2.39:1 bars (MPC Letterbox), streaks crossing them
Extras for this lane's brief: TriggerTear (TearAmount 1 for 0.6 s on Custom Stencil 2), TriggerStutter (world hold + skip).
"""
import os

import unreal

BEL, GE, PL, EAL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary, unreal.EditorAssetLibrary
PATH = "/Game/FoA/PostProcess/BP_DreamDirector"
MPC = "/Game/FoA/PostProcess/MPC_Dream.MPC_Dream"
BPL = "/Game/FoA/VFX/Sand/BPL_SandFX"  # sandvfx: SpawnAmbientBloom(Tier)
KML, KSL, GS, KM = ("/Script/Engine." + c for c in ("KismetMaterialLibrary", "KismetSystemLibrary", "GameplayStatics", "KismetMathLibrary"))
COL = {"look": (0.10, 0.22, 0.32), "tick": (0.10, 0.28, 0.26), "glitch": (0.36, 0.12, 0.10), "tear": (0.30, 0.10, 0.26),
       "stutter": (0.32, 0.25, 0.08), "menu": (0.22, 0.14, 0.34), "api": (0.15, 0.28, 0.15), "retro": (0.30, 0.18, 0.06), "streak": (0.32, 0.28, 0.12)}
MENU_LOOK = {  # stronger menu look; gameplay values come from MPC_Dream at BeginPlay
    "MenuFilm": "(R=0.40,G=0.15,B=0.00,A=0.35)",   # vignette (breathing), extra shader grain, free, ink contrast
    "MenuLens": "(R=0.50,G=0.55,B=0.25,A=0.55)",   # halation, edge softness, barrel, chroma
    "MenuEcho": "(R=2.20,G=1.20,B=0.80,A=0.45)",   # motion frames per ghost, static vertical slip, decay, gain
}


def pin(node, name, out=False):
    p = (BEL.find_output_pin if out else BEL.find_input_pin)(node, name)
    assert PL.is_valid(p), f"no {'output' if out else 'input'} {name} on {BEL.get_node_title(node)}: " \
                           f"{[str(PL.get_pin_name(x)) for x in BEL.list_all_pins(node)]}"
    return p


def value_out(node):
    """The data output of a node (ReturnValue, a variable get, or a Set node's pass-through)."""
    for p in BEL.list_output_pins(node):
        if str(PL.get_pin_name(p)) not in ("then", "execute"):
            return p
    raise AssertionError("no data output on " + BEL.get_node_title(node))


def link(a, b):
    assert PL.try_create_connection(a, b), f"link {PL.get_pin_name(a)} -> {PL.get_pin_name(b)}"


def impure(node):
    return PL.is_valid(BEL.find_execute_pin(node))


def chain(*nodes):
    """Exec-wire the impure nodes left to right."""
    nodes = [n for n in nodes if impure(n) or PL.is_valid(BEL.find_then_pin(n))]  # events have then, pure nodes neither
    for a, b in zip(nodes, nodes[1:]):
        link(BEL.find_then_pin(a), BEL.find_execute_pin(b))


def place(node, x, y):
    BEL.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    return node


PENDING = []  # pin defaults a promotable operator (Multiply, Add, ...) refuses until a link has typed its wildcard pins


def fn(ed, cls, name, x, y, **values):
    n = place(ed.add_call_function_node(f"{cls}:{name}"), x, y)
    for k, v in values.items():
        if not PL.set_pin_value(pin(n, k), str(v)):
            PENDING.append((n, k, str(v), name))
    return n


def settle():
    """Set the deferred pin defaults now that every link is made (the links typed the wildcard pins)."""
    failed = [f"{name}.{k} = {v}" for n, k, v, name in PENDING if not PL.set_pin_value(pin(n, k), v)]
    PENDING.clear()
    assert not failed, failed


def get(ed, var, x, y):
    return place(ed.add_get_member_variable_node(var), x, y)


def setv(ed, var, x, y, src=None):
    n = place(ed.add_set_member_variable_node(var), x, y)
    if src is not None:
        link(src, pin(n, var))
    return n


def set_mpc(ed, param, x, y, value=None, vector=False):
    n = fn(ed, KML, "SetVectorParameterValue" if vector else "SetScalarParameterValue", x, y,
           Collection=MPC, ParameterName=param)
    if value is not None:
        if isinstance(value, (int, float)):
            assert PL.set_pin_value(pin(n, "ParameterValue"), str(value))
        else:
            link(value, pin(n, "ParameterValue"))
    return n


def box(ed, title, desc, x0, y0, x1, y1, group):
    """House style: a 2-5 word title only (the user's rule: no descriptions in graphs; desc documents the code here),
    snug box, coloured bubble that stays readable zoomed out."""
    c = ed.add_comment_node(title, unreal.Vector2D(x0, y0), unreal.Vector2D(x1 - x0, y1 - y0))
    BEL.set_comment_color(c, unreal.LinearColor(*COL[group], 1.0))
    for k, v in (("font_size", 18), ("comment_bubble_visible_in_details_panel", True), ("color_comment_bubble", True)):
        c.set_editor_property(k, v)
    return c


def own(bp, graph, name, x, y):
    """Call one of the Blueprint's own functions: it must be on the compiled class, i.e. built in an earlier stage."""
    return place(graph.add_call_function_node(f"{BEL.generated_class(bp).get_path_name()}:{name}"), x, y)


def retro_color(bp):
    """T8 battle styles (contract), part 1: the StyleColor preset picker the style functions call."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    fs = GE.create_and_edit_function_graph(bp, "StyleColor")
    fs.add_graph_input_parameter("Mode", integer, "0")
    ret = fs.add_graph_output_parameter("Color", color)
    fs.set_is_pure_function(True)
    place(ret, 1400, 0)
    mode = pin(PL.get_owning_node(fs.find_graph_entry_pin()), "Mode", True)
    pick = value_out(get(fs, "StyleReal", 200, 420))
    for i, (var, n) in enumerate((("StylePixel", 1), ("StyleDither", 2), ("StyleCRT", 3))):
        eq = fn(fs, KM, "EqualEqual_IntInt", 200 + 380 * i, 200, B=n)
        link(mode, pin(eq, "A"))
        sel = fn(fs, KM, "SelectColor", 420 + 380 * i, 0)
        link(value_out(get(fs, var, 420 + 380 * i, 420)), pin(sel, "A"))
        link(pick, pin(sel, "B"))
        link(value_out(eq), pin(sel, "bPickA"))
        pick = value_out(sel)
    link(pick, pin(ret, "Color"))
    link(fs.find_graph_entry_pin(), BEL.find_execute_pin(ret))
    box(fs, "StyleColor (pure)", "Mode 0 Real / 1 Pixel / 2 Dither / 3 CRT -> its RetroMix preset (Style* variables).",
        -40, -70, 1660, 540, "retro")


def retro_modes(bp):
    """T8 battle styles, part 2: SetStyleMode, PulseStyle, StartStyleCycle (they call StyleColor)."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    fsm = GE.create_and_edit_function_graph(bp, "SetStyleMode")
    fsm.add_graph_input_parameter("Mode", integer, "0")
    fsm.add_graph_input_parameter("BlendSeconds", real, "0.2")
    entry = PL.get_owning_node(fsm.find_graph_entry_pin())
    sc = own(bp, fsm, "StyleColor", 300, 220)
    link(pin(entry, "Mode", True), pin(sc, "Mode"))
    st = setv(fsm, "RetroTarget", 300, 0, value_out(sc))
    mx = fn(fsm, KM, "FMax", 640, 220, B=0.02)
    link(pin(entry, "BlendSeconds", True), pin(mx, "A"))
    dv = fn(fsm, KM, "Divide_DoubleDouble", 860, 220, A=3.0)
    link(value_out(mx), pin(dv, "B"))
    sp = setv(fsm, "RetroSpeed", 640, 0, value_out(dv))
    sw = setv(fsm, "RetroWipe", 980, 0)
    assert PL.set_pin_value(pin(sw, "RetroWipe"), "1.0")
    link(fsm.find_graph_entry_pin(), BEL.find_execute_pin(st))
    chain(st, sp, sw)
    box(fsm, "Set battle style", "Blend to a battle style over BlendSeconds, with a short glitch wipe (vertical slip + block "
        "scramble; the material drops it under ReduceMotion).", -40, -70, 1300, 400, "retro")

    fp = GE.create_and_edit_function_graph(bp, "PulseStyle")
    fp.add_graph_input_parameter("Mode", integer, "1")
    fp.add_graph_input_parameter("Seconds", real, "0.05")
    entry = PL.get_owning_node(fp.find_graph_entry_pin())
    rm = fn(fp, KML, "GetScalarParameterValue", 260, 220, Collection=MPC, ParameterName="ReduceMotion")
    gt = fn(fp, KM, "Greater_DoubleDouble", 600, 220, B=0.5)
    link(value_out(rm), pin(gt, "A"))
    br = place(fp.add_branch_node(), 820, 0)
    link(value_out(gt), BEL.find_condition_pin(br))
    hold = setv(fp, "RetroHold", 1080, 0, value_out(get(fp, "RetroTarget", 1080, 220)))
    sc = own(bp, fp, "StyleColor", 1400, 260)
    link(pin(entry, "Mode", True), pin(sc, "Mode"))
    tgt = setv(fp, "RetroTarget", 1400, 0, value_out(sc))
    cur = setv(fp, "RetroCurrent", 1720, 0, value_out(sc))
    wp = setv(fp, "RetroWipe", 2040, 0)
    assert PL.set_pin_value(pin(wp, "RetroWipe"), "1.0")
    tm = fn(fp, KSL, "K2_SetTimer", 2360, 0, FunctionName="EndPulse")
    link(pin(entry, "Seconds", True), pin(tm, "Time"))
    link(fp.find_graph_entry_pin(), BEL.find_execute_pin(rm) if impure(rm) else BEL.find_execute_pin(br))
    chain(rm, br) if impure(rm) else None
    link(BEL.find_else_pin(br), BEL.find_execute_pin(hold))
    chain(hold, tgt, cur, wp, tm)
    box(fp, "Pulse battle style", "Hard-cut to a style for Seconds (a frame or two = the dream losing resolution), then back. "
        "Skipped under ReduceMotion.", -40, -70, 2700, 480, "retro")

    fc = GE.create_and_edit_function_graph(bp, "StartStyleCycle")
    fc.add_graph_input_parameter("Interval", real, "4.0")
    entry = PL.get_owning_node(fc.find_graph_entry_pin())
    si = setv(fc, "CycleInterval", 300, 0, pin(entry, "Interval", True))
    ct = fn(fc, KSL, "K2_SetTimer", 640, 0, FunctionName="StyleCycleTick", bLooping="true")
    link(pin(entry, "Interval", True), pin(ct, "Time"))
    link(fc.find_graph_entry_pin(), BEL.find_execute_pin(si))
    chain(si, ct)
    box(fc, "Start style cycle", "Auto-switch battle styles every Interval s (StyleCycleTick), with rare 1-2 frame flickers.",
        -40, -70, 1000, 300, "retro")


def retro_events(bp, ed):
    """T8 battle styles, part 3: StopStyleCycle and the timer events (they call SetStyleMode / PulseStyle)."""
    fx = GE.create_and_edit_function_graph(bp, "StopStyleCycle")
    c1 = fn(fx, KSL, "K2_ClearTimer", 300, 0, FunctionName="StyleCycleTick")
    c2 = fn(fx, KSL, "K2_ClearTimer", 640, 0, FunctionName="FlickerOnce")
    back = own(bp, fx, "SetStyleMode", 980, 0)
    assert PL.set_pin_value(pin(back, "BlendSeconds"), "0.3")
    link(fx.find_graph_entry_pin(), BEL.find_execute_pin(c1))
    chain(c1, c2, back)
    box(fx, "Stop style cycle", "Stop switching and blend back to the real, inked look in 0.3 s.", -40, -70, 1340, 300, "retro")

    # events the timers call
    y = 2800
    ev = place(ed.add_custom_event_node("EndPulse"), 0, y)
    hv = get(ed, "RetroHold", 60, y + 220)
    t1 = setv(ed, "RetroTarget", 300, y, value_out(hv))
    t2 = setv(ed, "RetroCurrent", 620, y, value_out(hv))
    t3 = setv(ed, "RetroWipe", 940, y)
    assert PL.set_pin_value(pin(t3, "RetroWipe"), "0.6")
    chain(ev, t1, t2, t3)
    box(ed, "EndPulse (timer)", "A pulse ends: hard cut back to the held style, with a small wipe.", -40, y - 70, 1240, y + 330, "retro")

    y = 3250
    ev = place(ed.add_custom_event_node("StyleCycleTick"), 0, y)
    rm = fn(ed, KML, "GetScalarParameterValue", 220, y + 220, Collection=MPC, ParameterName="ReduceMotion")
    gt = fn(ed, KM, "Greater_DoubleDouble", 560, y + 220, B=0.5)
    link(value_out(rm), pin(gt, "A"))
    br = place(ed.add_branch_node(), 780, y)
    link(value_out(gt), BEL.find_condition_pin(br))
    calm = own(bp, ed, "SetStyleMode", 1040, y - 260)
    assert PL.set_pin_value(pin(calm, "Mode"), "2") and PL.set_pin_value(pin(calm, "BlendSeconds"), "0.3")
    pickm = fn(ed, KM, "RandomIntegerInRange", 1040, y + 260, Min=1, Max=3)
    sw = own(bp, ed, "SetStyleMode", 1040, y)
    link(value_out(pickm), pin(sw, "Mode"))
    assert PL.set_pin_value(pin(sw, "BlendSeconds"), "0.15")
    late = fn(ed, KM, "FMax", 1400, y + 260, B=1.0)
    sub = fn(ed, KM, "Subtract_DoubleDouble", 1400, y + 400, B=0.5)
    link(value_out(get(ed, "CycleInterval", 1180, y + 420)), pin(sub, "A"))
    link(value_out(sub), pin(late, "A"))
    when = fn(ed, KM, "RandomFloatInRange", 1640, y + 260, Min=0.8)
    link(value_out(late), pin(when, "Max"))
    fl = fn(ed, KSL, "K2_SetTimer", 1880, y, FunctionName="FlickerOnce")
    link(value_out(when), pin(fl, "Time"))
    chain(ev, rm, br)
    link(BEL.find_then_pin(br), BEL.find_execute_pin(calm))
    link(BEL.find_else_pin(br), BEL.find_execute_pin(sw))
    chain(sw, fl)
    box(ed, "StyleCycleTick (timer)", "Each interval: a new random battle style with a glitch wipe, and one flicker scheduled "
        "somewhere inside the hold. ReduceMotion holds the dither style instead.", -40, y - 330, 2240, y + 560, "retro")

    y = 4000
    ev = place(ed.add_custom_event_node("FlickerOnce"), 0, y)
    fm = fn(ed, KM, "RandomIntegerInRange", 260, y + 220, Min=0, Max=3)
    pu = own(bp, ed, "PulseStyle", 560, y)
    link(value_out(fm), pin(pu, "Mode"))
    assert PL.set_pin_value(pin(pu, "Seconds"), "0.05")
    chain(ev, pu)
    box(ed, "FlickerOnce (timer)", "The dream loses resolution for a frame or two: pulse a random style for 0.05 s.",
        -40, y - 70, 980, y + 360, "retro")


def streak_api(bp):
    """Shift streak API, part 1: SetShiftStreak, PulseShiftStreak."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    f1 = GE.create_and_edit_function_graph(bp, "SetShiftStreak")
    for nm, dv in (("Length", "0.25"), ("Angle", "0.0"), ("Intensity", "1.0")):
        f1.add_graph_input_parameter(nm, real, dv)
    entry = PL.get_owning_node(f1.find_graph_entry_pin())
    a1 = setv(f1, "StreakLength", 300, 0, pin(entry, "Length", True))
    a2 = setv(f1, "StreakAngle", 620, 0, pin(entry, "Angle", True))
    a3 = setv(f1, "StreakBase", 940, 0, pin(entry, "Intensity", True))
    mk = fn(f1, KM, "MakeColor", 1260, 220)
    for ch, src in (("R", "Length"), ("G", "Angle"), ("B", "Intensity")):
        link(pin(entry, src, True), pin(mk, ch))
    link(value_out(get(f1, "StreakThreshold", 1040, 420)), pin(mk, "A"))
    a4 = set_mpc(f1, "ShiftStreak", 1260, 0, value_out(mk), vector=True)
    link(f1.find_graph_entry_pin(), BEL.find_execute_pin(a1))
    chain(a1, a2, a3, a4)
    box(f1, "Set shift streak", "Resting highlight streak: Length (frame fraction), Angle (0 = vertical), Intensity 0..5.",
        -40, -70, 1640, 560, "streak")

    f2 = GE.create_and_edit_function_graph(bp, "PulseShiftStreak")
    f2.add_graph_input_parameter("Intensity", real, "2.5")
    f2.add_graph_input_parameter("Seconds", real, "0.6")
    entry = PL.get_owning_node(f2.find_graph_entry_pin())
    b1 = setv(f2, "StreakPulse", 300, 0, pin(entry, "Intensity", True))
    mxs = fn(f2, KM, "FMax", 300, 220, B=0.05)
    link(pin(entry, "Seconds", True), pin(mxs, "A"))
    dv = fn(f2, KM, "Divide_DoubleDouble", 560, 220)
    link(pin(entry, "Intensity", True), pin(dv, "A"))
    link(value_out(mxs), pin(dv, "B"))
    b2 = setv(f2, "StreakDecay", 620, 0, value_out(dv))
    link(f2.find_graph_entry_pin(), BEL.find_execute_pin(b1))
    chain(b1, b2)
    box(f2, "Pulse shift streak", "A transition: the highlights streak at Intensity, fading to the resting level over Seconds.",
        -40, -70, 960, 400, "streak")


def letterbox_api(bp):
    """Shift streak API, part 2: SetLetterbox (it calls PulseShiftStreak)."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    f3 = GE.create_and_edit_function_graph(bp, "SetLetterbox")
    f3.add_graph_input_parameter("Enabled", BEL.get_basic_type_by_name("bool"), "true")
    f3.add_graph_input_parameter("Seconds", real, "0.8")
    entry = PL.get_owning_node(f3.find_graph_entry_pin())
    cv = fn(f3, KM, "Conv_BoolToDouble", 300, 220)
    link(pin(entry, "Enabled", True), pin(cv, "InBool"))
    c1 = setv(f3, "LetterTarget", 300, 0, value_out(cv))
    mxl = fn(f3, KM, "FMax", 560, 220, B=0.05)
    link(pin(entry, "Seconds", True), pin(mxl, "A"))
    inv = fn(f3, KM, "Divide_DoubleDouble", 800, 220, A=1.0)
    link(value_out(mxl), pin(inv, "B"))
    c2 = setv(f3, "LetterSpeed", 640, 0, value_out(inv))
    pul = own(bp, f3, "PulseShiftStreak", 980, 0)
    link(pin(entry, "Seconds", True), pin(pul, "Seconds"))
    link(f3.find_graph_entry_pin(), BEL.find_execute_pin(c1))
    chain(c1, c2, pul)
    box(f3, "Letterbox in or out", "2.39:1 bars slide in or out over Seconds (cinematic beats only, never gameplay) while the "
        "highlight streaks cross them.", -40, -70, 1320, 420, "streak")


def stage1():
    """The asset and its variables."""
    # editor-rules (structural BP edits): never gut a Blueprint in place; a rebuild deletes the asset in its own run first
    assert not EAL.does_asset_exist(PATH), "BP_DreamDirector exists: delete it in its own run (no instances placed), then rebuild"
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    bp = BEL.create_blueprint_asset_with_parent(PATH, unreal.Actor)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    ed = GE.get_graph_editor(BEL.find_event_graph(bp))
    for c in list(ed.list_comment_nodes()):
        ed.remove_comment_node(c)
    ed.remove_nodes(list(ed.list_all_nodes()))
    real, color = BEL.get_basic_type_by_name("real"), BEL.get_struct_type(unreal.LinearColor.static_struct())
    names = BEL.list_member_variable_names(bp, False)
    variables = [("BaseEcho", real, "0.08", True), ("BreathPeriod", real, "4.5", True), ("MenuEchoBoost", real, "2.6", True),
                 ("MenuTarget", real, "0.0", False), ("MenuSpeed", real, "1.0", False), ("MenuBlend", real, "0.0", False),
                 ("TierGlitch", real, "0.0", False),
                 ("RetroCurrent", color, "(R=0,G=0,B=0,A=0)", False), ("RetroTarget", color, "(R=0,G=0,B=0,A=0)", False),
                 ("RetroHold", color, "(R=0,G=0,B=0,A=0)", False), ("RetroSpeed", real, "8.0", False),
                 ("RetroWipe", real, "0.0", False), ("CycleInterval", real, "4.0", True),
                 ("StreakLength", real, "0.25", True), ("StreakAngle", real, "0.0", True), ("StreakBase", real, "0.0", True),
                 ("StreakThreshold", real, "1.2", True), ("StreakPulse", real, "0.0", False), ("StreakDecay", real, "4.0", False),
                 ("LetterTarget", real, "0.0", False), ("LetterSpeed", real, "1.0", False), ("LetterCur", real, "0.0", False),
                 ("RevealTarget", real, "0.0", False), ("RevealSpeed", real, "1.0", False), ("RevealCur", real, "0.0", False),
                 ("CurrentTier", BEL.get_basic_type_by_name("int"), "0", False),
                 ("StyleReal", color, "(R=0,G=0,B=0,A=0)", True), ("StylePixel", color, "(R=1,G=0,B=0,A=0)", True),
                 ("StyleDither", color, "(R=0,G=1,B=0,A=0)", True), ("StyleCRT", color, "(R=0.6,G=0,B=1,A=0)", True),
                 ("GameFilm", color, "(R=0.25,G=0.0,B=0.0,A=0.35)", False), ("GameLens", color, "(R=0.08,G=0.10,B=0.16,A=0.08)", False),
                 ("GameEcho", color, "(R=1.5,G=0.6,B=0.72,A=0.35)", False)] + \
                [(k, color, v, True) for k, v in MENU_LOOK.items()]
    for var, t, default, editable in variables:
        if var not in names:
            ed.add_member_variable(var, t, default)
        BEL.set_blueprint_variable_instance_editable(bp, var, editable)
        BEL.set_blueprint_variable_category(bp, var, "Dream" if editable else "Dream|State")


def stage2(bp, ed):
    """Event graph (BeginPlay, Tick, timer events), then the contract API functions and StyleColor."""
    stage2_events(bp, ed)
    stage2_funcs(bp, ed)


def stage2_events(bp, ed):
    """BeginPlay, Tick and the timer events. Stage "2e" clears the event graph and runs only this again."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    # ---- BeginPlay: remember the gameplay look ----
    y = -700
    bpl = place(BEL.add_event_override(bp, "ReceiveBeginPlay", unreal.IntPoint(0, y)), 0, y)
    steps = []
    for i, (var, param) in enumerate((("GameFilm", "FilmLook"), ("GameLens", "LensLook"), ("GameEcho", "EchoShape"))):
        g = fn(ed, KML, "GetVectorParameterValue", 300 + 640 * i, y + 180, Collection=MPC, ParameterName=param)
        s = setv(ed, var, 300 + 640 * i + 330, y, value_out(g))
        steps += [g, s]
    arm = fn(ed, KSL, "K2_SetTimer", 300 + 640 * 3, y, FunctionName="AmbientBloomTick", Time=8.0)
    chain(bpl, *steps, arm)
    box(ed, "Gameplay look (BeginPlay)", "Remember MPC_Dream's look vectors, so menu mode can blend away and back.",
        -40, y - 70, 2280, y + 330, "look")

    # ---- Tick: menu blend, idle breathing, echo ----
    tick = place(BEL.add_event_override(bp, "ReceiveTick", unreal.IntPoint(0, 0)), 0, 0)
    interp = fn(ed, KM, "FInterpTo_Constant", 260, 260)
    link(value_out(get(ed, "MenuBlend", 0, 250)), pin(interp, "Current"))
    link(value_out(get(ed, "MenuTarget", 0, 340)), pin(interp, "Target"))
    link(pin(tick, "DeltaSeconds", True), pin(interp, "DeltaTime"))
    link(value_out(get(ed, "MenuSpeed", 0, 430)), pin(interp, "InterpSpeed"))
    set_mb = setv(ed, "MenuBlend", 600, 0, value_out(interp))
    blend = value_out(set_mb)
    t = fn(ed, GS, "GetTimeSeconds", 900, 260)
    tau = fn(ed, KM, "Multiply_DoubleDouble", 1140, 260, B=6.2831853)
    link(value_out(t), pin(tau, "A"))
    phase = fn(ed, KM, "Divide_DoubleDouble", 1380, 260)
    link(value_out(tau), pin(phase, "A"))
    link(value_out(get(ed, "BreathPeriod", 1140, 420)), pin(phase, "B"))
    sin = fn(ed, KM, "Sin", 1620, 260)
    link(value_out(phase), pin(sin, "A"))
    breath = fn(ed, KM, "MapRangeClamped", 1820, 260, InRangeA=-1.0, InRangeB=1.0, OutRangeA=0.0, OutRangeB=1.0)
    link(value_out(sin), pin(breath, "Value"))
    set_b = set_mpc(ed, "Breath", 1820, 0, value_out(breath))
    swell = fn(ed, KM, "Lerp", 2200, 260, A=0.8, B=1.2)
    link(value_out(breath), pin(swell, "Alpha"))
    boost = fn(ed, KM, "Lerp", 2200, 470, A=1.0)
    link(value_out(get(ed, "MenuEchoBoost", 1960, 560)), pin(boost, "B"))
    link(blend, pin(boost, "Alpha"))
    e1 = fn(ed, KM, "Multiply_DoubleDouble", 2460, 300)
    link(value_out(swell), pin(e1, "A"))
    link(value_out(get(ed, "BaseEcho", 2200, 400)), pin(e1, "B"))
    e2 = fn(ed, KM, "Multiply_DoubleDouble", 2680, 380)
    link(value_out(e1), pin(e2, "A"))
    link(value_out(boost), pin(e2, "B"))
    set_e = set_mpc(ed, "EchoStrength", 2260, 0, value_out(e2))
    box(ed, "Menu blend and breathing", "MenuBlend eases to its target; vignette and echo breathe on one "
        "4.5 s sine; menu mode multiplies the echo.", -40, -70, 2900, 690, "tick")

    # ---- Tick: menu look, only while some menu blend remains ----
    sets = []
    for i, (game, menu, param) in enumerate((("GameFilm", "MenuFilm", "FilmLook"), ("GameLens", "MenuLens", "LensLook"),
                                             ("GameEcho", "MenuEcho", "EchoShape"))):
        x = 3060 + 420 * i
        mix = fn(ed, KM, "LinearColorLerp", x, 300)
        link(value_out(get(ed, game, x, 470)), pin(mix, "A"))
        link(value_out(get(ed, menu, x, 560)), pin(mix, "B"))
        link(blend, pin(mix, "Alpha"))
        sets.append(set_mpc(ed, param, x, 0, value_out(mix), vector=True))
    # battle styles: RetroCurrent eases to RetroTarget, the wipe decays in ~0.2 s, both go out as MPC RetroMix
    rc = setv(ed, "RetroCurrent", 4520, 0)
    ci = fn(ed, KM, "CInterpTo", 4520, 260)
    link(value_out(get(ed, "RetroCurrent", 4300, 250)), pin(ci, "Current"))
    link(value_out(get(ed, "RetroTarget", 4300, 340)), pin(ci, "Target"))
    link(pin(tick, "DeltaSeconds", True), pin(ci, "DeltaTime"))
    link(value_out(get(ed, "RetroSpeed", 4300, 430)), pin(ci, "InterpSpeed"))
    link(value_out(ci), pin(rc, "RetroCurrent"))
    rw = setv(ed, "RetroWipe", 4900, 0)
    wi = fn(ed, KM, "FInterpTo_Constant", 4900, 260, Target=0.0, InterpSpeed=5.0)
    link(value_out(get(ed, "RetroWipe", 4700, 520)), pin(wi, "Current"))
    link(pin(tick, "DeltaSeconds", True), pin(wi, "DeltaTime"))
    link(value_out(wi), pin(rw, "RetroWipe"))
    bc = fn(ed, KM, "BreakColor", 5260, 260)
    link(value_out(rc), pin(bc, "InColor"))
    mk = fn(ed, KM, "MakeColor", 5500, 260)
    for ch in ("R", "G", "B"):
        link(pin(bc, ch, True), pin(mk, ch))
    link(value_out(rw), pin(mk, "A"))
    mix = set_mpc(ed, "RetroMix", 5500, 0, value_out(mk), vector=True)
    # shift streak + letterbox: the bars ease toward their target, a streak pulse decays, both go out to the MPC.
    # Idle gating: Letterbox, ShiftStreak and ColorReveal go out only while they move, so a Level Sequence can key
    # them (deterministic in Movie Render Queue, scrubbable) whenever the director is idle.
    def gate(var_a, var_b, x, cmp="NotEqual_DoubleDouble", **values):
        c = fn(ed, KM, cmp, x, 860, **values)
        link(value_out(get(ed, var_a, x - 220, 860)), pin(c, "A"))
        if var_b:
            link(value_out(get(ed, var_b, x - 220, 950)), pin(c, "B"))
        b = place(ed.add_branch_node(), x, -180)
        link(value_out(c), BEL.find_condition_pin(b))
        return b
    bl = gate("LetterCur", "LetterTarget", 5980)
    lc = setv(ed, "LetterCur", 6040, 0)
    li = fn(ed, KM, "FInterpTo_Constant", 6040, 260)
    link(value_out(get(ed, "LetterCur", 5960, 470)), pin(li, "Current"))
    link(value_out(get(ed, "LetterTarget", 5960, 560)), pin(li, "Target"))
    link(pin(tick, "DeltaSeconds", True), pin(li, "DeltaTime"))
    link(value_out(get(ed, "LetterSpeed", 5960, 650)), pin(li, "InterpSpeed"))
    link(value_out(li), pin(lc, "LetterCur"))
    lb = set_mpc(ed, "Letterbox", 6380, 0, value_out(lc))
    bs = gate("StreakPulse", None, 6740, "Greater_DoubleDouble", B=0.0)
    sp_ = setv(ed, "StreakPulse", 6760, 0)
    pi_ = fn(ed, KM, "FInterpTo_Constant", 6760, 260, Target=0.0)
    link(value_out(get(ed, "StreakPulse", 6560, 470)), pin(pi_, "Current"))
    link(pin(tick, "DeltaSeconds", True), pin(pi_, "DeltaTime"))
    link(value_out(get(ed, "StreakDecay", 6560, 560)), pin(pi_, "InterpSpeed"))
    link(value_out(pi_), pin(sp_, "StreakPulse"))
    add = fn(ed, KM, "Add_DoubleDouble", 7060, 380)
    link(value_out(get(ed, "StreakBase", 6860, 560)), pin(add, "A"))
    link(value_out(sp_), pin(add, "B"))
    mc = fn(ed, KM, "MakeColor", 7300, 260)
    link(value_out(get(ed, "StreakLength", 7060, 640)), pin(mc, "R"))
    link(value_out(get(ed, "StreakAngle", 7060, 730)), pin(mc, "G"))
    link(value_out(add), pin(mc, "B"))
    link(value_out(get(ed, "StreakThreshold", 7060, 820)), pin(mc, "A"))
    ss = set_mpc(ed, "ShiftStreak", 7300, 0, value_out(mc), vector=True)
    br = gate("RevealCur", "RevealTarget", 7740)
    rv = setv(ed, "RevealCur", 7760, 0)
    ri = fn(ed, KM, "FInterpTo_Constant", 7760, 260)
    link(value_out(get(ed, "RevealCur", 7680, 470)), pin(ri, "Current"))
    link(value_out(get(ed, "RevealTarget", 7680, 560)), pin(ri, "Target"))
    link(pin(tick, "DeltaSeconds", True), pin(ri, "DeltaTime"))
    link(value_out(get(ed, "RevealSpeed", 7680, 650)), pin(ri, "InterpSpeed"))
    link(value_out(ri), pin(rv, "RevealCur"))
    cr = set_mpc(ed, "ColorReveal", 8100, 0, value_out(rv))
    chain(tick, set_mb, set_b, set_e, *sets, rc, rw, mix, bl)
    for b, first, last, nxt in ((bl, lc, lb, bs), (bs, sp_, ss, br), (br, rv, cr, None)):
        link(BEL.find_then_pin(b), BEL.find_execute_pin(first))
        chain(first, last)
        if nxt is not None:
            link(BEL.find_then_pin(last), BEL.find_execute_pin(nxt))
            link(BEL.find_else_pin(b), BEL.find_execute_pin(nxt))
    box(ed, "Colour reveal (Tick)", "ColorReveal eases to its target (SetColorReveal); 1 = the whole frame in real colour.",
        7720, -70, 8480, 760, "api")
    box(ed, "Streak and letterbox (Tick)", "Bars ease to their target; a streak pulse decays; ShiftStreak and Letterbox go "
        "out to MPC_Dream.", 5920, -70, 7700, 900, "streak")
    box(ed, "Menu look (Tick)", "Film, lens and echo looks lerp from the gameplay look to the Menu* values by MenuBlend "
        "(0 = gameplay, so the director owns these three vectors).", 2960, -70, 4240, 690, "menu")
    box(ed, "Battle styles (Tick)", "RetroCurrent eases to the target style, the glitch wipe decays in ~0.2 s; both go out "
        "as MPC RetroMix.", 4260, -70, 5900, 690, "retro")

    # ---- EndGlitchBurst: the timer TriggerGlitchBurst arms ----
    y = 950
    ev = place(ed.add_custom_event_node("EndGlitchBurst"), 0, y)
    eg = set_mpc(ed, "GlitchAmount", 300, y)
    link(value_out(get(ed, "TierGlitch", 60, y + 200)), pin(eg, "ParameterValue"))
    chain(ev, eg, set_mpc(ed, "MoshAmount", 680, y, 0.0))
    box(ed, "EndGlitchBurst (timer)", "A burst ends: glitch back to the tier's baseline, mosh off.", -40, y - 70, 1060, y + 290, "glitch")

    # ---- TriggerTear ----
    y = 1300
    ev = place(ed.add_custom_event_node("TriggerTear"), 0, y)
    chain(ev, set_mpc(ed, "TearAmount", 300, y, 1.0), fn(ed, KSL, "Delay", 680, y, Duration=0.6),
          set_mpc(ed, "TearAmount", 920, y, 0.0))
    box(ed, "Trigger stencil tear", "Horizontal tear on Custom Stencil 2 (the Nightmare) for 0.6 s.", -40, y - 70, 1300, y + 230, "tear")

    # ---- TriggerStutter ----
    y = 1650
    ev = place(ed.add_custom_event_node("TriggerStutter"), 0, y)
    rm = fn(ed, KML, "GetScalarParameterValue", 280, y + 200, Collection=MPC, ParameterName="ReduceMotion")
    gt = fn(ed, KM, "Greater_DoubleDouble", 640, y + 200, B=0.5)
    link(value_out(rm), pin(gt, "A"))
    br = place(ed.add_branch_node(), 880, y)
    link(value_out(gt), BEL.find_condition_pin(br))
    hold = [set_mpc(ed, "StutterAmount", 1140, y, 1.0), fn(ed, GS, "SetGlobalTimeDilation", 1520, y, TimeDilation=0.02),
            fn(ed, KSL, "Delay", 1800, y, Duration=0.0016), fn(ed, GS, "SetGlobalTimeDilation", 2040, y, TimeDilation=3.0),
            fn(ed, KSL, "Delay", 2320, y, Duration=0.15), fn(ed, GS, "SetGlobalTimeDilation", 2560, y, TimeDilation=1.0),
            set_mpc(ed, "StutterAmount", 2840, y, 0.0)]
    chain(ev, rm, br)
    link(BEL.find_else_pin(br), BEL.find_execute_pin(hold[0]))
    chain(*hold)
    box(ed, "Trigger time stutter", "Hold the world ~5 frames, skip ahead 3x, resume; the camera keeps moving. Skipped under "
        "ReduceMotion. Delays run in dilated time.", -40, y - 70, 3220, y + 400, "stutter")

    # ---- MenuGlitch: rare flicker while in menu mode ----
    y = 2200
    ev = place(ed.add_custom_event_node("MenuGlitch"), 0, y)
    on = fn(ed, KM, "Greater_DoubleDouble", 280, y + 200, B=0.5)
    link(value_out(get(ed, "MenuTarget", 40, y + 220)), pin(on, "A"))
    br = place(ed.add_branch_node(), 560, y)
    link(value_out(on), BEL.find_condition_pin(br))
    flick = [set_mpc(ed, "GlitchAmount", 820, y, 0.3), fn(ed, KSL, "Delay", 1200, y, Duration=0.08),
             set_mpc(ed, "GlitchAmount", 1440, y, 0.0), fn(ed, KSL, "K2_SetTimer", 1820, y, FunctionName="MenuGlitch")]
    wait = fn(ed, KM, "RandomFloatInRange", 1560, y + 260, Min=6.0, Max=12.0)
    link(value_out(wait), pin(flick[3], "Time"))
    chain(ev, br)
    link(BEL.find_then_pin(br), BEL.find_execute_pin(flick[0]))
    chain(*flick)
    box(ed, "MenuGlitch (timer)", "While in menu mode: a 0.08 s glitch flicker, then re-arm itself 6-12 s later.",
        -40, y - 70, 2200, y + 420, "menu")



def stage2_funcs(bp, ed):
    """The contract API functions and StyleColor."""
    real, integer = BEL.get_basic_type_by_name("real"), BEL.get_basic_type_by_name("int")
    color = BEL.get_struct_type(unreal.LinearColor.static_struct())
    # ---- functions with parameters ----
    fe = GE.create_and_edit_function_graph(bp, "SetEchoStrength")
    fe.add_graph_input_parameter("Amount", real, "0.35")
    entry = PL.get_owning_node(fe.find_graph_entry_pin())
    sv = place(fe.add_set_member_variable_node("BaseEcho"), 320, 0)
    link(fe.find_graph_entry_pin(), BEL.find_execute_pin(sv))
    link(pin(entry, "Amount", True), pin(sv, "BaseEcho"))
    box(fe, "Set echo strength", "", -40, -70, 640, 200, "api")

    fh = GE.create_and_edit_function_graph(bp, "SetHueDrift")
    fh.add_graph_input_parameter("Amount", real, "0.0")
    entry = PL.get_owning_node(fh.find_graph_entry_pin())
    sh = set_mpc(fh, "HueDrift", 320, 0, pin(entry, "Amount", True))
    link(fh.find_graph_entry_pin(), BEL.find_execute_pin(sh))
    box(fh, "Set hue drift", "Story hue 0..1: soft yellow > honey > amber > ochre; luminance never changes.", -40, -70, 720, 230, "api")

    fm = GE.create_and_edit_function_graph(bp, "SetMenuMode")
    fm.add_graph_input_parameter("Enabled", BEL.get_basic_type_by_name("bool"), "true")
    entry = PL.get_owning_node(fm.find_graph_entry_pin())
    menu = pin(entry, "Enabled", True)
    to_f = fn(fm, KM, "Conv_BoolToDouble", 300, 200)
    link(menu, pin(to_f, "InBool"))
    st = setv(fm, "MenuTarget", 300, 0, value_out(to_f))
    sel = fn(fm, KM, "SelectFloat", 620, 200, A=1.0, B=0.4)
    link(menu, pin(sel, "bPickA"))
    ss = setv(fm, "MenuSpeed", 620, 0, value_out(sel))
    br = place(fm.add_branch_node(), 940, 0)
    link(menu, BEL.find_condition_pin(br))
    hue = set_mpc(fm, "HueDrift", 1200, -60, 0.0)
    arm = fn(fm, KSL, "K2_SetTimer", 1580, -60, FunctionName="MenuGlitch", Time=6.0)
    clear = fn(fm, KSL, "K2_ClearTimer", 1200, 220, FunctionName="MenuGlitch")
    link(fm.find_graph_entry_pin(), BEL.find_execute_pin(st))
    chain(st, ss, br)
    link(BEL.find_then_pin(br), BEL.find_execute_pin(hue))
    chain(hue, arm)
    link(BEL.find_else_pin(br), BEL.find_execute_pin(clear))
    box(fm, "Set menu mode", "Menu: blend to the menu look in ~1 s, hue at its tutorial value, rare glitch flickers. "
        "Off: back to gameplay in ~2.5 s.", -40, -130, 1960, 400, "menu")

    fg = GE.create_and_edit_function_graph(bp, "TriggerGlitchBurst")
    fg.add_graph_input_parameter("Strength", real, "1.0")
    fg.add_graph_input_parameter("Seconds", real, "0.5")
    entry = PL.get_owning_node(fg.find_graph_entry_pin())
    sg = set_mpc(fg, "GlitchAmount", 320, 0, pin(entry, "Strength", True))
    mo = fn(fg, KM, "Multiply_DoubleDouble", 320, 220, B=0.6)
    link(pin(entry, "Strength", True), pin(mo, "A"))
    sm = set_mpc(fg, "MoshAmount", 700, 0, value_out(mo))
    tm = fn(fg, KSL, "K2_SetTimer", 1080, 0, FunctionName="EndGlitchBurst")
    link(pin(entry, "Seconds", True), pin(tm, "Time"))
    # menu mode only: the title datamosh (blocks drag the frame down 0.5-1.2 s, MF_Dream_GlitchUV) needs a start + seed
    gm = fn(fg, KM, "Greater_DoubleDouble", 1420, 220, B=0.5)
    link(value_out(get(fg, "MenuTarget", 1180, 260)), pin(gm, "A"))
    br = place(fg.add_branch_node(), 1440, 0)
    link(value_out(gm), BEL.find_condition_pin(br))
    # MoshSeed = a random integer (which bands and blocks drag) + Seconds/4 (the hold, for the 0.25 s ragged release)
    ri = fn(fg, KM, "Conv_IntToDouble", 1720, 220)
    link(value_out(fn(fg, KM, "RandomIntegerInRange", 1480, 300, Min=1, Max=999)), pin(ri, "InInt"))
    hs = fn(fg, KM, "FMin", 1720, 340, B=3.99)
    link(pin(entry, "Seconds", True), pin(hs, "A"))
    q = fn(fg, KM, "Multiply_DoubleDouble", 1960, 340, B=0.25)
    link(value_out(hs), pin(q, "A"))
    sv = fn(fg, KM, "Add_DoubleDouble", 1960, 220)
    link(value_out(ri), pin(sv, "A"))
    link(value_out(q), pin(sv, "B"))
    seed = set_mpc(fg, "MoshSeed", 2200, 0, value_out(sv))
    start = set_mpc(fg, "MoshStart", 2580, 0, value_out(fn(fg, GS, "GetTimeSeconds", 2580, 220)))
    link(fg.find_graph_entry_pin(), BEL.find_execute_pin(sg))
    chain(sg, sm, tm, br)
    link(BEL.find_then_pin(br), BEL.find_execute_pin(seed))
    chain(seed, start)
    box(fg, "Trigger glitch burst", "Strength 0..1 for Seconds: glitch + mosh at once; the EndGlitchBurst timer brings "
        "the tier baseline back; in menu mode the blocks also drag (MoshStart, MoshSeed). Materials gate it with "
        "ReduceMotion.", -40, -70, 2900, 460, "glitch")

    ft = GE.create_and_edit_function_graph(bp, "SetTier")
    ft.add_graph_input_parameter("Tier", BEL.get_basic_type_by_name("int"), "0")
    entry = PL.get_owning_node(ft.find_graph_entry_pin())
    tf = fn(ft, KM, "Conv_IntToDouble", 300, 220)
    link(pin(entry, "Tier", True), pin(tf, "InInt"))
    tg = fn(ft, KM, "Multiply_DoubleDouble", 560, 220, B=0.0)
    link(value_out(tf), pin(tg, "A"))
    stv = setv(ft, "TierGlitch", 560, 0, value_out(tg))
    sgm = set_mpc(ft, "GlitchAmount", 880, 0, value_out(stv))
    tb = fn(ft, KM, "Multiply_DoubleDouble", 1180, 220, B=0.5)
    link(value_out(tf), pin(tb, "A"))
    sb = set_mpc(ft, "OpenTier", 1260, 0, value_out(tb))
    ctv = setv(ft, "CurrentTier", 1640, 0, pin(entry, "Tier", True))
    link(ft.find_graph_entry_pin(), BEL.find_execute_pin(stv))
    chain(stv, sgm, sb, ctv)
    box(ft, "Set dream tier", "0 Plausible / 1 Suspicious / 2 Open: MPC OpenTier 0 / 0.5 / 1 lerps the look toward its Open "
        "values (look-dev recipe: echo, slips, tears, sort).", -40, -70, 1640, 400, "api")

    fl = GE.create_and_edit_function_graph(bp, "SetLook")
    fl.add_graph_input_parameter("Look", BEL.get_basic_type_by_name("int"), "0")
    entry = PL.get_owning_node(fl.find_graph_entry_pin())
    lf = fn(fl, KM, "Conv_IntToDouble", 300, 220)
    link(pin(entry, "Look", True), pin(lf, "InInt"))
    sl = set_mpc(fl, "LookIndex", 300, 0, value_out(lf))
    link(fl.find_graph_entry_pin(), BEL.find_execute_pin(sl))
    box(fl, "Set look-dev look", "Look-dev look 0 A Silver print / 1 B Etched / 2 C Smoke nocturne / 3 D Time slip (MPC LookIndex).",
        -40, -70, 700, 400, "api")
    fr = GE.create_and_edit_function_graph(bp, "SetColorReveal")
    fr.add_graph_input_parameter("Amount", real, "1.0")
    fr.add_graph_input_parameter("BlendSeconds", real, "1.0")
    entry = PL.get_owning_node(fr.find_graph_entry_pin())
    r1 = setv(fr, "RevealTarget", 300, 0, pin(entry, "Amount", True))
    mxr = fn(fr, KM, "FMax", 300, 220, B=0.05)
    link(pin(entry, "BlendSeconds", True), pin(mxr, "A"))
    ir = fn(fr, KM, "Divide_DoubleDouble", 560, 220, A=1.0)
    link(value_out(mxr), pin(ir, "B"))
    r2 = setv(fr, "RevealSpeed", 640, 0, value_out(ir))
    link(fr.find_graph_entry_pin(), BEL.find_execute_pin(r1))
    chain(r1, r2)
    box(fr, "Set colour reveal", "Amount 0..1 of real colour over the whole frame, reached in BlendSeconds (T9 payoff).",
        -40, -70, 1000, 400, "api")
    retro_color(bp)


def sand_bloom(bp):
    """Stage 5 (needs sandvfx's BPL_SandFX): AmbientBloomTick calls SpawnAmbientBloom(CurrentTier), then re-arms itself
    sooner at higher tiers (8-14 s at tier 0, half that at tier 1, a third at tier 2). BeginPlay arms the first one."""
    fb = GE.create_and_edit_function_graph(bp, "AmbientBloomTick")
    lib = BEL.generated_class(unreal.load_asset(BPL)).get_path_name()
    sp = place(fb.add_call_function_node(f"{lib}:SpawnAmbientBloom"), 300, 0)
    link(value_out(get(fb, "CurrentTier", 60, 220)), pin(sp, "Tier"))
    ti = fn(fb, KM, "Conv_IntToDouble", 560, 300)
    link(value_out(get(fb, "CurrentTier", 340, 320)), pin(ti, "InInt"))
    t1 = fn(fb, KM, "Add_DoubleDouble", 800, 300, B=1.0)
    link(value_out(ti), pin(t1, "A"))
    rnd = fn(fb, KM, "RandomFloatInRange", 800, 440, Min=8.0, Max=14.0)
    dv = fn(fb, KM, "Divide_DoubleDouble", 1040, 300)
    link(value_out(rnd), pin(dv, "A"))
    link(value_out(t1), pin(dv, "B"))
    tm = fn(fb, KSL, "K2_SetTimer", 1280, 0, FunctionName="AmbientBloomTick")
    link(value_out(dv), pin(tm, "Time"))
    link(fb.find_graph_entry_pin(), BEL.find_execute_pin(sp))
    chain(sp, tm)
    box(fb, "Ambient sand bloom", "sandvfx's BPL_SandFX.SpawnAmbientBloom at the current tier, re-armed sooner as the "
        "tier rises.", -40, -70, 1620, 600, "glitch")


def patch_set_shift_streak(bp):
    """Stage 2e: SetShiftStreak writes MPC ShiftStreak itself (the Tick only writes while a pulse decays). In place."""
    f1 = GE.get_graph_editor(BEL.find_graph(bp, "SetShiftStreak"))
    nodes = list(f1.list_all_nodes())
    if any("Vector Parameter" in str(BEL.get_node_title(n)) for n in nodes):
        return
    a3 = next(n for n in nodes if "StreakBase" in str(BEL.get_node_title(n)))
    entry = PL.get_owning_node(f1.find_graph_entry_pin())
    mk = fn(f1, KM, "MakeColor", 1260, 220)
    for ch, src in (("R", "Length"), ("G", "Angle"), ("B", "Intensity")):
        link(pin(entry, src, True), pin(mk, ch))
    link(value_out(get(f1, "StreakThreshold", 1040, 420)), pin(mk, "A"))
    a4 = set_mpc(f1, "ShiftStreak", 1260, 0, value_out(mk), vector=True)
    link(BEL.find_then_pin(a3), BEL.find_execute_pin(a4))


# Blueprint compiles go through Hayba (editor-rules, 20:40): each stage is its own ue_remote run, then Hayba
# blueprint_compile + asset_save before the next, because later stages call functions the earlier ones made.
STAGES = {"1": None, "2": "SetEchoStrength", "3": "SetStyleMode", "4": "StopStyleCycle", "5": "AmbientBloomTick"}  # stage -> first graph it makes


def run(stage):
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(["/Game/FoA/PostProcess"], True)
    if stage == "1":
        stage1()
    elif stage == "2e":  # redo the event graph in place (idle gating) without touching the functions others call
        bp = unreal.load_asset(PATH)
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
        ed = GE.get_graph_editor(BEL.find_event_graph(bp))
        assert not BEL.find_graph(bp, "StopStyleCycle"), "run 2e before stage 4 (stage 4 adds events to this graph)"
        for c in list(ed.list_comment_nodes()):
            ed.remove_comment_node(c)
        ed.remove_nodes(list(ed.list_all_nodes()))
        stage2_events(bp, ed)
        patch_set_shift_streak(bp)
    else:
        bp = unreal.load_asset(PATH)
        assert bp and not BEL.find_graph(bp, STAGES[stage]), f"stage {stage}: needs stage {int(stage) - 1} and no {STAGES[stage]}"
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
        ed = GE.get_graph_editor(BEL.find_event_graph(bp))
        if stage == "2":
            # stage 2 is the first to fill the event graph: start it clean, so a run that failed half way can repeat
            for c in list(ed.list_comment_nodes()):
                ed.remove_comment_node(c)
            ed.remove_nodes(list(ed.list_all_nodes()))
            stage2(bp, ed)
        elif stage == "3":
            retro_modes(bp)
            streak_api(bp)
        elif stage == "4":
            retro_events(bp, ed)
            letterbox_api(bp)
        else:
            assert EAL.does_asset_exist(BPL), "stage 5 waits for sandvfx's BPL_SandFX"
            sand_bloom(bp)
    settle()
    print(f"BP_DreamDirector stage {stage} built: now Hayba blueprint_compile + asset_save {PATH}")


run(os.environ.pop("FOA_STAGE"))
