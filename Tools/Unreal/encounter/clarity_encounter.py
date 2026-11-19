"""Battle clarity, BP_Encounter side (battle lane, 2026-11-17). Hayba only; idempotent; edits existing graphs in place.
  $env:HAYBA_AGENT_ID='battle'; python Tools/Unreal/encounter/clarity_encounter.py <phase>
Hold a lease on BP_Encounter first. Phases, in order: declare, bodies, enemy, keys, rules, cues. Each compiles and saves.
What it adds (rules and dispatchers are unchanged; damage only changes when the player braces):
  Wind-up      every enemy act that does something gets 1 s of warning: the garment holds its Telegraph clip, its
               wind-up sound plays (cloth, elastic or knot), bWindUp/WindUpStart drive the widget's closing ring.
               Acts that do nothing (Hang There) are skipped at once, so the enemy phase only shows real attacks.
  Brace        Space or gamepad A in the last 30% of the wind-up halves the Composure hit and shrugs off the status
               (IncomingDelta, ApplySelf). One press per attack; an early press spends it.
  Impact       every Composure hit freezes, shakes (CS_SandHit) and pulses; a brace clashes instead.
  Feedback     key hit and miss sounds, a fumble sound for a failed timed move, stun, hit and garment sounds, a
               hit-stop when a garment is won, victory and defeat stings.
  selftest     offline checks of the graph finders."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/level2']
from held_tool_graphs import Batch, inspect  # noqa: E402
import build_drive as b  # noqa: E402

ENC = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
GAR = '/Game/FoA/Gameplay/Encounter/BP_Garment'
MOVE = '/Game/FoA/Gameplay/Encounter/PDA_Move'
OPP = '/Game/FoA/Gameplay/Encounter/PDA_Opponent'
EC, GC, MC = b.cls(ENC), b.cls(GAR), b.cls(MOVE)
K, GS, SL = b.K, b.GS, b.SL
KIL = '/Script/Engine.KismetInputLibrary:'
MS = '/Game/FoA/Audio/MetaSounds/'
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C'


def snd(path):
    return MS + path + '.' + path.rsplit('/', 1)[1]


VARS = [('bWindUp', 'bool', 'false'), ('WindUpStart', 'float', '0'), ('WindUpTime', 'float', '1.0'),
        ('ImpactAt', 'float', '-10'), ('bBraced', 'bool', 'false'), ('bBraceSpent', 'bool', 'false'),
        ('BraceFrom', 'float', '0.7')]
FUNCS = {  # name: (inputs, outputs, pure)
    'IsIdleMove': ([('Move', 'object:' + MC)], [('bIdle', 'bool')], True),
    'IncomingDelta': ([('Move', 'object:' + MC)], [('Delta', 'int')], True),
    'WindUp': ([('Garment', 'object:' + GC)], [], False),
    'Brace': ([('Key', 'struct:/Script/InputCore.Key')], [], False),
    'CueBrace': ([], [], False),
    'CueKey': ([('bHit', 'bool')], [], False),
    'CueTiming': ([('Multiplier', 'int')], [], False),
}


# ---------------------------------------------------------------- graph search
def pin(node, name):
    return next((p.get('default_value') for p in node['pins'] if p['name'] == name), None)


def one(nodes, title, **pins):
    hits = [n['node_id'] for n in nodes if n['title'] == title and all(pin(n, k) == v for k, v in pins.items())]
    assert len(hits) == 1, (title, pins, len(hits))
    return hits[0]


def has(nodes, title):
    return any(n['title'] == title for n in nodes)


def exec_in(edges, node):
    return [e for e in edges if e['to_node'] == node and e['to_pin'] == 'execute']


def exec_out(edges, node, out='then'):
    return [e for e in edges if e['from_node'] == node and e['from_pin'] == out]


def src(edges, node, to_pin):
    e = [e for e in edges if e['to_node'] == node and e['to_pin'] == to_pin]
    assert len(e) == 1, (node, to_pin, e)
    return e[0]['from_node'], e[0]['from_pin']


class GR(b.G):
    """b.G for a function with outputs: keeps the result node and ends the chain there."""
    def __init__(self, path, name):
        Batch.__init__(self, path, name)
        ns, _ = inspect(path, name)
        self.e = next(n['node_id'] for n in ns if n['title'].replace(' ', '') == name)
        self.r = next(n['node_id'] for n in ns if n['title'] == 'Return Node')
        old = [n['node_id'] for n in ns if n['node_id'] not in (self.e, self.r)]
        if old:
            self.ops.append(dict(op='remove', node_ids=old))
        self.i, self.tail = 0, self.e

    def ret(self, **pins):
        self.chain(self.tail, self.r)
        for k, v in pins.items():
            self.put(self.r, k, v)
        return self.finish()


def set_on(g, var, cls_path, target, value):
    """Set a member of another Blueprint's instance (b.G.setv only sets its own)."""
    r = g.ref()
    g.set(r, var, 0, 0, b.cls(cls_path))
    g.put(r, 'self', target)
    g.put(r, var, value)
    g.chain(g.tail, r)
    g.tail = r


