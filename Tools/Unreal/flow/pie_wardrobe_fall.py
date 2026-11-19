"""Story lane, in PIE (run_chase_final.py pie_wardrobe_fall, one EXCLUSIVE window): the first-person wardrobe fall
through the real flow. Fixture: T6 by its events (as pie_notify_repro.py), the door's latch freed (SetState LatchFree).
Then the real pull: he stands at the door, the interactor focuses it (pinned only if its own scan does not), one real E
on "Pull the handle" -> HandleOff -> the wardrobe's Notify -> WardrobeFalling -> BeginWardrobeTransition ->
LS_WardrobeFall -> WardrobeFallDone. From the E on, time runs at x0.5 and a frame is taken every 0.1 s.
Checks: door vanishes, the pawn scatters and reforms behind the wardrobe, fallen (the wardrobe reaches Fallen),
sequence_seen (the view is a sequence camera during the fall), control_back (bWardrobeTransition false, move input free,
the view on him or the top-down camera after it), clear_of_it (he ends outside the fallen wardrobe's bounds).
Result: Saved/StoryShots/wardrobe_fall.json; frames Saved/StoryShots/wardrobe_fall/*.png."""
import importlib
import json
import math
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)

OUT = Path('P:/FoA/Saved/StoryShots/wardrobe_fall.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/wardrobe_fall_input.json')
INPUTS.unlink(missing_ok=True)
SHOTS = Path('P:/FoA/Saved/StoryShots/wardrobe_fall/')
SHOTS.mkdir(parents=True, exist_ok=True)
for f in SHOTS.glob('*.png'):
    f.unlink()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
S = dict(t0=time.time(), phase=0, rows=[], done=False, h=None, at=0.0, n=0, shot=0.0, pull=None, done_at=None)
DIL = 0.5


