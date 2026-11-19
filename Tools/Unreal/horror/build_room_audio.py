"""BP_RoomAudio: the bedroom's own sound director (audio lane). Native Hayba graphs, no Tick, no editor Python.
  $env:HAYBA_AGENT_ID='horror'; python Tools/Unreal/horror/build_room_audio.py [assets|poll|cues|events|music|presence|all]
Placed once as FOA_RoomAudio. It reads BP_BeatDirector's public state through GetActorOfClass on a 0.1 s timer and
plays only its own components and presets, so the other lanes don't have to wire these:
  - music (UpdateMusic, the level's one music manager): MenuMusic on the title while BP_FoAFrontEnd is neither in
    gameplay nor waking (fades in 3 s, out 2.5 s on Wake up); BattleIntroSting once as the director's
    bBattleIntroPlaying rises (LS_BattleIntro starts), faded out 1 s when it ends; BattleMusic for the T8 fight after
    the intro (fades in 3 s), out 2.5 s when the beat leaves 8 (victory into the T9 suit). Nothing in between: the
    bedroom keeps its horror bed. Each track is one class-default variable, so a swap is one change.
  - beds: rain on the bay glass, the radiator under the bay, the distant town hum (auto-play, positional)
  - the house settling: a random creak somewhere in the room every 7-18 s, sooner as the beats advance
  - the Nightmare's presence drone, riding BP_Nightmare while it is visible
  - headache (bHeadacheActive): pressure swell plus ringing, ducked mix while it lasts
  - rollover (bRollingOver): tape time-shift plus a heartbeat bed while the day turns over
  - T8 battle: panic breathing bed; T9 suit: one warm tone over a short duck; T10: the outside, at the door
Edges are detected against the Last* variables so every cue fires once per change."""
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, find, inspect  # noqa: E402

P = '/Game/FoA/Audio/BP_RoomAudio'
C = P + '.BP_RoomAudio_C'
DIR_C = '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'
FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
MUS = {k: f'/Game/FoA/Audio/Music/{v}.{v}' for k, v in (
    ('MenuMusic', 'MUS_Menu_Loop'), ('BattleMusic', 'MUS_Battle_Loop'), ('BattleIntroSting', 'MUS_BattleIntro_Sting'))}
# MusicState -> track (the Tracks map's default; a swap is one entry). Beats: 0 Wake (the phone after the cinematic),
# 1-6 Explore, 7 Chase, 8 Battle (after the intro), 9 Payoff (once, into T10), 10 Ending (the walk-out and credits)
TRACKS = {'Menu': 'MUS_Menu_Loop', 'Wake': 'MUS_Wake_Loop', 'Explore': 'MUS_Explore_Loop', 'Chase': 'MUS_Chase_Loop',
          'Battle': 'MUS_Battle_Loop', 'Payoff': 'MUS_Payoff', 'Ending': 'MUS_Ending',
          'Dream': 'MUS_Dream_Loop', 'City': 'MUS_CityDrive_Loop'}
MARE_C = '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C'
MS = '/Game/FoA/Audio/MetaSounds/'
SND = {k: f'{MS}{k.split("_")[1]}/{k}.{k}' for k in (
    'S_Ambience_RainOnGlass_Loop_01', 'S_Ambience_Radiator_Loop_01', 'S_Ambience_DistantCity_Loop_01',
    'S_Ambience_Outside_Loop_01', 'S_Horror_Presence_Loop_01', 'S_Dream_Heartbeat_Loop_01', 'S_Breath_Panic_Loop_01',
    'S_Battle_ComposureLow_Loop_01', 'S_Creaks_Settle', 'S_Story_HeadPressure', 'S_Story_HeadRing', 'S_Story_TimeShift', 'S_Story_SuitTone')}
DUCK = '/Game/FoA/Audio/Mix/SMX_StoryDuck.SMX_StoryDuck'
K = '/Script/Engine.KismetMathLibrary:'
KS = '/Script/Engine.KismetSystemLibrary:'
GS = '/Script/Engine.GameplayStatics:'
SC = '/Script/Engine.SceneComponent:'
AU = '/Script/Engine.AudioComponent:'
# component, sound, relative location (the actor sits at the room origin), auto play, volume
BEDS = [('Rain', 'S_Ambience_RainOnGlass_Loop_01', '-60,-385,170', True, 0.55),
        ('Radiator', 'S_Ambience_Radiator_Loop_01', '-60,-375,35', True, 0.35),
        ('Hum', 'S_Ambience_DistantCity_Loop_01', '-60,-395,220', False, 0.3),  # only with the outside at T10 (au3: 5 beds at once)
        ('Outside', 'S_Ambience_Outside_Loop_01', '375,87,110', False, 0.8),
        ('Presence', 'S_Horror_Presence_Loop_01', '0,0,120', False, 0.7),
        ('Heartbeat', 'S_Dream_Heartbeat_Loop_01', '0,0,0', False, 0.8),
        ('Panic', 'S_Breath_Panic_Loop_01', '0,0,0', False, 0.35),
        ('Composure', 'S_Battle_ComposureLow_Loop_01', '0,0,0', False, 0.6)]  # the fight, composure under 30 %


def call(cmd, **params):
    r = h.call(cmd, params)
    assert r.get('ok'), r
    d = r.get('data', {})
    assert d.get('ok', True) and not d.get('failed'), d
    return d