def now(g):
    return g.f(SL + 'GetGameTimeInSeconds')


def as_sound(g, obj):
    return g.cast(obj, '/Script/Engine.SoundBase', 'Sound Base')


# ---------------------------------------------------------------- phases
def declare():
    for name, kind, default in VARS:
        b.call('blueprint_add_variable', path=ENC, variable_name=name, variable_type=kind, default_value=default,
               category='Encounter|Clarity', update_existing=True)
    for name, (ins, outs, pure) in FUNCS.items():
        if not b.h.call('blueprint_inspect_graph', dict(path=ENC, graph_name=name, limit=1)).get('ok'):  # info lists are truncated
            b.call('blueprint_add_function', path=ENC, function_name=name, pure=pure,
                   inputs=[dict(name=n, type=t) for n, t in ins], outputs=[dict(name=n, type=t) for n, t in outs])
    nodes, _ = inspect(ENC, 'EventGraph')
    if not any(n['title'] == 'KeyTimeout' for n in nodes):
        b.call('blueprint_add_custom_event', path=ENC, event_name='KeyTimeout', x=0, y=9000)
    r = b.call('blueprint_compile', path=ENC)
    print('declare compile', r.get('error_count', r))


def bodies():
    g = GR(ENC, 'IsIdleMove')
    m = g.arg('Move')
    z = [g.math('EqualEqual_IntInt', A=g.getv(f, m, MOVE), B=0) for f in ('ComposureDelta', 'ResolveDelta', 'ProgressDelta')]
    s = g.math('EqualEqual_NameName', A=g.getv('StatusApplied', m, MOVE), B='None')
    w = g.math('Not_PreBool', A=g.getv('bSwapsTwin', m, MOVE))
    idle = g.math('BooleanAND', A=g.math('BooleanAND', A=z[0], B=z[1]),
                  B=g.math('BooleanAND', A=g.math('BooleanAND', A=z[2], B=s), B=w))
    g.ret(bIdle=idle)

    g = GR(ENC, 'IncomingDelta')
    d = g.getv('ComposureDelta', g.arg('Move'), MOVE)
    use = g.math('BooleanAND', A=g.getv('bBraced'), B=g.math('Less_IntInt', A=d, B=0))
    g.ret(Delta=g.math('SelectInt', A=g.math('Divide_IntInt', A=d, B=2), B=d, bPickA=use))

    g = b.G(ENC, 'WindUp')
    gar = g.arg('Garment')
    g.setv('bBraced', False)
    g.setv('bBraceSpent', False)
    g.setv('WindUpStart', now(g))
    g.setv('bWindUp', True)
    set_on(g, 'State', GAR, gar, 'Telegraph')
    g.do(GC + ':SyncStateClip', self=gar)
    gid = g.getv('GarmentId', g.getv('Data', gar, GAR), OPP)
    tie = g.math('EqualEqual_NameName', A=gid, B='Tie')
    stretchy = g.math('BooleanOR', A=g.math('EqualEqual_NameName', A=gid, B='Socks'),
                      B=g.math('EqualEqual_NameName', A=gid, B='Trousers'))
    pick = g.math('SelectObject', A=snd('Battle/S_Battle_TelegraphKnot'), B=snd('Battle/S_Battle_TelegraphCloth'), bSelectA=tie)
    pick = g.math('SelectObject', A=snd('Battle/S_Battle_TelegraphElastic'), B=pick, bSelectA=stretchy)
    sound = as_sound(g, pick)
    g.do(GS + 'PlaySoundAtLocation', Sound=sound, Location=g.f(b.A + 'K2_GetActorLocation', self=gar))
    # A focused card would take Space as its own click: keyboard focus goes to the game for the brace.
    g.do('/Script/UMG.WidgetBlueprintLibrary:SetFocusToGameViewport')
    r = g.ref()
    g.node(r, 'call_dispatcher', 0, 0, dispatcher_name='OnChanged')
    g.chain(g.tail, r)
    g.tail = r
    g.finish()

    g = b.G(ENC, 'Brace')
    k = g.arg('Key')
    # Key pin defaults take the bare key name; '(KeyName="...")' is stored as AnyKey (read back 23:15).
    key = g.math('BooleanOR', A=g.f(KIL + 'EqualEqual_KeyKey', A=k, B='SpaceBar'),
                 B=g.f(KIL + 'EqualEqual_KeyKey', A=k, B='Gamepad_FaceButton_Bottom'))
    gate = g.branch(g.math('BooleanAND', A=key, B=g.math('Not_PreBool', A=g.getv('bBraceSpent'))))
    g.side(gate)
    g.setv('bBraceSpent', True)
    t = g.math('Divide_DoubleDouble', A=g.math('Subtract_DoubleDouble', A=now(g), B=g.getv('WindUpStart')),
               B=g.math('FMax', A=g.getv('WindUpTime'), B=0.05))
    g.setv('bBraced', g.math('GreaterEqual_DoubleDouble', A=t, B=g.getv('BraceFrom')))
    g.finish()

    g = b.G(ENC, 'CueBrace')
    g.do(GS + 'PlaySound2D', Sound=snd('Battle/S_Battle_SwordClash'), bIsUISound=False)
    pawn = g.f(GS + 'GetPlayerPawn', PlayerIndex=0)
    g.do(SANDFX + ':SpawnSandBurst', Location=g.f(b.A + 'K2_GetActorLocation', self=pawn), Scale=0.6)
    g.finish()

    g = b.G(ENC, 'CueKey')
    hit = g.arg('bHit')
    sound = as_sound(g, g.math('SelectObject', A=snd('Battle/S_Battle_Button'), B=snd('Foley/S_Foley_ClothMove'), bSelectA=hit))
    g.do(GS + 'PlaySound2D', Sound=sound, PitchMultiplier=g.math('SelectFloat', A=1.0, B=0.7, bPickA=hit), bIsUISound=False)
    g.finish()

    g = b.G(ENC, 'CueTiming')
    gate = g.branch(g.math('EqualEqual_IntInt', A=g.arg('Multiplier'), B=0))
    g.side(gate)
    g.do(GS + 'PlaySound2D', Sound=snd('Dream/S_Dream_TapeStop'), bIsUISound=False)
    g.own('DreamPulse', Mode=3, Seconds=0.3)
    g.finish()


