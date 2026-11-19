"""Door-tool lane: the four lock-plate screws back out under the screwdriver and drop, instead of vanishing (BP_Door).
- SelectToolScrew(I): ToolScrewSel / ToolScrewSelHome = screw I and its home (relative) transform.
- PlaceSelectedToolScrew(Out, Turn): the selected screw at its home, Out cm out of the plate (door -X), turned Turn deg
  about its own axis (door X; SM_DoorLockScrew's axis is X).
- HomeToolScrews(): keeps the four homes the first time (the screws are home then), afterwards puts all four back.
  Called by BeginDoorTool (after the step index resets) and CancelPendingRow (new day).
- RefreshDoorTool, screwdriver, screw ToolStepIndex < 4: the screw turns with the driving 70% of each 90 deg stroke and
  holds while the wrist regrips (the hand's ratchet in SetToolHandRotation), so it advances 90 deg a stroke and comes out
  OUT_CM over its 720 deg (8 strokes). The screws are no longer hidden while the tool runs (they fall instead);
  RestoreDoorTool still hides plate and screws once the plate is off.
- AdvanceDoorTool: when a screw comes out, DropToolScrew(index - 1) replaces the old ScrewDrop sound at the plate.
- DropToolScrew(I) + TickToolScrewDrop (60/s timer): pops free (25 cm/s away from the door), falls under gravity to the
  floor, one 1 cm bounce, spins about the vertical while airborne, plays S_Props_ScrewDrop where it lands, stops.
Idempotent per step. Hayba batches, each compiled 0/0 and saved (or rolled back).
  $env:HAYBA_AGENT_ID='doortool'; python Tools/Unreal/doortool/screw_out.py"""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
from hayba_call import call  # noqa: E402
from held_tool_graphs import Batch, inspect, find, K, SC  # noqa: E402

DOOR = '/Game/FoA/Gameplay/BP_Door'
ME = DOOR + '.BP_Door_C:'
KS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
DROP_SOUND = '/Game/FoA/Audio/MetaSounds/Props/S_Props_ScrewDrop.S_Props_ScrewDrop'
OUT_CM = 1.2  # SM_DoorLockScrew is 1.6 cm long at the plate's 0.42 scale: out by 1.2, it is free
G, VB, VX, SPIN = 981.0, 45.0, 25.0, 600.0  # cm/s2; bounce cm/s (1 cm high); pop-out cm/s; deg/s while airborne
TB = 2 * VB / G  # bounce duration
REST = 0.43  # the lying screw's centre above the floor (half its 0.85 cm head)
SMC = 'object:/Script/Engine.StaticMeshComponent'


def functions():
    return [str(f) for f in (call('blueprint_get_info', dict(path=DOOR))['data'].get('functions') or [])]


def ensure_members():
    for name, typ in ([('ToolScrewHome%d' % i, 'transform') for i in range(4)] +
                      [('bToolScrewHomes', 'bool'), ('ToolScrewSel', SMC), ('ToolScrewSelHome', 'transform'),
                       ('ToolDropScrew', SMC), ('ToolDropFrom', 'transform'), ('ToolDropTime', 'float'), ('bToolDropLanded', 'bool')]):
        r = call('blueprint_add_variable', dict(path=DOOR, variable_name=name, variable_type=typ, instance_editable=False,
                                                update_existing=True, category='Door tool'))
        assert r.get('ok'), (name, r)
    have = functions()
    for name, inputs in (('SelectToolScrew', [dict(name='I', type='int')]),
                         ('PlaceSelectedToolScrew', [dict(name='Out', type='float'), dict(name='Turn', type='float')]),
                         ('HomeToolScrews', []), ('DropToolScrew', [dict(name='I', type='int')]), ('TickToolScrewDrop', [])):
        if name not in have:
            r = call('blueprint_add_function', dict(path=DOOR, function_name=name, inputs=inputs))
            assert r.get('ok'), (name, r)


def empty(fn):
    nodes, _ = inspect(DOOR, fn)
    return find(nodes, fn) if len([n for n in nodes if n['title'] != 'Comment']) <= 1 else None


