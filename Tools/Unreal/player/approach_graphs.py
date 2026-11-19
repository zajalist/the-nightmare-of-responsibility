"""Walk up to it instead of "Move closer to reach it." (the user, live playtest 2026-11-09). Hayba graph batches.
BP_Interactable.BeginPendingRow's bare-hand gate (Codex, Nov 8) narrated "Move closer" whenever the standing reach check
failed, and a low knob can never pass it from outside the capsule, so it looped forever. Now:
- BP_FoAPlayer.ApproachAndInteract(Target, Verb, Item): from the contact point the gate just measured
  (EnvironmentContactAim) pick a stand spot on the player's side, capsule radius + 14 cm out, never farther than he
  already is (already close: no backing away, he just turns and does it). The spot is collision-checked with a capsule
  sweep from where he stands; if blocked it tries 35 deg either side around the target, and falls back to the direct
  spot (the 1.6 s cap still ends the walk). Input locks, the view eases onto the target (InteractLook).
- UpdateApproach (on Tick, first): forced movement input toward the spot, so the real GASP start, walk and stop play.
  Within 6 cm, or after 1.6 s, FinishApproach unlocks and re-issues the same Interact(Verb, Item) through
  BPI_Interactable, with a one-shot bReachOverride that BeginEnvironmentContact honours, so the row always starts.
- BP_Interactable.BeginPendingRow: the Narrate("Move closer to reach it.") becomes ApproachAndInteract(self, Verb, Item).
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/approach_graphs.py      (backs up both assets first)"""
import datetime
import shutil
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PC = P + '.BP_FoAPlayer_C'
BI = '/Game/FoA/Gameplay/BP_Interactable'
BPI = '/Game/FoA/Gameplay/BPI_Interactable.BPI_Interactable_C'
K = '/Script/Engine.KismetMathLibrary:'
SYS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
CAP = '/Script/Engine.CapsuleComponent:'
CLEAR_CM, ARRIVE_CM, CAP_S, SIDE_DEG = 20.0, 6.0, 1.6, 35.0

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
bk = Path('P:/FoA/Saved/Backups/approach') / stamp
bk.mkdir(parents=True, exist_ok=True)
for a in (P, BI):
    src = Path('P:/FoA/Content') / (a.removeprefix('/Game/') + '.uasset')
    shutil.copy2(src, bk / src.name)
print('backup', bk)

for name, typ in (('bApproaching', 'bool'), ('ApproachTarget', 'object:/Script/Engine.Actor'), ('ApproachVerb', 'name'),
                  ('ApproachItem', 'name'), ('ApproachSpot', 'vector'), ('ApproachStarted', 'float'), ('bReachOverride', 'bool')):
    r = h.call('blueprint_add_variable', dict(path=P, variable_name=name, variable_type=typ, instance_editable=False,
                                              update_existing=True, category='Approach'))
    assert r.get('ok'), r


def ensure_fn(name, inputs=()):
    if not h.call('blueprint_inspect_graph', dict(path=P, graph_name=name)).get('ok'):
        r = h.call('blueprint_add_function', dict(path=P, function_name=name, inputs=list(inputs)))
        assert r.get('ok'), r
    nodes, _ = inspect(P, name)
    return find(nodes, name), len(nodes)


# ---------------------------------------------------------------- ApproachAndInteract(Target, Verb, Item)
e, n = ensure_fn('ApproachAndInteract', [dict(name='Target', type='object:/Script/Engine.Actor'), dict(name='Verb', type='name'),
                                         dict(name='Item', type='name')])
