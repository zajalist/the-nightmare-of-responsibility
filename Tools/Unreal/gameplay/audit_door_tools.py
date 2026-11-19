"""Read-only saved graph/input/timer audit. Run only after the coordinator releases PIE."""
import json
from pathlib import Path
import unreal
exec(open('P:/FoA/Tools/Unreal/ui/bp_graph.py', encoding='utf-8').read())
path = '/Game/FoA/Gameplay/BP_Door'
rows = []
for name in ('StepDoorTool', 'BeginDoorTool'):
    g = Graph(path, name)
    for n in g.ed.list_all_nodes():
        title = BEL.get_node_title(n).splitlines()[0]
        pins = {str(PIN.get_pin_name(p)): str(PIN.get_pin_value(p)) for p in BEL.list_all_pins(n)}
        if 'Key' in pins or 'FunctionName' in pins:
            rows.append(dict(graph=name, title=title, defaults=pins,
                exec_sources=[str(PIN.get_pin_name(p)) for p in PIN.list_connected_pins(Graph.pin(n, 'execute', 'in'))]
                    if 'execute' in pins else 'pure'))
keys = [r['defaults']['Key'] for r in rows if r['graph'] == 'StepDoorTool' and 'Key' in r['defaults']]
assert set(keys) == {'D', 'A', 'Q', 'Gamepad_FaceButton_Right', 'Gamepad_RightX'}, keys
timers = [r for r in rows if r['defaults'].get('FunctionName') == 'StepDoorTool']
assert len(timers) == 1 and timers[0]['exec_sources'], timers
assert timers[0]['defaults']['bLooping'].lower() == 'true'
out = Path('P:/FoA/Saved/Integration/door_tools_input_graph.json')
out.write_text(json.dumps(rows, indent=2)); print('PASS actual saved raw FKey defaults and looping Step timer exec', out)