def select():
    e = empty('SelectToolScrew')
    if not e:
        return print('SelectToolScrew built')
    b = Batch(DOOR, 'SelectToolScrew')
    prev, pin = e, 'then'
    for i in range(4):
        x, y = 300 + i * 650, i * 300
        if i < 3:
            b.fn(f'eq{i}', K + 'EqualEqual_IntInt', x, y + 200, B=i); b.link(e, 'I', f'eq{i}', 'A')
            b.node(f'br{i}', 'branch', x, y); b.link(f'eq{i}', 'ReturnValue', f'br{i}', 'Condition')
            b.link(prev, pin, f'br{i}', 'execute')
            first, prev, pin = (f'br{i}', 'then'), f'br{i}', 'else'
        else:
            first = (prev, pin)
        b.get(f'c{i}', f'ToolScrew{i}', x + 250, y + 450); b.get(f'h{i}', f'ToolScrewHome{i}', x + 250, y + 600)
        b.set(f'sc{i}', 'ToolScrewSel', x + 250, y + 150); b.link(f'c{i}', f'ToolScrew{i}', f'sc{i}', 'ToolScrewSel')
        b.set(f'sh{i}', 'ToolScrewSelHome', x + 500, y + 150); b.link(f'h{i}', f'ToolScrewHome{i}', f'sh{i}', 'ToolScrewSelHome')
        b.link(first[0], first[1], f'sc{i}', 'execute'); b.chain(f'sc{i}', f'sh{i}')
    b.comment('Pick the screw', [o['ref'] for o in b.ops if o['op'] == 'add_node'])
    b.run()


def place():
    e = empty('PlaceSelectedToolScrew')
    if not e:
        return print('PlaceSelectedToolScrew built')
    b = Batch(DOOR, 'PlaceSelectedToolScrew')
    b.get('home', 'ToolScrewSelHome', 0, 300)
    b.fn('parts', K + 'BreakTransform', 250, 300); b.link('home', 'ToolScrewSelHome', 'parts', 'InTransform')
    b.fn('back', K + 'Multiply_DoubleDouble', 250, 550, B=-1.0); b.link(e, 'Out', 'back', 'A')
    b.fn('outward', K + 'MakeVector', 500, 550, Y=0.0, Z=0.0); b.link('back', 'ReturnValue', 'outward', 'X')
    b.fn('where', K + 'Add_VectorVector', 750, 300); b.link('parts', 'Location', 'where', 'A'); b.link('outward', 'ReturnValue', 'where', 'B')
    b.fn('spin', K + 'MakeRotator', 500, 750); b.link(e, 'Turn', 'spin', 'Roll')
    b.fn('turned', K + 'ComposeRotators', 750, 550); b.link('parts', 'Rotation', 'turned', 'A'); b.link('spin', 'ReturnValue', 'turned', 'B')
    b.get('screw', 'ToolScrewSel', 750, 150)
    b.fn('move', SC + 'K2_SetRelativeLocationAndRotation', 1000, 0, bSweep='false', bTeleport='true')
    b.link('screw', 'ToolScrewSel', 'move', 'self'); b.link('where', 'ReturnValue', 'move', 'NewLocation'); b.link('turned', 'ReturnValue', 'move', 'NewRotation')
    b.link(e, 'then', 'move', 'execute')
    b.comment('Out of the plate and turned', [o['ref'] for o in b.ops if o['op'] == 'add_node'])
    b.run()


