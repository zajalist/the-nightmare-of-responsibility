"""AAA pass, main menu (Hayba, in place): the four words form from sand down the column, 60 ms apart.
MenuFadeStep already ramps MenuFade 0 -> 1 over 0.6 s; each button gets SetReveal(ease_out3(clamp((MenuFade - i * 0.1) / 0.7))).
  python Tools/Unreal/ui/aaa_menu_form.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

P = '/Game/FoA/UI/Widgets/Menus/WBP_MainMenu'
KML = '/Script/Engine.KismetMathLibrary'
SB = '/Game/FoA/UI/Widgets/Common/WBP_SandButton.WBP_SandButton_C:SetReveal'
BTNS = ('Btn_WakeUp', 'Btn_Settings', 'Btn_Credits', 'Btn_Quit')

nodes, edges, off = [], [], 0
while off is not None:
    d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'EventGraph', 'offset': off})['data']
    nodes += d['nodes']
    off = d['page']['nodes']['next_offset']
off = 0
while off is not None:
    d = hc.call('blueprint_inspect_graph', {'path': P, 'graph_name': 'EventGraph', 'edge_offset': off, 'offset': 0})['data']
    edges += d['edges']
    nxt = d['page']['edges']['next_offset']
    off = nxt if nxt and nxt > off else None
title = {n['node_id']: n['title'].replace('\n', ' ') for n in nodes}
if any(t.startswith('SetReveal') for t in title.values()):
    sys.exit('already applied')
br = next(k for k, t in title.items() if t == 'Branch' and any(
    e['to_node'] == k and title.get(e['from_node']) == 'SetRenderOpacity' for e in edges))
last = next(e['from_node'] for e in edges if e['to_node'] == br and e['to_pin'] == 'execute')
setmf = next(k for k, t in title.items() if t == 'Set MenuFade')
ops = [{'op': 'disconnect', 'node_id': last, 'pin_name': 'then', 'to_node': br, 'to_pin': 'execute'}]
prev, refs = last, []
for i, b in enumerate(BTNS):
    x, y = 4900 + i * 420, -1300
    r = lambda n: f'{n}{i}'
    refs += [r('btn'), r('sub'), r('div'), r('cl'), r('ease'), r('sr')]
    ops += [
        {'op': 'add_node', 'ref': r('btn'), 'node_type': 'variable_get', 'variable_name': b, 'x': x, 'y': y + 260},
        {'op': 'add_node', 'ref': r('sub'), 'node_type': 'call_function', 'function_name': f'{KML}:Subtract_DoubleDouble', 'x': x, 'y': y + 340},
        {'op': 'set_pin', 'node_id': r('sub'), 'pin_name': 'B', 'value': f'{i * 0.1:.1f}'},
        {'op': 'add_node', 'ref': r('div'), 'node_type': 'call_function', 'function_name': f'{KML}:Divide_DoubleDouble', 'x': x, 'y': y + 420},
        {'op': 'set_pin', 'node_id': r('div'), 'pin_name': 'B', 'value': '0.7'},
        {'op': 'add_node', 'ref': r('cl'), 'node_type': 'call_function', 'function_name': f'{KML}:FClamp', 'x': x, 'y': y + 500},
        {'op': 'set_pin', 'node_id': r('cl'), 'pin_name': 'Min', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': r('cl'), 'pin_name': 'Max', 'value': '1.0'},
        {'op': 'add_node', 'ref': r('ease'), 'node_type': 'call_function', 'function_name': f'{KML}:Ease', 'x': x, 'y': y + 580},
        {'op': 'set_pin', 'node_id': r('ease'), 'pin_name': 'A', 'value': '0.0'},
        {'op': 'set_pin', 'node_id': r('ease'), 'pin_name': 'B', 'value': '1.0'},
        {'op': 'set_pin', 'node_id': r('ease'), 'pin_name': 'EasingFunc', 'value': 'EaseOut'},
        {'op': 'set_pin', 'node_id': r('ease'), 'pin_name': 'BlendExp', 'value': '3.0'},
        {'op': 'add_node', 'ref': r('sr'), 'node_type': 'call_function', 'function_name': SB, 'x': x, 'y': y},
        {'op': 'connect', 'from_node': setmf, 'from_pin': 'Output_Get', 'to_node': r('sub'), 'to_pin': 'A'},
        {'op': 'connect', 'from_node': r('sub'), 'from_pin': 'ReturnValue', 'to_node': r('div'), 'to_pin': 'A'},
        {'op': 'connect', 'from_node': r('div'), 'from_pin': 'ReturnValue', 'to_node': r('cl'), 'to_pin': 'Value'},
        {'op': 'connect', 'from_node': r('cl'), 'from_pin': 'ReturnValue', 'to_node': r('ease'), 'to_pin': 'Alpha'},
        {'op': 'connect', 'from_node': r('ease'), 'from_pin': 'ReturnValue', 'to_node': r('sr'), 'to_pin': 'Alpha'},
        {'op': 'connect', 'from_node': r('btn'), 'from_pin': b, 'to_node': r('sr'), 'to_pin': 'self'},
        {'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': r('sr'), 'to_pin': 'execute'},
    ]
    prev = r('sr')
ops += [{'op': 'connect', 'from_node': prev, 'from_pin': 'then', 'to_node': br, 'to_pin': 'execute'},
        {'op': 'comment', 'title': 'Words form from sand', 'node_ids': refs, 'color': [0.30, 0.22, 0.10]},
        {'op': 'fit_comments'}]
r = hc.call('blueprint_graph_batch', {'path': P, 'graph_name': 'EventGraph', 'ops': ops, 'compile': True, 'save': True})
dd = r.get('data') or {}
print(r.get('ok'), dd.get('applied'), dd.get('total'), dd.get('failed_index'), dd.get('error') or r.get('error'),
      json.dumps(dd.get('compile'))[:300])
