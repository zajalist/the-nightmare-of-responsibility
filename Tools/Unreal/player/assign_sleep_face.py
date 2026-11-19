"""Assign only the protagonist's face AnimBP; original face mesh, skeleton and DNA remain intact."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
owner = 'sleep-face-assign'
path = '/Game/FoA/Characters/Player/BP_FoAPlayer'
assert not hc.call('editor_get_state')['data']['pie_running']
lease = hc.lease_acquire(owner, ['asset:' + path], ttl_s=60, wait_s=10)
try:
    face = path + '.BP_FoAPlayer_C:Face_GEN_VARIABLE'
    before = hc.call('object_get_property', dict(path=face, names=['SkeletalMeshAsset']), owner=owner, lease=lease)['data']['properties']
    result = hc.call('object_set_property', dict(path=face, properties={'AnimClass': '/Game/FoA/Characters/Player/ABP_FoA_Face.ABP_FoA_Face_C'}), owner=owner, lease=lease)
    assert result.get('ok') and result['data'].get('ok'), result
    actual = hc.call('object_get_property', dict(path=face, names=['AnimClass', 'SkeletalMeshAsset']), owner=owner, lease=lease)['data']['properties']
    assert 'ABP_FoA_Face' in actual['AnimClass'] and actual['SkeletalMeshAsset'] == before['SkeletalMeshAsset'], actual
    saved = hc.call('asset_save', dict(asset_paths=[path]), owner=owner, lease=lease); assert saved.get('ok'), saved
    print('PASS protagonist sleep Face AnimBP assigned; exact face mesh preserved')
finally:
    hc.release(owner, lease)
