"""level1 lane: the T9 suit reads clean. BP_FoAPlayer.UpdateClothCorruption drives a roaming cloth stain (CorruptionPulse
on M_FoA_TeenCloth, a chest, arm or thigh site every 32 s, plus ClothSmoke above 0.6) on every garment, the Suit
included, so the payoff hero shot showed a grey crumpled stain on the suit's chest. While the Suit is visible the
pulse is now 0 for every garment and the smoke stays off; UnequipAll hides the Suit, so a new day brings it back.
One Hayba batch, compile and save; idempotent (skips when the Suit gate exists).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/suit_clean.py   (inside an asset lease on BP_FoAPlayer)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

BP = '/Game/FoA/Characters/Player/BP_FoAPlayer'
G = 'UpdateClothCorruption'
K = '/Script/Engine.KismetMathLibrary'


def call(name, **a):
    r = h.call(name, a, owner='level1', timeout=120)
    assert r.get('ok'), (name, str(r)[:400])
    return r['data']


def inspect_all(g):
    """Every node and edge of a graph: blueprint_inspect_graph returns 50 per page (offset / edge_offset)."""
    d = call('blueprint_inspect_graph', path=BP, graph_name=g)
    nodes, edges = {n['node_id']: n for n in d['nodes']}, list(d['edges'])
    off = d['page']['nodes'].get('next_offset')
    while off:
        p = call('blueprint_inspect_graph', path=BP, graph_name=g, offset=off)
        nodes.update({n['node_id']: n for n in p['nodes']})
        off = p['page']['nodes'].get('next_offset')
    off = d['page']['edges'].get('next_offset')
    while off:
        p = call('blueprint_inspect_graph', path=BP, graph_name=g, edge_offset=off)
        edges += p['edges']
        off = p['page']['edges'].get('next_offset')
    return nodes, edges


nodes, edges = inspect_all(G)
if any(n['title'] == 'IsVisible' for n in nodes.values()):
    print('SUIT_CLEAN kept')
    sys.exit(0)
sin = [i for i, n in nodes.items() if n['title'] == 'Sin (Radians)']
assert len(sin) == 1, sin
sin = sin[0]
users = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == sin and e['from_pin'] == 'ReturnValue']
assert len(users) == 6, users  # five SetScalarParameterValueOnMaterials (CorruptionPulse) and the smoke threshold
ops = [dict(op='disconnect', node_id=sin, pin_name='ReturnValue', to_node=n, to_pin=p) for n, p in users]
ops += [
    dict(op='add_node', ref='suit', node_type='variable_get', variable_name='Suit', x=-200, y=900),
    dict(op='add_node', ref='worn', node_type='call_function', class_path='/Script/Engine.SceneComponent', function_name='IsVisible', x=50, y=900),
    dict(op='connect', from_node='suit', from_pin='Suit', to_node='worn', to_pin='self'),
    dict(op='add_node', ref='pulse', node_type='call_function', class_path=K, function_name='SelectFloat', x=300, y=800),
    dict(op='set_pin', node_id='pulse', pin_name='A', value='0'),
    dict(op='connect', from_node='worn', from_pin='ReturnValue', to_node='pulse', to_pin='bPickA'),
    dict(op='connect', from_node=sin, from_pin='ReturnValue', to_node='pulse', to_pin='B'),
]
ops += [dict(op='connect', from_node='pulse', from_pin='ReturnValue', to_node=n, to_pin=p) for n, p in users]
ops += [dict(op='comment', title='No stain on the suit', node_ids=['suit', 'worn', 'pulse'], bubble=True)]
r = call('blueprint_graph_batch', path=BP, graph_name=G, ops=ops, compile=True, save=True)
c = r.get('compile') or {}
print('SUIT_CLEAN', {k: r.get(k) for k in ('applied', 'total', 'failed_index', 'error')}, 'errors', c.get('error_count'),
      'saved', c.get('saved'), c.get('save_error'))
assert r.get('failed_index') is None and c.get('error_count') == 0 and c.get('saved'), r