if n <= 1:
    b = Batch(P, 'ApproachAndInteract')
    b.set('t', 'ApproachTarget', 300, 0); b.link(e, 'Target', 't', 'ApproachTarget')
    b.set('v', 'ApproachVerb', 600, 0); b.link(e, 'Verb', 'v', 'ApproachVerb')
    b.set('i', 'ApproachItem', 900, 0); b.link(e, 'Item', 'i', 'ApproachItem')
    b.set('look', 'InteractLook', 1200, 0); b.link(e, 'Target', 'look', 'InteractLook')
    b.chain(e, 't', 'v', 'i', 'look')
    # geometry: contact point, direction to him on the floor plane, stand distance (never farther than he is)
    b.get('aim', 'EnvironmentContactAim', 0, 400)
    b.fn('me', '/Script/Engine.Actor:K2_GetActorLocation', 0, 600)
    b.fn('diff', K + 'Subtract_VectorVector', 300, 500); b.link('me', 'ReturnValue', 'diff', 'A'); b.link('aim', 'EnvironmentContactAim', 'diff', 'B')
    b.fn('dxy', K + 'BreakVector', 600, 500); b.link('diff', 'ReturnValue', 'dxy', 'InVec')
    b.fn('flat', K + 'MakeVector', 900, 500, Z=0.0); b.link('dxy', 'X', 'flat', 'X'); b.link('dxy', 'Y', 'flat', 'Y')
    b.fn('dir', K + 'Normal', 1200, 500); b.link('flat', 'ReturnValue', 'dir', 'A')
    b.fn('away', K + 'VSize', 1200, 700); b.link('flat', 'ReturnValue', 'away', 'A')
    b.get('cap', 'CapsuleComponent', 0, 900)  # inherited member of self: no class_path (that makes a target pin)
    b.fn('rad', CAP + 'GetScaledCapsuleRadius', 300, 900); b.link('cap', 'CapsuleComponent', 'rad', 'self')
    b.fn('hh', CAP + 'GetScaledCapsuleHalfHeight', 300, 1100); b.link('cap', 'CapsuleComponent', 'hh', 'self')
    b.fn('want', K + 'Add_DoubleDouble', 600, 900, B=CLEAR_CM); b.link('rad', 'ReturnValue', 'want', 'A')
    b.fn('dist', K + 'FMin', 900, 900); b.link('want', 'ReturnValue', 'dist', 'A'); b.link('away', 'ReturnValue', 'dist', 'B')
    b.fn('mez', K + 'BreakVector', 300, 700); b.link('me', 'ReturnValue', 'mez', 'InVec')
    # the sweep capsule is 3 cm thinner and 10 cm shorter, so the floor and a rug edge never count as blocking
    b.fn('rads', K + 'Subtract_DoubleDouble', 600, 1100, B=3.0); b.link('rad', 'ReturnValue', 'rads', 'A')
    b.fn('hhs', K + 'Subtract_DoubleDouble', 600, 1250, B=10.0); b.link('hh', 'ReturnValue', 'hhs', 'A')
    spots = []
    for k, ang in enumerate((0.0, SIDE_DEG, -SIDE_DEG)):
        y = 1300 + k * 450
        b.fn('rot%d' % k, K + 'RotateAngleAxis', 1500, y, AngleDeg=ang, Axis='0,0,1'); b.link('dir', 'ReturnValue', 'rot%d' % k, 'InVect')
        b.fn('off%d' % k, K + 'Multiply_VectorFloat', 1800, y); b.link('rot%d' % k, 'ReturnValue', 'off%d' % k, 'A'); b.link('dist', 'ReturnValue', 'off%d' % k, 'B')
        b.fn('pt%d' % k, K + 'Add_VectorVector', 2100, y); b.link('aim', 'EnvironmentContactAim', 'pt%d' % k, 'A'); b.link('off%d' % k, 'ReturnValue', 'pt%d' % k, 'B')
        b.fn('pxy%d' % k, K + 'BreakVector', 2400, y); b.link('pt%d' % k, 'ReturnValue', 'pxy%d' % k, 'InVec')
        b.fn('spot%d' % k, K + 'MakeVector', 2700, y); b.link('pxy%d' % k, 'X', 'spot%d' % k, 'X'); b.link('pxy%d' % k, 'Y', 'spot%d' % k, 'Y')
        b.link('mez', 'Z', 'spot%d' % k, 'Z')
        b.fn('sweep%d' % k, SYS + 'CapsuleTraceSingle', 3000 + k * 900, 0, TraceChannel='TraceTypeQuery1', bTraceComplex='false',
             DrawDebugType='None', bIgnoreSelf='true')
        b.link('me', 'ReturnValue', 'sweep%d' % k, 'Start'); b.link('spot%d' % k, 'ReturnValue', 'sweep%d' % k, 'End')
        b.link('rads', 'ReturnValue', 'sweep%d' % k, 'Radius'); b.link('hhs', 'ReturnValue', 'sweep%d' % k, 'HalfHeight')
        b.node('free%d' % k, 'branch', 3300 + k * 900, 0); b.link('sweep%d' % k, 'ReturnValue', 'free%d' % k, 'Condition')
        b.set('use%d' % k, 'ApproachSpot', 3600 + k * 900, 250); b.link('spot%d' % k, 'ReturnValue', 'use%d' % k, 'ApproachSpot')
        b.link('sweep%d' % k, 'then', 'free%d' % k, 'execute'); b.link('free%d' % k, 'else', 'use%d' % k, 'execute')  # no hit: free
        spots.append(k)
    b.link('look', 'then', 'sweep0', 'execute')
    b.link('free0', 'then', 'sweep1', 'execute'); b.link('free1', 'then', 'sweep2', 'execute')
    b.set('fallback', 'ApproachSpot', 5700, 500); b.link('spot0', 'ReturnValue', 'fallback', 'ApproachSpot')
    b.link('free2', 'then', 'fallback', 'execute')
    b.fn('now', GS + 'GetTimeSeconds', 6000, 300)
    b.set('started', 'ApproachStarted', 6000, 0); b.link('now', 'ReturnValue', 'started', 'ApproachStarted')
    for k in spots:
        b.link('use%d' % k, 'then', 'started', 'execute')
    b.link('fallback', 'then', 'started', 'execute')
    b.set('going', 'bApproaching', 6300, 0); b.pin('going', 'bApproaching', 'true')
    b.fn('lock', PC + ':SetInteractionLocked', 6600, 0, bEnable='true')
    b.chain('started', 'going', 'lock')
    b.comment('Remember the interaction', ['t', 'v', 'i', 'look'])
    b.comment('Stand spot on his side', ['aim', 'me', 'diff', 'dxy', 'flat', 'dir', 'away', 'cap', 'rad', 'hh', 'want', 'dist', 'mez', 'rads', 'hhs'] +
              [r % k for k in spots for r in ('rot%d', 'off%d', 'pt%d', 'pxy%d', 'spot%d')])
    b.comment('Free path, else the next angle', [r % k for k in spots for r in ('sweep%d', 'free%d', 'use%d')] + ['fallback'])
    b.comment('Walk there', ['now', 'started', 'going', 'lock'])
    b.run()

