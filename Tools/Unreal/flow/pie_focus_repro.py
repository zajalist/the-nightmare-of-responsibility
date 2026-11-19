"""Native-E focus proof, one bounded PIE per FOA_FOCUS_CASE=boot (default) or bed.
Boot: focus holds, E grants the key, real E closes inspection, then walking away clears focus.
Bed: fixture T6 and the wardrobe's HandleOff notify; wait for the full transition, fixture the
three search clues and owned hanger, then require steady bed focus and native-E unhook.
Navigation never runs while paused, interaction-locked, Scan-suspended or mid camera blend.
run_chase_final.py pie_focus_repro relays keys; results: Saved/StoryShots/focus_repro.json.
"""
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

OUT = Path('P:/FoA/Saved/StoryShots/focus_repro.json')
INPUTS = Path('P:/FoA/Saved/StoryShots/focus_repro_input.json')
CASE = os.environ.get('FOA_FOCUS_CASE', 'boot')
assert CASE in ('boot', 'bed'), CASE
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, watch_end=0.0, last=0.0, dts=[], checks={})


def cls(path):
    return unreal.load_class(None, path)


D = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
IA = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
BAG = P.get_component_by_class(cls('/Game/FoA/Gameplay/BPC_Inventory.BPC_Inventory_C'))
BPI = cls('/Game/FoA/Gameplay/BPI_Interactable.BPI_Interactable_C')
ACT = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls('/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C'))}
BOOT = ACT['Boot_L']


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


BED = prop(D, 'SearchBed')


def v(x):
    return [round(x.x, 1), round(x.y, 1), round(x.z, 1)]


def candidates():
    cam = pc.player_camera_manager
    c, r = cam.get_camera_location(), cam.get_camera_rotation()
    fwd = r.get_forward_vector()
    pawn = P.get_actor_location()
    reach, radius = prop(IA, 'Reach', 200.0) or 200.0, prop(IA, 'Radius', 10.0) or 10.0
    length = (c - pawn).length() + reach
    end = c + fwd * length
    types = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2]
    hits = unreal.SystemLibrary.sphere_trace_multi_for_objects(w, c, end, radius, types, True, [], unreal.DrawDebugTrace.NONE,
                                                                True, unreal.LinearColor(), unreal.LinearColor(), 0.0)
    if isinstance(hits, tuple) and hits and isinstance(hits[0], bool):
        hits = hits[1]
    out = []
    for hit in hits or []:
        t = hit.to_tuple()
        initial, impact, actor, comp = t[1], t[5], t[9], t[10]
        if actor is None:
            continue
        if initial and comp:
            o, e, _ = unreal.SystemLibrary.get_component_bounds(comp)
            p = o
        else:
            p = impact
        d = (p - pawn).length()
        to = p - c
        dot = to.dot(fwd)
        n = to.normal()
        ang = math.degrees(math.acos(max(-1.0, min(1.0, n.dot(fwd)))))
        cost = ang + d / reach * 5.0
        ok_bpi = unreal.SystemLibrary.does_implement_interface(actor, BPI)
        out.append(dict(actor=actor.get_actor_label(), comp=comp.get_name() if comp else None, initial=bool(initial), p=v(p),
                        dist=round(d), dot=round(dot), angle=round(ang, 1), cost=round(cost, 2),
                        accepted=bool(ok_bpi and d <= reach and dot > 0)))
    best = min((x for x in out if x['accepted']), key=lambda x: x['cost'], default=None)
    return dict(cam=v(c), pitch=round(r.pitch, 1), yaw=round(r.yaw, 1), reach=reach, radius=radius,
                best=best['actor'] if best else None, hits=out)


