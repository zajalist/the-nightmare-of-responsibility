"""level1 lane: no interaction outline behind the item inspect. BPC_Interactor keeps its focused mesh's outline (custom
stencil 3) while BP_ItemInspect pauses the game, so the boot stayed outlined behind the T3 key. BP_ItemInspect.Open now
suspends the player's interactor first (BPC_Interactor.SetSuspended(true): Scan timer paused, focus, outline and prompt
cleared) and Finish resumes it last (SetSuspended(false): the scan picks the focus up again). One Hayba batch per
graph, compile and save; idempotent (skips a graph that already calls SetSuspended).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/inspect_focus_suspend.py  (inside an asset lease on BP_ItemInspect)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

BP = '/Game/FoA/UI/Game/BP_ItemInspect'
IA = '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'


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


graph = inspect_all


def one(nodes, title):
    hits = [i for i, n in nodes.items() if n['title'] == title]
    assert len(hits) == 1, (title, hits)
    return hits[0]


def suspend_ops(on, x, y):
    return [
        dict(op='add_node', ref='pawn', node_type='call_function', class_path='/Script/Engine.GameplayStatics', function_name='GetPlayerPawn', x=x, y=y + 250),
        dict(op='add_node', ref='find', node_type='call_function', class_path='/Script/Engine.Actor', function_name='GetComponentByClass', x=x + 250, y=y + 250),
        dict(op='set_pin', node_id='find', pin_name='ComponentClass', value=IA),
        dict(op='connect', from_node='pawn', from_pin='ReturnValue', to_node='find', to_pin='self'),
        dict(op='add_node', ref='cast', node_type='cast', class_path=IA, x=x + 500, y=y),
        dict(op='connect', from_node='find', from_pin='ReturnValue', to_node='cast', to_pin='Object'),
        dict(op='add_node', ref='set', node_type='call_function', class_path=IA, function_name='SetSuspended', x=x + 800, y=y),
        dict(op='set_pin', node_id='set', pin_name='bSuspended', value='true' if on else 'false'),
        dict(op='connect', from_node='cast', from_pin='AsBPC Interactor', to_node='set', to_pin='self'),
        dict(op='connect', from_node='cast', from_pin='then', to_node='set', to_pin='execute'),
    ]


def batch(g, ops):
    d = call('blueprint_graph_batch', path=BP, graph_name=g, ops=ops, compile=True, save=True)
    c = d.get('compile') or {}
    print(g, {k: d.get(k) for k in ('applied', 'total', 'failed_index', 'error')}, 'errors', c.get('error_count'),
          'saved', c.get('saved'), c.get('save_error'))
    assert d.get('failed_index') is None and c.get('error_count') == 0 and c.get('saved'), d


nodes, edges = graph('Open')
if not any(n['title'] == 'SetSuspended' for n in nodes.values()):
    entry = one(nodes, 'Open')
    first = [e['to_node'] for e in edges if e['from_node'] == entry and e['from_pin'] == 'then']
    assert len(first) == 1, first
    batch('Open', [dict(op='disconnect', node_id=entry, pin_name='then', to_node=first[0], to_pin='execute')]
          + suspend_ops(True, -1200, 400)
          + [dict(op='connect', from_node=entry, from_pin='then', to_node='cast', to_pin='execute'),
             dict(op='connect', from_node='set', from_pin='then', to_node=first[0], to_pin='execute'),
             dict(op='connect', from_node='cast', from_pin='CastFailed', to_node=first[0], to_pin='execute'),
             dict(op='comment', title='No focus outline behind', node_ids=['pawn', 'find', 'cast', 'set'], bubble=True)])

nodes, edges = graph('Finish')
if not any(n['title'] == 'SetSuspended' for n in nodes.values()):
    hud = one(nodes, 'Branch')
    opacity = one(nodes, 'SetRenderOpacity')
    assert not [e for e in edges if e['from_node'] == opacity and e['from_pin'] == 'then'], 'Finish grew past SetRenderOpacity'
    assert not [e for e in edges if e['from_node'] == hud and e['from_pin'] == 'else'], 'Finish Branch else is wired'
    batch('Finish', suspend_ops(False, 3600, 0)
          + [dict(op='connect', from_node=opacity, from_pin='then', to_node='cast', to_pin='execute'),
             dict(op='connect', from_node=hud, from_pin='else', to_node='cast', to_pin='execute'),
             dict(op='comment', title='Focus back', node_ids=['pawn', 'find', 'cast', 'set'], bubble=True)])
print('INSPECT_FOCUS done')