def home():
    e = empty('HomeToolScrews')
    if not e:
        return print('HomeToolScrews built')
    b = Batch(DOOR, 'HomeToolScrews')
    b.fn('stop', KS + 'K2_ClearTimer', 250, 0, FunctionName='TickToolScrewDrop')
    b.get('kept', 'bToolScrewHomes', 250, 250)
    b.node('once', 'branch', 550, 0); b.link('kept', 'bToolScrewHomes', 'once', 'Condition')
    b.chain(e, 'stop', 'once')
    prev = ('once', 'else')
    for i in range(4):
        x = 850 + i * 300
        b.get(f'c{i}', f'ToolScrew{i}', x, 450)
        b.fn(f'r{i}', SC + 'GetRelativeTransform', x, 300); b.link(f'c{i}', f'ToolScrew{i}', f'r{i}', 'self')
        b.set(f'k{i}', f'ToolScrewHome{i}', x, 0); b.link(f'r{i}', 'ReturnValue', f'k{i}', f'ToolScrewHome{i}')
        b.link(prev[0], prev[1], f'k{i}', 'execute'); prev = (f'k{i}', 'then')
    b.set('keptnow', 'bToolScrewHomes', 2050, 0); b.pin('keptnow', 'bToolScrewHomes', 'true')
    b.link(prev[0], prev[1], 'keptnow', 'execute')
    prev = None
    for i in range(4):
        x = 2350 + i * 300
        b.get(f'g{i}', f'ToolScrewHome{i}', x, 300)
        b.fn(f'p{i}', SC + 'K2_SetRelativeTransform', x, 0, bSweep='false', bTeleport='true')
        b.link(f'c{i}', f'ToolScrew{i}', f'p{i}', 'self'); b.link(f'g{i}', f'ToolScrewHome{i}', f'p{i}', 'NewTransform')
        if prev:
            b.chain(prev, f'p{i}')
        prev = f'p{i}'
    b.link('keptnow', 'then', 'p0', 'execute'); b.link('once', 'then', 'p0', 'execute')
    b.comment('Keep the homes once', ['kept', 'once'] + [f'{k}{i}' for k in 'crk' for i in range(4)] + ['keptnow'])
    b.comment('Put every screw back', [f'{k}{i}' for k in 'gp' for i in range(4)])
    b.run()


def drop():
    e = empty('DropToolScrew')
    if not e:
        return print('DropToolScrew built')
    b = Batch(DOOR, 'DropToolScrew')
    b.fn('pick', ME + 'SelectToolScrew', 250, 0); b.link(e, 'I', 'pick', 'I')
    b.get('sel', 'ToolScrewSel', 250, 300)
    b.set('which', 'ToolDropScrew', 550, 0); b.link('sel', 'ToolScrewSel', 'which', 'ToolDropScrew')
    b.fn('from', SC + 'GetRelativeTransform', 550, 300); b.link('sel', 'ToolScrewSel', 'from', 'self')
    b.set('start', 'ToolDropFrom', 850, 0); b.link('from', 'ReturnValue', 'start', 'ToolDropFrom')
    b.set('zero', 'ToolDropTime', 1150, 0); b.pin('zero', 'ToolDropTime', '0.0')
    b.set('air', 'bToolDropLanded', 1450, 0); b.pin('air', 'bToolDropLanded', 'false')
    b.fn('go', KS + 'K2_SetTimer', 1750, 0, FunctionName='TickToolScrewDrop', Time='%.6f' % (1 / 60), bLooping='true')
    b.chain(e, 'pick', 'which', 'start', 'zero', 'air', 'go')
    b.comment('Let the screw go', [o['ref'] for o in b.ops if o['op'] == 'add_node'])
    b.run()


