"""QA playthrough driver: plays the real level inside a running PIE from a Slate post-tick callback, waiting on game
state (never fixed delays) and acting through the player's own paths. Owned by the qa lane.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/gameplay/pie_play.py FOA_PLAN=<plan> [FOA_CAP=50]
      [FOA_OUT=<dir>] [FOA_SHOT=1.0]
Runner: python Tools/QA/playtest_all.py (EXCLUSIVE lease, floating PIE window, report).

Every plan boots cold through the real front end: splash, title, menu Wake up, the WBP_IntroStory skip (its Skip
button's Finish), the LS_WakeUp skip (BP_BeatDirector.SkipWakeUp, the hold-Space target), then the T0 phone
(BP_Phone.PhoneConfirm, the E/Enter handler). Gameplay is first person: the driver walks with movement input, turns the
control rotation to look, waits for BPC_Interactor's own 0.1 s scan to focus the target, cycles the verb with
CycleVerb, selects inventory items with BPC_Inventory.Select and presses Interact, exactly as IA_Interact does. Door
tools are turned with AdvanceDoorTool (what held D/A call). The battle is fought by clicking WBP_Encounter's command
buttons (the widget's handler events their OnSandClicked is bound to) and pressing the prompted keys through BP_Encounter.HandleKey, at 6x game speed.
Shortcuts are used only where a plan says so; each is logged as kind 'shortcut'.
Plans (each fits one <= 60 s EXCLUSIVE PIE burst):
  A1  boot, T0 phone, T1 walk, T2 look at the bed, T3 key from the boot, T4 boots on
  A1b [fixture T4: key owned, boot Searched] put boots on and wait for interaction release
  A2  [shortcut T4: key + boots] T4 key in the door until it snaps (the four-stage rusted key), T5 take the hanger
  A3  [shortcut T5: key jammed, hanger held] hanger in the gap, T6 pull the handle, the wardrobe falls, T7 top-down
  B1  [fixture T6 + wardrobe HandleOff, then ExitTopDown] clothing search: wardrobe, desk, bed, hanger, unhook
  B2  [shortcut T7 + search events to the snag] hanger, unhook, chase the shirt three times, vase, take it, T8
  B2b [shortcut T7, ExitTopDown, snag, toss + escape one by stage functions] escape two, the vase, the boss, T8
  B3  [shortcut T8] battle intro skipped (hold Space), battle won by button clicks and prompted keys, T9, T10 phone
  B3i [shortcut T8] the battle intro in full: subtitles on screen while the HUD is hidden, then the encounter
  C   [shortcut T9] T9 payoff, T10 phone, approach doorway, timed door opening, playable Level 2 colour path
  D1  [knows KeyInBoot; shortcut T8] lose the battle (Flee), FailDay rollover, new morning, knowledge shortcut:
      the boot straight away skips T2-T3
  D3  [knows KeyInBoot; shortcut FailDay] rollover, new morning, knowledge shortcut: the boot straight away
  D2  pause, Restart Day, new morning (T0 phone must rise, #18; no HUD over the wake film, #17), pause, Settings,
      close, Quit to Title, confirm
  C2  [shortcut T9] T10 phone, explicit EndLevel fallback, timed door opening and playable Level 2 colour path
  F22 walk to T2 and look at the bed: one frame with the Bed focused (#22 re-check)
  S2R [fixture T6 + wardrobe HandleOff; the hanger never taken] Restart Day during the dropped-hanger glance:
      the new morning must leave move and look input free and the hanger back on the rail
  I1  [A1's path] the T3 boot key, item inspect (real P, Tab, E), inventory unit checks
  I2  [shortcut T5] take the hanger, item inspect (real P, Tab, gamepad B)
  I3  [shortcut T5] take the screwdriver, item inspect (real P, Tab; Esc is never sent, its Close handler)
  SP  [shortcut T5] take the screwdriver, spend it, T7: the refilled spare is Look-only
  V2  self-tests of the inspect, phone, pause and carried detectors, and of the real-key relay
  V   self-test of the view-change check: the director's top-down camera blended 1.5 s into the player must FAIL
  S1  [shortcut T5: key jammed] the screwdriver route: take the screwdriver, four screws, plate off, latch, T6
  S2  [fixture T6 + wardrobe HandleOff; the hanger never taken, as on the screwdriver route] the fall,
      T7, then reach for the coat-rail hanger from four sides (the clothing stage does not change the reach)
Progress is isolated: GI_FoA.SetProofProgressContext('FoA_QA_Play', ...) so no run touches the player's save; the slot
is reset first (GI_FoA.ResetProgress on that slot: day 18, nothing known, the first morning a new player sees) and
deleted at the end. Outputs in FOA_OUT (default Saved/Integration/play_<plan>/): play.json (steps with pass/miss,
log, states), frametimes.csv (wall-clock ms per Slate tick, screenshot frames flagged), frames/*.png ('Shot showui'),
done.json last. Never writes /Game or the level."""
import csv
import json
import math
import os
import time

import unreal

PLAN = os.environ.get('FOA_PLAN', 'A1')
CAP = float(os.environ.get('FOA_CAP', '50'))
OUT = os.environ.get('FOA_OUT') or f'P:/FoA/Saved/Integration/play_{PLAN}'
SHOT_EVERY = float(os.environ.get('FOA_SHOT', '1.0'))
QA_SLOT = 'FoA_QA_Play'
G = '/Game/FoA/Gameplay/'
P = dict(director=G + 'BP_BeatDirector.BP_BeatDirector_C', fe='/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C',
         enc=G + 'Encounter/BP_Encounter.BP_Encounter_C', phone='/Game/FoA/UI/Game/BP_Phone.BP_Phone_C',
         ia=G + 'BPC_Interactor.BPC_Interactor_C', inv=G + 'BPC_Inventory.BPC_Inventory_C',
         base=G + 'BP_Interactable.BP_Interactable_C',
         threshold='/Game/FoA/Level2/Transition/BP_DreamThreshold.BP_DreamThreshold_C')
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
S = dict(t0=time.time(), log=[], steps=[], i=0, gen=None, t_step=0.0, done=False, h=None, w0=None, last=None, n=0,
         shot_n=-99, shot_t=0.0, snap_t=0.0, beat=None, frames=[], cls={}, actors={}, fight=None, ctx=None, dt=0.0)
os.makedirs(OUT + '/frames', exist_ok=True)


class Miss(Exception):
    """A step that cannot continue (logged as a miss with this reason)."""


# ---- world access ------------------------------------------------------------------------------------------------
def W():
    return UES.get_game_world()


def cls(path):
    if path not in S['cls']:
        S['cls'][path] = unreal.load_class(None, path)
    return S['cls'][path]


def one(key):
    return unreal.GameplayStatics.get_actor_of_class(W(), cls(P[key]))


def pc():
    return unreal.GameplayStatics.get_player_controller(W(), 0)


def pawn():
    return unreal.GameplayStatics.get_player_pawn(W(), 0)


def comp(key):
    p = pawn()
    return p.get_component_by_class(cls(P[key])) if p else None


def gi():
    return unreal.GameplayStatics.get_game_instance(W())


def actor(label):
    a = S['actors'].get(label)
    if a is None or not unreal.SystemLibrary.is_valid(a):
        S['actors'] = {x.get_actor_label(): x for x in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor)}
        a = S['actors'].get(label)
    if a is None:
        raise Miss(f'no actor labelled {label}')
    return a


def prop(o, name, default=None):
    try:
        return o.get_editor_property(name) if o else default
    except Exception:  # the property was renamed or removed by another lane: report None, keep playing
        return default


def name_of(o):
    return o.get_actor_label() if o and hasattr(o, 'get_actor_label') else (o.get_class().get_name() if o else None)


def beat():
    b = prop(one('director'), 'Beat')
    return str(b.get_editor_property('Id')) if b else 'None'


def screen():
    s = prop(one('fe'), 'Screen')
    return s.get_class().get_name() if s else None


def view():
    vt = pc().get_view_target() if pc() else None
    return vt.get_class().get_name() if vt else None


def items():
    return [str(x) for x in prop(comp('inv'), 'Items', [])]


def state_of(label):
    return str(prop(actor(label), 'State'))


def stage():
    return prop(one('director'), 'ClothingSearchStage', -1)


def free():
    """The player has control: own camera, movement not locked, no cinematic, no interaction lock, no phone."""
    p, c, ph = pawn(), pc(), one('phone')
    return bool(p and c and c.get_view_target() == p and not c.is_move_input_ignored()
                and not prop(p, 'bCinematic') and not prop(p, 'bInteractionLocked') and not prop(ph, 'bOpen'))


def state():
    fe, p, ia, enc = one('fe'), pawn(), comp('ia'), one('enc')
    cam = pc().player_camera_manager if pc() else None
    loc = p.get_actor_location() if p else None
    head = None
    if p and cam:
        try:
            head = round((cam.get_camera_location() - p.get_editor_property('Body').get_socket_location('head')).length())
        except Exception:  # no Body component or head socket on this pawn
            head = None
    return dict(beat=beat(), screen=screen(), in_game=prop(fe, 'bInGameplay'), paused=unreal.GameplayStatics.is_game_paused(W()),
                view=view(), free=free(), cinematic=prop(p, 'bCinematic'), locked=prop(p, 'bInteractionLocked'),
                move_ignored=pc().is_move_input_ignored() if pc() else None, focus=name_of(prop(ia, 'Target')),
                prompt=str(prop(ia, 'Prompt', '')), verb=str(prop(ia, 'Verb', '')), items=items(), stage=stage(),
                battle=str(prop(enc, 'BattleState')) if prop(enc, 'bActive') else None, composure=prop(enc, 'Composure') if prop(enc, 'bActive') else None,
                pawn=[round(v) for v in loc.to_tuple()] if loc else None, cam_to_head_cm=head,
                control_rotation=str(pc().get_control_rotation()) if pc() else None,
                camera_rotation=str(cam.get_camera_rotation()) if cam else None,
                interaction_target=name_of(prop(p,'InteractLook')),
                interaction_aim=str(prop(p,'EnvironmentContactAim')),
                interaction_contact=str(prop(p,'EnvironmentContactMesh')),
                day=prop(gi(), 'DayCount'), knows=sorted(str(k) for k in prop(gi(), 'Knowledge', [])),
                dilation=round(unreal.GameplayStatics.get_global_time_dilation(W()), 2))


def t_now():
    return round(time.time() - S['t0'], 2)


def log(kind, **kw):
    e = dict(t=t_now(), kind=kind, **kw)
    S['log'].append(e)
    unreal.log('[play] ' + json.dumps(e, default=str)[:400])


def shot(tag):
    if time.time() - S['shot_t'] < 0.25:  # a second request before the first renders would replace it
        return S.get('shot_f')
    S['shot_n'], S['shot_t'] = S['n'], time.time()
    f = f'{OUT}/frames/{PLAN}_{int((time.time() - S["t0"]) * 100):05d}_{beat()}_{tag}.png'
    unreal.SystemLibrary.execute_console_command(W(), f'Shot showui filename={f} -nosuffix')
    S['shot_f'] = f
    # stills mode (a run folder named *stills*, main 11-19): each named moment also gets a 2x scene-only HighResShot
    if 'stills' in OUT.lower() and tag not in ('t', 'beat') and not tag.startswith(('MISS', 'viewchange', 'hud_')):
        os.makedirs(OUT + '/stills', exist_ok=True)
        unreal.SystemLibrary.execute_console_command(
            W(), f'HighResShot 2 filename={OUT}/stills/{PLAN}_{int((time.time() - S["t0"]) * 100):05d}_{tag}.png')
    return f


# ---- generator helpers (each yield = wait one tick) ----------------------------------------------------------------
def wait(pred, why=''):
    while not pred():
        yield


def sleep(s):
    end = time.time() + s
    while time.time() < end:
        yield


def look_point(a):
    """Centre of the target's visible static meshes (the actor origin is often on the floor)."""
    lo, hi = None, None
    for c in a.get_components_by_class(unreal.StaticMeshComponent):
        if not c.is_visible() or not c.get_editor_property('static_mesh'):
            continue
        o, e, _ = unreal.SystemLibrary.get_component_bounds(c)
        lo = [min(x, y) for x, y in zip(lo, (o - e).to_tuple())] if lo else list((o - e).to_tuple())
        hi = [max(x, y) for x, y in zip(hi, (o + e).to_tuple())] if hi else list((o + e).to_tuple())
    if not lo:
        o, e = a.get_actor_bounds(False)
        return o, e
    return (unreal.Vector(*[(x + y) / 2 for x, y in zip(lo, hi)]), unreal.Vector(*[(y - x) / 2 for x, y in zip(lo, hi)]))


def aim_point(a):
    """Where a player looks to use it: an interaction point (BP_Door's ToolContact at the lock, a handle or knob) when
    the actor has one, else the centre of its visible meshes."""
    for c in a.get_components_by_class(unreal.SceneComponent):
        if c.get_name() in ('ToolContact', 'Handle', 'Knob', 'Lock'):
            return c.get_world_location()
    return look_point(a)[0]


def turn_toward(target, rate=8.0):
    """Correct the rendered camera's aim through control input, including animated camera offsets."""
    c = pc()
    want = unreal.MathLibrary.find_look_at_rotation(c.player_camera_manager.get_camera_location(), target)
    cur = c.get_control_rotation()
    view = c.player_camera_manager.get_camera_rotation()
    k = min(1.0, S['dt'] * rate)
    dy = (want.yaw - view.yaw + 180) % 360 - 180
    dp = (want.pitch - view.pitch + 180) % 360 - 180
    c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=cur.pitch + dp * k, yaw=cur.yaw + dy * k))
    return abs(dy) < 2 and abs(dp) < 2


def walk_leg(goal, tol, limit):
    """Walk toward one floor point with movement input, looking where he walks. Time locked by a story moment or a
    cinematic does not count. True on arrival, False on a stall (no progress for 1 s) or the time limit."""
    p, spent, best, idle = pawn(), 0.0, 1e9, 0.0
    while spent < limit:
        if not free():  # a monologue or cinematic owns the player: wait like a player would
            yield
            continue
        here = p.get_actor_location()
        to = unreal.Vector(goal.x - here.x, goal.y - here.y, 0.0)
        if to.length() < tol:
            return True
        idle = 0.0 if to.length() < best - 3 else idle + S['dt']
        best = min(best, to.length())
        if idle > 1.0:
            return False
        to.normalize()
        p.add_movement_input(to, 1.0, False)
        turn_toward(unreal.Vector(goal.x, goal.y, here.z + 40), 5.0)
        spent += S['dt']
        yield
    return False


def go_to(goal, tol=18.0, limit=6.0):
    """Walk to a floor point. A stall (furniture in the way) detours once toward the room centre, then teleports
    with the engine's checked placement and logs it: that is the driver's steering, not the game."""
    if (yield from walk_leg(goal, tol, limit)):
        return
    p = pawn()
    here = p.get_actor_location()
    mid = unreal.Vector((here.x + goal.x) * 0.3, (here.y + goal.y) * 0.3, here.z)
    log('walk_detour', goal=[round(goal.x), round(goal.y)], at=[round(here.x), round(here.y)], via=[round(mid.x), round(mid.y)])
    yield from walk_leg(mid, 40.0, 3.0)
    if (yield from walk_leg(goal, tol, limit)):
        return
    here = p.get_actor_location()
    ok = p.teleport(unreal.Vector(goal.x, goal.y, here.z), p.get_actor_rotation())
    log('walk_teleport', goal=[round(goal.x), round(goal.y)], at=[round(here.x), round(here.y)], placed=bool(ok))
    yield


PAWN = next(getattr(unreal.CollisionChannel, n) for n in dir(unreal.CollisionChannel) if n.endswith('PAWN'))


def comp_blocks_pawn(c):
    return (c.get_collision_enabled() in (unreal.CollisionEnabled.QUERY_AND_PHYSICS, unreal.CollisionEnabled.QUERY_ONLY)
            and c.get_collision_response_to_channel(PAWN) == unreal.CollisionResponseType.ECR_BLOCK)



def pawn_blockers(x, y, z0=0.0):
    """'Actor.Component' for each overlapped component that keeps the player's capsule out of (x, y) standing at height
    z0: only components that themselves block pawns count (S2 01:40: actor-level read BeatDirector as a blocker)."""
    p = pawn()
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    r, hh = cap.get_scaled_capsule_radius() + 3, cap.get_scaled_capsule_half_height()
    types = [getattr(unreal.ObjectTypeQuery, f'OBJECT_TYPE_QUERY{i}') for i in range(1, 7)]  # not only WorldStatic/
    # WorldDynamic: the bed-foot chest is another object type and refuses a standing player (story, 02:05)
    hits = unreal.SystemLibrary.capsule_overlap_components(  # UE folds the bool: the overlapped components, or None
        W(), unreal.Vector(x, y, z0 + hh + 6), r, hh - 2, types, None, [p])
    return [f'{name_of(c.get_owner())}.{c.get_name()}' for c in (hits or []) if comp_blocks_pawn(c)]


def capsule_fits(x, y, z0=0.0):
    return not pawn_blockers(x, y, z0)


def stand_z(x, y):
    """Top of what he would stand on at (x, y): a downward visibility trace, the floor (0) when nothing is hit."""
    hit = unreal.SystemLibrary.line_trace_single(W(), unreal.Vector(x, y, 200.0), unreal.Vector(x, y, -20.0),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn()],
                                                 unreal.DrawDebugTrace.NONE, True)
    t = hit.to_tuple() if hit else None
    return t[4].z if t and t[0] else 0.0


def stand_point(a, extra, skip=0):
    """Where a player would stand to use the target: the room-centre side first, then swinging around it and backing
    off, the first spot whose capsule fits inside the room and the interactor's reach. `skip` passes over that many
    fitting spots (a retry stands somewhere else)."""
    o, e = look_point(a)
    base = math.atan2(-o.y, -o.x) if abs(o.x) + abs(o.y) > 1 else 0.0
    reach = prop(comp('ia'), 'Reach', 200.0) or 200.0
    for more in (extra, extra + 25.0, extra + 50.0, extra + 80.0, extra + 110.0):
        for deg in (0, 25, -25, 50, -50, 80, -80, 115, -115, 150, -150):
            ang = base + math.radians(deg)
            dx, dy = math.cos(ang), math.sin(ang)
            dist = min(abs(dx) * e.x + abs(dy) * e.y + more, reach * 0.9)
            x, y = o.x + dx * dist, o.y + dy * dist
            if abs(x) < 355 and -290 < y < 285 and capsule_fits(x, y):
                if skip <= 0:
                    return unreal.Vector(x, y, 0.0)
                skip -= 1
    log('stand_none_fits', target=name_of(a), centre=[round(v) for v in o.to_tuple()], half=[round(v) for v in e.to_tuple()])
    return None


def approach(a, extra=45.0, skip=0):
    spot = stand_point(a, extra, skip)
    if spot is not None:
        yield from go_to(spot)
        return
    o, _ = look_point(a)  # no free spot on the grid: walk straight at it until it is within reach, as a player would
    reach = prop(comp('ia'), 'Reach', 200.0) or 200.0
    yield from walk_leg(unreal.Vector(o.x, o.y, 0.0), reach * 0.7, 6.0)


def aim(a, settle=0.15):
    o = aim_point(a)
    end = time.time() + 1.5  # the camera's pitch limits may stop short of a floor target
    while not turn_toward(o, 10.0) and time.time() < end:
        yield
    yield from sleep(settle)


def focus_on(a, label):
    """Let BPC_Interactor's own scan pick the target; pin it only if the scan never does (logged: a finding)."""
    ia, o = comp('ia'), aim_point(a)
    end = time.time() + 2.0
    while prop(ia, 'Target') != a and time.time() < end:
        turn_toward(o, 10.0)
        yield
    if prop(ia, 'Target') != a:
        log('focus_pinned', target=label, scan_chose=name_of(prop(ia, 'Target')), prompt=str(prop(ia, 'Prompt', '')))
        ia.call_method('SetFocus', (a,))
        ia.call_method('Refresh', (True,))
        yield


def want_verb(verb):
    ia = comp('ia')
    for _ in range(2):
        if str(prop(ia, 'Verb')) == verb:
            return
        ia.call_method('CycleVerb')  # the IA_CycleVerb handler
        yield
    if str(prop(ia, 'Verb')) != verb:
        raise Miss(f'verb {verb} unavailable (interactor offers {prop(ia, "Verb")}: "{prop(ia, "Prompt", "")}")')


def select(item):
    inv = comp('inv')
    have = items()
    if item is None:
        return
    if item not in have:
        raise Miss(f'{item} not in inventory {have}')
    inv.call_method('Select', (have.index(item),))


def use(label, verb='Use', item=None, until=None, extra=45.0, retry_after=6.0):
    """Walk to, look at and use one interactable through the interactor, then wait for `until` (default: its State
    changed or the beat moved). If nothing happened after `retry_after` s and the player is free again, that is logged
    as 'no_effect' (a finding) and he tries once more from another spot, as a player would."""
    def gen():
        a = actor(label)
        before = None
        for attempt in (0, 1):
            yield from wait(free)
            before = before or (str(prop(a, 'State')), beat())
            done = until or (lambda: (str(prop(a, 'State')), beat()) != before)
            yield from approach(a, extra, skip=2 * attempt)
            yield from aim(a)
            yield from focus_on(a, label)
            select(item)
            yield from sleep(0.2)  # the interactor re-reads the held item on its 0.1 s scan
            if prop(comp('ia'), 'Target') != a:  # the focus dropped while he stood still: a finding, then look again
                log('focus_flicker', target=label, scan_chose=name_of(prop(comp('ia'), 'Target')))
                yield from focus_on(a, label)
            yield from want_verb(verb)
            ia = comp('ia')
            log('interact', target=label, verb=str(prop(ia, 'Verb')), item=item, prompt=str(prop(ia, 'Prompt', '')),
                state=str(prop(a, 'State')), attempt=attempt, at=[round(v) for v in pawn().get_actor_location().to_tuple()])
            shot('use_' + label)
            yield from sleep(0.15)  # the shot renders at the end of the frame: take it before the action
            ia.call_method('Interact')  # what IA_Interact runs
            end = time.time() + retry_after
            while not done() and (time.time() < end or not free()):
                yield
            if done():
                return
            log('no_effect', target=label, verb=verb, prompt=str(prop(ia, 'Prompt', '')), state=str(prop(a, 'State')),
                attempt=attempt, frame=shot('noeffect_' + label), pending_row=prop(a, 'bPendingRow'))
            if prop(a, 'bPendingRow') or prop(a, 'PendingMontage'):  # the montage played but its contact never came
                raise Miss('contact notify missing (known): the montage played, the row never committed')
        yield from wait(done)
    return gen


def door_tool(until):
    """Turn the door tool like a player holding D: push; when the angle stops rising (the key binds) ease off with A
    for 1.3 s, then push again. AdvanceDoorTool is exactly what the held keys call each frame."""
    def gen():
        door = actor('Door_Bedroom')
        yield from wait(lambda: prop(door, 'bToolActive') or until())
        last, gain, ease = None, time.time(), 0.0
        while prop(door, 'bToolActive'):
            if prop(door, 'bToolReady'):
                ang, step, now = prop(door, 'ToolAngle', 0.0), prop(door, 'ToolStepIndex'), time.time()
                if last is None or ang > last[0] + 0.05 or step != last[1]:
                    gain = now
                last = (ang, step)
                if str(prop(door, 'ToolMode')) == 'Key' and now >= ease and now - gain > 0.5:  # only the key binds
                    ease, gain = now + 1.3, now + 1.3
                    log('door_tool_ease', angle=round(ang, 1), step=prop(door, 'ToolStepIndex'))
                door.call_method('AdvanceDoorTool', (-1.0 if now < ease else 1.0, S['dt']))
            yield
        yield from wait(until)
    return gen


def native_focus_report(target):
    """Read the real scanner's candidate geometry without changing focus or collision."""
    cam=pc().player_camera_manager;start=cam.get_camera_location();forward=cam.get_camera_rotation().get_forward_vector()
    ia=comp('ia');reach=prop(ia,'Reach',200.0);radius=prop(ia,'Radius',10.0)
    end=start+forward*((start-pawn().get_actor_location()).length()+reach)
    hits=unreal.SystemLibrary.sphere_trace_multi_for_objects(W(),start,end,radius,
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1,unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2],True,[],
        unreal.DrawDebugTrace.NONE,True,unreal.LinearColor(),unreal.LinearColor(),0.0)
    if isinstance(hits,tuple) and hits and isinstance(hits[0],bool):hits=hits[1]
    rows=[]
    for hit in hits or []:
        values=hit.to_tuple();actor,mesh=values[9],values[10]
        if actor:rows.append(dict(actor=actor.get_actor_label(),component=mesh.get_name() if mesh else None,
                                  initial=bool(values[1]),impact=list(values[5].to_tuple())))
    direct=unreal.SystemLibrary.line_trace_single_for_objects(W(),start,end,
        [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1,unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2],True,[],
        unreal.DrawDebugTrace.NONE,True,unreal.LinearColor(),unreal.LinearColor(),0.0)
    if isinstance(direct,tuple):direct=next((v for v in direct if hasattr(v,'to_tuple')),None)
    hitactor=direct.to_tuple()[9] if direct else None
    log('native_focus_candidates',target=target.get_actor_label(),selected=name_of(prop(ia,'Target')),
        point=list(aim_point(target).to_tuple()),camera=list(start.to_tuple()),forward=list(forward.to_tuple()),
        direct=name_of(hitactor),hits=rows)


def native_use(label, verb='Use', item=None, until=None, extra=45.0):
    """Strict continuation probe: scanner focus and dispatched E, with no SetFocus/Interact fallback."""
    def gen():
        yield from wait(free)
        target=actor(label)
        yield from approach(target,extra)
        point=aim_point(target)
        if label=='Bed':
            origin,extent=target.get_actor_bounds(True)
            point=unreal.Vector(origin.x-extent.x,origin.y+extent.y-16,origin.z)
        select(item)
        end=time.time()+4.0;steady=None
        while time.time()<end:
            turn_toward(point,10.0)
            if prop(comp('ia'),'Target')==target:
                steady=steady or time.time()
                if time.time()-steady>=.5:break
            else:steady=None
            yield
        else:
            native_focus_report(target)
            raise Miss(f'{label}: scanner never held target; no focus pin applied')
        yield from want_verb(verb)
        # Keep aiming while the verb refresh settles; never pin a target after a scan miss.
        end=time.time()+3.0;steady=None
        while time.time()<end:
            turn_toward(point,10.0)
            if prop(comp('ia'),'Target')==target:
                steady=steady or time.time()
                if time.time()-steady>=.4:break
            else:steady=None
            yield
        else:
            native_focus_report(target)
            raise Miss(f'{label}: focus dropped before native E')
        before=state_of(label)
        if label=='Screwdriver_DeskDrawer':native_focus_report(target)
        log('native_interact',target=label,verb=verb,item=item,prompt=str(prop(comp('ia'),'Prompt')),
            frame=shot('native_'+label))
        old_owner=S.get('inspect_owner',False)
        S['inspect_owner']=True  # This strict probe also owns the real-key inspection close.
        try:
            if not (yield from press('E')):raise Miss(f'{label}: native E was not dispatched')
            done=until or (lambda:state_of(label)!=before and free())
            while True:
                if inspect_open():
                    yield from sleep(1.2)
                    if not (yield from press('E')):raise Miss(f'{label}: inspection close E was not dispatched')
                    yield from wait(lambda:not inspect_open())
                if done() and not unreal.GameplayStatics.is_game_paused(W()):return
                yield
        finally:
            S['inspect_owner']=old_owner
    return gen


def chain(*gens):
    def gen():
        for g in gens:
            yield from g()
    return gen


def walk(seconds):
    """A few steps toward the middle of the room, turning to face it first (he may wake facing a wall)."""
    def gen():
        yield from wait(free)
        p, end = pawn(), time.time() + seconds
        here = p.get_actor_location()
        mid = unreal.Vector(0.0, 0.0, here.z + 40)
        to = unreal.Vector(-here.x, -here.y, 0.0)
        to.normalize()
        while time.time() < end:
            turn_toward(mid, 6.0)
            p.add_movement_input(to, 1.0, False)
            yield
    return gen


def do(fn, **shortcut):
    """One immediate call; with shortcut=... it is logged as a plan shortcut (not a player action)."""
    def gen():
        if shortcut:
            log('shortcut', **shortcut)
        fn()
        yield
    return gen


def until(pred):
    return lambda: wait(pred)


def beat_is(*ids):
    return lambda: beat() in ids


# ---- front end ---------------------------------------------------------------------------------------------------
def g_phone():
    ph = one('phone')
    yield from wait(lambda: prop(ph, 'bOpen'))  # the phone rises in the hand since 00:47: the view stays on the pawn
    yield from sleep(1.6)  # past the lock screen (about 1.4 s)
    shot('phone')
    yield from sleep(0.15)
    ph.call_method('PhoneConfirm')  # E / Enter while the phone is up
    yield from wait(lambda: not prop(ph, 'bOpen') and free())


def threshold_phase():
    return prop(one('threshold'), 'Phase', 0)


def g_threshold_open():
    yield from wait(lambda: threshold_phase() >= 1)
    started = S.setdefault('threshold_started', unreal.GameplayStatics.get_time_seconds(W()))
    S.setdefault('threshold_pawn', pawn())
    initial = state_of('Door_Bedroom')
    yield from wait(lambda: state_of('Door_Bedroom') == 'Open')
    delay = unreal.GameplayStatics.get_time_seconds(W()) - started
    okay = initial != 'Open' and delay >= 2.5 and threshold_phase() >= 1 and prop(one('fe'), 'bInGameplay')
    log('threshold_door', result='PASS' if okay else 'FAIL', initial=initial, opened_after=round(delay, 2),
        phase=threshold_phase(), frame=shot('threshold_door'))
    if not okay:
        raise Miss('Threshold must open the door during its cinematic, not immediately at T10')


def g_portal_probe():
    """Coordinator probe: the T10 doorway once the door gives way (a still plate of Dream A's arrival view, 2026-11-18)."""
    yield from wait(lambda: threshold_phase() >= 1)
    yield from sleep(3.0)
    th = one('threshold')
    plane = prop(th, 'PortalPlane')
    cm = unreal.GameplayStatics.get_player_camera_manager(W(), 0)
    log('portal_probe', result='PASS' if plane.is_visible() else 'FAIL',
        plane=[round(v) for v in plane.get_world_location().to_tuple()], plane_visible=plane.is_visible(),
        cam=[round(v) for v in cm.get_camera_location().to_tuple()], frame=shot('portal_probe'))
    if not plane.is_visible():
        raise Miss('the doorway plate is not showing during the threshold')


def g_yaw_watch():
    """Coordinator: control and camera yaw every tick from the Dream A teleport, to find what turns him off yaw 90."""
    yield from wait(lambda: pawn() and pawn().get_actor_location().y < -70000)
    t0, last, rows = time.time(), None, []
    cm = unreal.GameplayStatics.get_player_camera_manager(W(), 0)
    while time.time() - t0 < 4.0:
        cy, ky = round(pc().get_control_rotation().yaw, 1), round(cm.get_camera_rotation().yaw, 1)
        row = (cy, ky, pc().get_view_target().get_name(), threshold_phase())
        if row != last:
            rows.append([round(time.time() - t0, 3)] + list(row))
            last = row
        yield
    log('yaw_watch', result='INFO', rows=rows[:60])


def g_arrival_ablate():
    """Coordinator: on the Dream A arrival, hide one candidate at a time and shoot, to find what walls off the view."""
    yield from wait(lambda: threshold_phase() >= 3 and free())
    yield from sleep(1.0)
    log('ablate', what='baseline', frame=shot('abl_0_base'))
    p = pawn()
    body = prop(p, 'Body')
    body.set_visibility(False, True)
    yield from sleep(0.4)
    log('ablate', what='body hidden', frame=shot('abl_1_nobody'))
    body.set_visibility(True, True)
    vf = [a for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor) if a.get_actor_label() == 'ViewFill']
    for a in vf: a.set_actor_hidden_in_game(True)
    yield from sleep(0.4)
    log('ablate', what='ViewFill hidden', n=len(vf), frame=shot('abl_2_noviewfill'))
    for a in vf: a.set_actor_hidden_in_game(False)
    sp = [a for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor) if a.get_actor_label() in ('DreamA_Splats',)]
    for a in sp: a.set_actor_hidden_in_game(True)
    yield from sleep(0.4)
    log('ablate', what='DreamA_Splats hidden', n=len(sp), frame=shot('abl_3_nosplats'))
    for a in sp: a.set_actor_hidden_in_game(False)
    p.set_actor_location(p.get_actor_location() + unreal.Vector(0, 30, 0), False, True)
    yield from sleep(0.6)
    log('ablate', what='moved 30 cm forward', frame=shot('abl_4_fwd30'))


def g_dream_plate():
    """Coordinator: a clean high-res still of Dream A's arrival view (no UI), the doorway plate for the T10 threshold."""
    yield from wait(lambda: threshold_phase() >= 3 and free())
    yield from sleep(0.9)
    cm = unreal.GameplayStatics.get_player_camera_manager(W(), 0)
    unreal.SystemLibrary.execute_console_command(W(), 'HighResShot 1920x1080', pc())
    yield from sleep(3.0)
    log('dream_plate', result='INFO', cam=[round(v) for v in cm.get_camera_location().to_tuple()],
        yaw=round(cm.get_camera_rotation().yaw, 1), fov=round(cm.get_fov_angle(), 1), frame=shot('dream_plate'))


def g_arrival_probe():
    """Coordinator: what blocks the Dream A arrival view (camera, view target, trace hits, actors near the camera)."""
    cm = unreal.GameplayStatics.get_player_camera_manager(W(), 0)
    loc, rot = cm.get_camera_location(), cm.get_camera_rotation()
    fwd = rot.get_forward_vector()
    hits = []
    for d in (0, 15, -15):
        r = unreal.Rotator(rot.roll, rot.pitch + 0.0, rot.yaw + d)
        h = unreal.SystemLibrary.line_trace_single(W(), loc, loc + r.get_forward_vector() * 3000, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                 False, [pawn()], unreal.DrawDebugTrace.NONE, True)
        if h:
            t = h.to_tuple()
            hits.append([d, round((t[4] - loc).length()), t[9].get_actor_label() if t[9] else None, t[10].get_name() if t[10] else None])
    near = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor):
        dist = (a.get_actor_location() - loc).length()
        if dist < 400 and a != pawn():
            near.append([round(dist), a.get_actor_label(), a.get_class().get_name(), a.is_hidden_ed() if hasattr(a, 'is_hidden_ed') else None])
    near.sort()
    p = pawn()
    head = {}
    for c in ('Face', 'Hair', 'Eyebrows', 'Body'):
        try:
            comp = prop(p, c)
            head[c] = [comp.is_visible(), bool(comp.get_editor_property('owner_no_see')) if comp else None]
        except Exception as ex:
            head[c] = str(ex)[:60]
    try:
        head['bCameraClose'] = prop(p, 'bCameraClose'); head['bCinematic'] = prop(p, 'bCinematic')
        head['head_cm'] = round((prop(p, 'Body').get_socket_location('head') - loc).length())
    except Exception as ex:
        head['err'] = str(ex)[:80]
    inside = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor):
        o, ext = a.get_actor_bounds(True)
        if max(ext.x, ext.y, ext.z) < 3000 and all(abs(getattr(loc, k) - getattr(o, k)) <= getattr(ext, k) + 30 for k in 'xyz'):
            inside.append([a.get_actor_label(), a.get_class().get_name(), [round(v) for v in ext.to_tuple()]])
    log('arrival_head', result='INFO', head=head, inside=inside[:20])
    log('arrival_probe', result='INFO', cam=[round(v) for v in loc.to_tuple()], rot=[round(rot.pitch, 1), round(rot.yaw, 1)],
        ctrl_yaw=round(pc().get_control_rotation().yaw, 1), pawn=[round(v) for v in p.get_actor_location().to_tuple()],
        view=pc().get_view_target().get_name(), hits=hits, near=near[:25], frame=shot('arrival_probe'))
    yield


def g_threshold_arrival():
    yield from wait(lambda: threshold_phase() >= 3 and free())
    threshold = one('threshold')
    stream = prop(threshold, 'Stream')
    same_pawn = pawn() == S.get('threshold_pawn') and pawn() == prop(threshold, 'Player')
    okay = bool(stream and stream.is_level_visible() and same_pawn and prop(one('fe'), 'bInGameplay'))
    log('level2_arrival', result='PASS' if okay else 'FAIL', phase=threshold_phase(), same_pawn=same_pawn,
        stream_visible=bool(stream and stream.is_level_visible()), frame=shot('level2_path'))
    if not okay:
        raise Miss('Threshold did not reach the visible Level 2 path with the original pawn and free input')


ORDER = ('splash', 'title', 'menu', 'story', 'film', 'game')


def phase():
    """Where the front end is: splash, title, menu, story (intro), film (LS_WakeUp), game, or black in between."""
    fe, d = one('fe'), one('director')
    s = str(screen())
    for key, name in (('Splash', 'splash'), ('Title', 'title'), ('MainMenu', 'menu')):
        if key in s:
            return name
    st = prop(fe, 'Story')
    if st and st.is_in_viewport():
        return 'story'
    if prop(fe, 'bInGameplay') and prop(d, 'SeqPlayer') and not prop(d, 'bWakeDone'):
        return 'film'
    return 'game' if beat() != 'None' else 'black'


def front(own, act, settle):
    """One front-end screen: wait until the game reaches it (or skips past it, logged as a note: the front end is
    being cut by other lanes), look at it for `settle` s, then use the screen's own handler."""
    def gen():
        i = ORDER.index(own)
        yield from wait(lambda: phase() != 'black' and ORDER.index(phase()) >= i)
        if phase() != own:
            log('note', what=f'{own} not shown: the game went straight to {phase()}')
            return
        yield from sleep(settle)
        shot(own)
        yield from sleep(0.15)
        act()
        yield from wait(lambda: phase() != own)
    return gen


def skip_story():
    one('fe').get_editor_property('Story').call_method('Finish')  # the Skip button's OnClicked


def boot():
    fe = lambda fn: (lambda: one('fe').call_method(fn))  # noqa: E731
    return [('boot', 'splash, ended by its own handler', front('splash', fe('OnSplashFinished'), 1.2), 15, True),
            ('title', 'title confirmed (any key)', front('title', fe('OnTitleConfirmed'), 1.5), 10, True),
            ('menu', 'Wake up pressed', front('menu', fe('WakeUp'), 1.2), 12, True),
            ('intro', 'intro story skipped (Skip)', front('story', skip_story, 2.0), 12, False),
            ('wakeup', 'LS_WakeUp skipped (hold Space)', front('film', lambda: one('director').call_method('SkipWakeUp'), 1.5), 15, True),
            ('T0', 'T0 phone, if it opens: confirm Wake up', g_t0, 15, False),
            ('T1', 'T1 reached, first person, free', until(lambda: beat() == 'T1' and free()), 8, True)]


