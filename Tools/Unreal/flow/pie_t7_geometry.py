"""Story lane, in PIE, read only (run_chase_final.py pie_t7_geometry, one EXCLUSIVE window): where the coat-rail hanger
can land when the wardrobe falls (QA S2, main 2026-11-10). Drives to T7 through the real fall, then, with the wardrobe
down and the pawn where the transition hands him back:
  floor spots for the hanger on a 15 cm grid between the rail and the room: a standing capsule (the player's own
  radius and half height) fits somewhere within the interactor's Reach of the spot, the spot is on the floor, and it is
  in plain view (clear line) from the pawn's eye where the transition left him.
-> Saved/StoryShots/t7_geometry.json, plus Saved/StoryShots/t7_geometry/*.png (his view at T7)."""
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

OUT = Path('P:/FoA/Saved/StoryShots/t7_geometry.json')
SHOTS = 'P:/FoA/Saved/StoryShots/t7_geometry'
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
PROOF = proof_save.isolate(w)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
os.makedirs(SHOTS, exist_ok=True)
S = dict(t0=time.time(), phase=0, after=0.0, done=False, h=None, rows=[])
D = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
P = unreal.GameplayStatics.get_player_character(w, 0)
STATIC = [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1]  # WorldStatic (WorldDynamic includes room-sized volumes)
VIS = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1


def prop(o, n, default=None):
    try:
        return o.get_editor_property(n)
    except Exception:  # noqa: BLE001
        return default


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def finish(reason, **data):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        proof_save.restore(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), PROOF)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning('[proof_save] restore failed: %r' % exc)
    OUT.write_text(json.dumps(dict(reason=reason, **data), indent=1, default=str))
    unreal.log('[t7_geometry] finished ' + reason)


def survey():
    actors = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)}
    hanger, rail, wardrobe = actors.get('Hanger_CoatRail'), actors.get('Dress_CoatRail_Door'), prop(D, 'Wardrobe')
    cap = P.get_component_by_class(unreal.CapsuleComponent)
    r, hh = cap.get_scaled_capsule_radius(), cap.get_scaled_capsule_half_height()
    ia = P.get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
    reach = prop(ia, 'Reach', 170.0)
    pawn = P.get_actor_location()
    eye = pawn + unreal.Vector(0, 0, 70)  # his eye after the cut back (the top-down camera may still own the view)
    wo, we = wardrobe.get_actor_bounds(False) if wardrobe else (None, None)
    hl = hanger.get_actor_location() if hanger else None
    ignore = [P] + ([hanger] if hanger else [])
    stands = []
    blockers = {}
    dir_blocks = [(c.get_name(), [v.to_tuple() for v in unreal.SystemLibrary.get_component_bounds(c)[:2]]) for c in D.get_components_by_class(unreal.PrimitiveComponent) if c.is_collision_enabled() and c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN) == unreal.CollisionResponseType.ECR_BLOCK]
    for x in range(-330, 441, 15):
        for y in range(-350, 281, 15):
            p = unreal.Vector(x, y, hh + 3)
            hit = unreal.SystemLibrary.capsule_overlap_actors(w, p, r, hh, STATIC, None, ignore)
            if hit:
                for a in hit:
                    blockers[a.get_actor_label()] = blockers.get(a.get_actor_label(), 0) + 1
                continue
            if wardrobe and abs(p.x - wo.x) < we.x + r and abs(p.y - wo.y) < we.y + r:
                continue  # the fallen wardrobe (moved at runtime; its collision channel may not be WorldStatic)
            down = unreal.SystemLibrary.line_trace_single(w, p, p - unreal.Vector(0, 0, 300), VIS, True, ignore, unreal.DrawDebugTrace.NONE, True)
            if down and abs(down.to_tuple()[4].z) < 6:
                stands.append(p)
    spots = []
    for x in range(-60, 431, 15):
        for y in range(60, 281, 15):
            s = unreal.Vector(x, y, 4)
            down = unreal.SystemLibrary.line_trace_single(w, s + unreal.Vector(0, 0, 60), s - unreal.Vector(0, 0, 60), VIS, True, ignore, unreal.DrawDebugTrace.NONE, True)
            if not down or abs(down.to_tuple()[4].z) > 6:
                continue  # not open floor (furniture or the fallen wardrobe on top)
            near = [st for st in stands if (unreal.Vector(st.x, st.y, 0) - unreal.Vector(s.x, s.y, 0)).length() <= reach - 20]
            if not near:
                continue
            seen = not unreal.SystemLibrary.line_trace_single(w, eye, s + unreal.Vector(0, 0, 3), VIS, True, ignore, unreal.DrawDebugTrace.NONE, True)
            spots.append(dict(spot=s.to_tuple(), stands=len(near), seen_from_t7=seen,
                              from_rail=round((s - hl).length()) if hl else None, from_pawn=round((s - pawn).length())))
    good = [sp for sp in spots if sp['seen_from_t7']]
    good.sort(key=lambda sp: (sp['from_rail'] or 0))
    return dict(pawn=pawn.to_tuple(), pawn_yaw=P.get_actor_rotation().yaw, eye=eye.to_tuple(), capsule=(r, hh), reach=reach,
                hanger=hl.to_tuple() if hl else None, hanger_state=str(prop(hanger, 'State')),
                rail=[v.to_tuple() for v in rail.get_actor_bounds(False)] if rail else None,
                wardrobe=dict(origin=wo.to_tuple(), extent=we.to_tuple()) if wardrobe else None,
                stands=len(stands), spots=len(spots), blockers=blockers, director_blockers=dir_blocks, stand_points=[(round(st.x), round(st.y)) for st in stands], good=good[:25])


def tick(dt):
    try:
        if S['done']:
            return
        el = time.time() - S['t0']
        if el > 46:
            return finish('timeout_phase_%d' % S['phase'])
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
            cmd('ke * ReportEvent PhoneWakeUp'); cmd('ke * ClosePhone'); S['after'] = time.time() + 0.6; S['phase'] += 1
        elif ph == 6:
            for ev in ('FirstSteps', 'Searched', 'KeyTaken', 'KeySnapped', 'LatchFreed', 'WardrobeLanded'):
                cmd('ke * ReportEvent ' + ev)
            S['phase'] += 1
        elif ph == 7:  # the fall done and the pawn handed back (the top-down hold may still run: the pawn is placed)
            if prop(D, 'BeatIndex') != 7 or prop(D, 'bWardrobeTransition'):
                return
            S['after'] = time.time() + 1.0; S['phase'] += 1
        elif ph == 8:
            data = survey()
            cmd('Shot showui filename=%s/t7_view.png -nosuffix' % SHOTS)
            finish('surveyed', **data)
    except Exception as exc:  # noqa: BLE001
        finish('error', error=repr(exc))


OUT.unlink(missing_ok=True)
S['h'] = unreal.register_slate_post_tick_callback(tick)
