"""Hayba-native unit correction: world speed to the live source mesh's component speed."""
import json,sys,re
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
path='/Game/FoA/Characters/Player/ABP_FoAPlayer';owner='animation-stride-scale';token=None
def call(name,**params):
    r=h.call(name,params,owner=owner,lease=token);assert r.get('ok'),r
    d=r.get('data',{});assert d.get('ok',True),d
    return d
assert not call('editor_get_state')['pie_running']
prop=call('object_get_property',path='/Game/FoA/Characters/Player/BP_FoAPlayer.Default__BP_FoAPlayer_C:CharacterMesh0',names=['RelativeScale3D'])
xyz=[float(v) for v in re.findall(r'[XYZ]=([-+0-9.eE]+)',prop['properties']['RelativeScale3D'])]
assert len(xyz)==3 and min(xyz)>0 and max(xyz)-min(xyz)<1e-5,xyz
# Final Teen retarget lengthens planted-foot travel 10.3%; calibrated from live world-space feet.
scale=xyz[0]*1.103
token=h.lease_acquire(owner,['asset:'+path],ttl_s=60,wait_s=5)
try:
    g=call('blueprint_inspect_graph',path=path,graph_name='AnimGraph');nodes={n['node_id']:n for n in g['nodes']}
    sw=next(n['node_id'] for n in g['nodes'] if n['title']=='Stride Warping')
    edge=next(e for e in g['edges'] if e['to_node']==sw and e['to_pin']=='LocomotionSpeed')
    if nodes[edge['from_node']]['title']=='Get GroundSpeed':
        ops=[dict(op='add_node',ref='component_speed',node_type='call_function',function_name='/Script/Engine.KismetMathLibrary:Divide_DoubleDouble',x=2500,y=1450),
             dict(op='set_pin',node_id='component_speed',pin_name='B',value=str(scale)),
             dict(op='connect',from_node=edge['from_node'],from_pin='GroundSpeed',to_node='component_speed',to_pin='A'),
             dict(op='disconnect',node_id=sw,pin_name='LocomotionSpeed'),
             dict(op='connect',from_node='component_speed',from_pin='ReturnValue',to_node=sw,to_pin='LocomotionSpeed'),
             dict(op='comment',title='Component speed',node_ids=['component_speed'],color=[.18,.35,.38])]
        result=call('blueprint_graph_batch',path=path,graph_name='AnimGraph',ops=ops,compile=True,save=True)
        assert result.get('mutation_status') in ('complete','applied',None) or result.get('applied')==len(ops),result
    else:
        assert 'divide' in nodes[edge['from_node']]['title'].lower() or nodes[edge['from_node']]['title'] in ('/','float / float','double / double'),edge
        call('blueprint_graph_batch',path=path,graph_name='AnimGraph',ops=[dict(op='set_pin',node_id=edge['from_node'],pin_name='B',value=str(scale))],compile=True,save=True)
    compiled=call('blueprint_compile',path=path,save=True)
    assert compiled['error_count']==0 and compiled['warning_count']==0 and compiled['saved'],compiled
    g=call('blueprint_inspect_graph',path=path,graph_name='AnimGraph')
    edge=next(e for e in g['edges'] if e['to_node']==sw and e['to_pin']=='LocomotionSpeed')
    assert any(e['to_node']==edge['from_node'] and e['from_pin']=='GroundSpeed' for e in g['edges'])
    Path('P:/FoA/Saved/CharacterShots/stride_scale_fix.json').write_text(json.dumps(dict(scale=scale,compile=compiled,graph=g),indent=1))
    print('Saved source component-speed correction; world130cm/s -> component',130/scale)
finally:h.release(owner,token)
