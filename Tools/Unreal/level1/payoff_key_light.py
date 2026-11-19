"""level1 lane: a key light on the T9 hero shot (the suit and the colour reveal read black on black without one).
Reuses BP_BeatDirector's WardrobeKeyLight (hidden point light, only lit for the T6 fall): PayoffShot moves it to the
pawn's front left, above his head, and shows it after the cut; PayoffShotCut hides it and puts it back at its template
spot (195, 70, 240) before the cut back to first person, so the next wardrobe fall finds it where it expects.
One Hayba batch per graph, compile and save. Not idempotent by itself: it refuses to run when PayoffShot already moves
the light (a SetWorldLocation on WardrobeKeyLight is present).
  $env:HAYBA_AGENT_ID='level1'; python Tools/Unreal/level1/payoff_key_light.py  (inside an asset lease on BP_BeatDirector)"""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import hayba_call as h  # noqa: E402

BP = '/Game/FoA/Gameplay/BP_BeatDirector'
K = '/Script/Engine.KismetMathLibrary'
SC = '/Script/Engine.SceneComponent'
KEY_IN_PAWN = '(X=90.0,Y=-70.0,Z=80.0)'  # front left, above the head (capsule centre space); the camera is front left low
HOME = '195,70,240'  # the template's relative location (build_director.py WardrobeKeyLight)


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


def node(nodes, title, **pin):
    hits = [i for i, n in nodes.items() if n['title'] == title and all(
        any(p['name'] == k and str(p.get('default_value')) == v for p in n['pins']) for k, v in pin.items())]
    assert len(hits) == 1, (title, pin, hits)
    return hits[0]


def batch(g, ops):
    d = call('blueprint_graph_batch', path=BP, graph_name=g, ops=ops, compile=True, save=True)
    c = d.get('compile') or {}
    print(g, {k: d.get(k) for k in ('applied', 'total', 'failed_index', 'error')}, 'errors', c.get('error_count'),
          'saved', c.get('saved'), c.get('save_error'))
    assert d.get('failed_index') is None and c.get('error_count') == 0 and c.get('saved'), d


shot, _ = graph('PayoffShot')
PATCHED = any(n['title'] in ('SetWorldLocation', 'Set World Location') for n in shot.values())
look_off = node(shot, 'SetIgnoreLookInput')
pawn_xf = node(shot, 'Get Actor Transform')
if not PATCHED:
  batch('PayoffShot', [
    dict(op='add_node', ref='key', node_type='variable_get', variable_name='WardrobeKeyLight', x=2600, y=320),
    dict(op='add_node', ref='spot', node_type='call_function', class_path=K, function_name='TransformLocation', x=2600, y=480),
    dict(op='set_pin', node_id='spot', pin_name='Location', value=KEY_IN_PAWN),
    dict(op='connect', from_node=pawn_xf, from_pin='ReturnValue', to_node='spot', to_pin='T'),
    dict(op='add_node', ref='place', node_type='call_function', class_path=SC, function_name='K2_SetWorldLocation', x=2900, y=0),
    dict(op='connect', from_node='key', from_pin='WardrobeKeyLight', to_node='place', to_pin='self'),
    dict(op='connect', from_node='spot', from_pin='ReturnValue', to_node='place', to_pin='NewLocation'),
    dict(op='add_node', ref='show', node_type='call_function', class_path=SC, function_name='SetVisibility', x=3250, y=0),
    dict(op='set_pin', node_id='show', pin_name='bNewVisibility', value='true'),
    dict(op='connect', from_node='key', from_pin='WardrobeKeyLight', to_node='show', to_pin='self'),
    dict(op='connect', from_node=look_off, from_pin='then', to_node='place', to_pin='execute'),
    dict(op='connect', from_node='place', from_pin='then', to_node='show', to_pin='execute'),
    dict(op='comment', title='Key light on the hero', node_ids=['key', 'spot', 'place', 'show'], bubble=True),
])