def enemy():
    """EventGraph: wind-up before each real act, skip idle acts, brace or full impact after it."""
    nodes, edges = inspect(ENC, 'EventGraph')
    if has(nodes, 'WindUp'):
        print('enemy: already spliced')
        return
    act = one(nodes, 'EnemyAct')
    (stun, out), = [(e['from_node'], e['from_pin']) for e in exec_in(edges, act)]
    assert out == 'else', out
    item = src(edges, act, 'Garment')
    g = Batch(ENC, 'EventGraph')
    x, y = 2200, 6000
    g.get('cl_intent', 'Intent', x, y + 300, GC)
    g.link(*item, 'cl_intent', 'self')
    g.fn('cl_idle', EC + ':IsIdleMove', x + 250, y + 300)
    g.link('cl_intent', 'Intent', 'cl_idle', 'Move')
    g.node('cl_gate', 'branch', x + 500, y)
    g.link('cl_idle', 'bIdle', 'cl_gate', 'Condition')
    g.fn('cl_skip', EC + ':EnemyStep', x + 800, y - 200)
    g.fn('cl_wind', EC + ':WindUp', x + 800, y + 100)
    g.link(*item, 'cl_wind', 'Garment')
    g.get('cl_time', 'WindUpTime', x + 900, y + 350)
    g.fn('cl_delay', SL + 'Delay', x + 1100, y + 100)
    g.link('cl_time', 'WindUpTime', 'cl_delay', 'Duration')
    g.get('cl_active', 'bActive', x + 1300, y + 350)
    g.node('cl_alive', 'branch', x + 1400, y + 100)
    g.link('cl_active', 'bActive', 'cl_alive', 'Condition')
    g.set('cl_off', 'bWindUp', x + 1700, y + 100)
    g.pin('cl_off', 'bWindUp', 'false')
    g.fn('cl_now', SL + 'GetGameTimeInSeconds', x + 1800, y + 350)
    g.set('cl_hit', 'ImpactAt', x + 2000, y + 100)
    g.link('cl_now', 'ReturnValue', 'cl_hit', 'ImpactAt')
    g.cut(stun, out, act, 'execute')
    g.link(stun, out, 'cl_gate', 'execute')
    g.link('cl_gate', 'then', 'cl_skip', 'execute')
    g.link('cl_gate', 'else', 'cl_wind', 'execute')
    g.chain('cl_wind', 'cl_delay', 'cl_alive', 'cl_off', 'cl_hit')
    g.link('cl_hit', 'then', act, 'execute')
    g.set('cl_off_ended', 'bWindUp', x + 1700, y + 300)  # the fight ended during the wind-up: no stale brace routing
    g.pin('cl_off_ended', 'bWindUp', 'false')
    g.link('cl_alive', 'else', 'cl_off_ended', 'execute')
    g.comment('Wind-up', ['cl_intent', 'cl_idle', 'cl_gate', 'cl_skip', 'cl_wind', 'cl_time', 'cl_delay', 'cl_active',
                          'cl_alive', 'cl_off', 'cl_now', 'cl_hit', 'cl_off_ended'])
    # Impact: every Composure hit shakes (was -8 and worse); a brace clashes instead.
    big = one(nodes, 'integer <= integer', B='-8')
    g.pin(big, 'B', -1)
    cond = [e['to_node'] for e in edges if e['from_node'] == big and e['to_pin'] == 'Condition']
    assert len(cond) == 1, cond
    (changed, cpin), = [(e['from_node'], e['from_pin']) for e in exec_in(edges, cond[0])]
    delay = [e['to_node'] for e in exec_out(edges, cond[0], 'else')]
    assert len(delay) == 1, delay
    g.get('cl_braced', 'bBraced', x + 2400, y + 900)
    g.node('cl_brace_gate', 'branch', x + 2600, y + 700)
    g.link('cl_braced', 'bBraced', 'cl_brace_gate', 'Condition')
    g.fn('cl_clash', EC + ':CueBrace', x + 2900, y + 600)
    g.cut(changed, cpin, cond[0], 'execute')
    g.link(changed, cpin, 'cl_brace_gate', 'execute')
    g.link('cl_brace_gate', 'then', 'cl_clash', 'execute')
    g.link('cl_clash', 'then', delay[0], 'execute')
    g.link('cl_brace_gate', 'else', cond[0], 'execute')
    g.comment('Brace or impact', ['cl_braced', 'cl_brace_gate', 'cl_clash'])
    # Hit-stop: a real camera shake after the freeze (CS_SandHit, the sand lane's hit shake).
    unfreeze = one(nodes, 'SetGlobalTimeDilation', TimeDilation='1.0')
    (bump, bpin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, unfreeze)]
    g.fn('cl_cam', GS + 'GetPlayerCameraManager', x + 3200, y + 1500)
    g.pin('cl_cam', 'PlayerIndex', 0)
    g.fn('cl_shake', '/Script/Engine.PlayerCameraManager:StartCameraShake', x + 3500, y + 1300)
    g.link('cl_cam', 'ReturnValue', 'cl_shake', 'self')
    g.pin('cl_shake', 'ShakeClass', '/Game/FoA/VFX/CS_SandHit.CS_SandHit_C')
    g.pin('cl_shake', 'Scale', 1.0)
    g.cut(unfreeze, 'then', bump, bpin)
    g.link(unfreeze, 'then', 'cl_shake', 'execute')
    g.link('cl_shake', 'then', bump, bpin)
    g.comment('Camera shake', ['cl_cam', 'cl_shake'])
    g.run()


