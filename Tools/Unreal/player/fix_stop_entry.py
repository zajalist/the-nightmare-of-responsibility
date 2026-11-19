"""Initialize the stop evaluator at its predicted stopping distance, including0.

At low frame rates braking can finish before Stop first updates. Starting it at
time0 then advancing replays a running stop while the capsule stands still.
"""
from held_tool_graphs import Batch,inspect,find,call
P='/Game/FoA/Characters/Player/ABP_FoAPlayer'
name='SetupStopDM'
# Native animation-node function creation owns the exact engine signature.
response=call('anim_blueprint_add_node_function',dict(path=P,name=name))
if not response.get('ok'):
    assert 'already' in str(response).lower() or 'exists' in str(response).lower(),response
nodes,_=inspect(P,name)
if not any('Distance Match' in n['title'] for n in nodes):
    b=Batch(P,name);entry=find(nodes,name)
    b.fn('eval','/Script/AnimGraphRuntime.SequenceEvaluatorLibrary:ConvertToSequenceEvaluatorPure',250,200)
    b.link(entry,'Node','eval','Node')
    b.get('distance','StopDistance',250,400)
    b.fn('match','/Script/AnimationLocomotionLibraryRuntime.AnimDistanceMatchingLibrary:DistanceMatchToTarget',600,0,DistanceCurveName='Distance')
    b.link('eval','SequenceEvaluator','match','SequenceEvaluator');b.link('distance','StopDistance','match','DistanceToTarget')
    b.chain(entry,'match');b.run()
nodes,_=inspect(P,'Stop')
for node in nodes:
    if not node['title'].startswith('Sequence Evaluator'):continue
    result=call('anim_graph_node_bind_function',dict(path=P,graph_name='Stop',node=node['node_id'],slot='become_relevant',
        function=name,dynamic_properties=['ExplicitTime']))
    assert result.get('ok') and result['data']['verified'] and result['data']['dynamic_properties_verified'],result
print('Stop entry now distance-matches before settling, even after braking already ended')
