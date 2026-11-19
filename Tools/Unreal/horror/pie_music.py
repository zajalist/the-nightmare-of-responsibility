"""Audio lane: PIE proof of the level-1 music (BP_RoomAudio.UpdateMusic) on story's real path, isolated from the
player's save (proof_save). Title (menu loop) -> Wake up (fade out) -> story/skip -> T0 -> events to T7 -> EnterBeat 8
(StartShirtFight -> PlayBattleIntro: the sting) -> BattleIntroDone (battle loop fades in) -> 8 s of fight -> EncounterWon
(T9: battle loop fades out). Logs every change of FOA_RoomAudio's MusicState and bLastIntro with its epoch, and each
step. Pair with record_audio.sh (FOA_DRIVER=Tools/Unreal/horror/pie_music.py). Writes Saved/HorrorShots/<run>_timeline.json."""
import importlib
import json
import os
import sys
import time

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

RUN = os.environ.get('FOA_RUN', 'music')
OUT = f'P:/FoA/Saved/HorrorShots/{RUN}_timeline.json'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
PROOF = proof_save.isolate(w)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))


D = actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
RA = actor('/Game/FoA/Audio/BP_RoomAudio.BP_RoomAudio_C')
S = dict(t0=time.time(), log=[], h=None, done=False, phase=0, until=0.0, music=None, intro=None, mark=None)
# (command or callable, then wait s); a callable returning False holds the step
FULL = os.environ.get('FOA_MUSIC_PASS') != 'first'  # every beat's cue; FOA_MUSIC_PASS=first: the first pass, title to fight
STEPS = ([('ke * OnSplashFinished', 0.8), ('ke * OnTitleConfirmed', 4.0), ('ke * WakeUp', 4.0), ('ke * OnStoryFinished', 1.5),
          ('ke * SkipWakeUp', 0.6), (lambda: D.get_editor_property('BeatIndex') == 0, 2.0), ('ke * ReportEvent PhoneWakeUp', 0.0),
          ('ke * ClosePhone', 5.0), ('events', 0.6), (lambda: D.get_editor_property('BeatIndex') == 7, 5.0), ('enter8', 0.0),
          (lambda: not D.get_editor_property('bBattleIntroPlaying') and S['intro'] is False, 4.0),
          ('ke * ReportEvent EncounterWon', 5.0), ('ke * ReportEvent PayoffEnded', 6.0), ('end', 0.0)] if FULL else
         [('ke * OnSplashFinished', 0.8), ('ke * OnTitleConfirmed', 6.0),  # the title holds 6 s: the menu loop fades in
          ('ke * WakeUp', 5.0), ('ke * OnStoryFinished', 2.0), ('ke * SkipWakeUp', 0.6),
          (lambda: D.get_editor_property('BeatIndex') == 0, 0.0), ('ke * ReportEvent PhoneWakeUp', 0.0), ('ke * ClosePhone', 0.6),
          ('events', 0.6), (lambda: D.get_editor_property('BeatIndex') == 7, 0.0), ('enter8', 0.0),
          (lambda: not D.get_editor_property('bBattleIntroPlaying') and S['intro'] is False, 8.0),
          ('ke * ReportEvent EncounterWon', 5.0), ('end', 0.0)])


def log(kind, **kw):
    S['log'].append(dict(t=round(time.time() - S['t0'], 3), epoch=round(time.time(), 3), kind=kind,
                         beat=D.get_editor_property('BeatIndex'), **kw))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        log('restore_failed', what=repr(exc))
    log('end', reason=reason)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1, default=str)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c)


def tick(_dt):
    try:
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        now = time.time()
        m, i = str(RA.get_editor_property('MusicState')), bool(RA.get_editor_property('bLastIntro'))
        if m != S['music']:
            log('music', state=m)
            S['music'] = m
        if i != S['intro']:
            log('sting' if i else 'intro_end', intro=i)
            S['intro'] = i
        if now - S['t0'] > 57:
            return finish('cap')
        if now < S['until'] or S['phase'] >= len(STEPS):
            return
        step, wait = STEPS[S['phase']]
        if callable(step):
            if not step():
                return
        elif step == 'events':
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
        elif step == 'enter8':
            D.call_method('EnterBeat', (8,))
        elif step == 'end':
            return finish('done')
        else:
            cmd(step)
        log('step', what=step if isinstance(step, str) else 'wait')
        S['phase'] += 1
        S['until'] = now + wait
    except Exception as exc:  # noqa: BLE001
        log('error', what=repr(exc)[:300])
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
print('music proof scheduled ->', OUT)