cut, edges = graph('PayoffShotCut')
entry = node(cut, 'PayoffShotCut')
first = node(cut, 'SetViewTargetWithBlend')
if not PATCHED:
  assert any(e['from_node'] == entry and e['to_node'] == first for e in edges), 'unexpected PayoffShotCut entry'
  batch('PayoffShotCut', [
    dict(op='disconnect', node_id=entry, pin_name='then', to_node=first, to_pin='execute'),
    dict(op='add_node', ref='key', node_type='variable_get', variable_name='WardrobeKeyLight', x=-300, y=400),
    dict(op='add_node', ref='hide', node_type='call_function', class_path=SC, function_name='SetVisibility', x=-300, y=200),
    dict(op='set_pin', node_id='hide', pin_name='bNewVisibility', value='false'),
    dict(op='connect', from_node='key', from_pin='WardrobeKeyLight', to_node='hide', to_pin='self'),
    dict(op='add_node', ref='home', node_type='call_function', class_path=SC, function_name='K2_SetRelativeLocation', x=0, y=200),
    dict(op='set_pin', node_id='home', pin_name='NewLocation', value=HOME),
    dict(op='connect', from_node='key', from_pin='WardrobeKeyLight', to_node='home', to_pin='self'),
    dict(op='connect', from_node=entry, from_pin='then', to_node='hide', to_pin='execute'),
    dict(op='connect', from_node='hide', from_pin='then', to_node='home', to_pin='execute'),
    dict(op='connect', from_node='home', from_pin='then', to_node=first, to_pin='execute'),
    dict(op='comment', title='Key light off', node_ids=['key', 'hide', 'home'], bubble=True),
])
# Tune (L1P 00:54): at 350 cm the light also washed the wall behind him (2.3 m away at the T1 spot). During the shot the
# radius drops to 200 (the wall falls outside it) and the intensity rises to 140 lm to keep him exposed; both go back
# to the template's 350 cm and 100 lm in PayoffShotCut.
LL = '/Script/Engine.LocalLightComponent'
LC = '/Script/Engine.LightComponent'
shot, _ = graph('PayoffShot')
if not any(n['title'] == 'SetAttenuationRadius' for n in shot.values()):
    show = node(shot, 'SetVisibility')
    key = node(shot, 'Get WardrobeKeyLight')
    batch('PayoffShot', [
        dict(op='add_node', ref='rad', node_type='call_function', class_path=LL, function_name='SetAttenuationRadius', x=3550, y=0),
        dict(op='set_pin', node_id='rad', pin_name='NewRadius', value='200'),
        dict(op='add_node', ref='lum', node_type='call_function', class_path=LC, function_name='SetIntensity', x=3850, y=0),
        dict(op='set_pin', node_id='lum', pin_name='NewIntensity', value='140'),
        dict(op='connect', from_node=key, from_pin='WardrobeKeyLight', to_node='rad', to_pin='self'),
        dict(op='connect', from_node=key, from_pin='WardrobeKeyLight', to_node='lum', to_pin='self'),
        dict(op='connect', from_node=show, from_pin='then', to_node='rad', to_pin='execute'),
        dict(op='connect', from_node='rad', from_pin='then', to_node='lum', to_pin='execute'),
    ])
    cut, edges = graph('PayoffShotCut')
    home = node(cut, 'Set Relative Location')
    key = node(cut, 'Get WardrobeKeyLight')
    first = node(cut, 'SetViewTargetWithBlend')
    batch('PayoffShotCut', [
        dict(op='disconnect', node_id=home, pin_name='then', to_node=first, to_pin='execute'),
        dict(op='add_node', ref='rad', node_type='call_function', class_path=LL, function_name='SetAttenuationRadius', x=300, y=200),
        dict(op='set_pin', node_id='rad', pin_name='NewRadius', value='350'),
        dict(op='add_node', ref='lum', node_type='call_function', class_path=LC, function_name='SetIntensity', x=600, y=200),
        dict(op='set_pin', node_id='lum', pin_name='NewIntensity', value='100'),
        dict(op='connect', from_node=key, from_pin='WardrobeKeyLight', to_node='rad', to_pin='self'),
        dict(op='connect', from_node=key, from_pin='WardrobeKeyLight', to_node='lum', to_pin='self'),
        dict(op='connect', from_node=home, from_pin='then', to_node='rad', to_pin='execute'),
        dict(op='connect', from_node='rad', from_pin='then', to_node='lum', to_pin='execute'),
        dict(op='connect', from_node='lum', from_pin='then', to_node=first, to_pin='execute'),
    ])
