"""Story lane, "It won't come" (the user's pick A, 2026-11-10): the vase-to-battle wiring around the rebuilt LS_BattleIntro
(build_wont_come.py). Hayba batches, compiled and saved; idempotent where marked.
  director  OnClothingCameraReady, final reach: ClothingBossFormed at once (was RoomTakeover.BreakVaseThenBoss, the sand
            figure, and ClothingBossFormed 3.8 s later). ShirtTaken -> T8 -> StartShirtFight -> PlayBattleIntro as before.
            PlayBattleIntro: the same cut either way, one cue (BI_FX_Vase at 0.8 s: RoomTakeover.BreakVaseOnly) and
            BattleIntroDone at 3.2 s. BattleIntroDone: the vase breaks now if a skip came first; the sequence is stopped
            while it still holds the battle framing, the encounter starts on that same picture (no fade, no
            HandoffFadeUp: nothing is black any more), then the lines: "Get dressed." 2.0 s, "Okay. Shirt first."
            2.9 s, or on a replay (bBattleIntroShort) "Again. Shirt first." 2.4 s.
  encounter IntroStep's Delay 1.5 -> 0.6 s: the garments come in one after another, not as five entrance cards.
  garment   PlaceForRise, first in the Rise event: socks start at the open commode drawer, the pants at the fallen
            wardrobe, the tie at the chair back; Rise's MoveComponentTo then carries them to their places. The shirt
            (no source) still rises out of the mound it sank into.
  python Tools/Unreal/flow/patch_wont_come.py [director] [encounter] [garment]"""
import importlib
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player', 'P:/FoA/Tools/Unreal/flow']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402
import patch_battle_intro as PBI  # noqa: E402

P, C = PBI.P, PBI.C
E = '/Game/FoA/Gameplay/Encounter/BP_Encounter'
G = '/Game/FoA/Gameplay/Encounter/BP_Garment'
G_C = G + '.BP_Garment_C'
OPP_C = '/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C'
ROOM_C = '/Game/FoA/Gameplay/Ambient/BP_RoomTakeover.BP_RoomTakeover_C'
K, KS, GS, SC = PBI.K, PBI.KS, PBI.GS, '/Script/Engine.SceneComponent:'
CUE = 3.2
LINES = [('BI_N01', 2.0), ('BI_L05', 2.9)]
REPLAY = [('BI_L06', 2.4)]
# shortcut: world positions in L_Tutorial_Bedroom (Commode, Wardrobe fallen across the door, Chair); move with the furniture.
SOURCES = {'Socks': (-150.0, 232.0, 70.0), 'Trousers': (285.0, 120.0, 60.0), 'Tie': (-285.0, 172.0, 95.0)}


def norm(t):
    return t.split('\n')[0].replace(' ', '')


def wipe(graph):
    ns, es = inspect(P, graph)
    e = find(ns, graph)
    rest = [n['node_id'] for n in ns if n['node_id'] != e]
    if rest:
        b = Batch(P, graph)
        b.ops.append(dict(op='remove', node_ids=rest))
        b.run()


def room_ready():
    ns, es = inspect(P, 'OnClothingCameraReady')
    t = {n['node_id']: norm(n['title']) for n in ns}
    if 'ClothingBossFormed' in t.values():
        return 'kept'
    brk = next(i for i, x in t.items() if x == 'BreakVaseThenBoss')
    room = next(x['from_node'] for x in es if x['to_node'] == brk and x['from_pin'] == 'then')
    which = next(x for x in es if x['to_node'] == room and x['to_pin'] == 'execute')
    timer = next(x['to_node'] for x in es if x['from_node'] == brk and x['from_pin'] == 'then')
    assert t[room] == 'GetActorOfClass' and t[timer] == 'SetTimerbyFunctionName', (t[room], t[timer])
    b = Batch(P, 'OnClothingCameraReady')
    b.ops.append(dict(op='remove', node_ids=[room, brk, timer]))
    b.fn('formed', C + ':ClothingBossFormed', 1200, 0)
    b.link(which['from_node'], which['from_pin'], 'formed', 'execute')
    b.comment('The shirt is taken: into T8', ['formed'])
    b.run()
    return 'final reach -> ClothingBossFormed'


