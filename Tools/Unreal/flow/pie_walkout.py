"""Story lane, in PIE (run_chase_final.py pie_walkout, one EXCLUSIVE window): QA plan C, the walk-out. Past the moved door
frame there is no floor; he must stop in the doorway and stay at about z 87 through the fade and the "Day one." card.
  menu -> Wake up -> intro -> skip -> T0 -> events skip ahead to the payoff (EncounterWon), PayoffEnded -> T10 (the door
  opens, CheckWalkedOut runs) -> he steps into the doorway, 30 cm past the frame line (frame-local X +30), with a
  little forward speed -> WalkedOut -> the end. Every 0.25 s: z, movement mode, input, view, a shot.
Save-isolated. Shots: Saved/StoryShots/walkout/*.png. Result: Saved/StoryShots/walkout.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/walkout.json')
SHOTS = 'P:/FoA/Saved/StoryShots/walkout'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, out=None)
D = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def log(kind, **kw):
    vt = pc.get_view_target()
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), z=round(P.get_actor_location().z, 1),
               pawn=[round(v) for v in P.get_actor_location().to_tuple()], mode=str(P.character_movement.movement_mode),
               move_ignored=pc.is_move_input_ignored(), held=prop(D, 'bWalkOutHeld'), view=vt.get_class().get_name() if vt else None,
               **kw)
    if S['out'] is not None:
        row['since_out'] = round(time.time() - S['out'], 2)
    S['rows'].append(row)
    unreal.log('[walkout] ' + json.dumps(row, default=str))
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    zs = [r['z'] for r in S['rows'] if 'since_out' in r]
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, z_min=min(zs) if zs else None, z_max=max(zs) if zs else None, rows=S['rows']),
                              indent=1, default=str))
    unreal.log('[walkout] finished ' + reason)


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
        if S['out'] is not None and time.time() - S['shot'] >= 0.25:
            S['n'] += 1
            cmd('Shot showui filename=%s/%03d.png -nosuffix' % (SHOTS, S['n']))
            S['shot'] = time.time()
            log('sample')
            if time.time() - S['out'] > 9.0:
                return finish('watched')
        if time.time() < S['after']:
            return
        ph = S['phase']
        steps = {0: ('ke * OnSplashFinished', 0.8), 1: ('ke * OnTitleConfirmed', 1.2), 2: ('ke * WakeUp', 6.2),
                 3: ('ke * OnStoryFinished', 2.6), 4: ('ke * SkipWakeUp', 0.6)}
        if ph in steps:
            cmd(steps[ph][0]); S['after'] = time.time() + steps[ph][1]; S['phase'] += 1
        elif ph == 5:
            if prop(D, 'BeatIndex') != 0:
                return
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.6)
        elif ph == 6:
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'EncounterWon'):
                cmd('ke * ReportEvent ' + ev)
            log('to_payoff'); wait(0.5)
        elif ph == 7:  # the payoff hero shot plays (~2.7 s), then T10 and its phone
            if prop(D, 'BeatIndex') != 10:
                return
            cmd('ke * ClosePhone'); log('t10'); wait(1.5)
        elif ph == 8:  # into the doorway, just past the frame line, still moving forward
            frame = prop(D, 'DoorFrame')
            xf = frame.get_actor_transform()
            spot = unreal.MathLibrary.transform_location(xf, unreal.Vector(30, 0, 0))
            spot.z = 92.0
            fwd = unreal.MathLibrary.transform_direction(xf, unreal.Vector(1, 0, 0))
            P.teleport(spot, unreal.MathLibrary.make_rot_from_x(fwd))
            P.launch_character(fwd * 200.0, True, False)
            S['out'] = time.time()
            log('stepped_out', spot=spot.to_tuple()); wait(60)
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