# Reset guard (coordinator, 2026-11-18): ResetHouse clears the PayoffShotOut / PayoffShotCut timers, so a Restart Day
# or Quit to Title during the 2.5 s hero shot never ran PayoffShotCut and left the light on at the hero spot. ResetHouse
# now puts it back the same way, right after it clears those timers.
reset, edges = graph('ResetHouse')
if not any(n['title'] == 'SetAttenuationRadius' for n in reset.values()):
    cut_timer = node(reset, 'Clear Timer by Function Name', FunctionName='PayoffShotCut')
    after = [e for e in edges if e['from_node'] == cut_timer and e['from_pin'] == 'then']
    assert len(after) == 1, after
    nxt = after[0]['to_node']
    batch('ResetHouse', [
        dict(op='disconnect', node_id=cut_timer, pin_name='then', to_node=nxt, to_pin='execute'),
        dict(op='add_node', ref='key', node_type='variable_get', variable_name='WardrobeKeyLight', x=0, y=900),
        dict(op='add_node', ref='hide', node_type='call_function', class_path=SC, function_name='SetVisibility', x=0, y=700),
        dict(op='set_pin', node_id='hide', pin_name='bNewVisibility', value='false'),
        dict(op='add_node', ref='home', node_type='call_function', class_path=SC, function_name='K2_SetRelativeLocation', x=300, y=700),
        dict(op='set_pin', node_id='home', pin_name='NewLocation', value=HOME),
        dict(op='add_node', ref='rad', node_type='call_function', class_path=LL, function_name='SetAttenuationRadius', x=600, y=700),
        dict(op='set_pin', node_id='rad', pin_name='NewRadius', value='350'),
        dict(op='add_node', ref='lum', node_type='call_function', class_path=LC, function_name='SetIntensity', x=900, y=700),
        dict(op='set_pin', node_id='lum', pin_name='NewIntensity', value='100'),
        *[dict(op='connect', from_node='key', from_pin='WardrobeKeyLight', to_node=r, to_pin='self') for r in ('hide', 'home', 'rad', 'lum')],
        dict(op='connect', from_node=cut_timer, from_pin='then', to_node='hide', to_pin='execute'),
        dict(op='connect', from_node='hide', from_pin='then', to_node='home', to_pin='execute'),
        dict(op='connect', from_node='home', from_pin='then', to_node='rad', to_pin='execute'),
        dict(op='connect', from_node='rad', from_pin='then', to_node='lum', to_pin='execute'),
        dict(op='connect', from_node='lum', from_pin='then', to_node=nxt, to_pin='execute'),
        dict(op='comment', title='Payoff light back', node_ids=['key', 'hide', 'home', 'rad', 'lum'], bubble=True),
    ])
# Head room (L1W after a real win, 02:30): with the 2.39:1 letterbox on, the aim at 35 cm above the capsule centre put
# his head against the top bar. The aim rises to 45 cm (about 3 deg of tilt).
shot, _ = graph('PayoffShot')
aim = node(shot, 'TransformLocation', Location='(X=0.0,Y=0.0,Z=35.0)') if any(
    n['title'] == 'TransformLocation' and any(p.get('default_value') == '(X=0.0,Y=0.0,Z=35.0)' for p in n['pins'])
    for n in shot.values()) else None
if aim:
    batch('PayoffShot', [dict(op='set_pin', node_id=aim, pin_name='Location', value='(X=0.0,Y=0.0,Z=45.0)')])
print('PAYOFF_KEY_LIGHT done')
