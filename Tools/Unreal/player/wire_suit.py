"""Gate the fitted suit and masked body to Suit equip, and restore the original body on every UnequipAll."""
from pathlib import Path
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
import hayba_call as hc
from build_interaction_lock import command, P, OWNER

CLOTH = "/Game/FoA/Characters/Player/Clothing"
ORIGINAL = "/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh"


def add(ops, ref, kind, x, y, **params):
    ops.append({"op": "add_node", "ref": ref, "node_type": kind, "x": x, "y": y, **params})


def connect(ops, a, b, ap="then", bp="execute"):
    ops.append({"op": "connect", "from_node": a, "from_pin": ap, "to_node": b, "to_pin": bp})


def pin(ops, node, name, value):
    ops.append({"op": "set_pin", "node_id": node, "pin_name": name, "value": value})


def main():
    assert not command("editor_get_state")["pie_running"], "Exit PIE before wiring clothing"
    lease = hc.lease_acquire(OWNER, ["asset:/Game/FoA/Characters"], ttl_s=120, wait_s=20)
    try:
        info = command("blueprint_get_info", path=P)
        if "SetSuitedBody" not in info["functions"]:
            command("blueprint_add_function", path=P, function_name="SetSuitedBody", inputs=[{"name": "bEnable", "type": "bool"}])
        graph = command("blueprint_inspect_graph", path=P, graph_name="SetSuitedBody")
        entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "SetSuitedBody")
        ops = []
        old = [n["node_id"] for n in graph["nodes"] if n["node_id"] != entry]
        if old:
            ops.append({"op": "remove", "node_ids": old})
        add(ops, "branch", "branch", 240, 0)
        add(ops, "body", "variable_get", 240, 300, variable_name="Body")
        add(ops, "starter", "variable_get", 500, 350, variable_name="StartOutfit")
        connect(ops, entry, "branch")
        connect(ops, entry, "branch", "bEnable", "Condition")
        for enabled, ref, mesh, y, branch_pin in ((True, "suited", CLOTH + "/SK_FoA_Body_Suited", -100, "then"),
                                                (False, "original", ORIGINAL, 700, "else")):
            add(ops, ref, "call_function", 500, y, function_name="/Script/Engine.SkeletalMeshComponent:SetSkeletalMeshAsset")
            connect(ops, "branch", ref, branch_pin)
            connect(ops, "body", ref, "Body", "self")
            pin(ops, ref, "NewMesh", mesh)
            show = ref + "_starter"
            add(ops, show, "call_function", 840, y, function_name="/Script/Engine.SceneComponent:SetVisibility")
            connect(ops, ref, show)
            connect(ops, "starter", show, "StartOutfit", "self")
            pin(ops, show, "bNewVisibility", str(not enabled).lower())
            previous = show
            if enabled:
                for i, slot in enumerate(("Shirt", "Trousers", "Socks", "Tie")):
                    add(ops, slot, "variable_get", 1160 + 320 * i, 250, variable_name=slot)
                    add(ops, slot + "_hide", "call_function", 1160 + 320 * i, y, function_name="/Script/Engine.SceneComponent:SetVisibility")
                    connect(ops, previous, slot + "_hide")
                    connect(ops, slot, slot + "_hide", slot, "self")
                    pin(ops, slot + "_hide", "bNewVisibility", "false")
                    previous = slot + "_hide"
        command("blueprint_graph_batch", path=P, graph_name="SetSuitedBody", ops=ops, compile=True, save=True)
        command("object_set_property", path=P + ".BP_FoAPlayer_C:Suit_GEN_VARIABLE", properties={
            "SkeletalMeshAsset": CLOTH + "/SK_FoA_Suit.SK_FoA_Suit", "bVisible": False})
        graph = command("blueprint_inspect_graph", path=P, graph_name="Equip")
        if not any(n["title"] == "SetSuitedBody" for n in graph["nodes"]):
            entry = next(n["node_id"] for n in graph["nodes"] if n["title"] == "Equip")
            next_edge = next(e for e in graph["edges"] if e["from_node"] == entry and e["from_pin"] == "then")
            ops = [{"op": "disconnect", "node_id": entry, "pin_name": "then"}]
            add(ops, "is_suit", "call_function", -500, 200, function_name="/Script/Engine.KismetMathLibrary:EqualEqual_NameName")
            add(ops, "branch", "branch", -250, 0)
            add(ops, "suited", "call_function", 0, -300, function_name=P + ".BP_FoAPlayer_C:SetSuitedBody")
            connect(ops, entry, "is_suit", "GarmentId", "A")
            pin(ops, "is_suit", "B", "Suit")
            pin(ops, "suited", "bEnable", "true")
            connect(ops, "is_suit", "branch", "ReturnValue", "Condition")
            connect(ops, entry, "branch")
            connect(ops, "branch", "suited")
            connect(ops, "suited", next_edge["to_node"], bp=next_edge["to_pin"])
            connect(ops, "branch", next_edge["to_node"], ap="else", bp=next_edge["to_pin"])
            ops.append({"op": "fit_comments"})
            command("blueprint_graph_batch", path=P, graph_name="Equip", ops=ops, compile=True, save=True)
        graph = command("blueprint_inspect_graph", path=P, graph_name="UnequipAll")
        if not any(n["title"] == "SetSuitedBody" for n in graph["nodes"]):
            tail = next(n["node_id"] for n in graph["nodes"] if n["title"] == "SetVisibility" and not any(
                e["from_node"] == n["node_id"] and e["from_pin"] == "then" for e in graph["edges"]))
            ops = []
            add(ops, "restore", "call_function", 1900, 0, function_name=P + ".BP_FoAPlayer_C:SetSuitedBody")
            pin(ops, "restore", "bEnable", "false")
            connect(ops, tail, "restore")
            ops.append({"op": "fit_comments"})
            command("blueprint_graph_batch", path=P, graph_name="UnequipAll", ops=ops, compile=True, save=True)
        print("Suit equip switches only its covered body; UnequipAll restores the original MetaHuman and starter outfit")
    finally:
        hc.release(OWNER, lease)


if __name__ == "__main__":
    main()
