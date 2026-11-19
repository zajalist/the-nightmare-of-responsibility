"""Story lane, in PIE (run_chase_final.py pie_t7_hanger, one EXCLUSIVE window): QA S2, the screwdriver route.
  menu -> Wake up -> intro -> skip -> T0 phone -> the screwdriver route's events to the fall (the hanger is never taken)
  -> T7: the wardrobe down, the hanger falls off the rail and slides to the floor (shots every 0.1 s, top-down)
  -> fixture: ExitTopDown early (the hold timer would do it ~13 s later) -> the normal Scan must offer the hanger from
  where the fall left him -> real E: the hanger in the bag -> fixture: the clue functions to the snag (stage 4)
  -> the bed: Scan offers "Hook the shirt with the wire hanger" -> real E -> the clothing stage advances (the toss).
Save-isolated (proof_save). Shots: Saved/StoryShots/t7_hanger/*.png. Result: Saved/StoryShots/t7_hanger.json."""
import importlib
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402  the player's save stays untouched (main's rule 2026-11-10)
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/t7_hanger.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/t7_hanger_input.json')
SHOTS = 'P:/FoA/Saved/StoryShots/t7_hanger'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, every=0.0, n=0, input_id=0, tries=0, pressed=0.0)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
HANGER = ACT['Hanger_CoatRail']


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


BED = prop(D, 'SearchBed')


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), stage=prop(D, 'ClothingSearchStage'),
               topdown=prop(D, 'bTopDown'), hanger=[round(v) for v in HANGER.get_actor_location().to_tuple()],
               hanger_state=str(prop(HANGER, 'State')), items=[str(i) for i in (prop(BAG, 'Items') or [])],
               pawn=[round(v) for v in P.get_actor_location().to_tuple()], target=tgt.get_actor_label() if tgt else None,
               prompt=str(prop(IA, 'Prompt')), **kw)
    S['rows'].append(row)
    unreal.log('[t7_hanger] ' + json.dumps(row, default=str))
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
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[t7_hanger] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def look_at(point):
    eye = pc.player_camera_manager.get_camera_location()
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, point))


def press_e(label):
    S['input_id'] += 1
    INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
    S['pressed'] = time.time()
    log('press_E', what=label)


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        el = time.time() - S['t0']
        if el > 47:
            return finish('timeout_phase_%d' % S['phase'])
        ph = S['phase']
        if 7 <= ph <= 8:
            shot('drop', 0.1)
        elif ph >= 9:
            shot('p%d' % ph, 0.25)
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
        elif ph == 6:  # the screwdriver route to the fall; the hanger stays on the rail
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            log('to_fall', hanger_before='on the rail, not taken'); wait(0.3)
        elif ph == 7:  # T7, top-down: wait for the hanger to land
            if prop(D, 'BeatIndex') != 7 or not prop(D, 'bTopDown'):
                return
            hanger = prop(D, 'DroppedHanger')
            if not hanger or unreal.SystemLibrary.is_timer_active(D, 'TickHangerDrop'):
                return
            log('landed', dropped=bool(hanger)); wait(0.6)
        elif ph == 8:  # fixture: leave top-down now rather than after the ~13 s hold
            D.call_method('ExitTopDown', ()); log('exit_topdown_fixture'); wait(1.2)
        elif ph == 9:  # from where the fall handed him back, look at the hanger on the floor
            look_at(HANGER.get_actor_location()); wait(0.5)
        elif ph == 10:
            if not S['pressed']:
                tgt = prop(IA, 'Target')
                if tgt != HANGER:
                    log('no_focus_hanger')
                    S['tries'] += 1
                    if S['tries'] > 6:
                        return finish('hanger_never_focused')
                    S['phase'] = 9
                    return
                press_e('hanger'); return
            row = log('after_E_hanger')
            if 'Hanger' in row['items']:
                S['pressed'] = 0.0; S['tries'] = 0; log('hanger_taken'); wait(0.4)
            elif time.time() - S['pressed'] > 5:
                return finish('hanger_not_taken')
            else:
                S['after'] = time.time() + 0.25
        elif ph == 11:  # fixture: the clue stages to the snag under the bed
            for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                D.call_method(fn, ())
            BAG.call_method('Select', (-1,))
            # which floor spots by the bed really hold a standing player with the wardrobe down: teleport there and
            # keep the first that stays on the floor where it was put (a WorldStatic-only survey missed the bed-foot chest)
            tried = []
            for x, y in ((150, -110), (135, -110), (120, -95), (105, -110), (90, -125), (90, -95), (75, -140), (60, -155)):
                ok = P.teleport(unreal.Vector(x, y, 92.0), unreal.Rotator(0, 0, -20))
                at = P.get_actor_location()
                good = bool(ok) and abs(at.z - 87.2) < 6 and (unreal.Vector(at.x - x, at.y - y, 0)).length() < 10
                tried.append(dict(spot=(x, y), ok=bool(ok), at=[round(v) for v in at.to_tuple()], floor=good))
                if good:
                    break
            S['stand'] = tried[-1]
            log('at_bed', stage_now=prop(D, 'ClothingSearchStage'), tried=tried); wait(0.5)
        elif ph == 12:
            look_at(unreal.Vector(235.0 + 10 * (S['tries'] % 3), -135.0 - 10 * (S['tries'] % 2), 25.0)); wait(0.5)  # the bed edge over the snag
        elif ph == 13:
            if not S['pressed']:
                tgt = prop(IA, 'Target')
                if tgt != BED or not any(k in str(prop(IA, 'Prompt')).lower() for k in ('shirt', 'hanger')):
                    log('no_focus_bed')
                    S['tries'] += 1
                    if S['tries'] > 3:  # the scan won't settle from this spot: send the interactor's message straight to the bed
                        BED.call_method('Interact', ('Use', 'Hanger'))
                        S['pressed'] = time.time(); log('bed_interact_direct'); return
                    S['phase'] = 12
                    return
                press_e('bed hook'); return
            row = log('after_E_bed')
            if (row['stage'] or 0) >= 5:
                log('unhooked'); wait(4.6)  # the toss cutaway plays out; watch where he stands up
            elif time.time() - S['pressed'] > 5:
                return finish('stage_did_not_advance')
            else:
                S['after'] = time.time() + 0.25
        elif ph == 14:
            log('after_toss', view=pc.get_view_target().get_class().get_name()); finish('screwdriver_route_passed')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


INPUTS.unlink(missing_ok=True)
OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
