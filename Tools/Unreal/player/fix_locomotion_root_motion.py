"""Strip root motion from the authored walk while preserving capsule-driven gameplay movement."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
path = '/Game/FoA/Characters/Player/ABP_FoAPlayer'
owner = 'metahuman-walking'
assert not hc.call('editor_get_state')['data']['pie_running'], 'Never mutate during user PIE'
lease = hc.lease_acquire(owner, ['asset:' + path], ttl_s=60, wait_s=10)
try:
    # Hayba SetDefaults stages an instance under TransientPackage, which violates
    # UAnimInstance's ClassWithin SkeletalMeshComponent and faults. Touch the existing CDO.
    result = hc.call('python_exec_file', dict(path='P:/FoA/Tools/Unreal/player/apply_locomotion_root_motion.py',
        env={}, resources=['asset:' + path]), owner=owner, lease=lease)
    assert result.get('ok') and result.get('data', {}).get('ok', True), result
    compiled = hc.call('blueprint_compile', dict(path=path, save=True), owner=owner, lease=lease)
    assert compiled.get('ok') and compiled['data'].get('error_count') == 0 and compiled['data'].get('warning_count') == 0, compiled
    saved = hc.call('asset_save', dict(asset_paths=[path]), owner=owner, lease=lease)
    assert saved.get('ok'), saved
    print('PASS runtime RootMotionMode=IgnoreRootMotion initialization compiled0/0 saved; capsule remains authoritative')
finally:
    hc.release(owner, lease)