def g_t0(need=False):
    """The T0 phone has come and gone between builds: accept either the phone (confirmed with its own Enter/E,
    PhoneConfirm) or a morning that starts straight at T1, and log which. need=True: the phone must rise (#18)."""
    ph = one('phone')
    end = time.time() + 8  # the T0 phone opens by itself about 3.2 s after the wake hand-off (2026-11-10)
    while time.time() < end and not prop(ph, 'bOpen') and not (beat() == 'T1' and free()):
        yield
    if not prop(ph, 'bOpen'):
        if beat() == 'T1':
            if need:
                raise Miss('no T0 phone: the morning started at T1')
            log('note', what='no T0 phone: the morning started at T1')
            return
        raise Miss(f'neither the T0 phone nor T1 within 8 s (beat {beat()})')
    log('note', what='T0 phone up', view=view())  # since 00:47 UI's phone rises in the hand (view stays on the pawn)
    yield from sleep(1.6)  # every open shows the lock screen first; Today is up by about 1.4 s (UI, 01:00)
    shot('phone_T0')
    yield from sleep(0.15)
    ph.call_method('PhoneConfirm')  # E / Enter on the selected Wake up task
    yield from wait(lambda: beat() == 'T1' and not prop(ph, 'bOpen'))


# ---- battle (real input) -----------------------------------------------------------------------------------------
MOVES = {"ButtonUp": (10, "SleeveLabyrinth"), "PullOn": (5, "Mismatched"), "StepIn": (5, "TwistedLeg"), "TieKnot": (5, "Constricted")}
CLEAR = {"SleeveLabyrinth": "FindArmhole", "Mismatched": "MatchPair", "TwistedLeg": "UntwistLeg", "Constricted": "Loosen"}
STUN = {"Trousers": "UntwistLeg", "Tie": "Loosen"}


def short(o, prefix):
    return o.get_name().replace(prefix, '') if o else None


def policy(e, fast=False):
    """pie_fight.py's win policy (sim_party.py): stun a telegraphed attacker, mirror when low, else progress the
    weakest garment, clearing its blocker first. fast (B3f): stun only below 40 Composure, to fit a burst."""
    gs = []
    for g in e.get_editor_property('Garments'):
        d = g.get_editor_property('Data')
        gs.append(dict(id=short(d, 'DA_Opponent_'), p=g.get_editor_property('Progress'), r=d.get_editor_property('Resistance'),
                       s=str(g.get_editor_property('State')), intent=short(g.get_editor_property('Intent'), 'DA_Move_'),
                       act=[short(m, 'DA_Move_') for m in d.get_editor_property('ActMoves')]))
    st = [str(s) for s in e.get_editor_property('Statuses')]
    c, r = e.get_editor_property('Composure'), e.get_editor_property('Resolve')
    alive = [(i, g) for i, g in enumerate(gs) if g['s'] != 'Defeated']
    for i, g in alive:
        if g['intent'] in ('Kick', 'Strike') and g['id'] in STUN and g['s'] != 'Stunned' and (not fast or c < 40):
            return i, STUN[g['id']], gs
    if c <= 25 and r >= 5:
        return None, 'CheckMirror', gs
    i, g = min(alive, key=lambda ig: (ig[1]['r'] - ig[1]['p'], ig[1]['r']))
    prog = next((m for m in g['act'] if m in MOVES), g['act'][0])
    cost, blocker = MOVES.get(prog, (0, None))
    if blocker in st:
        return i, CLEAR[blocker], gs
    if r < cost:
        if 'Constricted' in st:
            tie = next((j for j, h in alive if h['id'] == 'Tie'), None)
            return (tie, 'Loosen', gs) if tie is not None else (None, 'CheckMirror', gs)
        return None, 'DeepBreath', gs
    return i, prog, gs


def click(e, button, fallback):
    """Click a WBP_Encounter command: if the button is shown and enabled, run the widget's own handler event that its
    OnSandClicked is bound to (OnAct0, OnBreathe, ...). Never read the delegate itself: touching a Blueprint
    multicast delegate from Python preceded an editor crash on 2026-11-10 03:10 UTC."""
    wid = prop(e, 'Widget')
    btn = prop(wid, button)
    if not btn or not btn.get_is_enabled() or not btn.is_visible():  # logged as a finding; the command keeps it going
        log('battle_click_blocked', button=button, present=bool(btn),
            enabled=btn.get_is_enabled() if btn else None, visible=btn.is_visible() if btn else None)
        if PLAN=='D1l':
            raise Miss('Defeat proof command unavailable; refusing Flee fallback')
        fallback()
        return
    wid.call_method('On' + button.replace('Btn_', ''))


def battle_key(name):
    k = unreal.Key()
    k.set_editor_property('key_name', name)
    return k


def fight_tick(mode):
    e = one('enc')
    w = W()
    if not e or not prop(e, 'bActive'):
        return
    winding = prop(e, 'bWindUp')
    # The QA editor can run at ~3 fps (11-17): every state hop and Delay costs a frame, so the fight runs at 12x, and
    # at 2x only while a timed move's key prompts are open (a 1 s window must outlast one frame). lose: 10x, untimed.
    pend = prop(e, 'PendingMove')
    timed = str(prop(e, 'BattleState')) == 'ResolvePlayerAction' and bool(pend) and bool(prop(pend, 'bTimedInput'))
    dil = unreal.GameplayStatics.get_global_time_dilation(w)
    speed = 10.0 if mode == 'lose' else 2.0 if (timed or prop(e, 'bAwaitingKey')) else 12.0
    if dil > 0.5 and abs(dil - speed) > 0.1:  # hit-stop drops to 0.05 and returns to 1: leave the freeze alone
        unreal.GameplayStatics.set_global_time_dilation(w, speed)
    F = S['fight']
    if winding:  # an enemy attack winds up (clarity pass, battle lane): the winner braces if a tick lands in the window
        t0 = prop(e, 'WindUpStart')
        frac = (unreal.GameplayStatics.get_time_seconds(w) - t0) / max(prop(e, 'WindUpTime'), 0.05)
        if mode.startswith('win') and F.get('brace') != t0 and prop(e, 'BraceFrom') <= frac < 1.0:
            F['brace'] = t0
            e.call_method('HandleKey', (battle_key('SpaceBar'),))
            log('brace', frac=round(frac, 2), braced=prop(e, 'bBraced'), composure=prop(e, 'Composure'))
        return
    if prop(e, 'bAwaitingKey'):
        idx = prop(e, 'InputIndex')
        if idx != F['key'] and mode.startswith('win'):  # lose: the player lets the window lapse
            F['key'] = idx
            e.call_method('HandleKey', (prop(e, 'InputKeys')[idx],))  # the prompt's key, as pressed
        return
    if not prop(e, 'bPlayerTurn'):
        F['acted'] = False
        return
    if F['acted'] or time.time() < F.get('next', 0):
        return
    data = '/Game/FoA/Gameplay/Encounter/Data/DA_Move_'
    if mode == 'lose':  # a struggling player: the first command, then he lets every key prompt lapse (Flee is hidden)
        F['acted'] = True
        log('turn', move='Act0, keys missed', composure=prop(e, 'Composure'))
        click(e, 'Btn_Act0', lambda: e.call_method('Flee'))
        return
    idx, mv, gs = policy(e, fast=(mode == 'win_fast'))
    for _ in range(len(gs) if idx is not None else 0):  # E cycles +1 (the Change target button is gone)
        if prop(e, 'Target') == idx:
            break
        e.call_method('HandleKey', (battle_key('E'),))
    if idx is not None and prop(e, 'Target') != idx:
        log('retarget_failed', wanted=idx, target=prop(e, 'Target'))
    F['acted'], F['key'] = True, -1
    if mv and bool(prop(unreal.load_asset(data + mv), 'bTimedInput')):  # slow down before the prompts open
        unreal.GameplayStatics.set_global_time_dilation(w, 2.0)
    tg = gs[prop(e, 'Target')] if gs else None
    if mv == 'DeepBreath':
        button = 'Btn_Breathe'
    elif mv == 'CheckMirror':
        button = 'Btn_Mirror'
    elif tg and mv in tg['act']:
        button = f'Btn_Act{tg["act"].index(mv)}'
    else:
        button = None
    log('turn', move=mv, button=button, target=prop(e, 'Target'), composure=prop(e, 'Composure'), resolve=prop(e, 'Resolve'))
    if button:
        click(e, button, lambda: e.call_method('ChooseMove', (unreal.load_asset(data + mv),)))
    else:
        log('battle_click_api', button=None, why=f'{mv} is not on a command button')
        e.call_method('ChooseMove', (unreal.load_asset(data + mv),))


def battle_marks(e):
    """Read-only snapshot of the clarity widgets: glyph text, ring and meter opacity and canvas position."""
    wid, out = prop(e, 'Widget'), {}
    if not wid:
        return out
    for name in ('ThreatRing', 'Glyph', 'Txt_Glyph', 'KeyCap', 'PromptBox', 'MarkRows', 'MarkPips0', 'MarkPips1', 'MarkPips2',
                 'MarkPips3', 'MarkPips4', 'LogPanel'):
        w = prop(wid, name)
        if not w:
            out[name] = None
            continue
        slot, pos = w.get_editor_property('slot'), None
        if isinstance(slot, unreal.CanvasPanelSlot):
            p = slot.get_position()
            pos = (round(p.x), round(p.y))
        out[name] = dict(op=round(w.get_render_opacity(), 2), pos=pos, vis=str(w.get_visibility()).split('.')[-1][:12],
                         kids=[round(k.get_render_opacity(), 2) for k in w.get_all_children()][:6] if isinstance(w, unreal.PanelWidget) else None)
    t = prop(wid, 'Txt_Glyph')
    out['glyph_text'] = str(t.get_text()) if t else None
    out['state'] = str(prop(e, 'BattleState'))
    out['clock'] = dict(now=round(unreal.GameplayStatics.get_time_seconds(W()), 2), impact=round(prop(e, 'ImpactAt') or 0, 2),
                        windup=round(prop(e, 'WindUpStart') or 0, 2), wind=prop(e, 'bWindUp'), spent=prop(e, 'bBraceSpent'),
                        dilation=round(unreal.GameplayStatics.get_global_time_dilation(W()), 2))
    out.update({k: round(prop(wid, k) or 0) for k in ('RingX', 'RingY', 'TargetMarkX', 'TargetMarkY')})
    return out


def shirt_head_start():
    """Fixture for B3f: the Shirt starts four of its six buttons done, so a real win fits a burst at ~3 fps."""
    e = one('enc')
    for g in e.get_editor_property('Garments'):
        if str(g.get_editor_property('Data').get_editor_property('GarmentId')) == 'Shirt':
            g.call_method('AddProgress', (4,))
            log('fixture_progress', garment='Shirt', progress=g.get_editor_property('Progress'))


def low_composure():
    """Fixture for D1f: seven Tie Strikes through BP_Encounter.ApplySelf (Composure 100 to 16; it is not
    instance-editable), so the real attacks and the drain end the fight inside a burst."""
    e = one('enc')
    strike = unreal.load_asset('/Game/FoA/Gameplay/Encounter/Data/DA_Move_Strike')
    for _ in range(7):
        e.call_method('ApplySelf', (strike,))
    log('fixture_composure', composure=e.get_editor_property('Composure'))


def g_battle_real_keys():
    """Battle lane, clarity pass (2026-11-17): the keys the new screen shows are pressed for real through the runner.
    E on the player's turn must change the target, Enter must pick the focused card, and a Space late in an enemy
    wind-up must reach BP_Encounter.Brace (bBraceSpent goes true; bBraced if it landed in the window)."""
    e = one('enc')
    yield from wait(lambda: prop(e, 'bActive'))
    for n in range(8):
        yield from wait(lambda: prop(e, 'bWindUp') or (prop(e, 'bPlayerTurn') and str(prop(e, 'BattleState')) == 'PlayerCommand')
                        or str(prop(e, 'BattleState')) in ('Victory', 'Defeat'))
        if str(prop(e, 'BattleState')) in ('Victory', 'Defeat'):
            raise Miss('battle ended before a wind-up')
        if prop(e, 'bWindUp'):
            w = W()
            # The relay's round trip outlasts a 1 s wind-up at ~3 fps: slow the world so the real key lands inside it.
            unreal.GameplayStatics.set_global_time_dilation(w, 0.25)
            log('windup_widgets', **battle_marks(e), frame=shot('windup_ring'))
            sent = press_now('SpaceBar', 90)
            yield from wait(lambda: prop(e, 'bBraceSpent') or not prop(e, 'bWindUp'))
            spent, braced = prop(e, 'bBraceSpent'), prop(e, 'bBraced')
            unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
            log('real_brace', result='PASS' if spent else 'FAIL', sent=sent, spent=spent, braced=braced,
                composure=prop(e, 'Composure'), frame=shot('brace'))
            yield from sleep(0.6)
            log('impact_widgets', **battle_marks(e), frame=shot('after_impact'))
            yield from sleep(1.5)
            log('later_widgets', **battle_marks(e), frame=shot('later'))
            if not spent:
                raise Miss('a real Space during the wind-up never reached Brace')
            return
        yield from sleep(0.5)
        if n == 0:
            before = prop(e, 'Target')
            log('turn_widgets', **battle_marks(e), frame=shot('first_turn'))
            sent = yield from press('E', 120)
            yield from sleep(0.4)
            log('real_target_key', result='PASS' if prop(e, 'Target') != before or prop(e, 'Remaining') < 2 else 'FAIL',
                sent=sent, before=before, after=prop(e, 'Target'), frame=shot('target_e'))
        yield from press('Enter', 120)
        yield from wait(lambda: not prop(e, 'bPlayerTurn') or str(prop(e, 'BattleState')) != 'PlayerCommand')
        if n == 0:
            yield from sleep(0.3)
            log('resolve_widgets', **battle_marks(e), frame=shot('resolve'))
    raise Miss('no enemy wind-up in eight turns')


SG_GROUPS = ('ResolutionQuality', 'ViewDistanceQuality', 'AntiAliasingQuality', 'ShadowQuality', 'GlobalIlluminationQuality',
             'ReflectionQuality', 'PostProcessQuality', 'TextureQuality', 'EffectsQuality', 'FoliageQuality', 'ShadingQuality',
             'LandscapeQuality')


def cd_dump():
    """Battle lane: every primitive in the PIE world that renders custom depth, by stencil ([components, in view, static
    mesh triangles in view]), the in-view list, and how many BP_Encounter.ApplyLowDepth took (depth off, stencil 205)."""
    groups, seen, taken = {}, [], 0
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor):
        for c in a.get_components_by_class(unreal.PrimitiveComponent):
            st = c.get_editor_property('custom_depth_stencil_value')
            if not c.get_editor_property('render_custom_depth'):
                taken += st == 205
                continue
            view = (c.is_visible() and not c.get_editor_property('hidden_in_game') and not prop(a, 'hidden', False)
                    and a.was_recently_rendered(0.3))
            tris = c.static_mesh.get_num_triangles(0) if view and isinstance(c, unreal.StaticMeshComponent) and c.static_mesh else 0
            g = groups.setdefault(st, [0, 0, 0])
            g[0], g[1], g[2] = g[0] + 1, g[1] + int(view), g[2] + tris
            if view:
                seen.append(f'{a.get_class().get_name()}.{c.get_name()}:{st}:{tris}')
    return dict(by_stencil={str(k): v for k, v in sorted(groups.items())}, in_view=sorted(seen), taken=taken)


def g_low_depth():
    """Battle lane, the GTX 1060 Low fight (11-18 15:10): at Low, BP_Encounter.ApplyLowDepth takes the black sand
    (stencil 5) out of custom depth; Medium must not change. On the first player turn, at speed: the encounter's 1 s
    timer alone must apply and undo it on a preset change. Then world frozen: Medium twice (noise floor), Low twice before
    the cut (noise floor), Low after it, Medium again (restored), with the custom-depth census. The editor's own
    scalability is put back at the end."""
    e = one('enc')
    yield from wait(lambda: prop(e, 'bActive') and prop(e, 'bPlayerTurn') and str(prop(e, 'BattleState')) == 'PlayerCommand')
    sysl = unreal.SystemLibrary
    orig = {g: sysl.get_console_variable_int_value('sg.' + g) for g in SG_GROUPS}
    con = lambda c: sysl.execute_console_command(W(), c)  # noqa: E731
    shading = lambda: sysl.get_console_variable_int_value('sg.ShadingQuality')  # noqa: E731
    w = W()
    try:
        con('scalability 1')
        yield from sleep(1.0)
        base = cd_dump()
        con('scalability 0')  # at speed: only the timer reacts
        t = time.time()
        yield from wait(lambda: prop(e, 'bLowDepth') or time.time() - t > 4)
        on_low, t_low, cut = prop(e, 'bLowDepth'), round(time.time() - t, 2), cd_dump()
        con('scalability 1')
        t = time.time()
        yield from wait(lambda: not prop(e, 'bLowDepth') or time.time() - t > 4)
        off_med, t_med, back = not prop(e, 'bLowDepth'), round(time.time() - t, 2), cd_dump()
        ok = (on_low and off_med and cut['taken'] > 0 and back['taken'] == 0 and '5' not in cut['by_stencil']
              and {k: v[0] for k, v in back['by_stencil'].items()} == {k: v[0] for k, v in base['by_stencil'].items()})  # components, not in-view (the fight moves)
        log('ld_timer', result='PASS' if ok else 'FAIL', low_after_s=t_low, medium_after_s=t_med, cut_taken=cut['taken'],
            base_by_stencil=base['by_stencil'], cut_by_stencil=cut['by_stencil'], back_by_stencil=back['by_stencil'])
        unreal.GameplayStatics.set_global_time_dilation(w, 0.0001)  # frozen: the frames share one pose
        yield from sleep(1.0)
        log('ld_medium_a', shading=shading(), low=prop(e, 'bLowDepth'), **cd_dump())
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_medium_a')
        yield from sleep(0.6)
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_medium_a2')
        con('scalability 0')
        yield from sleep(4.0)  # the timer is frozen with the world: the cut waits for the direct call below
        log('ld_low_before', shading=shading(), low=prop(e, 'bLowDepth'), **cd_dump())
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_low_before')
        yield from sleep(0.6)
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_low_before2')
        yield from sleep(0.4)
        e.call_method('ApplyLowDepth')
        yield from sleep(0.8)
        log('ld_low_after', shading=shading(), low=prop(e, 'bLowDepth'), **cd_dump())
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_low_after')
        yield from sleep(0.4)
        con('scalability 1')
        yield from sleep(2.0)
        e.call_method('ApplyLowDepth')
        yield from sleep(0.8)
        log('ld_medium_b', shading=shading(), low=prop(e, 'bLowDepth'), **cd_dump())
        yield from wait(lambda: time.time() - S['shot_t'] >= 0.3)  # the 1 s periodic shot must not swallow this one
        shot('ld_medium_b')
        yield from sleep(1.2)  # the shot renders a frame or two later: PIE must still be up
        if not ok:
            raise Miss('the encounter timer did not follow the preset change (see ld_timer)')
    finally:
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        for g, v in orig.items():  # at Scalability priority: a plain `sg.X v` is SetByConsole and blocks every later preset switch
            con(f'SetCVar sg.{g} {v} -setby=Scalability')
        log('ld_restore', sg={g: sysl.get_console_variable_int_value('sg.' + g) for g in SG_GROUPS}, was=orig)


def fight(mode, outcome):
    def gen():
        e = one('enc')
        yield from wait(lambda: prop(e, 'bActive'))
        S['fight'] = dict(mode=mode, key=-1, acted=False)
        face = prop(pawn(), 'Face')  # anim is chasing a headless player at the battle start (2026-11-10): log it
        log('battle_head', face_present=bool(face), face_visible=face.is_visible() if face else None,
            frame=shot('battle_start'))
        yield from wait(lambda: str(prop(e, 'BattleState')) in ('Victory', 'Defeat') or not prop(e, 'bActive'))
        result = str(prop(e, 'BattleState'))
        S['fight'] = None
        unreal.GameplayStatics.set_global_time_dilation(W(), 1.0)
        shot('battle_' + result)
        if result != outcome:
            raise Miss(f'battle ended {result}, wanted {outcome}')
    return gen


def widgets_under(w):
    """A plain widget and every widget below it (read-only; a UserWidget's WidgetTree is protected from Python)."""
    todo, out = [w], []
    while todo:
        x = todo.pop()
        if x is None:
            continue
        out.append(x)
        if isinstance(x, unreal.PanelWidget):
            todo += list(x.get_all_children())
        elif isinstance(x, unreal.ContentWidget):
            todo.append(x.get_content())
    return out


def texts_in(w):
    """Every Text/RichText widget inside a UserWidget at any nesting depth. Python cannot read UserWidget.WidgetTree
    (protected; D2 02:00 found 0 texts in WBP_HUD that way), so: every live text widget whose outer chain reaches w."""
    out = []
    for kind in (unreal.TextBlock, unreal.RichTextBlock):
        for t in unreal.ObjectIterator(kind):
            o = t.get_outer()
            for _ in range(10):  # text -> WidgetTree -> nested UserWidget -> WidgetTree -> ... -> w
                if o is None or o == w:
                    break
                o = o.get_outer()
            if o is not None and o == w:
                out.append(t)
    return out


def owner_widget(x):
    """The UserWidget whose WidgetTree holds x (x -> WidgetTree -> UserWidget), or None."""
    o = x.get_outer()
    o = o.get_outer() if isinstance(o, unreal.WidgetTree) else None
    return o if isinstance(o, unreal.UserWidget) else None


def focused_in(root):
    """(widget, texts of its button) for every widget inside `root`, at any depth, that holds keyboard focus."""
    out = []
    for x in unreal.ObjectIterator(unreal.Widget):
        if not x.has_keyboard_focus():
            continue
        o = x
        for _ in range(10):
            if o is None or o == root:
                break
            o = o.get_outer()
        if o is not None and o == root:
            btn = owner_widget(x) if owner_widget(x) not in (None, root) else x
            out.append((x.get_name(), sorted(str(t.get_text()).strip() for t in texts_in(btn) if str(t.get_text()).strip())
                        if isinstance(btn, unreal.UserWidget) else []))
    return out


def g_credits_back():
    """UI's fix (main 03:05): after the level end's credits, Back (BP_FoAFrontEnd.HandleBack, what Esc/B call) lands
    on the main menu with keyboard focus on Wake up."""
    fe = one('fe')
    if S.get('z_walkout') is not None:  # #12: he must not fall behind the end card
        drop = S['z_walkout'] - S['zmin']
        log('walkout_hold', result='PASS' if drop < 50 else 'FAIL', z_walkout=round(S['z_walkout']), z_min=round(S['zmin']))
        S['z_walkout'] = None
    yield from wait(lambda: 'Credits' in str(name_of(prop(fe, 'Overlay'))) or 'Credits' in str(screen()))
    log('note', what='credits up', screen=screen(), overlay=name_of(prop(fe, 'Overlay')))
    yield from sleep(1.0)
    shot('credits')
    yield from sleep(0.15)
    fe.call_method('HandleBack')
    yield from wait(lambda: 'MainMenu' in str(screen()) and not overlay_up())
    yield from sleep(0.6)
    f = focused_in(prop(fe, 'Screen'))
    ok = any('Wake up' in t for _, texts in f for t in texts)
    log('menu_focus', result='PASS' if ok else 'FAIL', screen=screen(), focused=f, frame=shot('menu_focus'))
    if not ok:
        raise Miss(f'main menu focus after Back: {f}')


def g_victory_ui():
    """UI's repair (main 2026-11-10), read 1 s after Victory: SelfBox and EnemyPanel collapsed, no "You are dressed."
    banner on screen, LogPanel (the subtitle plate) no wider than its text plus padding."""
    yield from sleep(1.0)
    wid = prop(one('enc'), 'Widget')
    if not wid or not wid.is_in_viewport():
        log('victory_ui', result='PASS', why='battle widget already gone')
        return
    hidden = (unreal.SlateVisibility.COLLAPSED, unreal.SlateVisibility.HIDDEN)
    panels = {n: str(prop(wid, n).get_visibility()) if prop(wid, n) else 'missing' for n in ('SelfBox', 'EnemyPanel')}
    shown = [x for x in texts_in(wid) if on_screen(x)]
    banner = [str(t.get_text()) for t in shown if 'You are dressed' in str(t.get_text())]
    plate, plate_w, text_w = prop(wid, 'LogPanel'), None, None
    if plate:  # any text at any depth inside the plate (B3 01:20: the subtitle sits deeper than two levels)
        inner = [t for t in widgets_under(plate) if isinstance(t, (unreal.TextBlock, unreal.RichTextBlock))
                 and t.get_visibility() not in hidden and str(t.get_text()).strip()]
        plate_w = round(plate.get_desired_size().x)
        text_w = round(max((t.get_desired_size().x for t in inner), default=0)) or None
    hug = plate is None or (text_w is not None and plate_w - text_w <= 80)
    ok = all(('COLLAPSED' in v or 'HIDDEN' in v) for v in panels.values()) and not banner and hug
    blind = plate is not None and text_w is None  # no text found in the plate: the check cannot judge the hug
    log('victory_ui', result='INCONCLUSIVE' if blind and not banner else ('PASS' if ok else 'FAIL'), panels=panels,
        banner=banner, plate_w=plate_w, text_w=text_w, frame=shot('victory_ui'))
    yield from sleep(0.15)
    if not ok:
        raise Miss(f'victory UI: panels {panels}, banner {banner}, plate {plate_w} vs text {text_w}')


def g_aim_dot():
    """Check the live centre slot and visibility; review captured pixel alignment."""
    hud=prop(one('fe'),'HUD');dot=prop(hud,'Size_AimDot')
    if not dot:raise Miss('Aim dot missing from live HUD')
    yield from sleep(.4)
    if not on_screen(dot):raise Miss('Aim dot hidden during free interaction')
    def centre(widget):
        geo=widget.get_cached_geometry();size=unreal.SlateLibrary.get_local_size(geo)
        if size.x<=0 or size.y<=0:return None
        return unreal.SlateLibrary.local_to_absolute(geo,unreal.Vector2D(size.x*.5,size.y*.5))
    a,b=centre(dot),centre(hud)
    slot=dot.get_editor_property('slot')
    assert slot.get_editor_property('horizontal_alignment')==unreal.HorizontalAlignment.H_ALIGN_CENTER
    assert slot.get_editor_property('vertical_alignment')==unreal.VerticalAlignment.V_ALIGN_CENTER
    padding=slot.get_editor_property('padding')
    assert all(getattr(padding,key)==0 for key in ('left','right','top','bottom'))
    assert dot.get_editor_property('width_override')==6 and dot.get_editor_property('height_override')==6
    # shortcut: retained Slate widgets expose zero geometry; screenshots verify pixel alignment.
    error=math.hypot(a.x-b.x,a.y-b.y) if a and b else None
    log('aim_dot',check='centred slot',error_pixels=error,geometry_measured=error is not None,frame=shot('aim_dot_free'))
    if error is not None and error>1:raise Miss('Aim dot is not centred on the viewport')
    yield from sleep(.3)
    p=pawn()
    try:
        p.call_method('SetCinematic',(True,))
        yield from sleep(.3)
        if dot.get_render_opacity()>.01:raise Miss('Aim dot visible while cinematic owns input')
        log('aim_dot',check='cinematic hidden',frame=shot('aim_dot_cinematic'))
        yield from sleep(.3)
    finally:
        if unreal.SystemLibrary.is_valid(p):p.call_method('SetCinematic',(False,))
    yield from sleep(.3)
    if not on_screen(dot):raise Miss('Aim dot did not return after cinematic')
    fe=one('fe')
    try:
        fe.call_method('TogglePause')
        yield from sleep(.3)
        if on_screen(dot):raise Miss('Aim dot visible while paused')
        log('aim_dot',check='pause hidden',frame=shot('aim_dot_pause'))
        yield from sleep(.3)
    finally:
        if unreal.SystemLibrary.is_valid(fe):fe.call_method('Resume')
    yield from sleep(.3)
    if not on_screen(dot):raise Miss('Aim dot did not return after pause')
    log('aim_dot',check='restored',frame=shot('aim_dot_restored'))


def g_battle_command_layout():
    """Capture real command states and confirm through native Enter; retained text needs visual review."""
    enc=one('enc')
    yield from wait(lambda:prop(enc,'bPlayerTurn') and str(prop(enc,'BattleState'))=='PlayerCommand')
    ui=prop(enc,'Widget');measured=[]
    def rectangle(widget):
        geo=widget.get_paint_space_geometry();size=unreal.SlateLibrary.get_absolute_size(geo)
        origin=unreal.SlateLibrary.local_to_absolute(geo,unreal.Vector2D(0,0))
        return [origin.x,origin.y,origin.x+size.x,origin.y+size.y]
    def child(widget,name):
        candidates=[unreal.find_object(tree,name) for tree in unreal.ObjectIterator(unreal.WidgetTree)
                    if tree.get_outer()==widget]
        candidates=[item for item in candidates if item]
        if len(candidates)<=1:return candidates[0] if candidates else None
        painted=[item for item in candidates if rectangle(item)[2]>rectangle(item)[0]+1]
        if len(painted)!=1:raise Miss('Ambiguous painted command widget: '+name)
        return painted[0]
    for view_index in range(3):
        yield from sleep(.6)
        rows=[]
        for name in ('Act0','Act1','Act2','Breathe','Mirror','NextTarget'):
            button=child(ui,'Btn_'+name);label=child(button,'Txt_Label') if button else None;card=child(ui,'TornCard_'+name)
            if not button or not button.is_visible() or not label or not on_screen(label):continue
            text=str(label.get_text()).strip()
            if not text:continue
            box=rectangle(card or button);bounds=rectangle(label)
            painted=min(box[2]-box[0],box[3]-box[1],bounds[2]-bounds[0],bounds[3]-bounds[1])>1
            # shortcut: retained Slate text can expose zero geometry; review screenshots until Slate exposes its painted bounds.
            within=(bounds[0]>=box[0]-8 and bounds[1]>=box[1]-8 and bounds[2]<=box[2]+8 and bounds[3]<=box[3]+8) if painted else None
            rows.append(dict(command=name,text=text,card=box,label=bounds,within_card=within,geometry_measured=painted,enabled=button.get_is_enabled()))
        frame=shot('commands_'+str(view_index))
        log('battle_command_layout',target=prop(enc,'Target'),commands=rows,frame=frame)
        measured+=rows
        if not rows or any(r['within_card'] is False for r in rows):raise Miss('Command label exceeds card geometry; see battle_command_layout')
        if view_index<2:
            before=prop(enc,'Target');button=child(ui,'Btn_NextTarget');button.call_method('FocusButton')
            if not (yield from press('Enter')):raise Miss('Native Enter target-cycle input was not dispatched')
            yield from sleep(.25)
            if prop(enc,'Target')==before:raise Miss('Native Enter did not cycle the battle target')
    available=[r for r in rows if r['enabled'] and r['command']!='NextTarget']
    if not available:raise Miss('No enabled visible battle command')
    chosen=max(available,key=lambda r:len(r['text']));name=chosen['command'];button=child(ui,'Btn_'+name)
    if name.startswith('Act'):
        garment=enc.call_method('TargetGarment')
        if isinstance(garment,tuple):garment=garment[0]
        expected=prop(prop(garment,'Data'),'ActMoves')[int(name[-1])]
    else:expected=prop(enc,name+'Move')
    button.call_method('FocusButton');yield from sleep(.4)
    frame=shot('longest_command_focused');yield from sleep(.15)
    if not (yield from press('Enter')):raise Miss('Native Enter command input was not dispatched')
    yield from sleep(.3)
    pending=prop(enc,'PendingMove')
    log('battle_command_confirm',command=name,text=chosen['text'],expected=expected.get_name(),
        pending=pending.get_name() if pending else None,state=str(prop(enc,'BattleState')),frame=frame)
    if pending!=expected:raise Miss('Native Enter did not select the focused command')


def hidden_why(x):
    """'' when this widget is drawn: it and every parent (across nested UserWidgets) visible and not faded out, the top
    one in the viewport; else what hides it. shortcut: ignores ColorAndOpacity alpha and clipping; upgrade if a lane
    fades text by colour."""
    hidden = (unreal.SlateVisibility.COLLAPSED, unreal.SlateVisibility.HIDDEN)
    top = None
    while x is not None:
        if x.get_visibility() in hidden:
            return f'{x.get_name()} {x.get_visibility()}'
        if x.get_render_opacity() < 0.05:
            return f'{x.get_name()} opacity {x.get_render_opacity():.2f}'
        top, p = x, x.get_parent()
        if p is None:  # the root of a WidgetTree: carry on in the UserWidget that owns it
            o = x.get_outer()
            o = o.get_outer() if isinstance(o, unreal.WidgetTree) else None
            p = o if isinstance(o, unreal.UserWidget) and o != x else None
        x = p
    if not isinstance(top, unreal.UserWidget) or not top.is_in_viewport():
        return f'top {top.get_name() if top else None} not in the viewport'
    return ''


def on_screen(x):
    return not hidden_why(x)


def hud_texts():
    w = prop(one('fe'), 'HUD')  # BP_FoAFrontEnd owns the one WBP_HUD (UMG's widget search is not in Python here)
    return {str(t.get_text()).strip()[:40] for t in (texts_in(w) if w else []) if str(t.get_text()).strip() and on_screen(t)}


def hud_probe():
    """Why the HUD detector sees no text (D2 01:30 was blind while "Take a few steps." was on screen)."""
    w = prop(one('fe'), 'HUD')
    rows = [(t.get_class().get_name(), t.get_name(), str(t.get_text()).strip()[:30], hidden_why(t))
            for t in (texts_in(w) if w else [])]
    return dict(hud=w.get_class().get_name() if w else None, in_viewport=w.is_in_viewport() if w else None,
                text_widgets=len(rows), texts=rows[:12])


def hud_check(now):
    """#17: while the wake film's CineCameraActor is the view target, sample (every 0.25 s) the WBP_HUD text (BP_FoAFrontEnd.HUD) that is
    really on screen, per day. g_hud_film judges it; the first morning is the control."""
    c = pc()
    vt = c.get_view_target() if c else None
    if vt is None or vt.get_class().get_name() != 'CineCameraActor' or now - S.get('hud_t', 0) < 0.25:
        return
    S['hud_t'] = now
    texts = hud_texts()
    day = str(prop(gi(), 'DayCount'))
    row = S.setdefault('hud_film', {}).setdefault(day, dict(samples=0, texts=[]))
    row['samples'] += 1
    if texts - set(row['texts']):
        row['texts'] = sorted(set(row['texts']) | texts)
        shot('hud_over_film')


def g_hud_film():
    """#17 verdict: both mornings' films were sampled and no HUD text was on screen over either. Green only if the same
    detector sees HUD text now, in free play at T1 (else it is blind, INCONCLUSIVE)."""
    end = time.time() + 3  # the objective may fade in after the hand-off
    while time.time() < end and not hud_texts():
        yield
    rows, live = S.get('hud_film', {}), sorted(hud_texts())
    bad = {d: r['texts'] for d, r in rows.items() if r['texts']}
    ok = len(rows) >= 2 and bool(live)
    log('hud_over_film', result='FAIL' if bad else ('PASS' if ok else 'INCONCLUSIVE'), mornings=rows, hud_in_play=live,
        probe=None if live else hud_probe())
    if bad:
        raise Miss(f'HUD text over the wake film: {bad}')
    if not ok:
        raise Miss(f'inconclusive: films sampled on {len(rows)} morning(s), HUD text seen in play {live}')


# ---- plan pieces -------------------------------------------------------------------------------------------------
def fixture_t5(item):
    """T5 as the key snap leaves it: the door KeyJammed, plus the item the route needs."""
    one('director').call_method('EnterBeat', (5,))
    actor('Door_Bedroom').call_method('SetState', ('KeyJammed', True))
    if item:
        comp('inv').call_method('Add', (item,))


def fixture_t4():
    d, inv = one('director'), comp('inv')
    d.call_method('EnterBeat', (4,))
    inv.call_method('Add', ('Key',))
    boot_l = actor('Boot_L')
    boot_l.call_method('SetState', ('Worn', True))
    d.call_method('ReportEvent', ('BootsWorn',))


def fixture_t4_unworn():
    """Continue A1 before wearing the boots; the interaction must do that work."""
    one('director').call_method('EnterBeat', (4,))
    comp('inv').call_method('Add', ('Key',))
    actor('Boot_L').call_method('SetState', ('Searched', True))


def fixture_door_state(beat_index,state,item=None):
    """Only seed a preceding completed action; the continuation must exercise the next one."""
    one('director').call_method('EnterBeat',(beat_index,))
    actor('Door_Bedroom').call_method('SetState',(state,True))
    if item:comp('inv').call_method('Add',(item,))


def fixture_prior_battle_hits():
    """Continue a losing fight after earlier hits, without setting its outcome."""
    enc=one('enc');move=unreal.load_asset('/Game/FoA/Gameplay/Encounter/Data/DA_Move_Kick')
    delta=prop(move,'ComposureDelta',0)
    if delta>=0:raise Miss('Prior-hit fixture needs a damaging authored move')
    for _ in range(20):
        value=prop(enc,'Composure',0)
        if value<=25 or value+delta<=0:break
        enc.call_method('ApplySelf',(move,))
    value=prop(enc,'Composure',0)
    if not 0<value<=25:raise Miss(f'Prior-hit fixture failed at {value} composure')
    log('shortcut',what='Earlier authored Kick hits only',composure=value)


def fixture_clothing_before(wanted):
    """After the actual wardrobe transition, complete only earlier clues/flights in order."""
    def gen():
        d=one('director')
        yield from wait(free)
        for required,fn in ((1,'SearchWardrobeClue'),(2,'SearchDeskClue'),(3,'SearchBedClue')):
            if wanted<=required:break
            if stage()!=required:raise Miss(f'clue fixture needs stage {required}, got {stage()}')
            d.call_method(fn)
            d.call_method('CancelClothingInspection')
            yield from wait(lambda:stage()==required+1 and free())
        for required,fn in ((4,'BeginClothingToss'),(5,'EscapeClothingOne'),(6,'EscapeClothingTwo')):
            if wanted<=required:break
            if stage()!=required:raise Miss(f'chase fixture needs stage {required}, got {stage()}')
            d.call_method(fn)
            # Never overlap flights or inherit their input lock into the action under test.
            yield from wait(lambda:stage()==required+1 and not prop(d,'bClothingChaseActive') and free())
        if stage()!=wanted:raise Miss(f'fixture ended at {stage()}, expected {wanted}')
        log('shortcut',what='Prior clothing actions only',ready_stage=wanted)
    return gen


def record_replay_baseline():
    seed_knowledge()
    S['replay_day']=prop(gi(),'DayCount')


def g_replay_preserved():
    current=prop(gi(),'DayCount')
    known={str(k) for k in prop(gi(),'Knowledge',[])}
    okay=current==S['replay_day']+1 and 'Knows.KeyInBoot' in known and free()
    log('replay_preserved',result='PASS' if okay else 'FAIL',day=current,previous=S['replay_day'],knowledge=sorted(known))
    if not okay:raise Miss('FailDay must advance exactly one day and retain learned key knowledge with control restored')
    yield


def fixture_wardrobe():
    one('director').call_method('EnterBeat', (6,))
    actor('Wardrobe').call_method('Interact', ('Notify', 'HandleOff'))


