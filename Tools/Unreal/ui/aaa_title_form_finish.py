"""Finish FormStep's wiring after aaa_title_form.py form stopped at op 25 (a Set node outputs Output_Get)."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

T = '/Game/FoA/UI/Widgets/Menus/WBP_Title'
d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': 'FormStep'})['data']
ids = {}
for n in d['nodes']:
    ids.setdefault(n['title'].replace('\n', ' '), []).append(n['node_id'])
print({k: len(v) for k, v in ids.items()})
one = lambda prefix: next(v[0] for k, v in ids.items() if k.startswith(prefix))
entry, sset, ease = one('FormStep'), one('Set FormT'), one('Ease')
gem, ret, ssp = one('GetEffectMaterial'), one('Get Ret_Title'), one('SetScalarParameterValue')
ge, br, stop = one('float >= float'), one('Branch'), one('Clear Timer')
get_, add, clamp = one('Get FormT'), one('float + float'), one('Clamp')
ops = [
    {'op': 'connect', 'from_node': sset, 'from_pin': 'Output_Get', 'to_node': ease, 'to_pin': 'Alpha'},
    {'op': 'connect', 'from_node': ret, 'from_pin': 'Ret_Title', 'to_node': gem, 'to_pin': 'self'},
    {'op': 'connect', 'from_node': gem, 'from_pin': 'ReturnValue', 'to_node': ssp, 'to_pin': 'self'},
    {'op': 'connect', 'from_node': ease, 'from_pin': 'ReturnValue', 'to_node': ssp, 'to_pin': 'Value'},
    {'op': 'connect', 'from_node': sset, 'from_pin': 'then', 'to_node': ssp, 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': sset, 'from_pin': 'Output_Get', 'to_node': ge, 'to_pin': 'A'},
    {'op': 'connect', 'from_node': ge, 'from_pin': 'ReturnValue', 'to_node': br, 'to_pin': 'Condition'},
    {'op': 'connect', 'from_node': ssp, 'from_pin': 'then', 'to_node': br, 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': br, 'from_pin': 'then', 'to_node': stop, 'to_pin': 'execute'},
    {'op': 'comment', 'title': 'Logotype forms from sand',
     'node_ids': [entry, get_, add, clamp, sset, ease, ret, gem, ssp, ge, br, stop], 'color': [0.30, 0.22, 0.10]},
    {'op': 'fit_comments'},
]
r = hc.call('blueprint_graph_batch', {'path': T, 'graph_name': 'FormStep', 'ops': ops, 'compile': True, 'save': True})
dd = r.get('data') or {}
print(r.get('ok'), dd.get('applied'), dd.get('total'), dd.get('error') or r.get('error'), dd.get('compile'))
