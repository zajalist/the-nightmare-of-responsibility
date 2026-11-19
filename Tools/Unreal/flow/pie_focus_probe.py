"""Story lane, in PIE (run_chase_final.py pie_focus_probe, one EXCLUSIVE window): why BPC_Interactor's focus flickers on
low and bed-adjacent targets (QA B1/B2 and the boot probes, 2026-11-10). Read only: it never interacts.
It re-runs FindBest's own test in Python every 50 ms while the player looks down at the target from where QA's walk
stands him, and logs every candidate:
  sphere trace (Radius) for WorldStatic+WorldDynamic from the camera along its forward, length dist(cam, pawn) + Reach;
  per hit: P = ImpactPoint, or the hit component's bounds origin when the sweep starts inside it (bInitialOverlap);
  accepted if the actor implements BPI_Interactable, dist(pawn, P) <= Reach and (P - cam) . fwd > 0;
  cost = angle(P - cam, fwd) + dist(pawn, P) / Reach * 5, lowest wins.
Plus the camera's location and pitch (fp_lookdown slides it forward when pitched down) and the interactor's Target.
  1. T3: the boot (Boot_L) from (90, -100), looking at its bounds centre, 3 s.
  2. T7 ClothingSnag (fixtures to stage 4, Hanger carried): the bed from (105, -110), looking at the bed edge over the
     snag, 3 s.
Result: Saved/StoryShots/focus_probe.json."""
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

OUT = Path('P:/FoA/Saved/StoryShots/focus_probe.json')
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
S = dict(t0=time.time(), phase=0, after=0.0, rows=[], done=False, h=None, watch_end=0.0, last=0.0, dts=[])


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
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1, default=str))
    unreal.log('[focus_probe] finished ' + reason)


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def wait(sec):
    S['after'] = time.time() + sec
    S['phase'] += 1


def stand(at, look):
    """teleport onto the first spot near `at` that keeps him on the floor, then aim from the camera's NEW place for 0.5 s
    (the camera follows the teleport a tick later, and the eye height settles)"""
    for dx, dy in ((0, 0), (-15, 0), (0, 15), (0, -15), (-30, 0), (-15, 15), (-15, -15)):
        spot = unreal.Vector(at[0] + dx, at[1] + dy, at[2])
        if P.teleport(spot, unreal.Rotator(0, 0, 0)):
            break
    S['aim'] = unreal.Vector(*look)
    S['aim_until'] = time.time() + 0.5


def aim():
    if S.get('aim') is not None and time.time() < S.get('aim_until', 0):
        eye = pc.player_camera_manager.get_camera_location()
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(eye, S['aim']))


def watch(label):
    """log FindBest's test every 50 ms until the watch ends"""
    if time.time() - S['last'] >= 0.05:
        S['last'] = time.time()
        log('scan', what=label, **candidates())
    return time.time() >= S['watch_end']


def tick(dt):
    try:
        if S['done']:
            return
        if not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
            return finish('pie_gone')
        S['dts'].append(dt)
        if len(S['dts']) == 40:
            med = sorted(S['dts'])[20]
            log('fps', median_ms=round(med * 1000, 1))
            if med > 0.066:
                return finish('throttled_fps')
        if time.time() - S['t0'] > 46:
            return finish('timeout_phase_%d' % S['phase'])
        aim()
        ph = S['phase']
        if ph in (7, 11):
            if watch('boot' if ph == 7 else 'bed'):
                wait(0.2)
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
            o, e = BOOT.get_actor_bounds(False)
            stand((90.0, -100.0, 92.0), (o.x, o.y, o.z))
            S['watch_end'] = time.time() + 3.6; log('watch_boot'); wait(0.6)
        elif ph == 8:
            for ev in ('KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            log('to_t7'); wait(1.0)
        elif ph == 9:
            if not prop(D, 'bTopDown'):
                if time.time() - S['t0'] > 38:
                    return finish('no_topdown')
                S['after'] = time.time() + 0.3
                return
            D.call_method('ExitTopDown', ()); log('exit_topdown'); wait(1.5)
        elif ph == 10:
            for fn in ('SearchWardrobeClue', 'SearchDeskClue', 'SearchBedClue', 'CancelClothingInspection'):
                D.call_method(fn, ())
            BAG.call_method('Add', ('Hanger',))
            stand((105.0, -110.0, 92.0), (235.0, -135.0, 25.0))
            S['watch_end'] = time.time() + 3.6; log('watch_bed'); wait(0.6)
        elif ph == 12:
            finish('done')
    except Exception as exc:  # noqa: BLE001
        log('error', error=repr(exc))
        finish('error')


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
log('started')
