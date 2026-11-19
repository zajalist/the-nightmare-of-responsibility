"""Native-only patch: Dream A grains retain source colours with MPC_Dream.ColorReveal.
Requires BOTH Transition and M_SplatWorld_Lean asset leases. The city master is untouched.
This is a shared-material edit; inspect current node inputs before applying.
"""
from pathlib import Path
import os
import sys
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h

MAT='/Game/FoA/Level2/M_SplatWorld_Lean'

def call(cmd,**args):
    r=h.call(cmd,args)
    assert r.get('ok') and (r.get('data') or {}).get('ok',True),(cmd,r)
    return r.get('data') or {}

def main():
    resources=[r.lower() for _,rs in h.leases_of(os.environ.get('FOA_AGENT','dream-transition')) for r in rs]
    assert 'asset:'+MAT.lower() in resources,'Hold the shared dream master lease explicitly'
    assert not call('editor_get_state')['pie_running']
    info=call('material_get_info',path=MAT)
    candidates=[n for n in info['expressions'] if n['class']=='MaterialExpressionCustom'
                and {'Colour','Sand','RS','Clock'} <= {i['name'] for i in n['inputs']}]
    assert len(candidates)==1,'Shared splat graph changed; inspect before applying'
    grain=candidates[0]
    out=Path('P:/FoA/Saved/Codex/dream_transition');out.mkdir(parents=True,exist_ok=True)
    import json
    (out/'dream_material_before.json').write_text(json.dumps(info,indent=2))
    snapshot=out/'dream_material_snapshot.json'
    import time
    assert snapshot.exists() and time.time()-snapshot.stat().st_mtime<30,'Run the read-only probe in this lease first'
    original=json.loads(snapshot.read_text())[grain['id']]
    assert {i['InputName'] for i in original['Inputs']} in ({'Colour','Sand','RS','Clock'},{'Colour','Sand','RS','Clock','Reveal'})
    existing=[n for n in info['expressions'] if n['class']=='MaterialExpressionCollectionParameter' and n.get('x')==800 and n.get('y')==1800]
    node=existing[0]['id'] if existing else call('material_add_node',material_path=MAT,
        expression_class='MaterialExpressionCollectionParameter',node_pos=[800,1800],
        properties={'Collection':'/Game/FoA/PostProcess/MPC_Dream.MPC_Dream','ParameterName':'ColorReveal'})['node_id']
    properties={
        'Inputs':[{'InputName':n} for n in ('Colour','Sand','RS','Clock','Reveal')],
        'Code':'float glint = step(0.989, frac(RS.y*37.13)) * pow(max(0, sin(Clock*2+RS.y*91)),16);\n'
               'float3 grains = lerp(float3(0.009,0.009,0.009), Colour * 0.7, saturate(Reveal));\n'
               'return lerp(Colour, grains + glint*0.6, saturate(Sand*3));'}
    assert all(s['connected'] for s in grain['inputs']),grain['inputs']
    def apply(props):
        call('material_set_node',material_path=MAT,node_id=grain['id'],properties=props)
        for source in grain['inputs']:
            call('material_connect_nodes',material_path=MAT,from_node=source['from_node'],from_output_index=source['from_output'],
                 to_node=grain['id'],to_input=source['name'])
    def compile_checked():
        result=call('material_validate',material_path=MAT)
        assert not result.get('has_errors'),result
        result=call('material_compile',material_path=MAT)
        assert not result.get('has_errors'),result
    try:
        apply(properties)
        call('material_connect_nodes',material_path=MAT,from_node=node,from_output_index=0,to_node=grain['id'],to_input='Reveal')
        compile_checked()
    except BaseException:
        apply(original)
        compile_checked()
        raise
    call('asset_save',asset_paths=[MAT])
    print('Dream sand follows ColorReveal; default monochrome retained')

if __name__=='__main__':main()
