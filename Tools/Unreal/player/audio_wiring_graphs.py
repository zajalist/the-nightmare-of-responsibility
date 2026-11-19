"""Audio pass, anim lane, graph side (docs/design/horror/audio_wiring.md): Hayba graph batches, each compiled and saved
only when clean (Batch.run rolls back otherwise). Asset side: audio_wiring_assets.py.
  $env:HAYBA_AGENT_ID='anim'; python Tools/Unreal/player/audio_wiring_graphs.py gear|footstep|turn|breath|foley
gear      BP_FoAPlayer.FootGear (Name): SetBootsWorn(b) -> 'Boots'/'Socks'; SetSuitedBody(b) -> 'Shoes', or back to
          'Boots'/'Socks' by the boots mesh's visibility.
footstep  AN_FoA_FootPlant, the non-Sand branch: BPL_FoAAudio.PlayFootstep(impact point, 'Rug' if the hit actor has
          tag Rug else 'Wood', the player's FootGear ('Socks' for anyone else), ground speed / 250 clamped 0..2).
turn      UpdateFirstPersonVisibility: S_Foley_ClothTurn when the view turns faster than 120 deg/s, 0.6 s cooldown,
          not in cinematics (reuses the turn lean's yaw rate).
breath    UpdateBreathAudio(): BreathAudio to 0 over 0.6 s while bCinematic or bBattleActive, back to full over 1 s;
          called right after SetCinematic and SetBattle set their flags.
foley     AN_FoA_Foley.Received_Notify (after audio_wiring_assets.py foley made the override): with probability
          Chance, PlaySoundAtLocation(Sound) at the notified mesh's Socket."""
import sys

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Characters/Player/BP_FoAPlayer'
PC = P + '.BP_FoAPlayer_C'
AN = '/Game/FoA/Characters/Player/Anims/AN_FoA_FootPlant'
LIB = '/Game/FoA/Audio/BPL_FoAAudio.BPL_FoAAudio_C:PlayFootstep'
K = '/Script/Engine.KismetMathLibrary:'
GS = '/Script/Engine.GameplayStatics:'
MS = '/Game/FoA/Audio/MetaSounds/'

assert not h.call('editor_get_state')['data']['pie_running'], 'PIE running'


def var(name, typ, default):
    r = h.call('blueprint_add_variable', dict(path=P, variable_name=name, variable_type=typ, default_value=default,
                                              instance_editable=False, update_existing=True, category='Audio'))
    assert r.get('ok'), r


def exec_after(nodes, edges, title):
    """(node, its first exec successor) of the unique node with this title."""
    n = find(nodes, title)
    e = next(e for e in edges if e['from_node'] == n and e['from_pin'] == 'then')
    return n, e['to_node']


def gear():
    var('FootGear', 'name', 'Socks')
    nodes, edges = inspect(P, 'SetBootsWorn')
    if not any(n['title'] == 'Set FootGear' for n in nodes):
        e, nxt = exec_after(nodes, edges, 'SetBootsWorn')
        b = Batch(P, 'SetBootsWorn')
        b.cut(e, 'then', nxt, 'execute')
        b.fn('pick', K + 'SelectName', 200, 300, A='Boots', B='Socks'); b.link(e, 'bEnable', 'pick', 'bPickA')
        b.set('g', 'FootGear', 450, 0); b.link('pick', 'ReturnValue', 'g', 'FootGear')
        b.link(e, 'then', 'g', 'execute'); b.link('g', 'then', nxt, 'execute')
        b.comment('Footstep gear', ['pick', 'g'])
        b.run()
    nodes, edges = inspect(P, 'SetSuitedBody')
    if not any(n['title'] == 'Set FootGear' for n in nodes):
        e, nxt = exec_after(nodes, edges, 'SetSuitedBody')
        b = Batch(P, 'SetSuitedBody')
        b.cut(e, 'then', nxt, 'execute')
        b.get('boots', 'BootsWornMesh', -200, 500)
        b.fn('vis', '/Script/Engine.SceneComponent:IsVisible', 0, 500); b.link('boots', 'BootsWornMesh', 'vis', 'self')
        b.fn('plain', K + 'SelectName', 200, 450, A='Boots', B='Socks'); b.link('vis', 'ReturnValue', 'plain', 'bPickA')
        b.fn('pick', K + 'SelectName', 400, 300, A='Shoes'); b.link('plain', 'ReturnValue', 'pick', 'B')
        b.link(e, 'bEnable', 'pick', 'bPickA')
        b.set('g', 'FootGear', 650, 0); b.link('pick', 'ReturnValue', 'g', 'FootGear')
        b.link(e, 'then', 'g', 'execute'); b.link('g', 'then', nxt, 'execute')
        b.comment('Footstep gear', ['boots', 'vis', 'plain', 'pick', 'g'])
        b.run()


