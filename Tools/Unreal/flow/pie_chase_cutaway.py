"""Story lane, in PIE (run_chase_final.py pie_chase_cutaway, one EXCLUSIVE window): QA B2, the hanger toss cutaway.
  menu -> Wake up -> intro -> skip -> T0 phone -> the clothing search's clue functions -> the pawn stands on the floor
  by the bed -> BeginClothingToss (what the real unhook calls through FreeClothing) -> watch to the end of the return.
Every 0.1 s: a shot plus the view target, the HUD's visibility, the camera fade amount, the pawn's location, the
camera's distance to the head and whether the body is in front of a moving non-film camera (QA's view check).
Must show: HUD hidden through the cutaway, the return under black (fade 1 at the cut), the pawn standing on the floor
(z about 89) afterwards, no moving-camera sample with the body in view.
Shots: Saved/StoryShots/chase_cutaway/*.png. Result: Saved/StoryShots/chase_cutaway.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/chase_cutaway.json')
SHOTS = 'P:/FoA/Saved/StoryShots/chase_cutaway'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)  # before the splash: every save of this run goes to the QA slot
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, toss=None, last_cam=None, back=None)


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
FE = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def sample():
    cam = pc.player_camera_manager
    loc, fwd = cam.get_camera_location(), unreal.MathLibrary.get_forward_vector(cam.get_camera_rotation())
    body = prop(P, 'Body') or P.get_component_by_class(unreal.SkeletalMeshComponent)
    o, _, _ = unreal.SystemLibrary.get_component_bounds(body)
    head = body.get_socket_location('head')
    to = o - loc
    dist = to.length()
    to.normalize()
    ang = math.degrees(math.acos(max(-1.0, min(1.0, fwd.x * to.x + fwd.y * to.y + fwd.z * to.z))))
    moving = S['last_cam'] is not None and (loc - S['last_cam']).length() > 2.0
    S['last_cam'] = loc
    vt = pc.get_view_target()
    name = vt.get_class().get_name() if vt else ''
    seen = (loc - head).length() > 40.0 and ang < cam.get_fov_angle() / 2 + 5 and dist < 2000
    hud = prop(FE, 'HUD')
    ia = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
    tgt = prop(ia, 'Target')
    shirt = prop(D, 'SearchShirt')
    return dict(view=name, hud=str(hud.get_visibility()) if hud else None, hud_class=hud.get_class().get_name() if hud else None,
                story_hud_hidden=prop(D, 'bStoryHUDHidden'), story_hud=str(prop(D, 'StoryHUD')), dip=prop(D, 'bClothingReturnDip'),
                target=tgt.get_actor_label() if tgt else None, prompt=str(prop(ia, 'Prompt')),
                shirt=[round(v) for v in shirt.get_actor_location().to_tuple()] if shirt else None, fade=round(prop(cam, 'fade_amount', -1) or 0, 2),
                pawn=[round(v) for v in P.get_actor_location().to_tuple()], head_cm=round((loc - head).length()),
                body_angle=round(ang, 1), moving=moving, body_seen_moving=bool(seen and moving and name not in ('CineCameraActor', 'BP_FoAPlayer_C')),
                stage=prop(D, 'ClothingSearchStage'))


def log(kind, **kw):
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), **kw)
    if S['toss'] is not None:
        row['since_toss'] = round(time.time() - S['toss'], 2)
    S['rows'].append(row)
    unreal.log('[chase_cutaway] ' + json.dumps(row, default=str))
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
    unreal.log('[chase_cutaway] finished ' + reason)


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
        if S['toss'] is not None and time.time() - S['shot'] >= 0.1:
            S['n'] += 1
            since = time.time() - S['toss']
            cmd('Shot showui filename=%s/%03d_t%03d.png -nosuffix' % (SHOTS, S['n'], int(since * 10)))
            S['shot'] = time.time()
            row = log('frame', shot=S['n'], **sample())
            if S['back'] is None and since > 1.0 and row['view'] == 'BP_FoAPlayer_C':
                S['back'] = time.time()
            if S['back'] is not None and time.time() - S['back'] > 1.5:
                return finish('cutaway_watched')
            if since > 12:
                return finish('no_return')
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
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); wait(0.8)
        elif ph == 6:  # fixture: the clue stages through the director's own functions (as pie_chase_final.py)
            for fn in ('StartClothingSearch', 'SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                D.call_method(fn, ())
            P.teleport(unreal.Vector(200.0, 40.0, 92.0), unreal.Rotator(0, 0, -90))  # on the floor, by the bed
            log('before_toss', **sample()); wait(0.6)
        elif ph == 7:
            S['toss'] = time.time()
            D.call_method('BeginClothingToss', ())
            log('toss'); wait(60)
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
