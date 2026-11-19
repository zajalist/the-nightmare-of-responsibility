"""PIE proof of walk-up-to-it (run by record_anim.sh as FOA_PIE_SCRIPT). Skips the wake-up, lets T0 open the phone by
itself and closes it (ClosePhone), then for the Door, CommodeDrawer and WardrobeDoor interactables (the wardrobe last,
and only once the headache beat has ended): stands the PIE pawn on the floor 100 cm out in front of it, facing it, and
sends Interact the way the player does. A fourth case stands 55 cm from the bedroom door looking at its lock (QA #16:
the scan never focused it that close). Samples every 0.1 s (a shot every 0.2 s) for 3.8 s. Before each Interact it logs
the interactor's focus and a replica of its scan sweep (each hit: actor, start-penetrating, impact point).
The script FAILS (its reason starts with FAILED) unless, for every target:
- the pawn stays on the floor: capsule z within 3 cm of FLOOR_Z for the whole walk-up (no stepping onto furniture),
  and the spot it ends on projects onto the navmesh, or onto the floor when the level has no navmesh;
- the interactor focuses the target before Interact (no focus = a scan bug, reported as such);
- a hand reaches the contact point: some hand bone within 12 cm of it while the interaction is locked (the contact point
  is EnvironmentContactAim; when that is unset (0,0,0) the nearest point of the target's bounds), and at that moment
  the hand projects inside the viewport and the camera pitch is between -65 and +15 deg;
- the contact point belongs to the target: within 15 cm of its bounds.
Ends with '[anim] done'. Output: Saved/AnimShots/approach/<stamp>/."""
import datetime
import json
import math
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

w = p = pc = fe = d = None
KEYS = ('Door', 'CommodeDrawer', 'WardrobeDoor')
CASES = (('Door', 100.0), ('Door', 55.0), ('CommodeDrawer', 100.0), ('WardrobeDoor', 100.0))  # (key, stand-off cm)
FLOOR_Z = 87.15  # capsule centre standing on the bedroom floor (measured, approach6)
HANDS = ('hand_l', 'hand_r', 'middle_01_l', 'middle_01_r')
folder = Path('P:/FoA/Saved/AnimShots/approach') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(start=time.monotonic(), phase=0, story=False, skipped=False, k=0, t0=None, rows=[], fin=False, targets=None)


def resolve():
    global w, p, pc, fe, d
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return False
    p = unreal.GameplayStatics.get_player_character(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
    return bool(w and fe and d)


def targets():
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    found = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls):
        try:
            key = str(a.get_editor_property('InteractionKey'))
        except Exception:
            continue
        if key in KEYS and key not in found:
            found[key] = a
    return [(found[k], d) for k, d in CASES if k in found]


def center_of(a):
    """World centre of the interactable's own mesh (the moving door/drawer piece), not the actor pivot."""
    m = a.get_editor_property('Mesh')
    lo, hi = m.get_local_bounds()
    return m.get_world_transform().transform_location((lo + hi) * 0.5)


def look_point(a):
    """Where the player looks: the door's lock (ToolContact) when it has one, else the piece's centre."""
    for c in a.get_components_by_class(unreal.SceneComponent):
        if c.get_name().startswith('ToolContact'):
            return c.get_world_location()
    return center_of(a)


def place(a, dist):
    """On the floor, `dist` cm out from the piece's centre toward the room centre (inside the room), facing it; the view
    is aimed on the next tick (aim()), once the camera has moved with the pawn."""
    o = center_of(a)
    to_room = unreal.Vector(-o.x, -o.y, 0.0)
    to_room = to_room * (1.0 / max(1.0, to_room.length()))
    x = max(-330.0, min(330.0, o.x + to_room.x * dist))
    y = max(-260.0, min(260.0, o.y + to_room.y * dist))
    spot = unreal.Vector(x, y, FLOOR_Z)
    p.set_actor_location_and_rotation(spot, unreal.Rotator(0, 0, math.degrees(math.atan2(o.y - y, o.x - x))), False, True)
    return spot