def footstep():
    nodes, edges = inspect(AN, 'Received_Notify')
    if any(n['title'] == 'Play Footstep' or 'PlayFootstep' in n['title'] for n in nodes):
        return print('footstep already wired')
    e, ret = find(nodes, 'Received_Notify'), find(nodes, 'Return Node')
    brk = find(nodes, 'BreakHitResult')
    wood = find(nodes, 'PlaySoundAtLocation')
    sand_tag = next(n['node_id'] for n in nodes if n['title'] == 'ActorHasTag')
    sand_br = next(x['to_node'] for x in edges if x['from_node'] == sand_tag and x['to_pin'] == 'Condition')
    b = Batch(AN, 'Received_Notify')
    b.ops.append(dict(op='remove', node_ids=[wood]))
    b.fn('owner', '/Script/Engine.ActorComponent:GetOwner', 2000, 500); b.link(e, 'MeshComp', 'owner', 'self')
    b.node('cast', 'cast', 2300, 140, class_path=PC); b.link('owner', 'ReturnValue', 'cast', 'Object')
    b.get('gear', 'FootGear', 2600, 420, cls=PC); b.link('cast', 'AsBP Fo APlayer', 'gear', 'self')
    b.fn('vel', '/Script/Engine.Actor:GetVelocity', 2300, 600); b.link('owner', 'ReturnValue', 'vel', 'self')
    b.fn('speed', K + 'VSize', 2550, 600); b.link('vel', 'ReturnValue', 'speed', 'A')
    b.fn('gait', K + 'MapRangeClamped', 2800, 600, InRangeA=0, InRangeB=500, OutRangeA=0, OutRangeB=2)  # speed/250 in 0..2
    b.link('speed', 'ReturnValue', 'gait', 'Value')
    b.fn('rug', '/Script/Engine.Actor:ActorHasTag', 2300, 800, Tag='Rug'); b.link(brk, 'HitActor', 'rug', 'self')
    b.fn('surf', K + 'SelectName', 2550, 800, A='Rug', B='Wood'); b.link('rug', 'ReturnValue', 'surf', 'bPickA')
    for ref, y, gear_pin in (('step', 100, True), ('other', 300, False)):  # the player / anyone else playing the clips
        b.fn(ref, LIB, 3100, y)
        b.link(brk, 'ImpactPoint', ref, 'Location'); b.link('surf', 'ReturnValue', ref, 'Surface')
        b.link('gait', 'ReturnValue', ref, 'Gait')
        if gear_pin:
            b.link('gear', 'FootGear', ref, 'Gear')
        else:
            b.pin(ref, 'Gear', 'Socks')
        b.link(ref, 'then', ret, 'execute')
    b.link(sand_br, 'else', 'cast', 'execute')
    b.link('cast', 'then', 'step', 'execute'); b.link('cast', 'CastFailed', 'other', 'execute')
    b.comment('Wood or rug: the audio lane picks the take', ['owner', 'cast', 'gear', 'vel', 'speed', 'gait', 'rug', 'surf', 'step', 'other'])
    b.run()


