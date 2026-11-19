"""Read-only full graph export where the native response's 50-item cap hides target nodes."""
import json
import sys
from pathlib import Path
import unreal
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import bp_layout

BEL, PIN = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphPinLibrary
path = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
bp = unreal.load_asset(path)
exported = bp_layout.parse_t3d(bp_layout.export_t3d(bp))


def guid(node):
    return exported[name][node.get_name()]['props']['NodeGuid'].replace('-', '').upper()


result = {}
for name in ('RefreshBattlePresentation', 'EventGraph', 'RefreshAct', 'RefreshRow', 'RefreshCommands'):
    editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, name)
    nodes, edges = [], []
    for node in editor.list_all_nodes():
        pins = []
        for direction, values in (('input', BEL.list_input_pins(node)), ('output', BEL.list_output_pins(node))):
            for pin in values:
                pname = str(PIN.get_pin_name(pin))
                pins.append(dict(name=pname, direction=direction, default=str(PIN.get_pin_value(pin))))
                if direction == 'output':
                    for target in PIN.list_connected_pins(pin):
                        edges.append(dict(from_node=guid(node), from_pin=pname,
                                          to_node=guid(PIN.get_owning_node(target)), to_pin=str(PIN.get_pin_name(target))))
        nodes.append(dict(node_id=guid(node), title=str(BEL.get_node_title(node)).splitlines()[0], pins=pins))
    result[name] = dict(nodes=nodes, edges=edges)
Path('P:/FoA/Saved/UIShots/battle_feedback_full.json').write_text(json.dumps(result, indent=2))
print('Read-only battle graphs exported', {name:len(data['nodes']) for name,data in result.items()})