def keys():
    """HandleKey routes Space to Brace during a wind-up; key hit/miss sounds; a timeout is a miss; fumble sound."""
    nodes, edges = inspect(ENC, 'HandleKey')
    if not has(nodes, 'Brace'):
        entry = one(nodes, 'HandleKey')
        (first, fpin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, entry)]
        g = Batch(ENC, 'HandleKey')
        g.get('cl_wind', 'bWindUp', 200, -400)
        g.node('cl_gate', 'branch', 400, -400)
        g.link('cl_wind', 'bWindUp', 'cl_gate', 'Condition')
        g.fn('cl_brace', EC + ':Brace', 700, -500)
        g.link(entry, 'Key', 'cl_brace', 'Key')
        g.cut(entry, 'then', first, fpin)
        g.link(entry, 'then', 'cl_gate', 'execute')
        g.link('cl_gate', 'then', 'cl_brace', 'execute')
        g.link('cl_gate', 'else', first, fpin)
        g.comment('Brace during a wind-up', ['cl_wind', 'cl_gate', 'cl_brace'])
        g.run()
        nodes, edges = inspect(ENC, 'HandleKey')
    # Target keys: Q back, E and Tab forward. Left and Right were also card navigation, so Slate took them first.
    by = nodes_by(nodes)
    keyeq = [n['node_id'] for n in nodes if n['title'] == 'Equal (Key)']
    back = [k for k in keyeq for e in edges if e['from_node'] == k and by[e['to_node']]['title'] == 'SelectInt'
            and pin(by[e['to_node']], 'A') == '-1']
    fwd = sorted((e['to_pin'], k) for k in keyeq for e in edges if e['from_node'] == k and by[e['to_node']]['title'] == 'OR Boolean')
    assert len(back) == 1 and len(fwd) == 2, (back, fwd)
    g = Batch(ENC, 'HandleKey')
    for node, name in ((back[0], 'Q'), (fwd[0][1], 'E'), (fwd[1][1], 'Tab')):
        g.pin(node, 'B', name)
    g.run()
    nodes, edges = inspect(ENC, 'SubmitKey')
    if not has(nodes, 'CueKey'):
        hits = one(nodes, 'Set InputHits')
        (adv, apin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, hits)]
        match = one(nodes, 'Equal (Key)')
        g = Batch(ENC, 'SubmitKey')
        g.fn('cl_cue', EC + ':CueKey', 900, -300)
        g.link(match, 'ReturnValue', 'cl_cue', 'bHit')
        g.cut(hits, 'then', adv, apin)
        g.link(hits, 'then', 'cl_cue', 'execute')
        g.link('cl_cue', 'then', adv, apin)
        g.comment('Key sound', ['cl_cue'])
        g.run()
    nodes, edges = inspect(ENC, 'EventGraph')
    timeout = one(nodes, 'KeyTimeout')
    if not exec_out(edges, timeout):
        g = Batch(ENC, 'EventGraph')
        g.fn('cl_miss', EC + ':CueKey', 300, 9000)
        g.pin('cl_miss', 'bHit', 'false')
        g.fn('cl_adv', EC + ':AdvancePrompt', 600, 9000)
        g.chain(timeout, 'cl_miss', 'cl_adv')
        timer = one(nodes, 'Set Timer by Function Name', FunctionName='AdvancePrompt')
        g.pin(timer, 'FunctionName', 'KeyTimeout')
        g.comment('Key timeout', [timeout, 'cl_miss', 'cl_adv'])
        g.run()
        nodes, edges = inspect(ENC, 'EventGraph')
    end_nodes, _ = inspect(ENC, 'EndEncounter')
    stale = [n['node_id'] for n in end_nodes if n['title'] == 'Clear Timer by Function Name'
             and pin(n, 'FunctionName') == 'AdvancePrompt']
    if stale:  # the prompt timer now calls KeyTimeout; EndEncounter must clear that name
        g = Batch(ENC, 'EndEncounter')
        g.pin(stale[0], 'FunctionName', 'KeyTimeout')
        g.run()
    if not has(nodes, 'CueTiming'):
        apply = one(nodes, 'ApplyPlayerMove', Multiplier='0')
        (gate, gpin), = [(e['from_node'], e['from_pin']) for e in exec_in(edges, apply)]
        mult = src(edges, apply, 'Multiplier')
        g = Batch(ENC, 'EventGraph')
        g.fn('cl_timing', EC + ':CueTiming', 1500, 3600)
        g.link(*mult, 'cl_timing', 'Multiplier')
        g.cut(gate, gpin, apply, 'execute')
        g.link(gate, gpin, 'cl_timing', 'execute')
        g.link('cl_timing', 'then', apply, 'execute')
        g.comment('Fumble sound', ['cl_timing'])
        g.run()