def turn():
    var('LastClothTurn', 'float', '-10')
    F = 'UpdateFirstPersonVisibility'
    nodes, edges = inspect(P, F)
    if any(n['title'] == 'Set LastClothTurn' for n in nodes):
        return print('turn already wired')
    setprev, nxt = exec_after(nodes, edges, 'Set PrevViewYaw')
    wrap = next(n['node_id'] for n in nodes if n['title'].startswith('Normalize Axis') or n['title'] == 'NormalizeAxis')
    rate = next(x['to_node'] for x in edges if x['from_node'] == wrap and x['from_pin'] == 'ReturnValue')
    b = Batch(P, F)
    b.cut(setprev, 'then', nxt, 'execute')
    b.fn('abs', K + 'Abs', 4000, 2600); b.link(rate, 'ReturnValue', 'abs', 'A')
    b.fn('fast', K + 'Greater_DoubleDouble', 4200, 2600, B=120); b.link('abs', 'ReturnValue', 'fast', 'A')
    b.fn('now', GS + 'GetTimeSeconds', 4000, 2800)
    b.get('last', 'LastClothTurn', 4000, 2950)
    b.fn('since', K + 'Subtract_DoubleDouble', 4200, 2800); b.link('now', 'ReturnValue', 'since', 'A'); b.link('last', 'LastClothTurn', 'since', 'B')
    b.fn('cool', K + 'Greater_DoubleDouble', 4400, 2800, B=0.6); b.link('since', 'ReturnValue', 'cool', 'A')
    b.get('cin', 'bCinematic', 4200, 3000)
    b.fn('free', K + 'Not_PreBool', 4400, 3000); b.link('cin', 'bCinematic', 'free', 'A')
    b.fn('and1', K + 'BooleanAND', 4600, 2650); b.link('fast', 'ReturnValue', 'and1', 'A'); b.link('cool', 'ReturnValue', 'and1', 'B')
    b.fn('and2', K + 'BooleanAND', 4800, 2700); b.link('and1', 'ReturnValue', 'and2', 'A'); b.link('free', 'ReturnValue', 'and2', 'B')
    b.node('br', 'branch', 5000, 2400); b.link('and2', 'ReturnValue', 'br', 'Condition')
    b.fn('here', '/Script/Engine.Actor:K2_GetActorLocation', 5000, 2800)
    b.fn('play', GS + 'PlaySoundAtLocation', 5250, 2400, Sound=MS + 'Foley/S_Foley_ClothTurn.S_Foley_ClothTurn')
    b.link('here', 'ReturnValue', 'play', 'Location')
    b.set('mark', 'LastClothTurn', 5550, 2400); b.link('now', 'ReturnValue', 'mark', 'LastClothTurn')
    b.link(setprev, 'then', 'br', 'execute'); b.link('br', 'then', 'play', 'execute'); b.chain('play', 'mark')
    b.link('mark', 'then', nxt, 'execute'); b.link('br', 'else', nxt, 'execute')
    b.comment('Cloth on a fast turn', ['abs', 'fast', 'now', 'last', 'since', 'cool', 'cin', 'free', 'and1', 'and2', 'br', 'here', 'play', 'mark'])
    b.run()


