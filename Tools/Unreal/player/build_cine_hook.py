"""SetCinematic(bEnable) also suspends gameplay's BPC_Interactor (no focus scan, no stencil-3 highlight, empty prompt) for
the length of a cinematic, and resumes it after. Appended to the end of SetCinematic's exec chain; re-runnable.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/build_cine_hook.py FOA_AREAS=/Game/FoA/Characters/Player
then compile with Hayba blueprint_compile."""
import importlib
import sys

import unreal

sys.path.insert(0, "P:/FoA/Tools/Unreal/player")
import graph_style  # noqa: E402

importlib.reload(graph_style)
at, box, link = graph_style.at, graph_style.box, graph_style.link
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
bp = unreal.load_asset("/Game/FoA/Characters/Player/BP_FoAPlayer")
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "SetCinematic")
for n in list(ed.list_all_nodes()):  # re-runnable: drop this script's two nodes and its box
    if BEL.get_node_title(n).replace(" ", "") in ("SetSuspended", "GetBPC_Interactor", "BPC_Interactor"):
        ed.remove_nodes([n])
for c in list(ed.list_comment_nodes()):
    if BEL.get_comment_text(c) == "Pause interaction":
        ed.remove_comment_node(c)
entry = PIN.get_owning_node(ed.find_graph_entry_pin())
tail = entry
while True:  # follow the exec chain to its end (the Branch's two arms rejoin before PushAnimState)
    then = BEL.find_then_pin(tail)
    nxt = [PIN.get_owning_node(q) for q in PIN.list_connected_pins(then)] if PIN.is_valid(then) else []
    if not nxt:
        break
    tail = nxt[0]
x, y = BEL.get_node_pos(tail).x + 320, BEL.get_node_pos(tail).y
hits = [str(a) for a in ed.list_available_nodes([]) if str(a).split("|")[-1].replace(" ", "") == "SetSuspended"]
assert hits, "no SetSuspended in the palette (gameplay's BPC_Interactor)"
call = at(ed.create_node_from_name(min(hits, key=len), unreal.Vector2D(x, y), []), x, y)
comp = at(ed.add_get_member_variable_node("BPC_Interactor", ""), x - 40, y + 180)
link(tail, None, call, None)
link(comp, "BPC_Interactor", call, "self")
link(entry, "bEnable", call, "bSuspended")
box(ed, "Pause interaction", "", [call, comp], "state")
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
print("SetCinematic -> BPC_Interactor.SetSuspended(bEnable) after", BEL.get_node_title(tail))