def rules():
    """The brace halves Composure hits (IncomingDelta) and shrugs off the status in ApplySelf; EnemyAct reports it."""
    nodes, edges = inspect(ENC, 'ApplySelf')
    if not has(nodes, 'IncomingDelta'):
        entry = one(nodes, 'ApplySelf')
        comp = one(nodes, 'Get ComposureDelta')
        (add, apin), = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == comp]
        neq = one(nodes, 'Not Equal (Name)')
        (gate, gpin), = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == neq]
        g = Batch(ENC, 'ApplySelf')
        g.fn('cl_in', EC + ':IncomingDelta', 400, 900)
        g.link(entry, 'Move', 'cl_in', 'Move')
        g.cut(comp, 'ComposureDelta', add, apin)
        g.link('cl_in', 'Delta', add, apin)
        g.get('cl_braced', 'bBraced', 900, 1300)
        g.fn('cl_not', K + 'Not_PreBool', 1100, 1300)
        g.link('cl_braced', 'bBraced', 'cl_not', 'A')
        g.fn('cl_and', K + 'BooleanAND', 1300, 1200)
        g.link(neq, 'ReturnValue', 'cl_and', 'A')
        g.link('cl_not', 'ReturnValue', 'cl_and', 'B')
        g.cut(neq, 'ReturnValue', gate, gpin)
        g.link('cl_and', 'ReturnValue', gate, gpin)
        g.ops.append(dict(op='remove', node_ids=[comp]))
        g.comment('Brace', ['cl_in', 'cl_braced', 'cl_not', 'cl_and'])
        g.run()
    nodes, edges = inspect(ENC, 'EnemyAct')
    if not has(nodes, 'IncomingDelta'):
        comp = one(nodes, 'Get ComposureDelta')
        intent = src(edges, comp, 'self')
        outs = [(e['to_node'], e['to_pin']) for e in edges if e['from_node'] == comp]
        assert len(outs) == 3, outs
        g = Batch(ENC, 'EnemyAct')
        g.fn('cl_in', EC + ':IncomingDelta', 600, 900)
        g.link(*intent, 'cl_in', 'Move')
        for node, p in outs:
            g.cut(comp, 'ComposureDelta', node, p)
            g.link('cl_in', 'Delta', node, p)
        g.ops.append(dict(op='remove', node_ids=[comp]))
        g.comment('Braced damage', ['cl_in'])
        g.run()


