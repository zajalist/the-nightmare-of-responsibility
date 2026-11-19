"""Exit Start after its first usable stance, not capsule acceleration (~0.06s).

Readback of the selected clips puts the first usable left stance at0.6473s
walk/0.6497s run. Use evaluator time so distance matching owns this decision.
Run once under a scoped Player lease; repeat calls are idempotent.
"""
from held_tool_graphs import Batch,inspect
P='/Game/FoA/Characters/Player/ABP_FoAPlayer'
SEQ='/Script/AnimGraphRuntime.SequenceEvaluatorLibrary:'
K='/Script/Engine.KismetMathLibrary:'
norm=lambda text:''.join(text.split()).lower()


def one(nodes,title):
    matches=[n['node_id'] for n in nodes if norm(n['title'])==norm(title)]
    assert len(matches)==1,(title,matches)
    return matches[0]


def splice(batch,edges,tail,added):
    old=[e for e in edges if e['from_node']==tail and e['from_pin']=='then']
    for e in old:
        batch.cut(tail,'then',e['to_node'],e['to_pin'])
        batch.link(added,'then',e['to_node'],e['to_pin'])
    batch.chain(tail,added)


for graph in ('SetupStartDM','UpdateStartDM'):
    nodes,edges=inspect(P,graph)
    if any(norm(n['title'])=='setstartdone' for n in nodes):continue
    b=Batch(P,graph)
    b.set('phaseDone','StartDone',1400,0)
    if graph=='SetupStartDM':
        b.pin('phaseDone','StartDone','false')
        tail=one(nodes,'Set Explicit Time')
    else:
        evaluator=one(nodes,'Convert to Sequence Evaluator')
        b.fn('phaseTime',SEQ+'GetAccumulatedTime',900,400)
        b.link(evaluator,'SequenceEvaluator','phaseTime','SequenceEvaluator')
        b.fn('firstStance',K+'GreaterEqual_DoubleDouble',1150,400,B=.65)
        b.link('phaseTime','ReturnValue','firstStance','A');b.link('firstStance','ReturnValue','phaseDone','StartDone')
        tail=one(nodes,'Advance Time by Distance Matching')
    splice(b,edges,tail,'phaseDone');b.run()

nodes,_=inspect(P,'EventGraph')
old=[n['node_id'] for n in nodes if norm(n['title'])=='setstartdone']
if old:
    b=Batch(P,'EventGraph');b.ops.append(dict(op='remove',node_ids=old));b.run()
