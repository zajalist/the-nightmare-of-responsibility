"""Story lane, in PIE (run_chase_final.py pie_battle_intro, one EXCLUSIVE window): LS_BattleIntro on the real path.
  menu -> Wake up -> intro -> skip -> T0 phone -> events to T7 -> fixture EnterBeat(8): its hook is the real
  StartShirtFight -> ShowNightmare -> PlayBattleIntro (full or short, from GI Knows.BattleIntro) -> the sequence with the
  real pawn bound -> BattleIntroDone -> the encounter. FOA_SKIP=1 holds the skip instead (SkipWakeUp at 5 s).
Every 0.25 s from the play: a shot plus the view target, the encounter state, the pawn and the input state.
Shots: Saved/StoryShots/battle_intro/*.png. Result: Saved/StoryShots/battle_intro.json."""
import importlib
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/battle_intro.json')
SHOTS = 'P:/FoA/Saved/StoryShots/battle_intro'
SKIP = os.environ.get('FOA_SKIP') == '1'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, play=None, skipped=False)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
ENC = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    vt = pc.get_view_target()
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), playing=prop(D, 'bBattleIntroPlaying'),
               short=prop(D, 'bBattleIntroShort'), state=str(prop(ENC, 'BattleState')), active=prop(ENC, 'bActive'),
               view=vt.get_name() if vt else None, pawn=[round(v) for v in P.get_actor_location().to_tuple()],
               yaw=round(P.get_actor_rotation().yaw), move_ignored=pc.is_move_input_ignored(), **kw)
    if S['play'] is not None:
        row['since_play'] = round(time.time() - S['play'], 2)
    S['rows'].append(row)
    unreal.log('[battle_intro] ' + json.dumps(row, default=str))
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, skip=SKIP, rows=S['rows']), indent=1, default=str))
    unreal.log('[battle_intro] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
        if S['play'] is not None:
            since = time.time() - S['play']
            if SKIP and not S['skipped'] and since > 5.0:
                D.call_method('SkipWakeUp', ()); S['skipped'] = True; log('skip')
            if time.time() - S['shot'] >= 0.25:
                S['n'] += 1
                cmd('Shot showui filename=%s/%03d_t%03d.png -nosuffix' % (SHOTS, S['n'], int(since * 10)))
                S['shot'] = time.time()
                log('frame', shot=S['n'])
            if since > 20.0 or (prop(ENC, 'bActive') and not prop(D, 'bBattleIntroPlaying') and since > 2.0 and
                                str(prop(ENC, 'BattleState')) not in ('None', 'Intro')):
                return finish('intro_watched')
            return
        if time.time() < S['after']:
            return
        ph = S['phase']
        if ph == 0:
            cmd('ke * OnSplashFinished'); wait(0.8)
        elif ph == 1:
            cmd('ke * OnTitleConfirmed'); wait(1.2)
        elif ph == 2:
            cmd('ke * WakeUp'); wait(6.2)
        elif ph == 3:
            cmd('ke * OnStoryFinished'); wait(2.6)
        elif ph == 4:
            cmd('ke * SkipWakeUp'); wait(0.6)
        elif ph == 5:
            if prop(D, 'BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.6)
        elif ph == 6:
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            log('to_t7'); wait(0.6)
        elif ph == 7:
            if prop(D, 'BeatIndex') != 7:
                return
            D.call_method('EnterBeat', (8,)); log('enter_t8_fixture'); wait(0.0)
        elif ph == 8:
            if not prop(D, 'bBattleIntroPlaying'):
                return
            S['play'] = time.time(); log('intro_playing')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
