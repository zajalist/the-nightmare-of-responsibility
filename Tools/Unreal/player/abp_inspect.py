"""Read-only: ABP_FoAPlayer's graphs (every node title, position, links) and the anim palette entries this lane needs
(plugin nodes: stride/orientation warping, distance matching, random player, modify bone). Writes Saved/AnimShots/abp.txt.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/abp_inspect.py FOA_AREAS=/Game/FoA/Characters/Player"""
import unreal

BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
a = unreal.load_asset("/Game/FoA/Characters/Player/ABP_FoAPlayer")
L = []
for g in BEL.list_graphs(a):
    try:
        ed = unreal.BlueprintGraphEditor.get_graph_editor(g)
    except Exception as e:
        L.append(f"## {g.get_name()} ({g.get_class().get_name()}) ? {e}")
        continue
    nodes = ed.list_all_nodes()
    L.append(f"## {g.get_name()} ({g.get_class().get_name()}) outer={g.get_outer().get_name()} nodes={len(nodes)}")
    for n in nodes:
        p = BEL.get_node_pos(n)
        outs = []
        for op in BEL.list_output_pins(n):
            for q in PIN.list_connected_pins(op):
                outs.append(f"{PIN.get_pin_name(op)}->{BEL.get_node_title(PIN.get_owning_node(q))}.{PIN.get_pin_name(q)}")
        L.append(f"  [{p.x},{p.y}] {BEL.get_node_title(n)} <{n.get_class().get_name()}> {' | '.join(outs)}")
    for c in ed.list_comment_nodes():
        L.append(f"  comment: {BEL.get_comment_text(c)}")
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(a, "AnimGraph")
keys = ("Stride", "Orientation", "Distance", "Random", "Modify", "Inertial", "Sequence Evaluator", "Sequence Player",
        "Blend Poses", "Layered", "Apply Additive", "Two Bone", "Leg IK", "Control Rig", "Blendspace", "Slot", "Mirror")
for e in ed.list_available_nodes([]):
    s = str(e)
    if s.startswith("Animation|") and any(k.lower() in s.lower() for k in keys):
        L.append(f"palette {s}")
with open("P:/FoA/Saved/AnimShots/abp.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")
print(len(L), "lines")
