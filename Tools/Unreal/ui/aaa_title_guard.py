"""Fix the WBP_Title Accessed None (horror lane's 13:23 burst, 262 errors): a key during the 1.5 s form removes the title,
its retainer loses its Slate widget, GetEffectMaterial returns None, and FormStep's timer kept running. FormStep now
checks IsValid(GetEffectMaterial) and stops its own timer when the retainer is gone.
  python Tools/Unreal/ui/aaa_title_guard.py [bp graph var]   (default WBP_Title FormStep FormT)"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

T, G, VAR = (sys.argv[1:4] if len(sys.argv) > 3 else ('/Game/FoA/UI/Widgets/Menus/WBP_Title', 'FormStep', 'FormT'))
d = hc.call('blueprint_inspect_graph', {'path': T, 'graph_name': G})['data']
nodes, edges = d['nodes'], d['edges']
title = {n['node_id']: n['title'] for n in nodes}
if any(t.startswith('Is Valid') or t == 'IsValid' for t in title.values()):
    sys.exit('already guarded')
one = lambda p: next(k for k, v in title.items() if v.startswith(p))
sset, ssp, gem, stop = one('Set ' + VAR), one('SetScalarParameterValue'), one('GetEffectMaterial'), one('Clear Timer')
assert any(e['from_node'] == sset and e['from_pin'] == 'then' and e['to_node'] == ssp for e in edges)
ops = [
    {'op': 'disconnect', 'node_id': sset, 'pin_name': 'then', 'to_node': ssp, 'to_pin': 'execute'},
    {'op': 'add_node', 'ref': 'valid', 'node_type': 'call_function', 'function_name': '/Script/Engine.KismetSystemLibrary:IsValid', 'x': 1000, 'y': 120},
    {'op': 'add_node', 'ref': 'vb', 'node_type': 'branch', 'x': 1060, 'y': 0},
    {'op': 'connect', 'from_node': gem, 'from_pin': 'ReturnValue', 'to_node': 'valid', 'to_pin': 'Object'},
    {'op': 'connect', 'from_node': 'valid', 'from_pin': 'ReturnValue', 'to_node': 'vb', 'to_pin': 'Condition'},
    {'op': 'connect', 'from_node': sset, 'from_pin': 'then', 'to_node': 'vb', 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': 'vb', 'from_pin': 'then', 'to_node': ssp, 'to_pin': 'execute'},
    {'op': 'connect', 'from_node': 'vb', 'from_pin': 'else', 'to_node': stop, 'to_pin': 'execute'},
    {'op': 'fit_comments'},
]
r = hc.call('blueprint_graph_batch', {'path': T, 'graph_name': G, 'ops': ops, 'compile': True, 'save': True})
dd = r.get('data') or {}
print(r.get('ok'), dd.get('applied'), dd.get('total'), dd.get('error') or r.get('error'), json.dumps(dd.get('compile'))[:200])
