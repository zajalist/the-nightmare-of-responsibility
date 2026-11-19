"""The fall knocks the coat-rail hanger down (QA S2 softlock, main's go 2026-11-10). On the screwdriver route the player
first needs the hanger at T7 (the bed's ClothingSnag: "Hook the shirt with the wire hanger"), but once the wardrobe is
down no standable spot is within reach of Hanger_CoatRail (QA's survey and Saved/StoryShots/t7_geometry.json: standable
floor only at x <= 165; Spot_Hanger_WardrobeSide is the old wardrobe-side hook, inside FallenWardrobeBlocker).
  StageWrongWall (T7, top-down, the door moves): DropCoatRailHanger.
  DropCoatRailHanger: the BP_Pickup nearest the rail hook (within 30 cm) that is still Available falls off the rail
      and slides across the floor to (135, 165), lying flat (0.55 s, accelerating), then S_Props_HangerRail where it
      lands. Its rail transform is kept (DroppedHanger, DroppedHangerHome). Nothing happens if he already took it.
  TickHangerDrop: the fall/slide, 60 Hz timer.
  ResetHouse: the hanger back on the rail.
The door route keeps working: DT_Items Hanger has UsedBecomes None, so using it on the door never consumes it.
Hayba only; idempotent.  python Tools/Unreal/flow/patch_t7_hanger_drop.py"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
PICKUP = '/Game/FoA/Gameplay/BP_Pickup.BP_Pickup_C'
BASE = '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'
CLATTER = '/Game/FoA/Audio/MetaSounds/Props/S_Props_HangerRail.S_Props_HangerRail'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
A = '/Script/Engine.Actor:'
HOOK = '(X=359.7,Y=193.4,Z=157.6)'   # Hanger_CoatRail on the rail
SPOT = '(X=135.0,Y=165.0,Z=1.0)'     # open floor, 1.3 m from where the fall hands him back, in his view
LYING = dict(Roll=90.0, Pitch=0.0, Yaw=25.0)  # the mesh's thin local Y up: flat on the boards
TIME = 0.55
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def has(graph):
    return h.call('blueprint_inspect_graph', {'path': P, 'graph_name': graph}).get('ok')


def next_of(es, node, pin='then'):
    hits = [x for x in es if x['from_node'] == node and x['from_pin'] == pin]
    return hits[0] if hits else None


def drop():
    ns, _ = inspect(P, 'DropCoatRailHanger')
    if any(n['title'] == 'Set Timer by Function Name' for n in ns):
        return 'kept'
    e = find(ns, 'DropCoatRailHanger')
    b = Batch(P, 'DropCoatRailHanger')
    b.get('old', 'DroppedHanger', 0, 300)
    b.fn('already', KS + 'IsValid', 200, 300)
    b.link('old', 'DroppedHanger', 'already', 'Object')
    b.node('fresh', 'branch', 300, 0)
    b.link('already', 'ReturnValue', 'fresh', 'Condition')
    b.fn('all', GS + 'GetAllActorsOfClass', 600, 0, ActorClass=PICKUP)
    b.fn('near', GS + 'FindNearestActor', 900, 300, Origin=HOOK)
    b.link('all', 'OutActors', 'near', 'ActorsToCheck')
    b.fn('close', K + 'Less_DoubleDouble', 1150, 450, B=30.0)
    b.link('near', 'Distance', 'close', 'A')
    b.node('found', 'branch', 1200, 0)
    b.link('close', 'ReturnValue', 'found', 'Condition')
    b.node('item', 'cast', 1450, 0, class_path=BASE)
    b.link('near', 'ReturnValue', 'item', 'Object')
    b.get('state', 'State', 1450, 300, BASE)
    b.link('item', 'AsBP Interactable', 'state', 'self')
    b.fn('onrail', K + 'EqualEqual_NameName', 1700, 300, B='Available')
    b.link('state', 'State', 'onrail', 'A')
    b.node('avail', 'branch', 1750, 0)
    b.link('onrail', 'ReturnValue', 'avail', 'Condition')
    b.set('keep', 'DroppedHanger', 2000, 0)
    b.link('near', 'ReturnValue', 'keep', 'DroppedHanger')
    b.fn('xf', A + 'GetTransform', 2000, 300)
    b.link('near', 'ReturnValue', 'xf', 'self')
    b.set('home', 'DroppedHangerHome', 2250, 0)
    b.link('xf', 'ReturnValue', 'home', 'DroppedHangerHome')
    b.fn('now', GS + 'GetTimeSeconds', 2250, 300)
    b.set('start', 'HangerDropStart', 2500, 0)
    b.link('now', 'ReturnValue', 'start', 'HangerDropStart')
    b.fn('tick', KS + 'K2_SetTimer', 2750, 0, FunctionName='TickHangerDrop', Time=1.0 / 60, bLooping='true')
    b.link(e, 'then', 'fresh', 'execute')
    b.link('fresh', 'else', 'all', 'execute')
    b.chain('all', 'found')
    b.link('found', 'then', 'item', 'execute')
    b.link('item', 'then', 'avail', 'execute')
    b.link('avail', 'then', 'keep', 'execute')
    b.chain('keep', 'home', 'start', 'tick')
    b.comment('The fall takes the hanger off the rail', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def tick():
    ns, _ = inspect(P, 'TickHangerDrop')
    if any(n['title'] == 'PlaySoundAtLocation' for n in ns):
        return 'kept'
    e = find(ns, 'TickHangerDrop')
    b = Batch(P, 'TickHangerDrop')
    b.get('hanger', 'DroppedHanger', 0, 300)
    b.fn('valid', KS + 'IsValid', 200, 300)
    b.link('hanger', 'DroppedHanger', 'valid', 'Object')
    b.node('live', 'branch', 300, 0)
    b.link('valid', 'ReturnValue', 'live', 'Condition')
    b.fn('now', GS + 'GetTimeSeconds', 300, 600)
    b.get('start', 'HangerDropStart', 300, 750)
    b.fn('since', K + 'Subtract_DoubleDouble', 550, 600)
    b.link('now', 'ReturnValue', 'since', 'A')
    b.link('start', 'HangerDropStart', 'since', 'B')
    b.fn('frac', K + 'Divide_DoubleDouble', 800, 600, B=TIME)
    b.link('since', 'ReturnValue', 'frac', 'A')
    b.fn('alpha', K + 'FClamp', 1050, 600, Min=0.0, Max=1.0)
    b.link('frac', 'ReturnValue', 'alpha', 'Value')
    b.fn('ease', K + 'Multiply_DoubleDouble', 1300, 600)  # accelerating, like a fall
    b.link('alpha', 'ReturnValue', 'ease', 'A')
    b.link('alpha', 'ReturnValue', 'ease', 'B')
    b.get('home', 'DroppedHangerHome', 300, 900)
    b.fn('parts', K + 'BreakTransform', 550, 900)
    b.link('home', 'DroppedHangerHome', 'parts', 'InTransform')
    b.fn('where', K + 'VLerp', 1550, 900, B=SPOT)
    b.link('parts', 'Location', 'where', 'A')
    b.link('ease', 'ReturnValue', 'where', 'Alpha')
    b.fn('flat', K + 'MakeRotator', 1300, 1100, **LYING)
    b.fn('turn', K + 'RLerp', 1550, 1100, bShortestPath='true')
    b.link('parts', 'Rotation', 'turn', 'A')
    b.link('flat', 'ReturnValue', 'turn', 'B')
    b.link('alpha', 'ReturnValue', 'turn', 'Alpha')
    b.fn('move', A + 'K2_SetActorLocationAndRotation', 1800, 0, bSweep='false', bTeleport='true')
    b.link('hanger', 'DroppedHanger', 'move', 'self')
    b.link('where', 'ReturnValue', 'move', 'NewLocation')
    b.link('turn', 'ReturnValue', 'move', 'NewRotation')
    b.fn('landed', K + 'GreaterEqual_DoubleDouble', 2000, 600, B=1.0)
    b.link('alpha', 'ReturnValue', 'landed', 'A')
    b.node('done', 'branch', 2100, 0)
    b.link('landed', 'ReturnValue', 'done', 'Condition')
    b.fn('stop', KS + 'K2_ClearTimer', 2350, 0, FunctionName='TickHangerDrop')
    b.fn('spot', K + 'MakeVector', 2350, 300, X=135.0, Y=165.0, Z=1.0)
    b.fn('clatter', GS + 'PlaySoundAtLocation', 2650, 0, Sound=CLATTER)
    b.link('spot', 'ReturnValue', 'clatter', 'Location')
    b.fn('stopdead', KS + 'K2_ClearTimer', 600, -250, FunctionName='TickHangerDrop')
    b.link(e, 'then', 'live', 'execute')
    b.link('live', 'then', 'move', 'execute')
    b.link('live', 'else', 'stopdead', 'execute')
    b.chain('move', 'done')
    b.link('done', 'then', 'stop', 'execute')
    b.chain('stop', 'clatter')
    b.comment('Off the rail and across the floor', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def hook_stage():
    ns, es = inspect(P, 'StageWrongWall')
    if any(n['title'] == 'DropCoatRailHanger' for n in ns):
        return 'kept'
    door = find(ns, 'MoveDoor')
    after = next_of(es, door)
    b = Batch(P, 'StageWrongWall')
    b.cut(door, 'then', after['to_node'], after['to_pin'])
    b.fn('drop', C + ':DropCoatRailHanger', 700, -200)
    b.link(door, 'then', 'drop', 'execute')
    b.link('drop', 'then', after['to_node'], after['to_pin'])
    b.run()
    return 'StageWrongWall drops it after the door moves'


def restore():
    ns, es = inspect(P, 'ResetHouse')
    if any(n['title'] == 'Set DroppedHanger' for n in ns):
        return 'kept'
    anchor = next(n['node_id'] for n in ns if n['title'] == 'Clear Timer by Function Name'
                  and any(p['name'] == 'FunctionName' and p.get('default_value') == 'PayoffShotCut' for p in n['pins']))
    after = next_of(es, anchor)
    b = Batch(P, 'ResetHouse')
    b.get('hanger', 'DroppedHanger', 1350, 450)
    b.fn('valid', KS + 'IsValid', 1350, 600)
    b.link('hanger', 'DroppedHanger', 'valid', 'Object')
    b.node('was', 'branch', 1400, 300)
    b.link('valid', 'ReturnValue', 'was', 'Condition')
    b.fn('stop', KS + 'K2_ClearTimer', 1450, 300, FunctionName='TickHangerDrop')
    b.get('home', 'DroppedHangerHome', 1500, 600)
    b.fn('back', A + 'K2_SetActorTransform', 1550, 300, bSweep='false', bTeleport='true')
    b.link('hanger', 'DroppedHanger', 'back', 'self')
    b.link('home', 'DroppedHangerHome', 'back', 'NewTransform')
    b.set('forget', 'DroppedHanger', 1650, 300)
    b.cut(anchor, 'then', after['to_node'], after['to_pin'])
    b.link(anchor, 'then', 'was', 'execute')
    b.link('was', 'then', 'stop', 'execute')
    b.chain('stop', 'back', 'forget')
    b.link('forget', 'then', after['to_node'], after['to_pin'])
    b.link('was', 'else', after['to_node'], after['to_pin'])
    b.comment('The hanger back on the rail', ['hanger', 'valid', 'was', 'stop', 'home', 'back', 'forget'])
    b.run()
    return 'ResetHouse hangs it back'


assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
token = h.lease_acquire('story', ['asset:' + P], ttl_s=300, wait_s=240)
try:
    for name, t in (('DroppedHanger', 'object:/Script/Engine.Actor'), ('DroppedHangerHome', 'transform'),
                    ('HangerDropStart', 'float')):
        call('blueprint_add_variable', path=P, variable_name=name, variable_type=t, category='Story|T7 hanger', update_existing=True)
    for fn in ('DropCoatRailHanger', 'TickHangerDrop'):
        if not has(fn):
            call('blueprint_add_function', path=P, function_name=fn)
    report = dict(Drop=drop(), Tick=tick(), Stage=hook_stage(), Reset=restore())
    Path('P:/FoA/Saved/StoryShots/t7_hanger_drop.json').write_text(json.dumps(report, indent=1))
    print('t7 hanger drop', report)
finally:
    h.release('story', token)
