"""Restore the two authored gameplay actors missing from the bedroom map."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
owner = hc.agent_id()
assert not hc.call('editor_get_state', {})['data']['pie_running']
lease = hc.lease_acquire(owner, ['world:/Game/FoA/Maps/L_Tutorial_Bedroom'], ttl_s=60, wait_s=30)
try:
    for name, path, pos, rot in (
        # Hayba rotations are pitch, yaw, roll; rolling this actor puts the stage below the floor.
        ('Encounter_T8', '/Game/FoA/Gameplay/Encounter/BP_Encounter', [-200,-55,0], [0,180,0]),
        ('Phone_Nightstand', '/Game/FoA/UI/Game/BP_Phone', [338,-52,80.22], [180,0,200]),
    ):
        found = hc.call('actor_list', {'class_filter': path.rsplit('/', 1)[1] + '_C'})['data']['actors']
        assert len(found) <= 1, found
        if not found:
            r = hc.call('actor_spawn', dict(class_path=path+'.'+path.rsplit('/',1)[1]+'_C', location=pos, rotation=rot, label=name))
            assert r.get('ok') and r.get('data',{}).get('ok', True), r
            print(name, r['data'])
        assert hc.call('actor_list', {'class_filter': path.rsplit('/', 1)[1] + '_C'})['data']['count'] == 1
    r = hc.call('level_save', {})
    assert r.get('ok'), r
    print('Saved room with encounter and phone controllers')
finally:
    hc.release(owner, lease)