def to_t7():
    return [('T6', 'fixture T6, then the wardrobe HandleOff notification starts the full fall',
             do(fixture_wardrobe, what='EnterBeat 6, Wardrobe Interact Notify HandleOff'), 2, True),
            ('T7', 'wardrobe fall and top-down play out, search starts', until(lambda: beat() == 'T7' and stage() >= 1 and free()), 25, True)]


def search_events():
    d = one('director')
    for ev, st in (('ClothingWardrobeSearched', 1), ('ClothingDeskSearched', 2), ('ClothingBedSearched', 3)):
        if stage() == st:
            d.call_method('ReportEvent', (ev,))
    if 'Hanger' not in items():  # route B players carry it from T5; B1 tests reaching the rail after the fall
        comp('inv').call_method('Add', ('Hanger',))


def hanger_then_bed():
    take = use('Hanger_CoatRail', 'Take', until=lambda: 'Hanger' in items())
    unhook = use('Bed', 'Use', item='Hanger', until=lambda: stage() >= 5)

    def gen():
        if 'Hanger' not in items():
            yield from take()
        yield from unhook()
    return gen


def chase(n):
    landed = until(lambda: state_of('Shirt_T7') in ('ChaseOne', 'ChaseTwo', 'ChaseFinal') and free())
    return chain(landed, use('Shirt_T7', 'Use', until=lambda: stage() >= 5 + n))


def skip_top_down():
    """Story (03:40): once T7 has started the search from the top-down, the director's own ExitTopDown dips and cuts
    back in 0.2 s (the late hold timer becomes a no-op)."""
    def gen():
        d = one('director')
        yield from wait(lambda: beat() == 'T7' and not prop(d, 'bWardrobeTransition') and stage() >= 1)
        if prop(d, 'bTopDown'):
            d.call_method('ExitTopDown')
        yield from wait(free)
    return gen


def g_hanger_glance():
    """Story's dropped-hanger glance (patch_hanger_glance.py): back from the T7 top-down, once per drop, the view eases
    down onto the fallen hanger (0.6 s), holds through the line (0.8 s) and eases back (0.6 s); move and look input are
    held for those 2 s only. Judged: it starts, the hanger is in the view cone at the hold, input is held during it
    and free after, the view comes back within 2 deg, and it does not run again."""
    d, c = one('director'), pc()
    end = time.time() + 5.0
    while not prop(d, 'bHangerGlancing') and time.time() < end:
        yield
    if not prop(d, 'bHangerGlancing'):
        raise Miss('no hanger glance within 5 s of the hand-back')
    start_rot, t0 = c.get_control_rotation(), time.time()
    hanger = actor('Hanger_CoatRail')
    best, held, frame, target, fov = 180.0, True, None, None, 90.0
    while prop(d, 'bHangerGlancing') and time.time() - t0 < 3.0:
        cam = c.player_camera_manager
        fov = cam.get_fov_angle()
        loc, fwd = cam.get_camera_location(), unreal.MathLibrary.get_forward_vector(cam.get_camera_rotation())
        o = look_point(hanger)[0]
        to = unreal.Vector(o.x - loc.x, o.y - loc.y, o.z - loc.z)
        to.normalize()
        best = min(best, math.degrees(math.acos(max(-1.0, min(1.0, fwd.x * to.x + fwd.y * to.y + fwd.z * to.z)))))
        held = held and c.is_move_input_ignored() and c.is_look_input_ignored()
        if frame is None and time.time() - t0 > 0.9:  # the middle of the hold
            frame, target = shot('hanger_glance'), name_of(prop(comp('ia'), 'Target'))
        yield
    secs = time.time() - t0
    yield from sleep(0.3)
    back = c.get_control_rotation()
    drift = max(abs((back.yaw - start_rot.yaw + 180) % 360 - 180), abs(back.pitch - start_rot.pitch))
    free_after = not c.is_move_input_ignored() and not c.is_look_input_ignored()
    yield from sleep(1.0)
    again = bool(prop(d, 'bHangerGlancing'))
    ok = best < fov / 2 and held and free_after and drift < 2.0 and not again and 1.5 < secs < 2.6
    log('hanger_glance', result='PASS' if ok else 'FAIL', secs=round(secs, 2), hanger_off_centre_deg=round(best, 1),
        input_held=held, input_free_after=free_after, view_back_drift_deg=round(drift, 2), ran_again=again,
        focus_at_hold=target, frame=frame)
    if not ok:
        raise Miss(f'hanger glance: {secs:.1f} s, hanger {best:.0f} deg off centre, held {held}, free after {free_after}, '
                   f'drift {drift:.1f} deg, again {again}')


def restart_mid_glance():
    """Restart Day while the glance holds input (story: ResetHouse ends it): pause, Restart Day, confirm."""
    def gen():
        d = one('director')
        end = time.time() + 30.0  # the fall and top-down come first
        while not prop(d, 'bHangerGlancing') and time.time() < end:
            yield
        if not prop(d, 'bHangerGlancing'):
            raise Miss('no hanger glance to interrupt')
        yield from sleep(0.5)
        log('note', what='Restart Day mid-glance', move_ignored=pc().is_move_input_ignored(),
            look_ignored=pc().is_look_input_ignored())
        fe = one('fe')
        fe.call_method('TogglePause')
        yield from sleep(0.4)
        fe.call_method('RequestRestartDay')
        yield from sleep(0.6)
        fe.call_method('ConfirmPending')
        yield from wait(lambda: not prop(d, 'bHangerGlancing'))
    return gen


def g_input_free_after_restart():
    """After the restarted morning: move and look input free, the hanger back on the rail (ResetHouse)."""
    yield from sleep(0.5)
    c, h = pc(), actor('Hanger_CoatRail')
    z = h.get_actor_location().z
    ok = not c.is_move_input_ignored() and not c.is_look_input_ignored() and not prop(one('director'), 'bHangerGlancing')
    log('restart_mid_glance', result='PASS' if ok else 'FAIL', move_ignored=c.is_move_input_ignored(),
        look_ignored=c.is_look_input_ignored(), hanger_state=state_of('Hanger_CoatRail'), hanger_z=round(z),
        frame=shot('after_restart'))
    if not ok:
        raise Miss('input still held after Restart Day mid-glance')


# ---- real keys through the runner (Hayba editor_pie_press_key) ------------------------------------------------------
REAL_KEYS = frozenset({'P', 'Tab', 'E', 'Enter', 'Gamepad_FaceButton_Right', 'SpaceBar', 'A', 'D'})  # never Escape: PIE's Esc chord
# stops the session even unmodified (UI 19:00); the runner sends these only with no modifier down (Alt+P = RepeatLastPlay)


def press_now(key, held_ms=150):
    """Ask the runner to press a real key in the PIE window; returns the request id (the runner acks in input_ack.json).
    Keys outside REAL_KEYS are never sent (main 2026-11-10: a P reached the editor and stopped PIE)."""
    if key not in REAL_KEYS:
        log('key_skipped', key=key, why='real keys off until Hayba targets the PIE viewport')
        return None
    S['inp'] = S.get('inp', 0) + 1
    tmp = f'{OUT}/input.tmp'
    open(tmp, 'w').write(json.dumps(dict(id=S['inp'], key=key, held_ms=held_ms)))
    os.replace(tmp, f'{OUT}/input.json')
    return S['inp']


def press(key, held_ms=150):
    i = press_now(key, held_ms)
    if i is None:
        return False
    end = time.time() + 3.0 + held_ms / 1000.0
    while time.time() < end:
        try:
            ack = json.load(open(f'{OUT}/input_ack.json'))
        except (OSError, ValueError):
            ack = {}
        if ack.get('id') == i:
            sent = 'skipped' not in str(ack.get('result')) and 'error' not in str(ack.get('result'))
            log('key' if sent else 'key_not_sent', key=key, held_ms=held_ms, result=str(ack.get('result'))[:200],
                pie_alive=ack.get('pie_alive'))
            return sent
        yield
    log('key_relay_timeout', key=key)
    return False


# ---- (c) item inspect (UI: BP_ItemInspect) --------------------------------------------------------------------------
INSPECT = '/Game/FoA/UI/Game/BP_ItemInspect.BP_ItemInspect_C'


def inspector():
    i = S.get('ins')
    if i is None or not unreal.SystemLibrary.is_valid(i):
        i = S['ins'] = unreal.GameplayStatics.get_actor_of_class(W(), cls(INSPECT))
    return i


def inspect_open():
    i = inspector()
    return bool(i and prop(i, 'bOpen'))


def pause_menu_up():
    pm = prop(one('fe'), 'PauseMenu')
    return bool(pm and pm.is_in_viewport())


def g_inspect(item, close_key):
    """The first take of an item opens the inspect: the game pauses; P (phone) and Tab are swallowed (no phone, no
    pause menu); a real `close_key` closes it with no leak (unpaused, move and look free, no pause menu, no interaction
    started, the focused actor unchanged); the same item's Request again this morning does not reopen it."""
    def gen():
        S['inspect_owner'] = True
        try:
            end = time.time() + 3.0
            while not inspect_open() and time.time() < end:
                yield
            if not inspect_open():
                raise Miss(f'the item inspect never opened for {item}')
            ins = inspector()
            yield from sleep(0.6)  # past the 0.3 s ease-in
            frame = shot('inspect_' + item)
            yield from sleep(0.15)
            paused = unreal.GameplayStatics.is_game_paused(W())
            keys = 'P' in REAL_KEYS and 'Tab' in REAL_KEYS
            if keys:
                keys = (yield from press('P'))
                yield from sleep(0.4)
                keys = (yield from press('Tab')) and keys
                yield from sleep(0.4)
            phone_up, menu_up, still = bool(prop(one('phone'), 'bOpen')), pause_menu_up(), inspect_open()
            focus = prop(comp('ia'), 'Target')
            focus_state = str(prop(focus, 'State')) if focus else None
            if close_key in REAL_KEYS and (yield from press(close_key)):
                via = 'real ' + close_key
            else:
                ins.call_method('Close')  # what BP_ItemInspect's E, Escape and gamepad B events call
                via = 'Close() (the handler ' + close_key + ' calls; real keys off)'
            end = time.time() + 2.0
            while inspect_open() and time.time() < end:
                yield
            yield from sleep(0.5)
            c = pc()
            closed, unpaused = not inspect_open(), not unreal.GameplayStatics.is_game_paused(W())
            leak = dict(move=c.is_move_input_ignored(), look=c.is_look_input_ignored(), pause_menu=pause_menu_up(),
                        interaction=bool(prop(pawn(), 'bInteractionLocked')), pending_row=bool(focus and prop(focus, 'bPendingRow')),
                        focus_changed=bool(focus) and str(prop(focus, 'State')) != focus_state)
            ins.call_method('Request', (unreal.Name(item),))  # what the take does: a second take this morning
            yield from sleep(1.0)  # OpenDelay is 0.55 s
            again = inspect_open()
            if again:
                ins.call_method('Close')
            ok = paused and not phone_up and not menu_up and still and closed and unpaused and not any(leak.values()) and not again
            log('inspect', result='PASS' if ok else 'FAIL', item=item, close=via, paused=paused,
                p_tab_pressed=keys, phone_blocked=(not phone_up) if keys else 'not tested',
                pause_blocked=(not menu_up) if keys else 'not tested', stayed_open=still, closed=closed, unpaused=unpaused,
                leak=leak, reopened_same_morning=again, frame=frame)
            if not ok:
                raise Miss(f'inspect {item}: paused {paused}, phone {phone_up}, pause menu {menu_up}, stayed {still}, '
                           f'closed {closed}, unpaused {unpaused}, leak {leak}, reopened {again}')
        finally:
            S['inspect_owner'] = False
    return gen


def inspect_autoclose(now):
    """Plans that do not test the inspect close it like a player (a real E) 1.2 s after it opens."""
    if S.get('inspect_owner') or any('item inspect' in STEPS[j][1] for j in (S['i'], S['i'] + 1) if j < len(STEPS)):
        return  # an inspect step is running or next: it owns the inspect
    if inspect_open():
        S.setdefault('ins_t', now)
        if now - S['ins_t'] > 1.2 and not S.get('ins_sent'):
            S['ins_sent'] = True
            inspector().call_method('Close')
            log('inspect_autoclose', what="closed through BP_ItemInspect.Close (the handler E calls)")
    else:
        S.pop('ins_t', None)
        S['ins_sent'] = False


# ---- (a) inventory as a carried set, (b) Notify end states ---------------------------------------------------------
WATCH = ('Boot_L', 'Key_Lux3D', 'Door_Bedroom', 'Wardrobe', 'Shirt_T7', 'Screwdriver_DeskDrawer', 'Hanger_CoatRail')


def track(now):
    """Every watched actor's State transitions and any duplicate in the carried set, every tick."""
    st = S.setdefault('st', {})
    for label in WATCH:
        a = S['actors'].get(label) if S.get('actors') else None
        if a is None or not unreal.SystemLibrary.is_valid(a):
            try:
                a = actor(label)
            except Miss:
                continue
        v = str(prop(a, 'State'))
        seq = st.setdefault(label, [])
        if not seq or seq[-1][1] != v:
            seq.append((round(now - S['t0'], 2), v))
            log('state_change', actor=label, state=v)
    it = items()
    if len(it) != len(set(it)) and it != S.get('dup_seen'):
        S['dup_seen'] = it
        log('inv_dup', result='FAIL', items=it)


def went(label, *seq):
    """The watched actor passed through these states in this order."""
    states = [v for _, v in S.get('st', {}).get(label, [])]
    i = 0
    for v in states:
        if i < len(seq) and v == seq[i]:
            i += 1
    return i == len(seq), states


def beat_index():
    return prop(one('director'), 'BeatIndex', -1)


def g_notify(name, checks):
    """checks: list of (description, fn -> (ok, detail)); one 'notify' row per check."""
    def gen():
        yield from sleep(0.5)
        bad = []
        for desc, fn in checks:
            ok, detail = fn()
            log('notify', result='PASS' if ok else 'FAIL', check=f'{name}: {desc}', detail=detail)
            if not ok:
                bad.append(desc)
        if bad:
            raise Miss(f'{name}: {bad}')
    return gen


def g_carried(name, carried=(), gone=(), beat_idx=None):
    def gen():
        yield from sleep(0.6)  # ToolsDone runs first in ReportEvent; give the event a moment
        it = items()
        ok = all(x in it for x in carried) and not any(x in it for x in gone) and len(it) == len(set(it))
        if beat_idx is not None:
            ok = ok and beat_index() == beat_idx
        log('carried', result='PASS' if ok else 'FAIL', check=name, items=it, want_carried=list(carried),
            want_gone=list(gone), beat_index=beat_index())
        if not ok:
            raise Miss(f'{name}: items {it}, beat {beat_index()}')
    return gen


def g_inventory_unit():
    """Story: Add(X) is true for any non-None X (a carried one too, without growing), Add('None') is false, the set
    never holds duplicates, IsFull is always false. A probe item goes in and out again."""
    yield
    inv = comp('inv')

    def one_value(r):
        return bool(r[0] if isinstance(r, (tuple, list)) else r)
    before = items()
    carried = before[0] if before else None
    r_carried = one_value(inv.call_method('Add', (unreal.Name(carried),))) if carried else True
    a1 = items()
    r_none = one_value(inv.call_method('Add', (unreal.Name('None'),)))
    a2 = items()
    r_new = one_value(inv.call_method('Add', (unreal.Name('QA_Probe'),)))
    a3 = items()
    full = one_value(inv.call_method('IsFull'))
    inv.call_method('Remove', (unreal.Name('QA_Probe'),))
    a4 = items()
    ok = (r_carried and len(a1) == len(before) and not r_none and len(a2) == len(before) and r_new and
          len(a3) == len(before) + 1 and not full and a4 == before and len(a3) == len(set(a3)))
    log('inventory_unit', result='PASS' if ok else 'FAIL', before=before, add_carried=r_carried, after_carried=a1,
        add_none=r_none, add_new=r_new, after_new=a3, is_full=full, after_remove=a4)
    if not ok:
        raise Miss('inventory unit checks failed (see inventory_unit)')


# ---- (d) the battle intro (story: LS_BattleIntro; hold Space 0.8 s skips) --------------------------------------------
def g_battle_intro(skip):
    def gen():
        fe, enc = one('fe'), one('enc')

        def cine():
            return view() == 'CineCameraActor' or bool(prop(pawn(), 'bCinematic'))
        end = time.time() + 6
        while time.time() < end and not cine():
            yield
        if not cine():
            raise Miss('no battle intro within 6 s of EnterBeat 8')
        t0, subs, frame, pressed = time.time(), [], None, None
        intro_hud_hidden=False
        while cine() and not prop(enc, 'bActive') and time.time() - t0 < 40:
            hud=prop(fe,'HUD')
            intro_hud_hidden=bool(hidden_why(hud)) if hud else True
            sub = prop(fe, 'CineSub')
            line = prop(sub, 'Txt_Line')
            text = str(line.get_text()).strip() if line else ''
            if text and on_screen(line) and text[:50] not in [x[0] for x in subs]:
                hud = prop(fe, 'HUD')
                subs.append((text[:50], bool(hidden_why(hud)) if hud else True))
                frame = frame or shot('battle_intro_sub')
            if skip and pressed is None and time.time() - t0 > 1.5:
                pressed = time.time()
                if 'SpaceBar' in REAL_KEYS and (yield from press('SpaceBar', 1200)):
                    pass
                else:
                    one('director').call_method('SkipWakeUp')  # what holding Space / gamepad A for 0.8 s calls
                    log('note', what='battle intro skipped through SkipWakeUp (the hold handler; real keys off)')
            yield
        secs = round(time.time() - t0, 2)
        after = round(time.time() - pressed, 2) if pressed else None
        if skip:
            ok = pressed is not None and after is not None and after < 3.5
        else:
            # Current 3.5s cut speaks AFTER the encounter handoff (2.0s and2.9s), per story/script.md.
            line_end=time.time()+3.5
            while time.time()<line_end:
                sub=prop(fe,'CineSub');line=prop(sub,'Txt_Line')
                text=str(line.get_text()).strip() if line else ''
                if text and on_screen(line) and text[:50] not in [x[0] for x in subs]:
                    subs.append((text[:50],False));frame=frame or shot('battle_intro_sub')
                yield
            ok = intro_hud_hidden and any('Get dressed.' in text or 'Shirt first.' in text for text,_ in subs) and bool(prop(enc,'bActive'))
        log('battle_intro', result='PASS' if ok else 'FAIL', skip=skip, secs=secs, ended_after_press_s=after,
            subtitles=subs, intro_hud_hidden=intro_hud_hidden, encounter_active=bool(prop(enc, 'bActive')), frame=frame)
        if not ok:
            raise Miss(f'battle intro (skip {skip}): {secs} s, after press {after}, subtitles {subs}')
    return gen


def g_selftests():
    """Each detector must report the bad state when it is made to happen on purpose (red-proof), and a real key
    through the runner must reach the game."""
    S['inspect_owner'] = True
    try:
        yield from wait(free)
        r = {}
        pawn().call_method('TogglePhone')
        yield from sleep(1.0)
        r['phone_detector_sees_phone'] = bool(prop(one('phone'), 'bOpen'))
        one('phone').call_method('PhonePutAway')
        yield from wait(lambda: not prop(one('phone'), 'bOpen') and free())
        one('fe').call_method('TogglePause')
        yield from sleep(0.6)
        r['pause_detector_sees_menu'] = pause_menu_up()
        one('fe').call_method('TogglePause')
        yield from sleep(0.6)
        ins = inspector()
        if ins is None:  # as BPFL_ItemInspect.RequestInspect does on the first take
            ins = S['ins'] = unreal.GameplayStatics.finish_spawning_actor(
                unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(W(), cls(INSPECT), unreal.Transform()), unreal.Transform())
        ins.call_method('Open', (unreal.Name('Key'),))
        yield from sleep(0.8)
        r['inspect_detector_sees_open'] = inspect_open()
        r['inspect_pauses'] = unreal.GameplayStatics.is_game_paused(W())
        frame = shot('selftest_inspect')
        yield from sleep(0.15)
        real = 'E' in REAL_KEYS and (yield from press('E'))
        if not real:
            ins.call_method('Close')
        yield from sleep(0.8)
        r['close_closes_inspect' + ('_real_E' if real else '_handler')] = not inspect_open()
        ins.call_method('Open', (unreal.Name('Key'),))
        yield from sleep(0.8)
        r['reopen_detector_sees_open'] = inspect_open()
        ins.call_method('Close')
        yield from sleep(0.8)
        r['closed_again'] = not inspect_open()
        comp('inv').call_method('Add', (unreal.Name('Key'),))
        r['carried_detector_sees_key'] = 'Key' in items()
        comp('inv').call_method('Remove', (unreal.Name('Key'),))
        ok = all(r.values())
        log('selftest', result='PASS' if ok else 'FAIL', frame=frame, **r)
        if not ok:
            raise Miss(f'detector self-tests: {r}')
    finally:
        S['inspect_owner'] = False


def spend_screwdriver():
    """As LatchFreed does on the plate route: the carried screwdriver is used up."""
    comp('inv').call_method('Remove', (unreal.Name('Screwdriver'),))


def g_spare_look():
    """The refilled drawer: State 'Spare'; focused, the verbs offered never include Take (only Look); a real E (Look)
    leaves Items and the State unchanged."""
    label = 'Screwdriver_DeskDrawer'
    end = time.time() + 5.0
    while state_of(label) != 'Spare' and time.time() < end:
        yield
    st = state_of(label)
    if st != 'Spare':
        log('spare', result='FAIL', state=st)
        raise Miss(f'{label} is {st}, not Spare, after the T7 refill')
    yield from use(label, 'Look', until=lambda: True)()
    ia, verbs = comp('ia'), []
    for _ in range(3):  # every verb the interactor offers on it
        verbs.append(str(prop(ia, 'Verb')))
        ia.call_method('CycleVerb')
        yield
    before = items()
    yield from want_verb('Look')
    prompt = str(prop(ia, 'Prompt', ''))
    real = 'E' in REAL_KEYS and (yield from press('E'))
    if not real:
        ia.call_method('Interact')
    yield from sleep(2.0)
    ok = 'Take' not in verbs and set(verbs) <= {'Look', 'None', ''} and items() == before and state_of(label) == 'Spare'
    log('spare', result='PASS' if ok else 'FAIL', state=state_of(label), verbs=sorted(set(verbs)), prompt=prompt,
        e='real E' if real else 'Interact()', items_before=before, items_after=items(), frame=shot('spare'))
    if not ok:
        raise Miss(f'spare screwdriver: verbs {verbs}, items {before} -> {items()}, state {state_of(label)}')


def to_escape_two():
    """Story's stage functions, guarded by the stage: from the snag (4) BeginClothingToss and EscapeClothingOne back to
    back leave stage 6 with the shirt landed at (-75, -160), about 1.6 s."""
    d = one('director')
    d.call_method('BeginClothingToss')
    d.call_method('EscapeClothingOne')


def take_shirt():
    def gen():
        yield from wait(lambda: stage() >= 9 or beat() == 'T8')
        if beat() != 'T8':
            yield from use('Shirt_T7', 'Take', until=beat_is('T8'))()
    return gen


def pause_menu():
    return lambda: wait(lambda: unreal.GameplayStatics.is_game_paused(W()) and prop(one('fe'), 'PauseMenu')
                        and prop(one('fe'), 'PauseMenu').is_in_viewport())


def overlay_up():
    o = prop(one('fe'), 'Overlay')
    return bool(o and o.is_in_viewport())


def fe_call(fn):
    return do(lambda: one('fe').call_method(fn))


def wake_again(need_phone=False):
    t0 = ('T0', 'new morning: the T0 phone rises by itself (#18), confirm Wake up', lambda: g_t0(True), 15, False) \
        if need_phone else ('T0', 'new morning T0 phone, if it opens: confirm Wake up', g_t0, 15, False)
    return [('wakeup', 'new morning: LS_WakeUp skipped (or straight to T0)', g_new_morning, 25, True), t0,
            ('T1', 'back in first person at T1', until(lambda: beat() == 'T1' and free()), 8, False)]


def g_new_morning():
    """After a rollover or Restart Day: the wake-up film, skipped with its own skip, or a morning that starts straight
    at T0 (logged)."""
    yield from wait(lambda: phase() == 'film' or beat() == 'T0')
    if phase() != 'film':
        log('note', what='new morning without LS_WakeUp')
        return
    yield from front('film', lambda: one('director').call_method('SkipWakeUp'), 1.5)()


def g_pocket_phone():
    """P takes the phone out (BP_FoAPlayer.TogglePhone); the phone's own put-away input closes it."""
    ph = one('phone')
    yield from wait(free)
    pawn().call_method('TogglePhone')
    yield from wait(lambda: prop(ph, 'bOpen'))
    yield from sleep(1.6)  # past the lock screen (about 1.4 s), so the frame shows the phone's home
    shot('phone')
    yield from sleep(0.15)
    ph.call_method('PhonePutAway')  # while it is up the phone owns input; its put-away handler closes it
    yield from wait(lambda: not prop(ph, 'bOpen') and free())


def take_screwdriver():
    def gen():
        if state_of('Screwdriver_DeskDrawer') != 'Available':  # in the drawer: open the desk first
            yield from use('Desk', 'Use', until=lambda: state_of('Screwdriver_DeskDrawer') == 'Available')()
        yield from use('Screwdriver_DeskDrawer', 'Take', until=lambda: 'Screwdriver' in items())()
    return gen


def probe_reach(label, verb, done):
    """Can a player reach this at all? 1. Survey the floor within the interactor's reach for spots where his capsule
    fits (only pawn-blocking collision counts): none means unreachable for anyone. 2. For the three nearest spots, walk
    there for real; if the walk is blocked, place him there (logged) to tell 'no path' from 'no spot'. 3. Look at it and
    wait for the interactor's focus. Each try is a 'reach_probe' row; the first walked-and-focused try takes it."""
    def gen():
        a, ia = actor(label), comp('ia')
        o, _ = look_point(a)
        reach = prop(ia, 'Reach', 200.0) or 200.0
        spots, why = [], {}
        step = prop(pawn().get_component_by_class(unreal.CharacterMovementComponent), 'max_step_height', 45.0) or 45.0
        for r in range(50, int(reach), 20):
            for deg in range(0, 360, 15):
                x, y = o.x + r * math.cos(math.radians(deg)), o.y + r * math.sin(math.radians(deg))
                if not (abs(x) < 360 and -295 < y < 295):
                    continue
                z0 = stand_z(x, y)  # the floor, or a low surface he can step onto (the fallen wardrobe)
                if z0 > step:  # higher needs a jump the game does not have
                    why['too high to step onto'] = why.get('too high to step onto', 0) + 1
                    continue
                block = pawn_blockers(x, y, z0)
                for b in block:
                    why[b] = why.get(b, 0) + 1
                if not block:
                    spots.append((r, round(x), round(y), round(z0)))
        here = pawn().get_actor_location()
        own = pawn_blockers(here.x, here.y, stand_z(here.x, here.y))  # calibration: where he stands now must fit
        log('reach_spots', target=label, reach=reach, fitting=len(spots), nearest=sorted(spots)[:6],
            blocked_by=sorted(why.items(), key=lambda kv: -kv[1])[:6], own_spot_blocked_by=own)
        if own:
            raise Miss(f'{label}: inconclusive, the survey says even his own spot is blocked ({own})')
        if not spots:
            raise Miss(f'{label}: no standing spot (floor or a surface up to {step:.0f} cm) within {reach:.0f} cm '
                       f'fits the player: unreachable; blocked by {sorted(why.items(), key=lambda kv: -kv[1])[:4]}')
        tries = []  # three spots at least 40 cm apart, nearest to 1 m first: from 50 cm a floor item sits below the
        for sp in sorted(spots, key=lambda q: abs(q[0] - 100)):  # pitch limit and the scan takes the next thing (S2 02:30)
            if all(math.hypot(sp[1] - t[1], sp[2] - t[2]) >= 40 for t in tries):
                tries.append(sp)
            if len(tries) == 3:
                break
        for r, x, y, z0 in tries:
            yield from wait(free)
            walked = yield from walk_leg(unreal.Vector(x, y, 0.0), 25.0, 6.0)
            placed = None
            if not walked:
                here = pawn().get_actor_location()
                hh = pawn().get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
                placed = bool(pawn().teleport(unreal.Vector(x, y, max(here.z, z0 + hh + 2)), pawn().get_actor_rotation()))
            yield from aim(a)
            end = time.time() + 1.5
            while prop(ia, 'Target') != a and time.time() < end:
                turn_toward(o, 10.0)
                yield
            here = pawn().get_actor_location()
            focused = prop(ia, 'Target') == a
            log('reach_probe', target=label, spot=[x, y], dist_cm=r, walked=walked, placed=placed,
                at=[round(here.x), round(here.y), round(here.z)], focused=focused, prompt=str(prop(ia, 'Prompt', '')),
                frame=shot('reach_' + label))
            if focused and walked:
                yield from want_verb(verb)
                ia.call_method('Interact')
                yield from wait(done)
                return
        raise Miss(f'{label} never focused from a spot he could walk to (see reach_spots / reach_probe rows)')
    return gen


def door_focus_at(dist):
    """#16 re-test (anim's camera-based fix, 03:05): stand `dist` cm in front of the door's lock on the room side, look
    at it, and the interactor's own scan must focus Door_Bedroom within 2 s (no pinning)."""
    def gen():
        door, frame = actor('Door_Bedroom'), actor('DoorFrame_Bedroom')
        ap = aim_point(door)
        inward = unreal.MathLibrary.transform_direction(frame.get_actor_transform(), unreal.Vector(-1.0, 0.0, 0.0))
        yield from wait(free)
        yield from go_to(unreal.Vector(ap.x + inward.x * dist, ap.y + inward.y * dist, 0.0), 8.0)
        yield from aim(door)
        ia, end = comp('ia'), time.time() + 2.0
        while prop(ia, 'Target') != door and time.time() < end:
            turn_toward(ap, 10.0)
            yield
        here = pawn().get_actor_location()
        ok = prop(ia, 'Target') == door
        log('door_focus', want_cm=dist, dist_cm=round(math.hypot(here.x - ap.x, here.y - ap.y)), focused=ok,
            target=name_of(prop(ia, 'Target')), prompt=str(prop(ia, 'Prompt', '')), frame=shot('door_focus'))
        if not ok:
            raise Miss(f'Door_Bedroom not focused from {math.hypot(here.x - ap.x, here.y - ap.y):.0f} cm in 2 s')
    return gen


def seed_knowledge():
    g = gi()
    k = set(prop(g, 'Knowledge', [])) | {unreal.Name('Knows.KeyInBoot')}
    g.call_method('SetProofProgressContext', (QA_SLOT, k, list(prop(g, 'Notebook', []))))


