"""Story lane, in PIE (run_chase_final.py pie_hanger_glance, one EXCLUSIVE window): the dropped hanger's glance.
  menu -> Wake up -> intro -> skip -> T0 phone -> the screwdriver route's events to the fall (the hanger is never taken)
  -> T7 top-down: the hanger falls and lands -> fixture: ExitTopDown early (the hold timer would do it ~13 s later)
  -> from the hand-back, untouched: SayHangerFell (0.6 s after the fade-up) starts the glance; every 0.1 s a shot and a
  row (control rotation, input held, the hanger's top on screen, the interactor's target and prompt) until 1 s after
  it ends.
Pass: the glance ran once; in the hold the hanger is on screen and the prompt is the hanger's; it ends at the starting
view (within 1 deg) with move and look input back; the line was said. Save-isolated (proof_save).
Shots: Saved/StoryShots/hanger_glance/*.png. Result: Saved/StoryShots/hanger_glance.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/hanger_glance.json')
SHOTS = 'P:/FoA/Saved/StoryShots/hanger_glance'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, exit_at=0.0, seen=False,
         ended_at=0.0)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
HANGER = ACT['Hanger_CoatRail']


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def on_screen(pos):
    r = unreal.GameplayStatics.project_world_to_screen(pc, pos, False)
    sp = r[1] if isinstance(r, tuple) else r
    if sp is None or (isinstance(r, tuple) and not r[0]):
        return None
    size = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    return [round(sp.x / size.x, 2), round(sp.y / size.y, 2)]


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    rot = pc.get_control_rotation()
    origin, extent = HANGER.get_actor_bounds(False)
    top = unreal.Vector(origin.x, origin.y, origin.z + extent.z)
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), shot=S['n'],
               rot=[round(rot.pitch, 1), round(rot.yaw, 1)], glancing=prop(D, 'bHangerGlancing'),
               said=prop(D, 'bHangerLineSaid'), move_held=pc.is_move_input_ignored(), look_held=pc.is_look_input_ignored(),
               hanger_screen=on_screen(top), hanger_state=str(prop(HANGER, 'State')),
               target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')),
               pawn=[round(v) for v in P.get_actor_location().to_tuple()], **kw)
    S['rows'].append(row)
    unreal.log('[hanger_glance] ' + json.dumps(row, default=str))
    return row


def shot(tag):
    S['n'] += 1
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%s/%03d_%s.png -nosuffix' % (SHOTS, S['n'], tag), pc)


def verdict():
    rows = [r for r in S['rows'] if r['kind'] == 'watch']
    on = [r for r in rows if r['glancing']]
    if not on:
        return 'glance_never_started'
    start = rows[rows.index(on[0]) - 1] if rows.index(on[0]) else on[0]
    hold = [r for r in on if r['hanger_screen'] and 0.05 <= r['hanger_screen'][0] <= 0.95 and 0.05 <= r['hanger_screen'][1] <= 0.95]
    prompt = [r for r in hold if r['target'] == 'Hanger_CoatRail']
    last = rows[-1]
    back = abs(((last['rot'][0] - start['rot'][0]) + 180) % 360 - 180) <= 1 and abs(((last['rot'][1] - start['rot'][1]) + 180) % 360 - 180) <= 1
    runs = sum(1 for a, b in zip(rows, rows[1:]) if b['glancing'] and not a['glancing'])
    checks = dict(hanger_in_frame=bool(hold), prompt_on_hanger=bool(prompt), back_to_start=back,
                  input_back=not last['move_held'] and not last['look_held'], once=runs <= 1, line_said=bool(last['said']))
    S['checks'] = checks
    return 'glance_passed' if all(checks.values()) else 'glance_failed_' + '_'.join(k for k, v in checks.items() if not v)


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
    OUT.write_text(json.dumps(dict(reason=reason, checks=S.get('checks'), rows=S['rows']), indent=1, default=str))
    unreal.log('[hanger_glance] finished ' + reason)


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
        if time.time() - S['t0'] > 47:
            return finish('timeout_phase_%d' % S['phase'])
        ph = S['phase']
        if ph == 9:  # watching: one row and one shot every 0.1 s, nothing touches the view
            if time.time() - S['shot'] < 0.1:
                return
            S['shot'] = time.time()
            shot('g')
            row = log('watch')
            S['seen'] = S['seen'] or bool(row['glancing'])
            if S['seen'] and not row['glancing'] and not S['ended_at']:
                S['ended_at'] = time.time()
            if S['ended_at'] and time.time() - S['ended_at'] > 1.0:
                return finish(verdict())
            if not S['seen'] and time.time() - S['exit_at'] > 4.0:
                return finish(verdict())
            return
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
            log('to_fall'); wait(0.3)
        elif ph == 7:  # T7, top-down: wait for the hanger to land
            if prop(D, 'BeatIndex') != 7 or not prop(D, 'bTopDown'):
                return
            if not prop(D, 'DroppedHanger') or unreal.SystemLibrary.is_timer_active(D, 'TickHangerDrop'):
                return
            log('landed'); wait(0.6)
        elif ph == 8:  # fixture: leave top-down now rather than after the ~13 s hold; the glance is all the game's
            D.call_method('ExitTopDown', ()); log('exit_topdown_fixture')
            S['exit_at'] = time.time(); wait(0.0)
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
