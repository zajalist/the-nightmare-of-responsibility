"""BP_BeatDirector plays LS_BattleIntro (main's GO 2026-11-10, the "Nightmare speaks" version) between the formed sand
figure and the T8 fight. Hayba only; idempotent.
  StartShirtFight: ... ExitTopDownCut -> ShowNightmare(NightmareT8) -> PlayBattleIntro (StartShirtEncounter moves to the end).
  PlayBattleIntro: full the first time, LS_BattleIntro_Short once GI_FoA knows Knows.BattleIntro (learned here, so a
      morning that never reached the fight still gets the full one). HUD hidden, pawn cinematic and still, sequence
      player with the pawn bound to the "Player" tag, the cue timers, and BattleIntroDone at the sequence's end.
  BI_* cue functions: one subtitle line each (ShowIntroLine -> BP_FoAFrontEnd.ShowCinematicSubtitle, UI lane) or one
      sand burst / dream-director pulse.
  BattleIntroDone (end or skip, once): timers off, subtitle off, pawn back, HUD back, StartShirtEncounter under the
      sequence's held black, camera-cut flag, BP_FoAPlayer.HandoffFadeUp.
  SkipWakeUp (hold Space / gamepad A 0.8 s, the wake-up's control): during the intro it jumps the sequence to its end.
  python Tools/Unreal/flow/patch_battle_intro.py [subtitles]   (subtitles: wire ShowIntroLine once the UI call exists)"""
import json
import os
import sys
from pathlib import Path

sys.path[:0] = ['P:/FoA/Tools/Unreal', 'P:/FoA/Tools/Unreal/player']
import hayba_call as h  # noqa: E402
from held_tool_graphs import Batch, inspect, find  # noqa: E402

P = '/Game/FoA/Gameplay/BP_BeatDirector'
C = P + '.BP_BeatDirector_C'
GI_C = '/Game/FoA/Gameplay/GI_FoA.GI_FoA_C'
FRONT = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
PLAYER = '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C'
SANDFX = '/Game/FoA/VFX/Sand/BPL_SandFX.BPL_SandFX_C'
DREAM = '/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C'
LS = '/Game/FoA/Cinematics/BattleIntro/'
GS, KS, K = '/Script/Engine.GameplayStatics:', '/Script/Engine.KismetSystemLibrary:', '/Script/Engine.KismetMathLibrary:'
LSP = '/Script/LevelSequence.LevelSequencePlayer:'
MSP = '/Script/MovieScene.MovieSceneSequencePlayer:'
FULL_S, SHORT_S = 15.9, 4.0
# (function, time, kind, args): kind 'line' = (text, seconds, speaker); 'burst' = (x, y, z, scale); 'streak'; 'glitch'
FULL = [('BI_L01', 2.0, 'line', ("No. No no no. I had it.", 1.9, 'Him')),
        ('BI_FX_Collapse', 4.5, 'burst', (-15.0, -345.0, 0.0, 1.0)),
        ('BI_L02', 4.4, 'line', ("It's just a shirt. It's just a shirt.", 1.8, 'Him')),
        ('BI_N01', 6.2, 'line', ("Get dressed.", 0.8, 'Nightmare')),
        ('BI_FX_Pants', 6.95, 'burst', (-200.0, -30.0, 0.0, 0.6)),
        ('BI_FX_Socks', 7.7, 'burst', (-200.0, -100.0, 0.0, 0.5)),
        ('BI_FX_Tie', 8.35, 'burst', (-200.0, -60.0, 0.0, 0.6)),
        ('BI_FX_Streak', 9.1, 'streak', ()),
        ('BI_N02', 9.5, 'line', ("The bed is still warm.", 1.4, 'Nightmare')),
        ('BI_FX_Falter', 10.3, 'glitch', ()),
        ('BI_N03', 11.3, 'line', ("Take your time.", 1.0, 'Nightmare')),
        ('BI_L03', 12.6, 'line', ("Seventeen days.", 1.0, 'Him')),
        ('BI_L04', 13.7, 'line', ("Not eighteen.", 0.8, 'Him')),
        ('BI_L05', 14.6, 'line', ("Okay. Shirt first.", 0.9, 'Him'))]
