"""Replay a graph_layout.py plan's Hayba calls (material graphs: Python plans, Hayba applies).
  python Tools/Unreal/ui/replay_layout.py Saved/GraphLayout/M_X.json"""
import json
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc  # noqa: E402

plan = json.load(open(sys.argv[1], encoding='utf-8'))
bad = 0
for call in plan.get('calls', []):
    name, args = (call['name'], call['args']) if isinstance(call, dict) else call
    r = hc.call(name, args)
    if not r.get('ok'):
        bad += 1
        print('FAIL', name, (r.get('error') or '')[:160])
print(sys.argv[1], len(plan.get('calls', [])), 'calls,', bad, 'failed')