def aim(a):
    look = unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(), look_point(a))
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=look.pitch, yaw=look.yaw))


def scan_replica(it):
    """The interactor's sweep (camera out to camera-to-pawn distance + Reach, sphere Radius), every hit logged."""
    cam = pc.player_camera_manager
    start = cam.get_camera_location()
    reach, radius = it.get_editor_property('Reach'), it.get_editor_property('Radius')
    end = start + cam.get_camera_rotation().get_forward_vector() * ((start - p.get_actor_location()).length() + reach)
    try:
        hits = unreal.SystemLibrary.sphere_trace_multi_for_objects(
            w, start, end, radius, [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], True, [],
            unreal.DrawDebugTrace.NONE, True) or []
    except Exception as e:  # noqa: BLE001
        return dict(reach=reach, radius=radius, error=repr(e)[:200])
    out = []
    for hr in hits:
        t = hr.to_tuple()
        out.append(dict(actor=t[9].get_actor_label() if t[9] else None, start_pen=bool(t[1]),
                        impact=[round(v, 1) for v in t[5].to_tuple()]))
    return dict(reach=reach, radius=radius, hits=out[:8])


def interactor():
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C')
    return p.get_component_by_class(cls)


def shot(label):
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=' + str(folder / (label + '.png')) + ' -nosuffix', pc)


def on_screen(pos):
    r = unreal.GameplayStatics.project_world_to_screen(pc, pos, False)
    sp = r[1] if isinstance(r, tuple) else r
    if sp is None or (isinstance(r, tuple) and not r[0]):
        return False
    size = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    return bool(0 <= sp.x <= size.x and 0 <= sp.y <= size.y)


def on_nav(pos):
    """'nav' or 'floor' when the stand spot projects onto the navmesh, or (no navmesh) a trace down lands at floor level."""
    try:
        r = unreal.NavigationSystemV1.k2_project_point_to_navigation(w, pos, None, None, unreal.Vector(20, 20, 120))
        if (r[0] if isinstance(r, tuple) else r):
            return 'nav'
    except Exception:
        pass
    h = unreal.SystemLibrary.line_trace_single(w, pos, pos - unreal.Vector(0, 0, 200), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               False, [p], unreal.DrawDebugTrace.NONE, True)
    z = h.to_tuple()[4].z if h else None  # the impact point
    return 'floor' if z is not None and abs(z - (FLOOR_Z - 85.0)) < 4.0 else False


def sample(a, el):
    cam = pc.player_camera_manager
    body = p.get_editor_property('Body')
    aim = p.get_editor_property('EnvironmentContactAim')
    pts = {b: body.get_socket_location(b) for b in HANDS}
    src = 'contact aim'
    if aim.length() < 1.0 and p.get_editor_property('bInteractionLocked'):  # unset mid-interaction: the target's bounds
        o, ext = a.get_actor_bounds(False)
        q = pts[min(HANDS, key=lambda b: (pts[b] - o).length())]
        aim = unreal.Vector(*(min(max(v, c - e), c + e) for v, c, e in zip(q.to_tuple(), o.to_tuple(), ext.to_tuple())))
        src = 'target bounds'
    near = min(HANDS, key=lambda b: (pts[b] - aim).length())
    m = p.get_current_montage()
    loc = p.get_actor_location()
    return dict(target=a.get_actor_label(), t=round(el, 2), pawn=[round(loc.x, 1), round(loc.y, 1), round(loc.z, 2)],
                approaching=p.get_editor_property('bApproaching'), locked=p.get_editor_property('bInteractionLocked'),
                montage=m.get_name() if m else None, speed=round(p.get_velocity().length(), 1),
                pitch=round(cam.get_camera_rotation().pitch, 1), aim=[round(aim.x, 1), round(aim.y, 1), round(aim.z, 1)],
                hand=near, hand_cm=round((pts[near] - aim).length(), 1), hand_on_screen=on_screen(pts[near]), aim_source=src)