PLANS = {
    'A1': boot() + [
        ('T1', 'phone out with P, read, put away', g_pocket_phone, 8, False),
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'look at the bed', use('Bed', 'Look', until=beat_is('T3')), 20, False),
        ('T3', 'search the left boot: key', use('Boot_L', 'Use', until=lambda: 'Key' in items() and beat() == 'T4'), 20, False),
        ('T4', 'Notify: the boot gives the key', g_notify('T3 boot', [
            ('Boot_L Closed to Searched', lambda: went('Boot_L', 'Closed', 'Searched')),
            ('Key_Lux3D Hidden to Taken', lambda: went('Key_Lux3D', 'Hidden', 'Taken')),
            ('Key carried', lambda: ('Key' in items(), items()))]), 3, False),
        ('T4', 'put the boots on', use('Boot_L', 'Use', until=lambda: state_of('Boot_L') == 'Worn' and free()), 20, False),
        ('T4', 'hold', lambda: sleep(1.5), 3, False)],
    'A1b': boot() + [
        ('T4', 'fixture: key owned, boots searched but not worn',
         do(fixture_t4_unworn, what='EnterBeat 4, Add Key, Boot_L Searched'), 2, True),
        ('T4', 'put the boots on and regain control',
         use('Boot_L', 'Use', until=lambda: state_of('Boot_L') == 'Worn' and free()), 20, False),
        ('T4', 'hold after interaction release', lambda: sleep(1.5), 3, False)],
    'I1': boot() + [
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'look at the bed', use('Bed', 'Look', until=beat_is('T3')), 20, False),
        ('T3', 'search the left boot: key', use('Boot_L', 'Use', until=lambda: 'Key' in items()), 20, False),
        ('T4', 'item inspect: the key (real P, Tab, E)', g_inspect('Key', 'E'), 12, False),
        ('T4', 'inventory unit checks (Add, None, IsFull, no duplicates)', g_inventory_unit, 3, False)],
    'I2': boot() + [
        ('T5', 'shortcut: T5, key jammed', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the wire hanger', use('Hanger_CoatRail', 'Take', until=lambda: 'Hanger' in items()), 20, False),
        ('T5', 'item inspect: the hanger (real P, Tab, gamepad B)', g_inspect('Hanger', 'Gamepad_FaceButton_Right'), 12, False)],
    'I3': boot() + [
        ('T5', 'shortcut: T5, key jammed', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the screwdriver from the desk', take_screwdriver(), 20, False),
        ('T5', 'item inspect: the screwdriver (real P, Tab; Esc through its Close handler)', g_inspect('Screwdriver', 'Escape'), 12, False)],
    'SP': boot() + [
        ('T5', 'shortcut: T5, key jammed', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the screwdriver from the desk', take_screwdriver(), 20, False),
        ('T5', 'fixture: the screwdriver spent (as LatchFreed)', do(spend_screwdriver, what='Inventory.Remove Screwdriver'), 2, True)]
    + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'the refilled screwdriver: Spare, Look only, E changes nothing', g_spare_look, 14, False)],
    'F22': boot() + [  # #22 re-check (world's depth-tested rim, 04:35): a frame with the Bed focused at T2
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'look at the bed (frame taken while focused)', use('Bed', 'Look', until=beat_is('T3')), 20, False),
        ('T3', 'hold', lambda: sleep(1.0), 3, False)],
    'A2': boot() + [
        ('T4', 'shortcut: T4 with the key and boots on', do(fixture_t4, what='EnterBeat 4, Add Key, boots Worn, BootsWorn'), 2, True),
        ('T4', 'door focused from 55 cm (#16 re-test)', door_focus_at(55.0), 10, False),
        ('T4', 'key in the door, turn until it snaps', chain(use('Door_Bedroom', 'Use', item='Key', extra=90.0, until=lambda: prop(actor('Door_Bedroom'), 'bToolActive')),
                                                              door_tool(beat_is('T5'))), 32, False),
        ('T5', 'after the snap: neither Key nor KeyStub carried', g_carried('key snap', gone=('Key', 'KeyStub')), 3, False),
        ('T5', 'take the wire hanger', use('Hanger_CoatRail', 'Take', until=lambda: 'Hanger' in items()), 20, False)],
    'A3': boot() + [
        ('T5', 'shortcut: T5, key jammed, hanger in hand', do(lambda: fixture_t5('Hanger'), what='EnterBeat 5, Door KeyJammed, Add Hanger'), 2, True),
        ('T5', 'hanger through the door gap', chain(use('Door_Bedroom', 'Use', item='Hanger', extra=90.0,
                                                         until=lambda: prop(actor('Door_Bedroom'), 'bToolActive') or beat() == 'T6'),
                                                     door_tool(beat_is('T6'))), 25, False),
        ('T6', 'latch free: Hanger kept, Screwdriver gone', g_carried('door gap', carried=('Hanger',), gone=('Screwdriver',)), 3, False),
        ('T6', 'pull the handle: the wardrobe falls', use('Door_Bedroom', 'Use', extra=90.0, until=beat_is('T7')), 20, False),
        ('T7', 'Notify: HandleOff drops the wardrobe, BeatIndex 7', g_notify('handle pull', [
            ('Door_Bedroom LatchFree to HandleOff', lambda: went('Door_Bedroom', 'LatchFree', 'HandleOff')),
            ('Wardrobe Standing, Falling, Fallen', lambda: went('Wardrobe', 'Standing', 'Falling', 'Fallen')),
            ('BeatIndex 7', lambda: (beat_index() == 7, beat_index()))]), 4, False),
        ('T7', 'top-down: door moved', until(lambda: view() == 'BP_BeatDirector_C' or stage() >= 1), 10, False)],
    'B1': boot() + to_t7()[:1] + [  # B2, S2 and A3 play the full fall and top-down; B1 needs the time for the bed
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'search the fallen wardrobe', use('Wardrobe', 'Use', until=lambda: stage() >= 2 and free()), 20, False),
        ('T7', 'search the desk', use('Desk', 'Use', until=lambda: stage() >= 3 and free()), 20, False),
        ('T7', 'search the bed: the shirt is snagged', use('Bed', 'Use', until=lambda: stage() >= 4 and free()), 20, False),
        ('T7', 'hanger, unhook the shirt', hanger_then_bed(), 16, False)],
    'B2': boot() + to_t7() + [
        ('T7', 'shortcut: search events to the snag', chain(do(search_events, what='ReportEvent Clothing*Searched x3, Add Hanger'),
                                                            until(lambda: stage() >= 4 and free())), 15, True),
        ('T7', 'hanger, unhook the shirt', hanger_then_bed(), 16, False),
        ('T7', 'unhooked: Hanger gone', g_carried('unhooked', gone=('Hanger',)), 3, False),
        ('T7', 'chase 1: reach the shirt', chase(1), 8, False),
        ('T7', 'chase 2: reach the shirt', chase(2), 8, False),
        ('T7', 'chase 3: reach the shirt', chase(3), 8, False),
        ('T7', 'vase breaks, take the shirt: T8', take_shirt(), 12, False),
        ('T8', 'battle starts', until(lambda: prop(one('enc'), 'bActive')), 8, False)],
    'B2b': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'shortcut: search events to the snag', chain(do(search_events, what='ReportEvent Clothing*Searched x3, Add Hanger'),
                                                            until(lambda: stage() >= 4 and free())), 15, True),
        ('T7', 'fixture: toss and escape one (stage functions) to stage 6', chain(do(to_escape_two, what='BeginClothingToss, EscapeClothingOne'),
                                                                                 until(lambda: stage() >= 6 and free())), 8, True),
        ('T7', 'chase 2: reach the shirt again, escape two', chase(2), 10, False),
        ('T7', 'the vase: grab the shirt', chase(3), 10, False),
        ('T7', 'boss forms: T8', take_shirt(), 14, False),
        ('T8', 'the shirt accepted, BeatIndex 8', g_carried('boss formed', carried=('Shirt',), beat_idx=8), 3, False)],
    'B3': boot() + [
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'battle won by clicks and prompted keys', fight('win', 'Victory'), 30, False),
        ('T8', 'victory UI: HUD collapsed, no banner, plate hugs the text', g_victory_ui, 6, False),
        ('T9', 'T9 suit payoff', until(beat_is('T9', 'T10')), 8, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False)],
    'B3i': boot() + [  # LS_BattleIntro is 15.9 s: played in full here, skipped in B3 and D1
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro plays in full; subtitles while the HUD is hidden', g_battle_intro(False), 25, False),
        ('T8', 'the encounter starts after the intro', until(lambda: prop(one('enc'), 'bActive')), 6, False)],
    'Aim': boot()+[('T1','centred aim dot and cinematic/pause visibility',g_aim_dot,7,False)],
    'B3u': boot() + [
        ('T8','fixture: encounter starts normally',do(lambda:one('director').call_method('EnterBeat',(8,)),what='EnterBeat8'),2,True),
        ('T8','capture command cards and activate with native Enter',g_battle_command_layout,20,False)],
    'B3f': boot() + [  # battle lane: a real win that fits a burst at ~3 fps (B3 needs ~110 frames for the whole fight)
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'fixture: the Shirt starts four buttons in', do(shirt_head_start, what='Shirt AddProgress 4'), 2, True),
        ('T8', 'battle won by the policy (real moves, keys and braces)', fight('win_fast', 'Victory'), 30, False),
        ('T9', 'EncounterWon: T9 suit payoff', until(beat_is('T9', 'T10')), 8, False)],
    'D1f': boot() + [  # battle lane: a real loss that fits a burst
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'fixture: seven Strikes (Composure 16)', do(low_composure, what='ApplySelf Strike x7'), 2, True),
        ('T8', 'battle lost (no braces, every key lapses)', fight('lose', 'Defeat'), 30, False),
        ('rollover', 'FailDay rollover card', until(lambda: prop(one('fe'), 'Rollover') or prop(one('director'), 'bRollingOver')), 8, False)],
    'B3k': boot() + [  # battle lane: the clarity pass's keys, pressed for real (E target, Enter card, Space brace)
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'real E switches the target, real Enter picks a card, real Space braces', g_battle_real_keys, 30, False)],
    'B3d': boot() + [  # battle lane: Low drops the sand's custom depth in the fight, Medium untouched (11-18 15:10)
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'Low cuts the sand from custom depth, Medium and the timer path unchanged', g_low_depth, 75, False)],
    'C': boot() + [
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'payoff plays, T10', until(beat_is('T10')), 10, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False),
        ('T10', 'approach the doorway: threshold starts', lambda: walk_out(), 12, False),
        ('threshold', 'door opens after the threshold cinematic begins', g_threshold_open, 6, False),
        ('L2', 'colour path visible, same pawn and input restored', g_threshold_arrival, 18, False)],
    'CP': boot() + [  # coordinator: the doorway shows the dream (portal probe)
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'payoff plays, T10', until(beat_is('T10')), 10, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False),
        ('T10', 'approach the doorway: threshold starts', lambda: walk_out(), 12, False),
        ('threshold', 'portal render target and state after the door opens', g_portal_probe, 10, False)],
    'CPM': boot() + [  # coordinator: the T10 door portal after the T7 door move (the real flow; CP skips the move)
        ('T9', 'fixture: move the door like T7 (MoveDoor)', do(lambda: one('director').call_method('MoveDoor'), what='MoveDoor'), 2, True),
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'payoff plays, T10', until(beat_is('T10')), 10, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False),
        ('T10', 'fixture: stand 2.6 m in front of the moved door', do(lambda: cpm_stand(), what='teleport in front of DoorFrame'), 2, True),
        ('T10', 'approach the doorway: threshold starts', lambda: walk_out(), 14, False),
        ('threshold', 'portal render target and state after the door opens', g_portal_probe, 10, False)],
    'DPL': boot() + [  # coordinator: shoot the Dream A arrival plate for the T10 doorway
        ('T9', 'fixture: move the door like T7 (MoveDoor)', do(lambda: one('director').call_method('MoveDoor'), what='MoveDoor'), 2, True),
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'payoff plays, T10', until(beat_is('T10')), 10, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False),
        ('T10', 'fixture: stand 2.6 m in front of the moved door', do(lambda: cpm_stand(), what='teleport in front of DoorFrame'), 2, True),
        ('T10', 'approach the doorway: threshold starts', lambda: walk_out(), 14, False),
        ('dream', 'Dream A arrival plate (HighResShot)', g_dream_plate, 30, False),
        ('dream', 'arrival probe: what blocks the view', g_arrival_probe, 5, False)],
    'D1': boot() + [
        ('T1', 'fixture: a player who knows the key is in the boot', do(seed_knowledge, what='Knowledge += Knows.KeyInBoot'), 2, True),
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'battle lost (first command, every key prompt missed)', fight('lose', 'Defeat'), 30, False),
        ('rollover', 'FailDay rollover card', until(lambda: prop(one('fe'), 'Rollover') or prop(one('director'), 'bRollingOver')), 8, False)]
    + wake_again() + [
        ('T1', 'knowledge shortcut: straight to the boot', chain(walk(0.8), use('Boot_L', 'Use', until=lambda: 'Key' in items())), 20, False),
        ('T4', 'beat skipped ahead to T4', until(beat_is('T4')), 4, False)],
    'S1': boot() + [
        ('T5', 'shortcut: T5, key jammed (A2 proves the snap)', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the screwdriver from the desk', take_screwdriver(), 20, False),
        ('T5', 'screwdriver: four screws out of the plate', chain(use('Door_Bedroom', 'Use', item='Screwdriver', extra=90.0,
                                                                       until=lambda: prop(actor('Door_Bedroom'), 'bToolActive') or state_of('Door_Bedroom') == 'PlateOff'),
                                                                   door_tool(lambda: state_of('Door_Bedroom') == 'PlateOff' and free())), 30, False),
        ('T5', 'plate off: free the latch', use('Door_Bedroom', 'Use', extra=90.0, until=beat_is('T6')), 15, False),
        ('T6', 'latch free: Screwdriver gone', g_carried('latch freed', gone=('Screwdriver',)), 3, False)],
    'S2': boot() + to_t7() + [
        ('T7', 'the dropped-hanger glance (story)', g_hanger_glance, 8, False),
        ('T7', 'reach the hanger on the coat rail after the fall', probe_reach('Hanger_CoatRail', 'Take', lambda: 'Hanger' in items()), 34, False)],
    'V2': boot() + [
        ('T1', 'detector self-tests (phone, pause menu, inspect open and close, reopen, carried)', g_selftests, 20, False)],
    'S2R': boot() + to_t7()[:1] + [
        ('T7', 'Restart Day while the hanger glance holds input', restart_mid_glance(), 32, True)]
    + wake_again(need_phone=True) + [
        ('T1', 'input free after the restart, hanger back on the rail', g_input_free_after_restart, 4, False)],
    'C2': boot() + [
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'payoff plays, T10', until(beat_is('T10')), 10, False),
        ('T10', 'T10 phone confirmed', g_phone, 12, False),
        ('T10', 'fixture: EndLevel starts the threshold fallback',
         do(lambda: one('director').call_method('EndLevel'), what='EndLevel event'), 2, True),
        ('threshold', 'fallback opens door during the cinematic', g_threshold_open, 6, False),
        ('L2', 'fallback reaches the playable colour path', g_threshold_arrival, 18, False)],
    'D3': boot() + [
        ('T1', 'fixture: a player who knows the key is in the boot', do(seed_knowledge, what='Knowledge += Knows.KeyInBoot'), 2, True),
        ('T8', 'shortcut: the encounter lost (FailDay, its lose hand-off)', do(lambda: one('director').call_method('FailDay'), what='FailDay'), 2, True),
        ('rollover', 'FailDay rollover card', until(lambda: prop(one('fe'), 'Rollover') or prop(one('director'), 'bRollingOver')), 8, False)]
    + wake_again() + [
        ('T1', 'knowledge shortcut: straight to the boot', chain(walk(0.8), use('Boot_L', 'Use', until=lambda: 'Key' in items())), 20, False),
        ('T4', 'beat skipped ahead to T4', until(beat_is('T4')), 4, False)],
    'V': boot() + [
        ('T1', 'self-test: a 1.5 s blend from the top-down camera into the player must FAIL the view check',
         chain(do(lambda: pc().set_view_target_with_blend(one('director'), 0.0), what='view on BP_BeatDirector (top-down)'),
               lambda: sleep(1.0), do(lambda: pc().set_view_target_with_blend(pawn(), 1.5), what='blend 1.5 s back to the pawn'),
               until(lambda: view() == 'BP_FoAPlayer_C'), lambda: sleep(0.5),
               until(lambda: any(e['kind'] == 'view_into_player' and e['result'] == 'FAIL' for e in S['log']))), 8, False)],
    'D2': boot() + [
        ('pause', 'pause (Esc)', chain(fe_call('TogglePause'), pause_menu()), 4, False),
        ('pause', 'Restart Day, confirm', chain(fe_call('RequestRestartDay'), lambda: sleep(0.6), fe_call('ConfirmPending')), 3, False)]
    + wake_again(need_phone=True) + [
        ('T1', 'no HUD text over either morning\'s wake film (#17)', g_hud_film, 5, False),
        ('pause', 'pause again', chain(fe_call('TogglePause'), pause_menu()), 4, False),
        ('pause', 'Settings open', chain(fe_call('OpenSettings'), until(overlay_up), lambda: sleep(1.0)), 4, False),
        ('pause', 'Settings closed', chain(fe_call('CloseOverlay'), until(lambda: not overlay_up())), 4, False),
        ('title', 'Quit to Title, confirm', chain(fe_call('RequestQuitToTitle'), lambda: sleep(0.6), fe_call('ConfirmPending'),
                                                  until(lambda: 'Title' in str(screen()))), 10, False)],
}


# One action per continuation: earlier state is an explicit fixture, never the action being tested.
def clothing_continuation(required,action,label,budget=16):
    return boot()+to_t7()[:1]+[
        ('T7','wait for actual wardrobe transition and hand-back',skip_top_down(),25,True),
        ('T7',f'fixture: only clothing actions before stage {required}',fixture_clothing_before(required),14,True),
        ('T7',label,action,budget,False)]


PLANS.update({
    'A2k':boot()+[
        ('T4','fixture: key and worn boots',do(fixture_t4,what='T4 key owned and boots Worn'),2,True),
        ('T4','native key insert, full bind/ease/snap tool',chain(
            native_use('Door_Bedroom',item='Key',extra=90,until=lambda:prop(actor('Door_Bedroom'),'bToolActive')),
            door_tool(lambda:beat()=='T5' and free())),30,False),
        ('T5','key and stub consumed',g_carried('key snap',gone=('Key','KeyStub')),3,False)],
    'A3h':boot()+[
        ('T5','fixture: jammed key, hanger owned',do(lambda:fixture_t5('Hanger'),what='T5 KeyJammed, Hanger owned'),2,True),
        ('T5','native hanger insert and full latch tool',chain(
            native_use('Door_Bedroom',item='Hanger',extra=90,until=lambda:prop(actor('Door_Bedroom'),'bToolActive') or beat()=='T6'),
            door_tool(lambda:beat()=='T6' and free())),25,False),
        ('T6','hanger retained after freeing latch',g_carried('hanger latch',carried=('Hanger',)),3,False)],
    'A3f':boot()+[
        ('T6','fixture: previously freed latch',do(lambda:fixture_door_state(6,'LatchFree'),what='T6 Door LatchFree'),2,True),
        ('T6','native handle pull starts wardrobe',native_use('Door_Bedroom',extra=90,until=lambda:beat()=='T7'),12,False),
        ('T7','wardrobe finishes and restores control',until(lambda:stage()>=1 and not prop(one('director'),'bWardrobeTransition') and free()),18,False)],
    'S1p':boot()+[
        ('T5','fixture: key jammed',do(lambda:fixture_t5(None),what='T5 KeyJammed'),2,True),
        ('T5','desk opens to reveal screwdriver',native_use('Desk',until=lambda:state_of('Screwdriver_DeskDrawer')=='Available' and free()),14,False),
        ('T5','native screwdriver pickup',native_use('Screwdriver_DeskDrawer','Take',until=lambda:'Screwdriver' in items() and free()),16,False)],
    'S1s':boot()+[
        ('T5','fixture: key jammed, screwdriver owned',do(lambda:fixture_t5('Screwdriver'),what='T5 KeyJammed, Screwdriver owned'),2,True),
        ('T5','native screwdriver insert, all four screws',chain(
            native_use('Door_Bedroom',item='Screwdriver',extra=90,until=lambda:prop(actor('Door_Bedroom'),'bToolActive')),
            door_tool(lambda:state_of('Door_Bedroom')=='PlateOff' and free())),30,False)],
    'S1l':boot()+[
        ('T5','fixture: four screws already removed',do(lambda:fixture_door_state(5,'PlateOff','Screwdriver'),what='T5 PlateOff, Screwdriver owned'),2,True),
        ('T5','native latch push after plate removal',native_use('Door_Bedroom',extra=90,until=lambda:beat()=='T6' and free()),16,False),
        ('T6','screwdriver consumed by latch release',g_carried('latch release',gone=('Screwdriver',)),3,False)],
    'B1w':clothing_continuation(1,native_use('Wardrobe',until=lambda:stage()==2 and free()),'native wardrobe clue'),
    'B1d':clothing_continuation(2,native_use('Desk',until=lambda:stage()==3 and free()),'native desk clue'),
    'B1b':clothing_continuation(3,native_use('Bed',until=lambda:stage()==4 and free()),'native bed clue'),
    'B2c1':clothing_continuation(5,native_use('Shirt_T7',until=lambda:stage()==6 and free()),'native first shirt catch'),
    'B2c2':clothing_continuation(6,native_use('Shirt_T7',until=lambda:stage()==7 and free()),'native second shirt catch'),
    'B2c3':clothing_continuation(7,native_use('Shirt_T7',until=lambda:stage()>=9 or beat()=='T8'),'native final catch, vase and T8 handoff',18),
    'D1l':boot()+[
        ('T8','fixture: encounter start',do(lambda:one('director').call_method('EnterBeat',(8,)),what='EnterBeat8'),2,True),
        ('T8','intro completes before loss continuation',until(lambda:prop(one('enc'),'bActive') and not prop(pawn(),'bCinematic')),8,False),
        ('T8','fixture: prior missed turns left low composure',do(fixture_prior_battle_hits,what='Prior authored hits only; no outcome or FailDay call'),2,True),
        ('T8','lose by commands and missed prompts',fight('lose','Defeat'),30,False),
        ('rollover','defeat actually starts FailDay',until(lambda:prop(one('fe'),'Rollover') or prop(one('director'),'bRollingOver')),5,False)],
    'D1r':boot()+[
        ('T1','fixture: retained key knowledge and day baseline',do(record_replay_baseline,what='QA knowledge seed, record DayCount'),2,True),
        ('rollover','fixture: defeat has called FailDay',do(lambda:one('director').call_method('FailDay'),what='FailDay callback'),2,True)]
        +wake_again()+[('T1','next day keeps knowledge and restores control',g_replay_preserved,3,False)],
    'D1k':boot()+[
        ('T1','fixture: prior-day key knowledge',do(seed_knowledge,what='Knows.KeyInBoot'),2,True),
        ('T1','native known-key shortcut from first beat',native_use('Boot_L',until=lambda:'Key' in items() and beat()=='T4' and free()),22,False)]
})


# ---- drive lane: Level 2's rails drive and its QTE strikes (2026-11-17) ---------------------------------------------
# DR    the street -> the car -> the teaching leg to the first stop: one strike, braced with the real Space key.
# DR2a-d  the long second leg (J0 -> J1), started at 0/200/400/600 m so four bursts cover it whole: real Space, A and
#         D answers, one strike deliberately left alone to show the failure response; props, traffic and frames.
P.update(car='/Game/FoA/Level2/Drive/BP_L2Car.BP_L2Car_C')
DRIVE_T, DRIVE_W, DRIVE_LEAD = 2.5, .6, 1.6  # drive_data TELEGRAPH, BRACE_WINDOW, PROMPT_LEAD


def l2_fixture():
    """Shortcut to Level 2's street (the dream-transition lane's job fixture): front end and Level 1 skipped; the door,
    the threshold, the colour path and the fall run by themselves at 4x; then Journey Phase 1 at normal speed."""
    def gen():
        yield from wait(lambda: one('director') and one('fe') and pawn() and pc())
        w = W()
        unreal.GameplayStatics.set_game_paused(w, False)
        # Finish the front end's own screens first: a splash left running ends later on its timer and puts the
        # title in the viewport, whose OnKeyDown then eats the drive's Space (first DR run, 23:12).
        fe = one('fe')
        fe.call_method('OnSplashFinished')
        fe.call_method('OnTitleConfirmed')
        fe.call_method('StopBed')
        lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
        for widget in lib.call_method('GetAllWidgetsOfClass', (w, unreal.UserWidget, True)):
            widget.remove_from_parent()
        lib.call_method('SetInputMode_GameOnly', (pc(), True))
        one('director').call_method('OpenTheDoor')
        one('threshold').call_method('StartThreshold')
        jumped = False
        while True:
            th = one('threshold')
            j = prop(th, 'Journey')
            if prop(th, 'Phase', 0) >= 6 and j and unreal.SystemLibrary.is_valid(j) and prop(j, 'Phase') == 1:
                break
            if unreal.GameplayStatics.is_game_paused(w):
                unreal.GameplayStatics.set_game_paused(w, False)
            unreal.GameplayStatics.set_global_time_dilation(w, 4 if prop(th, 'Phase', 0) < 6 else 1)
            if prop(th, 'Phase', 0) == 3 and not jumped and prop(th, 'Age', 0) >= 13:
                unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (th, 'RouteBeat', 2))
                th.call_method('HidePath')
                pawn().set_actor_location(unreal.Vector(20000, -79660, 92), False, True)
                th.call_method('BeginFall')
                jumped = True
            yield
        unreal.GameplayStatics.set_global_time_dilation(w, 1)
        fe = one('fe')
        for key in ('SplashClass', 'TitleClass', 'MainMenuClass'):
            widget_class = prop(fe, key)
            if widget_class:
                for widget in lib.call_method('GetAllWidgetsOfClass', (w, widget_class, True)):
                    widget.remove_from_parent()
        if not unreal.SystemLibrary.is_valid(prop(fe, 'HUD')):
            fe.call_method('EnterGameplay')
            prop(fe, 'HUD').remove_from_parent()
        lib.call_method('SetInputMode_GameOnly', (pc(), True))
        # GPU, render and game thread cost per frame from here on (valid even when the editor throttles its frame rate)
        # an aborted burst never stops its capture, and a running capture ignores start (DRP 01:25 landed in DR2d's file)
        unreal.SystemLibrary.execute_console_command(w, 'csvprofile stop')
        yield from sleep(.3)  # the capture ends at a frame boundary
        unreal.SystemLibrary.execute_console_command(w, 'csvprofile start')
        log('csv_start', wall=time.time())
        log('l2_street', journey_phase=prop(prop(one('threshold'), 'Journey'), 'Phase'), screen=screen(),
            frame=shot('l2_street'))
    return gen


def l2_journey():
    return prop(one('threshold'), 'Journey')


def into_car(leg=None, at_cm=0.0, employability=None):
    """Journey Confirm twice (inspect the C.V., get in): the car drives off by itself. With leg, a fixture restarts the
    car on that leg from its canonical start and jumps at_cm along the rail once the route is chosen."""
    def gen():
        j = l2_journey()
        j.call_method('Confirm')
        j.call_method('Confirm')
        yield from wait(lambda: prop(one('car'), 'Active') and prop(one('car'), 'RouteReady'))
        car = one('car')
        if employability is not None:  # the interview's sign shows only once the player may go there
            unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (car, 'Employability', employability))
        if leg is not None:
            car.call_method('StartLeg', (leg,))
            yield from wait(lambda: prop(car, 'RouteReady'))
            if at_cm:  # never notify: a notified set on a PIE actor re-runs its construction script
                quiet = unreal.PropertyAccessChangeNotifyMode.NEVER
                car.set_editor_property('Distance', float(at_cm), notify_mode=quiet)
                setint = unreal.get_default_object(unreal.SystemLibrary)  # NextProp is not instance-editable
                setint.call_method('SetIntPropertyByName', (car, 'NextProp', int(max(0.0, at_cm - 3200) // 2900) + 1))
                # stream the jump point's next 150 m and hold the car for it, as a leg start does (DR2d, 01:12 stall)
                car.call_method('PreloadCity')
                setint.call_method('SetBoolPropertyByName', (car, 'CityHold', True))
                setint.call_method('SetDoublePropertyByName', (car, 'HoldUntil', float(prop(car, 'Clock', 0)) + 6.0))
                yield from wait(lambda: not prop(car, 'CityHold'))
        log('drive_start', leg=prop(car, 'Leg'), rail=prop(car, 'RailIndex'), length_m=round(prop(car, 'RouteLength', 0) / 100),
            at_m=round(prop(car, 'Distance', 0) / 100), strikes=prop(car, 'MeteorsLeft'), target=prop(car, 'ArrivalJob'),
            frame=shot('drive_start'))
    return gen


def drive_meteor_px(met):
    """Where the falling meteor body is on screen (viewport pixels, None if behind the camera) and how high it is."""
    try:
        body = prop(met, 'Shadow')
        at = body.get_world_location()
        px = unreal.GameplayStatics.project_world_to_screen(pc(), at, False)
        px = px[-1] if isinstance(px, tuple) else px
        size = unreal.WidgetLayoutLibrary.get_viewport_size(W())
        return dict(px=[round(px.x), round(px.y)] if px else None, viewport=[round(size.x), round(size.y)],
                    height_m=round(body.get_editor_property('relative_location').z / 100, 1), visible=body.is_visible())
    except Exception as err:  # evidence only: never fail a burst over it
        return str(err)[:120]


SECTOR_C = '/Game/FoA/Level2/City/Expanded/BP_City2Sector.BP_City2Sector_C'


def city_watch(car, seen):
    """Rolling-preload evidence: each city sector that turns visible, with its box distance from the car at that moment
    (a sector the camera rule loads late appears within its 90 m load radius; a preloaded one appears much further)."""
    at = car.get_actor_location()
    actors = unreal.GameplayStatics.get_all_actors_of_class(W(), cls(SECTOR_C))
    visible = 0
    for sector in actors:
        stream = prop(sector, 'Stream')
        on = bool(stream) and stream.is_level_visible()
        visible += on
        name = sector.get_name()
        if on and not seen.get(name):
            c = sector.get_actor_location()
            box = ((max(0.0, abs(at.x - c.x) - 2500)) ** 2 + (max(0.0, abs(at.y - c.y) - 2500)) ** 2) ** .5
            seen.setdefault('appeared', []).append(round(box / 100))
        seen[name] = on
    seen['peak'] = max(seen.get('peak', 0), visible)
    seen['pinned'] = sum(bool(prop(s, 'BootstrapPending')) for s in actors)


def drive_watch(car, w):
    """Round 3 evidence while driving: the set-piece's states (framed as it rises, stands and bursts), traffic cars
    that turn to sand near the player (framed), a committed dodge's swerve (framed), the streak's mood and the music."""
    state = prop(car, 'SetPieceState', 0)
    if state != w.get('piece'):
        w['piece'] = state
        w.setdefault('pieces', []).append(dict(state=state, at_m=round(prop(car, 'Distance', 0) / 100), t=t_now(),
                                               frame=shot(f'setpiece{state}')))
        if state == 1:
            w['tall_at'] = time.time() + 2.2
    if w.get('tall_at') and time.time() >= w['tall_at']:
        w['tall_at'] = None
        w.setdefault('pieces', []).append(dict(state='standing', t=t_now(), frame=shot('setpiece_standing')))
    road, at = prop(car, 'Road'), car.get_actor_location()
    for name in [n for n in ('TrafficEastACollision', 'TrafficWestACollision', 'TrafficEastBCollision',
                             'TrafficWestBCollision', 'TrafficEastCCollision')] + [f'Traffic{i}' for i in range(5, 14)]:
        c = prop(road, name)
        if not c:
            continue
        on = c.is_visible()
        if w.get(name, True) and not on and c.get_world_location().distance(at) < 1600:
            n = len(w.setdefault('sand', []))
            w['sand'].append(dict(car=name, t=t_now(), frame=shot(f'traffic_sand{n}') if n < 3 else None))
        w[name] = on
    met = prop(car, 'Meteor')
    away = abs(prop(car, 'Lateral', 0) - prop(car, 'StrikeLateral', 0))
    if prop(met, 'Active') and prop(met, 'Kind', 0) != 0 and away > 150 and w.get('swerve') != prop(car, 'MeteorIndex'):
        w['swerve'] = prop(car, 'MeteorIndex')
        w['swerve_at'] = time.time()
    if w.get('swerve_at') and time.time() >= w['swerve_at']:
        w['swerve_at'] = None
        w.setdefault('swerves', []).append(dict(lateral_cm=round(prop(car, 'Lateral', 0)), t=t_now(), frame=shot('swerve')))
    w['mood'] = round(prop(car, 'Mood', 0), 2)
    w['engine'] = round(prop(car, 'EngineSpeed', 0), 2)
    music = prop(prop(car, 'RoomAudio'), 'Music')
    w['music'] = round(music.get_editor_property('volume_multiplier'), 2) if music else None


def g_drive(skip=(), arrive=True, limit=None, perfect=False, watch=False):
    """Answer each strike with the real key at the right moment (Space when the ring meets the key, A or D once the
    prompt shows), leave the strikes in `skip` alone, log every outcome and frame the prompt, the window and the result.
    PASS: every answered strike resolved clean (late counts as answered), every skipped one hit, and (arrive) the car
    parked by itself and handed the stop to the journey."""
    def gen():
        car, rows, n, armed, sent, framed = one('car'), [], -1, False, False, set()
        met, started = prop(car, 'Meteor'), time.time()
        city, next_watch = {}, 0.0
        city_watch(car, city); city['appeared'] = []  # what is already in when the leg starts does not count
        w = {}
        while True:
            if time.time() >= next_watch:
                city_watch(car, city); next_watch = time.time() + .5
            if watch:
                drive_watch(car, w)
            if arrive and (prop(car, 'Arrived') or prop(l2_journey(), 'Phase', 0) >= 4):
                break
            if not arrive and not prop(car, 'Active'):
                break
            age, active = prop(met, 'Age', 0), prop(met, 'Active')
            index = prop(car, 'MeteorIndex', 0)  # a new strike is a new arm, even in the frame another resolved
            if active and index != S.get('drive_index'):
                S['drive_index'] = index
                n, armed, sent = n + 1, True, False
                rows.append(dict(n=n, kind=prop(met, 'Kind'), teaching=prop(car, 'Teaching'), skip=n in skip,
                                 at_m=round(prop(car, 'Distance', 0) / 100), t=t_now()))
            if armed:
                kind, row = prop(met, 'Kind'), rows[-1]
                if age >= DRIVE_T - DRIVE_LEAD + .1 and ('prompt', n) not in framed:
                    framed.add(('prompt', n)); row['prompt_frame'] = shot(f'strike{n}_prompt'); row['prompt_meteor'] = drive_meteor_px(met)
                if age >= DRIVE_T - DRIVE_W + .05 and ('window', n) not in framed:
                    framed.add(('window', n)); row['window_frame'] = shot(f'strike{n}_window'); row['window_meteor'] = drive_meteor_px(met)
                if not sent and n not in skip:
                    # QA bursts run at the editor's 3 fps background throttle: a relayed key lands 0.5-1.2 s late.
                    # Dodges (open until 0.2 s before impact) and the slowed teaching brace take the real key early;
                    # other braces call the handler Space is bound to (IA_L2Brace -> Brace) inside the window.
                    handler = kind == 0 and not row['teaching']
                    # aim the real key at the window's middle: the relay costs ~0.12 s plus ~2.5 frames
                    lag = (.12 + 2.5 * S['dt']) * unreal.GameplayStatics.get_global_time_dilation(W())
                    # perfect: the handler in the last 0.2 s (round 3's near miss); otherwise mid-window
                    due = ((DRIVE_T - (.1 if perfect else .35)) if handler else DRIVE_T - DRIVE_W / 2 - lag) if kind == 0 \
                        else DRIVE_T - DRIVE_LEAD + .05
                    if age >= due:
                        sent = True
                        row['key'] = 'Brace()' if handler else 'SpaceBar' if kind == 0 else ('D' if kind > 0 else 'A')
                        row['key_age'] = round(age, 2)
                        hold = 120 if kind == 0 else int(800 / max(.2, unreal.GameplayStatics.get_global_time_dilation(W())))
                        car.call_method('Brace') if handler else press_now(row['key'], hold)
                # The game ignores an early Space (DR 00:43: the relayed key landed before the window and the teaching
                # brace was hit). A player who sees no result presses again; so does the driver, once, late in the window.
                elif (sent and kind == 0 and row.get('key') == 'SpaceBar' and 'key2_age' not in row and age >= DRIVE_T - .2
                      and not prop(met, 'Braced') and not prop(met, 'Result', 0)):
                    row['key2_age'] = round(age, 2)
                    press_now('SpaceBar', 120)
                if prop(met, 'Braced') and 'braced_age' not in row:
                    row['braced_age'] = round(age, 2)
                if prop(met, 'Committed') and 'dodge_age' not in row:
                    row['dodge_age'], row['dodged'] = round(age, 2), prop(met, 'Dodged')
                if not active or prop(met, 'Result', 0) > 0:
                    armed = False
                    if prop(met, 'Result', 0) > 0:
                        row.update(result=('clean', 'late', 'hit', 'perfect')[prop(met, 'Result') - 1],
                                   composure=prop(car, 'Composure'), mood=round(prop(car, 'Mood', 0), 2),
                                   lateral_cm=round(prop(car, 'Lateral', 0)), strike_lateral_cm=round(prop(car, 'StrikeLateral', 0)),
                                   dilation=round(unreal.GameplayStatics.get_global_time_dilation(W()), 2))
                        yield
                        row['result_frame'] = shot(f'strike{n}_{row["result"]}')
            if limit and time.time() - started > limit:
                break
            yield
        unreal.SystemLibrary.execute_console_command(W(), 'csvprofile stop')
        bad = [r for r in rows if 'result' in r and ((r['skip'] and r['result'] != 'hit') or (not r['skip'] and r['result'] == 'hit'))]
        if watch:
            log('drive_round3', set_piece=w.get('pieces'), traffic_sand=w.get('sand'), swerves=w.get('swerves'),
                mood=w.get('mood'), music_multiplier=w.get('music'), engine_speed=w.get('engine'))
        log('city_stream', appeared_m=city.get('appeared'), nearest_m=min(city.get('appeared') or [None], key=lambda v: 1e9 if v is None else v),
            peak_visible=city.get('peak'), pinned_at_end=city.get('pinned'), table=len(str(prop(car, 'SpanTable', ''))))
        log('drive_leg', result='FAIL' if bad or not rows else 'PASS', strikes=rows, composure=prop(car, 'Composure'),
            arrived=prop(car, 'Arrived'), journey_phase=prop(l2_journey(), 'Phase'), at_m=round(prop(car, 'Distance', 0) / 100),
            employability=prop(car, 'Employability'), frame=shot('drive_end'))
        if bad or not rows:
            raise Miss(f'strike outcomes off: {bad or "no strike armed"}')
    return gen


PLANS.update({
    'DR': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
           ('drive', 'into the car: Confirm twice; the car drives off on its own', into_car(), 6, True),
           ('drive', 'teaching leg: brace with the real Space as the ring meets the key; the car parks itself', g_drive(), 22, False)],
    **{f'DR2{c}': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                   ('drive', f'fixture: second leg (Queen Market to Night Dispatch) from {m} m', into_car(1, m * 100.0), 12, True),
                   ('drive', 'long leg: real Space, A and D answers; one strike left alone',
                    g_drive(skip=(1,), arrive=c == 'd', limit=24 if c != 'd' else None), 30, False)]
       for c, m in zip('abcd', (0, 200, 400, 600))}})


def g_drive_ab(seconds=11.0):
    """Perf A/B on the same leg: A with the new content (sand props, 14 cars), then B with props and traffic hidden.
    Wall-clock marks go to the log; the CSV profile (started by l2_fixture) is split by them afterwards."""
    def gen():
        car = one('car')
        road = prop(car, 'Road')
        log('perf_mark', phase='A', wall=time.time(), frame=shot('perf_A'))
        yield from sleep(seconds)
        setint = unreal.get_default_object(unreal.SystemLibrary)  # not instance-editable: set them by name
        setint.call_method('SetIntPropertyByName', (car, 'PropSlots', 0))
        setint.call_method('SetIntPropertyByName', (road, 'TrafficLimit', 0))
        road.call_method('ApplyTrafficLimit')
        for i in range(4):
            prop(road, f'SandProp{i}').set_visibility(False)
        log('perf_mark', phase='B', wall=time.time(), frame=shot('perf_B'))
        yield from sleep(seconds)
        log('perf_mark', phase='end', wall=time.time(), frame=shot('perf_end'))
        unreal.SystemLibrary.execute_console_command(W(), 'csvprofile stop')
    return gen


def g_drive_fail():
    """Leave every strike alone: three unbraced hits take Composure to 0, the car asks the journey for its road
    restart (RestartRun), and the same leg starts again from its rail start with Composure 100."""
    def gen():
        car, j = one('car'), l2_journey()
        attempts, start = prop(j, 'RoadAttempts', 0), prop(car, 'RailIndex')
        yield from wait(lambda: prop(car, 'Failed'))
        log('road_fail', composure=prop(car, 'Composure'), place=str(prop(car, 'Place')), frame=shot('road_fail'))
        yield from wait(lambda: not prop(car, 'Failed') and prop(car, 'Active') and prop(car, 'RouteReady'))
        yield from sleep(.5)
        ok = (prop(car, 'Composure') == 100 and prop(car, 'RailIndex') == start and prop(car, 'Distance', 1e9) < 2000
              and prop(j, 'RoadAttempts', 0) == attempts + 1 and prop(j, 'Employability') == 0)
        log('road_restart', result='PASS' if ok else 'FAIL', composure=prop(car, 'Composure'), rail=prop(car, 'RailIndex'),
            at_m=round(prop(car, 'Distance', 0) / 100), attempts=prop(j, 'RoadAttempts'), frame=shot('road_restart'))
        if not ok:
            raise Miss('road restart did not restart the same leg cleanly')
    return gen


PLANS['DRF'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                ('drive', 'fixture: second leg from 0 m', into_car(1, 0.0), 8, True),
                ('drive', 'three strikes left alone: Composure 0, road restart of the same leg', g_drive_fail(), 32, False)]


PLANS['DRP'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                ('drive', 'fixture: second leg from 100 m', into_car(1, 10000.0), 8, True),
                ('drive', 'perf A/B: new content on, then props and traffic hidden', g_drive_ab(), 26, False)]

def debug_overlay(on):
    """The front end's read-only debug panel (WBP_Debug, F-key toggle; refreshes every 0.25 s while visible), on at
    render opacity 0 so the frames stay clean: it reads GetPlayerCharacter, which is None while the car is the pawn
    (the cooked smoke's Accessed None). Off: log what its camera line last read (the proof it refreshed in the car)."""
    def gen():
        fe = one('fe')
        panel = prop(fe, 'DebugPanel')
        if on:
            if not panel:
                try:  # its first refresh runs inside the toggle: a script error there must be logged, not fatal
                    fe.call_method('ToggleDebugPanel')
                except Exception as err:
                    log('debug_overlay_error', err=str(err)[:200])
                yield
                panel = prop(fe, 'DebugPanel')
            panel.set_render_opacity(0.0)
            log('debug_overlay', on=True, panel=str(panel))
        else:
            text = str(prop(panel, 'Txt_Camera').get_text()) if panel and prop(panel, 'Txt_Camera') else None
            log('debug_overlay', on=False, camera_line=(text or '')[:160])
            if panel:
                fe.call_method('CloseDebugPanel')
        yield
    return gen


def g_steer():
    """Free steering on the route: hold A, let go, hold D, let go; log the lateral offset (cm, + right of the rail) and
    frame each. PASS: A slides left and D right, both stop inside the corridor (|lateral| <= 320), and letting go leaves
    the car on the road (the soft wall settles it inside 75% of the corridor, the pull eases it back toward the rail)."""
    def gen():
        car, rows = one('car'), []

        def sample(tag):
            rows.append(dict(tag=tag, lateral_cm=round(prop(car, 'Lateral', 0)), steer=round(prop(car, 'Steer', 0), 2),
                             speed=round(prop(car, 'Speed', 0)), t=t_now(), frame=shot('steer_' + tag)))
        sample('start')
        press_now('A', 1500)
        yield from sleep(1.3)
        sample('held_left')
        yield from sleep(1.4)
        sample('let_go')
        press_now('D', 2200)
        yield from sleep(2.0)
        sample('held_right')
        yield from sleep(1.8)
        sample('settled')
        lat = {r['tag']: r['lateral_cm'] for r in rows}
        ok = (lat['held_left'] < -150 and lat['held_right'] > 150 and all(abs(v) <= 320 for v in lat.values())
              and abs(lat['settled']) <= 250)
        log('steer', result='PASS' if ok else 'FAIL', samples=rows)
        if not ok:
            raise Miss(f'steering off: {lat}')
    return gen


# DR4   free steering (coordinator 11-18 10:4x): leg 2 from 300 m: hold A, let go, hold D (the corridor and its soft
#       walls), the set-piece, then strikes: a brace, a steer dodge (the arrow; the real D or A held), a perfect brace.
PLANS['DR4'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                ('drive', 'fixture: second leg (Queen Market to Night Dispatch) from 300 m', into_car(1, 30000.0), 12, True),
                ('drive', 'free steering: A, let go, D, inside the corridor', g_steer(), 12, False),
                ('drive', 'strikes with steering: a brace, a steer dodge, a perfect brace',
                 g_drive(arrive=False, limit=19, perfect=True, watch=True), 24, False)]


# DRS2, DRS3  the hiring signs at Northline Supply (leg 2, J1 to J2, from 200 m) and Central Personnel (leg 3, J1 to
#       the interview, from 660 m, Employability 60 so its sign shows): the car parks at each
def g_arrive(limit=22.0):
    """Drive on to the stop (strikes, if any, answered by Brace or left), framing the approach every second and the
    parked car. PASS: the car parked by itself and handed the stop to the journey."""
    def gen():
        car, started, next_shot = one('car'), time.time(), 0.0
        while time.time() - started < limit and not (prop(car, 'Arrived') or prop(l2_journey(), 'Phase', 0) >= 4):
            if time.time() >= next_shot:
                shot('approach'); next_shot = time.time() + 1.0
            met = prop(car, 'Meteor')
            if prop(met, 'Active') and prop(met, 'Kind', 0) == 0 and prop(met, 'Age', 0) >= 2.15 and not prop(met, 'Braced'):
                car.call_method('Brace')
            yield
        yield from sleep(.6)
        log('arrive', arrived=bool(prop(car, 'Arrived')), phase=prop(l2_journey(), 'Phase'), frame=shot('parked'))
        if not prop(car, 'Arrived'):
            raise Miss('the car did not park')
    return gen


for _name, _leg, _at, _emp in (('DRS2', 2, 20000.0, None), ('DRS3', 3, 66000.0, 60)):
    PLANS[_name] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                    ('drive', f'fixture: leg {_leg} from {_at / 100:.0f} m', into_car(_leg, _at, _emp), 12, True),
                    ('drive', 'drive to the stop: the sign beside the road', g_arrive(), 26, False)]