def tick():
    e = empty('TickToolScrewDrop')
    if not e:
        return print('TickToolScrewDrop built')
    b = Batch(DOOR, 'TickToolScrewDrop')
    f = lambda ref, fn, x, y, **p: b.fn(ref, K + fn, x, y, **p)  # noqa: E731
    # time, one 60/s timer step per call (game time)
    b.get('t0', 'ToolDropTime', 0, 400); f('tnext', 'Add_DoubleDouble', 250, 400, B='%.6f' % (1 / 60)); b.link('t0', 'ToolDropTime', 'tnext', 'A')
    b.set('tset', 'ToolDropTime', 250, 0); b.link('tnext', 'ReturnValue', 'tset', 'ToolDropTime')
    b.get('t', 'ToolDropTime', 0, 700)
    # where it popped free, and the floor in the door's frame
    b.get('from', 'ToolDropFrom', 0, 1000); f('fromparts', 'BreakTransform', 250, 1000); b.link('from', 'ToolDropFrom', 'fromparts', 'InTransform')
    f('fromxyz', 'BreakVector', 500, 1000); b.link('fromparts', 'Location', 'fromxyz', 'InVec')
    b.fn('actor', '/Script/Engine.Actor:K2_GetActorLocation', 250, 1300); f('actorxyz', 'BreakVector', 500, 1300); b.link('actor', 'ReturnValue', 'actorxyz', 'InVec')
    f('floor', 'Subtract_DoubleDouble', 750, 1300, A=REST); b.link('actorxyz', 'Z', 'floor', 'B')
    f('height', 'Subtract_DoubleDouble', 1000, 1150); b.link('fromxyz', 'Z', 'height', 'A'); b.link('floor', 'ReturnValue', 'height', 'B')
    f('t1sq', 'Multiply_DoubleDouble', 1250, 1150, B='%.8f' % (2 / G)); b.link('height', 'ReturnValue', 't1sq', 'A')
    f('t1', 'Sqrt', 1500, 1150); b.link('t1sq', 'ReturnValue', 't1', 'A')
    # z: the fall, then one bounce
    f('ta', 'FMin', 1750, 700); b.link('t', 'ToolDropTime', 'ta', 'A'); b.link('t1', 'ReturnValue', 'ta', 'B')
    f('ta2', 'Multiply_DoubleDouble', 2000, 700); b.link('ta', 'ReturnValue', 'ta2', 'A'); b.link('ta', 'ReturnValue', 'ta2', 'B')
    f('fall', 'Multiply_DoubleDouble', 2250, 700, B=G / 2); b.link('ta2', 'ReturnValue', 'fall', 'A')
    f('za', 'Subtract_DoubleDouble', 2500, 700); b.link('fromxyz', 'Z', 'za', 'A'); b.link('fall', 'ReturnValue', 'za', 'B')
    f('since', 'Subtract_DoubleDouble', 1750, 900); b.link('t', 'ToolDropTime', 'since', 'A'); b.link('t1', 'ReturnValue', 'since', 'B')
    f('tb', 'FClamp', 2000, 900, Min=0.0, Max='%.6f' % TB); b.link('since', 'ReturnValue', 'tb', 'Value')
    f('tbg', 'Multiply_DoubleDouble', 2250, 900, B=G / 2); b.link('tb', 'ReturnValue', 'tbg', 'A')
    f('up', 'Subtract_DoubleDouble', 2500, 900, A=VB); b.link('tbg', 'ReturnValue', 'up', 'B')
    f('zb', 'Multiply_DoubleDouble', 2750, 900); b.link('tb', 'ReturnValue', 'zb', 'A'); b.link('up', 'ReturnValue', 'zb', 'B')
    f('z', 'Add_DoubleDouble', 3000, 800); b.link('za', 'ReturnValue', 'z', 'A'); b.link('zb', 'ReturnValue', 'z', 'B')
    # x: away from the door while airborne; spin about the vertical while airborne
    f('flight', 'Add_DoubleDouble', 1750, 1150, B='%.6f' % TB); b.link('t1', 'ReturnValue', 'flight', 'A')
    f('tx', 'FMin', 2000, 1150); b.link('t', 'ToolDropTime', 'tx', 'A'); b.link('flight', 'ReturnValue', 'tx', 'B')
    f('away', 'Multiply_DoubleDouble', 2250, 1150, B=VX); b.link('tx', 'ReturnValue', 'away', 'A')
    f('x', 'Subtract_DoubleDouble', 2500, 1150); b.link('fromxyz', 'X', 'x', 'A'); b.link('away', 'ReturnValue', 'x', 'B')
    f('where', 'MakeVector', 3250, 900); b.link('x', 'ReturnValue', 'where', 'X'); b.link('fromxyz', 'Y', 'where', 'Y'); b.link('z', 'ReturnValue', 'where', 'Z')
    f('yawdeg', 'Multiply_DoubleDouble', 2250, 1400, B=SPIN); b.link('tx', 'ReturnValue', 'yawdeg', 'A')
    f('yaw', 'MakeRotator', 2500, 1400); b.link('yawdeg', 'ReturnValue', 'yaw', 'Yaw')
    f('rot', 'ComposeRotators', 2750, 1400); b.link('fromparts', 'Rotation', 'rot', 'A'); b.link('yaw', 'ReturnValue', 'rot', 'B')
    b.get('screw', 'ToolDropScrew', 3250, 300)
    b.fn('move', SC + 'K2_SetRelativeLocationAndRotation', 3500, 0, bSweep='false', bTeleport='true')
    b.link('screw', 'ToolDropScrew', 'move', 'self'); b.link('where', 'ReturnValue', 'move', 'NewLocation'); b.link('rot', 'ReturnValue', 'move', 'NewRotation')
    # the tink where it lands, once
    f('down', 'GreaterEqual_DoubleDouble', 3500, 600); b.link('t', 'ToolDropTime', 'down', 'A'); b.link('t1', 'ReturnValue', 'down', 'B')
    b.get('landed', 'bToolDropLanded', 3500, 800); f('fresh', 'Not_PreBool', 3750, 800); b.link('landed', 'bToolDropLanded', 'fresh', 'A')
    f('hit', 'BooleanAND', 4000, 650); b.link('down', 'ReturnValue', 'hit', 'A'); b.link('fresh', 'ReturnValue', 'hit', 'B')
    b.node('land', 'branch', 3850, 0); b.link('hit', 'ReturnValue', 'land', 'Condition')
    b.set('mark', 'bToolDropLanded', 4150, -200); b.pin('mark', 'bToolDropLanded', 'true')
    b.fn('at', SC + 'K2_GetComponentLocation', 4150, 300); b.link('screw', 'ToolDropScrew', 'at', 'self')
    b.fn('tink', GS + 'PlaySoundAtLocation', 4450, -200, Sound=DROP_SOUND, VolumeMultiplier=0.9); b.link('at', 'ReturnValue', 'tink', 'Location')
    # stop once it rests
    f('restat', 'Add_DoubleDouble', 4450, 600, B=0.05); b.link('flight', 'ReturnValue', 'restat', 'A')
    f('rests', 'Greater_DoubleDouble', 4700, 600); b.link('t', 'ToolDropTime', 'rests', 'A'); b.link('restat', 'ReturnValue', 'rests', 'B')
    b.node('done', 'branch', 4800, 0); b.link('rests', 'ReturnValue', 'done', 'Condition')
    b.fn('stop', KS + 'K2_ClearTimer', 5100, 0, FunctionName='TickToolScrewDrop')
    b.chain(e, 'tset', 'move', 'land')
    b.link('land', 'then', 'mark', 'execute'); b.chain('mark', 'tink', 'done'); b.link('land', 'else', 'done', 'execute')
    b.link('done', 'then', 'stop', 'execute')
    b.comment('Fall and bounce', ['t0', 'tnext', 'tset', 't', 'from', 'fromparts', 'fromxyz', 'actor', 'actorxyz', 'floor', 'height', 't1sq', 't1',
                                   'ta', 'ta2', 'fall', 'za', 'since', 'tb', 'tbg', 'up', 'zb', 'z', 'flight', 'tx', 'away', 'x', 'where',
                                   'yawdeg', 'yaw', 'rot', 'screw', 'move'])
    b.comment('Tink where it lands', ['down', 'landed', 'fresh', 'hit', 'land', 'mark', 'at', 'tink'])
    b.comment('Stop once it rests', ['restat', 'rests', 'done', 'stop'])
    b.run()


