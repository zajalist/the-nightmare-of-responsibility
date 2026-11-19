"""Story lane, in PIE (run_chase_final.py pie_topdown_exit, one EXCLUSIVE window): two proofs at the same moment.
1. ExitTopDown cuts under a fade: shots at 20 fps from bTopDown going false until 1.2 s later; no frame may show the
   player's body from outside (the old 1.5 s blend swept from above into the head).
2. The T7 headache line no longer takes control: before the cut the pawn is placed facing the fallen wardrobe, so after
   it the normal Scan offers "Search the fallen wardrobe"; through the line the prompt must stay and movement stay free.
Shots: Saved/StoryShots/topdown_exit/*.png. Result: Saved/StoryShots/topdown_exit.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/topdown_exit.json')
SHOTS = 'P:/FoA/Saved/StoryShots/topdown_exit'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, exit_at=None)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))


D = actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), topdown=prop(D, 'bTopDown'),
               target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')),
               move_ignored=pc.is_move_input_ignored(), cinematic=prop(P, 'bCinematic'), **kw)
    S['rows'].append(row)
    unreal.log('[topdown_exit] ' + json.dumps(row, default=str))
    return row


def shot(tag, every):
    if time.time() - S['shot'] < every:
        return
    S['n'] += 1
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%s/%03d_%s.png -nosuffix' % (SHOTS, S['n'], tag), pc)
    S['shot'] = time.time()


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
    unreal.log('[topdown_exit] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def face_wardrobe():
    wd = actor('/Game/FoA/Gameplay/BP_Topple.BP_Topple_C')
    o, e = wd.get_actor_bounds(False)
    v = unreal.Vector(-o.x, -o.y, 0)
    v.normalize()
    for k in (1.0, 1.25, 0.8, 1.5):
        stand = o + v * (max(e.x, e.y) * k + 85)
        stand.z = 92
        if P.teleport(stand, P.get_actor_rotation()):
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(unreal.Vector(stand.x, stand.y, 160), o))
            return stand.to_tuple()
    return None


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        el = time.time() - S['t0']
        if el > 50:
            return finish('timeout_phase_%d' % S['phase'])
        ph = S['phase']
        if S['exit_at'] is not None:
            since = time.time() - S['exit_at']
            shot('exit', 0.05 if since < 1.2 else 0.25)
            if since > 1.2 and not S.get('logged_cut'):
                S['logged_cut'] = True
                log('after_cut')
        if time.time() < S['after']:
            return
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
            log('to_t7'); wait(0.5)
        elif ph == 7:
            if not prop(D, 'bTopDown'):
                return
            log('topdown', stand=face_wardrobe()); wait(0.2)
        elif ph == 8:
            if prop(D, 'bTopDown'):
                return
            S['exit_at'] = time.time()
            log('exit_started'); wait(1.4)
        elif ph == 9:  # the cut is done: watch the prompt through the T7 line (it comes ~2.4 s after the player is free)
            row = log('watch')
            if el > 46 or time.time() - S['exit_at'] > 9:
                return finish('watched')
            S['after'] = time.time() + 0.4
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
