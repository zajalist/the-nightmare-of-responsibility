"""Cache controls on settings apply; triggered Aim scales its two axes without Tick or disk reads."""
import sys
sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc
from build_interaction_lock import command, OWNER, P
from wire_suit import add, connect, pin

PARENT = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
SETTINGS = "/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C"


def main():
    assert not command("editor_get_state")["pie_running"], "Exit PIE before wiring look controls"
    lease = hc.lease_acquire(OWNER, ["asset:/Game/FoA/Characters", "asset:" + PARENT], ttl_s=120, wait_s=20)
    try:
        info = command("blueprint_get_info", path=PARENT)
        command("blueprint_add_variable", path=PARENT, variable_name="LookScale", variable_type="vector",
                default_value="(X=1,Y=1,Z=0)", category="Controls", update_existing=True)
        if "ApplyLookSettings" not in info["functions"]:
            command("blueprint_add_function", path=PARENT, function_name="ApplyLookSettings",
                    inputs=[{"name": "Settings", "type": "object:" + SETTINGS}])
        graph = command("blueprint_inspect_graph", path=PARENT, graph_name="ApplyLookSettings")
        entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "ApplyLookSettings")
        ops = []
        old = [n["node_id"] for n in graph["nodes"] if n["node_id"] != entry]
        if old:
            ops.append({"op": "remove", "node_ids": old})
        for ref, kind, x, y, args in (
                ("valid", "call_function", 0, 200, {"function_name": "/Script/Engine.KismetSystemLibrary:IsValid"}),
                ("branch", "branch", 250, 0, {}),
                ("sensitivity", "variable_get", 250, 220, {"variable_name": "MouseSensitivity", "class_path": SETTINGS}),
                ("invert", "variable_get", 250, 400, {"variable_name": "bInvertY", "class_path": SETTINGS}),
                ("clamp", "call_function", 500, 220, {"function_name": "/Script/Engine.KismetMathLibrary:FClamp"}),
                ("negative", "call_function", 760, 380, {"function_name": "/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble"}),
                ("signed", "call_function", 1020, 280, {"function_name": "/Script/Engine.KismetMathLibrary:SelectFloat"}),
                ("scale", "call_function", 1280, 220, {"function_name": "/Script/Engine.KismetMathLibrary:MakeVector"}),
                ("remember", "variable_set", 1560, 0, {"variable_name": "LookScale"})):
            add(ops, ref, kind, x, y, **args)
        for a, b, ap, bp in ((entry, "valid", "Settings", "Object"), (entry, "branch", "then", "execute"),
                              ("valid", "branch", "ReturnValue", "Condition"),
                              (entry, "sensitivity", "Settings", "self"), (entry, "invert", "Settings", "self"),
                              ("sensitivity", "clamp", "MouseSensitivity", "Value"),
                              ("clamp", "negative", "ReturnValue", "A"), ("negative", "signed", "ReturnValue", "A"),
                              ("clamp", "signed", "ReturnValue", "B"), ("invert", "signed", "bInvertY", "bPickA"),
                              ("clamp", "scale", "ReturnValue", "X"), ("signed", "scale", "ReturnValue", "Y"),
                              ("branch", "remember", "then", "execute"), ("scale", "remember", "ReturnValue", "LookScale")):
            connect(ops, a, b, ap, bp)
        pin(ops, "clamp", "Min", "0.25")
        pin(ops, "clamp", "Max", "2.5")
        pin(ops, "negative", "B", "-1")
        command("blueprint_graph_batch", path=PARENT, graph_name="ApplyLookSettings", ops=ops, compile=True, save=True)
        graph = command("blueprint_inspect_graph", path=PARENT, graph_name="Aim")
        if not any(n["title"] == "Get LookScale" for n in graph["nodes"]):
            entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "Aim")
            yaw = next(n["node_id"] for n in graph["nodes"] if n["title"] == "AddControllerYawInput")
            pitch = next(n["node_id"] for n in graph["nodes"] if n["title"] == "AddControllerPitchInput")
            remove = [n["node_id"] for n in graph["nodes"] if n["title"] in ("Reroute Node", "Comment")]
            ops = [{"op": "remove", "node_ids": remove}, {"op": "disconnect", "node_id": yaw, "pin_name": "Val"}]
            add(ops, "scale", "variable_get", 0, 220, variable_name="LookScale")
            add(ops, "xy", "call_function", 240, 220, function_name="/Script/Engine.KismetMathLibrary:BreakVector")
            add(ops, "yaw_scale", "call_function", 480, 100, function_name="/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble")
            add(ops, "pitch_scale", "call_function", 480, 320, function_name="/Script/Engine.KismetMathLibrary:Multiply_DoubleDouble")
            for a, b, ap, bp in (("scale", "xy", "LookScale", "InVec"), (entry, "yaw_scale", "X Axis", "A"),
                                  (entry, "pitch_scale", "Y Axis", "A"), ("xy", "yaw_scale", "X", "B"),
                                  ("xy", "pitch_scale", "Y", "B"), ("yaw_scale", yaw, "ReturnValue", "Val"),
                                  ("pitch_scale", pitch, "ReturnValue", "Val")):
                connect(ops, a, b, ap, bp)
            ops.append({"op": "comment", "title": "Look response", "node_ids": [entry, yaw, pitch, "scale", "xy", "yaw_scale", "pitch_scale"], "color": [0.2, 0.32, 0.55]})
            ops.append({"op": "fit_comments"})
            command("blueprint_graph_batch", path=PARENT, graph_name="Aim", ops=ops, compile=True, save=True)
        graph = command("blueprint_inspect_graph", path=P, graph_name="EventGraph")
        if not any(n["title"] == "ApplyLookSettings" for n in graph["nodes"]):
            entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "Event BeginPlay")
            following = next(e for e in graph["edges"] if e["from_node"] == entry and e["from_pin"] == "then")
            ops = [{"op": "disconnect", "node_id": entry, "pin_name": "then"}]
            add(ops, "load", "call_function", -2200, 1500, function_name="/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C:LoadSettings")
            add(ops, "apply", "call_function", -1850, 1500, function_name=PARENT + ".BP_ThirdPersonCharacter_C:ApplyLookSettings")
            connect(ops, entry, "load")
            connect(ops, "load", "apply")
            connect(ops, "load", "apply", "Settings", "Settings")
            connect(ops, "apply", following["to_node"], bp=following["to_pin"])
            ops.append({"op": "comment", "title": "Load controls once", "node_ids": ["load", "apply"], "color": [0.2, 0.32, 0.55]})
            ops.append({"op": "fit_comments"})
            command("blueprint_graph_batch", path=P, graph_name="EventGraph", ops=ops, compile=True, save=True)
        print("Look sensitivity and invert Y: cached settings apply, two triggered input multipliers, no Tick/disk reads")
    finally:
        hc.release(OWNER, lease)


if __name__ == "__main__":
    main()
