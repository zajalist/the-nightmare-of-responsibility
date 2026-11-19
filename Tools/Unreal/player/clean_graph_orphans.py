"""Removes dead nodes and duplicate comment boxes (same title) from one Blueprint function graph.
Dead: a node with no exec pins whose outputs reach no live node (transitively), or any node with no links at all.
Leftovers of a rolled-back Hayba graph batch (auto-inserted conversions, half-wired pure chains) are exactly that.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/clean_graph_orphans.py FOA_BP=... FOA_GRAPH=... [FOA_DRY=1]"""
import os
import unreal
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT
bp = unreal.load_asset(os.environ['FOA_BP'])
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, os.environ['FOA_GRAPH'])
dry = os.environ.get('FOA_DRY') == '1'
nodes = [n for n in ed.list_all_nodes() if n.get_class().get_name() != 'EdGraphNode_Comment']
pins = {n: list(BEL.list_all_pins(n)) for n in nodes}
is_exec = lambda p: str(PIN.get_pin_type(p).get_editor_property('pin_category')) == 'exec' if hasattr(PIN, 'get_pin_type') else str(PIN.get_pin_name(p)) in ('execute', 'then')  # noqa: E731
live = {n for n in nodes if any(str(PIN.get_pin_name(p)) in ('execute', 'then') for p in pins[n])
        and sum(len(PIN.list_connected_pins(p)) for p in pins[n])}
live |= {n for n in nodes if n.get_class().get_name() in ('K2Node_FunctionEntry', 'K2Node_FunctionResult')}
grew = True
while grew:
    grew = False
    for n in nodes:
        if n in live:
            continue
        outs = [q for p in pins[n] if PIN.get_pin_direction(p) == OUT for q in PIN.list_connected_pins(p)]
        if any(PIN.get_owning_node(q) in live for q in outs):
            live.add(n); grew = True
dead = [n for n in nodes if n not in live]
seen, dupes = set(), []
for c in ed.list_comment_nodes():
    t = str(BEL.get_comment_text(c))
    (dupes if t in seen else []).append(c)
    seen.add(t)
print('DEAD', [str(BEL.get_node_title(n)) for n in dead], 'DUPLICATE_COMMENTS', [str(BEL.get_comment_text(c)) for c in dupes])
if not dry:
    if dead:
        ed.remove_nodes(dead)
    for c in dupes:
        ed.remove_comment_node(c)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print('removed', len(dead), len(dupes))