# ---------------------------------------------------------------- FinishApproach()
e, n = ensure_fn('FinishApproach')
if n <= 1:
    b = Batch(P, 'FinishApproach')
    b.set('stop', 'bApproaching', 300, 0); b.pin('stop', 'bApproaching', 'false')
    b.fn('unlock', PC + ':SetInteractionLocked', 600, 0, bEnable='false')
    b.set('override', 'bReachOverride', 900, 0); b.pin('override', 'bReachOverride', 'true')
    b.get('tg', 'ApproachTarget', 900, 300); b.get('vb', 'ApproachVerb', 900, 450); b.get('it', 'ApproachItem', 900, 600)
    b.node('again', 'message', 1200, 0, function_name='Interact', class_path=BPI)
    b.link('tg', 'ApproachTarget', 'again', 'self'); b.link('vb', 'ApproachVerb', 'again', 'Verb'); b.link('it', 'ApproachItem', 'again', 'HeldItem')
    b.chain(e, 'stop', 'unlock', 'override', 'again')
    b.comment('Arrived: do it', ['stop', 'unlock', 'override', 'tg', 'vb', 'it', 'again'])
    b.run()

# ---------------------------------------------------------------- UpdateApproach() (Tick)
e, n = ensure_fn('UpdateApproach')
if n <= 1:
    b = Batch(P, 'UpdateApproach')
    b.get('on', 'bApproaching', 0, 300)
    b.node('active', 'branch', 300, 0); b.link('on', 'bApproaching', 'active', 'Condition'); b.chain(e, 'active')
    b.get('spot', 'ApproachSpot', 0, 500)
    b.fn('me', '/Script/Engine.Actor:K2_GetActorLocation', 0, 700)
    b.fn('to', K + 'Subtract_VectorVector', 300, 600); b.link('spot', 'ApproachSpot', 'to', 'A'); b.link('me', 'ReturnValue', 'to', 'B')
    b.fn('txy', K + 'BreakVector', 600, 600); b.link('to', 'ReturnValue', 'txy', 'InVec')
    b.fn('flat', K + 'MakeVector', 900, 600, Z=0.0); b.link('txy', 'X', 'flat', 'X'); b.link('txy', 'Y', 'flat', 'Y')
    b.fn('left', K + 'VSize', 1200, 600); b.link('flat', 'ReturnValue', 'left', 'A')
    b.fn('there', K + 'Less_DoubleDouble', 1500, 600, B=ARRIVE_CM); b.link('left', 'ReturnValue', 'there', 'A')
    b.fn('now', GS + 'GetTimeSeconds', 1200, 900)
    b.get('began', 'ApproachStarted', 1200, 1050)
    b.fn('spent', K + 'Subtract_DoubleDouble', 1500, 900); b.link('now', 'ReturnValue', 'spent', 'A'); b.link('began', 'ApproachStarted', 'spent', 'B')
    b.fn('late', K + 'Greater_DoubleDouble', 1800, 900, B=CAP_S); b.link('spent', 'ReturnValue', 'late', 'A')
    b.fn('done', K + 'BooleanOR', 2100, 600); b.link('there', 'ReturnValue', 'done', 'A'); b.link('late', 'ReturnValue', 'done', 'B')
    b.node('arrive', 'branch', 600, 0); b.link('done', 'ReturnValue', 'arrive', 'Condition'); b.link('active', 'then', 'arrive', 'execute')
    b.fn('finish', PC + ':FinishApproach', 900, -200); b.link('arrive', 'then', 'finish', 'execute')
    b.fn('dir', K + 'Normal', 1500, 300); b.link('flat', 'ReturnValue', 'dir', 'A')
    b.fn('ease', K + 'Divide_DoubleDouble', 1800, 300, B=40.0); b.link('left', 'ReturnValue', 'ease', 'A')
    b.fn('scale', K + 'FClamp', 2100, 300, Min=0.4, Max=1.0); b.link('ease', 'ReturnValue', 'scale', 'Value')
    b.fn('step', '/Script/Engine.Pawn:AddMovementInput', 2400, 0, bForce='true')
    b.link('dir', 'ReturnValue', 'step', 'WorldDirection'); b.link('scale', 'ReturnValue', 'step', 'ScaleValue')
    b.link('arrive', 'else', 'step', 'execute')
    b.comment('Walk to the stand spot', ['on', 'active', 'spot', 'me', 'to', 'txy', 'flat', 'left', 'there', 'now', 'began', 'spent',
                                         'late', 'done', 'arrive', 'finish', 'dir', 'ease', 'scale', 'step'])
    b.run()

