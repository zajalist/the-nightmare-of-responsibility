"""AAA pass: focus is unmistakable without Slate's focus rectangle (RenderFocusRule=Never). WBP_SandButton.PushState
also steps the focused word 12 px right (v4: focus = brightness + a step right + grains; it never slides).
Appended after PushState's last exec node, in place (Hayba).
  python Tools/Unreal/ui/aaa_focus_step.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

B = '/Game/FoA/UI/Widgets/Common/WBP_SandButton'
G = 'PushState'
KML = '/Script/Engine.KismetMathLibrary'
d = hc.call('blueprint_inspect_graph', {'path': B, 'graph_name': G})['data']
nodes, edges = d['nodes'], d['edges']
assert d['page']['nodes']['next_offset'] is None and d['page']['edges']['next_offset'] is None, 'paged: extend reader'
if any(n['title'].startswith('SetRenderTranslation') for n in nodes):
    sys.exit('already applied')
title = {n['node_id']: n['title'] for n in nodes}
# every path ends in the last Branch (plain-label focus mark, two SetVisibility arms): step in just before it
last = next(n for n in title if title[n] == 'Branch' and any(
    e['from_node'] == n and title[e['to_node']].startswith('SetVisibility') for e in edges))
into = [e for e in edges if e['to_node'] == last and e['to_pin'] == 'execute']
print('feeds into the last Branch:', [title[e['from_node']] for e in into])
ops = [{'op': 'disconnect', 'node_id': e['from_node'], 'pin_name': e['from_pin'], 'to_node': last, 'to_pin': 'execute'}
       for e in into]
ops += [{'op': 'connect', 'from_node': e['from_node'], 'from_pin': e['from_pin'], 'to_node': 'tr', 'to_pin': 'execute'}
        for e in into]
ops = [
    {'op': 'add_node', 'ref': 'hov', 'node_type': 'variable_get', 'variable_name': 'bHovered', 'x': 3400, 'y': 200},
    {'op': 'add_node', 'ref': 'sel', 'node_type': 'call_function', 'function_name': f'{KML}:SelectFloat', 'x': 3600, 'y': 200},
    {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'A', 'value': '12.0'},
    {'op': 'set_pin', 'node_id': 'sel', 'pin_name': 'B', 'value': '0.0'},
    {'op': 'connect', 'from_node': 'hov', 'from_pin': 'bHovered', 'to_node': 'sel', 'to_pin': 'bPickA'},
    {'op': 'add_node', 'ref': 'v2', 'node_type': 'call_function', 'function_name': f'{KML}:MakeVector2D', 'x': 3800, 'y': 200},
    {'op': 'connect', 'from_node': 'sel', 'from_pin': 'ReturnValue', 'to_node': 'v2', 'to_pin': 'X'},
    {'op': 'add_node', 'ref': 'ret', 'node_type': 'variable_get', 'variable_name': 'Ret_Sand', 'x': 3800, 'y': 120},
    {'op': 'add_node', 'ref': 'tr', 'node_type': 'call_function', 'function_name': '/Script/UMG.Widget:SetRenderTranslation', 'x': 4000, 'y': 0},
    {'op': 'connect', 'from_node': 'ret', 'from_pin': 'Ret_Sand', 'to_node': 'tr', 'to_pin': 'self'},
    {'op': 'connect', 'from_node': 'v2', 'from_pin': 'ReturnValue', 'to_node': 'tr', 'to_pin': 'Translation'},
    {'op': 'connect', 'from_node': 'tr', 'from_pin': 'then', 'to_node': last, 'to_pin': 'execute'},
    {'op': 'comment', 'title': 'Focus steps right', 'node_ids': ['hov', 'sel', 'v2', 'ret', 'tr'], 'color': [0.30, 0.22, 0.10]},
]
rewire = ([{'op': 'disconnect', 'node_id': e['from_node'], 'pin_name': e['from_pin'], 'to_node': last, 'to_pin': 'execute'}
           for e in into] +
          [{'op': 'connect', 'from_node': e['from_node'], 'from_pin': e['from_pin'], 'to_node': 'tr', 'to_pin': 'execute'}
           for e in into])
ops = ops[:-2] + rewire + ops[-2:]  # nodes first, then move the incoming exec links onto the step
r = hc.call('blueprint_graph_batch', {'path': B, 'graph_name': G, 'ops': ops, 'compile': True, 'save': True})
dd = r.get('data') or {}
print(r.get('ok'), dd.get('applied'), dd.get('total'), dd.get('error') or r.get('error'), json.dumps(dd.get('compile'))[:200])
