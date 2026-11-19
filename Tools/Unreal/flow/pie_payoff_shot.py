"""Story lane, in PIE (run_chase_final.py pie_payoff_shot, one EXCLUSIVE window): the T9 hero shot (QA B3).
  menu -> Wake up -> intro -> skip -> T0 phone -> events to T7 -> fixture EnterBeat(8) (its hook is the real
  StartShirtFight, which now finishes the top-down exit on the spot) -> fixture: the encounter's own SetState('Victory') -> everything after is the
  shipped path: the victory shot with its subtitle, EndEncounter, SuitUp cuts to PayoffCam (low three-quarter, colour
  floods in, suit lands), 2.5 s hold, 0.2 s dip, first person, colour drains, T10.
Every 0.1 s from the victory: a shot plus the view target, the face's visibility and the input state, so the strip can
show that no frame blends through the body and that the head is visible in the hero shot.
Shots: Saved/StoryShots/payoff_shot/*.png. Result: Saved/StoryShots/payoff_shot.json."""
import json
import os
import time
from pathlib import Path

import unreal
import importlib
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  the player's save stays untouched (main's rule 2026-11-10)
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/payoff_shot.json')
SHOTS = 'P:/FoA/Saved/StoryShots/payoff_shot'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, won=None)


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
    face = prop(P, 'Face')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), state=str(prop(ENC, 'BattleState')),
               active=prop(ENC, 'bActive'), view=vt.get_class().get_name() if vt else None,
               face=face.is_visible() if face else None, cinematic=prop(P, 'bCinematic'),
               move_ignored=pc.is_move_input_ignored(), **kw)
    if S['won'] is not None:
        row['since_victory'] = round(time.time() - S['won'], 2)
    S['rows'].append(row)
    unreal.log('[payoff_shot] ' + json.dumps(row, default=str))
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:  # back to the player's slot before the runner stops PIE
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001  never lose the run's outputs over the restore
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    cam = prop(D, 'PayoffCam')
    OUT.write_text(json.dumps(dict(reason=reason, payoff_cam=cam.get_actor_location().to_tuple() if cam else None,
                                   rows=S['rows']), indent=1, default=str))
    unreal.log('[payoff_shot] finished ' + reason)


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
        el = time.time() - S['t0']
        if el > 46:
            return finish('timeout_phase_%d' % S['phase'])
        if S['won'] is not None and time.time() - S['shot'] >= 0.1:
            S['n'] += 1
            since = time.time() - S['won']
            cmd('Shot showui filename=%s/%03d_t%03d.png -nosuffix' % (SHOTS, S['n'], int(since * 10)))
            S['shot'] = time.time()
            log('frame', shot=S['n'])
            if since > 9.0 or (prop(D, 'BeatIndex') == 10 and since > 7.0):
                return finish('payoff_watched')
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
            # fixture: T8 entered directly (ShirtTaken is only accepted from the clothing search's stage 9); its hook is
            # the real StartShirtFight, which finishes the top-down exit on the spot and starts the encounter
            D.call_method('EnterBeat', (8,)); log('enter_t8_fixture'); wait(0.4)
        elif ph == 8:
            if not prop(ENC, 'bActive'):
                return
            log('fight_started'); wait(1.0)
        elif ph == 9:  # fixture: the encounter's own state change; the rest is the shipped path
            ENC.call_method('SetState', ('Victory',))
            S['won'] = time.time()
            log('victory_fixture'); wait(60)
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
