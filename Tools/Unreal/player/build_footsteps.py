"""Surface-aware footsteps: AN_FoA_FootPlant (Blueprint AnimNotify, Foot = bone name per instance). On a plant it traces
40 cm down from that foot; a hit actor tagged "Sand" (look lane tags the walkable sand) gets BPL_SandFX.SpawnSandStep at
the impact point (its own puff and sand step sound), anything else the wood step. Lives on the clips, so any character
playing them gets it. Re-runnable.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_footsteps.py FOA_AREAS=/Game/FoA/Characters/Player FOA_STEP=class|graph|clips
class  create the notify Blueprint and its Foot variable (compile with Hayba next)
graph  Received_Notify: trace, branch on the Sand tag, sand step or wood step (compile next)
clips  swap the wood PlaySound notifies on the walk clip (and AS_GASP_* when present) for AN_FoA_FootPlant"""
import importlib
import os
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link, value = graph_style.at, graph_style.box, graph_style.link, graph_style.value
P = "/Game/FoA/Characters/Player"
AN = P + "/Anims/AN_FoA_FootPlant"
WOOD = "/Game/FoA/Audio/MetaSounds/Footsteps/S_Footsteps_WoodWalk"
SAND_LIB = "/Game/FoA/VFX/Sand/BPL_SandFX"
EAL, BEL, AL = unreal.EditorAssetLibrary, unreal.BlueprintEditorLibrary, unreal.AnimationLibrary
BGE, PIN = unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary


def step_class():
    bp = unreal.load_asset(AN)
    if not bp:
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.AnimNotify)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("AN_FoA_FootPlant", P + "/Anims", unreal.Blueprint, f)
    # The notify Blueprint has no EventGraph (graph_style.ensure_variable needs one): Foot is added with Hayba
    #   blueprint_add_variable {"path": AN, "variable_name": "Foot", "variable_type": "name"}, then made editable here.
    assert "Foot" in [str(v) for v in BEL.list_member_variable_names(bp, False)], "add Foot with Hayba first (see above)"
    BEL.set_blueprint_variable_instance_editable(bp, "Foot", True)
    EAL.save_loaded_asset(bp, False)
    print("class", bp.get_path_name(), [str(g) for g in BEL.list_graph_names(bp)])