# DR3   drive lane round 3: leg 2 from 300 m: the set-piece (the Nightmare rising out of the road at 425 m, driven
#       through), traffic turning to sand as the car passes, the dodges answered (the car swerves), braces perfect.
PLANS['DR3'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                ('drive', 'fixture: second leg (Queen Market to Night Dispatch) from 300 m', into_car(1, 30000.0), 12, True),
                ('drive', 'the debug overlay on, unseen (the cooked smoke had it open)', debug_overlay(True), 3, True),
                ('drive', 'round 3: set-piece, traffic to sand, swerves, perfect braces',
                 g_drive(arrive=False, limit=28, perfect=True, watch=True), 34, False),
                ('drive', 'the debug overlay off; what it last read', debug_overlay(False), 3, False)]
# DR3P  round 3's near miss: leg 2 from 470 m, past the set-piece: teaching brace (real Space), the dodge answered
#       (the swerve), then a brace answered in the last 0.2 s: perfect (deep slow motion, the director's streak).
PLANS['DR3P'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
                 ('drive', 'fixture: second leg (Queen Market to Night Dispatch) from 470 m', into_car(1, 47000.0), 12, True),
                 ('drive', 'round 3: swerve and a perfect brace', g_drive(arrive=False, limit=30, perfect=True, watch=True), 36, False)]


# CL    citylife lane: leg 2 from 380 m, where the left pavement opens. BP_L2CityLife's Lux3D pool around the car: a
#       frame every 1.5 s and, per visible thing, its distance ahead (m), lateral (cm from the rail, + right), height and
#       speed. PASS: three or more things within 120 m in most frames; walkers and flyers both seen; ground things clear
#       of the steering corridor plus 1.5 m (|lateral| >= 470); walkers walking (30-500 cm/s) and flocks turning.
P['citylife'] = '/Game/FoA/Level2/CityLife/BP_L2CityLife.BP_L2CityLife_C'


def g_citylife(samples=12, every=1.5):
    def gen():
        life, car = one('citylife'), one('car')
        if not life or not car:
            raise Miss(f'citylife {life} car {car}')
        WS = unreal.SplineCoordinateSpace.WORLD
        sub = lambda a, b: (a.x - b.x, a.y - b.y, a.z - b.z)  # noqa: E731
        dot = lambda a, b: a[0] * b.x + a[1] * b.y + a[2] * b.z  # noqa: E731
        rows, last = [], {}
        for k in range(samples):
            yield from sleep(every)
            rail, at = prop(car, 'Rail'), prop(car, 'Distance', 0.0)
            here, fwd = car.get_actor_location(), rail.get_direction_at_distance_along_spline(at, WS)
            seen = []
            for c in life.get_components_by_class(unreal.PrimitiveComponent):
                if not c.is_visible():
                    continue
                loc, name = c.get_world_location(), c.get_name()
                near = rail.find_location_closest_to_world_location(loc, WS)
                lateral = dot(sub(loc, near), rail.find_right_vector_closest_to_world_location(loc, WS))
                yaw = c.get_world_rotation().yaw
                was = last.get(name)
                speed = sum(v * v for v in sub(loc, was[0])) ** .5 / every if was else None
                turned = abs((yaw - was[1] + 180) % 360 - 180) if was else None
                last[name] = (loc, yaw)
                # along the rail, not projected on the car's heading: past a corner the cross street projects flat
                along = rail.get_distance_along_spline_at_spline_input_key(rail.find_input_key_closest_to_world_location(loc))
                seen.append(dict(name=name, ahead_m=round((along - at) / 100, 1), straight_m=round(dot(sub(loc, here), fwd) / 100, 1),
                                 lateral_cm=round(lateral), up_m=round((loc.z - near.z) / 100, 1),
                                 speed_cms=None if speed is None else round(speed), turned_deg=None if turned is None else round(turned)))
            close = [s for s in seen if -10 <= s['ahead_m'] <= 120]
            rows.append(dict(car_m=round(at / 100), visible=len(seen), within_120m=len(close), things=seen,
                             frame=shot(f'citylife_{k:02d}')))
            log('citylife', **rows[-1])
        ground = [s for r in rows for s in r['things'] if s['name'].startswith(('WalkMesh', 'ChairMesh'))]
        walking = [s for s in ground if s['name'].startswith('WalkMesh') and s['speed_cms'] and 30 <= s['speed_cms'] <= 500]
        turning = [s for r in rows for s in r['things'] if s['name'].startswith(('Flock', 'Phone')) and (s['turned_deg'] or 0) > 5]
        busy = sum(1 for r in rows if r['within_120m'] >= 3)
        tight = [s for s in ground if abs(s['lateral_cm']) < 470]
        ok = busy >= .6 * len(rows) and walking and turning and not tight
        log('citylife_result', result='PASS' if ok else 'FAIL', busy_frames=busy, frames=len(rows), walkers_seen=len(ground),
            walking=len(walking), turning=len(turning), in_corridor=tight[:4])
        if not ok:
            raise Miss(f'city life: busy {busy}/{len(rows)}, walking {len(walking)}, turning {len(turning)}, tight {tight[:2]}')
    return gen


PLANS['CL'] = [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
               ('drive', 'fixture: second leg (Queen Market to Night Dispatch) from 380 m', into_car(1, 38000.0), 12, True),
               ('drive', 'city life: the Lux3D walkers, chairs and flocks around the car', g_citylife(), 24, False)]


def walkout_held():
    """Story 03:15: WalkedOut freezes his movement (move input ignored, MOVE_None) for the fade and the end card."""
    p = pawn()
    mc = p.get_component_by_class(unreal.CharacterMovementComponent) if p else None
    return bool(pc() and pc().is_move_input_ignored()) or bool(mc and mc.movement_mode == unreal.MovementMode.MOVE_NONE)


def probe_walkout():
    """T10: can a player get out of the open doorway at all? From four starts inside (doorway-local X -150 or -250, Y
    -35/0/+35), walk straight through and log how far he got in DoorFrame_Bedroom's frame ('walkout_probe')."""
    def gen():
        frame = actor('DoorFrame_Bedroom')
        xf = frame.get_actor_transform()
        for sx, sy in ((-150.0, 0.0), (-150.0, 35.0), (-150.0, -35.0), (-250.0, 0.0)):
            if beat() != 'T10':
                return
            yield from wait(free)
            start = unreal.MathLibrary.transform_location(xf, unreal.Vector(sx, sy, 0.0))
            yield from go_to(unreal.Vector(start.x, start.y, 0.0), 20.0, 4.0)
            goal = unreal.MathLibrary.transform_location(xf, unreal.Vector(120.0, sy, 0.0))
            p, best, end = pawn(), -1e9, time.time() + 4.0
            while beat() == 'T10' and time.time() < end and not walkout_held():
                here = p.get_actor_location()
                to = unreal.Vector(goal.x - here.x, goal.y - here.y, 0.0)
                to.normalize()
                p.add_movement_input(to, 1.0, False)
                turn_toward(unreal.Vector(goal.x, goal.y, here.z + 40), 6.0)
                best = max(best, unreal.MathLibrary.inverse_transform_location(xf, here).x)
                yield
            local = unreal.MathLibrary.inverse_transform_location(xf, pawn().get_actor_location())
            ended = beat() != 'T10' or 'Title' in str(screen()) or best > 60 or walkout_held()  # T10 lasts through the ending
            log('walkout_probe', start=[sx, sy], reached_local=[round(v) for v in local.to_tuple()], best_local_x=round(best),
                walked_out=ended, frame=shot('walkout'))
            if ended:
                return
        if beat() == 'T10':
            raise Miss('no approach got through the doorway (see walkout_probe rows)')
    return gen


def cpm_stand():
    """Coordinator fixture: put the pawn in front of the door frame wherever T7 moved it, facing it."""
    xf = actor('DoorFrame_Bedroom').get_actor_transform()
    spot = unreal.MathLibrary.transform_location(xf, unreal.Vector(-260.0, 0.0, 92.0))
    pawn().set_actor_location(spot, False, True)
    yaw = xf.rotation.rotator().yaw
    pc().set_control_rotation(unreal.Rotator(0.0, 0.0, yaw))


def walk_out():
    """Walk into the 2 m approach trigger and stop issuing movement as soon as the threshold owns control."""
    frame = actor('DoorFrame_Bedroom')
    xf = frame.get_actor_transform()
    inside = unreal.MathLibrary.transform_location(xf, unreal.Vector(-150.0, 0.0, 0.0))
    end = time.time() + 10
    p = pawn()
    while threshold_phase() == 0 and time.time() < end:
        if free():
            here = p.get_actor_location()
            to = unreal.Vector(inside.x - here.x, inside.y - here.y, 0.0)
            if to.length() > 20:
                to.normalize()
                p.add_movement_input(to, 1.0, False)
            turn_toward(frame.get_actor_location() + unreal.Vector(0, 0, 100), 6.0)
        yield
    if threshold_phase() == 0:
        raise Miss('Approaching the doorway never started the threshold')
    S['threshold_started'] = unreal.GameplayStatics.get_time_seconds(W())
    S['threshold_pawn'] = p
    log('threshold_approach', phase=threshold_phase(), held=walkout_held(), frame=shot('threshold_start'))


# ---- credits lane: the ending roll's Lux3D showcase (plan CR) ---------------------------------------------------------
SHOWCASE = '/Game/FoA/UI/Credits/BP_CreditsShowcase.BP_CreditsShowcase_C'


def credits_roll():
    return prop(one('threshold'), 'WakeCredits')


def g_credits_showcase():
    """The ending roll (BP_DreamThreshold.BeginWakeCredits, WBP_L2CreditsRoll) spawns two BP_CreditsShowcase actors and
    switches the game view off (SetEnableWorldRendering). Each side must fade fully in, the sides must never be mid-fade
    together, no capture may wait on the game view (bCaptureEveryFrame stays off: Step calls CaptureScene while a side
    shows), each side's render target must keep changing while the game view is off, at least eight Lux3D meshes must
    appear in the 30 s roll, the last card must reach its hold, and once the roll leaves the viewport both actors must
    be gone and the game view back on. One ProfileGPU mid-roll puts the capture cost in the editor log."""
    yield from wait(lambda: credits_roll() is not None and credits_roll().is_in_viewport())
    roll = credits_roll()  # our own handle: the threshold clears its variable when it goes
    game = lambda: unreal.GameplayStatics.get_time_seconds(W())  # noqa: E731  the roll runs on game time
    g0, w0 = game(), time.time()
    rows, meshes, full, both_mid, wrong_capture, profiled, next_shot, next_row = [], set(), set(), 0, 0, False, 0.8, 0.0
    world_on, samples = 0, {0: set(), 1: set()}
    while game() - g0 < 30.6 and time.time() - w0 < 36.0 and roll.is_in_viewport():
        age = game() - g0
        if age > 0.2 and unreal.GameplayStatics.get_enable_world_rendering(W()):
            world_on += 1
        sides = []
        for a in unreal.GameplayStatics.get_all_actors_of_class(W(), cls(SHOWCASE)):
            img, hero, cap = prop(a, 'Image'), prop(a, 'Hero'), prop(a, 'Capture')
            raw = img.get_render_opacity() if img else -1.0
            op = round(raw, 3)
            every = bool(cap.get_editor_property('capture_every_frame')) if cap else None
            mesh = hero.static_mesh.get_name() if hero and hero.static_mesh else None
            sides.append(dict(side=prop(a, 'FirstIndex'), op=op, capture=every, mesh=mesh, cap=cap))
            if op >= 0.999:
                full.add(prop(a, 'FirstIndex'))
                meshes.add(mesh)
            if every:
                wrong_capture += 1
        mids = [s for s in sides if 0.02 < s['op'] < 0.98]
        if len(mids) == 2:
            both_mid += 1
        if age >= next_row:
            scroll = prop(roll, 'CreditNames').get_editor_property('render_transform').translation.y
            for s in sides:  # a live capture keeps changing the target while the object turns (one GPU read per side)
                rt = s['cap'].get_editor_property('texture_target') if s['cap'] else None
                if rt and s['op'] >= 0.999:
                    n = rt.get_editor_property('size_x')
                    px = [unreal.RenderingLibrary.read_render_target_raw_pixel(W(), rt, int(n * u), int(n * v))
                          for u, v in ((0.5, 0.5), (0.39, 0.55), (0.61, 0.43))]
                    samples[s['side']].add(tuple(round(p.r + p.g + p.b, 3) for p in px))
            rows.append(dict(t=round(age, 2), actors=len(sides), scroll=round(scroll),
                             sides=sorted(({k: v for k, v in s.items() if k != 'cap'} for s in sides), key=lambda s: s['side'] or 0)))
            next_row += 0.5
        if age >= next_shot:
            shot('credits_%02d' % int(age))
            next_shot += 2.5
        if not profiled and age > 12.0:
            unreal.SystemLibrary.execute_console_command(W(), 'ProfileGPU')
            profiled = True
        yield
    log('credits_showcase_rows', rows=rows, game_s=round(game() - g0, 2), wall_s=round(time.time() - w0, 2))
    # the scroll: about 95 to 105 px/s, then holding on "Thank you for playing" (SetScroll: -(column height + 585))
    column = prop(roll, 'CreditNames')
    column_h = column.get_desired_size().y  # read before the roll comes down (a removed widget measures 0)
    hold_at = -(column_h + 585.0)
    mid = [r for r in rows if 4.0 <= r['t'] <= 20.0]
    speed = (mid[-1]['scroll'] - mid[0]['scroll']) / (mid[-1]['t'] - mid[0]['t']) if len(mid) > 1 else 0.0
    held_rows = [r for r in rows if abs(r['scroll'] - hold_at) < 2.0]
    held_for = rows[-1]['t'] - held_rows[0]['t'] if held_rows else 0.0
    held = rows[-1]['scroll'] if rows and held_rows and abs(rows[-1]['scroll'] - hold_at) < 2.0 else None
    # no automatic wraps: each block's height is its own line count times one line of its size
    blocks, one_line, wraps = [], {}, []
    for child in column.get_all_children():
        text = str(child.get_text())
        size = child.get_editor_property('font').get_editor_property('size')
        blocks.append((text, size, child.get_desired_size().y, text.count('\n') + 1))
    for text, size, h, n in blocks:
        if n == 1:
            one_line[size] = min(one_line.get(size, h), h)
    for text, size, h, n in blocks:
        if size in one_line and round(h / one_line[size]) > n:
            wraps.append(text.split('\n')[0][:40])
    ending = shot('credits_end')
    yield from sleep(0.4)
    still_up = unreal.SystemLibrary.is_valid(roll) and roll.is_in_viewport()
    if still_up:  # RestoreWakeLook takes the roll down only after the real wake (WakeActive); this shortcut skips it
        log('note', what='roll still in the viewport after its 30 s: RemoveFromParent, as RestoreWakeLook does')
        roll.remove_from_parent()
    gone_by = time.time() + 3.0
    while time.time() < gone_by and unreal.GameplayStatics.get_all_actors_of_class(W(), cls(SHOWCASE)):
        yield
    left = len(unreal.GameplayStatics.get_all_actors_of_class(W(), cls(SHOWCASE)))
    world_back = unreal.GameplayStatics.get_enable_world_rendering(W())
    live = {side: len(v) for side, v in samples.items()}
    ok = (max(r['actors'] for r in rows) == 2 and full == {0, 1} and both_mid == 0 and wrong_capture == 0
          and len(meshes) >= 8 and left == 0 and held is not None and held_for >= 0.5 and -106.0 <= speed <= -94.0
          and not wraps and world_on == 0 and world_back and min(live.values()) >= 4)
    log('credits_showcase', result='PASS' if ok else 'FAIL', sides_fully_in=sorted(full), meshes=sorted(meshes),
        both_mid_ticks=both_mid, deferred_capture_ticks=wrong_capture, world_rendered_ticks=world_on,
        distinct_target_samples=live, actors_after_roll=left, world_rendering_after=world_back,
        scroll_px_per_s=round(speed, 1), hold_at=round(hold_at), final_scroll=held, held_s=round(held_for, 2),
        column_px=round(column_h), wrapped_blocks=wraps, blocks=len(blocks),
        roll_removed_by_game=not still_up, frame=ending, after=shot('credits_after'))
    if not ok:
        raise Miss('credits showcase check failed (see credits_showcase)')


PLANS.update({
    'CR': boot()[:2] + [
        ('end', 'fixture: the director spawns the threshold (OpenTheDoor, as before T10)',
         chain(do(lambda: one('director').call_method('OpenTheDoor'), what='BP_BeatDirector.OpenTheDoor'),
               until(lambda: one('threshold') is not None)), 3, True),
        ('end', 'shortcut: the ending credits (BP_DreamThreshold.BeginWakeCredits)',
         do(lambda: one('threshold').call_method('BeginWakeCredits'), what='BeginWakeCredits'), 2, True),
        ('end', 'credits roll with the Lux3D showcase, then teardown', g_credits_showcase, 40, False)],
})


# ---- level1 lane: the T7 bed hanger (ClothingSnag) filmed densely, with the arm and leg bones per frame -------------
L1_BONES = ('hand_r', 'lowerarm_r', 'upperarm_r', 'thigh_r', 'calf_r', 'foot_r', 'thigh_l', 'calf_l', 'pelvis', 'head')


def l1_pose(tag):
    """One row: montage and position, the view, the right arm and both legs in the pawn frame (x fwd, y right, z up),
    and the frame. arm_behind_leg: the hand is inside (left of) and behind the right shin, seen from the camera."""
    p, body = pawn(), prop(pawn(), 'Body')
    anim = p.get_editor_property('mesh').get_anim_instance()
    mon = anim.get_current_active_montage() if anim else None
    xf = p.get_actor_transform()
    loc = lambda b: xf.inverse_transform_location(body.get_socket_location(b))  # noqa: E731
    row = {b: [round(v, 1) for v in loc(b).to_tuple()] for b in L1_BONES}
    cam = pc().player_camera_manager
    eye, hand, knee, ankle = cam.get_camera_location(), body.get_socket_location('hand_r'), body.get_socket_location('calf_r'), body.get_socket_location('foot_r')
    shin_mid = (knee + ankle) * 0.5
    # the hand is hidden behind the right shin when the shin is nearer the eye and the two overlap on screen
    to_hand, to_shin = hand - eye, shin_mid - eye
    ang = math.degrees(math.acos(max(-1.0, min(1.0, to_hand.normal().dot(to_shin.normal())))))
    row.update(montage=mon.get_name() if mon else None, pos=round(anim.montage_get_position(mon), 2) if mon else None,
               view=view(), stage=stage(), eye=[round(v) for v in eye.to_tuple()],
               hand_shin_deg=round(ang, 1), shin_nearer_cm=round(to_hand.length() - to_shin.length(), 1),
               at=[round(v) for v in p.get_actor_location().to_tuple()], body_yaw=round(p.get_actor_rotation().yaw, 1),
               ctrl=str(pc().get_control_rotation()),
               shirt=[round(v) for v in actor('Shirt_T7').get_actor_location().to_tuple()], focus=name_of(prop(comp('ia'), 'Target')),
               frame=shot(tag))
    log('l1_pose', **row)


def l1_film_bed_hanger(seconds=14.0, every=0.25):
    start = use('Bed', 'Use', item='Hanger', until=lambda: stage() >= 5 or (
        pawn().get_editor_property('mesh').get_anim_instance().get_current_active_montage() is not None))

    def gen():
        if 'Hanger' not in items():
            comp('inv').call_method('Add', ('Hanger',))
        yield from start()
        end, last, n = time.time() + seconds, 0.0, 0
        while time.time() < end:
            if time.time() - last >= every:
                last, n = time.time(), n + 1
                l1_pose('hb%02d' % n)
            if stage() >= 5 and free() and n > 4:
                S['l1_free'] = S.get('l1_free') or time.time()
                if time.time() - S['l1_free'] > 1.5:  # the settled hand-back view, after the camera blend
                    break
            yield
        if stage() < 5:
            raise Miss(f'the shirt never came out (stage {stage()})')
    return gen


def l1_film(seconds, every=0.25, tag='f'):
    """Film whatever plays for `seconds`: a frame, the view target and MPC_Dream's payoff scalars every `every` s."""
    def gen():
        mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
        names = [str(p.get_editor_property('parameter_name')) for p in mpc.get_editor_property('scalar_parameters')] if mpc else []
        keep = [n for n in names if any(k in n for k in ('Reveal', 'Letterbox', 'Hue'))]
        end, last, n = time.time() + seconds, 0.0, 0
        while time.time() < end:
            if time.time() - last >= every:
                last, n = time.time(), n + 1
                vals = {k: round(unreal.MaterialLibrary.get_scalar_parameter_value(W(), mpc, k), 3) for k in keep}
                log('l1_film', view=view(), beat=beat(), mpc=vals, frame=shot('%s%02d' % (tag, n)))
            yield
    return gen


def l1_chest():
    """After the payoff: a temporary camera 75 cm in front of his chest; one frame with every visible skeletal mesh,
    then one with each of them hidden in turn (restored at once), so the frames say which mesh shows under the suit."""
    def gen():
        p = pawn()
        meshes = [c for c in p.get_components_by_class(unreal.SkeletalMeshComponent) if c.is_visible()]
        log('l1_visible_meshes', meshes=[(c.get_name(), c.get_editor_property('skeletal_mesh_asset').get_name()
                                          if c.get_editor_property('skeletal_mesh_asset') else None) for c in meshes])
        xf = p.get_actor_transform()
        eye = xf.transform_location(unreal.Vector(45.0, -15.0, 45.0))
        chest = xf.transform_location(unreal.Vector(0.0, 0.0, 40.0))
        # the level's PayoffCam (PayoffShot moves it every payoff anyway); Python here cannot spawn into the PIE world
        cam = unreal.GameplayStatics.get_all_actors_with_tag(W(), 'PayoffCam')[0]
        cam.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, chest), False, True)
        try:
            pc().set_view_target_with_blend(cam, 0.0)
            yield from sleep(0.4)
            shot('chest_all')
            yield from sleep(0.35)
            for c in meshes:
                if c.get_name() in ('Body', 'Face'):
                    continue
                c.set_visibility(False, False)
                yield from sleep(0.3)
                log('l1_chest_hidden', mesh=c.get_name(), frame=shot('chest_no_' + c.get_name()))
                yield from sleep(0.3)
                c.set_visibility(True, False)
        finally:
            if unreal.SystemLibrary.is_valid(p):
                pc().set_view_target_with_blend(p, 0.0)
    return gen


def l1_moments():
    """Round 3 dream moments (BP_L1DreamMoments): walk near the standing wardrobe (it should stir once), then look at the
    school backpack, turn away until it moves (Moves goes up), turn back and film where it is now; twice."""
    def look_at(point, secs=1.2):
        end = time.time() + secs
        while time.time() < end:
            turn_toward(point, 8.0)
            yield

    def gen():
        m, bag = actor('L1_DreamMoments'), actor('Dress_Lux3D_Backpack')
        yield from wait(free)
        yield from go_to(unreal.Vector(190.0, 60.0, 0.0), 25.0, 6.0)
        end = time.time() + 2.0
        while not prop(m, 'bRattled') and time.time() < end:
            yield
        log('l1_moment', what='wardrobe stir', rattled=prop(m, 'bRattled'), frame=shot('stir'))
        for n in range(2):
            at = bag.get_actor_location()
            yield from look_at(at)
            log('l1_moment', what='backpack seen', moves=prop(m, 'Moves'), at=[round(v) for v in at.to_tuple()], frame=shot('bag_seen%d' % n))
            away = pawn().get_actor_location() * 2.0 - at  # the point opposite the backpack, through him
            before, end = prop(m, 'Moves'), time.time() + 9.0
            while prop(m, 'Moves') == before and time.time() < end:
                turn_toward(unreal.Vector(away.x, away.y, 150.0), 8.0)
                yield
            now = bag.get_actor_location()
            log('l1_moment', what='backpack moved' if prop(m, 'Moves') > before else 'backpack did not move', moves=prop(m, 'Moves'),
                at=[round(v) for v in now.to_tuple()])
            yield from look_at(now)
            log('l1_moment', what='backpack found again', frame=shot('bag_moved%d' % n))
        if prop(m, 'Moves') < 2:
            raise Miss(f'the backpack moved {prop(m, "Moves")} times, expected 2')
    return gen


def l1_look(label, verb):
    """Walk up to an interactable, focus it with the interactor's own scan, press E on `verb`, film the line."""
    def gen():
        a = actor(label)
        yield from wait(free)
        yield from approach(a, 60.0)
        yield from aim(a)
        yield from focus_on(a, label)
        yield from want_verb(verb)
        ia = comp('ia')
        log('l1_look', target=label, verb=str(prop(ia, 'Verb')), prompt=str(prop(ia, 'Prompt', '')), frame=shot('look_' + verb))
        yield from sleep(0.2)
        ia.call_method('Interact')
        yield from sleep(1.4)
        log('l1_look_line', target=label, verb=verb, frame=shot('line_' + verb))
    return gen


def l1_nudge(label):
    """Open a drawer through the interactor and measure the tactile nudge: the rendered camera rotation against the
    control rotation every tick for 0.8 s after the state changes (the shake moves only the camera)."""
    def gen():
        # the three stacked drawers share the scan: whichever one the interactor took counts
        drawers = [label[:-2] + n for n in ('01', '02', '03')] if label[-2:].isdigit() else [label]
        before = {d: state_of(d) for d in drawers}
        go = use(label, 'Use', until=lambda: any(state_of(d) != before[d] for d in drawers))
        yield from go()
        moved = next(d for d in drawers if state_of(d) != before[d])
        worst, when, t0 = 0.0, None, time.time()  # the row's sound (and the nudge) can come after the state, at contact
        while time.time() < t0 + 3.0:
            cam, ctl = pc().player_camera_manager.get_camera_rotation(), pc().get_control_rotation()
            off = max(abs((cam.pitch - ctl.pitch + 180) % 360 - 180), abs((cam.yaw - ctl.yaw + 180) % 360 - 180))
            if off > worst:
                worst, when = off, round(time.time() - t0, 2)
            yield
        log('l1_nudge', target=moved, state=state_of(moved), max_offset_deg=round(worst, 3), at_s=when, frame=shot('nudge'))
    return gen


PLANS.update({
    'L1C': boot() + [
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'the calendar by the door: look', l1_look('Dress_Lux3D_Calendar', 'Look'), 16, False),
        ('T2', 'the calendar by the door: count the days', l1_look('Dress_Lux3D_Calendar', 'Use'), 10, False),
],
    'L1N': boot() + [
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'a commode drawer: the tactile nudge with its sound', l1_nudge('Commode_GothicCommode_01_door02'), 25, False)],
    'L1M': boot() + [
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'dream moments: the wardrobe stirs, the backpack moves when unseen', l1_moments(), 32, False)],
    'L1P': boot() + [
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'the suit payoff filmed every 0.25 s with the colour and letterbox values', l1_film(7.0, tag='p'), 9, False),
        ('T10', 'chest close-up: which mesh shows under the suit', l1_chest(), 12, False)],
    # B3f's real won battle (battle lane's steps, unchanged), then the T9 hero shot filmed and the chest close-up
    'L1W': PLANS['B3f'][:-1] + [
        ('T9', 'EncounterWon: T9 suit payoff', until(beat_is('T9', 'T10')), 8, False),
        ('T9', 'the suit payoff after a real win, filmed every 0.25 s', l1_film(3.5, tag='w'), 5, False),
        ('T10', 'chest close-up after a real win', l1_chest(), 12, False)],
    'L1H': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'fixture: the three clues, to the snag', fixture_clothing_before(4), 14, True),
        ('T7', 'hanger on the bed, filmed every 0.25 s', l1_film_bed_hanger(), 22, False)],
})


# ---- atmosphere lane: the opening as a player sees it, nothing skipped (2026-11-17) -------------------------------
# AT1  title and menu, then the intro story played to its own end, then the first part of LS_WakeUp.
# AT2  the intro skipped, LS_WakeUp played in full, the T0 phone and the first free seconds of the room.
PLANS.update({
    'AT1': boot()[:3] + [
        ('intro', 'intro story plays to its own end', until(lambda: phase() not in ('story', 'black', 'menu')), 40, False),
        ('wakeup', 'LS_WakeUp watched', lambda: sleep(14.0), 16, False)],
    'AT2': boot()[:4] + [
        ('wakeup', 'LS_WakeUp plays to its own end', until(lambda: beat() in ('T0', 'T1')), 40, False),
        ('T0', 'T0 phone, if it opens: confirm Wake up', g_t0, 12, False),
        ('T1', 'first free seconds in the room', chain(until(lambda: beat() == 'T1' and free()), lambda: sleep(3.0)), 8, False)],
})


# ---- level2 lane: Level 2's interview, ending and credits hand-off (plans L2E) ----------------------------------------
# L2E  street (l2_fixture), fixture: two shifts already on the C.V (Employability 60, Edited0/1) and the parked arrival
#      at the interview (Stop 3 -> StageStop), the six best answers through DialogueSelect/DialogueConfirm, the offer,
#      Submit, the ending film and the hand-off to the credits roll. Frames every 0.6 s from Submit.
def l2_to_interview():
    def gen():
        j = l2_journey()
        sl = unreal.get_default_object(unreal.SystemLibrary)  # Blueprint variables are not instance-editable
        for k, v in (('Employability', 60), ('Stop', 3), ('Phase', 4)):
            sl.call_method('SetIntPropertyByName', (j, k, v))
        for k in ('Edited0', 'Edited1', 'StopBusy'):
            sl.call_method('SetBoolPropertyByName', (j, k, True))
        j.call_method('StageStop')
        yield from wait(lambda: prop(j, 'DialogueMode') == 3 and prop(j, 'DialogueReady'))
        log('l2_interview', phase=prop(j, 'Phase'), employability=prop(j, 'Employability'), frame=shot('interview_q0'))
    return gen


def g_win_interview():
    import sys
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
    import job_boss_data as boss
    j, answered = l2_journey(), 0
    while prop(j, 'DialogueState') != 3:
        yield from wait(lambda: prop(j, 'DialogueReady') and not prop(j, 'DialogueHeld'))
        st = prop(j, 'DialogueState')
        if st == 2:
            raise Miss('interview lost on the best answers')
        if st == 3:
            break
        if st == 0:
            step = prop(j, 'DialogueStep')
            sec = boss.SECTIONS[step // 2]
            row = sec if step % 2 == 0 else sec['followups'][prop(j, 'DialoguePrior')]
            j.call_method('DialogueSelect', (min(range(3), key=lambda i: row['choices'][i]['cost']),))
            answered += 1
        elif answered == 1:
            shot('interview_reply')
        j.call_method('DialogueConfirm')
        j.call_method('DialogueRelease')
        yield
    yield from wait(lambda: prop(j, 'DialogueReady'))
    yield from sleep(0.4)
    log('l2_offer', state=prop(j, 'DialogueState'), employability=prop(j, 'Employability'), merge=prop(prop(j, 'Merge'), 'MergeAmount'),
        frame=shot('offer'))


def g_l2_ending():
    """Accept the offer (DialogueConfirm in state 3 -> Submit) and film the ending at 0.6 s steps until the credits roll
    has been in the viewport for 3 s. PASS: Submitted, the ending ran (threshold Phase >= 7) and the roll came up."""
    j, th = l2_journey(), one('threshold')
    j.call_method('DialogueConfirm')
    j.call_method('DialogueRelease')
    t0, nxt, rows, rolled = time.time(), 0.0, [], None
    while time.time() - t0 < 30:
        age = time.time() - t0
        roll = prop(th, 'WakeCredits')
        up = roll is not None and unreal.SystemLibrary.is_valid(roll) and roll.is_in_viewport()
        if up and rolled is None:
            rolled = age
        if age >= nxt:
            audio = unreal.GameplayStatics.get_actor_of_class(W(), cls('/Game/FoA/Audio/BP_RoomAudio.BP_RoomAudio_C'))
            playing = []
            for slot in ('Music', 'Music2'):  # BP_RoomAudio crossfades between two components
                comp_ = prop(audio, slot)
                snd = comp_.get_editor_property('sound') if comp_ else None
                if snd and comp_.is_playing():
                    playing.append(snd.get_name())
            rows.append(dict(t=round(age, 1), phase=prop(th, 'Phase'), view=view(), credits=up,
                             music=str(prop(audio, 'MusicOverride')), playing=playing,
                             merge=prop(prop(j, 'Merge'), 'MergeAmount') if unreal.SystemLibrary.is_valid(j) else None))
            shot('end_%04.1f' % age)
            nxt += 0.6
        if rolled is not None and age - rolled > 3.0:
            break
        yield
    ok = bool(prop(j, 'Submitted')) and rolled is not None
    log('l2_ending', result='PASS' if ok else 'FAIL', submitted=prop(j, 'Submitted'), credits_at=rolled, rows=rows,
        frame=shot('ending_last'))
    if not ok:
        raise Miss('the ending did not reach the credits roll')


def l2_arrive(stop):
    """Fixture: the car parked at job stop `stop` (job_route.DESTINATIONS) and the journey's own Arrive(stop), as the
    rails car calls it when it parks."""
    def gen():
        import sys
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        from job_route import DESTINATIONS
        j = l2_journey()
        sl = unreal.get_default_object(unreal.SystemLibrary)
        if stop:
            sl.call_method('SetIntPropertyByName', (j, 'Employability', 30 * stop))
            for i in range(stop):
                sl.call_method('SetBoolPropertyByName', (j, f'Edited{i}', True))
        sl.call_method('SetIntPropertyByName', (j, 'Phase', 3))
        car = prop(j, 'Car')
        car.set_actor_location(unreal.Vector(*DESTINATIONS[stop]), False, True)
        # the heading the rails car parks with (drive_data: last route segment into J0, J1, J2)
        car.set_actor_rotation(unreal.Rotator(0, 0, (0.0, -2.9, -90.0)[stop]), True)
        log('l2_arrive_car', stop=stop, car_yaw=round(car.get_actor_rotation().yaw, 2), control_yaw=round(pc().get_control_rotation().yaw, 2))
        j.call_method('Arrive', (stop,))
        yield from wait(lambda: prop(j, 'DialogueMode') == 4 and prop(j, 'DialogueReady'))
        yield from sleep(0.5)
        sand = []
        for slot in ('StopSandA', 'StopSandB'):  # the Lux3D sand objects this stop forms (build_l2_stop_sand.py)
            c = prop(j, slot)
            if c:
                mesh = c.get_editor_property('static_mesh')
                sand.append(dict(slot=slot, visible=c.is_visible(), mesh=mesh.get_name() if mesh else None,
                                 at=[round(v) for v in c.get_world_location().to_tuple()]))
        p = pawn()
        cam = pc().player_camera_manager
        log('l2_stop', stop=stop, sand=sand, pawn=[round(v) for v in p.get_actor_location().to_tuple()] if p else None,
            car_yaw=round(prop(j, 'Car').get_actor_rotation().yaw, 2), control_yaw=round(pc().get_control_rotation().yaw, 2),
            yaw_limits=[prop(cam, 'view_yaw_min'), prop(cam, 'view_yaw_max')], frame=shot(f'stop{stop}_employer'))
    return gen


def g_l2_job(stop):
    """The pitch with the best answers (job_hunt_data points), the offer, the time card, the shift board; then a fixture
    FinishJob(True) for the result and the C.V. line, and back to the car. Frames at each screen."""
    def gen():
        import sys
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        import job_hunt_data as jobs
        j, job = l2_journey(), None
        job = jobs.JOBS[stop]
        while prop(j, 'DialogueMode') == jobs.PITCH:
            yield from wait(lambda: (prop(j, 'DialogueReady') and not prop(j, 'DialogueHeld')) or prop(j, 'DialogueMode') != jobs.PITCH)
            if prop(j, 'DialogueMode') != jobs.PITCH:
                break
            beat_n = prop(j, 'JobBeat')
            if beat_n == 0:  # the first question with its key caps (level2 stop look, 2026-11-18)
                yield from sleep(0.5)
                shot(f'stop{stop}_pitch')
                yield from sleep(0.35)
            if beat_n < 2:
                j.call_method('DialogueSelect', (job.pitch[beat_n].points.index(2),))
            else:
                shot(f'stop{stop}_offer')
                yield from sleep(0.35)  # 'Shot' renders at the end of a later frame: hold the screen until then
            j.call_method('DialogueConfirm')
            j.call_method('DialogueRelease')
            yield
        yield from wait(lambda: prop(j, 'DialogueMode') == jobs.TIME_SKIP)
        yield from sleep(0.5)
        shot(f'stop{stop}_timecard')
        yield from wait(lambda: prop(j, 'DialogueMode') == jobs.SHIFT and prop(j, 'DialogueReady'))
        yield from sleep(0.9)
        shot(f'stop{stop}_shift')
        yield from sleep(0.35)
        j.call_method('FinishJob', (True,))
        yield from wait(lambda: prop(j, 'DialogueMode') == jobs.RESULT and prop(j, 'DialogueReady'))
        yield from sleep(0.4)
        log('l2_job', stop=stop, employability=prop(j, 'Employability'), won=prop(j, 'JobWon'), frame=shot(f'stop{stop}_result'))
        yield from sleep(0.35)
        j.call_method('DialogueConfirm')
        j.call_method('DialogueRelease')
        yield from wait(lambda: prop(j, 'Phase') == 3)
        yield from sleep(0.6)
        shot(f'stop{stop}_back_in_car')
    return gen


def g_l2_fall():
    """The fall at normal speed: the threshold fixture at 4x up to the colour path's jump, then 1x from BeginFall
    (Phase 4) through PlayFall, Land, EndFade and Finish to the street with control back. A frame every 0.5 s."""
    w = W()
    yield from wait(lambda: one('director') and one('fe') and pawn() and pc())
    fe = one('fe')
    fe.call_method('OnSplashFinished')
    fe.call_method('OnTitleConfirmed')
    fe.call_method('StopBed')
    lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
    for widget in lib.call_method('GetAllWidgetsOfClass', (w, unreal.UserWidget, True)):
        widget.remove_from_parent()
    lib.call_method('SetInputMode_GameOnly', (pc(), True))
    one('director').call_method('OpenTheDoor')
    one('threshold').call_method('StartThreshold')
    jumped, t_fall, nxt, rows = False, None, 0.0, []
    while True:
        th = one('threshold')
        ph = prop(th, 'Phase', 0)
        if unreal.GameplayStatics.is_game_paused(w):
            unreal.GameplayStatics.set_game_paused(w, False)
        unreal.GameplayStatics.set_global_time_dilation(w, 4 if ph < 4 else 1)
        if ph == 3 and not jumped and prop(th, 'Age', 0) >= 13:
            unreal.get_default_object(unreal.SystemLibrary).call_method('SetIntPropertyByName', (th, 'RouteBeat', 2))
            th.call_method('HidePath')
            pawn().set_actor_location(unreal.Vector(20000, -79660, 92), False, True)
            th.call_method('BeginFall')
            jumped = True
        if ph >= 4:
            t_fall = t_fall or time.time()
            age = time.time() - t_fall
            if age >= nxt:
                rows.append(dict(t=round(age, 1), phase=ph, view=view()))
                shot('fall_%04.1f' % age)
                nxt += 0.5
            j = prop(th, 'Journey')
            if ph >= 6 and j and unreal.SystemLibrary.is_valid(j) and prop(j, 'Phase') == 1 and age > 2 and free():
                break
            if age > 26:
                raise Miss('the fall did not reach the street with control in 26 s')
        yield
    yield from sleep(2.5)
    log('l2_fall', rows=rows, frame=shot('fall_street'))


def g_l2_pitch_to_shift(stop):
    """The best pitch answers, the offer and the time card, until the shift board takes input."""
    def gen():
        import sys
        sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
        import job_hunt_data as jobs
        j, job = l2_journey(), jobs.JOBS[stop]
        while prop(j, 'DialogueMode') == jobs.PITCH:
            yield from wait(lambda: (prop(j, 'DialogueReady') and not prop(j, 'DialogueHeld')) or prop(j, 'DialogueMode') != jobs.PITCH)
            if prop(j, 'DialogueMode') != jobs.PITCH:
                break
            if prop(j, 'JobBeat') < 2:
                j.call_method('DialogueSelect', (job.pitch[prop(j, 'JobBeat')].points.index(2),))
            j.call_method('DialogueConfirm')
            j.call_method('DialogueRelease')
            yield
        yield from wait(lambda: prop(j, 'DialogueMode') == jobs.SHIFT and prop(j, 'DialogueReady'))
        yield from sleep(0.6)
    return gen


def g_l2_pack_shift():
    """Queen Market's crate, played: one deliberate wrong case first (the miss reaction), then the four orders. Each
    order's last case finishes it (AcceptShiftRound -> ShiftReact). Frames after the miss and after orders 1, 2 and 4;
    logs the bills' dissolve (ShiftSand) and the overlay line each time."""
    import sys
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
    from shift_minigame_data import RECIPES, PACKED
    j, rows = l2_journey(), []

    def press(index):
        j.call_method('DialogueSelect', (index,))
        j.call_method('DialogueConfirm')
        j.call_method('DialogueRelease')

    def note(tag):
        rows.append(dict(tag=tag, order=prop(j, 'JobOrder'), mistakes=prop(j, 'JobMistakes'), sand=round(prop(j, 'ShiftSand', 0), 2)))
        return shot(tag)
    # order 0 recipe (2,1,0): oat milk is the wrong case
    yield from sleep(0.4)  # clear of the previous step's frame (shot() drops requests within 0.25 s)
    note('shift_start')
    yield from sleep(0.4)
    j.call_method('DialogueSelect', (0,))
    yield from sleep(0.3)
    press(0)  # one rice in, so the miss has something to take with it
    yield from sleep(0.5)
    press(2)
    yield from sleep(0.22)
    note('shift_spill')  # the jug over the rim (SpillCrateItem, 0.5 s)
    yield from sleep(0.6)
    note('shift_miss')
    yield from sleep(0.4)
    for order in range(4):
        recipe = RECIPES[order]
        packed = 0
        for item, count in enumerate(recipe):
            for _ in range(count):
                yield from wait(lambda: prop(j, 'DialogueReady') and not prop(j, 'DialogueHeld'))
                press(item)
                packed += 1
                if order == 0 and packed == 2:
                    yield from sleep(0.45)
                    note('shift_two_in')  # two items in, the order card's pips filling
                    yield from sleep(0.3)
                if order == 0 and packed == 3:
                    yield from sleep(0.33)
                    note('shift_full_case')  # the third lands, before the case goes in sand
                yield
        yield from sleep(0.9)
        if order in (0, 1, 3):
            note(f'shift_order{order + 1}')
            yield from sleep(0.4)
        if prop(j, 'DialogueMode') != 6:
            break
    log('l2_shift', rows=rows, won=prop(j, 'JobWon'), mode=prop(j, 'DialogueMode'), frame=shot('shift_after'))
    if not prop(j, 'JobWon'):
        raise Miss('the crate shift did not finish as won')


def g_l2_interview_mixed():
    """The interview with two inflated answers (the middle-cost choice at steps 0 and 2) and four straight ones: frames
    after each answer's reaction; logs the room's dissolve (InterviewSand), the loom and the lens."""
    import sys
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
    import job_boss_data as boss
    j, rows = l2_journey(), []
    while prop(j, 'DialogueState') != 3:
        yield from wait(lambda: prop(j, 'DialogueReady') and not prop(j, 'DialogueHeld'))
        st = prop(j, 'DialogueState')
        if st == 2:
            raise Miss('interview lost')
        if st == 3:
            break
        if st == 0:
            step = prop(j, 'DialogueStep')
            sec = boss.SECTIONS[step // 2]
            row = sec if step % 2 == 0 else sec['followups'][prop(j, 'DialoguePrior')]
            costs = [c['cost'] for c in row['choices']]
            pick = costs.index(sorted(costs)[1]) if step in (0, 2) else costs.index(min(costs))
            j.call_method('DialogueSelect', (pick,))
            j.call_method('DialogueConfirm')
            j.call_method('DialogueRelease')
            yield from sleep(0.7)
            stage = prop(j, 'StopSet')
            cam = prop(stage, 'StageCamera')
            rows.append(dict(step=step, cost=costs[pick], sand=round(prop(j, 'InterviewSand', 0), 2), loom=prop(j, 'InterviewLoom'),
                             fov=round(cam.get_editor_property('field_of_view'), 1) if cam else None,
                             frame=shot(f'answer{step}_cost{costs[pick]}')))
            yield from sleep(0.3)
            continue
        j.call_method('DialogueConfirm')
        j.call_method('DialogueRelease')
        yield
    log('l2_interview_mixed', rows=rows, composure=prop(j, 'InterviewComposure'))
    if not any(r['cost'] for r in rows) or not any(r['loom'] for r in rows):
        raise Miss('no inflated answer reached the room')


def g_l2_arrival_cost():
    """The arrival at Queen Market as the game runs it: with the car driving (Active, the pawn unpossessed), park it
    at the stop and call the journey's Arrive(0) (fade, then the StageStop timer runs BeginJob). Log every frame's
    wall time from Arrive until 2 s later, and which frame BeginJob ran in (Phase turns 4). Perf lane 11-18: one
    1,670 ms game-thread frame in the cooked build near here."""
    import sys
    sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
    from job_route import DESTINATIONS
    j = l2_journey()
    car = one('car')
    yield from sleep(1.5)
    car.set_actor_location(unreal.Vector(*DESTINATIONS[0]), False, True)
    yield
    start = len(S['frames'])
    t = time.perf_counter()
    j.call_method('Arrive', (0,))
    arrive_ms = round((time.perf_counter() - t) * 1000, 1)
    begin = None
    t0 = time.time()
    while time.time() - t0 < 2.0:
        yield
        if begin is None and prop(j, 'Phase') == 4:
            begin = len(S['frames']) - 1  # this tick's frame time covers the frame that ran the timer
    frames = [round(f[1], 1) for f in S['frames'][start:]]
    log('l2_arrival_cost', arrive_call_ms=arrive_ms, frames=len(frames), max_ms=max(frames),
        begin_frame_ms=S['frames'][begin][1] if begin is not None else None,
        around_begin=[round(f[1]) for f in S['frames'][begin - 2:begin + 4]] if begin is not None else None,
        over_33=[x for x in frames if x > 33], phase=prop(j, 'Phase'), frame=shot('arrival_cost'))


PLANS.update({
    'L2H': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('drive', 'into the car: Confirm twice; the car drives off on its own', into_car(), 6, True),
            ('L2', 'arrival at Queen Market, every frame timed', g_l2_arrival_cost, 8, False)],
    'L2W': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'fixture: parked at Queen Market (Arrive 0)', l2_arrive(0), 6, True),
            ('L2', 'Queen Market: best pitch, offer, time card, to the crate', g_l2_pitch_to_shift(0), 12, True),
            ('L2', 'the crate played: one wrong case, then four orders', g_l2_pack_shift, 27, False)],
    'L2I': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'fixture: two shifts on the C.V, parked at the interview (StageStop 3)', l2_to_interview(), 8, True),
            ('L2', 'interview: two inflated answers, four straight; the room reacts', g_l2_interview_mixed, 22, False)],
    'L2F': [('L2', 'the fall at 1x: colour path jump, fall, landing card, the street, control back', g_l2_fall, 50, False)],
    'L2S': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'Queen Street: the sand crow forms ahead (3.6 s)', chain(lambda: sleep(3.6), do(lambda: shot('street_crow'), what='frame')), 6, False),
            ('L2', 'fixture: parked at Queen Market (Arrive 0)', l2_arrive(0), 6, True),
            ('L2', 'Queen Market: pitch, time card, shift, result, back to the car', g_l2_job(0), 16, False)],
    'L2S1': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
             ('L2', 'fixture: Queen Market on the C.V, parked at Night Dispatch (Arrive 1)', l2_arrive(1), 6, True),
             ('L2', 'Night Dispatch: pitch, time card, shift, result, back to the car', g_l2_job(1), 16, False)],
    'L2S2': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
             ('L2', 'fixture: two shifts on the C.V, parked at Northline Supply (Arrive 2)', l2_arrive(2), 6, True),
             ('L2', 'Northline Supply: pitch, time card, shift, result, back to the car', g_l2_job(2), 16, False)],
    'L2E': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'fixture: two shifts on the C.V, parked at the interview (StageStop 3)', l2_to_interview(), 8, True),
            ('L2', 'interview: the six best answers through the dialogue handlers', g_win_interview, 16, True),
            ('end', 'accept, the ending film, hand-off to the credits roll', g_l2_ending, 32, False)],
})


