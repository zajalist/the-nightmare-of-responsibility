"""Read-only Hayba regression checks for the player fixes (run outside the editor)."""
import sys

sys.path.insert(0, "P:/FoA/Tools/Unreal")
from hayba_call import call

P = "/Game/FoA/Characters/Player"


def read(command, **params):
    reply = call(command, params)
    assert reply.get("ok"), reply
    return reply.get("data", reply.get("result", reply))


def check_footstep():
    graph = read("blueprint_inspect_graph", path=P + "/Anims/AN_FoA_FootPlant", graph_name="Received_Notify")
    titles = {n["node_id"]: n["title"] for n in graph["nodes"]}
    edges = graph["edges"]
    valid = next((e["to_node"] for e in edges if e["from_pin"] == "HitActor"
                  and titles[e["to_node"]] == "IsValid"), None)
    assert valid, "HitActor must be validated before ActorHasTag is evaluated"
    gate = next(e["to_node"] for e in edges if e["from_node"] == valid and e["to_pin"] == "Condition")
    sand_gate = next(e["to_node"] for e in edges if titles[e["from_node"]] == "ActorHasTag")
    assert any(e["from_node"] == gate and e["from_pin"] == "then" and e["to_node"] == sand_gate for e in edges)
    assert any(e["from_node"] == gate and e["from_pin"] == "else"
               and titles[e["to_node"]] == "Return Node" for e in edges), "No surface must produce no step"
    print("PASS footstep: null hit exits before surface-tag evaluation")


def check_overlay():
    graph = read("blueprint_inspect_graph", path=P + "/BP_FoAPlayer", graph_name="SetSandOverlay")
    titles = {n["node_id"]: n["title"] for n in graph["nodes"]}
    targets = {titles[e["from_node"]] for e in graph["edges"] if e["to_pin"] == "self"
               and titles[e["to_node"]] == "SetOverlayMaterial"}
    expected = {"Get " + n for n in ("Body", "Face", "StartOutfit", "Shirt", "Trousers", "Socks", "Tie", "Suit")}
    assert targets == expected, (targets, expected)
    print("PASS overlay: every visible player layer uses the sand MID")


def check_battle():
    info = read("anim_blueprint_get_info", path=P + "/ABP_FoAPlayer")
    machine = next(s for s in info["state_machines"] if s["name"] == "Locomotion")
    assert "Battle" in {s["name"] for s in machine["states"]}
    pairs = {(t["from"], t["to"]) for t in machine["transitions"]}
    assert {("Idle", "Battle"), ("Walk / Run", "Battle"), ("Battle", "Idle")} <= pairs
    graph = read("blueprint_inspect_graph", path=P + "/BP_FoAPlayer", graph_name="SetBattle")
    titles = {n["node_id"]: n["title"] for n in graph["nodes"]}
    assert any(e["from_pin"] == "bEnable" and e["to_pin"] == "IsBattle"
               and titles[e["to_node"]] == "Set IsBattle" for e in graph["edges"])
    print("PASS battle: public SetBattle bool reaches the locomotion battle state")


def check_interaction_lock():
    graph = read("blueprint_inspect_graph", path=P + "/BP_FoAPlayer", graph_name="SetInteractionLocked")
    titles = [n["title"] for n in graph["nodes"]]
    assert titles.count("SetIgnoreMoveInput") == 1 and titles.count("Branch") == 2
    assert "Not Equal (Boolean)" in titles, titles
    for name in ("PlayInteraction", "EndInteraction"):
        body = read("blueprint_inspect_graph", path=P + "/BP_FoAPlayer", graph_name=name)
        names = [n["title"] for n in body["nodes"]]
        assert "SetInteractionLocked" in names and "ResetIgnoreMoveInput" not in names, (name, names)
    print("PASS interaction: both montage and timer use the balanced owner lock")


if __name__ == "__main__":
    check_footstep()
    if "--footstep" not in sys.argv:
        check_overlay()
        check_battle()
        check_interaction_lock()
