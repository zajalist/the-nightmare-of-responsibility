"""Offline data and native patch-plan checks. Never connects to Unreal."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cv_data as d

assert len(d.OPPONENTS) == 3
assert sum(x['Resistance'] for x in d.OPPONENTS.values()) == 12
assert d.OPPONENTS['CVExperience']['Party'] == ['CVLogistics', 'CVReliability']
assert all(not x['GarmentId'] and not x['EquipSocket'] for x in d.OPPONENTS.values())
for row in d.OPPONENTS.values():
    assert row['Resistance'] == 4 and row['Rig'] is None
    assert set(row['ActMoves']) <= d.MOVES.keys()
    assert set(row['MoveWeights']) <= d.MOVES.keys()
    assert row['MoveWeights']['CVWait'] == (4,4,4,4)
    assert next(w for n,w in row['MoveWeights'].items() if n.startswith('CVOriginal')) == (1,1,1,2)
for name in ('CVOriginalExperience', 'CVOriginalLogistics', 'CVOriginalReliability'):
    assert d.MOVES[name]['ProgressDelta'] == -1
    assert d.MOVES[name]['bTelegraphed']
assert not d.MOVES['CVMisfile']['bSwapsTwin']
assert d.MOVES['CVSortFacts']['bStuns']
assert d.MOVES['CVRewriteLogistics']['bTimedInput'] is False
assert d.MOVES['CVRewriteExperience']['ResolveCost'] == 10
assert d.MOVES['CVRewriteReliability']['ResolveCost'] == 5
assert all(d.employability([p, 0, 0]) == 60 + 40*p//12 for p in range(5))
assert d.employability([4, 4, 4]) == 100
assert d.employability([4, 3, 4]) == 96
assert d.employability([-1, 5, 0]) == 73
assert d.employability([0, 0, 0]) == 60
print('CV data passed: three sections, truth loss, progress bounds and no-equipment rows')

import build_cv as c

def edge(a, b, pin='then'):
    return dict(from_node=a, from_pin=pin, to_node=b, to_pin='execute')

# The original L1 chain survives byte-for-byte behind the false branch.
nodes=[dict(node_id='entry',title='S_Victory'),dict(node_id='old',title='Dream Cycle')]
edges=[edge('entry','old')]
plan=c.guard_plan(c.ENCOUNTER,'EventGraph',nodes,edges,'S_Victory','FinishLevel2CV',{'Won':True})
assert [o for o in plan.ops if o['op']=='disconnect'] == [dict(op='disconnect',node_id='entry',pin_name='then',to_node='old',to_pin='execute')]
assert any(o.get('from_pin')=='else' and o.get('to_node')=='old' for o in plan.ops)
assert not any(o['op']=='remove' for o in plan.ops)
assert any(o.get('function_name','').endswith(':FinishLevel2CV') for o in plan.ops)
# Reapplying a patch is a no-op.
assert c.guard_plan(c.ENCOUNTER,'EventGraph',nodes+[dict(node_id='gate',title='Branch'),dict(node_id='done',title='Finish Level2 CV')],
                    [edge('entry','gate'),edge('gate','done'),edge('gate','old','else')],
                    'S_Victory','FinishLevel2CV',{'Won':True}) is None
print('CV patch plans passed: preserved L1 path, contextual callback, idempotent guard')

# Record the actual helper builders without entering Hayba. Check every data input has
# one producer and that public callbacks use the agreed Journey API.
plans=[]
def record(self): plans.append(self)
def inspect(path,name):
    entry=dict(node_id='entry',title=name)
    if name in ('CVMoveDetail','MoveDetail'):
        return [entry,dict(node_id='return',title='Return Node'),dict(node_id='value',title='Text')], [
            dict(from_node='value',from_pin='ReturnValue',to_node='return',to_pin='Detail')]
    if name=='RedrawAll':
        return [entry,dict(node_id='presentation',title='Refresh Battle Presentation')], [edge('entry','presentation')]
    return [entry],[]
c.inspect=inspect
c.b.inspect=inspect
c.Batch.run=record
c.b.G.run=record
for build in (c.start,c.context,c.sync,c.abort,c.finish,c.fold,c.assisted,c.presentation,c.detail):build()
assert len(plans)==11, len(plans)
for plan in plans:
    refs={'entry','return','value','presentation'}
    inputs=set()
    for op in plan.ops:
        if op['op']=='add_node':
            assert op['ref'] not in refs,(plan.graph,op)
            refs.add(op['ref'])
        elif op['op']=='connect':
            assert op['from_node'] in refs and op['to_node'] in refs,(plan.graph,op)
            if op['to_pin']!='execute':
                key=(op['to_node'],op['to_pin'])
                assert key not in inputs,(plan.graph,key)
                inputs.add(key)
functions=[o['function_name'] for p in plans for o in p.ops if o['op']=='add_node' and 'function_name' in o]
assert c.JC+':FinaleWon' in functions and c.JC+':FinaleLost' in functions
assert c.JC+':RefreshEmployability' in functions
assert not any(f.endswith((':FailDay',':Equip',':ReportEvent')) for f in functions)
assert any(f.endswith(':EndEncounter') for f in functions)
abort_plan=next(p for p in plans if p.graph=='AbortLevel2CV')
assert sum(o.get('function_name','').endswith(':K2_ClearTimer') for o in abort_plan.ops)==9
assert any(o.get('pin_name')=='bLevel2CV' and o.get('value')=='false' for o in abort_plan.ops)
member_calls=[]
c.b.call=lambda command,**args:member_calls.append((command,args)) or {}
c.widget_members()
assert [args['widget_name'] for command,args in member_calls if command=='ui_set_variable']==[
    'Txt_Intent0','Txt_Intent1','Txt_Intent2']
print('CV helper plans passed:',len(plans),'graphs,',sum(len(p.ops) for p in plans),'operations; no L1 outcome/equip calls')