def graph(name):
    ns, _ = inspect(P, name)
    e = find(ns, name)
    b = Batch(P, name)
    old = [n['node_id'] for n in ns if n['node_id'] != e]
    if old:
        b.ops.append(dict(op='remove', node_ids=old))
    return b, e


def compile_clean():
    """Compile and return (ok, summary); 0 errors and 0 warnings only."""
    c = h.call('blueprint_compile', {'path': P}).get('data') or {}
    ok = c.get('ok', True) and c.get('compiled', True) and not c.get('error_count', 0) and not c.get('warning_count', 0)
    return ok, {k: c.get(k) for k in ('error_count', 'warning_count', 'errors', 'warnings')}


def done(b, title):
    """One Hayba batch, compiled. Saved only on a clean 0/0 compile; on any failure its own new nodes are removed and the
    Blueprint is recompiled, so it is never left failing in memory (a failing BP_RoomAudio froze PIE behind a modal
    dialog on 2026-11-09)."""
    b.comment(title, [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.ops.append(dict(op='fit_comments'))
    r = h.call('blueprint_graph_batch', dict(path=P, graph_name=b.graph, ops=b.ops, compile=True, save=False), timeout=120)
    d = r.get('data') or {}
    c = d.get('compile') or {}
    clean = (r.get('ok') and not d.get('compile_error') and c.get('ok', True) and c.get('compiled', True)
             and not c.get('error_count', 0) and not c.get('warning_count', 0))
    if clean:
        call('asset_save', asset_paths=[P])
        print(b.graph, 'ok', d.get('applied'), '/', d.get('total'))
        return
    made = list((d.get('refs') or {}).values())
    if made:
        h.call('blueprint_remove_nodes', dict(path=P, graph_name=b.graph, node_ids=made))
    ok, summary = compile_clean()
    print(b.graph, 'FAILED, rolled back', len(made), 'nodes; recompile clean:', ok, summary, d.get('failed_index'),
          r.get('error') or d.get('error') or c.get('errors'))
    if ok:
        call('asset_save', asset_paths=[P])
    sys.exit(1)


def timer(b, ref, fn, x, y, t, loop=False):
    return b.fn(ref, KS + 'K2_SetTimer', x, y, FunctionName=fn, Time=t, bLooping=str(loop).lower())


def fade(b, ref, comp, x, y, up, seconds, level=1.0):
    b.get(ref + 'C', comp, x, y + 250)
    if up:
        b.fn(ref, AU + 'FadeIn', x, y, FadeInDuration=seconds, FadeVolumeLevel=level, StartTime=0)
    else:
        b.fn(ref, AU + 'FadeOut', x, y, FadeOutDuration=seconds, FadeVolumeLevel=0)
    b.link(ref + 'C', comp, ref, 'self')
    return ref


def play2d(b, ref, sound, x, y, vol=1.0):
    return b.fn(ref, GS + 'PlaySound2D', x, y, Sound=SND[sound], VolumeMultiplier=vol)


def assets():
    if not h.call('blueprint_get_info', {'path': P}).get('ok'):
        call('blueprint_create', name='BP_RoomAudio', package_path=P, parent_class_path='/Script/Engine.Actor')
    info = call('blueprint_get_info', path=P)
    have = {x['name'] for x in info['components']}
    for name in ['Root'] + [c for c, *_ in BEDS] + ['Music', 'Music2', 'Sting']:
        if name not in have:
            call('blueprint_add_component', path=P, component_name=name,
                 component_class_path='/Script/Engine.' + ('SceneComponent' if name == 'Root' else 'AudioComponent'))
    for comp, snd, loc, auto, vol in BEDS:
        call('object_set_property', path=f'{C}:{comp}_GEN_VARIABLE', properties={
            'Sound': SND[snd], 'bAutoActivate': auto, 'VolumeMultiplier': vol, 'RelativeLocation': '(X={},Y={},Z={})'.format(*loc.split(','))})
    for comp in ('Music', 'Music2', 'Sting'):  # music: 2D (the MUS_ waves carry SC_Music and no attenuation), started by UpdateMusic
        call('object_set_property', path=f'{C}:{comp}_GEN_VARIABLE', properties={'bAutoActivate': False, 'VolumeMultiplier': 1.0})
    variables = [('Director', 'object:' + DIR_C, ''), ('LastBeat', 'int', '-1'), ('bLastHeadache', 'bool', 'false'),
                 ('bLastRollover', 'bool', 'false'), ('bLastPresence', 'bool', 'false'),
                 ('MusicState', 'name', 'None'), ('MusicOverride', 'name', 'None'), ('bLastIntro', 'bool', 'false'), ('bIntroSeen', 'bool', 'false'),
                 ('bMenuWanted', 'bool', 'false'), ('bWakeWanted', 'bool', 'false'), ('bMusicB', 'bool', 'false'), ('bLastLowComposure', 'bool', 'false')]
    for n, t, v in variables:
        call('blueprint_add_variable', path=P, variable_name=n, variable_type=t, default_value=v, instance_editable=False,
             update_existing=True, category='Room audio')
    call('blueprint_add_variable', path=P, variable_name='Tracks', variable_type='name', container='map',
         map_value_type='object:/Script/Engine.SoundBase', instance_editable=False, update_existing=True, category='Music',
         default_value='(' + ','.join(f'({k},"/Game/FoA/Audio/Music/{v}.{v}")' for k, v in TRACKS.items()) + ')')
    for n, v in MUS.items():  # the sting (and the first pass's two loops): swapping one is this one default
        call('blueprint_add_variable', path=P, variable_name=n, variable_type='object:/Script/Engine.SoundBase', default_value=v,
             instance_editable=False, update_existing=True, category='Music')
    for fn, inputs in (('Poll', []), ('Settle', []), ('UpdatePresence', []), ('UpdateMusic', []), ('UpdateComposure', []),
                       ('OnHeadache', [{'name': 'bActive', 'type': 'bool'}]),
                       ('OnRollover', [{'name': 'bActive', 'type': 'bool'}]),
                       ('OnBeat', [{'name': 'Beat', 'type': 'int'}]), ('Unduck', [])):
        if fn not in info['functions']:
            call('blueprint_add_function', path=P, function_name=fn, inputs=inputs)
    ok, summary = compile_clean()
    assert ok, ('BP_RoomAudio does not compile clean after the asset step', summary)
    call('asset_save', asset_paths=[P])


def edge(b, ref, var, last, fn, x, y, src, src_pin):
    """if src != Last: Last = src; fn(src)"""
    b.get(ref + 'L', last, x, y + 250)
    b.fn(ref + 'Ne', K + ('NotEqual_BoolBool' if var == 'bool' else 'NotEqual_IntInt'), x, y + 400)
    b.link(src, src_pin, ref + 'Ne', 'A')
    b.link(ref + 'L', last, ref + 'Ne', 'B')
    b.node(ref, 'branch', x, y)
    b.link(ref + 'Ne', 'ReturnValue', ref, 'Condition')
    b.set(ref + 'S', last, x + 250, y - 150)
    b.link(src, src_pin, ref + 'S', last)
    b.link(ref, 'then', ref + 'S', 'execute')
    return ref


def poll():
    b, e = graph('Poll')
    b.fn('find', GS + 'GetActorOfClass', 0, 300, ActorClass=DIR_C)
    b.set('keep', 'Director', 250, 0)
    b.link('find', 'ReturnValue', 'keep', 'Director')
    b.get('dir', 'Director', 250, 300)
    b.fn('valid', KS + 'IsValid', 500, 300)
    b.link('dir', 'Director', 'valid', 'Object')
    b.node('hasDir', 'branch', 500, 0)
    b.link('valid', 'ReturnValue', 'hasDir', 'Condition')
    for var, x in (('bHeadacheActive', 750), ('bRollingOver', 1000), ('BeatIndex', 1250)):
        b.get(var, var, x, 500, DIR_C)
        b.link('dir', 'Director', var, 'self')
    edge(b, 'eHead', 'bool', 'bLastHeadache', 'OnHeadache', 750, 0, 'bHeadacheActive', 'bHeadacheActive')
    b.fn('head', C + ':OnHeadache', 1000, -150)
    b.link('bHeadacheActive', 'bHeadacheActive', 'head', 'bActive')
    b.link('eHeadS', 'then', 'head', 'execute')
    edge(b, 'eRoll', 'bool', 'bLastRollover', 'OnRollover', 1300, 0, 'bRollingOver', 'bRollingOver')
    b.fn('roll', C + ':OnRollover', 1550, -150)
    b.link('bRollingOver', 'bRollingOver', 'roll', 'bActive')
    b.link('eRollS', 'then', 'roll', 'execute')
    b.link('eHead', 'else', 'eRoll', 'execute')
    b.link('head', 'then', 'eRoll', 'execute')
    edge(b, 'eBeat', 'int', 'LastBeat', 'OnBeat', 1850, 0, 'BeatIndex', 'BeatIndex')
    b.fn('beat', C + ':OnBeat', 2100, -150)
    b.link('BeatIndex', 'BeatIndex', 'beat', 'Beat')
    b.link('eBeatS', 'then', 'beat', 'execute')
    b.link('eRoll', 'else', 'eBeat', 'execute')
    b.link('roll', 'then', 'eBeat', 'execute')
    b.fn('mare', C + ':UpdatePresence', 2400, 0)
    b.link('eBeat', 'else', 'mare', 'execute')
    b.link('beat', 'then', 'mare', 'execute')
    b.fn('music', C + ':UpdateMusic', 2650, 0)  # the title has music too, so it runs with or without the director
    b.link('mare', 'then', 'music', 'execute')
    b.fn('comp', C + ':UpdateComposure', 2900, 0)
    b.link('music', 'then', 'comp', 'execute')
    b.link('hasDir', 'else', 'music', 'execute')
    b.chain(e, 'find', 'keep', 'hasDir')
    b.link('hasDir', 'then', 'eHead', 'execute')
    done(b, 'Read the house state')


def cues():
    # Headache: pressure swell plus ringing under a duck; the duck pops when it ends
    b, e = graph('OnHeadache')
    b.node('on', 'branch', 250, 0)
    b.link(e, 'bActive', 'on', 'Condition')
    b.fn('duck', GS + 'PushSoundMixModifier', 500, -150, InSoundMixModifier=DUCK)
    play2d(b, 'press', 'S_Story_HeadPressure', 750, -150, 0.9)
    play2d(b, 'ring', 'S_Story_HeadRing', 1000, -150, 0.5)
    b.fn('unduck', GS + 'PopSoundMixModifier', 500, 150, InSoundMixModifier=DUCK)
    b.chain(e, 'on', 'duck', 'press', 'ring')
    b.link('on', 'else', 'unduck', 'execute')
    done(b, 'Headache')
    # Rollover: tape time-shift and a heartbeat bed while the day turns
    b, e = graph('OnRollover')
    b.node('on', 'branch', 250, 0)
    b.link(e, 'bActive', 'on', 'Condition')
    play2d(b, 'shift', 'S_Story_TimeShift', 500, -150)
    fade(b, 'beatIn', 'Heartbeat', 750, -150, True, 1.0, 0.8)
    fade(b, 'beatOut', 'Heartbeat', 500, 200, False, 2.5)
    b.fn('duck', GS + 'PushSoundMixModifier', 1000, -150, InSoundMixModifier=DUCK)
    b.fn('unduck', GS + 'PopSoundMixModifier', 750, 200, InSoundMixModifier=DUCK)
    b.chain(e, 'on', 'shift', 'beatIn', 'duck')
    b.link('on', 'else', 'beatOut', 'execute')
    b.chain('beatOut', 'unduck')
    done(b, 'Day rollover')
    # Beats: battle breathing, the suit tone, the outside at the door
    b, e = graph('OnBeat')
    for i, (ref, n) in enumerate((('is8', 8), ('is9', 9), ('is10', 10))):
        b.fn(ref, K + 'EqualEqual_IntInt', 250, 300 + i * 150, B=n)
        b.link(e, 'Beat', ref, 'A')
    b.node('battle', 'branch', 500, 0)
    b.link('is8', 'ReturnValue', 'battle', 'Condition')
    fade(b, 'panicIn', 'Panic', 750, -200, True, 2.0, 0.35)
    fade(b, 'panicOut', 'Panic', 750, 150, False, 2.0)  # harmless when it isn't playing
    b.node('suit', 'branch', 1300, 0)
    b.link('is9', 'ReturnValue', 'suit', 'Condition')
    b.fn('duck', GS + 'PushSoundMixModifier', 1550, -150, InSoundMixModifier=DUCK)
    play2d(b, 'tone', 'S_Story_SuitTone', 1800, -150, 0.8)
    timer(b, 'undo', 'Unduck', 2050, -150, 4.0)
    b.node('out', 'branch', 2350, 0)
    b.link('is10', 'ReturnValue', 'out', 'Condition')
    b.fn('door', '/Script/Engine.Actor:K2_GetActorLocation', 2600, 300)
    b.get('dir', 'Director', 2600, 450)
    b.get('doorA', 'Door', 2600, 550, DIR_C)
    b.link('dir', 'Director', 'doorA', 'self')
    b.link('doorA', 'Door', 'door', 'self')
    b.get('outC', 'Outside', 2850, 300)
    b.fn('place', SC + 'K2_SetWorldLocation', 2850, -150, bSweep='false', bTeleport='true')
    b.link('outC', 'Outside', 'place', 'self')
    b.link('door', 'ReturnValue', 'place', 'NewLocation')
    fade(b, 'outIn', 'Outside', 3100, -150, True, 3.0, 0.8)
    fade(b, 'outOff', 'Outside', 2600, 200, False, 1.5)
    b.chain(e, 'battle', 'panicIn')
    b.link('battle', 'else', 'panicOut', 'execute')
    b.link('panicIn', 'then', 'suit', 'execute')
    b.link('panicOut', 'then', 'suit', 'execute')
    b.chain('suit', 'duck', 'tone', 'undo')
    b.link('suit', 'else', 'out', 'execute')
    b.link('undo', 'then', 'out', 'execute')
    fade(b, 'humIn', 'Hum', 3350, -150, True, 4.0, 0.3)
    fade(b, 'humOff', 'Hum', 2850, 200, False, 1.5)
    b.chain('out', 'place', 'outIn', 'humIn')
    b.link('out', 'else', 'outOff', 'execute')
    b.chain('outOff', 'humOff')
    done(b, 'Beat cues')
    # The house settling: one creak at a random spot, then the next one sooner as the beats advance
    b, e = graph('Settle')
    b.fn('x', K + 'RandomFloatInRange', 0, 300, Min=-340, Max=340)
    b.fn('y', K + 'RandomFloatInRange', 0, 450, Min=-280, Max=280)
    b.fn('z', K + 'RandomFloatInRange', 0, 600, Min=20, Max=290)
    b.fn('at', K + 'MakeVector', 250, 300)
    for a in 'xyz':
        b.link(a, 'ReturnValue', 'at', a.upper())
    b.fn('creak', GS + 'PlaySoundAtLocation', 500, 0, Sound=SND['S_Creaks_Settle'], VolumeMultiplier=0.8)
    b.link('at', 'ReturnValue', 'creak', 'Location')
    b.get('beat', 'LastBeat', 500, 450)
    b.fn('bf', K + 'Conv_IntToDouble', 750, 450)
    b.link('beat', 'LastBeat', 'bf', 'InInt')
    b.fn('lo', K + 'MapRangeClamped', 1000, 450, InRangeA=0, InRangeB=10, OutRangeA=12, OutRangeB=5)
    b.link('bf', 'ReturnValue', 'lo', 'Value')
    b.fn('gap', K + 'RandomFloatInRange', 1250, 450)
    b.link('lo', 'ReturnValue', 'gap', 'Min')
    b.fn('hi', K + 'Add_DoubleDouble', 1250, 600, B=6)
    b.link('lo', 'ReturnValue', 'hi', 'A')
    b.link('hi', 'ReturnValue', 'gap', 'Max')
    timer(b, 'next', 'Settle', 1500, 0, 10)
    b.link('gap', 'ReturnValue', 'next', 'Time')
    b.chain(e, 'creak', 'next')
    done(b, 'House settling')
    presence()
    # Unduck after the suit tone
    b, e = graph('Unduck')
    b.fn('pop', GS + 'PopSoundMixModifier', 250, 0, InSoundMixModifier=DUCK)
    b.chain(e, 'pop')
    done(b, 'Lift the duck')


def presence():
    """The Nightmare's presence: the drone rides BP_Nightmare while it is visible. The actor can be gone (a PIE session
    on 2026-11-10 lost it 7.5 min in), so validity gates the exec path: an AND of IsValid and bHidden still read bHidden
    from None, because Blueprint evaluates both inputs. Gone counts as not here, so a playing drone fades out."""
    b, e = graph('UpdatePresence')
    b.fn('find', GS + 'GetActorOfClass', 0, 300, ActorClass=MARE_C)
    b.fn('valid', KS + 'IsValid', 250, 300)
    b.link('find', 'ReturnValue', 'valid', 'Object')
    b.node('isValid', 'branch', 250, 0)
    b.link('valid', 'ReturnValue', 'isValid', 'Condition')
    b.get('hidden', 'bHidden', 500, 300, '/Script/Engine.Actor')
    b.link('find', 'ReturnValue', 'hidden', 'self')
    b.fn('shown', K + 'Not_PreBool', 500, 450)
    b.link('hidden', 'bHidden', 'shown', 'A')
    b.node('isHere', 'branch', 750, 0)
    b.link('shown', 'ReturnValue', 'isHere', 'Condition')
    b.fn('where', '/Script/Engine.Actor:K2_GetActorLocation', 1000, 300)
    b.link('find', 'ReturnValue', 'where', 'self')
    b.get('pc', 'Presence', 1000, 450)
    b.fn('follow', SC + 'K2_SetWorldLocation', 1000, -150, bSweep='false', bTeleport='true')
    b.link('pc', 'Presence', 'follow', 'self')
    b.link('where', 'ReturnValue', 'follow', 'NewLocation')
    # here: fade in once, when it was not here before
    b.get('lastOn', 'bLastPresence', 1250, 300)
    b.fn('wasOff', K + 'Not_PreBool', 1250, 450)
    b.link('lastOn', 'bLastPresence', 'wasOff', 'A')
    b.node('arrive', 'branch', 1500, -150)
    b.link('wasOff', 'ReturnValue', 'arrive', 'Condition')
    b.set('keepOn', 'bLastPresence', 1750, -150)
    b.pin('keepOn', 'bLastPresence', 'true')
    fade(b, 'in', 'Presence', 2000, -300, True, 1.5, 0.7)
    # hidden or gone: fade out once, when it was here before
    b.get('lastOff', 'bLastPresence', 1250, 700)
    b.node('leave', 'branch', 1500, 400)
    b.link('lastOff', 'bLastPresence', 'leave', 'Condition')
    b.set('keepOff', 'bLastPresence', 1750, 400)
    b.pin('keepOff', 'bLastPresence', 'false')
    fade(b, 'out', 'Presence', 2000, 400, False, 2.0)
    b.chain(e, 'find', 'isValid', 'isHere', 'follow', 'arrive', 'keepOn', 'in')
    b.link('isValid', 'else', 'leave', 'execute')
    b.link('isHere', 'else', 'leave', 'execute')
    b.chain('leave', 'keepOff', 'out')
    done(b, 'The Nightmare is near')


def music():
    """UpdateMusic, every poll. Reads of another actor sit behind an IsValid exec branch (an AND would still read them
    from None). The sting rides the rising edge of bBattleIntroPlaying. The tracks follow MusicState: Menu (the title),
    Wake (Wake up pressed, through T0), then by beat (TRACKS). A change crossfades: the active component (Music or
    Music2, bMusicB) fades out over 2.5 s while the other takes Tracks[new] and fades in over 3 s; None only fades out."""
    b, e = graph('UpdateMusic')
    # the front end: menu while it is neither in gameplay nor waking; the wake bed while it wakes
    b.fn('fe', GS + 'GetActorOfClass', 0, 300, ActorClass=FRONT)
    b.fn('feOk', KS + 'IsValid', 250, 300)
    b.link('fe', 'ReturnValue', 'feOk', 'Object')
    b.node('feB', 'branch', 250, 0)
    b.link('feOk', 'ReturnValue', 'feB', 'Condition')
    b.get('inGame', 'bInGameplay', 500, 300, FRONT)
    b.link('fe', 'ReturnValue', 'inGame', 'self')
    b.get('waking', 'bWaking', 500, 450, FRONT)
    b.link('fe', 'ReturnValue', 'waking', 'self')
    b.fn('busy', K + 'BooleanOR', 750, 350)
    b.link('inGame', 'bInGameplay', 'busy', 'A')
    b.link('waking', 'bWaking', 'busy', 'B')
    b.fn('idle', K + 'Not_PreBool', 1000, 350)
    b.link('busy', 'ReturnValue', 'idle', 'A')
    b.set('menuOn', 'bMenuWanted', 1000, -150)
    b.link('idle', 'ReturnValue', 'menuOn', 'bMenuWanted')
    b.set('wakeOn', 'bWakeWanted', 1150, -150)
    b.link('waking', 'bWaking', 'wakeOn', 'bWakeWanted')
    b.set('menuOff', 'bMenuWanted', 1000, 150)
    b.pin('menuOff', 'bMenuWanted', 'false')
    b.set('wakeOff', 'bWakeWanted', 1150, 150)
    b.pin('wakeOff', 'bWakeWanted', 'false')
    b.chain(e, 'fe', 'feB', 'menuOn', 'wakeOn')
    b.link('feB', 'else', 'menuOff', 'execute')
    b.chain('menuOff', 'wakeOff')
    # the battle intro: the sting on the rising edge, faded out on the falling edge
    b.get('dir', 'Director', 1250, 300)
    b.fn('dirOk', KS + 'IsValid', 1250, 450)
    b.link('dir', 'Director', 'dirOk', 'Object')
    b.node('dirB', 'branch', 1300, 0)
    b.link('dirOk', 'ReturnValue', 'dirB', 'Condition')
    b.link('wakeOn', 'then', 'dirB', 'execute')
    b.link('wakeOff', 'then', 'dirB', 'execute')
    b.get('intro', 'bBattleIntroPlaying', 1550, 300, DIR_C)
    b.link('dir', 'Director', 'intro', 'self')
    b.get('lastI', 'bLastIntro', 1550, 450)
    b.fn('notLast', K + 'Not_PreBool', 1800, 450)
    b.link('lastI', 'bLastIntro', 'notLast', 'A')
    b.fn('rise', K + 'BooleanAND', 2050, 350)
    b.link('intro', 'bBattleIntroPlaying', 'rise', 'A')
    b.link('notLast', 'ReturnValue', 'rise', 'B')
    b.node('riseB', 'branch', 2050, 0)
    b.link('rise', 'ReturnValue', 'riseB', 'Condition')
    b.link('dirB', 'then', 'riseB', 'execute')
    b.get('stingC', 'Sting', 2300, 300)
    b.get('stingS', 'BattleIntroSting', 2300, 450)
    b.fn('setSting', AU + 'SetSound', 2300, -150)
    b.link('stingC', 'Sting', 'setSting', 'self')
    b.link('stingS', 'BattleIntroSting', 'setSting', 'NewSound')
    b.fn('playSting', AU + 'Play', 2550, -150, StartTime=0)
    b.link('stingC', 'Sting', 'playSting', 'self')
    b.set('seen', 'bIntroSeen', 2800, -150)
    b.pin('seen', 'bIntroSeen', 'true')
    b.fn('notIntro', K + 'Not_PreBool', 2300, 650)
    b.link('intro', 'bBattleIntroPlaying', 'notIntro', 'A')
    b.fn('fall', K + 'BooleanAND', 2550, 650)
    b.link('notIntro', 'ReturnValue', 'fall', 'A')
    b.link('lastI', 'bLastIntro', 'fall', 'B')
    b.node('fallB', 'branch', 2550, 150)
    b.link('fall', 'ReturnValue', 'fallB', 'Condition')
    b.link('riseB', 'else', 'fallB', 'execute')
    fade(b, 'stingOut', 'Sting', 2800, 150, False, 1.0)
    b.set('keepI', 'bLastIntro', 3050, 0)
    b.link('intro', 'bBattleIntroPlaying', 'keepI', 'bLastIntro')
    b.chain('riseB', 'setSting', 'playSting', 'seen', 'keepI')
    b.chain('fallB', 'stingOut', 'keepI')
    b.link('fallB', 'else', 'keepI', 'execute')
    # leaving beat 8 forgets the intro
    b.get('lb', 'LastBeat', 3300, 300)
    b.fn('is8', K + 'EqualEqual_IntInt', 3300, 450, B=8)
    b.link('lb', 'LastBeat', 'is8', 'A')
    b.node('b8', 'branch', 3300, 0)
    b.link('is8', 'ReturnValue', 'b8', 'Condition')
    b.link('keepI', 'then', 'b8', 'execute')
    b.link('dirB', 'else', 'b8', 'execute')
    b.set('unseen', 'bIntroSeen', 3550, 150)
    b.pin('unseen', 'bIntroSeen', 'false')
    b.link('b8', 'else', 'unseen', 'execute')
    # the wanted state: Menu, else Wake, else by beat
    b.get('seenG', 'bIntroSeen', 3550, 450)
    b.get('lastI2', 'bLastIntro', 3550, 600)
    b.fn('nl2', K + 'Not_PreBool', 3800, 600)
    b.link('lastI2', 'bLastIntro', 'nl2', 'A')
    b.fn('and1', K + 'BooleanAND', 3800, 450)
    b.link('is8', 'ReturnValue', 'and1', 'A')
    b.link('seenG', 'bIntroSeen', 'and1', 'B')
    b.fn('fight', K + 'BooleanAND', 4050, 450)
    b.link('and1', 'ReturnValue', 'fight', 'A')
    b.link('nl2', 'ReturnValue', 'fight', 'B')
    b.fn('c8', K + 'SelectName', 4300, 450, A='Battle', B='None')
    b.link('fight', 'ReturnValue', 'c8', 'bPickA')
    prev = 'c8'
    # beat 9 then 10 sit below 8 in the chain; built from the bottom up: 10, 9, then 8 above them
    b.fn('is10', K + 'EqualEqual_IntInt', 4050, 900, B=10)
    b.link('lb', 'LastBeat', 'is10', 'A')
    b.fn('c10', K + 'SelectName', 4300, 900, A='Ending', B='None')
    b.link('is10', 'ReturnValue', 'c10', 'bPickA')
    b.fn('is9', K + 'EqualEqual_IntInt', 4300, 1050, B=9)
    b.link('lb', 'LastBeat', 'is9', 'A')
    b.fn('c9', K + 'SelectName', 4550, 900, A='Payoff')
    b.link('c10', 'ReturnValue', 'c9', 'B')
    b.link('is9', 'ReturnValue', 'c9', 'bPickA')
    b.fn('c8b', K + 'SelectName', 4800, 450)  # beat 8: battle-or-None; otherwise the 9/10 chain
    b.link(prev, 'ReturnValue', 'c8b', 'A')
    b.link('c9', 'ReturnValue', 'c8b', 'B')
    b.link('is8', 'ReturnValue', 'c8b', 'bPickA')
    b.fn('is7', K + 'EqualEqual_IntInt', 4800, 900, B=7)
    b.link('lb', 'LastBeat', 'is7', 'A')
    b.fn('c7', K + 'SelectName', 5050, 450, A='Chase')
    b.link('c8b', 'ReturnValue', 'c7', 'B')
    b.link('is7', 'ReturnValue', 'c7', 'bPickA')
    b.fn('in16', K + 'InRange_IntInt', 5050, 900, Min=1, Max=6, InclusiveMin='true', InclusiveMax='true')
    b.link('lb', 'LastBeat', 'in16', 'Value')
    b.fn('c16', K + 'SelectName', 5300, 450, A='Explore')
    b.link('c7', 'ReturnValue', 'c16', 'B')
    b.link('in16', 'ReturnValue', 'c16', 'bPickA')
    b.fn('is0', K + 'LessEqual_IntInt', 5300, 900, B=0)  # before T1: the story screen (beat -1) and the T0 phone keep the wake bed
    b.link('lb', 'LastBeat', 'is0', 'A')
    b.get('wakeG', 'bWakeWanted', 5300, 1050)
    b.fn('wake0', K + 'BooleanOR', 5550, 900)
    b.link('is0', 'ReturnValue', 'wake0', 'A')
    b.link('wakeG', 'bWakeWanted', 'wake0', 'B')
    b.fn('cw', K + 'SelectName', 5550, 450, A='Wake')
    b.link('c16', 'ReturnValue', 'cw', 'B')
    b.link('wake0', 'ReturnValue', 'cw', 'bPickA')
    b.get('menuG', 'bMenuWanted', 5550, 1050)
    b.fn('want', K + 'SelectName', 5800, 450, A='Menu')
    b.link('cw', 'ReturnValue', 'want', 'B')
    b.link('menuG', 'bMenuWanted', 'want', 'bPickA')
    b.get('state', 'MusicState', 5800, 650)
    b.fn('chg', K + 'NotEqual_NameName', 6050, 450)
    b.get('override', 'MusicOverride', 5550, 1400)
    b.fn('overrideValid', K + 'NotEqual_NameName', 5800, 1400, B='None')
    b.link('override', 'MusicOverride', 'overrideValid', 'A')
    b.fn('journeyWant', K + 'SelectName', 6050, 1400)
    b.link('override', 'MusicOverride', 'journeyWant', 'A')
    b.link('want', 'ReturnValue', 'journeyWant', 'B')
    b.link('overrideValid', 'ReturnValue', 'journeyWant', 'bPickA')
    b.link('journeyWant', 'ReturnValue', 'chg', 'A')
    b.link('state', 'MusicState', 'chg', 'B')
    b.node('chgB', 'branch', 6050, 0)
    b.link('chg', 'ReturnValue', 'chgB', 'Condition')
    b.link('b8', 'then', 'chgB', 'execute')
    b.link('unseen', 'then', 'chgB', 'execute')
    b.set('keepS', 'MusicState', 6300, 0)
    b.link('journeyWant', 'ReturnValue', 'keepS', 'MusicState')
    b.link('chgB', 'then', 'keepS', 'execute')
    # the crossfade: out on the active component, in on the other; the active flag flips
    b.get('tracks', 'Tracks', 6300, 650)
    b.fn('track', '/Script/Engine.BlueprintMapLibrary:Map_Find', 6550, 650)
    b.link('tracks', 'Tracks', 'track', 'TargetMap')
    b.link('journeyWant', 'ReturnValue', 'track', 'Key')
    b.get('useB', 'bMusicB', 6300, 300)
    b.node('which', 'branch', 6550, 0)
    b.link('useB', 'bMusicB', 'which', 'Condition')
    b.link('keepS', 'then', 'which', 'execute')
    for side, (old, new, flip) in (('A', ('Music', 'Music2', 'true')), ('B', ('Music2', 'Music', 'false'))):
        y = -300 if side == 'A' else 500
        fade(b, 'out' + side, old, 6800, y, False, 2.5)
        b.node('has' + side, 'branch', 7050, y)
        b.link('track', 'ReturnValue', 'has' + side, 'Condition')
        b.get('nc' + side, new, 7300, y + 250)
        b.fn('set' + side, AU + 'SetSound', 7300, y)
        b.link('nc' + side, new, 'set' + side, 'self')
        b.link('track', 'Value', 'set' + side, 'NewSound')
        fade(b, 'in' + side, new, 7550, y, True, 3.0, 1.0)
        b.set('flip' + side, 'bMusicB', 7800, y)
        b.pin('flip' + side, 'bMusicB', flip)
        b.chain('out' + side, 'has' + side, 'set' + side, 'in' + side, 'flip' + side)
    b.link('which', 'else', 'outA', 'execute')  # bMusicB false: Music is active
    b.link('which', 'then', 'outB', 'execute')
    done(b, 'Music: title, wake, beats, battle intro')


def composure():
    """UpdateComposure: the frightened-breathing bed while the fight is on and Composure is under 30 % of the leader's
    StartComposure; fades in 2 s on the way down, out 2 s on the way back (or when the fight ends)."""
    b, e = graph('UpdateComposure')
    enc_c = '/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'
    opp_c = '/Game/FoA/Gameplay/Encounter/PDA_Opponent.PDA_Opponent_C'
    b.fn('enc', GS + 'GetActorOfClass', 0, 300, ActorClass=enc_c)
    b.fn('encOk', KS + 'IsValid', 250, 300)
    b.link('enc', 'ReturnValue', 'encOk', 'Object')
    b.node('encB', 'branch', 250, 0)
    b.link('encOk', 'ReturnValue', 'encB', 'Condition')
    b.get('lead', 'Leader', 500, 300, enc_c)
    b.link('enc', 'ReturnValue', 'lead', 'self')
    b.fn('leadOk', KS + 'IsValid', 500, 450)
    b.link('lead', 'Leader', 'leadOk', 'Object')
    b.node('leadB', 'branch', 500, 0)
    b.link('leadOk', 'ReturnValue', 'leadB', 'Condition')
    b.get('act', 'bActive', 750, 300, enc_c)
    b.link('enc', 'ReturnValue', 'act', 'self')
    b.get('cmp', 'Composure', 750, 450, enc_c)
    b.link('enc', 'ReturnValue', 'cmp', 'self')
    b.get('start', 'StartComposure', 750, 600, opp_c)
    b.link('lead', 'Leader', 'start', 'self')
    b.fn('c10', K + 'Multiply_IntInt', 1000, 450, B=10)
    b.link('cmp', 'Composure', 'c10', 'A')
    b.fn('s3', K + 'Multiply_IntInt', 1000, 600, B=3)
    b.link('start', 'StartComposure', 's3', 'A')
    b.fn('low', K + 'Less_IntInt', 1250, 450)
    b.link('c10', 'ReturnValue', 'low', 'A')
    b.link('s3', 'ReturnValue', 'low', 'B')
    b.fn('want', K + 'BooleanAND', 1500, 400)
    b.link('act', 'bActive', 'want', 'A')
    b.link('low', 'ReturnValue', 'want', 'B')
    edge(b, 'eLow', 'bool', 'bLastLowComposure', None, 1750, 0, 'want', 'ReturnValue')
    b.node('dirn', 'branch', 2050, -150)
    b.link('want', 'ReturnValue', 'dirn', 'Condition')
    b.link('eLowS', 'then', 'dirn', 'execute')
    fade(b, 'in', 'Composure', 2300, -300, True, 2.0, 0.6)
    fade(b, 'out', 'Composure', 2300, 100, False, 2.0)
    b.link('dirn', 'then', 'in', 'execute')
    b.link('dirn', 'else', 'out', 'execute')
    b.chain(e, 'enc', 'encB', 'leadB', 'eLow')
    done(b, 'Composure low')


def events():
    b = Batch(P, 'EventGraph')
    ns, _ = inspect(P, 'EventGraph')
    if ns:
        b.ops.append(dict(op='remove', node_ids=[n['node_id'] for n in ns]))
    b.ops.append(dict(op='add_event', ref='begin', event_name='ReceiveBeginPlay', x=0, y=0))
    timer(b, 'poll', 'Poll', 300, 0, 0.1, True)  # 0.1 s: the battle-intro sting lands within a few frames of the sequence
    timer(b, 'settle', 'Settle', 600, 0, 9.0)
    b.chain('begin', 'poll', 'settle')
    done(b, 'Start listening')


STEPS = {'assets': assets, 'music': music, 'composure': composure, 'poll': poll, 'cues': cues, 'events': events, 'presence': presence}  # cues() includes presence

if __name__ == '__main__':
    assert not call('editor_get_state')['pie_running'], 'PIE is running: wait'
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    lease = h.lease_acquire(h.agent_id(), ['asset:' + P], ttl_s=180, wait_s=900)
    try:
        for name, step in STEPS.items():
            if which == name or (which == 'all' and name != 'presence'):
                step()
    finally:
        h.release(h.agent_id(), lease)