def judge(a, rows):
    """This target's failures (empty = pass); logged as a verdict row."""
    bad = []
    zs = [r['pawn'][2] for r in rows]
    if any(abs(z - FLOOR_Z) > 3.0 for z in zs):
        bad.append('%s left the floor: z %.1f..%.1f (floor %.2f)' % (a.get_actor_label(), min(zs), max(zs), FLOOR_Z))
    end = rows[-1]['pawn']
    nav = on_nav(unreal.Vector(end[0], end[1], end[2]))
    if not nav:
        bad.append('%s stand spot %s is not on the floor nav' % (a.get_actor_label(), end))
    lock = [r for r in rows if r['locked']]
    if not lock and 'Use' not in S.get('verbs', ['Use']):  # approach10: the wardrobe offers only Look before its story beat
        unreal.log('[anim] approach %s skipped: only %s offered at this beat (story gate, not an approach fault)' % (a.get_actor_label(), S['verbs']))
        return bad
    if not lock:
        bad.append('%s at %d cm: the interaction never started (verb %s)' % (a.get_actor_label(), S['dist'], S.get('verb')))
    best = min(lock or rows, key=lambda r: r['hand_cm'])
    if best['hand_cm'] > 12.0:
        bad.append('%s: no hand within 12 cm of the contact point (closest %s %.1f cm at %.2f s)' % (
            a.get_actor_label(), best['hand'], best['hand_cm'], best['t']))
    elif lock and (not best['hand_on_screen'] or not -65.0 <= best['pitch'] <= 15.0):  # a low door handle close up reads at -58
        bad.append('%s contact off-frame: hand on screen %s, pitch %.1f at %.2f s' % (
            a.get_actor_label(), best['hand_on_screen'], best['pitch'], best['t']))
    o, ext = a.get_actor_bounds(False)
    aim = best['aim']
    out = math.sqrt(sum(max(0.0, abs(q - c) - e) ** 2 for q, c, e in zip(aim, (o.x, o.y, o.z), (ext.x, ext.y, ext.z))))
    if out > 15.0:
        bad.append('%s contact point %s is %.0f cm outside the target' % (a.get_actor_label(), aim, out))
    if not S.get('focused'):
        bad.insert(0, '%s at %d cm: the interactor never focused it (scan)' % (a.get_actor_label(), S['dist']))
    shots = [r for r in rows if r.get('shot')]
    nearest = min(shots, key=lambda r: r['hand_cm'])['shot'] if shots else None  # the frame face measures skin on
    S['rows'].append(dict(verdict=a.get_actor_label(), dist=S['dist'], bad=bad, nav=nav, contact=best, nearest_shot=nearest))
    return bad


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_slot.leave(S)
    unreal.unregister_slate_post_tick_callback(S['h'])
    (folder / 'approach.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1))
    unreal.log('[anim] approach %s %s' % (reason, folder))
    unreal.log('[anim] done')


def tick(dt):
    try:
        if not proof_slot.enter_once(S):
            return
        t = time.monotonic() - S['start']
        if w is None or not unreal.SystemLibrary.is_valid(w):
            if not resolve():
                if t > 25:
                    finish('FAILED no PIE world')
                return
            S['start'] = time.monotonic(); return
        if t > 42:
            return finish('FAILED time_cap (%d of %d targets judged)' % (S['k'], len(S['targets'] or ())))
        if S['phase'] == 0 and t > .3:
            fe.call_method('OnSplashFinished', ()); S['phase'] = 1
        elif S['phase'] == 1 and t > 1:
            fe.call_method('OnTitleConfirmed', ()); S['phase'] = 2
        elif S['phase'] == 2 and t > 1.8:
            fe.call_method('WakeUp', ()); S['phase'] = 3
        if S['phase'] < 3:
            return
        story = fe.get_editor_property('Story')
        if story and story.is_in_viewport() and not S['story']:
            story.call_method('Finish', ()); S['story'] = True
            return
        sp = d.get_editor_property('SeqPlayer')
        if not S['skipped'] and sp and sp.is_playing() and not d.get_editor_property('bWakeDone'):
            d.call_method('SkipWakeUp', ()); S['skipped'] = True
            return
        if not d.get_editor_property('bWakeDone'):
            return
        if S['targets'] is None:
            # T0 opens the phone by itself after the hand-off (never forced); close it the way the player does
            if S.get('ready_t') is None:
                S['ready_t'] = t
            ph = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
            if not (ph and ph.get_editor_property('bOpen')):
                if t - S['ready_t'] > 9.0:
                    return finish('FAILED the T0 phone never opened by itself')
                return
            ph.call_method('ClosePhone', ())
            d.call_method('ReportEvent', (unreal.Name('FirstSteps'),))  # he has walked: T1's gate on Use lifts (QA slot)
            S['targets'] = targets()
            S['rows'].append(dict(found=[(a.get_actor_label(), d) for a, d in S['targets']], t0_open_after_handoff_s=round(t - S['ready_t'], 2)))
            S['t0'] = t + 1.0
            return
        if S['k'] >= len(S['targets']):
            bad = [b for r in S['rows'] if 'verdict' in r for b in r['bad']]
            if len(S['targets']) < len(CASES):
                bad.append('found only %s' % [(a.get_actor_label(), d) for a, d in S['targets']])
            return finish('FAILED ' + '; '.join(bad) if bad else 'passed')
        a, S['dist'] = S['targets'][S['k']]
        el = t - S['t0']
        if el < 0:
            return
        if S.get('placed') != S['k']:
            spot = place(a, S['dist']); S['placed'] = S['k']; S['sent'] = False; S['trows'] = []; S['aimed'] = False; S['cycled'] = 0; S.pop('verbs', None)
            S['rows'].append(dict(target=a.get_actor_label(), dist=S['dist'], start=[round(spot.x, 1), round(spot.y, 1), round(spot.z, 2)]))
            return
        if not S['aimed']:
            aim(a); S['aimed'] = True
            return
        m = p.get_current_montage()
        if not S['sent'] and (d.get_editor_property('bHeadacheActive') or (m and m.get_name() == 'AM_FoA_Headache')):
            S['t0'] = t; S['placed'] = None  # wait the headache beat out, then stand in front of it again
            return
        it = interactor()
        if not S['sent']:
            if el < 1.6 and it.get_editor_property('Target') != a:
                return  # give the focus scan up to 1.6 s to pick the target up
            if el < 0.6:
                return
            tg = it.get_editor_property('Target')
            S['focused'] = tg == a or (tg is not None and tg.get_actor_label().split('_')[0] == a.get_actor_label().split('_')[0])
            if str(it.get_editor_property('Verb')) != 'Use' and S.get('cycled', 0) < 2:
                it.call_method('CycleVerb', ()); S['cycled'] = S.get('cycled', 0) + 1
                return  # one tick for Refresh to pick the verb up
            S['verb'] = str(it.get_editor_property('Verb'))
            S['verbs'] = [str(v) for v in it.get_editor_property('Verbs')]
            S['rows'].append(dict(at=round(el, 2), focus=tg.get_actor_label() if tg else None, dist=S['dist'],
                                  verb=str(it.get_editor_property('Verb')), prompt=str(it.get_editor_property('Prompt')),
                                  verbs=[str(v) for v in it.get_editor_property('Verbs')], look_mode=it.get_editor_property('bLookMode'),
                                  scan=scan_replica(it)))
            it.call_method('Interact', ())
            S['sent'] = True; S['sent_t'] = el; S['next'] = el
        if el >= S['next']:
            r = sample(a, el - S['sent_t'])
            S['trows'].append(r); S['rows'].append(r)
            if len(S['trows']) % 2 == 1:
                r['shot'] = '%s%d_%02d' % (str(a.get_editor_property('InteractionKey')), S['dist'], len(S['trows']) // 2)
                shot(r['shot'])
            S['next'] += 0.1
        if el - S['sent_t'] > 3.8:
            judge(a, S['trows'])
            S['k'] += 1; S['t0'] = t + 0.5
    except Exception as e:
        S['rows'].append(dict(error=repr(e)))
        finish('FAILED error ' + repr(e))


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[anim] approach armed')