def cues():
    """Sounds that were missing: player and garment hits, stun, garment won hit-stop, victory and defeat."""
    nodes, edges = inspect(ENC, 'CueDamage')
    g = Batch(ENC, 'CueDamage')
    first = [n['node_id'] for n in nodes if n['title'] == 'PlaySound2D' and exec_in(edges, n['node_id'])
             and nodes_by(nodes)[exec_in(edges, n['node_id'])[0]['from_node']]['title'] == 'Branch']
    assert len(first) == 1, first
    g.pin(first[0], 'Sound', snd('Battle/S_Battle_PlayerHit'))
    hit = one(nodes, 'PlaySoundAtLocation')
    g.pin(hit, 'Sound', snd('Battle/S_Battle_GarmentHit'))
    if not exec_out(edges, hit):  # a pip filling clicks like a button going through its hole (coordinator, 11-18)
        g.fn('cl_click', GS + 'PlaySound2D', 1700, 300)
        g.pin('cl_click', 'Sound', snd('Battle/S_Battle_Button'))
        g.link(hit, 'then', 'cl_click', 'execute')
        g.comment('Pip click', ['cl_click'])
    g.run()
    nodes, edges = inspect(ENC, 'ApplyPlayerMove')
    if not has(nodes, 'PlaySoundAtLocation'):
        stunned = one(nodes, 'Set State', State='Stunned')
        (nxt, npin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, stunned)]
        target = src(edges, stunned, 'self')
        remaining = one(nodes, 'Set Remaining')
        (after, apin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, remaining)]
        g = Batch(ENC, 'ApplyPlayerMove')
        g.fn('cl_at', b.A + 'K2_GetActorLocation', 2600, 900)
        g.link(*target, 'cl_at', 'self')
        g.fn('cl_stun', GS + 'PlaySoundAtLocation', 2900, 700)
        g.pin('cl_stun', 'Sound', snd('Battle/S_Battle_Stun'))
        g.link('cl_at', 'ReturnValue', 'cl_stun', 'Location')
        g.cut(stunned, 'then', nxt, npin)
        g.link(stunned, 'then', 'cl_stun', 'execute')
        g.link('cl_stun', 'then', nxt, npin)
        g.fn('cl_won', EC + ':Shake', 3600, 700)
        g.cut(remaining, 'then', after, apin)
        g.link(remaining, 'then', 'cl_won', 'execute')
        g.link('cl_won', 'then', after, apin)
        g.comment('Stun sound', ['cl_at', 'cl_stun'])
        g.comment('Garment won hit-stop', ['cl_won'])
        g.run()
    nodes, edges = inspect(ENC, 'CueWon')
    if sum(n['title'] == 'PlaySound2D' for n in nodes) < 2:
        entry = one(nodes, 'CueWon')
        (nxt, npin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, entry)]
        g = Batch(ENC, 'CueWon')
        g.fn('cl_sting', GS + 'PlaySound2D', 200, -300)
        g.pin('cl_sting', 'Sound', snd('Battle/S_Battle_Victory'))
        g.cut(entry, 'then', nxt, npin)
        g.link(entry, 'then', 'cl_sting', 'execute')
        g.link('cl_sting', 'then', nxt, npin)
        g.comment('Victory sting', ['cl_sting'])
        g.run()
    nodes, edges = inspect(ENC, 'EventGraph')
    lost = one(nodes, 'Call On Encounter Lost')
    (nxt, npin), = [(e['to_node'], e['to_pin']) for e in exec_out(edges, lost)]
    if nodes_by(nodes)[nxt]['title'] != 'PlaySound2D':
        g = Batch(ENC, 'EventGraph')
        g.fn('cl_lost', GS + 'PlaySound2D', 3000, 9800)
        g.pin('cl_lost', 'Sound', snd('Battle/S_Battle_Defeat'))
        g.cut(lost, 'then', nxt, npin)
        g.link(lost, 'then', 'cl_lost', 'execute')
        g.link('cl_lost', 'then', nxt, npin)
        g.comment('Defeat sting', ['cl_lost'])
        g.run()


def nodes_by(nodes):
    return {n['node_id']: n for n in nodes}


def selftest():
    nodes = [dict(node_id='a', title='Set Timer by Function Name', pins=[dict(name='FunctionName', default_value='AdvancePrompt')]),
             dict(node_id='b', title='Set Timer by Function Name', pins=[dict(name='FunctionName', default_value='TickWindow')])]
    assert one(nodes, 'Set Timer by Function Name', FunctionName='AdvancePrompt') == 'a'
    edges = [dict(from_node='a', from_pin='then', to_node='b', to_pin='execute')]
    assert exec_in(edges, 'b')[0]['from_node'] == 'a' and exec_out(edges, 'a')[0]['to_node'] == 'b'
    assert snd('Battle/S_Battle_Stun') == '/Game/FoA/Audio/MetaSounds/Battle/S_Battle_Stun.S_Battle_Stun'
    try:
        one(nodes, 'Set Timer by Function Name')
        raise SystemExit('one() must refuse two matches')
    except AssertionError:
        pass
    print('selftest ok')


if __name__ == '__main__':
    {'declare': declare, 'bodies': bodies, 'enemy': enemy, 'keys': keys, 'rules': rules, 'cues': cues,
     'selftest': selftest}[sys.argv[1]]()