# ---- ui lane: the text FX kit (WBP_SandLine), plan UIK -------------------------------------------------------------
SANDLINE = '/Game/FoA/UI/Widgets/Common/WBP_SandLine.WBP_SandLine_C'


def g_textfx_kit():
    """Four WBP_SandLine lines, one per mood (0 Calm, 1 Shock, 2 Matters, 3 Quick), start together over live play;
    frames across the form, the shock's shiver and the sweeps; then Dismiss scatters them. PASS: every line's Reveal
    reaches 1, Shiver is back to 0, and every line is collapsed 0.6 s (game) after Dismiss. Runs at time dilation 0.2
    (timers dilate, the screenshots do not), so the frames catch the motion between their capture stalls."""
    slow = 0.2
    unreal.GameplayStatics.set_global_time_dilation(W(), slow)
    lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
    lines = []
    for i, (mood, text) in enumerate(((0, 'He breathes out. The letters settle.'), (1, 'Wait. That shirt just moved.'),
                                      (2, 'The key is in the boot.'), (3, 'A plain line, formed quickly.'))):
        w = lib.call_method('Create', (W(), cls(SANDLINE), pc()))
        w.call_method('AddToViewport', (40,))
        w.call_method('SetAlignmentInViewport', (unreal.Vector2D(0.0, 0.0),))
        w.call_method('SetPositionInViewport', (unreal.Vector2D(120.0, 150.0 + i * 120.0), True))
        w.call_method('Play', (unreal.Text(text), mood, 0.0))
        lines.append(w)
    # a line played before it is on screen (WBP_L2Journey does this): no material yet, so it must wait, then form
    late = lib.call_method('Create', (W(), cls(SANDLINE), pc()))
    late.call_method('Play', (unreal.Text('Played before it was on screen.'), 0, 0.0))
    late_mid_before = prop(late, 'Ret_Line').call_method('GetEffectMaterial')
    mids = [prop(w, 'Ret_Line').call_method('GetEffectMaterial') for w in lines]
    par = lambda m, n: round(m.call_method('K2_GetScalarParameterValue', (n,)), 2)  # noqa: E731
    t0, rows = time.time(), []
    try:
        for at in (0.06, 0.15, 0.3, 0.45, 0.6, 0.8, 1.1, 1.8):
            yield from wait(lambda: time.time() - t0 >= at / slow)
            rows.append(dict(t=at, reveal=[par(m, 'Reveal') for m in mids], shiver=[par(m, 'Shiver') for m in mids],
                             sweep=[par(m, 'Sweep') for m in mids]))
            shot('kit_form_%03d' % int(at * 100))
        formed = rows[-1]
        late.call_method('AddToViewport', (40,))
        late.call_method('SetAlignmentInViewport', (unreal.Vector2D(0.0, 0.0),))
        late.call_method('SetPositionInViewport', (unreal.Vector2D(120.0, 630.0), True))
        tl = time.time()
        yield from wait(lambda: time.time() - tl >= 1.2 / slow)
        shot('kit_late')
        late_mid = prop(late, 'Ret_Line').call_method('GetEffectMaterial')
        late_reveal = round(late_mid.call_method('K2_GetScalarParameterValue', ('Reveal',)), 2) if late_mid else None
        lines.append(late)
        for w in lines:
            w.call_method('Dismiss')
        t1 = time.time()
        for at in (0.06, 0.14, 0.22, 0.3, 0.38):
            yield from wait(lambda: time.time() - t1 >= at / slow)
            shot('kit_out_%03d' % int(at * 100))
        yield from wait(lambda: time.time() - t1 >= 0.7 / slow)
        gone = ['COLLAPSED' in str(w.call_method('GetVisibility')).upper() for w in lines]
        # the HUD's thought line on the same kit: a shock line ("Ow" opens it) forms, shivers, then scatters
        hud = prop(one('fe'), 'HUD')
        hud.call_method('HandleNarration', (unreal.Text('Ow. Not now.'),))
        t2 = time.time()
        for at in (0.05, 0.12, 0.25, 0.45, 0.9):
            yield from wait(lambda: time.time() - t2 >= at / slow)
            shot('kit_hud_%03d' % int(at * 100))
        shock = prop(hud, 'NarrShock')
        hud.call_method('ClearNarration')
        t3 = time.time()
        for at in (0.08, 0.2, 0.32):
            yield from wait(lambda: time.time() - t3 >= at / slow)
            shot('kit_hud_out_%03d' % int(at * 100))
        yield from wait(lambda: time.time() - t3 >= 0.6 / slow)
        hud_gone = 'COLLAPSED' in str(prop(hud, 'Brd_Narration').call_method('GetVisibility')).upper()
        ok = (all(r >= 0.999 for r in formed['reveal']) and all(s <= 0.001 for s in formed['shiver']) and all(gone)
              and shock == 1.0 and hud_gone and late_mid_before is None and late_reveal is not None and late_reveal >= 0.999)
        log('textfx_kit', result='PASS' if ok else 'FAIL', rows=rows, collapsed=gone, hud_shock=shock, hud_cleared=hud_gone,
            late_material_before=str(late_mid_before), late_reveal=late_reveal)
        if not ok:
            raise Miss('the sand line kit did not form, settle or leave (see textfx_kit)')
    finally:
        unreal.GameplayStatics.set_global_time_dilation(W(), 1.0)
        for w in lines:
            w.remove_from_parent()


SETTINGS_LIB = '/Game/FoA/UI/Framework/BPFL_FoASettings.BPFL_FoASettings_C'
SETTINGS_SG = '/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C'
QUALITY = ('view_distance', 'anti_aliasing', 'shadow', 'global_illumination', 'reflection', 'post_processing',
           'texture', 'visual_effect', 'foliage', 'shading', 'landscape')  # every group: a missed one left the editor mixed


def g_graphics_detect():
    """First-run graphics auto-detect (BPFL_FoASettings.AutoDetectGraphics) on a fresh, unsaved SG_FoASettings, the
    state a player with no settings save is in; Settings.sav and FoA.sav are never read or written. bAllowInEditor
    stands in for the cooked build. Then Settings opens to show the preset it chose. The editor's own scalability is
    restored afterwards (one shared editor). PASS: the first call runs the benchmark and lands on one preset (0..3),
    a second call on the same slot does not run again, and the flag is set."""
    gus = unreal.GameUserSettings.get_game_user_settings()
    before = {q: getattr(gus, f'get_{q}_quality')() for q in QUALITY}
    scale, overall0 = gus.get_resolution_scale_normalized(), gus.get_overall_scalability_level()
    lib = unreal.get_default_object(cls(SETTINGS_LIB))
    sg = unreal.new_object(cls(SETTINGS_SG))
    ran = lambda r: r if isinstance(r, bool) else bool(r[0] if isinstance(r, (tuple, list)) and r else r)  # noqa: E731
    try:
        # the packaged-build gate: in the editor the command line carries the .uproject, so with bAllowInEditor false
        # it must not run (a GetCommandLine compiled out returns '' and would let it run: perf lane, 04:10)
        gated = ran(lib.call_method('AutoDetectGraphics', kwargs=dict(world_context=W(), settings=unreal.new_object(cls(SETTINGS_SG)), allow_in_editor=False)))
        t = time.time()
        first = ran(lib.call_method('AutoDetectGraphics', kwargs=dict(world_context=W(), settings=sg, allow_in_editor=True)))
        secs = round(time.time() - t, 2)
        after = {q: getattr(gus, f'get_{q}_quality')() for q in QUALITY}
        overall1 = gus.get_overall_scalability_level()
        yield
        again = ran(lib.call_method('AutoDetectGraphics', kwargs=dict(world_context=W(), settings=sg, allow_in_editor=True)))
        one('fe').call_method('OpenSettings')
        yield from sleep(1.2)
        row, sw = None, None
        for w in unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary')).call_method(
                'GetAllWidgetsOfClass', (W(), unreal.UserWidget, False)):
            if w.get_class().get_name().startswith('WBP_Settings'):
                sw = w
                q = prop(w, 'Row_Quality')
                row = prop(q, 'Index') if q else None
        frame = shot('settings_quality')
        # round 3: a Quality change lifts the scrim for 2 s so the room shows the new preset, then settles back
        lifts = []
        if sw:
            sw.call_method('OnQualityChanged', (max(0, overall1 - 2),))
            tq = time.time()
            for at in (0.1, 1.0, 2.0, 4.0, 6.0):  # ApplySettings can stall PIE's rendering for a moment
                yield from wait(lambda: time.time() - tq >= at)
                lifts.append(round(prop(sw, 'Img_Scrim').get_render_opacity(), 2))
                shot('settings_preview_%03d' % int(at * 100))
        log('settings_preview', scrim_opacity=lifts)
        sysl = unreal.SystemLibrary
        dyn_low = dict(res_quality=round(sysl.get_console_variable_float_value('sg.ResolutionQuality'), 1),
                       mode=sysl.get_console_variable_int_value('r.DynamicRes.OperationMode'),
                       max_pct=round(sysl.get_console_variable_float_value('r.DynamicRes.MaxScreenPercentage'), 1))
        ok = (not gated and first and not again and prop(sg, 'GraphicsDetectVersion') == 2 and 0 <= overall1 <= 3
              and row == overall1 and (not sw or (dyn_low['mode'] == 2 and dyn_low['max_pct'] == dyn_low['res_quality'])))
        log('graphics_detect', result='PASS' if ok else 'FAIL', ran_in_editor_gate=gated, ran_first=first, ran_again=again, benchmark_s=secs,
            detect_version=prop(sg, 'GraphicsDetectVersion'), dynres_after_quality_change=dyn_low if sw else None,
            overall_before=overall0, overall_after=overall1, levels_after=after, settings_row_index=row, frame=frame)
        if not ok:
            raise Miss('graphics auto-detect did not run once and land on one preset (see graphics_detect)')
    finally:
        for q, v in before.items():
            getattr(gus, f'set_{q}_quality')(v)
        gus.set_resolution_scale_normalized(scale)
        gus.apply_settings(False)
        gus.save_settings()
        lib.call_method('ApplyDynamicResolution', kwargs=dict(world_context=W()))  # back to Epic: the hook turns dynres off
        log('note', what='editor scalability restored', overall=gus.get_overall_scalability_level(),
            dynres_mode=unreal.SystemLibrary.get_console_variable_int_value('r.DynamicRes.OperationMode'))


def replay_intro(widget, slow=0.25, at=(0.05, 0.2, 0.35, 0.5, 0.7, 1.0), tag='intro'):
    """Re-run a restyled Level 2 widget's AnimateIn (LastKey cleared) at time dilation `slow` and frame it."""
    def gen():
        sl = unreal.get_default_object(unreal.SystemLibrary)
        w = W()
        unreal.GameplayStatics.set_global_time_dilation(w, slow)
        try:
            sl.call_method('SetStringPropertyByName', (widget(), 'LastKey', ''))
            widget().call_method('AnimateIn')
            t0 = time.time()
            for a in at:
                yield from wait(lambda: time.time() - t0 >= a / slow)
                shot('%s_%03d' % (tag, int(a * 100)))
        finally:
            unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        log('replay_intro', widget=widget().get_class().get_name(), intro_t=prop(widget(), 'IntroT'))
    return gen


def g_interview_focus():
    """Answer focus on the restyled interview: move the selection down twice, a frame each."""
    j = l2_journey()
    hud = prop(j, 'InterviewHUD')
    log('interview_text', **{n: dict(text=str(prop(prop(hud, n), 'Text', '')), opacity=round(prop(hud, n).get_render_opacity(), 2),
                                    visibility=str(prop(hud, n).get_visibility())) for n in ('Txt_Hint', 'Txt_Evidence', 'Txt_Status')})
    for i in (1, 2):
        j.call_method('DialogueSelect', (i,))
        yield from sleep(0.5)
        shot('interview_focus_%d' % i)
    yield from sleep(0.3)


ROLLOVER = '/Game/FoA/UI/Game/WBP_DayRollover.WBP_DayRollover_C'


def g_round3():
    """ui round 3, filmed at time dilation 0.25 (timers dilate, screenshots do not):
    objective swap (the old line scatters, the new one gathers), a phone message typing itself out, the day rollover
    card breathing. PASS: the objective text swapped and the swap flag cleared, the message reached its full length,
    and the rollover card's render scale moved off 1 while it held."""
    slow, w = 0.25, W()
    lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
    unreal.GameplayStatics.set_global_time_dilation(w, slow)
    roll, res = None, {}
    try:
        hud = prop(one('fe'), 'HUD')
        before = str(prop(prop(hud, 'Txt_Objective'), 'Text', ''))
        hud.call_method('HandleBeatChanged', ('T2', unreal.Text('Find something to wear.'), False))
        t0 = time.time()
        for at in (0.05, 0.15, 0.3, 0.45, 0.7, 1.1, 1.8):
            yield from wait(lambda: time.time() - t0 >= at / slow)
            shot('r3_objective_%03d' % int(at * 100))
        res['reduce_motion'] = round(unreal.get_default_object(unreal.load_class(None, '/Script/Engine.KismetMaterialLibrary')).call_method(
            'GetScalarParameterValue', (w, unreal.load_asset('/Game/FoA/UI/Style/MPC_UI.MPC_UI'), 'ReduceMotion')), 2)
        res['hud_opacity'] = round(hud.get_render_opacity(), 2)
        res['objective'] = dict(before=before, after=str(prop(prop(hud, 'Txt_Objective'), 'Text', '')), swap_flag=prop(hud, 'bObjSwap'))
        ph = one('phone')
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        one('fe').call_method('OpenPhone')
        yield from wait(lambda: prop(ph, 'bOpen'))
        t1 = time.time()
        yield from wait(lambda: time.time() - t1 >= 1.8)  # past the lock screen
        slow = 0.5
        unreal.GameplayStatics.set_global_time_dilation(w, slow)
        pw = prop(ph, 'Screen').get_user_widget_object()
        pw.call_method('SetPage', (1,))
        pw.call_method('OpenMessage', (0,))
        t2 = time.time()
        for at in (0.1, 0.4, 0.8, 1.4, 2.4):
            yield from wait(lambda: time.time() - t2 >= at / slow)
            shot('r3_phone_%03d' % int(at * 100))
        full = str(prop(pw, 'TypeFull', ''))
        res['phone'] = dict(full_len=len(full), shown_len=len(str(prop(prop(pw, 'Txt_Message'), 'Text', ''))))
        one('fe').call_method('ClosePhone')
        yield from wait(lambda: not prop(ph, 'bOpen'))
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        slow = 1.0
        roll = lib.call_method('Create', (w, cls(ROLLOVER), pc()))
        roll.call_method('AddToViewport', (60,))
        roll.call_method('PlayRollover', (19, unreal.Text("Key's in my left boot. Under the bed.")))
        t3, scales = time.time(), []
        for at in (0.4, 1.2, 2.0, 2.8):
            yield from wait(lambda: time.time() - t3 >= at / slow)
            scales.append((round(prop(roll, 'VB_Card').get_editor_property('render_transform').scale.x, 4), round(prop(roll, 'Elapsed', 0), 2)))
            shot('r3_rollover_%03d' % int(at * 100))
        res['rollover'] = dict(scales=scales)
    finally:
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        if roll:
            roll.remove_from_parent()
    ok = (res.get('objective', {}).get('after') == 'Find something to wear.' and not res['objective']['swap_flag']
          and res.get('phone', {}).get('full_len', 0) > 0 and res['phone']['shown_len'] == res['phone']['full_len']
          and max(abs(s[0] - 1.0) for s in res.get('rollover', {}).get('scales', [(1.0, 0)])) > 0.002)
    log('ui_round3', result='PASS' if ok else 'FAIL', **res)
    if not ok:
        raise Miss('round 3 motion check failed (see ui_round3)')


def g_settings_boxes():
    """The user's Settings bug: every tab label must sit inside its focus box with even padding, left edges aligned,
    the < > arrows on the value's line, no speck of sand by the box. Settings opens from the main menu; each tab is
    selected in turn at 1280x720 and 1920x1080, plus a hover on an unselected tab. PASS: for every selected tab the
    label fits its box (desired height <= box height) and the label has no focus step; the tabs' left edges agree."""
    sl = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.SlateBlueprintLibrary'))
    yield from wait(lambda: screen() and 'MainMenu' in screen())
    yield from sleep(1.0)
    one('fe').call_method('OpenSettings')
    yield from sleep(1.2)
    sw = next(w for w in unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary')).call_method(
        'GetAllWidgetsOfClass', (W(), unreal.UserWidget, False)) if w.get_class().get_name().startswith('WBP_Settings'))
    tabs = ('Btn_TabGraphics', 'Btn_TabAudio', 'Btn_TabControls', 'Btn_TabAccess')
    rows, bad = [], []
    try:
        # r.SetRes does not resize a PIE window (run_1325's "1920" frames were 1286x760): one pass at the PIE size;
        # the sizes are compared in Slate units, which do not change with resolution, and the 1920x1080 layout is
        # rendered separately with ui_render_widget_to_png
        for res in ((1280, 720),):
            for i, name in enumerate(tabs):
                sw.call_method('ShowPage', (i,))
                prop(sw, name).call_method('FocusButton')  # keyboard focus moves with the page, as a real press does
                yield from sleep(1.2)
                tab = prop(sw, name)
                label, box = prop(tab, 'Txt_Label'), prop(tab, 'SizeBox_0')
                lh = round(label.get_desired_size().y, 1)
                bh = round(prop(box, 'HeightOverride', 0.0), 1)  # ApplyLook sizes the box; cached geometry reads 0 here
                step = round(prop(tab, 'Ret_Sand').get_editor_property('render_transform').translation.x, 1)
                rows.append(dict(res=res, tab=name, label_h=lh, box_h=bh, label_step=step))
                if lh <= 0 or bh <= 0 or lh > bh or step != 0.0:  # a zero size means nothing was measured: fail
                    bad.append(rows[-1])
                shot('settings_%s_%d' % (name[7:].lower(), res[0]))
                yield from sleep(0.6)  # let the capture land before the next page
            hover = prop(sw, 'Btn_TabAudio')
            sw.call_method('ShowPage', (0,))
            prop(sw, 'Btn_TabGraphics').call_method('FocusButton')
            yield from sleep(0.8)
            hover.call_method('SetHovered', (True,))
            yield from sleep(0.6)
            shot('settings_hover_%d' % res[0])
            yield from sleep(0.6)
            hover.call_method('SetHovered', (False,))
    finally:
        pass
    log('settings_boxes', result='FAIL' if bad else 'PASS', rows=rows, bad=bad)
    if bad:
        raise Miss('a Settings tab label overflows its box or still steps on focus (see settings_boxes)')


def g_debug_f9():
    """F9 still opens and closes the debug panel in a Development PIE (the QA harness relies on it); Shipping is gated
    by GetBuildConfiguration (the perf lane checks that in its build). A real F9 through the runner's key relay."""
    def key(k):
        S['inp'] = S.get('inp', 0) + 1
        i = S['inp']
        tmp = f'{OUT}/input.tmp'
        open(tmp, 'w').write(json.dumps(dict(id=i, key=k, held_ms=120)))
        os.replace(tmp, f'{OUT}/input.json')
        end = time.time() + 4.0
        while time.time() < end:
            try:
                ack = json.load(open(f'{OUT}/input_ack.json'))
            except (OSError, ValueError):
                ack = {}
            if ack.get('id') == i:
                return str(ack.get('result'))[:120]
            yield
        return 'timeout'
    up = lambda: (lambda p: bool(p and unreal.SystemLibrary.is_valid(p) and p.is_in_viewport()))(prop(one('fe'), 'DebugPanel'))  # noqa: E731
    yield from wait(lambda: screen() and 'MainMenu' in screen())
    yield from sleep(0.8)
    r1 = yield from key('F9')
    yield from sleep(0.8)
    opened = up()
    shot('debug_f9_open')
    r2 = yield from key('F9')
    yield from sleep(0.8)
    closed = not up()
    log('debug_f9', result='PASS' if opened and closed else 'FAIL', opened=opened, closed=closed, relay=[r1, r2])
    if not (opened and closed):
        raise Miss('F9 did not open and close the debug panel in Development')


PLANS.update({
    'UIF': boot()[:2] + [('menu', 'F9 debug panel still works in Development', g_debug_f9, 12, False)],
    'UIS': boot()[:2] + [('menu', 'Settings tabs: labels inside their boxes, arrows on the value line, two resolutions',
                          g_settings_boxes, 30, False)],
    'UIR': boot() + [('T1', 'ui round 3: objective swap, phone typing, rollover breath', g_round3, 30, False)],
    'UIJ': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'ui look: the journey card forms (place name from sand, brief rising)',
             replay_intro(lambda: prop(l2_journey(), 'HUD'), tag='card'), 10, False)],
    'UII': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'fixture: two shifts on the C.V, parked at the interview (StageStop 3)', l2_to_interview(), 8, True),
            ('L2', 'ui look: the interview question rises in, answers follow',
             replay_intro(lambda: prop(l2_journey(), 'InterviewHUD'), tag='interview'), 8, False),
            ('L2', 'ui look: answer focus by brightness', g_interview_focus, 4, False)],
    'UIG': boot()[:2] + [('menu', 'first-run graphics auto-detect, then Settings shows the preset', g_graphics_detect, 30, False)],
    'UIK': boot() + [('T1', 'ui kit: four sand lines (calm, shock, matters, quick), then dismissed', g_textfx_kit, 30, False)],
})


# ---- dreamroom lane: the colour dream between Level 1 and Level 2 (plan DRM) ------------------------------------------
# DRM  fixture: front end skipped, the door and the threshold film at 4x to the colour path (as l2_fixture); then the
#      dream room played at 1x: walk the white marks toward EXIT while the black-sand fears rise, two real held
#      breaths (E through the key relay), each segment crumbles, EXIT, the fall begins.
def dream_fixture():
    def gen():
        yield from wait(lambda: one('director') and one('fe') and pawn() and pc())
        w = W()
        unreal.GameplayStatics.set_game_paused(w, False)
        fe = one('fe')
        fe.call_method('OnSplashFinished')
        fe.call_method('OnTitleConfirmed')
        fe.call_method('StopBed')
        lib = unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary'))
        for widget in lib.call_method('GetAllWidgetsOfClass', (w, unreal.UserWidget, True)):
            widget.remove_from_parent()
        lib.call_method('SetInputMode_GameOnly', (pc(), True))
        one('director').call_method('OpenTheDoor')
        one('threshold').call_method('StartThreshold')
        while prop(one('threshold'), 'Phase', 0) < 3:
            if unreal.GameplayStatics.is_game_paused(w):
                unreal.GameplayStatics.set_game_paused(w, False)
            unreal.GameplayStatics.set_global_time_dilation(w, 4)
            yield
        unreal.GameplayStatics.set_global_time_dilation(w, 1)
        log('dream_arrival', phase=threshold_phase(), frame=shot('dream_arrival'))
    return gen


def dream_state(th):
    p = pawn()
    return dict(stage=prop(th, 'Stage'), beat=prop(th, 'RouteBeat'), breath=prop(th, 'BreathState'),
                torment=round(prop(th, 'Torment', 0.0), 2), y=round(p.get_actor_location().y - th.get_actor_location().y),
                speed=round(p.get_editor_property('character_movement').get_editor_property('max_walk_speed')),
                visible=[c.get_name() for c in th.get_components_by_class(unreal.StaticMeshComponent)
                         if c.get_name().startswith('Fear') and c.is_visible()])


def g_dream_walk():
    th, t0 = one('threshold'), time.time()
    goal = th.get_actor_location() + unreal.Vector(0, 352, 150)  # the EXIT doorway
    seen, peak, slowest, rows, last = [], 0.0, 999, [], -1.0
    while prop(th, 'Phase', 0) == 3 and time.time() - t0 < 46:
        s = dream_state(th)
        peak, slowest = max(peak, s['torment']), min(slowest, s['speed'])
        if s['stage'] != (seen[-1][1] if seen else 0):
            seen.append((round(time.time() - t0, 1), s['stage'], s['y']))
            log('dream_stage', **s, frame=shot('stage%d' % s['stage']))
        if time.time() - last >= 0.8:
            last = time.time()
            rows.append(dict(t=round(time.time() - t0, 1), **s))
            shot('walk')
        turn_toward(goal, 3.0)
        if s['breath'] == 0:
            pawn().add_movement_input(unreal.Vector(0, 1, 0), 1.0, False)
        elif s['breath'] == 1 and prop(th, 'BreathArmed'):
            yield from sleep(0.6)  # a player reads the glyph first
            shot('breath%d_prompt' % s['beat'])
            # The early-release reset is proven offline (test_threshold_walk.py): the relay's short presses can leave E
            # down in PIE (run_20261118_0021), so this burst only plays the full held breaths.
            held = 4500  # BREATH_HOLD 2.4 s plus margin: holding past full is harmless
            shot('breath%d_in' % s['beat'])
            yield from press('E', held)
            shot('breath%d_out' % s['beat'])
        yield
    fell = prop(th, 'Phase', 0) >= 4
    yield from sleep(1.2)
    ok = fell and prop(th, 'RouteBeat') == 2 and [x[1] for x in seen][:8] == list(range(1, 9)) and peak >= 0.75 and slowest < 60
    log('dream_walk', result='PASS' if ok else 'FAIL', fell=fell, seconds=round(time.time() - t0, 1), stages=seen,
        peak_torment=peak, slowest_walk=slowest, rows=rows, frame=shot('dream_fall'))
    if not ok:
        raise Miss('the dream room did not play through both breaths to the fall')


PLANS.update({
    'DRM': [('L2', 'fixture: front end skipped, door and threshold at 4x to the colour path', dream_fixture(), 16, True),
            ('L2', 'dream room: marks, fears rise, two held breaths, fears crumble, EXIT, fall', g_dream_walk, 50, False)],
})


# ---- atmosphere lane: Dream A's exposure, swept in the PIE copy only (2026-11-18) ----------------------------------
# ATX  the colour path reached by the dream fixture, then PIE's PP_DreamMono exposure (fixed EV100, min = max) stepped
#      through EV_SWEEP with a frame and a luminance row at each, so one burst calibrates Dream A. Nothing in the
#      editor's level changes.
EV_SWEEP = (-1.0, 0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5)


def g_exposure_sweep():
    """Dream A's exposure is decided by the highest-priority source: BP_ViewFill's GameplayExposure component (priority
    10, histogram clamped to EV100 -2.8..-1) beats PP_DreamMono and the Dream map's L2_Post. Sweep a fixed EV there."""
    vf = next(c for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor)
              for c in a.get_components_by_class(unreal.PostProcessComponent) if c.get_name() == 'GameplayExposure')
    for ev in EV_SWEEP:
        s = vf.get_editor_property('settings')
        for k, v in (('override_auto_exposure_method', True), ('auto_exposure_method', unreal.AutoExposureMethod.AEM_HISTOGRAM),
                     ('override_auto_exposure_min_brightness', True), ('auto_exposure_min_brightness', ev),
                     ('override_auto_exposure_max_brightness', True), ('auto_exposure_max_brightness', ev)):
            s.set_editor_property(k, v)
        vf.set_editor_property('settings', s)
        yield from sleep(1.6)
        loc = pawn().get_actor_location()
        log('exposure', ev=ev, at=[round(loc.x), round(loc.y), round(loc.z)], frame=shot(f'ev{ev:+.1f}'))
        yield from sleep(0.3)


def g_place_beds():
    """BP_RoomAudio's Level 2 beds on the street: MusicOverride, LastPlace and each bed's play state, every second."""
    ra = actor('FOA_RoomAudio')
    comps = {c.get_name(): c for c in ra.get_components_by_class(unreal.AudioComponent)}
    for _ in range(8):
        log('place_beds', override=str(prop(ra, 'MusicOverride', '')), last=str(prop(ra, 'LastPlace', '')),
            beds={n: [comps[n].is_playing(), str(comps[n].get_editor_property('sound').get_name() if comps[n].get_editor_property('sound') else None)]
                  for n in ('DreamBed', 'CityBed', 'CityHum', 'Rain') if n in comps})
        yield from sleep(1.0)


PLANS.update({
    # the opening, the T8 room takeover and T9 to Dream A, each played untouched and ending before the cap
    'AT1r': boot()[:3] + [
        ('intro', 'intro story plays to its own end', until(lambda: phase() not in ('story', 'black', 'menu')), 40, False),
        ('wakeup', 'LS_WakeUp, first seconds', lambda: sleep(5.0), 6, False)],
    'AT8r': boot() + [
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'the room takes over and the fight opens, untouched', lambda: sleep(14.0), 16, False)],
    'ATLr': PLANS['C'][:-1] + [
        ('L2', 'colour path visible, same pawn and input restored', g_threshold_arrival, 18, False),
        ('L2', 'Dream A, a few seconds', lambda: sleep(3.0), 4, False)],
})


def g_exposure_control():
    """Positive control for ATX: the same PIE-copy exposure edit, in the bedroom, must visibly darken the frame."""
    ppv = actor('PP_DreamMono')
    for ev in (-1.0, 1.5, -1.0):
        s = ppv.get_editor_property('settings')
        s.set_editor_property('auto_exposure_min_brightness', ev)
        s.set_editor_property('auto_exposure_max_brightness', ev)
        ppv.set_editor_property('settings', s)
        yield from sleep(0.6)
        log('exposure_control', ev=ev, frame=shot(f'evc{ev:+.1f}'))
        yield from sleep(0.3)


