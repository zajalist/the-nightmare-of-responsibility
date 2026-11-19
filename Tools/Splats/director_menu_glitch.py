"""BP_DreamDirector.TriggerGlitchBurst: in menu mode the burst's GlitchAmount is 0.35 x Strength (the title datamosh
stays block-based over a mostly intact frame, the ui lane's page v3.1); MoshAmount keeps 0.6 x Strength. Gameplay
bursts (menu mode off) are unchanged. Idempotent: does nothing if the SelectFloat is already in place.
  FOA_DD=probe : print the function graph's call nodes and pins only
  python Tools/Unreal/ue_remote.py Tools/Splats/director_menu_glitch.py [FOA_DD=probe]
Compile and save afterwards with Hayba blueprint_compile + the save step."""
import os

import unreal

BEL, GE, PL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
KM = "/Script/Engine.KismetMathLibrary"


def run():
    bp = unreal.load_asset("/Game/FoA/PostProcess/BP_DreamDirector")
    ed = GE.get_graph_editor_by_name(bp, "TriggerGlitchBurst")
    nodes = list(ed.list_nodes_of_class(unreal.K2Node_CallFunction))
    info = {}
    for n in nodes:
        t = str(BEL.get_node_title(n)).replace("\n", " ")
        pins = {str(PL.get_pin_name(p)): str(PL.get_pin_value(p)) for p in BEL.list_all_pins(n)}
        info.setdefault(t, []).append((n, pins))
    if os.environ.get("FOA_DD") == "probe":
        print("TITLES", sorted(info))
        return
    if any("SelectFloat" in t.replace(" ", "") for t in info):
        print("already in place")
        return
    glitch = next(n for t, lst in info.items() for n, pins in lst
                  if "SetScalarParameterValue" in t.replace(" ", "") and pins.get("ParameterName") == "GlitchAmount")
    greater = next(n for t, lst in info.items() for n, pins in lst if ">" in t)
    strength = BEL.find_output_pin(list(ed.list_nodes_of_class(unreal.K2Node_FunctionEntry))[0], "Strength")
    sel = ed.add_call_function_node(f"{KM}:SelectFloat")
    mul = ed.add_call_function_node(f"{KM}:Multiply_DoubleDouble")
    BEL.set_node_pos(sel, unreal.IntPoint(320, 380))
    BEL.set_node_pos(mul, unreal.IntPoint(560, 300))
    assert PL.set_pin_value(BEL.find_input_pin(sel, "A"), "0.35") and PL.set_pin_value(BEL.find_input_pin(sel, "B"), "1.0")
    for a, b in ((BEL.find_output_pin(greater, "ReturnValue"), BEL.find_input_pin(sel, "bPickA")),
                 (strength, BEL.find_input_pin(mul, "A")),
                 (BEL.find_output_pin(sel, "ReturnValue"), BEL.find_input_pin(mul, "B")),
                 (BEL.find_output_pin(mul, "ReturnValue"), BEL.find_input_pin(glitch, "ParameterValue"))):
        assert PL.try_create_connection(a, b), (PL.get_pin_name(a), PL.get_pin_name(b))
    print("menu-mode GlitchAmount = 0.35 x Strength wired")


run()
