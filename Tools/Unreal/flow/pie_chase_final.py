"""Story lane, in PIE: the final shirt reach at its new landing (LANDINGS[2], the bay floor below the windowsill vase).
Run by run_chase_final.py inside an EXCLUSIVE PIE window; everything after the setup is the shipped game:
  menu -> Wake up -> intro (story finish) -> skip the wake-up -> T0 phone (Wake up) -> the clue, toss and escape functions
  -> EscapeClothingTwo (the shirt flies to the landing) -> the pawn stands near it -> the normal Scan must focus the shirt
  ("Grab the shirt") -> real E (the runner presses it) -> ReachClothingVase: the vase falls, shatters, the boss rises.
Shots: Saved/StoryShots/chase_final/*.png. Result: Saved/StoryShots/chase_final.json (reason 'final_reach_passed')."""
import json
import math
import os
import time
from pathlib import Path

import unreal
import importlib
import sys
sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  the player's save stays untouched (main's rule 2026-11-10)
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/chase_final.json')
SHOTS = 'P:/FoA/Saved/StoryShots/chase_final'
INPUTS = Path('P:/FoA/Saved/StoryShots/chase_final_input.json')
LANDING = unreal.Vector(-55.0, -335.0, 38.5)
STANDS = [(-55, -250), (15, -265), (-125, -265), (35, -320), (-140, -320), (-55, -225)]
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):  # one run per folder: an older, longer run would leave frames behind
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, input_id=0, stand=0)


def cls(path):
    return unreal.load_class(None, path)


def actor(path):
    return unreal.GameplayStatics.get_actor_of_class(w, cls(path))


D = actor('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)
    log('cmd', cmd=c)


def log(kind, **kw):
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), stage=prop(D, 'ClothingSearchStage'), **kw)
    S['rows'].append(row)
    unreal.log('[chase_final] ' + json.dumps(row, default=str))
    return row


def shot(tag):
    if time.time() - S['shot'] < 0.22:
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
    unreal.log('[chase_final] finished ' + reason)


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
        if S['phase'] >= 9:
            shot('p%d' % S['phase'])
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
        elif ph == 6:  # the stages through the director's own functions (the stage is not instance-editable)
            for fn in ('StartClothingSearch', 'SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                D.call_method(fn, ())
            log('clues_done'); D.call_method('BeginClothingToss', ()); wait(4.2)
        elif ph == 7 and not S.get('one'):  # stage 5: the first escape, then (61) the second, back to 7 to stand
            S['one'] = True
            log('toss_done'); D.call_method('EscapeClothingOne', ()); S['after'] = time.time() + 2.6; S['phase'] = 61
        elif ph == 61:
            log('escape_one_done'); D.call_method('EscapeClothingTwo', ()); S['after'] = time.time() + 3.2; S['phase'] = 7
        elif ph == 7:
            shirt = prop(D, 'SearchShirt')
            log('landed', shirt=shirt.get_actor_location().to_tuple() if shirt else None,
                state=str(prop(shirt, 'State', prop(shirt, 'CurrentState'))) if shirt else None)
            stand = STANDS[S['stand']]
            ok = P.teleport(unreal.Vector(stand[0], stand[1], 92.0), P.get_actor_rotation())
            log('stand', at=stand, ok=ok)
            if not ok:
                S['stand'] += 1
                if S['stand'] >= len(STANDS):
                    return finish('no_stand_spot')
                return
            cam = pc.player_camera_manager.get_camera_location()
            target = shirt.get_actor_location() if shirt else LANDING
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, target))
            wait(0.5)
        elif ph == 8:
            tgt = prop(IA, 'Target')
            row = log('focus', target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')))
            shot('focus')
            if not tgt or 'Shirt' not in tgt.get_actor_label():
                if el > 40:
                    return finish('scan_never_focused_the_shirt')
                S['stand'] = (S['stand'] + 1) % len(STANDS)
                S['phase'] = 7
                return
            S['input_id'] += 1
            INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
            log('press_E'); wait(0.3)
        elif ph == 9:
            if prop(D, 'ClothingSearchStage') < 8:
                if el > 44:
                    return finish('E_did_not_start_the_vase')
                return
            log('vase_forming'); wait(4.6)
        elif ph == 10:
            log('after_vase'); finish('final_reach_passed' if prop(D, 'ClothingSearchStage') >= 8 else 'stage_stalled')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


INPUTS.unlink(missing_ok=True)
OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