def log(kind, **kw):
    tgt = prop(IA, 'Target')
    row = dict(t=round(time.time() - S['t0'], 2), kind=kind, beat=prop(D, 'BeatIndex'), stage=prop(D, 'ClothingSearchStage'),
               target=tgt.get_actor_label() if tgt else None, prompt=str(prop(IA, 'Prompt')),
               pawn=v(P.get_actor_location()), **kw)
    S['rows'].append(row)
    return row


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        current = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if current == w and unreal.SystemLibrary.is_valid(w):
            proof_save.restore(w, PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    c = S['checks']
    required = ('boot_steady', 'boot_committed', 'walkaway_clears') if CASE == 'boot' else ('wardrobe_completed', 'bed_steady', 'bed_committed')
    ok = reason == 'done' and all(c.get(k) for k in required)
    OUT.write_text(json.dumps(dict(case=CASE, reason=reason, verdict='GREEN' if ok else 'RED', checks=c, flickers=S.get('flickers'),
                                   rows=S['rows']), indent=1, default=str))
    unreal.log('[focus_repro] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def free():
    return (not unreal.GameplayStatics.is_game_paused(w) and not prop(P, 'bInteractionLocked')
            and not prop(P, 'bCinematic') and pc.get_view_target() == P and not pc.is_move_input_ignored()
            and not unreal.SystemLibrary.is_timer_paused(IA, 'Scan')
            and (pc.player_camera_manager.get_camera_location() - prop(P, 'FollowCamera').get_world_location()).length() < 5)


def close_inspect():
    inspector = unreal.GameplayStatics.get_actor_of_class(w, cls('/Game/FoA/UI/Game/BP_ItemInspect.BP_ItemInspect_C'))
    if inspector and prop(inspector, 'bOpen'):
        opened = S.setdefault('inspect_opened', time.time())
        if time.time() - opened >= .6 and not S.get('inspect_close_sent'):
            S['input_id'] = S.get('input_id', 0) + 1
            INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
            S['inspect_close_sent'] = True
            log('inspect_close_requested', key='E')
    else:
        S.pop('inspect_opened', None)
        S.pop('inspect_close_sent', None)


def stand(at, look):
    """teleport onto the first spot near `at` that keeps him on the floor, then aim from the camera's NEW place for 0.5 s
    (the camera follows the teleport a tick later, and the eye height settles)"""
    assert free(), 'Proof navigation attempted before interaction and camera release'
    for dx, dy in ((0, 0), (-15, 0), (0, 15), (0, -15), (-30, 0), (-15, 15), (-15, -15)):
        spot = unreal.Vector(at[0] + dx, at[1] + dy, at[2])
        if P.teleport(spot, unreal.Rotator(0, 0, 0)):
            break
    else:
        raise RuntimeError('Proof stand blocked at all candidate positions: %r' % (at,))
    S['aim'] = unreal.Vector(*look)
    S['aim_until'] = time.time() + 0.5


def aim():
    if S.get('aim') is not None and time.time() < S.get('aim_until', 0):
        eye = pc.player_camera_manager.get_camera_location()
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, S['aim']))


def bed_focus_pose():
    """Use the reachable left-front corner and aim at its nearby colliding surface."""
    origin, extent = BED.get_actor_bounds(True)
    north = origin.y + extent.y
    left = origin.x - extent.x
    return ((left - 47.0, north + 16.0, 92.0), (left, north - 16.0, origin.z))


def focus_scan():
    try:
        return candidates()
    except Exception as exc:
        return {'diagnostic_error': repr(exc)}


def steady_then_e(target, want, label):
    """True once a real E was sent after Target == target with a matching prompt held for 1 s (no flicker)"""
    tgt, prompt = prop(IA, 'Target'), str(prop(IA, 'Prompt'))
    good = tgt == target and want(prompt.lower())
    if not good:
        if S.get('steady_from'):
            S.setdefault('flickers', {}).setdefault(label, 0)
            S['flickers'][label] += 1
            log('flicker', what=label, saw=tgt.get_actor_label() if tgt else None, saw_prompt=prompt, scan=focus_scan())
        S['steady_from'] = 0.0
    elif not S.get('steady_from'):
        S['steady_from'] = time.time()
    if S.get('steady_from') and time.time() - S['steady_from'] >= 1.0:
        S['input_id'] = S.get('input_id', 0) + 1
        INPUTS.write_text(json.dumps(dict(id=S['input_id'], key='E')))
        log('press_E', what=label, sent_prompt=prompt)
        S['steady_from'] = 0.0
        return True
    if time.time() >= S['watch_end']:
        S['checks'][label + '_steady'] = False
        log('never_steady', what=label, scan=focus_scan())
        return True
    return False