def vase_cue():
    ns, e = PBI.ensure('BI_FX_Vase')
    if len(ns) > 1:
        return 'kept'
    b = Batch(P, 'BI_FX_Vase')
    b.fn('room', GS + 'GetActorOfClass', 250, 0, ActorClass=ROOM_C)
    b.fn('ok', KS + 'IsValid', 250, 250)
    b.link('room', 'ReturnValue', 'ok', 'Object')
    b.node('has', 'branch', 500, 0)
    b.link('ok', 'ReturnValue', 'has', 'Condition')
    b.fn('break', ROOM_C + ':BreakVaseOnly', 750, 0)
    b.link('room', 'ReturnValue', 'break', 'self')
    b.link(e, 'then', 'room', 'execute')
    b.chain('room', 'has')
    b.link('has', 'then', 'break', 'execute')
    b.comment('The vase goes', ['room', 'ok', 'has', 'break'])
    b.run()
    return 'built'


def play():
    wipe('PlayBattleIntro')  # rebuilt every run: the timer list is the whole graph
    PBI.FULL, PBI.SHORT, PBI.FULL_S, PBI.SHORT_S = [('BI_FX_Vase', 0.8, 'vase', ())], [('BI_FX_Vase', 0.8, 'vase', ())], CUE, CUE
    return PBI.play()


