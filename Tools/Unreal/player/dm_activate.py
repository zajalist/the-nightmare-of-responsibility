"""Bind restart6 node functions and route locomotion through the prepared Start/Stop states.
Run under a player lease, then dm_states.py FOA_STEP=rules with the printed rule map.
"""
import json
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
from hayba_call import call

P = '/Game/FoA/Characters/Player/ABP_FoAPlayer'
def run(cmd, **params):
    r = call(cmd, dict(path=P, **params))
    assert r.get('ok'), r
    return r['data']

for state in ('Start', 'Stop'):
    for n in run('blueprint_inspect_graph', graph_name=state)['nodes']:
        if not n['title'].startswith('Sequence Evaluator'):
            continue
        for slot, fn in [('become_relevant', 'Setup'+state+'DM'), ('update', 'Update' + state + 'DM')]:
            d = run('anim_graph_node_bind_function', graph_name=state, node=n['node_id'], slot=slot, function=fn,
                    dynamic_properties=['ExplicitTime'])
            assert d['verified'] and d.get('dynamic_properties_verified'), d

d = run('blueprint_inspect_graph', graph_name='Locomotion')
nodes = {n['title']: n['node_id'] for n in d['nodes']}
# A state-machine transition is destroyed automatically when either end is disconnected.
obsolete = [nodes[t] for t in ('Idle to Walk / Run', 'Turn to Walk / Run', 'Walk / Run to Idle') if t in nodes]
if obsolete:
    run('blueprint_remove_nodes', graph_name='Locomotion', node_ids=obsolete)

rules = {}
for src, dst, rule in [('Idle', 'Start', 'ShouldMove'), ('Turn', 'Start', 'ShouldMove'),
                       ('Walk / Run', 'Stop', '!ShouldMove'),
                       ('Start', 'Walk / Run', 'StartDone'), ('Start', 'Stop', '!ShouldMove'),
                       ('Stop', 'Start', 'ShouldMove'), ('Stop', 'Idle', 'auto'),
                       ('Start', 'Battle', 'IsBattle'), ('Stop', 'Battle', 'IsBattle')]:
    title = src + ' to ' + dst
    if title not in nodes:
        result = run('anim_blueprint_add_transition', state_machine_name='Locomotion', from_state=src, to_state=dst)
        rules[result['transition_id']] = rule
print('FOA_RULES=' + ','.join(k + ':' + v for k, v in rules.items()))
open('P:/FoA/Saved/AnimShots/dm_rules.json', 'w').write(json.dumps(rules))
