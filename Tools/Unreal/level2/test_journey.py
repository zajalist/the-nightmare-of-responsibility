"""Offline L2 run contract, graph references and idempotent progression checks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import journey_data as d
import build_journey as j
import build_drive as b

assert len(d.STOPS) == 3 and len({s['flag'] for s in d.STOPS}) == 3
assert [d.employability(i, 0) for i in range(4)] == [0, 20, 40, 60]
assert [d.employability(3, i) for i in (0, 3, 6, 9, 12)] == [60, 70, 80, 90, 100]
assert d.employability(3, -8) == 60 and d.employability(3, 99) == 100
plans = []
original_inspect,original_run=b.inspect,b.G.run
b.inspect = lambda path, name: ([dict(node_id='entry', title=name)], [])
b.G.run = lambda self: plans.append(self)
for name, fn in j.GRAPHS.items():
    fn()
b.inspect,b.G.run=original_inspect,original_run
for plan in plans:
    refs={'entry'}; inputs=set()
    for op in plan.ops:
        if op['op']=='add_node':
            assert op['ref'] not in refs
            refs.add(op['ref'])
        if op['op']=='connect':
            assert op['from_node'] in refs and op['to_node'] in refs, (plan.graph, op)
            pin=(op['to_node'],op['to_pin'])
            if op['to_pin']!='execute': assert pin not in inputs, (plan.graph,pin)
            inputs.add(pin)
by_name={p.graph:p for p in plans}
def funcs(name):
    return [o.get('function_name','') for o in by_name[name].ops if o['op']=='add_node']
assert any(f.endswith(':RestartFromRoad') for f in funcs('RestartRun'))
assert not any(f.endswith(':FailDay') for p in plans for f in [o.get('function_name','') for o in p.ops])
assert any(f.endswith(':BeginEnding') for f in funcs('Submit'))
assert any(f.endswith(':Deactivate') for f in funcs('Abort'))
assert any(f.endswith(':DisableConfirm') for f in funcs('Abort'))
assert any(f.endswith(':DisableInput') for f in funcs('DisableConfirm'))
assert any(f.endswith(':Learn') for f in funcs('ConfirmEdit'))
assert any(f.endswith(':SetProofProgressContext') for f in funcs('DebugNextStep'))
assert any(o.get('value')=='FoA_QA_DebugSkip' for o in by_name['DebugNextStep'].ops)
assert any(f.endswith(':InterviewWon') for f in funcs('DebugNextStep'))
# ConfirmEdit must check each stop flag before setting it, then advance the phase to exclude repeat input.
get_flags={o.get('variable_name') for o in by_name['ConfirmEdit'].ops if o.get('node_type')=='variable_get'}
assert all('Edited'+str(i) in get_flags for i in range(3))
assert len(plans)==len(j.GRAPHS)
print('Journey checks passed:',len(plans),'graphs; once-only edits, 0/20/40/60/100, local retry, road/ending ownership')
