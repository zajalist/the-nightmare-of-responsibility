"""Story lane, in PIE (run_chase_final.py pie_inventory_repro, one EXCLUSIVE window): the "My hands are full" bag, red then
green. The user's live bag was (KeyStub, Screwdriver, Hanger, Screwdriver) with one screwdriver pickup in the level.
  menu -> Wake up -> intro -> skip -> T0 phone -> events to T5 -> real E: take the screwdriver on the desk -> real E: take the hanger off
  the rail -> events to T7 (StageWrongWall runs RefillDrawer: ResetForNewDay on Screwdriver_DeskDrawer) -> the pickup is
  Available again on the desk -> real E: take it again.
Logs the bag, the pickup's State and bPendingRow after every step, and how many times each take's line and commit ran
(no delegate access: QA rule 2026-11-10). Red: a second Screwdriver in the bag. Result: Saved/StoryShots/inventory_repro.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/inventory_repro.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/inventory_repro_input.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, input_id=0, pressed=0.0, tries=0, changes=0)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
SD, HG = ACT['Screwdriver_DeskDrawer'], ACT['Hanger_CoatRail']
DOOR = ACT['Door_Bedroom']


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), items=[str(i) for i in (prop(BAG, 'Items') or [])],
               sd_state=str(prop(SD, 'State')), sd_pending=prop(SD, 'bPendingRow'),
               hg_state=str(prop(HG, 'State')), target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')), **kw)
    S['rows'].append(row)
    unreal.log('[inventory_repro] ' + json.dumps(row, default=str))
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
    items = S['rows'][-1]['items'] if S['rows'] else []
    spent = str(S.get('refill_prompt', '')).startswith('Look') and items == ['Hanger']
    verdict = ('RED_duplicate_screwdriver' if items.count('Screwdriver') > 1 else
               'GREEN_spent_screwdriver_look_only' if reason == 'done' and spent else
               'GREEN_no_duplicate' if reason == 'done' else 'inconclusive')
    OUT.write_text(json.dumps(dict(reason=reason, verdict=verdict, rows=S['rows']), indent=1, default=str))
    unreal.log('[inventory_repro] finished %s %s' % (reason, verdict))


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def stand_and_look(actor, offset):
    at = actor.get_actor_location()
    P.teleport(unreal.Vector(at.x + offset[0], at.y + offset[1], 92.0), unreal.Rotator(0, 0, 0))
    eye = pc.player_camera_manager.get_camera_location()
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, at))


def take(actor, offset, label, done_when):
    """one real E on actor; returns True when done_when() holds"""
    if not S['pressed']:
        stand_and_look(actor, offset)
        if prop(IA, 'Target') != actor:
            S['tries'] += 1
            if S['tries'] > 12:
                finish('never_focused_' + label)
            S['after'] = time.time() + 0.3
            return False
        S['input_id'] += 1
        INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
        S['pressed'] = time.time()
        log('press_E', what=label)
        return False
    if done_when():
        S['pressed'] = 0.0
        S['tries'] = 0
        log('took', what=label)
        return True
    if time.time() - S['pressed'] > 6:
        finish('not_taken_' + label)
    S['after'] = time.time() + 0.25
    return False


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        S.setdefault('dts', []).append(dt)  # a minimized editor throttles PIE to 3 fps: the proof means nothing then
        if len(S['dts']) == 40:
            med = sorted(S['dts'])[20]
            log('fps', median_ms=round(med * 1000, 1))
            if med > 0.066:
                return finish('throttled_fps')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
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
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone')
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped'):  # to T5, where the tools can be taken
                cmd('ke * ReportEvent ' + ev)
            log('to_t5'); wait(0.8)
        elif ph == 6:  # the screwdriver, by hand
            if take(SD, (120.0, 0.0), 'screwdriver_1', lambda: 'Screwdriver' in log('poll')['items']):
                wait(1.0)
        elif ph == 7:  # the hanger off the rail
            if take(HG, (-60.0, -70.0), 'hanger', lambda: 'Hanger' in log('poll')['items']):
                wait(1.0)
        elif ph == 8:  # to T6 with the latch free, then the real handle pull: the wardrobe falls, T7, top-down, the refill
            cmd('ke * ReportEvent LatchFreed')
            DOOR.call_method('SetState', ('LatchFree', True))
            log('to_t6'); wait(0.5)
        elif ph == 9:
            if prop(D, 'BeatIndex') < 7 and not S.get('pulled'):
                stand_and_look(DOOR, (-90.0, -30.0))
                if prop(IA, 'Target') != DOOR:
                    IA.call_method('SetFocus', (DOOR,)); IA.call_method('Refresh', (True,))
                S['input_id'] += 1
                INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
                S['pulled'] = time.time(); log('press_E', what='handle'); S['after'] = time.time() + 0.5
                return
            row = log('poll_refill')
            if row['beat'] == 7 and row['sd_state'] in ('Available', 'Spare'):  # Spare: refilled but spent (look only)
                D.call_method('ExitTopDown', ()); log('refilled_and_back', sd_hidden=prop(SD, 'bHidden')); wait(1.5)
            elif time.time() - S['t0'] > 43:
                finish('no_refill')
            else:
                S['after'] = time.time() + 0.3
        elif ph == 10:  # the same pickup, again: one real E, whatever its prompt offers
            if not S['pressed']:
                stand_and_look(SD, (120.0, 0.0))
                if prop(IA, 'Target') != SD:
                    S['tries'] += 1
                    if S['tries'] > 12:
                        return finish('never_focused_screwdriver_2')
                    S['after'] = time.time() + 0.3
                    return
                S['refill_prompt'] = str(prop(IA, 'Prompt'))
                S['input_id'] += 1
                INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
                S['pressed'] = time.time()
                log('press_E', what='screwdriver_2')
                S['after'] = time.time() + 2.0
                return
            S['pressed'] = 0.0
            log('after_E', what='screwdriver_2', refill_prompt=S['refill_prompt']); wait(0.5)
        elif ph == 11:
            log('final', refill_prompt=S.get('refill_prompt')); finish('done')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


INPUTS.unlink(missing_ok=True)
OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