def breath():
    if not h.call('blueprint_inspect_graph', dict(path=P, graph_name='UpdateBreathAudio')).get('ok'):
        r = h.call('blueprint_add_function', dict(path=P, function_name='UpdateBreathAudio', inputs=[]))
        assert r.get('ok'), r
    nodes, _ = inspect(P, 'UpdateBreathAudio')
    if len(nodes) <= 1:
        e = find(nodes, 'UpdateBreathAudio')
        b = Batch(P, 'UpdateBreathAudio')
        b.get('cin', 'bCinematic', 0, 250); b.get('bat', 'bBattleActive', 0, 350)
        b.fn('quiet', K + 'BooleanOR', 220, 280); b.link('cin', 'bCinematic', 'quiet', 'A'); b.link('bat', 'bBattleActive', 'quiet', 'B')
        b.node('br', 'branch', 450, 0); b.link('quiet', 'ReturnValue', 'br', 'Condition')
        b.get('ac', 'BreathAudio', 450, 300)
        b.fn('down', '/Script/Engine.AudioComponent:AdjustVolume', 750, -100, AdjustVolumeDuration=0.6, AdjustVolumeLevel=0.0)
        b.fn('up', '/Script/Engine.AudioComponent:AdjustVolume', 750, 150, AdjustVolumeDuration=1.0, AdjustVolumeLevel=1.0)
        b.link('ac', 'BreathAudio', 'down', 'self'); b.link('ac', 'BreathAudio', 'up', 'self')
        b.link(e, 'then', 'br', 'execute'); b.link('br', 'then', 'down', 'execute'); b.link('br', 'else', 'up', 'execute')
        b.comment('Tired breathing: hush it in cinematics and the battle', ['cin', 'bat', 'quiet', 'br', 'ac', 'down', 'up'])
        b.run()
    for fn, flag in (('SetCinematic', 'Set bCinematic'), ('SetBattle', 'Set bBattleActive')):
        nodes, edges = inspect(P, fn)
        if any(n['title'] == 'Update Breath Audio' or n['title'] == 'UpdateBreathAudio' for n in nodes):
            continue
        s, nxt = exec_after(nodes, edges, flag)
        b = Batch(P, fn)
        b.cut(s, 'then', nxt, 'execute')
        b.fn('upd', PC + ':UpdateBreathAudio', 600, -200)
        b.link(s, 'then', 'upd', 'execute'); b.link('upd', 'then', nxt, 'execute')
        b.run()


def foley():
    N = '/Game/FoA/Characters/Player/Anims/AN_FoA_Foley'
    for name, typ, default in (('Sound', 'object:/Script/Engine.SoundBase', None), ('Chance', 'float', '1'), ('Socket', 'name', 'hand_r')):
        args = dict(path=N, variable_name=name, variable_type=typ, instance_editable=True, update_existing=True, category='Foley')
        if default is not None:
            args['default_value'] = default
        r = h.call('blueprint_add_variable', args)
        assert r.get('ok'), r
    nodes, _ = inspect(N, 'Received_Notify')
    if len(nodes) > 2:
        return print('foley already wired')
    e = find(nodes, 'Received_Notify')
    ret = next((n['node_id'] for n in nodes if n['title'] == 'Return Node'), None)  # a fresh override may have none
    b = Batch(N, 'Received_Notify')
    b.get('chance', 'Chance', 0, 250)
    b.fn('roll', K + 'RandomBoolWithWeight', 200, 250); b.link('chance', 'Chance', 'roll', 'Weight')
    b.node('br', 'branch', 450, 0); b.link('roll', 'ReturnValue', 'br', 'Condition')
    b.get('sock', 'Socket', 450, 400)
    b.fn('at', '/Script/Engine.SceneComponent:GetSocketLocation', 650, 300); b.link(e, 'MeshComp', 'at', 'self')
    b.link('sock', 'Socket', 'at', 'InSocketName')
    b.get('snd', 'Sound', 650, 500)
    b.fn('play', GS + 'PlaySoundAtLocation', 900, 0); b.link('snd', 'Sound', 'play', 'Sound'); b.link('at', 'ReturnValue', 'play', 'Location')
    b.link(e, 'then', 'br', 'execute'); b.link('br', 'then', 'play', 'execute')
    if ret:
        b.link('play', 'then', ret, 'execute'); b.link('br', 'else', ret, 'execute')
    b.comment('Foley at a socket, Chance of the time', ['chance', 'roll', 'br', 'sock', 'at', 'snd', 'play'])
    b.run()


lease = h.lease_acquire('anim', ['asset:/Game/FoA/Characters/Player'], ttl_s=60)
try:
    {'gear': gear, 'footstep': footstep, 'turn': turn, 'breath': breath, 'foley': foley}[sys.argv[1]]()
finally:
    h.release('anim', lease)
