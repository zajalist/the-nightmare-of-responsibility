"""Offline lifecycle graph checks; no editor calls or saved-game writes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import build_drive as b

plans = []
b.inspect = lambda path, name: ([dict(node_id='entry', title=name)], [])
b.G.run = lambda self: plans.append(self)

def calls(plan):
    return [op.get('function_name', '') for op in plan.ops if op['op'] == 'add_node']

assert 'Activate' in b.SIGNATURES[b.CAR], 'Streamed car needs explicit activation'
assert 'Deactivate' in b.SIGNATURES[b.CAR], 'Stops need complete control release'
for name in ('Begin', 'Activate', 'Deactivate', 'DriveStep', 'AutoPark', 'Continue'):
    b.STEPS['BP_L2Car.' + name]()
by_name = {p.graph:p for p in plans}
assert not any('SetViewTarget' in n or 'AddMappingContext' in n or 'CreateWidget' in n
               for n in calls(by_name['Begin']))
assert any(n.endswith(':Possess') for n in calls(by_name['Activate']))
assert any(n.endswith(':RemoveMappingContext') for n in calls(by_name['Deactivate']))
assert any(n.endswith(':RemoveFromParent') for n in calls(by_name['Deactivate']))
# Rails (2026-11-17): the car parks itself at the end of its rail; Continue hides the strike.
assert any(n.endswith(':Continue') for n in calls(by_name['AutoPark']))
assert any(n.endswith(':Hide') for n in calls(by_name['Continue']))
assert not any(n.endswith(':Percent_IntInt') for n in calls(by_name['Continue']))
print('Drive lifecycle checks passed: inert streamed car, explicit ownership, stopped hazards, terminal last leg')