def label(lbl):
    return next((a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_actor_label() == lbl), None)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def r1(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def log(kind, **kw):
    S['rows'].append(dict(kind=kind, t=round(time.time() - S['t0'], 2), **kw))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() == w:
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    rows = [r for r in S['rows'] if r.get('kind') == 'f']
    last = rows[-1] if rows else {}
    fb = last.get('wardrobe_bounds')
    clear = bool(fb) and not (abs(last['pawn'][0] - fb[0][0]) < fb[1][0] and abs(last['pawn'][1] - fb[0][1]) < fb[1][1])
    vanished = [i for i, r in enumerate(rows) if r['pawn_hidden']]
    reformed = rows[vanished[-1] + 1:] if vanished else []
    checks = dict(door_vanished=any(r['door_hidden'] for r in rows),
                  scattered=bool(vanished),
                  reformed=bool(reformed) and not last['pawn_hidden'] and not last['sand_transition'],
                  visible_reintegration=any(r['sand_transition'] and not r['pawn_hidden'] for r in reformed),
                  behind_wardrobe=bool(fb) and last['pawn'][0] < fb[0][0] - fb[1][0],
                  fallen=any(r['wardrobe'] == 'Fallen' for r in rows),
                  sequence_seen=any('Cam_' in r['view'] or 'CineCamera' in r['view'] for r in rows),
                  control_back=bool(last) and not last['transition'] and not last['move_ignored'],
                  clear_of_it=clear)
    OUT.write_text(json.dumps(dict(reason=reason, checks=checks, rows=S['rows']), indent=1, default=str))
    print('RESULT', reason, json.dumps(checks))


def frame(d, p, pc):
    wr, door = label('Wardrobe'), label('Door_Bedroom')
    o, e = wr.get_actor_bounds(True)
    S['n'] += 1
    S['rows'].append(dict(kind='f', n=S['n'], gt=round(unreal.GameplayStatics.get_time_seconds(w) - S['pull'], 3),
                          view=pc.get_view_target().get_name(), cam=r1(pc.player_camera_manager.get_camera_location()),
                          beat=str(prop(prop(d, 'Beat'), 'Id')), wardrobe=str(prop(wr, 'State')),
                          wardrobe_bounds=[r1(o), r1(e)], door=str(prop(door, 'State')), door_hidden=door.get_editor_property('hidden'),
                          pawn=r1(p.get_actor_location()), pawn_hidden=p.get_editor_property('hidden'),
                          sand_transition=prop(p, 'bSandTransition'),
                          transition=prop(d, 'bWardrobeTransition'), move_ignored=pc.is_move_input_ignored(),
                          topdown=prop(d, 'bTopDown')))
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=%s/f%04d.png -nosuffix' % (SHOTS.as_posix(), S['n']), pc)


def tick(dt):
    try:
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() != w:  # ended or replaced
            return finish('pie_gone')
        t = time.time() - S['t0']
        if t > 46:
            return finish('cap')
        d, fe = label('BeatDirector'), label('BP_FoAFrontEnd')
        if not (d and fe):
            return
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        p = unreal.GameplayStatics.get_player_character(w, 0)
        if S['pull'] is not None:
            if time.time() - S['shot'] >= 0.1:
                S['shot'] = time.time()
                frame(d, p, pc)
            if prop(d, 'bWardrobeTransition'): S['transition_seen'] = True
            if S.get('transition_seen') and S['done_at'] is None and not prop(d, 'bWardrobeTransition'):
                S['done_at'] = unreal.GameplayStatics.get_time_seconds(w)
            if S['done_at'] is not None and unreal.GameplayStatics.get_time_seconds(w) - S['done_at'] > 1.8:
                return finish('done')
            if unreal.GameplayStatics.get_time_seconds(w) - S['pull'] > 12:
                return finish('no_finish')
            return
        if t < S['at']:
            return
        ph = S['phase']
        if ph == 0:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1; S['at'] = t + 0.3
        elif ph == 1:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2; S['at'] = t + 0.3
        elif ph == 2:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        elif ph == 3:
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish', ())
            elif fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone'):
                d.call_method('SkipWakeUp', ()); S['phase'] = 4
        elif ph == 4 and d.get_editor_property('bWakeDone') and d.get_editor_property('BeatIndex') >= 0 and pc.get_view_target() == p and not p.get_editor_property('bCinematic'):
            for ev in ('PhoneWakeUp', 'FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed'):
                d.call_method('ReportEvent', (ev,))
            unreal.SystemLibrary.execute_console_command(w, 'ke * ClosePhone', pc)
            label('Door_Bedroom').call_method('SetState', ('LatchFree', True))
            log('to_t6', beat=str(prop(prop(d, 'Beat'), 'Id')), door=str(prop(label('Door_Bedroom'), 'State')))
            S['phase'] = 5; S['at'] = t + 1.0
        elif ph == 5:
            spot = unreal.Vector(330.0, 80.0, 92.0)
            p.teleport(spot, unreal.Rotator(0, 0, 0))
            S['phase'] = 6; S['at'] = t + 0.3
        elif ph == 6:
            door = label('Door_Bedroom')
            handle = unreal.Vector(375.0, 62.0, 100.0)
            pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(), handle))
            S['phase'] = 7; S['at'] = t + 0.4
        elif ph == 7:
            door = label('Door_Bedroom')
            ia = p.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
            if prop(ia, 'Target') != door:
                log('focus_pinned', saw=prop(ia, 'Target').get_actor_label() if prop(ia, 'Target') else None)
                ia.call_method('SetFocus', (door,))
                ia.call_method('Refresh', (True,))
            for _ in range(3):
                if 'pull' in str(prop(ia, 'Prompt')).lower():
                    break
                ia.call_method('CycleVerb')
            log('pull', prompt=str(prop(ia, 'Prompt')), verb=str(prop(ia, 'Verb')))
            unreal.GameplayStatics.set_global_time_dilation(w, DIL)
            S['pull'] = unreal.GameplayStatics.get_time_seconds(w)
            INPUTS.write_text(json.dumps(dict(id=1, key='E')))  # one real E, relayed by run_chase_final.py
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('wardrobe_fall scheduled')