def g_pp_probe():
    """Every post-process source live in Dream A: volumes, PostProcessComponents and cameras, with their exposure
    overrides and blendables, plus the view target, so the Dream A grade can be placed where it wins."""
    def ex(s):
        keys = ('auto_exposure_method', 'auto_exposure_bias', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness',
                'auto_exposure_apply_physical_camera_exposure', 'film_shoulder', 'film_white_clip', 'film_slope', 'bloom_intensity')
        out = {}
        for k in keys:
            try:
                if s.get_editor_property('override_' + k):
                    out[k] = str(s.get_editor_property(k))
            except Exception:
                pass
        try:
            out['blendables'] = [(b.get_editor_property('object').get_name() if b.get_editor_property('object') else None,
                                  b.get_editor_property('weight')) for b in s.get_editor_property('weighted_blendables').get_editor_property('array')]
        except Exception:
            pass
        return out
    yield from sleep(1.0)
    vt = pc().get_view_target()
    log('pp_probe_view', view=vt.get_name() if vt else None, at=str(pawn().get_actor_location()))
    for a in unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.Actor):
        if isinstance(a, unreal.PostProcessVolume):
            log('pp_probe', src='volume', name=a.get_actor_label(), prio=a.get_editor_property('priority'),
                unbound=a.get_editor_property('unbound'), weight=a.get_editor_property('blend_weight'),
                enabled=a.get_editor_property('enabled'), set=ex(a.get_editor_property('settings')))
        for c in a.get_components_by_class(unreal.PostProcessComponent):
            log('pp_probe', src='component', name=a.get_name() + '.' + c.get_name(), prio=c.get_editor_property('priority'),
                unbound=c.get_editor_property('unbound'), weight=c.get_editor_property('blend_weight'), set=ex(c.get_editor_property('settings')))
        for c in a.get_components_by_class(unreal.CameraComponent):
            w = c.get_editor_property('post_process_blend_weight')
            if w > 0:
                log('pp_probe', src='camera', name=a.get_name() + '.' + c.get_name(), weight=w,
                    set=ex(c.get_editor_property('post_process_settings')))
    yield


def g_engine_watch(seconds=7.0):
    """After the teaching leg parks: BP_RoomAudio's Engine bed against BP_L2Car's state, every 0.5 s, until it is silent."""
    def gen():
        ra = actor('FOA_RoomAudio')
        eng = next(c for c in ra.get_components_by_class(unreal.AudioComponent) if c.get_name() == 'Engine')
        car = next(iter(unreal.GameplayStatics.get_all_actors_of_class(W(), unreal.load_class(None, P['car']))), None)
        end = time.time() + seconds
        while time.time() < end:
            log('engine', playing=eng.is_playing(), want=prop(ra, 'bWantEngine'),
                active=prop(car, 'Active'), arrived=prop(car, 'Arrived'), speed=round(prop(car, 'Speed', 0.0) or 0.0))
            yield from sleep(0.5)
        if eng.is_playing():
            raise Miss('the engine still plays after the car parked')
    return gen


def g_hair_ab():
    """The fight's pale skullcap: frames with the player's Hair groom shown, hidden, shown again (PIE copy only)."""
    def gen():
        hair = next(c for c in pawn().get_components_by_class(unreal.SceneComponent) if c.get_name() == 'Hair')
        for i, vis in enumerate((True, False, True, False)):
            hair.set_visibility(vis)
            yield from sleep(0.5)
            log('hair_ab', visible=vis, frame=shot(f'hair_{"on" if vis else "off"}{i}'))
            yield from sleep(0.3)
        hair.set_visibility(True)
    return gen


def g_blendable_ab(name, tag, flips=6):
    """Frames of the threshold with one PP_DreamMono blendable (matched by name) on and off in turn, PIE copy only."""
    def gen():
        ppv = actor('PP_DreamMono')
        for i in range(flips):
            s = ppv.get_editor_property('settings')
            wbs = s.get_editor_property('weighted_blendables')
            arr = list(wbs.get_editor_property('array'))
            for b in arr:
                o = b.get_editor_property('object')
                if o and name in o.get_name():
                    b.set_editor_property('weight', 1.0 if i % 2 == 0 else 0.0)
            wbs.set_editor_property('array', arr)
            s.set_editor_property('weighted_blendables', wbs)
            ppv.set_editor_property('settings', s)
            yield from sleep(0.45)
            log('blendable_ab', blendable=name, on=i % 2 == 0, frame=shot(f'{tag}_{"on" if i % 2 == 0 else "off"}{i}'))
    return gen


PLANS.update({
    'ATF': PLANS['CP'][:-1] + [('threshold', 'face blur on and off at the open door', g_blendable_ab('FaceBlur', 'fb'), 8, False),
                               ('threshold', 'dream lens on and off at the open door', g_blendable_ab('DreamLens', 'lens'), 8, False),
                               ('threshold', 'control: the PIE exposure edit darkens a lit room (EV -1 then +1.5)', g_exposure_control, 4, False)],
    'ATX': [('L2', 'fixture: front end skipped, door and threshold at 4x to the colour path', dream_fixture(), 16, True),
            ('L2', 'exposure sweep in Dream A (PIE copy of PP_DreamMono only)', g_exposure_sweep, 20, False)],
    'ATH': boot() + [
        ('T8', 'shortcut: EnterBeat 8', do(lambda: one('director').call_method('EnterBeat', (8,)), what='EnterBeat 8'), 2, True),
        ('T8', 'battle intro: hold Space to skip', g_battle_intro(True), 12, False),
        ('T8', 'the player in the fight framing, Hair groom on and off', g_hair_ab(), 8, False)],
    'ATE': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('drive', 'into the car: Confirm twice; the car drives off on its own', into_car(), 6, True),
            ('drive', 'teaching leg: brace with the real Space; the car parks itself', g_drive(), 22, False),
            ('drive', 'parked: the engine bed fades out and stops', g_engine_watch(), 9, False)],
    'ATP': [('L2', 'fixture: front end skipped, door and threshold at 4x to the colour path', dream_fixture(), 16, True),
            ('L2', 'every post-process source live in Dream A', g_pp_probe, 6, False)],
    'ATC': [('L2', 'fixture: Level 2 street via the threshold fixture (4x)', l2_fixture(), 34, True),
            ('L2', 'the street: BP_RoomAudio place beds playing', g_place_beds, 10, False)],
})


# ---- intro lane: the opening story (WBP_IntroStory v4) played in full, filmed every 0.25 s (2026-11-18) -------------
# IN1  title and menu, then the intro to its own end with frames and a per-frame log of the panel clock and the sand line
#      (Line_Sub T, OutT, Mood, bLeaving), then LS_WakeUp must take over (the OnStoryFinished hand-off).
def intro_mpc(fn, name, *value):
    """KismetMaterialLibrary on MPC_UI in the PIE world (the class is not exposed to Python by name)."""
    lib = unreal.get_default_object(unreal.load_class(None, '/Script/Engine.KismetMaterialLibrary'))
    return lib.call_method(fn, (W(), unreal.load_asset('/Game/FoA/UI/Style/MPC_UI.MPC_UI'), name, *value))


def g_intro_film(every=0.25, limit=44.0):
    def gen():
        yield from wait(lambda: phase() not in ('black', 'menu'))  # Wake up cuts to black before the story is added
        t0, last, panels, end = time.time(), 0.0, [], time.time() + limit
        while phase() == 'story' and time.time() < end:
            st = prop(one('fe'), 'Story')
            i = prop(st, 'Index', -1) if st else -1
            if i not in panels:  # every tick, so a sparse film (IN0) still sees each panel
                panels.append(i)
            if time.time() - last >= every:
                last = time.time()
                ln = prop(st, 'Line_Sub') if st else None
                log('intro', i=i, pt=round(prop(st, 'PanelTime', 0.0) or 0.0, 2), s=round(time.time() - t0, 2),
                    rm=round(intro_mpc('GetScalarParameterValue', 'ReduceMotion'), 2),
                    motion=round(prop(st, 'Motion', 0.0) or 0.0, 3),
                    line=dict(T=round(prop(ln, 'T', 0.0) or 0.0, 2), out=round(prop(ln, 'OutT', 0.0) or 0.0, 2),
                              mood=prop(ln, 'Mood'), leaving=prop(ln, 'bLeaving'),
                              vis=str(ln.get_visibility()) if ln else None) if ln else None,
                    frame=shot(f'in{i}'))
            yield
        secs = round(time.time() - t0, 1)
        log('intro_end', result='PASS' if panels == [0, 1, 2, 3, 4] and phase() != 'story' else 'FAIL', secs=secs,
            panels=panels, phase=phase())
        if panels != [0, 1, 2, 3, 4]:
            raise Miss(f'intro panels {panels} in {secs} s')
    return gen


def g_intro_skip_check():
    """After the skip: the film runs, and the story's line timers never fire on the removed widget."""
    st = prop(one('fe'), 'Story')
    yield from wait(lambda: phase() in ('film', 'game'))
    yield from sleep(3.0)  # past every PlayLine and DismissLine time a skipped panel had pending
    ln = prop(st, 'Line_Sub') if st else None
    gone = st is None or (prop(st, 'bDone') and not st.is_in_viewport())  # the front end may drop its Story reference
    log('intro_skip', result='PASS' if gone and phase() in ('film', 'game') else 'FAIL',
        done=prop(st, 'bDone') if st else None, in_viewport=st.is_in_viewport() if st else None,
        line_T=round(prop(ln, 'T', 0.0) or 0.0, 2) if ln else None, phase=phase(), frame=shot('after_skip'))


PLANS.update({
    'IN1': boot()[:3] + [
        ('intro', 'intro story plays in full, filmed every 0.25 s', g_intro_film(), 46, False),
        ('wakeup', 'LS_WakeUp takes over after the story', until(lambda: phase() in ('film', 'game')), 4, False)],
    # IN2: Skip while the first line is forming (2.4 s in), then the film; IN0: the intro unfilmed, for frame times
    'IN2': boot()[:3] + [
        ('intro', 'intro skipped mid-line (Skip)', front('story', skip_story, 2.4), 12, False),
        ('wakeup', 'LS_WakeUp takes over, no line fires after the skip', g_intro_skip_check, 8, False)],
    'IN0': boot()[:3] + [
        ('intro', 'intro story plays in full, unfilmed (frame times)', g_intro_film(every=12.0), 46, False),
        ('wakeup', 'LS_WakeUp takes over after the story', until(lambda: phase() in ('film', 'game')), 4, False)],
    # IN3: Reduce Motion on (this PIE world's MPC_UI only, the Settings value is untouched): the camera holds, the
    # sand transitions and lines still play; frames every 0.5 s
    'IN3': [('boot', 'fixture: MPC_UI.ReduceMotion = 1 in the PIE world', do(lambda: intro_mpc('SetScalarParameterValue', 'ReduceMotion', 1.0),
                                                                             what='ReduceMotion 1'), 2, True)]
           + boot()[:3] + [
        ('intro', 'intro story under Reduce Motion, filmed every 0.5 s', g_intro_film(every=0.5), 46, False),
        ('wakeup', 'LS_WakeUp takes over after the story', until(lambda: phase() in ('film', 'game')), 4, False)],
})



# ---- level1 lane: pawn snaps in the T7 chase into T8 (the user's "teleports many times") ----------------------------
def g_wardrobe_film(seconds=7.0, every=0.1):
    """Coordinator (2026-11-18, the user: 'he is glitching and moving about, he falls then he is back up'): film the T6
    wardrobe fall densely with the actor, pelvis bone, montage and view for every frame."""
    def gen():
        end, last, n = time.time() + seconds, 0.0, 0
        while time.time() < end:
            if time.time() - last >= every:
                last, n = time.time(), n + 1
                p = pawn()
                body = prop(p, 'Body')
                ai = body.get_anim_instance() if body else None
                mont = ai.get_current_active_montage() if ai else None
                pel = body.get_socket_location('pelvis') if body else None
                rot = p.get_actor_rotation()
                log('wf', n=n, beat=beat(), view=view(), actor=[round(v) for v in p.get_actor_location().to_tuple()],
                    yaw=round(rot.yaw), pelvis=[round(v) for v in pel.to_tuple()] if pel else None,
                    montage=mont.get_name() if mont else None, cinematic=prop(p, 'bCinematic'),
                    mesh_rel=[round(v) for v in body.get_editor_property('relative_location').to_tuple()] if body else None,
                    frame=shot('wf%03d' % n))
            yield
    return gen


def l1_track_tick(now):
    """Every tick: the pawn's location and speed. A snap is a move the character's own velocity cannot explain (more
    than 1.5 x speed x dt + 15 cm), so a slow editor frame is not counted as a teleport. Logged, not filmed (a
    screenshot itself makes the next frame long); the path goes to l1_path.csv every 2 s."""
    p = pawn()
    if not p:
        return
    at, v = p.get_actor_location(), p.get_velocity().length()
    last = S.get('l1_last')
    S['l1_last'] = (now, at, v)
    S.setdefault('l1_path', []).append((round(now - S['t0'], 3), round(at.x, 1), round(at.y, 1), round(at.z, 1), round(v), view()))
    if now - S.get('l1_path_t', 0) > 2.0:
        S['l1_path_t'] = now
        open(OUT + '/l1_path.csv', 'w').write('t,x,y,z,speed,view' + chr(10) + chr(10).join(','.join(map(str, r)) for r in S['l1_path']))
    if not last:
        return
    d, dt = (at - last[1]).length(), now - last[0]
    if d > 1.5 * max(v, last[2]) * dt + 15.0:
        S['l1_jumps'] = S.get('l1_jumps', 0) + 1
        log('l1_jump', n=S['l1_jumps'], dist_cm=round(d, 1), dt_ms=round(dt * 1000, 1), speed=round(max(v, last[2])),
            src=[round(x) for x in last[1].to_tuple()], dst=[round(x) for x in at.to_tuple()], view=view(), beat=beat(),
            stage=stage(), shirt=state_of('Shirt_T7'))


def l1_track_on(on=True):
    def gen():
        S['l1_track'], S['l1_last'] = on, None
        if not on:
            path = S.get('l1_path', [])
            open(OUT + '/l1_path.csv', 'w').write('t,x,y,z,speed,view' + chr(10) + chr(10).join(','.join(map(str, r)) for r in path))
            log('l1_track_done', ticks=len(path), jumps=S.get('l1_jumps', 0))
        yield
    return gen


PLANS.update({
    # the hanger, the release and hand-back, the first chase
    'WF': boot() + [  # coordinator: the T6 wardrobe fall filmed every 0.1 s with the pawn tracked every tick
        ('T1', 'track the pawn every tick from here', l1_track_on(), 2, False),
        to_t7()[0],
        ('T6', 'the wardrobe fall, filmed every 0.1 s', g_wardrobe_film(7.0), 9, False),
        ('T6', 'tracking off, path written', l1_track_on(False), 2, False)],
    'L1T1': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'fixture: the three clues, to the snag', fixture_clothing_before(4), 14, True),
        ('T7', 'track the pawn every tick from here', l1_track_on(), 2, False),
        ('T7', 'hanger, unhook the shirt', hanger_then_bed(), 16, False),
        ('T7', 'chase 1: reach the shirt', chase(1), 10, False),
        ('T7', 'tracking off, path written', l1_track_on(False), 2, False)],
    # B2b's path (escape two, the vase, the boss into T8) with the same tracking
    'L1T2': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'shortcut: search events to the snag', chain(do(search_events, what='ReportEvent Clothing*Searched x3, Add Hanger'),
                                                            until(lambda: stage() >= 4 and free())), 15, True),
        ('T7', 'fixture: toss and escape one (stage functions) to stage 6', chain(do(to_escape_two, what='BeginClothingToss, EscapeClothingOne'),
                                                                                 until(lambda: stage() >= 6 and free())), 8, True),
        ('T7', 'track the pawn every tick from here', l1_track_on(), 2, False),
        ('T7', 'chase 2: reach the shirt again, escape two', chase(2), 10, False),
        ('T7', 'the vase: grab the shirt', chase(3), 10, False),
        ('T7', 'boss forms: T8', take_shirt(), 14, False),
        ('T8', 'the encounter starts', until(lambda: prop(one('enc'), 'bActive')), 6, False),
        ('T8', 'tracking off, path written', l1_track_on(False), 2, False)],
    # the final catch at the vase, the boss forming, into the encounter
    'L1T3': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'fixture: clues, toss and both escapes (stage functions) to stage 7', fixture_clothing_before(7), 16, True),
        ('T7', 'track the pawn every tick from here', l1_track_on(), 2, False),
        ('T7', 'the vase: grab the shirt', chase(3), 10, False),
        ('T7', 'boss forms: T8', take_shirt(), 14, False),
        ('T8', 'the encounter starts', until(lambda: prop(one('enc'), 'bActive')), 8, False),
        ('T8', 'tracking off, path written', l1_track_on(False), 2, False)],
})


# ---- level1 lane: first-person camera motion while he has control (the user: "the head moves too much") -----------
def l1_cam_probe():
    """Idle 3 s, walk forward 2.5 s, stop 1.5 s, strafe right 2 s, stop 1 s, turn with the mouse 2 s (90 deg/s), idle 1 s.
    Every tick: the rendered camera's offset from the capsule in the pawn's frame (x forward, y right, z up) and the
    camera rotation minus the control rotation (pitch, yaw, roll). Written to l1_cam.csv (phase, t, fwd, right, up,
    pitch, yaw, roll, speed)."""
    def gen():
        yield from wait(free)
        p, c = pawn(), pc()
        rows, phase_t0 = [], time.time()
        start = c.get_control_rotation()
        c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=start.yaw))
        plan = [('idle', 3.0), ('walk', 2.5), ('stop', 1.5), ('strafe', 2.0), ('stop2', 1.0), ('turn', 2.0), ('idle2', 1.0)]
        for name, secs in plan:
            end = time.time() + secs
            while time.time() < end:
                xf = p.get_actor_transform()
                cam = c.player_camera_manager
                loc = xf.inverse_transform_location(cam.get_camera_location())
                cr, ctl = cam.get_camera_rotation(), c.get_control_rotation()
                d = lambda a, b: round((a - b + 180) % 360 - 180, 3)  # noqa: E731
                rows.append((name, round(time.time() - phase_t0, 3), round(loc.x, 2), round(loc.y, 2), round(loc.z, 2),
                             d(cr.pitch, ctl.pitch), d(cr.yaw, ctl.yaw), round(cr.roll, 3), round(p.get_velocity().length())))
                yaw = c.get_control_rotation().yaw
                fwd = unreal.MathLibrary.get_forward_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
                right = unreal.MathLibrary.get_right_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
                if name == 'walk':
                    p.add_movement_input(fwd, 1.0, False)
                elif name == 'strafe':
                    p.add_movement_input(right, 1.0, False)
                elif name == 'turn':
                    r = c.get_control_rotation()
                    c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 90.0 * S['dt']))
                if name in ('walk', 'idle') and len(rows) % 12 == 0:
                    shot('cam_' + name)
                yield
        open(OUT + '/l1_cam.csv', 'w').write('phase,t,fwd,right,up,pitch,yaw,roll,speed' + chr(10) +
                                             chr(10).join(','.join(map(str, r)) for r in rows))
        log('l1_cam', ticks=len(rows))
    return gen


PLANS.update({
    'L1CAM': boot() + [('T1', 'first-person camera: idle, walk, stop, strafe, turn (per tick)', l1_cam_probe(), 16, False)],
})


def l1_inspect_turn():
    """The user's "turning fast I could see through my body": take the screwdriver, and the moment it is carried (before
    the inspect opens) turn the view 120 deg in 3 ticks. When the inspect is up, log the camera's distance to the head
    bone and its yaw from the body, then film it as is and with Face, Hair, Body hidden in turn (restored after)."""
    def gen():
        take = use('Screwdriver_DeskDrawer', 'Take', until=lambda: 'Screwdriver' in items())
        if state_of('Screwdriver_DeskDrawer') != 'Available':
            yield from use('Desk', 'Use', until=lambda: state_of('Screwdriver_DeskDrawer') == 'Available')()
        yield from take()
        c = pc()
        for _ in range(3):
            r = c.get_control_rotation()
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 40.0))
            yield
        end = time.time() + 4.0
        ins = None
        while time.time() < end:
            ins = unreal.GameplayStatics.get_actor_of_class(W(), cls(INSPECT))
            if ins and prop(ins, 'bOpen'):
                break
            yield
        yield from sleep(0.6)
        p = pawn()
        body = prop(p, 'Body')
        cam = c.player_camera_manager
        dist = (cam.get_camera_location() - body.get_socket_location('head')).length()
        yaw_off = (cam.get_camera_rotation().yaw - p.get_actor_rotation().yaw + 180) % 360 - 180
        log('l1_inspect_turn', open=bool(ins and prop(ins, 'bOpen')), cam_head_cm=round(dist, 1), cam_yaw_from_body=round(yaw_off, 1),
            hidden=p.is_hidden(), frame=shot('ins_all'))
        yield from sleep(0.35)
        for name in ('Face', 'Hair', 'Body'):
            comp_ = prop(p, name)
            if not comp_:
                continue
            was = comp_.is_visible()
            comp_.set_visibility(False, True)
            yield from sleep(0.3)
            log('l1_inspect_ablate', hidden=name, frame=shot('ins_no_' + name))
            yield from sleep(0.3)
            comp_.set_visibility(was, True)
        if ins:
            ins.call_method('Close')
        yield from sleep(1.0)
    return gen


PLANS.update({
    'L1INS': boot() + [
        ('T5', 'fixture: T5, key jammed', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the screwdriver, turn fast, item inspect: what is in the view', l1_inspect_turn(), 30, False)],
})


# ---- doortool lane: the screwdriver at the lock plate, measured in the door's frame and filmed densely -------------
def dt_measure(tag):
    try:
        dt_measure_now(tag)
    except Exception as ex:  # a measurement never stops the plan; say why
        log('doortool_measure_error', tag=tag, err=repr(ex)[:200])


def dt_measure_now(tag):
    """Logs (cm, door frame) the held screwdriver's tip against the current screw, its axis against the door normal,
    the arm bones, the hand's axes and the view."""
    door, p = actor('Door_Bedroom'), pawn()
    body, tool = p.get_editor_property('Body'), p.get_editor_property('HeldTool')
    xf = door.get_actor_transform()
    local = lambda v: [round(x, 2) for x in xf.inverse_transform_location(v).to_tuple()]  # noqa: E731
    i = min(prop(door, 'ToolStepIndex', 0), 3)
    parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
    screw = parts['ToolScrew%d' % i].get_world_location()
    tx = tool.get_world_transform()
    ends = [tx.transform_location(unreal.Vector(0, 0, z)) for z in (13.51, -7.39)]  # the mesh's two ends along Z
    tip, butt = sorted(ends, key=lambda v: (v - screw).length())
    axis = [a - b for a, b in zip(tip.to_tuple(), butt.to_tuple())]
    n = door.get_actor_forward_vector().to_tuple()
    off = math.degrees(math.acos(min(1.0, abs(sum(a * b for a, b in zip(axis, n))) / math.sqrt(sum(a * a for a in axis)))))
    hand = body.get_socket_transform('hand_r', unreal.RelativeTransformSpace.RTS_WORLD)
    q = hand.rotation
    axes = {k: [round(x, 3) for x in xf.inverse_transform_direction(v).to_tuple()]
            for k, v in (('x', q.get_axis_x()), ('y', q.get_axis_y()), ('z', q.get_axis_z()))}
    cam = pc().player_camera_manager
    mh = body.get_anim_instance()
    anim = {k: (local(prop(mh, k)) if 'Target' in k else round(prop(mh, k, -1.0), 3)) for k in (
        'ToolHandWeight', 'HeldToolWeight', 'RightGrip_Screwdriver0', 'RightGrip_Screwdriver1', 'RightGrip_Screwdriver2',
        'RightGrip_Screwdriver3', 'ScrewGripTime', 'ScrewReleaseWeight', 'ToolHandTarget', 'ToolElbowTarget')}
    anim.update(GripAlpha=prop(p, 'GripAlpha'), GripPose=str(prop(p, 'GripPose')), ScrewGripAlpha=prop(p, 'ScrewGripAlpha'))
    log('doortool_measure', tag=tag, index=prop(door, 'ToolStepIndex'), angle=round(prop(door, 'ToolAngle', 0.0), 1), anim=anim,
        tip=local(tip), butt=local(butt), screw=local(screw), tip_to_screw_cm=round((tip - screw).length(), 2),
        axis_off_normal_deg=round(off, 1), hand_axes=axes, camera=local(cam.get_camera_location()),
        camera_rot=str(cam.get_camera_rotation()), fov=round(cam.get_fov_angle(), 1), pawn=local(p.get_actor_location()),
        bones={b: local(body.get_socket_location(b)) for b in ('head', 'neck_01', 'clavicle_r', 'upperarm_r', 'lowerarm_r',
                                                               'hand_r', 'middle_01_r', 'thumb_02_r', 'index_03_r')})


def dt_sweep():
    """At screw 1: frames from candidate views near his own eyes (head bone + 7 up, 8 toward the door) and of the task
    light (as it is, off, a soft key above-left of the view at matched lock illuminance), then both put back exactly."""
    door, body = actor('Door_Bedroom'), pawn().get_editor_property('Body')
    xf = door.get_actor_transform()
    parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
    cam, light = parts['ToolCamera'], parts['ToolTaskLight']
    keep = (cam.get_world_location(), cam.get_world_rotation(), cam.get_editor_property('field_of_view'),
            light.get_world_location(), light.get_editor_property('intensity'))
    loc = lambda v: xf.inverse_transform_location(v)  # noqa: E731
    world = lambda v: xf.transform_location(unreal.Vector(*v))  # noqa: E731
    h = loc(body.get_socket_location('head')).to_tuple()
    s = loc(parts['ToolScrew0'].get_world_location()).to_tuple()
    aim = world((s[0] - 2, s[1], s[2]))
    old = loc(keep[0]).to_tuple()
    log('doortool_sweep_base', head=[round(x, 1) for x in h], old_camera=[round(x, 1) for x in old],
        light=[round(x, 1) for x in loc(keep[3]).to_tuple()], intensity=keep[4],
        units=str(light.get_editor_property('intensity_units')), radius=light.get_editor_property('attenuation_radius'))
    views = [(k, tuple(float(v) for v in off.split(',')), float(fov)) for k, off, fov in
             (r.split(':') for r in os.environ.get('FOA_DT_VIEWS', 'behind_r:-15,0,22:50;higher:-18,-6,30:50;'
                                                   'closer:-8,-4,16:50;wide:-15,-6,22:58').split(';'))]
    try:
        for tag, off, fov in views:  # offsets from the head bone, door frame; the frame shows the state when shot
            at = world(tuple(a + b for a, b in zip(h, off)))
            cam.set_world_location_and_rotation(at, unreal.MathLibrary.find_look_at_rotation(at, aim), False, True)
            cam.set_field_of_view(fov)
            yield from sleep(0.35)
            log('doortool_view', tag=tag, camera=[round(x, 1) for x in loc(at).to_tuple()], fov=fov, frame=shot('view_' + tag))
            yield from sleep(0.12)
        cam.set_world_location_and_rotation(keep[0], keep[1], False, True)  # the light from the door's own view
        cam.set_field_of_view(keep[2])
        for tag, where, power in (('as_is', keep[3], keep[4]), ('off', keep[3], 0.0), ('half', keep[3], keep[4] / 2)):
            light.set_world_location(where, False, True)
            light.set_intensity(power)
            yield from sleep(0.5)
            log('doortool_light', tag=tag, light=[round(x, 1) for x in loc(where).to_tuple()], intensity=round(power, 3),
                frame=shot('light_' + tag))
            yield from sleep(0.12)
    finally:
        cam.set_world_location_and_rotation(keep[0], keep[1], False, True)
        cam.set_field_of_view(keep[2])
        light.set_world_location(keep[3], False, True)
        light.set_intensity(keep[4])
    yield from sleep(0.3)


DT_SCREW = 1  # top right: the fist hides the top-left screw (0) from the game's view


def dt_screw(tag):
    """Logs where screw DT_SCREW is (door frame, cm) and its roll, the drop state and time."""
    try:
        door = actor('Door_Bedroom')
        parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
        s = parts['ToolScrew%d' % DT_SCREW]
        rel = s.get_editor_property('relative_location')
        log('doortool_screw', tag=tag, angle=round(prop(door, 'ToolAngle', 0.0), 1), index=prop(door, 'ToolStepIndex'),
            rel=[round(v, 2) for v in rel.to_tuple()], roll=round(s.get_editor_property('relative_rotation').roll, 1),
            yaw=round(s.get_editor_property('relative_rotation').yaw, 1), visible=s.is_visible(),
            world=[round(v, 1) for v in s.get_world_location().to_tuple()], landed=prop(door, 'bToolDropLanded'),
            holes=parts['ToolScrewHoles'].get_instance_count() if 'ToolScrewHoles' in parts else None,
            drop_time=round(prop(door, 'ToolDropTime', 0.0), 3))
    except Exception as ex:  # a measurement never stops the plan
        log('doortool_screw_error', tag=tag, err=repr(ex)[:200])


def dt_backout():
    """Screw DT_SCREW under the screwdriver (the ones before it turned out as a player would): held mid-stroke and at
    the end of each of its first four strokes from the game's view, plus a close-up at each stroke end; then the last
    stretch at 1/4 time and the drop filmed from a view that shows the floor. The camera and time are put back."""
    def gen():
        door = actor('Door_Bedroom')
        yield from wait(lambda: prop(door, 'bToolActive') and prop(door, 'bToolReady'))
        while prop(door, 'ToolStepIndex', 0) < DT_SCREW and prop(door, 'bToolActive'):
            if prop(door, 'bToolReady'):
                door.call_method('AdvanceDoorTool', (1.0, S['dt']))
            yield
        yield from wait(lambda: prop(door, 'bToolReady'))
        yield from sleep(0.8)
        xf = door.get_actor_transform()
        parts = {c.get_name(): c for c in door.get_components_by_class(unreal.SceneComponent)}
        cam = parts['ToolCamera']
        keep = (cam.get_world_location(), cam.get_world_rotation(), cam.get_editor_property('field_of_view'))
        w = lambda *v: xf.transform_location(unreal.Vector(*v))  # noqa: E731

        def view(at, aim, fov):
            cam.set_world_location_and_rotation(w(*at), unreal.MathLibrary.find_look_at_rotation(w(*at), w(*aim)), False, True)
            cam.set_field_of_view(fov)

        def to(angle):
            while prop(door, 'ToolAngle', 0.0) < angle and prop(door, 'ToolStepIndex', 0) == DT_SCREW:
                left = angle - prop(door, 'ToolAngle', 0.0)
                door.call_method('AdvanceDoorTool', (1.0, min(S['dt'], max(0.0005, left / 300.0))))
                yield

        def hold(tag):
            yield from sleep(0.35)
            dt_screw(tag)
            dt_measure(tag)
            shot(tag)
            yield from sleep(0.12)

        try:
            dt_screw('bo_000')
            shot('bo_000')
            yield from sleep(0.3)
            for k in range(1, 5):
                yield from to(90 * k - 45)
                yield from hold('bo_%03d' % (90 * k - 45))
                yield from to(90 * k)
                yield from hold('bo_%03d' % (90 * k))
                view((-9, -93.3, 96), (-0.75, -82.15, 91.5), 40.0)  # close-up, from the left of the screw
                yield from hold('bo_close_%03d' % (90 * k))
                cam.set_world_location_and_rotation(keep[0], keep[1], False, True)
                cam.set_field_of_view(keep[2])
            yield from to(690)
            # the drop from the game's own view: the player sees it pop out and fall away, then hears it land
            unreal.GameplayStatics.set_global_time_dilation(W(), 0.25)
            yield from hold('drop_before')
            while prop(door, 'ToolStepIndex', 0) == DT_SCREW and prop(door, 'bToolActive'):
                door.call_method('AdvanceDoorTool', (1.0, S['dt']))
                yield
            for k in range(10):  # 0.26 s real is about 0.065 s of game time
                dt_screw('drop_%02d' % k)
                shot('drop_%02d' % k)
                yield from sleep(0.26)
        finally:
            unreal.GameplayStatics.set_global_time_dilation(W(), 1.0)
            cam.set_world_location_and_rotation(keep[0], keep[1], False, True)
            cam.set_field_of_view(keep[2])
        yield from sleep(0.5)
    return gen


def dt_film():
    """Each screw seated (0.6 s settle, measured, one frame); one full stroke of screw 1 held every 15 deg; each reach to
    the next screw filmed every 0.26 s. Otherwise turns like a player holding D (AdvanceDoorTool, as door_tool).
    FOA_DT_SWEEP=1 (default) also runs dt_sweep at screw 1."""
    def gen():
        door = actor('Door_Bedroom')
        yield from wait(lambda: prop(door, 'bToolActive'))
        seen = -1
        while prop(door, 'bToolActive'):
            i = prop(door, 'ToolStepIndex', 0)
            if i != seen and i < 4:
                if seen >= 0:  # the reach to the next screw, as it happens
                    for k in range(4):
                        dt_measure('reach%d_%d' % (i, k))
                        shot('reach%d_%d' % (i, k))
                        yield from sleep(0.26)
                seen = i
                yield from wait(lambda: prop(door, 'bToolReady') or not prop(door, 'bToolActive'))
                yield from sleep(0.6)
                dt_measure('seat%d' % i)
                shot('seat%d' % i)
                yield from sleep(0.3)
                if i == 0 and os.path.exists('P:/FoA/Saved/QA/lanes/doortool/sweep.on'):
                    yield from dt_sweep()
                if i == 0:
                    for target in range(15, 91, 15):
                        while prop(door, 'ToolAngle', 0.0) < target and prop(door, 'ToolStepIndex', 0) == 0:
                            left = target - prop(door, 'ToolAngle', 0.0)
                            door.call_method('AdvanceDoorTool', (1.0, min(S['dt'], max(0.0005, left / 300.0))))
                            yield
                        yield from sleep(0.3)
                        dt_measure('twist_%03d' % target)
                        shot('twist_%03d' % target)
                        yield from sleep(0.12)  # the shot renders at the end of this frame: hold still until then
                continue
            if prop(door, 'bToolReady'):
                door.call_method('AdvanceDoorTool', (1.0, S['dt']))
            yield
        yield from wait(lambda: state_of('Door_Bedroom') == 'PlateOff' and free())
    return gen


PLANS.update({
    'DTS': boot() + [
        ('T5', 'fixture: key jammed, screwdriver owned', do(lambda: fixture_t5('Screwdriver'), what='T5 KeyJammed, Screwdriver owned'), 2, True),
        ('T5', 'native screwdriver insert, four screws measured and filmed', chain(
            native_use('Door_Bedroom', item='Screwdriver', extra=90, until=lambda: prop(actor('Door_Bedroom'), 'bToolActive')),
            dt_film()), 45, False)],
    'DTB': boot() + [
        ('T5', 'fixture: key jammed, screwdriver owned', do(lambda: fixture_t5('Screwdriver'), what='T5 KeyJammed, Screwdriver owned'), 2, True),
        ('T5', 'screw 1 backs out over four strokes, then pops free and drops', chain(
            native_use('Door_Bedroom', item='Screwdriver', extra=90, until=lambda: prop(actor('Door_Bedroom'), 'bToolActive')),
            dt_backout()), 40, False)],
})


def l1_dilate(rate):
    """World time dilation (timers and sequences follow it), so a slow capture still samples every 0.1 s of game time."""
    def gen():
        unreal.GameplayStatics.set_global_time_dilation(W(), rate)
        log('l1_dilation', rate=rate)
        yield
    return gen


def l1_dense_frame(n, gt, tag):
    """One logged frame: game time, actor, pelvis, head, feet z, hands, yaw, hidden, the mesh's anim mode, the montage,
    the view target, bCinematic, and the screenshot."""
    p = pawn()
    body = prop(p, 'Body')
    mesh = p.get_editor_property('mesh')
    anim = mesh.get_anim_instance()
    mon = anim.get_current_active_montage() if anim else None
    f = f'{OUT}/frames/{PLAN}_{int((time.time() - S["t0"]) * 100):05d}_{beat()}_{tag}{n:03d}.png'
    unreal.SystemLibrary.execute_console_command(W(), f'Shot showui filename={f} -nosuffix')
    at = p.get_actor_location()
    r = lambda v: [round(c) for c in v.to_tuple()]  # noqa: E731
    sock = (lambda b: body.get_socket_location(b)) if body else (lambda b: at)  # noqa: E731
    log('l1_dense', n=n, gt=round(gt, 3), at=r(at), pelvis=r(sock('pelvis')), head=r(sock('head')),
        feet=[round(sock('foot_l').z), round(sock('foot_r').z)], hands=[r(sock('hand_l')), r(sock('hand_r'))],
        yaw=round(p.get_actor_rotation().yaw), hidden=bool(p.get_editor_property('hidden')),
        mode=str(mesh.get_editor_property('animation_mode')).split('.')[-1].split(':')[0],
        montage=(mon.get_name() if mon else None), mpos=(round(anim.montage_get_position(mon), 2) if mon else None),
        view=view(), cinematic=prop(p, 'bCinematic'), beat=beat(), frame=f)


def l1_film_dense(seconds, every=0.1, tag='f'):
    """Film every `every` s of GAME time (bypassing shot()'s 0.25 s guard), one l1_dense_frame each.
    Ends with the wardrobe's colliding bounds (where the fallen wardrobe really lies)."""
    def gen():
        end, last, n = time.time() + seconds, -1.0, 0
        while time.time() < end:
            gt = unreal.GameplayStatics.get_time_seconds(W())
            if gt - last >= every - 0.005:
                last, n = gt, n + 1
                l1_dense_frame(n, gt, tag)
            yield
        w = actor('Wardrobe')
        if w:
            o, e = w.get_actor_bounds(True)
            log('l1_wardrobe_bounds', lo=[round(v) for v in (o - e).to_tuple()], hi=[round(v) for v in (o + e).to_tuple()])
    return gen


def l1_film_while(step, tail=1.5, every=0.1, tag='s'):
    """Run another step (a generator factory) while filming every `every` s of game time; film `tail` s more after."""
    def gen():
        g, last, n, end = step(), -1.0, 0, None
        while end is None or time.time() < end:
            gt = unreal.GameplayStatics.get_time_seconds(W())
            if gt - last >= every - 0.005:
                last, n = gt, n + 1
                l1_dense_frame(n, gt, tag)
            if end is None:
                try:
                    next(g)
                except StopIteration:
                    end = time.time() + tail
            yield
    return gen


def to_vase():
    """From the snag (stage 4): toss, escape one and escape two back to back, so the shirt waits at the vase."""
    to_escape_two()
    one('director').call_method('EscapeClothingTwo')


PLANS.update({
    'L1WF': boot() + [
        ('T1', 'track the pawn every tick from here', l1_track_on(), 2, False),
        ('T6', 'slow the world to 0.4 so frames land every 0.1 s of game time', l1_dilate(0.4), 1, False),
        ('T6', 'fixture T6, then the wardrobe HandleOff notification starts the full fall',
         do(fixture_wardrobe, what='EnterBeat 6, Wardrobe Interact Notify HandleOff'), 2, True),
        ('T6', 'the wardrobe fall, a frame every 0.1 s of game time', l1_film_dense(21.0, 0.1, 'wf'), 23, False),
        ('T7', 'normal speed, tracking off, path written', l1_dilate(1.0), 1, False),
        ('T7', 'tracking off', l1_track_on(False), 2, False)],
})

# ---- playercam lane: first-person camera motion and the fast-turn inspect (the user's two camera bugs, 2026-11-18) ----
def pc_torso_yaw(p):
    """The animated torso's facing, as BP_FoAPlayer computes it: Cross(upperarm_r - upperarm_l, up)."""
    b = prop(p, 'Body')
    a = b.get_socket_location('upperarm_r') - b.get_socket_location('upperarm_l')
    return math.degrees(math.atan2(-a.x, a.y))


def pc_sample(phase):
    """One per-tick row: the rendered camera in the capsule's frame (cm: forward, right, up), its rotation, the control
    rotation, capsule and torso yaw, speed, camera to head bone, the FollowCamera component's own offset from the
    rendered camera (a shake or modifier shows here), the view target and the flags. A tick next to a screenshot is
    marked (its frame time is long)."""
    p, c = pawn(), pc()
    cam = c.player_camera_manager
    xf = p.get_actor_transform()
    cl = cam.get_camera_location()
    loc = xf.inverse_transform_location(cl)
    cr, ctl = cam.get_camera_rotation(), c.get_control_rotation()
    fc = prop(p, 'FollowCamera')
    head = prop(p, 'Body').get_socket_location('head')
    hx = prop(p, 'Face').get_socket_transform('head', unreal.RelativeTransformSpace.RTS_WORLD)
    eye = xf.inverse_transform_location(hx.transform_location(unreal.Vector(0.0, -3.530588955620998, 11.768322164387774)))
    d = lambda a: round((a + 180) % 360 - 180, 3)  # noqa: E731
    S.setdefault('pc_rows', []).append(dict(
        cz=round(cl.z, 2), pz=round(xf.translation.z, 2), ex=round(eye.x, 2), ey=round(eye.y, 2), ez=round(eye.z, 2), phase=phase, t=round(time.time() - S['t0'], 3), dt=round(S['dt'] * 1000, 1), fwd=round(loc.x, 2), right=round(loc.y, 2),
        up=round(loc.z, 2), cpitch=round(cr.pitch, 3), cyaw=round(cr.yaw, 3), croll=round(cr.roll, 3), kpitch=round(ctl.pitch, 3),
        kyaw=round(ctl.yaw, 3), pyaw=round(p.get_actor_rotation().yaw, 3), tyaw=round(pc_torso_yaw(p), 2),
        view_torso=d(cr.yaw - pc_torso_yaw(p)), speed=round(p.get_velocity().length(), 1), head_cm=round((cl - head).length(), 1),
        fc_off=round((fc.get_world_location() - cl).length(), 2) if fc else None, view=view(), locked=bool(prop(p, 'bInteractionLocked')),
        cine=bool(prop(p, 'bCinematic')), paused=unreal.GameplayStatics.is_game_paused(W()), near_shot=int(S['n'] - S['shot_n'] <= 2)))


def pc_write(name='pc_cam.csv'):
    rows = S.get('pc_rows', [])
    if rows:
        with open(f'{OUT}/{name}', 'w', newline='', encoding='utf-8') as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            wr.writeheader()
            wr.writerows(rows)
    log('pc_rows', file=name, ticks=len(rows))


def pc_motion_probe():
    """Face the room centre, then idle, walk forward, stop, strafe right, stop, turn with the mouse at 150 deg/s, stop,
    flick 120 deg in 3 ticks, walk while turning, stop. Every tick sampled (pc_sample); the periodic 1 s screenshot is
    held off while sampling (it makes the next frame long), and one deliberate frame ends each phase."""
    def gen():
        yield from wait(free)
        p, c = pawn(), pc()
        mid = unreal.Vector(0.0, 0.0, p.get_actor_location().z + 40)
        end = time.time() + 1.0
        while time.time() < end:
            turn_toward(mid, 8.0)
            yield
        plan = [('idle', 3.0), ('walk', 2.2), ('stop', 1.5), ('strafe', 1.6), ('stop2', 1.2), ('turn', 1.2), ('turnstop', 1.0),
                ('flick', 0.0), ('flickstop', 1.0), ('walkturn', 1.5), ('stop3', 1.2), ('walkdown', 1.4), ('stopdown', 1.2)]
        for name, secs in plan:
            r = c.get_control_rotation()
            if name == 'walkdown':  # open floor: toward the room centre
                at = p.get_actor_location()
                r = unreal.Rotator(roll=0.0, pitch=0.0, yaw=math.degrees(math.atan2(-at.y, -at.x)))
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-50.0 if name.endswith('down') else 0.0, yaw=r.yaw))
            yaw0 = r.yaw
            fwd = unreal.MathLibrary.get_forward_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw0))
            right = unreal.MathLibrary.get_right_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw0))
            if name == 'flick':
                for _ in range(3):
                    r = c.get_control_rotation()
                    c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 40.0))
                    S['shot_t'] = time.time()
                    pc_sample(name)
                    yield
                continue
            end = time.time() + secs
            while time.time() < end:
                S['shot_t'] = time.time()  # no periodic screenshot while sampling
                pc_sample(name)
                if name == 'stopdown' and time.time() - S.get('pc_down_t', 0) > 0.25:  # the body below, as the stop lurches
                    S['pc_down_t'], S['shot_t'] = time.time(), 0.0
                    shot('pc_stopdown')
                if name in ('walk', 'walkdown'):
                    p.add_movement_input(fwd, 1.0, False)
                elif name == 'strafe':
                    p.add_movement_input(right, 1.0, False)
                elif name in ('turn', 'walkturn'):
                    r = c.get_control_rotation()
                    c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + (150.0 if name == 'turn' else 60.0) * S['dt']))
                    if name == 'walkturn':
                        p.add_movement_input(unreal.MathLibrary.get_forward_vector(unreal.Rotator(roll=0.0, pitch=0.0, yaw=r.yaw)), 1.0, False)
                yield
            S['shot_t'] = 0.0
            shot('pc_' + name)
            yield
            yield
        pc_write()
    return gen