SHORT = [('BI_FX_CollapseShort', 0.1, 'burst', (-15.0, -345.0, 0.0, 1.0)),
         ('BI_L06', 2.1, 'line', ("Again. Shirt first.", 1.2, 'Him'))]
os.environ['HAYBA_AGENT_ID'] = 'story'


def call(name, **args):
    r = h.call(name, args, owner='story', timeout=60)
    assert r.get('ok'), r
    return r.get('data', {})


def has(graph):
    return h.call('blueprint_inspect_graph', {'path': P, 'graph_name': graph}).get('ok')


def ensure(fn, inputs=()):
    if not has(fn):
        call('blueprint_add_function', path=P, function_name=fn, inputs=list(inputs))
    ns, _ = inspect(P, fn)
    return ns, find(ns, fn)


def show_line(subtitles):
    ns, e = ensure('ShowIntroLine', [dict(name='Line', type='text'), dict(name='Seconds', type='float'),
                                     dict(name='Speaker', type='name')])
    if any(n['title'] == 'ShowCinematicSubtitle' for n in ns):
        return 'kept'
    if not subtitles:
        return 'stub (waiting for BP_FoAFrontEnd.ShowCinematicSubtitle)'
    b = Batch(P, 'ShowIntroLine')
    b.fn('fe', GS + 'GetActorOfClass', 250, 250, ActorClass=FRONT)
    b.fn('valid', KS + 'IsValid', 500, 250)
    b.link('fe', 'ReturnValue', 'valid', 'Object')
    b.node('ok', 'branch', 300, 0)
    b.link('valid', 'ReturnValue', 'ok', 'Condition')
    b.fn('say', FRONT + ':ShowCinematicSubtitle', 600, 0)
    b.link('fe', 'ReturnValue', 'say', 'self')
    for p in ('Line', 'Seconds', 'Speaker'):
        b.link(e, p, 'say', p)
    b.link(e, 'then', 'fe', 'execute')
    b.chain('fe', 'ok')
    b.link('ok', 'then', 'say', 'execute')
    b.comment('A line over the battle intro', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'wired'


def cue(fn, kind, args):
    ns, e = ensure(fn)
    if len(ns) > 1:
        return 'kept'
    b = Batch(P, fn)
    if kind == 'line':
        b.fn('txt', '/Script/Engine.KismetTextLibrary:Conv_StringToText', 200, 250, InString=args[0])
        b.fn('show', C + ':ShowIntroLine', 450, 0, Seconds=args[1], Speaker=args[2])
        b.link('txt', 'ReturnValue', 'show', 'Line')
        b.link(e, 'then', 'show', 'execute')
    elif kind == 'burst':
        b.fn('at', K + 'MakeVector', 200, 250, X=args[0], Y=args[1], Z=args[2])
        b.fn('burst', SANDFX + ':SpawnSandBurst', 450, 0, Scale=args[3])
        b.link('at', 'ReturnValue', 'burst', 'Location')
        b.link(e, 'then', 'burst', 'execute')
    else:
        b.fn('dd', GS + 'GetActorOfClass', 200, 250, ActorClass=DREAM)
        b.fn('valid', KS + 'IsValid', 450, 250)
        b.link('dd', 'ReturnValue', 'valid', 'Object')
        b.node('ok', 'branch', 450, 0)
        b.link('valid', 'ReturnValue', 'ok', 'Condition')
        if kind == 'streak':
            b.fn('fx', DREAM + ':PulseShiftStreak', 700, 0, Intensity=1.0, Seconds=0.6)
        else:
            b.fn('fx', DREAM + ':TriggerGlitchBurst', 700, 0, Strength=0.3, Seconds=0.25)
        b.link('dd', 'ReturnValue', 'fx', 'self')
        b.link(e, 'then', 'dd', 'execute')
        b.chain('dd', 'ok')
        b.link('ok', 'then', 'fx', 'execute')
    b.run()
    return 'built'


def play():
    ns, e = ensure('PlayBattleIntro')
    if any(n['title'] == 'CreateLevelSequencePlayer' for n in ns):
        return 'kept'
    b = Batch(P, 'PlayBattleIntro')
    b.fn('gi', C + ':GetFoAGI', 0, 300)
    b.fn('known', GI_C + ':HasKnowledge', 250, 300, Flag='Knows.BattleIntro')
    b.link('gi', 'GI', 'known', 'self')
    b.set('short', 'bBattleIntroShort', 300, 0)
    b.link('known', 'Known', 'short', 'bBattleIntroShort')
    b.fn('learn', GI_C + ':Learn', 550, 0, Flag='Knows.BattleIntro')
    b.link('gi', 'GI', 'learn', 'self')
    b.fn('hud', C + ':SetStoryHUDHidden', 800, 0, Hidden='true')
    b.fn('cin', C + ':PlayerCinematic', 1050, 0, Enable='true')
    b.fn('pawn', GS + 'GetPlayerCharacter', 1050, 300, PlayerIndex=0)
    b.get('cm', 'CharacterMovement', 1300, 300, '/Script/Engine.Character')
    b.link('pawn', 'ReturnValue', 'cm', 'self')
    b.fn('still', '/Script/Engine.CharacterMovementComponent:DisableMovement', 1300, 0)
    b.link('cm', 'CharacterMovement', 'still', 'self')
    b.fn('nocol', '/Script/Engine.Actor:SetActorEnableCollision', 1550, 0, bNewActorEnableCollision='false')
    b.link('pawn', 'ReturnValue', 'nocol', 'self')
    b.fn('which', K + 'SelectObject', 1550, 300, A=LS + 'LS_BattleIntro_Short.LS_BattleIntro_Short',
         B=LS + 'LS_BattleIntro.LS_BattleIntro')
    b.link('known', 'Known', 'which', 'bSelectA')
    b.fn('mk', LSP + 'CreateLevelSequencePlayer', 1800, 0,
         Settings='(bDisableMovementInput=True,bDisableLookAtInput=True,bHideHud=True)')
    b.node('seq', 'cast', 1700, 0, class_path='/Script/LevelSequence.LevelSequence')
    b.link('which', 'ReturnValue', 'seq', 'Object')
    b.link('seq', 'AsLevel Sequence', 'mk', 'LevelSequence')
    b.set('keep', 'BattleIntroPlayer', 2100, 0)
    b.link('mk', 'ReturnValue', 'keep', 'BattleIntroPlayer')
    b.node('arr', 'make_array', 2100, 300)
    b.link('pawn', 'ReturnValue', 'arr', '[0]')
    b.fn('bind', '/Script/LevelSequence.LevelSequenceActor:SetBindingByTag', 2400, 0, BindingTag='Player',
         bAllowBindingsFromAsset='false')
    b.link('mk', 'OutActor', 'bind', 'self')
    b.link('arr', 'Array', 'bind', 'Actors')
    b.set('on', 'bBattleIntroPlaying', 2700, 0)
    b.pin('on', 'bBattleIntroPlaying', 'true')
    b.fn('go', MSP + 'Play', 2950, 0)
    b.link('keep', 'Output_Get', 'go', 'self')
    b.node('ver', 'branch', 3200, 0)
    b.link('known', 'Known', 'ver', 'Condition')
    b.link(e, 'then', 'short', 'execute')
    b.chain('short', 'learn', 'hud', 'cin', 'still', 'nocol', 'seq', 'mk', 'keep', 'bind', 'on', 'go', 'ver')
    prev = None
    for i, (fn, t, _, _) in enumerate(FULL + [('BattleIntroDone', FULL_S, None, None)]):
        b.fn('f%d' % i, KS + 'K2_SetTimer', 3500 + 250 * i, 0, FunctionName=fn, Time=t, bLooping='false')
        b.link(prev or 'ver', 'then' if prev else 'else', 'f%d' % i, 'execute')
        prev = 'f%d' % i
    prev = None
    for i, (fn, t, _, _) in enumerate(SHORT + [('BattleIntroDone', SHORT_S, None, None)]):
        b.fn('s%d' % i, KS + 'K2_SetTimer', 3500 + 250 * i, 400, FunctionName=fn, Time=t, bLooping='false')
        b.link(prev or 'ver', 'then', 's%d' % i, 'execute')
        prev = 's%d' % i
    b.comment('Play the battle intro', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built'


def done():
    ns, e = ensure('BattleIntroDone')
    if any(n['title'] == 'StartShirtEncounter' for n in ns):
        return 'kept'
    b = Batch(P, 'BattleIntroDone')
    b.get('on', 'bBattleIntroPlaying', 0, 300)
    b.node('once', 'branch', 250, 0)
    b.link('on', 'bBattleIntroPlaying', 'once', 'Condition')
    b.set('off', 'bBattleIntroPlaying', 500, 0)
    b.pin('off', 'bBattleIntroPlaying', 'false')
    b.link(e, 'then', 'once', 'execute')
    b.link('once', 'then', 'off', 'execute')
    prev = 'off'
    for i, fn in enumerate(sorted({c[0] for c in FULL + SHORT} | {'BattleIntroDone'})):
        b.fn('c%d' % i, KS + 'K2_ClearTimer', 750 + 200 * i, 0, FunctionName=fn)
        b.chain(prev, 'c%d' % i)
        prev = 'c%d' % i
    x = 750 + 200 * (i + 1)
    b.fn('fe', GS + 'GetActorOfClass', x, 300, ActorClass=FRONT)
    b.fn('fev', KS + 'IsValid', x + 250, 300)
    b.link('fe', 'ReturnValue', 'fev', 'Object')
    b.node('feok', 'branch', x, 0)
    b.link('fev', 'ReturnValue', 'feok', 'Condition')
    b.chain(prev, 'fe', 'feok')
    sub = h.call('blueprint_inspect_graph', {'path': '/Game/FoA/UI/Framework/BP_FoAFrontEnd', 'graph_name': 'HideCinematicSubtitle'}).get('ok')
    if sub:
        b.fn('hide', FRONT + ':HideCinematicSubtitle', x + 250, 0)
        b.link('fe', 'ReturnValue', 'hide', 'self')
        b.link('feok', 'then', 'hide', 'execute')
    b.fn('pawn', GS + 'GetPlayerCharacter', x + 500, 300, PlayerIndex=0)
    b.get('cm', 'CharacterMovement', x + 750, 300, '/Script/Engine.Character')
    b.link('pawn', 'ReturnValue', 'cm', 'self')
    b.fn('walk', '/Script/Engine.CharacterMovementComponent:SetMovementMode', x + 750, 0, NewMovementMode='MOVE_Walking')
    b.link('cm', 'CharacterMovement', 'walk', 'self')
    b.fn('col', '/Script/Engine.Actor:SetActorEnableCollision', x + 1000, 0, bNewActorEnableCollision='true')
    b.link('pawn', 'ReturnValue', 'col', 'self')
    b.fn('cin', C + ':PlayerCinematic', x + 1250, 0, Enable='false')
    b.fn('hud', C + ':SetStoryHUDHidden', x + 1500, 0, Hidden='false')
    b.fn('fight', C + ':StartShirtEncounter', x + 1750, 0)
    b.fn('pc', GS + 'GetPlayerCameraManager', x + 2000, 300, PlayerIndex=0)
    b.fn('cut', '/Script/Engine.PlayerCameraManager:SetGameCameraCutThisFrame', x + 2000, 0)
    b.link('pc', 'ReturnValue', 'cut', 'self')
    b.node('me', 'cast', x + 2250, 0, class_path=PLAYER)
    b.link('pawn', 'ReturnValue', 'me', 'Object')
    b.fn('up', PLAYER + ':HandoffFadeUp', x + 2500, 0)
    b.link('me', 'AsBP Fo APlayer', 'up', 'self')
    if sub:
        b.link('hide', 'then', 'walk', 'execute')
    b.link('feok', 'else', 'walk', 'execute')
    if not sub:
        b.link('feok', 'then', 'walk', 'execute')
    b.chain('walk', 'col', 'cin', 'hud', 'fight', 'cut', 'me', 'up')
    b.comment('Into the fight, under the black', [o['ref'] for o in b.ops if o.get('op') == 'add_node'])
    b.run()
    return 'built (subtitle hide %s)' % ('wired' if sub else 'pending')


def skip():
    """SkipWakeUp (the hold-to-skip timer's target): during the battle intro, jump its sequence to the end instead."""
    ns, es = inspect(P, 'EventGraph')
    if any(n['title'] == 'Get bBattleIntroPlaying' for n in ns):
        return 'kept'
    ev = next(n['node_id'] for n in ns if n['title'].replace(' ', '') in ('SkipWakeUp', 'CustomEventSkipWakeUp', 'SkipWakeUpCustomEvent')
              or (n['title'].startswith('Skip Wake Up') or n['title'] == 'SkipWakeUp'))
    first = next(x for x in es if x['from_node'] == ev and x['from_pin'] == 'then')
    b = Batch(P, 'EventGraph')
    b.get('on', 'bBattleIntroPlaying', 200, -300)
    b.node('intro', 'branch', 250, -450)
    b.link('on', 'bBattleIntroPlaying', 'intro', 'Condition')
    b.get('sp', 'BattleIntroPlayer', 450, -300)
    b.fn('end', MSP + 'GoToEndAndStop', 500, -500)
    b.link('sp', 'BattleIntroPlayer', 'end', 'self')
    b.fn('done', C + ':BattleIntroDone', 800, -500)
    b.cut(ev, 'then', first['to_node'], first['to_pin'])
    b.link(ev, 'then', 'intro', 'execute')
    b.link('intro', 'then', 'end', 'execute')
    b.chain('end', 'done')
    b.link('intro', 'else', first['to_node'], first['to_pin'])
    b.comment('Skip the battle intro', ['on', 'intro', 'sp', 'end', 'done'])
    b.run()
    return 'built'


def hook():
    ns, es = inspect(P, 'StartShirtFight')
    if any(n['title'] == 'PlayBattleIntro' for n in ns):
        return 'kept'
    xc, se, sn = find(ns, 'ExitTopDownCut'), find(ns, 'StartShirtEncounter'), find(ns, 'ShowNightmare')
    assert any(x['from_node'] == xc and x['to_node'] == se for x in es), 'unexpected StartShirtFight chain'
    b = Batch(P, 'StartShirtFight')
    b.cut(xc, 'then', se, 'execute')
    b.cut(se, 'then', sn, 'execute')
    b.ops.append(dict(op='remove', node_ids=[se]))
    b.link(xc, 'then', sn, 'execute')
    b.fn('intro', C + ':PlayBattleIntro', 1100, 0)
    b.link(sn, 'then', 'intro', 'execute')
    b.run()
    return 'StartShirtFight plays the intro; BattleIntroDone starts the encounter'


if __name__ == '__main__':
    subtitles = 'subtitles' in sys.argv
    assert not h.call('editor_get_state', {})['data']['pie_running'], 'PIE running'
    token = h.lease_acquire('story', ['asset:' + P], ttl_s=600, wait_s=240)
    try:
        for name, t in (('BattleIntroPlayer', 'object:/Script/LevelSequence.LevelSequencePlayer'),
                        ('bBattleIntroPlaying', 'bool'), ('bBattleIntroShort', 'bool')):
            call('blueprint_add_variable', path=P, variable_name=name, variable_type=t, category='Story|Battle intro',
                 update_existing=True)
        report = dict(Line=show_line(subtitles))
        for fn, _, kind, args in FULL + SHORT:
            report[fn] = cue(fn, kind, args)
        report.update(Done=done(), Play=play(), Skip=skip(), Hook=hook())
        Path('P:/FoA/Saved/StoryShots/battle_intro_patch.json').write_text(json.dumps(report, indent=1))
        print('battle intro', json.dumps(report))
    finally:
        h.release('story', token)
