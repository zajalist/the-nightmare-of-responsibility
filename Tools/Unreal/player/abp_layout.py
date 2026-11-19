"""Clean AnimGraph layout for ABP_FoAPlayer (the user's graph rule: left to right, no overlaps, one titled box per group).
Walks the pose chain from Main States to Output Pose and places every node on a grid, getters under the node they feed.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/abp_layout.py FOA_AREAS=/Game/FoA/Characters/Player"""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
a = unreal.load_asset("/Game/FoA/Characters/Player/ABP_FoAPlayer")
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(a)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(a, "AnimGraph")
nodes = ed.list_all_nodes()
title = {n: BEL.get_node_title(n).split("\n")[0] for n in nodes}
find = lambda pre: next(n for n in nodes if title[n].startswith(pre))  # noqa: E731


def at(n, x, y):
    BEL.set_node_pos(n, unreal.IntPoint(int(x), int(y)))


def next_pose(n):
    for p in BEL.list_output_pins(n):
        for q in PIN.list_connected_pins(p):
            return PIN.get_owning_node(q)
    return None


chain = []


def feeders(n):
    """Non-pose nodes wired into n's inputs (variable getters, the boolean gate), nearest first."""
    out = []
    for p in BEL.list_input_pins(n):
        for q in PIN.list_connected_pins(p):
            m = PIN.get_owning_node(q)
            if m not in out and m not in chain:
                out.append(m)
    return out


for c in list(ed.list_comment_nodes()):
    ed.remove_comment_node(c)
# Row 1: the locomotion state machine, inertialized, cached (Main States' Locomotion state reads the cache).
loco, inert, save = find("Locomotion"), find("Inertialization"), find("Save cached pose")
for i, n in enumerate((loco, inert, save)):
    at(n, i * 320, 0)
# Row 2: the pose chain.
n = find("Main States")
while n is not None:
    chain.append(n)
    n = next_pose(n)
X0, Y = 0, 360
xs, x = {}, X0
for n in chain:
    xs[n] = x
    at(n, x, Y)
    x += 300 if not title[n].startswith(("Control Rig", "Look At", "Stride")) else 360
    if title[n].startswith("Component To") and next_pose(n) is not None and title[next_pose(n)].startswith("Control Rig"):
        x += 560  # room for the foot-IK gate under the rig, clear of the look-at box
groups = {}
for n in chain:
    under = feeders(n)
    for j, f in enumerate(under):
        at(f, xs[n] - 40, Y + 200 + j * 90)
        for k, g in enumerate(feeders(f)):  # the NOT / FootIKEnabled under the AND, IsFalling left of the NOT
            at(g, xs[n] - 300, Y + 200 + j * 90 + k * 80)
            for h in feeders(g):
                at(h, xs[n] - 540, Y + 200 + j * 90 + k * 80)
    groups[n] = under
by = {title[n]: n for n in chain}
names = [title[n] for n in chain]
i_sw = next(i for i, t in enumerate(names) if t.startswith("Stride"))
i_la = next(i for i, t in enumerate(names) if t.startswith("Look At"))
i_cr = next(i for i, t in enumerate(names) if t.startswith("Control Rig"))
i_sl = next(i for i, t in enumerate(names) if t.startswith("Slot"))


def members(i0, i1):
    out = []
    for n in chain[i0:i1 + 1]:
        out.append(n)
        for f in groups.get(n, []):
            out.append(f)
            for g in feeders(f):
                out += [g] + feeders(g)
    return out


graph_style.box(ed, "Inertial locomotion", "", [loco, inert, save], "anim")
graph_style.box(ed, "Stride warping", "", members(i_sw - 1, i_sw + 1), "anim")
graph_style.box(ed, "Montages", "", [chain[i_sl]], "state")
graph_style.box(ed, "Head look-at", "", members(i_la - 1, i_la + 1), "look")
graph_style.box(ed, "Foot IK", "", members(i_cr, i_cr), "anim")
unreal.EditorAssetLibrary.save_loaded_asset(a, False)
print("layout:", " -> ".join(names))
