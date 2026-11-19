"""Story lane, in PIE (run_chase_final.py pie_chase_audit, one EXCLUSIVE window): QA B2's rule for every chase cutaway,
"frame the clothing and its motion, not his body". Real T7 (the fall, the search started by StageWrongWall), then each
chase step through the director's own functions with the pawn standing where a player catching the shirt would:
  toss (mode 1, from the bed stand), escape one (mode 2, from where the toss left him), escape two (mode 3, near the
  second landing), the vase (mode 4, the bay reach stand) and the boss frame.
Every 0.1 s while the director's camera owns the view: QA's view-check numbers (body bounds inside the field of view
+5 deg, camera outside the head) and a shot; per cutaway the first and middle frames go on the sheet.
Save-isolated. Shots: Saved/StoryShots/chase_audit/*.png. Result: Saved/StoryShots/chase_audit.json."""
import importlib
import json
import math
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/flow')
import proof_save  # noqa: E402
importlib.reload(proof_save)
from clothing_chase_contract import LANDINGS  # noqa: E402

OUT = Path('P:/FoA/Saved/StoryShots/chase_audit.json')
SHOTS = 'P:/FoA/Saved/StoryShots/chase_audit'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
for f in os.listdir(SHOTS):
    os.remove(os.path.join(SHOTS, f))
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, shot=0.0, n=0, cut=None, cuts=[])
D = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
BAG = P.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def view_numbers():
    cam = pc.player_camera_manager
    loc, fwd = cam.get_camera_location(), unreal.MathLibrary.get_forward_vector(cam.get_camera_rotation())
    body = prop(P, 'Body') or P.get_component_by_class(unreal.SkeletalMeshComponent)
    o, _, _ = unreal.SystemLibrary.get_component_bounds(body)
    head = body.get_socket_location('head')
    to = o - loc
    to.normalize()
    ang = math.degrees(math.acos(max(-1.0, min(1.0, fwd.x * to.x + fwd.y * to.y + fwd.z * to.z))))
    half = cam.get_fov_angle() / 2 + 5
    shirt = prop(D, 'SearchShirt')
    so, se = shirt.get_actor_bounds(False) if shirt else (None, None)
    sv = (so - loc) if shirt else None
    sd = sv.length() if shirt else 0
    if shirt:
        sv.normalize()
    s_ang = math.degrees(math.acos(max(-1.0, min(1.0, fwd.x * sv.x + fwd.y * sv.y + fwd.z * sv.z)))) if shirt else 180
    s_frac = (2 * max(se.x, se.y, se.z)) / (2 * max(sd, 1) * math.tan(math.radians(cam.get_fov_angle() / 2))) if shirt else 0
    extra = dict(shirt_cm=round(sd), shirt_in_view=bool(s_ang < cam.get_fov_angle() / 2), shirt_frac=round(s_frac, 2),
                 fov=round(cam.get_fov_angle()))
    return dict(**extra,cam=[round(v) for v in loc.to_tuple()], body_angle=round(ang, 1), half_fov=round(half, 1),
                head_cm=round((loc - head).length()), body_in_view=bool(ang < half and (loc - head).length() > 40))


def log(kind, **kw):
    vt = pc.get_view_target()
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, stage=prop(D, 'ClothingSearchStage'), beat=prop(D, 'BeatIndex'),
               view=vt.get_class().get_name() if vt else None, pawn=[round(v) for v in P.get_actor_location().to_tuple()], **kw)
    S['rows'].append(row)
    unreal.log('[chase_audit] ' + json.dumps(row, default=str))
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, cuts=S['cuts'], rows=S['rows']), indent=1, default=str))
    unreal.log('[chase_audit] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def stand(x, y, toward):
    P.teleport(unreal.Vector(x, y, 92.0), P.get_actor_rotation())
    eye = pc.player_camera_manager.get_camera_location()
    pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, unreal.Vector(*toward)))


