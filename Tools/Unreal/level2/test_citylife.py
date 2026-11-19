"""Offline: city life data selftest and BP_L2CityLife graph plans (no editor)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import citylife_data as C
import build_citylife as L

C.selftest()
lanes = Path(C.__file__).with_name('citylife_lanes.txt').read_text()
assert len(lanes) == len(C.D.RAILS) * C.BUCKETS and set(lanes) <= set('0LRB'), 'run citylife_data.py to rebuild the table'

plans = []
L.R.b.inspect = lambda path, name: ([dict(node_id='entry', title=name)], [])
L.R.b.G.run = lambda self: plans.append(self)
L.R.b.Batch.run = lambda self: plans.append(self)
L.graphs()
for plan in plans:
    refs, inputs = {'entry'}, set()
    for op in plan.ops:
        if op['op'] in ('add_node', 'add_event'):
            assert op['ref'] not in refs, (plan.graph, op); refs.add(op['ref'])
        if op['op'] == 'connect':
            assert op['from_node'] in refs and op['to_node'] in refs, (plan.graph, op)
            pin = (op['to_node'], op['to_pin'])
            if op['to_pin'] != 'execute':
                assert pin not in inputs, (plan.graph, pin)
            inputs.add(pin)
        if op['op'] == 'set_pin':
            assert op['node_id'] in refs and op['value'] != '', (plan.graph, op)
by = {p.graph: p for p in plans}
nodes = [o for p in plans for o in p.ops if o['op'] in ('add_node', 'add_event')]
assert not any(o.get('event_name') == 'ReceiveTick' for o in nodes), 'timer only, no Tick'
assert not any(o.get('node_type') == 'variable_set' and o.get('class_path') == L.cls(L.CAR) for o in nodes), 'never writes BP_L2Car'
tends = [o for o in by['Step'].ops if o['op'] == 'add_node' and o.get('function_name', '').endswith(':Tend')]
assert len(tends) == len(L.tend_args()) == 16, len(tends)
assert sum(1 for n, _ in L.COMPONENTS if n.startswith('WalkMesh')) <= 25, 'animated skeletal budget'
assert any(o.get('function_name', '').endswith('SetVelocityInLocalSpace') for o in by['Tend'].ops)
print('City life graph plans passed:', len(plans), 'graphs,', sum(len(p.ops) for p in plans), 'operations')
