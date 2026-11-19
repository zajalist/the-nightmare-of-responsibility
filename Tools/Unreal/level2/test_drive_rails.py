"""Offline: rails data selftest, rail clearance from building footprints, and the rails graph plans (no editor)."""
import json
from math import dist
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import build_drive as b
import drive_data as D
import drive_rails as R

D.selftest()

# Every rail sample keeps the car body (half width 1 m) at least 3 m from any surveyed building wall.
source = Path(D.SOURCE)
if (source / 'buildings.json').exists():
    corr = json.loads((source / 'corridor.json').read_text())
    (ox, oy), (ax, ay), (lx, ly) = corr['origin_utm_m'], corr['along_utm'], corr['left_utm']
    walls = []
    for record in json.loads((source / 'buildings.json').read_text())['records']:
        geometry = json.loads(record['geometry'])
        rings = [geometry['coordinates'][0]] if geometry['type'] == 'Polygon' else [p[0] for p in geometry['coordinates']]
        for ring in rings:
            pts = [(((e - ox) * ax + (n - oy) * ay) * 100, -((e - ox) * lx + (n - oy) * ly) * 100) for e, n, *_ in ring]
            walls += list(zip(pts, pts[1:]))

    def to_wall(p):
        best = 1e9
        for (x1, y1), (x2, y2) in walls:
            if min(x1, x2) - 3000 > p[0] or max(x1, x2) + 3000 < p[0]:
                continue
            dx, dy = x2 - x1, y2 - y1
            t = max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
            best = min(best, dist(p, (x1 + t * dx, y1 + t * dy)))
        return best
    worst = []
    for key, rail in zip(D.ROUTE_KEYS, D.RAILS):
        samples = []
        for p, q in zip(rail, rail[1:]):
            n = max(1, int(dist(p[:2], q[:2]) // 200))
            samples += [(p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n) for k in range(n)]
        clearance = min(to_wall(s) for s in samples)
        worst.append((round(clearance), key))
        assert clearance > 400, (key, clearance)
    print('Rail clearance from buildings (cm, worst first):', sorted(worst)[:4])
    # Each hiring sign stands off every rail's steering corridor and clear of the walls.
    def to_rail(p):
        best = 1e9
        for rail in D.RAILS:
            for (x1, y1, _), (x2, y2, _) in zip(rail, rail[1:]):
                dx, dy = x2 - x1, y2 - y1
                t = max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / (dx * dx + dy * dy or 1)))
                best = min(best, dist(p, (x1 + t * dx, y1 + t * dy)))
        return best
    spots = [(round(to_rail((x, y))), round(to_wall((x, y)))) for x, y, *_ in D.SIGN_SPOTS]
    assert all(road > D.CORRIDOR + 230 and wall > 200 for road, wall in spots), spots
    print('Sign spots (cm to the nearest rail, to the nearest wall):', spots)

# Graph plans: every connection joins created nodes, every data input has one source.
plans = []
b.inspect = lambda path, name: ([dict(node_id='entry', title=name)], [])
b.G.run = lambda self: plans.append(self)
for name, fn in R.GRAPHS.items():
    fn()
for plan in plans:
    refs, inputs = {'entry'}, set()
    for op in plan.ops:
        if op['op'] == 'add_node':
            assert op['ref'] not in refs; refs.add(op['ref'])
        if op['op'] == 'connect':
            assert op['from_node'] in refs and op['to_node'] in refs, (plan.graph, op)
            pin = (op['to_node'], op['to_pin'])
            if op['to_pin'] != 'execute':
                assert pin not in inputs, (plan.graph, pin)
            inputs.add(pin)
        if op['op'] == 'set_pin':
            assert op['node_id'] in refs and op['value'] != '', (plan.graph, op)
by = {p.path.rsplit('/', 1)[1] + '.' + p.graph: p for p in plans}
calls = lambda key: [o.get('function_name', '') for o in by[key].ops]
assert not any(f.endswith(('IsInputKeyDown', 'GetInputAnalogKeyState', 'AddActorWorldOffset')) for f in calls('BP_L2Car.Move')), \
    'Rails: no steering input and no swept free movement'
assert any(f.endswith('GetLocationAtDistanceAlongSpline') for f in calls('BP_L2Car.Move'))
assert any(f.endswith(':Continue') for f in calls('BP_L2Car.AutoPark')), 'Arrival parks by itself'
assert any(f.endswith(':Feedback') for f in calls('BP_L2Car.ResolveHit'))
assert any(f.endswith(':Restart') for f in calls('BP_L2Car.ResolveHit')), 'Composure 0 still requests the road restart'
assert not any('Employability' in str(o.get('variable_name', '')) and o['node_type'] == 'variable_set'
               for p in plans if p.path == b.CAR for o in p.ops if o['op'] == 'add_node'), 'Driving never sets EMPLOYABILITY'
assert any(f.endswith('SetGlobalTimeDilation') for f in calls('BP_L2Car.StartLeg'))
print('Rails graph plans passed:', len(plans), 'functions,', sum(len(p.ops) for p in plans), 'operations')
