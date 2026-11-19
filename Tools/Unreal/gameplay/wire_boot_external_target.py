"""Native target connection omitted by Python's hidden-pin enumeration; run after body, before compile."""
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as hc
path = '/Game/FoA/Gameplay/BP_Interactable'
owner = 'boot-pacing'
lease = hc.lease_acquire(owner, ['asset:' + path], ttl_s=60, wait_s=10)
try:
    r = hc.call('blueprint_inspect_graph', dict(path=path, graph_name='IsDressingBlocked'), owner=owner, lease=lease)
    assert r.get('ok'), r
    nodes = r['data']['nodes']
    peer = [n for n in nodes if n['title'] == 'Get BootProgressionSource']; assert len(peer) == 1
    state = [n for n in nodes if n['title'] == 'GetInteractionState']; assert len(state) == 1
    r = hc.call('blueprint_graph_batch', dict(path=path, graph_name='IsDressingBlocked', ops=[dict(op='connect',
        from_node=peer[0]['node_id'], from_pin='BootProgressionSource', to_node=state[0]['node_id'], to_pin='self')], compile=True, save=True), owner=owner, lease=lease)
    assert r.get('ok') and r['data'].get('ok'), r
    compiled = r['data'].get('compile', {}); assert compiled.get('error_count') == 0 and compiled.get('warning_count') == 0, r
    print('PASS native sibling-state target connected; compile0/0 saved')
finally:
    hc.release(owner, lease)