# ---------------------------------------------------------------- Tick: UpdateApproach first
nodes, edges = inspect(P, 'EventGraph')
if not any(nd['title'].replace(' ', '') == 'UpdateApproach' for nd in nodes):
    tick = find(nodes, 'Event Tick')
    first = next(x for x in edges if x['from_node'] == tick and x['from_pin'] == 'then')
    b = Batch(P, 'EventGraph')
    b.fn('approach', PC + ':UpdateApproach', 300, 3400)
    b.cut(tick, 'then', first['to_node'], first['to_pin'])
    b.link(tick, 'then', 'approach', 'execute'); b.link('approach', 'then', first['to_node'], first['to_pin'])
    b.comment('Walk up to it', ['approach'])
    b.run()

# ---------------------------------------------------------------- BeginEnvironmentContact honours one override
nodes, edges = inspect(P, 'BeginEnvironmentContact')
if not any(nd['title'] == 'Get bReachOverride' for nd in nodes):
    tail = find(nodes, 'Set EnvironmentContactUpperarmTwist')
    assert not any(x['from_node'] == tail and x['from_pin'] == 'then' for x in edges), 'contact tail moved'
    b = Batch(P, 'BeginEnvironmentContact')
    b.get('ovr', 'bReachOverride', 8700, 300)
    b.node('after', 'branch', 8700, 0); b.link('ovr', 'bReachOverride', 'after', 'Condition'); b.link(tail, 'then', 'after', 'execute')
    b.set('reach', 'EnvironmentContactReachable', 9000, 0); b.pin('reach', 'EnvironmentContactReachable', 'true')
    b.set('spent', 'bReachOverride', 9300, 0); b.pin('spent', 'bReachOverride', 'false')
    b.link('after', 'then', 'reach', 'execute'); b.chain('reach', 'spent')
    b.comment('After an approach, always start', ['ovr', 'after', 'reach', 'spent'])
    b.run()

# ---------------------------------------------------------------- BP_Interactable: walk up instead of "Move closer"
nodes, edges = inspect(BI, 'BeginPendingRow')
say = next((nd['node_id'] for nd in nodes if nd['title'] == 'Narrate'), None)
if say:
    byid = {nd['node_id']: nd for nd in nodes}
    into = next(x for x in edges if x['to_node'] == say and x['to_pin'] == 'execute')
    assert byid[into['from_node']]['title'] == 'ClearEnvironmentContact', 'unexpected Move closer wiring'
    feeders = {x['from_node'] for x in edges if x['to_node'] == say and x['to_pin'] in ('self', 'Line')}
    cast = find(nodes, 'Cast To BP_FoAPlayer')
    row = next(nd for nd in nodes if any(p['name'].startswith('Item_') for p in nd.get('pins', [])))
    item = next(p['name'] for p in row['pins'] if p['name'].startswith('Item_'))
    verb = next(p['name'] for p in row['pins'] if p['name'].startswith('Verb_'))
    b = Batch(BI, 'BeginPendingRow')
    b.node('me', 'self', 0, -650)
    b.fn('walk', PC + ':ApproachAndInteract', 0, -450)
    b.link(cast, 'AsBP Fo APlayer', 'walk', 'self'); b.link('me', 'self', 'walk', 'Target')
    b.link(row['node_id'], verb, 'walk', 'Verb'); b.link(row['node_id'], item, 'walk', 'Item')
    b.cut(into['from_node'], into['from_pin'], say, 'execute'); b.link(into['from_node'], into['from_pin'], 'walk', 'execute')
    b.ops.append(dict(op='remove', node_ids=[say] + [f for f in feeders if byid[f]['title'] in ('GetInteractor', 'To Text (String)')]))
    b.comment('Walk up to it, then do it', ['me', 'walk'])
    b.run()
print('APPROACH_BUILT')
