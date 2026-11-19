"""Read-only checks that the live Start/Stop evaluators have usable distance curves and bindings."""
import json
from pathlib import Path
import unreal

bp=unreal.load_asset('/Game/FoA/Characters/Player/ABP_FoAPlayer')
rows=[]
for state in ('Start','Stop'):
    graph=next(g for g in unreal.BlueprintEditorLibrary.list_graphs(bp)
               if g.get_name()==state and g.get_class().get_name()=='AnimationStateGraph')
    nodes=unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes()
    evaluators=[n for n in nodes if n.get_class().get_name()=='AnimGraphNode_SequenceEvaluator']
    assert len(evaluators)==2,(state,len(evaluators))
    for n in evaluators:
        update=n.get_editor_property('update_function').export_text()
        setup=n.get_editor_property('become_relevant_function').export_text()
        assert 'Update'+state+'DM' in update and 'Setup'+state+'DM' in setup,(state,update,setup)
        seq=n.get_editor_property('node').get_editor_property('sequence')
        assert not n.get_editor_property('node').get_editor_property('should_loop'),(state,seq.get_name(),'looping one-shot')
        compression=seq.get_editor_property('curve_compression_settings')
        assert compression and compression.get_editor_property('codec').get_class().get_name()=='AnimCurveCompressionCodec_UniformIndexable',seq.get_name()
        times,values=unreal.AnimationLibrary.get_float_keys(seq,'Distance')
        assert len(values)>2 and max(values)-min(values)>10,seq.get_name()
        assert all(b>=a-.01 for a,b in zip(values,values[1:])),seq.get_name()
        assert abs(values[0] if state=='Start' else values[-1])<.01,seq.get_name()
        rows.append(dict(state=state,sequence=seq.get_path_name(),keys=len(values),
                         distance_range=[min(values),max(values)],update=update,setup=setup,compression=compression.get_path_name()))
Path('P:/FoA/Saved/AnimShots/dm_asset_verified.json').write_text(json.dumps(rows,indent=1))
print('Verified four distance-matched evaluators and monotonic travel curves')