def done():
    wipe('BattleIntroDone')
    ns, e = PBI.ensure('BattleIntroDone')
    b = Batch(P, 'BattleIntroDone')
    b.get('on', 'bBattleIntroPlaying', 0, 300)
    b.node('once', 'branch', 250, 0)
    b.link('on', 'bBattleIntroPlaying', 'once', 'Condition')
    b.set('off', 'bBattleIntroPlaying', 500, 0)
    b.pin('off', 'bBattleIntroPlaying', 'false')
    b.link(e, 'then', 'once', 'execute')
    b.link('once', 'then', 'off', 'execute')
    # a skip before 0.8 s: the vase still goes
    b.fn('pending', KS + 'K2_IsTimerActive', 750, 300, FunctionName='BI_FX_Vase')
    b.node('late', 'branch', 750, 0)
    b.link('pending', 'ReturnValue', 'late', 'Condition')
    b.fn('vase', C + ':BI_FX_Vase', 1000, -150)
    prev = None
    names = ['BI_FX_Vase', 'BattleIntroDone'] + [n for n, _ in LINES + REPLAY]
    for i, fn in enumerate(names):
        b.fn('c%d' % i, KS + 'K2_ClearTimer', 1250 + 200 * i, 0, FunctionName=fn)
        if prev:
            b.chain(prev, 'c%d' % i)
        prev = 'c%d' % i
    b.chain('off', 'late')
    b.link('late', 'then', 'vase', 'execute')
    b.link('vase', 'then', 'c0', 'execute')
    b.link('late', 'else', 'c0', 'execute')
    x = 1250 + 200 * len(names)
    b.get('sp', 'BattleIntroPlayer', x, 300)
    b.fn('valid', KS + 'IsValid', x + 250, 300)
    b.link('sp', 'BattleIntroPlayer', 'valid', 'Object')
    b.node('playing', 'branch', x, 0)
    b.link('valid', 'ReturnValue', 'playing', 'Condition')
    b.fn('stop', PBI.MSP + 'Stop', x + 250, -150)
    b.link('sp', 'BattleIntroPlayer', 'stop', 'self')
    b.chain(prev, 'playing')
    b.link('playing', 'then', 'stop', 'execute')
    x += 500
    b.fn('fe', GS + 'GetActorOfClass', x, 300, ActorClass=PBI.FRONT)
    b.fn('fev', KS + 'IsValid', x + 250, 300)
    b.link('fe', 'ReturnValue', 'fev', 'Object')
    b.node('feok', 'branch', x, 0)
    b.link('fev', 'ReturnValue', 'feok', 'Condition')
    b.link('stop', 'then', 'fe', 'execute')
    b.link('playing', 'else', 'fe', 'execute')
    b.chain('fe', 'feok')
    b.fn('hide', PBI.FRONT + ':HideCinematicSubtitle', x + 250, -150)
    b.link('fe', 'ReturnValue', 'hide', 'self')
    b.link('feok', 'then', 'hide', 'execute')
    b.fn('pawn', GS + 'GetPlayerCharacter', x + 500, 300, PlayerIndex=0)
    b.get('cm', 'CharacterMovement', x + 750, 300, '/Script/Engine.Character')
    b.link('pawn', 'ReturnValue', 'cm', 'self')
    b.fn('walk', '/Script/Engine.CharacterMovementComponent:SetMovementMode', x + 750, 0, NewMovementMode='MOVE_Walking')
    b.link('cm', 'CharacterMovement', 'walk', 'self')
    b.link('hide', 'then', 'walk', 'execute')
    b.link('feok', 'else', 'walk', 'execute')
    b.fn('col', '/Script/Engine.Actor:SetActorEnableCollision', x + 1000, 0, bNewActorEnableCollision='true')
    b.link('pawn', 'ReturnValue', 'col', 'self')
    b.fn('cin', C + ':PlayerCinematic', x + 1250, 0, Enable='false')
    b.fn('hud', C + ':SetStoryHUDHidden', x + 1500, 0, Hidden='false')
    b.fn('fight', C + ':StartShirtEncounter', x + 1750, 0)
    b.fn('pcm', GS + 'GetPlayerCameraManager', x + 2000, 300, PlayerIndex=0)
    b.fn('cut', '/Script/Engine.PlayerCameraManager:SetGameCameraCutThisFrame', x + 2000, 0)
    b.link('pcm', 'ReturnValue', 'cut', 'self')
    b.chain('walk', 'col', 'cin', 'hud', 'fight', 'cut')
    b.get('short', 'bBattleIntroShort', x + 2250, 300)
    b.node('replay', 'branch', x + 2250, 0)
    b.link('short', 'bBattleIntroShort', 'replay', 'Condition')
    b.chain('cut', 'replay')
    for row, (pin, lines) in enumerate((('then', REPLAY), ('else', LINES))):
        prev = None
        for i, (fn, t) in enumerate(lines):
            ref = 'l%d_%d' % (row, i)
            b.fn(ref, KS + 'K2_SetTimer', x + 2500 + 250 * i, 300 * row, FunctionName=fn, Time=t, bLooping='false')
            b.link(prev or 'replay', 'then' if prev else pin, ref, 'execute')
            prev = ref
    b.comment('Into the fight on the same picture', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def director():
    for name, t in (('BattleIntroPlayer', 'object:/Script/LevelSequence.LevelSequencePlayer'),
                    ('bBattleIntroPlaying', 'bool'), ('bBattleIntroShort', 'bool')):
        r = h.call('blueprint_add_variable', dict(path=P, variable_name=name, variable_type=t, category='Story|Battle intro',
                                                  update_existing=True), owner='story', timeout=60)
        if not r.get('ok'):  # Hayba on 5.9 refuses object: types (2026-11-11); these exist since the battle intro
            print('variable', name, 'kept:', str(r.get('error'))[:90])
    return dict(ready=room_ready(), vase=vase_cue(), done=done(), play=play())


def encounter():
    ns, es = inspect(E, 'EventGraph')
    t = {n['node_id']: norm(n['title']) for n in ns}
    guards = {x['from_node'] for x in es if t.get(x['from_node']) == 'Branch'
              and t.get(x['to_node']) == 'IntroStep' and x['from_pin'] == 'then' and x['to_pin'] == 'execute'}
    hits = [x['from_node'] for x in es if t.get(x['from_node']) == 'Delay' and x['from_pin'] == 'then'
            and (t.get(x['to_node']) == 'IntroStep' or x['to_node'] in guards)]
    assert len(hits) == 1, hits
    b = Batch(E, 'EventGraph')
    b.pin(hits[0], 'Duration', '0.6')
    b.run()
    ns, _ = inspect(E, 'EventGraph')
    delay = next(n for n in ns if n['node_id'] == hits[0])
    assert float(next(p['default_value'] for p in delay['pins'] if p['name'] == 'Duration')) == 0.6
    return 'IntroStep delay 0.6 s'


def garment():
    if not h.call('blueprint_inspect_graph', dict(path=G, graph_name='PlaceForRise')).get('ok'):
        PBI.call('blueprint_add_function', path=G, function_name='PlaceForRise', inputs=[])
    ns, es = inspect(G, 'PlaceForRise')
    e = find(ns, 'PlaceForRise')
    if len(ns) <= 1:
        b = Batch(G, 'PlaceForRise')
        b.get('data', 'Data', 0, 300)
        b.get('id', 'GarmentId', 250, 300, OPP_C)
        b.link('data', 'Data', 'id', 'self')
        prev_vec, ors = '0,0,0', []
        for i, (gid, at) in enumerate(SOURCES.items()):
            b.fn('eq%d' % i, K + 'EqualEqual_NameName', 500, 300 + 150 * i, B=gid)
            b.link('id', 'GarmentId', 'eq%d' % i, 'A')
            b.fn('sel%d' % i, K + 'SelectVector', 800 + 250 * i, 300, A=','.join(str(v) for v in at))
            if i:
                b.link('sel%d' % (i - 1), 'ReturnValue', 'sel%d' % i, 'B')
            else:
                b.pin('sel0', 'B', prev_vec)
            b.link('eq%d' % i, 'ReturnValue', 'sel%d' % i, 'bPickA')
        b.fn('or1', K + 'BooleanOR', 800, 700)
        b.link('eq0', 'ReturnValue', 'or1', 'A')
        b.link('eq1', 'ReturnValue', 'or1', 'B')
        b.fn('or2', K + 'BooleanOR', 1050, 700)
        b.link('or1', 'ReturnValue', 'or2', 'A')
        b.link('eq2', 'ReturnValue', 'or2', 'B')
        b.node('from', 'branch', 300, 0)
        b.link('or2', 'ReturnValue', 'from', 'Condition')
        b.get('body', 'Body', 1300, 450)
        b.fn('place', SC + 'K2_SetWorldLocation', 1600, 0, bSweep='false', bTeleport='true')
        b.link('body', 'Body', 'place', 'self')
        b.link('sel%d' % (len(SOURCES) - 1), 'ReturnValue', 'place', 'NewLocation')
        b.link(e, 'then', 'from', 'execute')
        b.link('from', 'then', 'place', 'execute')
        b.comment('Start where he saw it', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
        b.run()
    ns, es = inspect(G, 'EventGraph')
    t = {n['node_id']: norm(n['title']) for n in ns}
    rise = next(i for i, x in t.items() if x == 'Rise')
    nxt = [x for x in es if x['from_node'] == rise and x['from_pin'] == 'then']
    assert len(nxt) == 1, nxt
    if t[nxt[0]['to_node']] == 'PlaceForRise':
        return 'kept'
    b = Batch(G, 'EventGraph')
    b.cut(rise, 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.fn('place', G_C + ':PlaceForRise', 0, -200)
    b.link(rise, 'then', 'place', 'execute')
    b.link('place', 'then', nxt[0]['to_node'], nxt[0]['to_pin'])
    b.comment('From where he saw it', ['place'])
    b.run()
    return 'Rise starts at the source'


if __name__ == '__main__':
    steps = sys.argv[1:] or ['director', 'encounter', 'garment']
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + P, 'asset:' + E, 'asset:' + G], ttl_s=600, wait_s=600)
    try:
        print('wont_come', {s: globals()[s]() for s in steps})
    finally:
        h.release('story', token)