def step_graph():
    bp = unreal.load_asset(AN)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    names = [str(g) for g in BEL.list_graph_names(bp)]
    if "Received_Notify" not in names:
        BEL.add_function_override(bp, "Received_Notify")
    ed = BGE.get_graph_editor_by_name(bp, "Received_Notify")
    for n in list(ed.list_all_nodes()):
        if n.get_class().get_name() not in ("K2Node_FunctionEntry", "K2Node_FunctionResult"):
            ed.remove_nodes([n])
    for c in list(ed.list_comment_nodes()):
        ed.remove_comment_node(c)
    entry = PIN.get_owning_node(ed.find_graph_entry_pin())
    result = next((n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"), None)
    at(entry, 0, 0)
    call = lambda path, x, y: at(ed.add_call_function_node(path), x, y)  # noqa: E731

    def ctx(node):  # UAnimNotify resolves its world from the notified mesh; wire the pin only where it is exposed
        if "WorldContextObject" in [str(PIN.get_pin_name(q)) for q in BEL.list_input_pins(node)]:
            link(entry, "MeshComp", node, "WorldContextObject")
    foot = at(ed.add_get_member_variable_node("Foot", ""), 0, 200)
    loc = call("/Script/Engine.SceneComponent:GetSocketLocation", 220, 160)
    up = call("/Script/Engine.KismetMathLibrary:MakeVector", 220, 320)
    down = call("/Script/Engine.KismetMathLibrary:MakeVector", 220, 460)
    start = call("/Script/Engine.KismetMathLibrary:Add_VectorVector", 480, 220)
    end = call("/Script/Engine.KismetMathLibrary:Add_VectorVector", 480, 380)
    trace = call("/Script/Engine.KismetSystemLibrary:LineTraceSingle", 740, 0)
    brk = call("/Script/Engine.GameplayStatics:BreakHitResult", 1060, 220)
    tag = call("/Script/Engine.Actor:ActorHasTag", 1340, 300)
    valid = call("/Script/Engine.KismetSystemLibrary:IsValid", 1060, 420)
    hit = at(ed.add_branch_node(), 1320, 0)
    br = at(ed.add_branch_node(), 1760, 0)
    lib = unreal.load_asset(SAND_LIB)
    assert lib, SAND_LIB
    sand = call(lib.generated_class().get_path_name() + ":SpawnSandStep", 2020, -80)
    wood = call("/Script/Engine.GameplayStatics:PlaySoundAtLocation", 2020, 140)
    link(entry, "MeshComp", loc, "self")
    link(foot, "Foot", loc, "InSocketName")
    value(up, "Z", "10.0")
    value(down, "Z", "-30.0")
    link(loc, "ReturnValue", start, "A")
    link(up, "ReturnValue", start, "B")
    link(loc, "ReturnValue", end, "A")
    link(down, "ReturnValue", end, "B")
    link(entry, None, trace, None)
    ctx(trace)
    link(start, "ReturnValue", trace, "Start")
    link(end, "ReturnValue", trace, "End")
    link(trace, "OutHit", brk, "Hit")
    link(brk, "HitActor", tag, "self")
    value(tag, "Tag", "Sand")
    # Blueprint pure AND evaluates both inputs: gate execution before ActorHasTag can read a missed hit.
    link(brk, "HitActor", valid, "Object")
    link(trace, None, hit, None)
    link(valid, "ReturnValue", hit, "Condition")
    link(hit, "Then", br, None)
    link(tag, "ReturnValue", br, "Condition")
    link(br, "Then", sand, None)
    ctx(sand)
    loc_pin = next(str(PIN.get_pin_name(q)) for q in BEL.list_input_pins(sand)
                   if str(PIN.get_pin_name(q)) not in ("execute", "WorldContextObject", "self"))
    link(brk, "ImpactPoint", sand, loc_pin)
    link(br, "Else", wood, None)
    ctx(wood)
    value(wood, "Sound", WOOD)
    link(loc, "ReturnValue", wood, "Location")
    made = [foot, loc, up, down, start, end, trace, brk, valid, hit, tag, br, sand, wood]
    if result:
        at(result, 2340, 0)
        link(sand, None, result, None)
        link(wood, None, result, None)
        link(hit, "Else", result, None)
        made.append(result)
    box(ed, "Foot plant", "", [entry] + made, "anim")
    EAL.save_loaded_asset(bp, False)
    print("graph: Received_Notify -> trace -> Sand ? SpawnSandStep : wood step")


def step_clips():
    import build_loco
    importlib.reload(build_loco)  # plant_times: heel strike before each mid-stance
    cls = EAL.load_blueprint_class(AN)
    assert cls, AN + " (compile it first)"
    paths = [P + "/Anims/Loco/AS_FoA_Walk_Brisk"] + [a.split(".")[0] for a in EAL.list_assets(P + "/Anims/GASP", recursive=False)
                                                       if a.split("/")[-1].startswith("AS_GASP_")]
    for path in paths:
        seq = unreal.load_asset(path)
        if not isinstance(seq, unreal.AnimSequence):
            continue
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
        if "Footsteps" not in [str(t) for t in AL.get_animation_notify_track_names(seq)]:
            continue
        times = [(t, f"foot_{side}") for side, ts in build_loco.plant_times(seq).items() for t in ts]
        AL.remove_animation_notify_events_by_track(seq, "Footsteps")
        for t, foot in times:
            n = AL.add_animation_notify_event(seq, "Footsteps", t, cls)
            n.set_editor_property("Foot", foot)
        EAL.save_loaded_asset(seq, False)
        print("clips:", seq.get_name(), [(round(t, 3), f) for t, f in times])


try:
    {"class": step_class, "graph": step_graph, "clips": step_clips}[os.environ["FOA_STEP"]]()
except Exception as e:  # Hayba truncates long traceback lines: name the failure on short lines
    import traceback
    for fr in traceback.extract_tb(e.__traceback__)[-2:]:
        print("AT", fr.lineno, fr.line)
    print("ERR", type(e).__name__, str(e)[:400])
    raise
