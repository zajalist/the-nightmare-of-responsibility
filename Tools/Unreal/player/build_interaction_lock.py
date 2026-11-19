"""Use Hayba C++ to give interaction timers their own balanced, idempotent movement lock.
Run outside the editor after PIE ends, before rebuilding player/host graphs.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc

P = "/Game/FoA/Characters/Player/BP_FoAPlayer"
OWNER = "character_resume"
trace = []


def command(name, **params):
    reply = hc.call(name, params, owner=OWNER)
    trace.append({"command": name, "params": params, "reply": reply})
    assert reply.get("ok"), reply
    result = reply.get("data", {})
    assert result.get("ok", True), result
    if "compile" in result:
        assert result["compile"].get("error_count", 0) == 0, result
    return result


def replace_lock(graph_name, old_title, enabled):
    graph = command("blueprint_inspect_graph", path=P, graph_name=graph_name)
    old = [n for n in graph["nodes"] if n["title"] == old_title]
    if not old:
        assert any(n["title"] == "SetInteractionLocked" for n in graph["nodes"]), graph_name
        return
    assert len(old) == 1, (graph_name, old)
    node = old[0]["node_id"]
    before = [e for e in graph["edges"] if e["to_node"] == node and e["to_pin"] == "execute"]
    after = [e for e in graph["edges"] if e["from_node"] == node and e["from_pin"] == "then"]
    assert before, (graph_name, "lock is not on an execution path")
    remove = [node]
    for e in graph["edges"]:
        if e["to_node"] == node and e["to_pin"] == "self" and not any(
                other["from_node"] == e["from_node"] and other["to_node"] != node for other in graph["edges"]):
            remove.append(e["from_node"])
    ops = [{"op": "remove", "node_ids": remove},
           {"op": "add_node", "ref": "lock", "node_type": "call_function",
            "function_name": P + ".BP_FoAPlayer_C:SetInteractionLocked", "x": 260, "y": 0},
           {"op": "set_pin", "node_id": "lock", "pin_name": "bEnable", "value": str(enabled).lower()}]
    ops += [{"op": "connect", "from_node": e["from_node"], "from_pin": e["from_pin"],
             "to_node": "lock"} for e in before]
    ops += [{"op": "connect", "from_node": "lock", "to_node": e["to_node"], "to_pin": e["to_pin"]} for e in after]
    ops += [{"op": "fit_comments"}]
    command("blueprint_graph_batch", path=P, graph_name=graph_name, ops=ops, compile=True, save=True)


def main():
    assert not command("editor_get_state")["pie_running"], "Exit PIE before editing player graphs"
    lease = hc.lease_acquire(OWNER, ["asset:/Game/FoA/Characters"], ttl_s=120, wait_s=30)
    try:
        info = command("blueprint_get_info", path=P)
        command("blueprint_add_variable", path=P, variable_name="bInteractionLocked", variable_type="bool",
                default_value="false", category="FoA|Movement", update_existing=True)
        if "SetInteractionLocked" not in info["functions"]:
            command("blueprint_add_function", path=P, function_name="SetInteractionLocked",
                    inputs=[{"name": "bEnable", "type": "bool"}])
        graph = command("blueprint_inspect_graph", path=P, graph_name="SetInteractionLocked")
        entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "SetInteractionLocked")
        ops = []
        old = [n["node_id"] for n in graph["nodes"] if n["node_id"] != entry]
        if old:
            ops.append({"op": "remove", "node_ids": old})
        for ref, kind, extra, x, y in (
                ("stop_jump", "call_function", {"function_name": "/Script/Engine.Character:StopJumping"}, 180, -180),
                ("held", "variable_get", {"variable_name": "bInteractionLocked"}, 0, 220),
                ("different", "call_function", {"function_name": "/Script/Engine.KismetMathLibrary:NotEqual_BoolBool"}, 240, 220),
                ("changed", "branch", {}, 460, 0),
                ("controller", "call_function", {"function_name": "/Script/Engine.Pawn:GetController"}, 460, 320),
                ("valid", "call_function", {"function_name": "/Script/Engine.KismetSystemLibrary:IsValid"}, 700, 320),
                ("owned", "branch", {}, 920, 0),
                ("hold", "call_function", {"function_name": "/Script/Engine.Controller:SetIgnoreMoveInput"}, 1160, 0),
                ("remember", "variable_set", {"variable_name": "bInteractionLocked"}, 1450, 0)):
            ops.append({"op": "add_node", "ref": ref, "node_type": kind, "x": x, "y": y, **extra})
        for a, ap, b, bp in (
                (entry, "then", "stop_jump", "execute"), ("stop_jump", "then", "changed", "execute"), (entry, "bEnable", "different", "B"),
                ("held", "bInteractionLocked", "different", "A"), ("different", "ReturnValue", "changed", "Condition"),
                ("changed", "then", "owned", "execute"), ("controller", "ReturnValue", "valid", "Object"),
                ("valid", "ReturnValue", "owned", "Condition"), ("owned", "then", "hold", "execute"),
                ("controller", "ReturnValue", "hold", "self"), (entry, "bEnable", "hold", "bNewMoveInput"),
                ("hold", "then", "remember", "execute"), (entry, "bEnable", "remember", "bInteractionLocked")):
            ops.append({"op": "connect", "from_node": a, "from_pin": ap, "to_node": b, "to_pin": bp})
        ops += [{"op": "comment", "title": "Interaction input", "node_ids": [entry, "held", "different", "changed",
                 "controller", "valid", "owned", "hold", "remember"], "color": [0.22, 0.4, 0.2]}, {"op": "fit_comments"}]
        command("blueprint_graph_batch", path=P, graph_name="SetInteractionLocked", ops=ops, compile=True, save=True)
        replace_lock("PlayInteraction", "SetIgnoreMoveInput", True)
        replace_lock("EventGraph", "SetIgnoreMoveInput", True)
        replace_lock("EndInteraction", "ResetIgnoreMoveInput", False)
        print("Interaction owns one balanced movement-input hold; delayed timers cannot reset battle locks")
    finally:
        hc.release(OWNER, lease)
        Path("P:/FoA/Saved/CharacterShots/interaction_lock_build.json").write_text(json.dumps(trace, indent=2))


if __name__ == "__main__":
    main()
