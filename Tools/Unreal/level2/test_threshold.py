"""Offline graph-plan checks. Does not claim Blueprint compilation or runtime correctness."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import threshold_data as D
import build_drive
import build_threshold as B
from held_tool_graphs import Batch

def main():
    D.selftest()
    build_drive.inspect=lambda path,name:([{'node_id':'entry','title':name}],[])
    B.inspect=lambda path,name:([],[])
    plans={}
    def check(batch):
        refs={'entry'}
        for op in batch.ops:
            if op['op'] in ('add_node','add_event'):
                assert op['ref'] not in refs,(batch.graph,op)
                refs.add(op['ref'])
        for op in batch.ops:
            if op['op']=='connect':
                assert op['from_node'] in refs and op['to_node'] in refs,(batch.graph,op)
            elif op['op']=='set_pin':
                assert op['node_id'] in refs,(batch.graph,op)
        plans[batch.graph]=batch.ops
    old=Batch.run
    Batch.run=check
    try:
        for name,fn in B.STEPS.items():
            if name not in ('skeleton','widget','walk_widget','walk_components','walk_padding'):fn()
    finally:
        Batch.run=old
    assert set(B.FUNCS)<=set(plans)
    finish=plans['Finish']
    assert any(o.get('variable_name')=='Phase' for o in finish)
    # Protect story ownership and the player's save: plans may call but never edit shared assets.
    source=Path(B.__file__).read_text()
    assert 'FoA.sav' not in source and 'SaveGameToSlot' not in source
    assert 'blueprint_graph_batch' not in source # all batches use the house rollback/compile helper
    assert any(o.get('function_name','').endswith(':IsLevelVisible') for o in plans['Land'])
    assert any(o.get('function_name','').endswith(':RestoreRoom') for o in plans['Abort'])
    assert any(o.get('function_name','').endswith(':SetShouldBeLoaded') for o in plans['UnloadCity'])
    assert any(o.get('pin_name')=='FunctionName' and o.get('value')=='EndFade' for o in plans['EndingColour'])
    assert any(o.get('variable_name')=='MusicOverride' for o in plans['RestoreRoom'])
    assert any(o.get('variable_name')=='OldWalkSpeed' for o in plans['Begin'])
    assert not any(o.get('variable_name')=='OldWalkSpeed' for o in plans['StartPath'])
    nodes=sum(o['op'] in ('add_node','add_event') for ops in plans.values() for o in ops)
    print(f'{len(plans)} graph plans, {nodes} planned nodes: references/branches and recovery checks passed')

if __name__=='__main__':main()
