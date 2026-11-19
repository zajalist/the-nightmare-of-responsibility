"""Story lane, in PIE (run_chase_final.py pie_restart_day, one EXCLUSIVE window): QA #18. Every morning runs the same T0.
  menu -> Wake up -> intro -> skip -> the first morning's T0 phone (it must open by itself) -> Wake up/close (T1)
  -> the pause menu's Restart Day (BP_FoAFrontEnd.RestartDay, what its confirm button calls) -> rollover card ->
  StartNextMorning -> LS_WakeUp (skipped) -> the new morning's T0: the phone must buzz and open by itself again,
  at BeatIndex 0, on the lock screen (the clock's first-open stamp resets when BeatIndex goes back to -1).
Shots every 0.25 s from the restart: Saved/StoryShots/restart_day/*.png. Result: Saved/StoryShots/restart_day.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/restart_day.json')
SHOTS = 'P:/FoA/Saved/StoryShots/restart_day'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, restart=None, first=None)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
FE = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
GI = unreal.GameplayStatics.get_game_instance(w)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    vt = pc.get_view_target()
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), day=prop(GI, 'DayCount'),
               view=vt.get_class().get_name() if vt else None, **kw)
    if S['restart'] is not None:
        row['since_restart'] = round(time.time() - S['restart'], 2)
    S['rows'].append(row)
    unreal.log('[restart_day] ' + json.dumps(row, default=str))
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
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[restart_day] finished ' + reason)


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
        if S['restart'] is not None and time.time() - S['shot'] >= 0.25:
            S['n'] += 1
            cmd('Shot showui filename=%s/%03d_r%03d.png -nosuffix' % (SHOTS, S['n'], int((time.time() - S['restart']) * 10)))
            S['shot'] = time.time()
            log('frame', shot=S['n'])
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
        elif ph == 5:  # the first morning: the phone opens by itself (BeatIndex 0)
            if prop(D, 'BeatIndex') != 0:
                if el > 22:
                    return finish('first_morning_no_t0')
                return
            S['first'] = log('first_morning_t0')
            wait(1.0)
        elif ph == 6:
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(1.2)
        elif ph == 7:
            log('before_restart')
            S['restart'] = time.time()
            FE.call_method('RestartDay', ())
            log('restart_day'); wait(0.5)
        elif ph == 8:  # the new morning's wake-up: skip it once its film owns the view
            vt = pc.get_view_target()
            if not vt or vt.get_class().get_name() != 'CineCameraActor' or prop(D, 'BeatIndex', 0) >= 0:
                return
            log('new_wakeup'); wait(1.0)
        elif ph == 9:
            cmd('ke * SkipWakeUp'); log('skip_new_wakeup'); wait(0.3)
        elif ph == 10:  # the new morning's T0: BeatIndex 0 again, by itself
            if prop(D, 'BeatIndex') != 0:
                if time.time() - S['restart'] > 26:
                    return finish('new_morning_no_t0')
                return
            log('new_morning_t0'); wait(2.2)
        elif ph == 11:
            log('after_t0'); finish('restart_day_t0_passed')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
