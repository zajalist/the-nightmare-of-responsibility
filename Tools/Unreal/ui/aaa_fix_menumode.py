"""AAA pass: restore the dream menu preset (it carries the menu grade) but stop its MenuGlitch datamosh timer.
BP_DreamDirector (world lane) arms MenuGlitch in SetMenuMode; the front end clears that timer on the director right after,
with K2_ClearTimer(Object = director, FunctionName = MenuGlitch). Datamosh stays reserved for time breaks.
  python Tools/Unreal/ui/aaa_fix_menumode.py"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

FE = '/Game/FoA/UI/Framework/BP_FoAFrontEnd'
G = 'SetDreamMenuMode'
d = hc.call('blueprint_inspect_graph', {'path': FE, 'graph_name': G})['data']
nodes, edges = d['nodes'], d['edges']
entry = next(n['node_id'] for n in nodes if n['title'] == G)
menu = next(n for n in nodes if n['title'].replace(' ', '').startswith('SetMenuMode'))
cast = next(n['node_id'] for n in nodes if n['title'].startswith('Cast To'))
cast_pin = next(p['name'] for p in next(n for n in nodes if n['node_id'] == cast)['pins']
                if p['direction'] == 'output' and p['type'] == 'object')
ops = []
if not any(e['to_node'] == menu['node_id'] and e['to_pin'] == 'Enabled' for e in edges):
    ops.append({'op': 'connect', 'from_node': entry, 'from_pin': 'bMenu', 'to_node': menu['node_id'], 'to_pin': 'Enabled'})
if not any(n['title'].startswith('Clear Timer') for n in nodes):
    nxt = [e for e in edges if e['from_node'] == menu['node_id'] and e['from_pin'] == 'then']
    ops += [{'op': 'add_node', 'ref': 'clr', 'node_type': 'call_function',
             'function_name': '/Script/Engine.KismetSystemLibrary:K2_ClearTimer', 'x': 1300, 'y': 0},
            {'op': 'set_pin', 'node_id': 'clr', 'pin_name': 'FunctionName', 'value': 'MenuGlitch'},
            {'op': 'connect', 'from_node': cast, 'from_pin': cast_pin, 'to_node': 'clr', 'to_pin': 'Object'},
            {'op': 'connect', 'from_node': menu['node_id'], 'from_pin': 'then', 'to_node': 'clr', 'to_pin': 'execute'}]
    for e in nxt:
        ops += [{'op': 'disconnect', 'node_id': menu['node_id'], 'pin_name': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']},
                {'op': 'connect', 'from_node': 'clr', 'from_pin': 'then', 'to_node': e['to_node'], 'to_pin': e['to_pin']}]
    ops += [{'op': 'comment', 'title': 'No menu datamosh', 'node_ids': ['clr'], 'color': [0.30, 0.22, 0.10]},
            {'op': 'fit_comments'}]
r = hc.call('blueprint_graph_batch', {'path': FE, 'graph_name': G, 'ops': ops, 'compile': True, 'save': True})
dd = r.get('data') or {}
print(r.get('ok'), dd.get('applied'), dd.get('total'), dd.get('error') or r.get('error'), json.dumps(dd.get('compile'))[:200])