def edges_of(graph):
    nodes, edges = inspect(DOOR, graph)
    by = {n['node_id']: n for n in nodes}
    return nodes, edges, by


def hook_begin():
    nodes, edges, by = edges_of('BeginDoorTool')
    if any(n['title'] == 'HomeToolScrews' for n in nodes):
        return print('BeginDoorTool hooked')
    idx = [n['node_id'] for n in nodes if n['title'] == 'Set ToolStepIndex']
    assert len(idx) == 1, idx
    nxt = [e for e in edges if e['from_node'] == idx[0] and e['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    b = Batch(DOOR, 'BeginDoorTool')
    b.cut(idx[0], 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.fn('homes', ME + 'HomeToolScrews', 3100, -250)
    b.link(idx[0], 'then', 'homes', 'execute'); b.link('homes', 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.run()


def hook_reset():
    nodes, edges, by = edges_of('CancelPendingRow')
    if any(n['title'] == 'HomeToolScrews' for n in nodes):
        return print('CancelPendingRow hooked')
    shows = [n['node_id'] for n in nodes if n['title'] == 'SetVisibility']
    last = [s for s in shows if not any(e['from_node'] == s and e['from_pin'] == 'then' for e in edges)]
    assert len(last) == 1, last
    b = Batch(DOOR, 'CancelPendingRow')
    b.fn('homes', ME + 'HomeToolScrews', 3200, 0); b.link(last[0], 'then', 'homes', 'execute')
    b.run()


def hook_refresh():
    nodes, edges, by = edges_of('RefreshDoorTool')
    if any(n['title'] == 'PlaceSelectedToolScrew' for n in nodes):
        return print('RefreshDoorTool hooked')
    b = Batch(DOOR, 'RefreshDoorTool')
    # the screws stay shown while the tool runs: a finished screw falls instead of vanishing
    gone = []
    for i in range(4):
        vis = [n['node_id'] for n in nodes if n['title'] == 'SetVisibility' and any(
            e['to_node'] == n['node_id'] and e['to_pin'] == 'self' and by[e['from_node']]['title'] == 'Get ToolScrew%d' % i for e in edges)]
        assert len(vis) == 1, (i, vis)
        orn = [e['from_node'] for e in edges if e['to_node'] == vis[0] and e['to_pin'] == 'bNewVisibility']
        assert len(orn) == 1 and by[orn[0]]['title'] == 'OR Boolean', orn
        less = [e['from_node'] for e in edges if e['to_node'] == orn[0] and by[e['from_node']]['title'].startswith('<=')]
        only = [x for x in less if all(e['to_node'] == orn[0] for e in edges if e['from_node'] == x)]
        gone += orn + only
        b.pin(vis[0], 'bNewVisibility', 'true')
    b.ops.insert(0, dict(op='remove', node_ids=gone))
    elbow = [n['node_id'] for n in nodes if n['title'] == 'Set ToolElbowTarget']
    assert len(elbow) == 1, elbow
    nxt = [e for e in edges if e['from_node'] == elbow[0] and e['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    nxt = (nxt[0]['to_node'], nxt[0]['to_pin'])
    x, y = 7100, -600
    b.cut(elbow[0], 'then', *nxt)
    b.get('index', 'ToolStepIndex', x, y + 300)
    b.fn('inplate', K + 'Less_IntInt', x + 250, y + 300, B=4); b.link('index', 'ToolStepIndex', 'inplate', 'A')
    b.node('screwing', 'branch', x + 250, y); b.link('inplate', 'ReturnValue', 'screwing', 'Condition')
    b.get('angle', 'ToolAngle', x, y + 500)
    b.fn('instroke', K + 'Percent_FloatFloat', x + 250, y + 500, B=90.0); b.link('angle', 'ToolAngle', 'instroke', 'A')
    b.fn('strokes', K + 'Subtract_DoubleDouble', x + 500, y + 450); b.link('angle', 'ToolAngle', 'strokes', 'A'); b.link('instroke', 'ReturnValue', 'strokes', 'B')
    b.fn('drivefrac', K + 'Multiply_DoubleDouble', x + 500, y + 650, B='%.8f' % (1 / 63)); b.link('instroke', 'ReturnValue', 'drivefrac', 'A')
    b.fn('driveclamp', K + 'FClamp', x + 750, y + 650, Min=0.0, Max=1.0); b.link('drivefrac', 'ReturnValue', 'driveclamp', 'Value')
    b.fn('drivedeg', K + 'Multiply_DoubleDouble', x + 1000, y + 650, B=90.0); b.link('driveclamp', 'ReturnValue', 'drivedeg', 'A')
    b.fn('turned', K + 'Add_DoubleDouble', x + 1250, y + 500); b.link('strokes', 'ReturnValue', 'turned', 'A'); b.link('drivedeg', 'ReturnValue', 'turned', 'B')
    b.fn('out', K + 'Multiply_DoubleDouble', x + 1500, y + 400, B='%.8f' % (OUT_CM / 720)); b.link('turned', 'ReturnValue', 'out', 'A')
    b.fn('loosen', K + 'Multiply_DoubleDouble', x + 1500, y + 600, B=-1.0); b.link('turned', 'ReturnValue', 'loosen', 'A')
    b.fn('pick', ME + 'SelectToolScrew', x + 500, y); b.link('index', 'ToolStepIndex', 'pick', 'I')
    b.fn('place', ME + 'PlaceSelectedToolScrew', x + 1750, y); b.link('out', 'ReturnValue', 'place', 'Out'); b.link('loosen', 'ReturnValue', 'place', 'Turn')
    b.link(elbow[0], 'then', 'screwing', 'execute')
    b.link('screwing', 'then', 'pick', 'execute'); b.chain('pick', 'place'); b.link('place', 'then', *nxt)
    b.link('screwing', 'else', *nxt)
    b.comment('Back the screw out', ['index', 'inplate', 'screwing', 'angle', 'instroke', 'strokes', 'drivefrac', 'driveclamp', 'drivedeg',
                                     'turned', 'out', 'loosen', 'pick', 'place'])
    b.run()


def hook_advance():
    nodes, edges, by = edges_of('AdvanceDoorTool')
    if any(n['title'] == 'DropToolScrew' for n in nodes):
        return print('AdvanceDoorTool hooked')
    # the screwdriver's step: Set ToolStepIndex (from int + int) -> ScrewTurn sound -> ScrewDrop sound -> "all four out?"
    step = [n['node_id'] for n in nodes if n['title'] == 'Set ToolStepIndex' and any(
        e['to_node'] == n['node_id'] and by[e['from_node']]['title'] == 'int + int' for e in edges)]
    assert len(step) == 1, step
    nxt = lambda node: [e for e in edges if e['from_node'] == node and e['from_pin'] == 'then']  # noqa: E731
    turn = nxt(step[0])
    assert len(turn) == 1 and by[turn[0]['to_node']]['title'] == 'PlaySoundAtLocation', turn
    sound2 = nxt(turn[0]['to_node'])
    assert len(sound2) == 1 and by[sound2[0]['to_node']]['title'] == 'PlaySoundAtLocation', sound2
    drop_sound = sound2[0]['to_node']
    before = [e for e in edges if e['to_node'] == drop_sound and e['to_pin'] == 'execute']
    after = nxt(drop_sound)
    assert len(before) == 1 and len(after) == 1, (before, after)
    x, y = where(drop_sound, 'AdvanceDoorTool')
    b = Batch(DOOR, 'AdvanceDoorTool')
    b.ops.append(dict(op='remove', node_ids=[drop_sound]))  # the tink now plays where the screw lands
    b.get('index', 'ToolStepIndex', x, y + 250)
    b.fn('which', K + 'Subtract_IntInt', x + 120, y + 400, B=1); b.link('index', 'ToolStepIndex', 'which', 'A')
    b.fn('drop', ME + 'DropToolScrew', x, y); b.link('which', 'ReturnValue', 'drop', 'I')
    b.link(before[0]['from_node'], 'then', 'drop', 'execute'); b.link('drop', 'then', after[0]['to_node'], after[0]['to_pin'])
    return b.run()


def where(node, graph):
    """A node's graph position (blueprint_measure_nodes pages)."""
    offset = 0
    while offset is not None:
        d = call('blueprint_measure_nodes', dict(path=DOOR, graph_name=graph, offset=offset, limit=50))['data']
        for n in d.get('nodes') or []:
            if n.get('node_id') == node:
                return int(n['rect'][0]), int(n['rect'][1])
        offset = (d.get('page') or {}).get('next_offset')
    raise AssertionError('node not measured: ' + node)


if __name__ == '__main__':
    assert not call('editor_get_state', {})['data']['pie_running'], 'PIE is running: wait'
    ensure_members()
    select()
    place()
    home()
    drop()
    tick()
    hook_begin()
    hook_reset()
    hook_refresh()
    hook_advance()