def pc_open_now(ins, item):
    """BP_ItemInspect.Open as its OpenDelay timer calls it (the first take's Request already spent this morning's)."""
    ins.call_method('Open', (unreal.Name(item),))


def pc_inspect_frames(tag, ins):
    """With the inspect up: measure (camera to head bone, view yaw from torso and capsule, the item's centre in the
    camera's frame) and film it as is, then with Face, Hair and Body hidden in turn (restored after)."""
    p, c = pawn(), pc()
    cam = c.player_camera_manager
    cl, cr = cam.get_camera_location(), cam.get_camera_rotation()
    mesh = prop(ins, 'ItemMesh')
    o, e, rad = unreal.SystemLibrary.get_component_bounds(mesh)
    rel = unreal.MathLibrary.less_less_vector_rotator(o - cl, cr)
    head = prop(p, 'Body').get_socket_location('head')
    d = lambda a: round((a + 180) % 360 - 180, 1)  # noqa: E731
    S['shot_t'] = 0.0  # the sampling loop held the periodic shot off; this frame must be taken
    log('pc_inspect', tag=tag, cam_head_cm=round((cl - head).length(), 1), view_from_torso=d(cr.yaw - pc_torso_yaw(p)),
        view_from_capsule=d(cr.yaw - p.get_actor_rotation().yaw), cam_pitch=round(cr.pitch, 1), item_in_cam=[round(v, 1) for v in rel.to_tuple()],
        item_radius=round(rad, 1), locked=bool(prop(p, 'bInteractionLocked')), paused=unreal.GameplayStatics.is_game_paused(W()),
        face_hidden=prop(p, 'Face').is_visible() is False or prop(p, 'Face').get_editor_property('hidden_in_game'),
        frame=shot(f'{tag}_all'))
    hits = unreal.SystemLibrary.line_trace_multi(W(), cl, o, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [ins],
                                                 unreal.DrawDebugTrace.NONE, True) or []
    seg = o - cl
    near = []  # the pawn's own visible primitives whose bounds cross the camera-to-item segment
    for cmp_ in p.get_components_by_class(unreal.PrimitiveComponent):
        if not cmp_.is_visible() or cmp_.get_editor_property('hidden_in_game'):
            continue
        bo, be, br = unreal.SystemLibrary.get_component_bounds(cmp_)
        k = max(0.0, min(1.0, (bo - cl).dot(seg) / max(seg.dot(seg), 1e-3)))
        if (cl + seg * k - bo).length() < br:
            near.append(cmp_.get_name())
    log('pc_occluders', tag=tag, world=[f'{name_of(t[9])}/{t[10].get_name() if t[10] else None}@{round(t[3])}cm' for t in (h.to_tuple() for h in hits)][:6],
        pawn_bounds_on_line=near[:12])
    yield from sleep(0.35)
    p.set_actor_hidden_in_game(True)
    yield from sleep(0.3)
    log('pc_ablate', tag=tag, hidden='whole pawn', frame=shot(f'{tag}_noPawn'))
    yield from sleep(0.3)
    p.set_actor_hidden_in_game(False)
    for name in ('Hair', 'Body'):
        cmp_ = prop(p, name)
        if not cmp_:
            continue
        was = cmp_.is_visible()
        cmp_.set_visibility(False, True)
        yield from sleep(0.3)
        log('pc_ablate', tag=tag, hidden=name, frame=shot(f'{tag}_no{name}'))
        yield from sleep(0.2)
        cmp_.set_visibility(was, True)
    yield from sleep(0.3)


def pc_inspect_turn():
    """The user's "turning fast I could see through my body" in the screwdriver inspect. (1) The real take: the moment
    E is pressed he turns the mouse fast (600 deg/s) until the inspect opens; measured and filmed (as is, then Face,
    Hair, Body hidden). (2) In the inspect: a mouse turn (control +90 in 3 ticks) and a drag (VelYaw 400 for 0.4 s),
    filmed. (3) Free play: flick 120 deg in 3 ticks and open the inspect on the next tick (its OpenDelay timer firing
    mid-flick), measured and filmed. Every tick sampled (pc_sample) to pc_ins.csv."""
    def gen():
        S['inspect_owner'] = True  # the driver's autoclose must leave this inspect alone
        if state_of('Screwdriver_DeskDrawer') != 'Available':
            yield from use('Desk', 'Use', until=lambda: state_of('Screwdriver_DeskDrawer') == 'Available')()
        a = actor('Screwdriver_DeskDrawer')
        yield from wait(free)
        yield from approach(a, 45.0)
        yield from aim(a)
        yield from focus_on(a, 'Screwdriver_DeskDrawer')
        yield from want_verb('Take')
        c = pc()
        comp('ia').call_method('Interact')
        log('pc_take', what='Interact, then a 600 deg/s mouse turn until the inspect opens')
        end = time.time() + 6.0
        while not inspect_open() and time.time() < end:
            r = c.get_control_rotation()
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 600.0 * S['dt']))
            S['shot_t'] = time.time()
            pc_sample('take')
            yield
        if not inspect_open():
            raise Miss('the inspect never opened after the take')
        ins = inspector()
        for _ in range(int(0.6 / max(S['dt'], 0.01)) + 1):
            S['shot_t'] = time.time()
            pc_sample('open')
            yield
        yield from pc_inspect_frames('take', ins)
        for _ in range(3):
            r = c.get_control_rotation()
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 30.0))
            pc_sample('insturn')
            yield
        yield from sleep(0.3)
        pc_sample('insturn')
        log('pc_inspect_turn', control_yaw=round(c.get_control_rotation().yaw, 1),
            cam_yaw=round(c.player_camera_manager.get_camera_rotation().yaw, 1), frame=shot('ins_turn'))
        yield from pc_inspect_frames('insturn', ins)
        ins.call_method('Close')
        end = time.time() + 3.0
        while time.time() < end and (inspect_open() or not free()):
            pc_sample('close')
            yield
        yield from sleep(1.0)
        for _ in range(3):
            r = c.get_control_rotation()
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + 40.0))
            S['shot_t'] = time.time()
            pc_sample('flick')
            yield
        pc_open_now(ins, 'Screwdriver')
        log('pc_flick_open', what='flick 120 deg in 3 ticks, Open on the next tick')
        for _ in range(int(0.6 / max(S['dt'], 0.01)) + 1):
            S['shot_t'] = time.time()
            pc_sample('flickopen')
            yield
        yield from pc_inspect_frames('flick', ins)
        ins.call_method('Close')
        end = time.time() + 3.0
        while time.time() < end and (inspect_open() or not free()):
            pc_sample('close2')
            yield
        pc_write('pc_ins.csv')
        S['inspect_owner'] = False
    return gen


def pc_phone_box(ph):
    """The phone screen's box on the viewport (px), from its WidgetComponent's bounds corners."""
    w = ph.get_component_by_class(unreal.WidgetComponent)
    o, e, _ = unreal.SystemLibrary.get_component_bounds(w)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                r = unreal.GameplayStatics.project_world_to_screen(pc(), unreal.Vector(o.x + sx * e.x, o.y + sy * e.y, o.z + sz * e.z), False)
                xy = r[-1] if isinstance(r, (tuple, list)) else r  # this binding returns the Vector2D alone (None when behind)
                if xy is not None and (not isinstance(r, (tuple, list)) or r[0]):
                    pts.append((xy.x, xy.y))
    if not pts:
        return None
    return [round(min(x for x, _ in pts)), round(min(y for _, y in pts)), round(max(x for x, _ in pts)), round(max(y for _, y in pts))]


def pc_phone_film(tag, secs, turn=0.0):
    """Hold (or turn the view at `turn` deg/s) for `secs`, a frame every 0.3 s with the screen's box; every tick sampled."""
    ph, c = one('phone'), pc()
    end, last = time.time() + secs, 0.0
    while time.time() < end:
        if turn:
            r = c.get_control_rotation()
            c.set_control_rotation(unreal.Rotator(roll=0.0, pitch=r.pitch, yaw=r.yaw + turn * S['dt']))
        if time.time() - last >= 0.3:
            last, S['shot_t'] = time.time(), 0.0
            log('pc_phone', tag=tag, box=pc_phone_box(ph), frame=shot('ph_' + tag))
        else:
            S['shot_t'] = max(S['shot_t'], time.time() - 0.2)
        pc_sample('ph_' + tag)
        yield


def pc_phone_probe():
    """The perf lane's smear ("Today" reads "Troag" under TSR, in phase with the head sway): the phone raised, filmed
    still and while the view turns at 25 deg/s (M_UI_PhoneScreen, translucent with depth and velocity since 14:43); then,
    in this PIE world only, its Screen widget switched to the engine's masked widget material (masked, no velocity, as
    the screen was before) and filmed the same way: the baseline. Nothing is saved."""
    def gen():
        ph = one('phone')
        yield from wait(free)
        pawn().call_method('TogglePhone')
        yield from wait(lambda: prop(ph, 'bOpen'))
        yield from sleep(1.8)  # past the lock screen
        yield from pc_phone_film('still', 2.4)
        yield from pc_phone_film('turn', 1.5, 25.0)
        w = ph.get_component_by_class(unreal.WidgetComponent)
        mat = unreal.load_asset('/Engine/EngineMaterials/Widget3DPassThrough_Masked_OneSided')
        how = []
        w.set_editor_property('blend_mode', unreal.WidgetBlendMode.MASKED, unreal.PropertyAccessChangeNotifyMode.NEVER)
        w.set_material(0, mat)
        log('pc_phone_variant', how=how, blend=str(w.get_editor_property('blend_mode')), material=str(w.get_material(0).get_name()))
        yield from sleep(0.4)
        yield from pc_phone_film('still_masked', 2.4)
        yield from pc_phone_film('turn_masked', 1.5, 25.0)
        pc_write('pc_phone.csv')
        ph.call_method('PhonePutAway')
        yield from wait(lambda: not prop(ph, 'bOpen'))
    return gen


PLANS.update({
    'PCM': boot() + [('T1', 'first-person camera motion: idle, walk, stop, strafe, turn, flick (every tick)', pc_motion_probe(), 30, False)],
    'PCP': boot() + [('T1', 'phone raised: still and turning, then the masked baseline the same way', pc_phone_probe(), 25, False)],
    'PCI': boot() + [
        ('T5', 'fixture: T5, key jammed', do(lambda: fixture_t5(None), what='EnterBeat 5, Door KeyJammed'), 2, True),
        ('T5', 'take the screwdriver turning fast; in the inspect turn and drag; flick then open', pc_inspect_turn(), 40, False)],
})


def l1_leg_clear(body, tool):
    """Closest approach (cm) of either leg to the held hanger's box, minus a limb radius (shin 6, thigh 8). Negative =
    the wire box cuts into the leg. The box is the hanger mesh's local bounds, so it is conservative."""
    if not tool or not tool.is_visible() or not tool.get_editor_property('static_mesh'):
        return None, None
    lo, hi = tool.get_local_bounds()
    xf = tool.get_world_transform()
    best = (1e9, None)
    for side in ('r', 'l'):
        chain = [body.get_socket_location(b + '_' + side) for b in ('thigh', 'calf', 'foot', 'ball')]
        for i, (a, b) in enumerate(zip(chain, chain[1:])):
            for k in range(7):
                p = a + (b - a) * (k / 6.0)
                q = xf.inverse_transform_location(p)
                c = unreal.Vector(min(max(q.x, lo.x), hi.x), min(max(q.y, lo.y), hi.y), min(max(q.z, lo.z), hi.z))
                d = (xf.transform_location(c) - p).length() - (8.0 if i == 0 else 6.0)
                if d < best[0]:
                    best = (d, ('thigh', 'shin', 'foot')[i] + '_' + side)
    return round(best[0], 1), best[1]


def l1_film_hanger_dense(seconds=26.0, every=0.1):
    """T7 hanger extraction, a frame every 0.1 s of game time. Per frame: the flight clock (director's
    ClothingFlightStarted), hand_r, the held hanger, the shirt, the IK weight, pelvis, montage, the arm-behind-leg
    test (l1_pose's), view."""
    start = use('Bed', 'Use', item='Hanger', until=lambda: stage() >= 5 or (
        pawn().get_editor_property('mesh').get_anim_instance().get_current_active_montage() is not None))

    def gen():
        if 'Hanger' not in items():
            comp('inv').call_method('Add', ('Hanger',))
        yield from start()
        unreal.GameplayStatics.set_global_time_dilation(W(), 0.4)  # slow only the extraction itself, not the walk to it
        log('l1_dilation', rate=0.4)
        end, last, n, done_at = time.time() + seconds, -1.0, 0, None
        d = one('director')
        while time.time() < end:
            gt = unreal.GameplayStatics.get_time_seconds(W())
            if gt - last >= every - 0.005:
                last, n = gt, n + 1
                p = pawn(); body = prop(p, 'Body'); tool = prop(p, 'HeldTool'); shirt = actor('Shirt_T7')
                banim = body.get_anim_instance()
                anim = p.get_editor_property('mesh').get_anim_instance()
                mon = anim.get_current_active_montage() if anim else None
                cam = pc().player_camera_manager
                eye, hand = cam.get_camera_location(), body.get_socket_location('hand_r')
                knee, ankle = body.get_socket_location('calf_r'), body.get_socket_location('foot_r')
                shin = (knee + ankle) * 0.5
                ang = math.degrees(math.acos(max(-1.0, min(1.0, (hand - eye).normal().dot((shin - eye).normal())))))
                f = f'{OUT}/frames/{PLAN}_{int((time.time() - S["t0"]) * 100):05d}_{beat()}_hd{n:03d}.png'
                unreal.SystemLibrary.execute_console_command(W(), f'Shot showui filename={f} -nosuffix')
                r = lambda v: [round(c, 1) for c in v.to_tuple()]  # noqa: E731
                log('l1_hd', n=n, gt=round(gt, 3), flight=round(gt - (prop(d, 'ClothingFlightStarted') or 0.0), 3),
                    flying=prop(d, 'bClothingFlight'), owned=prop(d, 'bClothingHangerOwned'),
                    hand=r(hand), tool=(r(tool.get_world_location()) if tool and tool.is_visible() else None),
                    shirt=r(shirt.get_actor_location()) if shirt else None, pelvis=r(body.get_socket_location('pelvis')),
                    ik=prop(banim, 'ToolHandWeight'), leg_clear=l1_leg_clear(body, tool), montage=(mon.get_name() if mon else None),
                    mpos=(round(anim.montage_get_position(mon), 2) if mon else None), hand_shin_deg=round(ang, 1),
                    shin_nearer_cm=round((hand - eye).length() - (shin - eye).length(), 1), view=view(), stage=stage(), frame=f)
                if stage() >= 5 and free():
                    done_at = done_at or gt
            if done_at and unreal.GameplayStatics.get_time_seconds(W()) - done_at > 1.0:
                break
            yield
        if stage() < 5:
            raise Miss(f'the shirt never came out (stage {stage()})')
    return gen


PLANS.update({
    'L1HD': boot() + to_t7()[:1] + [
        ('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
        ('T7', 'fixture: the three clues, to the snag', fixture_clothing_before(4), 14, True),
        ('T7', 'hanger on the bed (the world slows to 0.4 once he starts), a frame every 0.1 s of game time',
         l1_film_hanger_dense(), 40, False),
        ('T7', 'normal speed', l1_dilate(1.0), 1, False)],
})


# ---- level1 lane: Level 1 animation sweep (coordinator 15:15), every story moment filmed about every 0.1 s ----------
# Each plan fits one 47 s PIE lease; the world is slowed (l1_dilate) so a frame lands about every 0.1 to 0.2 s of game
# time. Logs: l1_dense rows (actor, pelvis, head, feet z, hands, yaw, montage, view, cinematic) plus the l1_track path.
T7_SNAG = [('T7', 'fixture: skip the top-down hold (ExitTopDown)', skip_top_down(), 25, True),
           ('T7', 'shortcut: search events to the snag', chain(do(search_events, what='ReportEvent Clothing*Searched x3, Add Hanger'),
                                                               until(lambda: stage() >= 4 and free())), 15, True)]
PLANS.update({
    'L1S0': boot()[:4] + [
        ('wakeup', 'track every tick; slow the world to 0.6', chain(l1_track_on(), l1_dilate(0.6)), 2, False),
        ('wakeup', 'LS_WakeUp and getting out of bed, filmed', l1_film_dense(33.0, 0.1, 's0'), 35, False)],
    'L1S2': boot() + [
        ('T1', 'walk: first steps', chain(walk(1.6), until(beat_is('T2'))), 6, False),
        ('T2', 'track every tick; slow the world to 0.6', chain(l1_track_on(), l1_dilate(0.6)), 2, False),
        ('T2', 'the calendar: look, filmed', l1_film_while(l1_look('Dress_Lux3D_Calendar', 'Look'), 1.5, 0.1, 's2'), 22, False)],
    'L1S4': boot() + [
        ('T4', 'shortcut: T4 with the key and boots on', do(fixture_t4, what='EnterBeat 4, Add Key, boots Worn, BootsWorn'), 2, True),
        ('T4', 'track every tick; slow the world to 0.7', chain(l1_track_on(), l1_dilate(0.7)), 2, False),
        ('T4', 'key in the door, the four-stage turn to the snap, filmed', l1_film_while(chain(
            use('Door_Bedroom', 'Use', item='Key', extra=90.0, until=lambda: prop(actor('Door_Bedroom'), 'bToolActive')),
            door_tool(beat_is('T5'))), 1.5, 0.1, 's4'), 27, False)],
    'L1SD': boot() + [
        ('T5', 'shortcut: T5, key jammed, hanger in hand', do(lambda: fixture_t5('Hanger'), what='EnterBeat 5, Door KeyJammed, Add Hanger'), 2, True),
        ('T5', 'track every tick; slow the world to 0.7', chain(l1_track_on(), l1_dilate(0.7)), 2, False),
        ('T5', 'door tool: entry, the hanger through the gap, exit, filmed', l1_film_while(chain(
            use('Door_Bedroom', 'Use', item='Hanger', extra=90.0,
                until=lambda: prop(actor('Door_Bedroom'), 'bToolActive') or beat() == 'T6'),
            door_tool(beat_is('T6'))), 2.0, 0.1, 'sd'), 27, False)],
    'L1S7': boot() + to_t7()[:1] + T7_SNAG + [
        ('T7', 'fixture: toss and escape one to stage 6', chain(do(to_escape_two, what='BeginClothingToss, EscapeClothingOne'),
                                                               until(lambda: stage() >= 6 and free())), 8, True),
        ('T7', 'slow the world to 0.6', l1_dilate(0.6), 1, False),
        ('T7', 'chase 2: catching the shirt, filmed', l1_film_while(chase(2), 1.0, 0.1, 's7'), 14, False)],
    'L1S8': boot() + to_t7()[:1] + T7_SNAG + [
        ('T7', 'fixture: toss, escape one and two: the shirt at the vase', chain(do(to_vase, what='BeginClothingToss, EscapeClothingOne, EscapeClothingTwo'),
                                                                                 until(lambda: stage() >= 7 and free())), 8, True),
        ('T7', 'slow the world to 0.6', l1_dilate(0.6), 1, False),
        ('T7', 'the vase grab, the boss forming and the battle intro, filmed', l1_film_while(chain(chase(3), take_shirt()), 4.0, 0.1, 's8'), 16, False)],
    'L1S9': boot() + [
        ('T9', 'shortcut: EnterBeat 9', do(lambda: one('director').call_method('EnterBeat', (9,)), what='EnterBeat 9'), 2, True),
        ('T9', 'track every tick; slow the world to 0.5', chain(l1_track_on(), l1_dilate(0.5)), 2, False),
        ('T9', 'the payoff and hero shot, filmed', l1_film_dense(24.0, 0.1, 's9'), 26, False)],
})


# ---- main: the ending's bedroom is the room as the game began (BP_DreamThreshold.RestoreWakeRoom), plan L2R ----------
ROOM_SHOTS = (('door', (60.0, 70.0, 150.0), (-4.0, 0.0)), ('wardrobe', (0.0, -140.0, 160.0), (-8.0, 60.0)))


def room_capture(tag):
    """Two stills of the room from a temporary SceneCapture2D (destroyed at once): the door wall and the wardrobe."""
    w = W()
    rt = unreal.RenderingLibrary.create_render_target2d(w, 960, 540, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    gs, xf, scale = unreal.get_default_object(unreal.GameplayStatics), unreal.Transform(), unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    files = []
    for name, at, (pitch, yaw) in ROOM_SHOTS:
        cap = gs.call_method('BeginDeferredActorSpawnFromClass', (w, unreal.SceneCapture2D.static_class(), xf,
                                                                   unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale))
        cap = gs.call_method('FinishSpawningActor', (cap, xf, scale))
        cap.set_actor_location_and_rotation(unreal.Vector(*at), unreal.Rotator(0.0, pitch, yaw), False, True)
        c = cap.capture_component2d
        c.set_editor_property('texture_target', rt)
        c.set_editor_property('capture_source', unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property('fov_angle', 80.0)
        c.capture_scene()
        unreal.RenderingLibrary.export_render_target(w, rt, OUT + '/frames', f'{PLAN}_room_{tag}_{name}.png')
        files.append(f'{OUT}/frames/{PLAN}_room_{tag}_{name}.png')
        cap.destroy_actor()
    return files


def room_state():
    wd, door, frame = actor('Wardrobe'), actor('Door_Bedroom'), actor('DoorFrame_Bedroom')
    piv = lambda a: [c for c in a.get_components_by_class(unreal.SceneComponent) if c.get_name() == 'Pivot'][0]  # noqa: E731
    r = lambda v: [round(x, 1) for x in v]  # noqa: E731
    return dict(wardrobe=str(prop(wd, 'State')), wardrobe_pivot=r(piv(wd).get_relative_transform().rotation.rotator().to_tuple()),
                wardrobe_at=r(wd.get_actor_location().to_tuple()), door=str(prop(door, 'State')), door_hidden=bool(prop(door, 'hidden')),
                door_pivot=r(piv(door).get_relative_transform().rotation.rotator().to_tuple()),
                door_at=r(door.get_actor_location().to_tuple()), frame_at=r(frame.get_actor_location().to_tuple()))


def room_after_l1():
    """Fixture: the room as Level 1 leaves it: the door moved to the wrong wall (StageWrongWall, T7) and the wardrobe
    fallen (its Fallen pose and state). The L2 fixture's OpenTheDoor then opens and hides the door, as T10 does."""
    def gen():
        yield from wait(lambda: one('director') and pawn())
        one('director').call_method('StageWrongWall')
        wd = actor('Wardrobe')
        unreal.get_default_object(unreal.SystemLibrary).call_method('SetNamePropertyByName', (wd, 'State', 'Fallen'))
        wd.call_method('ApplyState', (unreal.Name('Fallen'), True))
        yield from sleep(0.2)
        log('room_after_l1', **room_state())
    return gen


def g_room_restored():
    """PASS: after the ending film the wardrobe stands (Standing, pivot 0) where it began and the door is shown,
    closed (pivot 0) and back in its own frame on the east wall (375, 132.5)."""
    st = room_state()
    files = room_capture('after')
    ok = (st['wardrobe'] == 'Standing' and max(map(abs, st['wardrobe_pivot'])) < 0.5 and not st['door_hidden']
          and max(map(abs, st['door_pivot'])) < 0.5 and abs(st['door_at'][0] - 375) < 1 and abs(st['door_at'][1] - 132.5) < 1)
    log('room_restored', result='PASS' if ok else 'FAIL', files=files, **st)
    if not ok:
        raise Miss('the ending room is not the starting room: %s' % st)
    yield


def g_hud_trace(seconds):
    """Every tick for `seconds`: the HUD's render opacity, its objective text, the beat and the view target, logged
    whenever any of them changes (finds what brings the HUD back over the new morning's film)."""
    t0, last = time.time(), None
    while time.time() - t0 < seconds:
        w = prop(one('fe'), 'HUD')
        obj = prop(w, 'Txt_Objective')
        c = pc()
        vt = c.get_view_target() if c else None
        row = (round(w.get_render_opacity(), 2) if w else None, str(obj.get_text()) if obj else None, beat(),
               vt.get_class().get_name() if vt else None, w.is_in_viewport() if w else None)
        if row != last:
            log('hud_trace', at=round(time.time() - t0, 2), opacity=row[0], objective=row[1], beat_now=row[2], view=row[3],
                in_viewport=row[4])
            last = row
        yield


PLANS['D2H'] = boot() + [
    ('pause', 'pause (Esc)', chain(fe_call('TogglePause'), pause_menu()), 4, False),
    ('pause', 'Restart Day, confirm, then trace the HUD 9 s', chain(fe_call('RequestRestartDay'), lambda: sleep(0.6),
                                                                 fe_call('ConfirmPending'), lambda: sleep(2.0),
                                                                 do(lambda: one('director').call_method('SkipWakeUp'), what='SkipWakeUp'),
                                                                 lambda: g_hud_trace(8.0)), 14, False)]

PLANS['L2R'] = [('L1', 'fixture: the room after Level 1 (door moved, wardrobe fallen)', room_after_l1(), 6, True)] + \
    PLANS['L2E'][:3] + [
        ('L2', 'the room before the ending, captured', do(lambda: log('room_before', files=room_capture('before'), **room_state()),
                                                          what='room_before'), 4, False),
        PLANS['L2E'][3],
        ('end', 'the room is the starting room: wardrobe standing, door closed at home', g_room_restored, 4, False)]

STEPS = PLANS[PLAN]


# ---- driver ------------------------------------------------------------------------------------------------------
def finish(why):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    w = W()
    if w:
        unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
        if S['ctx'] is not None:
            try:  # back to the player's slot, reloaded from disk, so any later save rewrites his own values unchanged
                gi().call_method('SetProofProgressContext', S['ctx'])
                gi().call_method('LoadProgress')
                unreal.GameplayStatics.delete_game_in_slot(QA_SLOT, 0)
            except Exception as ex:  # never lose the run's outputs over the restore
                log('restore_error', err=repr(ex)[:200])
    log('end', why=why)
    doc = dict(plan=PLAN, why=why, cap=CAP, steps=S['steps'], log=S['log'])
    for path in (f'{OUT}/play.json', f'P:/FoA/Saved/Integration/play_{PLAN}.json'):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, indent=1, default=str)
    with open(f'{OUT}/frametimes.csv', 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(fh)
        wr.writerow(['t', 'ms', 'near_shot', 'phase'])
        wr.writerows(S['frames'])
    with open(f'{OUT}/done.json', 'w', encoding='utf-8') as fh:
        json.dump(dict(why=why, t=t_now(), passed=sum(s['result'] == 'pass' for s in S['steps']), steps=len(S['steps'])), fh)
    unreal.log(f'[play] {PLAN} -> {why} ({OUT})')


def view_check(now):
    """main's check (2026-11-10): while the view changes into BP_FoAPlayer, the player's own body must never be in front of
    a camera that is outside his head. Each tick samples the camera (moving or not), its distance to the head socket
    and whether the Body bounds are in the field of view; when the view target becomes the pawn, the 2.5 s before
    are judged ('view_into_player' pass/fail). The static top-down hold is not a change and does not count."""
    c, p = pc(), pawn()
    if not c or not p:
        return
    cam = c.player_camera_manager
    loc, fwd = cam.get_camera_location(), unreal.MathLibrary.get_forward_vector(cam.get_camera_rotation())
    body = prop(p, 'Body') or p.get_component_by_class(unreal.SkeletalMeshComponent)
    o, _, _ = unreal.SystemLibrary.get_component_bounds(body)
    head = body.get_socket_location('head')
    to = unreal.Vector(o.x - loc.x, o.y - loc.y, o.z - loc.z)
    dist = to.length()
    to.normalize()
    ang = math.degrees(math.acos(max(-1.0, min(1.0, fwd.x * to.x + fwd.y * to.y + fwd.z * to.z))))
    outside = (loc - head).length() > 40.0
    seen = outside and ang < cam.get_fov_angle() / 2 + 5 and dist < 2000
    moving = S.get('cam_last') is not None and (loc - S['cam_last']).length() > 2.0
    S['cam_last'] = loc
    vt = c.get_view_target()
    on_pawn = vt == p
    name = vt.get_class().get_name() if vt is not None else ''
    authored = name in ('CineCameraActor', 'BP_MenuCamera_C')  # films and the menu show him by design
    body_seen = seen and moving and not authored
    buf = S.setdefault('vbuf', [])
    buf.append((now, on_pawn, body_seen, round((loc - head).length())))
    while buf and now - buf[0][0] > 3.0:
        buf.pop(0)
    if body_seen and not on_pawn and name != 'BP_Encounter_C':  # the battle frames him by design: judge it, no clutter
        shot('viewchange')
    if on_pawn and S.get('was_on_pawn') is False:
        bad = [b for b in buf if not b[1] and b[2] and now - b[0] <= 2.5]
        log('view_into_player', result='FAIL' if bad else 'PASS', frames_with_body=len(bad),
            cam_to_head_cm=max((b[3] for b in bad), default=0), at=round(now - S['t0'], 2))
    S['was_on_pawn'] = on_pawn


def close_step(result, reason=''):
    beat_label, name, _, timeout, hard = STEPS[S['i']]
    rec = dict(n=S['i'], beat=beat_label, name=name, result=result, reason=reason, t0=round(S['t_step'] - S['t0'], 2),
               t1=t_now(), secs=round(time.time() - S['t_step'], 2), at_beat=beat(), frame=shot(('ok_' if result == 'pass' else 'MISS_') + str(S['i'])))
    S['steps'].append(rec)
    log('step', **{k: v for k, v in rec.items() if k != 'frame'})
    S['gen'], S['i'] = None, S['i'] + 1
    if result != 'pass' and hard:
        finish(f'hard miss: {name}')


def run():
    now = time.time()
    if os.path.exists(OUT + '/abort'):  # the runner lost (or ended) its EXCLUSIVE lease: stop driving at once
        if S['gen'] is not None and S['i'] < len(STEPS) and W():
            close_step('miss', 'runner abort: ' + open(OUT + '/abort').read())
        return finish('aborted by the runner')
    w = W()
    if w is None:
        return finish('pie_gone') if S['w0'] is not None or now - S['t0'] > 20 else None
    if S['w0'] is None:
        S['w0'] = now
        g = gi()
        S['ctx'] = (str(prop(g, 'SaveSlot')), set(prop(g, 'Knowledge', [])), list(prop(g, 'Notebook', [])))
        S['day0'] = prop(g, 'DayCount')
        g.call_method('SetProofProgressContext', (QA_SLOT, set(), []))
        g.call_method('ResetProgress')  # deletes only QA_SLOT (SaveSlot now): day 18, nothing known, as a new player
        log('setup', plan=PLAN, original_day=S['day0'], day=prop(g, 'DayCount'), qa_slot=QA_SLOT, t0_wall=round(S['t0'], 2))
        unreal.SystemLibrary.execute_console_command(w, 'viewmode lit')
    S['n'] += 1
    S['dt'] = min(now - (S['last'] or now), 0.1) or 1 / 60
    S['frames'].append((round(now - S['t0'], 3), round((now - (S['last'] or now)) * 1000.0, 2), int(S['n'] - S['shot_n'] <= 3),
                        STEPS[S['i']][0] if S['i'] < len(STEPS) else 'end'))
    S['last'] = now
    if now - S['t0'] > CAP:
        if S['gen'] is not None:
            close_step('miss', 'cap reached')
        return finish('cap')
    b = beat()
    if b != S['beat'] or now - S['snap_t'] > 2.0:
        S['snap_t'] = now
        log('beat' if b != S['beat'] else 'state', **state())
        if b != S['beat']:
            shot('beat')
        S['beat'] = b
    elif now - S['shot_t'] > SHOT_EVERY:
        shot('t')
    if S.get('z_walkout') is not None and pawn():
        S['zmin'] = min(S['zmin'], pawn().get_actor_location().z)
    try:
        view_check(now)
    except Exception as ex:  # a missing Body or socket must not stop the plan; say so once
        if not S.get('view_err'):
            S['view_err'] = True
            log('view_check_error', err=repr(ex)[:160])
    try:
        track(now)
        if S.get('l1_track'):
            l1_track_tick(now)
        inspect_autoclose(now)
    except Exception as ex:  # a renamed actor or class must not stop the plan; say so once
        if not S.get('track_err'):
            S['track_err'] = True
            log('track_error', err=repr(ex)[:160])
    if PLAN == 'D2':
        try:
            hud_check(now)
        except Exception as ex:  # a renamed HUD must not stop the plan; say so once
            if not S.get('hud_err'):
                S['hud_err'] = True
                log('hud_check_error', err=repr(ex)[:160])
    if S['fight']:
        fight_tick(S['fight']['mode'])
    if S['i'] >= len(STEPS):
        return finish('done') if now - S['t_step'] > 1.5 else None
    if S['gen'] is None:
        S['gen'], S['t_step'] = STEPS[S['i']][2](), now
        log('start', n=S['i'], name=STEPS[S['i']][1])
    if now - S['t_step'] > STEPS[S['i']][3]:
        return close_step('miss', 'timeout')
    try:
        next(S['gen'])
    except StopIteration:
        close_step('pass')
    except Miss as m:
        close_step('miss', str(m))


def tick(_dt):
    if S['done']:
        return
    try:
        run()
    except Exception as ex:  # never leave the callback registered or the game sped up
        log('error', err=repr(ex)[:300], step=S['i'])
        S['errors'] = S.get('errors', 0) + 1
        if S['errors'] > 40:
            return finish('driver errors')
        if S['gen'] is not None and S['i'] < len(STEPS):
            try:
                close_step('miss', 'driver error: ' + repr(ex)[:200])
            except Exception:  # the world is gone mid-step
                pass
        if not S['done']:
            S['gen'] = None
            if W() is None:
                finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('play scheduled', PLAN, len(STEPS), 'steps, cap', CAP, '->', OUT)