def tick(dt):
    try:
        if S['done']:
            return
        if (unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() != w
                or not all(unreal.SystemLibrary.is_valid(o) for o in (w, D, P, IA, BAG, pc))):
            return finish('pie_gone')
        if CASE == 'bed' and not unreal.SystemLibrary.is_valid(BED):
            return finish('bed_gone')
        S['dts'].append(dt)
        if len(S['dts']) == 40:
            med = sorted(S['dts'])[20]
            log('fps', median_ms=round(med * 1000, 1))
            if med > 0.066:
                return finish('throttled_fps')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
        close_inspect()
        aim()
        ph = S['phase']
        if ph in (7, 11):  # wait for a steady prompt, then one real E
            label = 'boot' if ph == 7 else 'bed'
            if time.time() < S['after']:
                return
            if not S.get('scan_logged_' + label):
                S['scan_logged_' + label] = True
                log('focus_settled', what=label, scan=focus_scan())
            if not S.get('sent_' + label) and label + '_steady' not in S['checks']:
                if steady_then_e(BOOT if ph == 7 else BED, (lambda p: 'boot' in p) if ph == 7 else (lambda p: 'hanger' in p), label):
                    S['checks'].setdefault(label + '_steady', True)
                    if S['checks'][label + '_steady']:
                        S['sent_' + label] = time.time()
            if S.get('sent_' + label):
                done = ('Key' in [str(i) for i in (prop(BAG, 'Items') or [])]) if ph == 7 else (prop(D, 'ClothingSearchStage') or 0) >= 5
                if done or time.time() - S['sent_' + label] > 4.0:
                    S['checks'][label + '_committed'] = bool(done)
                    log('result', what=label, committed=bool(done)); wait(0.6)
            elif S['checks'].get(label + '_steady') is False:
                S['checks'][label + '_committed'] = False; wait(0.2)
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
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone')
            for ev in ('FirstSteps', 'Searched'):
                cmd('ke * ReportEvent ' + ev)
            log('to_t3'); wait(0.6)
        elif ph == 6:
            if not free():
                return
            if CASE == 'bed':
                D.call_method('EnterBeat', (6,))
                ACT['Wardrobe'].call_method('Interact', ('Notify', 'HandleOff'))
                S['phase'] = 9
                log('fixture_wardrobe_handleoff')
                return
            o, e = BOOT.get_actor_bounds(False)
            stand((90.0, -100.0, 92.0), (o.x, o.y, o.z))
            S['watch_end'] = time.time() + 8.6; log('watch_boot'); wait(0.6)
        elif ph == 8:
            if not S.get('walked'):  # the hold must not keep a target he walked away from: out of reach, still looking at it
                if not free():
                    return
                log('walk_from', free=free(), locked=prop(P, 'bInteractionLocked'), cine=prop(P, 'bCinematic'),
                    view=pc.get_view_target().get_name(), move_ignored=pc.is_move_input_ignored())
                o, e = BOOT.get_actor_bounds(False)
                stand((-230.0, 150.0, 92.0), (o.x, o.y, o.z))
                S['walked'] = time.time(); S['after'] = time.time() + 0.6  # longer than the 0.35 s hold
                return
            tgt = prop(IA, 'Target')
            S['checks']['walkaway_clears'] = tgt != BOOT
            log('walked_away', target_after=tgt.get_actor_label() if tgt else None)
            finish('done')
        elif ph == 9:
            if prop(D, 'bWardrobeTransition'):
                S['transition_seen'] = True
                return
            if not S.get('transition_seen') or prop(D, 'ClothingSearchStage', 0) < 1:
                return
            if prop(D, 'bTopDown'):
                D.call_method('ExitTopDown', ())
            if not free():
                return
            S['checks']['wardrobe_completed'] = True
            log('wardrobe_completed'); wait(.2)
        elif ph == 10:
            if not S.get('searched'):
                for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                    D.call_method(fn, ())
                BAG.call_method('Add', ('Hanger',))
                S['searched'] = time.time()
            if not free() or time.time() - S['searched'] < 1.0:
                return
            log('bed_from', free=free(), locked=prop(P, 'bInteractionLocked'), cine=prop(P, 'bCinematic'),
                view=pc.get_view_target().get_name(), move_ignored=pc.is_move_input_ignored())
            at, look = bed_focus_pose()
            stand(at, look)
            S['watch_end'] = time.time() + 8.6
            log('watch_bed', requested_stand=at, aim_point=look)
            wait(0.6)
        elif ph == 12:
            finish('done')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
INPUTS.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