def sample():
    vt = pc.get_view_target()
    director = vt is not None and vt.get_class().get_name() == 'BP_BeatDirector_C'
    if director and S['cut'] is None:
        S['cut'] = dict(name=S.get('label', '?'), start=time.time(), frames=[])
    if S['cut'] is not None and time.time() - S['shot'] >= 0.1:
        S['n'] += 1
        tag = '%03d_%s' % (S['n'], S['cut']['name'] if director else 'after')
        cmd('Shot showui filename=%s/%s.png -nosuffix' % (SHOTS, tag))
        S['shot'] = time.time()
        row = log('frame', cut=S['cut']['name'], file=tag, **view_numbers())
        if director:
            S['cut']['frames'].append(dict(file=tag, t=round(time.time() - S['cut']['start'], 2), body_in_view=row['body_in_view'],
                                           body_angle=row['body_angle'], cam=row['cam'], shirt_cm=row['shirt_cm'],
                                           shirt_in_view=row['shirt_in_view'], shirt_frac=row['shirt_frac'], fov=row['fov']))
    if not director and S['cut'] is not None and S['cut']['frames'] and time.time() - S['cut']['start'] > 0.5:
        c = S['cut']
        S['cuts'].append(dict(name=c['name'], frames=len(c['frames']), body_in_view=sum(f['body_in_view'] for f in c['frames']),
                              shirt_max_frac=max((f['shirt_frac'] for f in c['frames'] if f['shirt_in_view']), default=0),
                              shirt_min_cm=min((f['shirt_cm'] for f in c['frames'] if f['shirt_in_view']), default=None),
                              first=c['frames'][0], middle=c['frames'][len(c['frames']) // 2]))
        S['cut'] = None


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        el = time.time() - S['t0']
        if el > 47:
            return finish('timeout_phase_%d' % S['phase'])
        if S['phase'] >= 10:
            sample()
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
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            wait(0.3)
        elif ph == 7:  # T7 top-down with the search started; leave it early (fixture)
            if prop(D, 'BeatIndex') != 7 or not prop(D, 'bTopDown') or prop(D, 'ClothingSearchStage', 0) < 1:
                return
            D.call_method('ExitTopDown', ()); wait(1.0)
        elif ph == 8:  # clues to the snag (fixture), the hanger in the bag (fixture: S2 proves the real take)
            for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                D.call_method(fn, ())
            BAG.call_method('Add', ('Hanger',))
            stand(105, -110, (240, -140, 25))
            log('ready'); wait(0.4)
        elif ph == 9:
            S['label'] = 'toss'; S['phase'] = 10; D.call_method('BeginClothingToss', ()); log('toss')
        elif ph == 10:  # escape one from wherever the toss left him, looking at the shirt (after the toss cutaway ended)
            if not any(c['name'] == 'toss' for c in S['cuts']) or S['cut'] is not None or pc.get_view_target() != P:
                if time.time() - S.get('since', time.time()) > 9:
                    return finish('toss_cutaway_never_ended')
                S.setdefault('since', time.time())
                return
            S.pop('since', None)
            S['after'] = time.time() + 0.6; S['phase'] = 11
            stand(P.get_actor_location().x, P.get_actor_location().y, LANDINGS[0])
        elif ph == 11:
            S['label'] = 'escape_one'; S['phase'] = 12; D.call_method('EscapeClothingOne', ()); log('escape_one')
        elif ph == 12:
            if not any(c['name'] == 'escape_one' for c in S['cuts']) or S['cut'] is not None or pc.get_view_target() != P:
                return
            stand(LANDINGS[1][0] + 70, LANDINGS[1][1] + 60, LANDINGS[1])  # came from the first landing's side
            S['after'] = time.time() + 0.6; S['phase'] = 13
            S['check_focus'] = True
        elif ph == 13 and S.get('check_focus'):  # the second landing must be reachable: the normal Scan offers the shirt
            S['check_focus'] = False
            ia = P.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
            tgt = prop(ia, 'Target')
            log('landing_one_focus', target=tgt.get_actor_label() if tgt else None, prompt=str(prop(ia, 'Prompt')),
                shirt=[round(v) for v in prop(D, 'SearchShirt').get_actor_location().to_tuple()])
            return
        elif ph == 13:
            S['label'] = 'escape_two'; S['phase'] = 14; D.call_method('EscapeClothingTwo', ()); log('escape_two')
        elif ph == 14:
            if not any(c['name'] == 'escape_two' for c in S['cuts']) or S['cut'] is not None or pc.get_view_target() != P:
                return
            stand(-55, -250, LANDINGS[2])
            S['after'] = time.time() + 0.6; S['phase'] = 15
        elif ph == 15:
            S['label'] = 'vase_and_boss'; S['phase'] = 16; D.call_method('ReachClothingVase', ()); log('vase')
        elif ph == 16:
            if S['cut'] is not None or prop(D, 'ClothingSearchStage', 0) < 9:
                return
            finish('audited')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
