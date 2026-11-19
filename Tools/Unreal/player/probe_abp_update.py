"""Read-only: ABP_FoAPlayer EventGraph update chain (what runs each frame) and the Character variable's type."""
import unreal
BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
a = unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(a, 'EventGraph')
rows = []
for n in ed.list_all_nodes():
    t = str(BEL.get_node_title(n)).replace('\n', ' ')
    if 'Sequence' == t or 'Update' in t.replace(' ', '') or 'Initialize' in t.replace(' ', ''):
        outs = [(str(PIN.get_pin_name(p)), [str(BEL.get_node_title(PIN.get_owning_node(q))).replace('\n', ' ')[:40] for q in PIN.list_connected_pins(p)])
                for p in BEL.list_output_pins(n)]
        rows.append(f'{t} @ {BEL.get_node_pos(n).x},{BEL.get_node_pos(n).y}: {outs}')
open('P:/FoA/Saved/AnimShots/abp_update.txt', 'w').write('\n'.join(rows))
print('rows', len(rows))
