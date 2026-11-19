"""Include the separate head in Body's animated bounds, without changing collision mode or bone poses."""
import sys,json
from pathlib import Path
sys.path.insert(0,'P:/FoA/Tools/Unreal')
import hayba_call as h
owner='character_finish';root='/Game/FoA/Characters/Teen/Mesh/PA_Teen_Body'
path=root+'.PA_Teen_Body:SkeletalBodySetup_7'
envelope=json.loads(Path('P:/FoA/Saved/CharacterShots/mpfb/head_bounds_envelope.json').read_text())
assert not h.call('editor_get_state',owner=owner)['data']['pie_running']
token=h.lease_acquire(owner,['asset:/Game/FoA/Characters/Teen'],ttl_s=30,wait_s=1)
def call(command,params):
    result=h.call(command,params,owner=owner,lease=token);assert result.get('ok'),result
    data=result['data'];assert data.get('ok',True),data
    return data
try:
    properties=call('object_get_property',{'path':path,'names':['BoneName','AggGeom']})['properties']
    assert properties['BoneName']=='neck_01',properties
    assert 'SphereElems=,' in properties['AggGeom'],'Bounds sphere already present or unexpected geometry'
    x,y,z=envelope['center_cm'];radius=envelope['radius_cm']
    sphere=f'SphereElems=((Center=(X={x:.6f},Y={y:.6f},Z={z:.6f}),Radius={radius:.6f})),'
    geometry=properties['AggGeom'].replace('SphereElems=,',sphere,1)
    call('object_set_property',{'path':path,'properties':{'AggGeom':geometry}})
    after=call('object_get_property',{'path':path,'names':['AggGeom']})['properties']['AggGeom']
    assert f'Radius={radius:.6f}' in after,after
    call('asset_save',{'asset_paths':[root]})
    Path('P:/FoA/Saved/CharacterShots/mpfb/head_bounds_applied.json').write_text(json.dumps({'envelope':envelope,'geometry':after},indent=2))
    print('HEAD_BOUNDS_APPLIED',after)
finally:h.release(owner,token)
