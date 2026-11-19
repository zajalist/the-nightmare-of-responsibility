"""PIE proof driver for BP_SandAmbience (world lane). Runs inside a PIE burst from a Slate post-tick callback, bounded
by WA_CAP seconds; started by Tools/Splats/pie_ambience.sh <plan> (EXCLUSIVE, in a PIE window).
  amb    boot -> T3 -> creep, pile, trickle, grains in the beam, clock leak (each forced through its real Ev_* function)
  fore   boot -> T3 -> sleeve, shirt imprint, hourglass, Nightmare glimpse, suit
  live   boot -> T3 -> stand still (feet bloom), the lock close-up, then the director left alone (natural events)
Each event: call Ev_X until its part plays (its own gates and chance), frame the part from the player's third-person
camera (pawn teleported nearby, control rotation set), take a 'Shot showui' every 0.4 s, hide the part. Log ->
Saved/WorldShots/pie_<plan>.json (shots with event names, the viewport rect, ambience state)."""
import json
import math
import os
import time

import unreal

PLAN = os.environ.get('WA_PLAN', 'amb')
CAP = float(os.environ.get('WA_CAP', '50'))
SHOTS = os.environ.get('WA_SHOTS', '1')
SKIP_STORY = os.environ.get('WA_SKIP_STORY') == '1'
assert SHOTS in ('0', '1'), 'WA_SHOTS must be 0 or 1'
OUT = f'P:/FoA/Saved/WorldShots/pie_{PLAN}.json'
G = '/Game/FoA/Gameplay/'
S = dict(t0=time.time(), log=[], i=0, mark=time.time(), shot=0.0, done=False, h=None, tag='boot', vp=None, n=0, tries=0)


def W():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def one(w, path):
    return unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))


def director(w):
    return one(w, G + 'BP_BeatDirector.BP_BeatDirector_C')


def frontend(w):
    return one(w, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')


def amb(w):
    return one(w, G + 'Ambient/BP_SandAmbience.BP_SandAmbience_C')


def beat(w):
    d = director(w)
    b = d.get_editor_property('Beat') if d else None
    return str(b.get_editor_property('Id')) if b else None


def log(kind, **kw):
    S['log'].append(dict(t=round(time.time() - S['t0'], 2), kind=kind, **kw))


def finish(why):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    log('end', why=why)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(S['log'], fh, indent=1, default=str)
    unreal.log(f'[world] {PLAN} -> {why} ({OUT})')


def viewport_rect(w):
    geo = unreal.WidgetLayoutLibrary.get_viewport_widget_geometry(w)
    pos = unreal.SlateLibrary.local_to_absolute(geo, unreal.Vector2D(0, 0))
    size = unreal.SlateLibrary.get_absolute_size(geo)
    return [round(pos.x), round(pos.y), round(size.x), round(size.y)]


def frame(w, target, dist, side=90.0, up=60.0):
    """Teleport the pawn dist cm short of target (coming from the room centre) and `side` cm to its right, then aim
    the third-person camera (spring arm length behind the pawn) at the target, so the player stands beside the event
    instead of in front of it."""
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    t = target
    fx, fy = t.x - 0.0, t.y + 45.0
    n = max(math.hypot(fx, fy), 1.0)
    fx, fy = fx / n, fy / n
    rx, ry = -fy, fx
    stand = unreal.Vector(t.x - fx * dist + rx * side, t.y - fy * dist + ry * side, p.get_actor_location().z)
    p.teleport(stand, unreal.Rotator(0, 0, 0))
    arm = p.get_component_by_class(unreal.SpringArmComponent)
    L = arm.get_editor_property('target_arm_length') if arm else 250.0
    cam = unreal.Vector(stand.x - fx * L, stand.y - fy * L, stand.z + up)
    look = unreal.MathLibrary.find_look_at_rotation(cam, t)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(roll=0.0, pitch=look.pitch, yaw=look.yaw))
    p.set_actor_rotation(unreal.Rotator(0, look.yaw, 0), False)


def hidden(a):
    return bool(a.get_editor_property('hidden'))


def state(w):
    a = amb(w)
    gi = unreal.GameplayStatics.get_game_instance(w)
    act = a.get_editor_property('Active') if a else None
    nm = one(w, '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C')
    return dict(beat=beat(w), ambient_beat=a.get_editor_property('Beat') if a else None,
                day=gi.get_editor_property('DayCount') if gi else None,
                level=round(a.get_editor_property('Level'), 2) if a else None,
                days=a.get_editor_property('Days') if a else None, still=a.get_editor_property('StillTime') if a else None,
                active=act.get_name() if act else None, active_vis=act.is_visible() if act else None,
                absorbing=a.get_editor_property('bAbsorbing') if a else None,
                nightmare_hidden=hidden(nm) if nm else None,
                view=unreal.GameplayStatics.get_player_controller(w, 0).get_view_target().get_class().get_name())


def view_on(w, target, dist, h, fov=60.0):
    """Shoot the event through the player's own camera, parked: the pawn is hidden and frozen and its spring arm
    shortened to zero, so the game camera sits dist cm from target (toward the room centre), h cm up. Python cannot
    spawn into the PIE world, and this keeps the frame the real game viewport with the full post-process."""
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    arm = p.get_component_by_class(unreal.SpringArmComponent)
    cam = p.get_component_by_class(unreal.CameraComponent)
    if 'arm0' not in S:
        S['arm0'] = (arm.get_editor_property('target_arm_length'), arm.get_editor_property('socket_offset'),
                     arm.get_editor_property('target_offset'), arm.get_editor_property('do_collision_test'),
                     cam.get_editor_property('field_of_view'), p.get_actor_location())
        p.set_actor_hidden_in_game(True)
        p.get_component_by_class(unreal.CharacterMovementComponent).set_movement_mode(unreal.MovementMode.MOVE_NONE)
        for k, v in (('target_arm_length', 0.0), ('socket_offset', unreal.Vector(0, 0, 0)), ('target_offset', unreal.Vector(0, 0, 0)),
                     ('do_collision_test', False), ('enable_camera_lag', False), ('enable_camera_rotation_lag', False)):
            arm.set_editor_property(k, v)
    fx, fy = -target.x, -45.0 - target.y
    n = max(math.hypot(fx, fy), 1.0)
    c = unreal.Vector(target.x + fx / n * dist, target.y + fy / n * dist, h)
    pivot = arm.get_world_location() - p.get_actor_location()
    p.set_actor_location(c - pivot, False, True)
    cam.set_editor_property('field_of_view', fov)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(c, target))
    S['aim'] = (c, target)


def keep_aim(w):
    """Every tick while parked: move the pawn by however far the real camera (read back from the camera manager)
    is from the wanted spot, and look at the target from where the camera really is. Cancels the camera
    component's own offsets and any push-out, whatever they are."""
    if 'aim' not in S or 'arm0' not in S:
        return
    c, target = S['aim']
    pcm = unreal.GameplayStatics.get_player_camera_manager(w, 0)
    got = pcm.get_camera_location()
    err = c - got
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    if err.length() > 2.0:
        p.set_actor_location(p.get_actor_location() + err, False, True)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(got, target))
    S['aim_err'] = round(err.length(), 1)
    S['aim_pitch'] = (round(pcm.get_camera_rotation().pitch, 1), round(unreal.MathLibrary.find_look_at_rotation(got, target).pitch, 1))


def own_view(w):
    """Back to the ordinary third-person camera and a walking, visible player."""
    S.pop('aim', None)
    if 'arm0' not in S:
        return
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    arm = p.get_component_by_class(unreal.SpringArmComponent)
    L, so, to, col, fov, home = S.pop('arm0')
    for k, v in (('target_arm_length', L), ('socket_offset', so), ('target_offset', to), ('do_collision_test', col)):
        arm.set_editor_property(k, v)
    p.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', fov)
    p.set_actor_location(home, False, True)
    p.set_actor_hidden_in_game(False)
    p.get_component_by_class(unreal.CharacterMovementComponent).set_movement_mode(unreal.MovementMode.MOVE_WALKING)


def no_absorb(w):
    """Forced shots park the player for seconds at a time: stop the stand-still watcher so its feet bloom stays out."""
    unreal.SystemLibrary.clear_timer(amb(w), 'WatchStill')


def force(fn, part, dist, yaw_off=25.0, up=60.0, aim_z=10.0, fov=60.0, where=None):
    """Call Ev_<fn> (its own gates) until the part named `part` is the active one, then frame it."""
    def act(w):
        a = amb(w)
        for _ in range(12):
            a.call_method(fn, ())
            act_c = a.get_editor_property('Active')
            if act_c and act_c.get_name() == part and act_c.is_visible() and (where is None or where(act_c.get_world_location())):
                break
        act_c = a.get_editor_property('Active')
        ok = bool(act_c and act_c.get_name() == part and act_c.is_visible()
                  and (where is None or where(act_c.get_world_location())))
        a.call_method('Rearm', (200.0,))           # the forced run owns the timing: no Step in between
        log('event', fn=fn, played=ok, **state(w))
        if ok:
            loc = act_c.get_world_location()
            view_on(w, unreal.Vector(loc.x, loc.y, loc.z + aim_z), dist, up, fov)
        S['tag'] = 'gap'
        S['next_tag'] = fn
    return act


def settle(w):
    S['tag'] = S.pop('next_tag', S['tag'])


def hide(w):
    a = amb(w)
    act_c = a.get_editor_property('Active')
    if act_c:
        act_c.set_visibility(False)
    S['tag'] = 'gap'


def glimpse_face(w):
    """Keep the bay site at the view edge without the spring arm orbiting when the camera turns."""
    target = unreal.Vector(-115.0, -345.0, 92.0)
    view_on(w, target, 250.0, 150.0, 90.0)
    c, _ = S['aim']
    d = target - c
    a = math.radians(38.0)
    look = unreal.Vector(d.x * math.cos(a) - d.y * math.sin(a),
                         d.x * math.sin(a) + d.y * math.cos(a), d.z)
    dot = (d.x * look.x + d.y * look.y + d.z * look.z) / (d.length() * look.length())
    assert 0.35 <= dot <= 0.82, dot
    S['aim'] = (c, c + look)


def glimpse(w):
    """Draw Ev_Glimpse (its own gates: beat window, chance, edge-of-view test) until the Nightmare shows."""
    a = amb(w)
    nm = one(w, '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C')
    for _ in range(30):
        a.call_method('Ev_Glimpse', ())
        if nm and not hidden(nm):
            break
    a.call_method('Rearm', (200.0,))
    log('event', fn='Ev_Glimpse', played=bool(nm and not hidden(nm)), at=str(nm.get_actor_location()) if nm else None, **state(w))
    S['tag'] = 'Ev_Glimpse'


def no_nightmare(w):
    """The T1->T4 shortcut skips T2's hook that sends the T1 corner Nightmare away: do what that hook does."""
    nm = one(w, '/Game/FoA/Characters/Player/BP_Nightmare.BP_Nightmare_C')
    if nm and not hidden(nm):
        nm.call_method('Vanish', ())
    log('nightmare_vanish', hidden=hidden(nm) if nm else None)


def clock(w):
    return one(w, '/Game/FoA/VFX/Sand/BP_SandMaterialize.BP_SandMaterialize_C')


def clock_reset(w):
    """After the skipped wake-up the clock is already sand (DissolveAmount kept at 1): put it back whole, no pile."""
    c = clock(w)
    c.call_method('SetDissolveAmount', (0.0,))
    log('clock_reset', pile=c.get_editor_property('bPileShown'))


def clock_ring(on):
    def act(w):
        clock(w).call_method('SetRing', (1.0 if on else 0.0,))
        log('clock_ring', on=on)
    return act


def clock_slap(w):
    """What LS_WakeUp keys at the contact: Ring to 0 and DissolveAmount 0 -> 1 over 1.2 s (ramped in tick())."""
    clock(w).call_method('SetRing', (0.0,))
    S['ramp'] = time.time()
    log('clock_slap')


def clock_persisted(w):
    c = clock(w)
    pile = c.get_editor_property('Pile')
    scale = pile.get_world_scale()
    assert c.get_editor_property('DissolveAmount') >= 0.99
    assert pile.is_visible() and 0.1 < scale.x < 0.2, (pile.is_visible(), scale)
    log('clock_persisted', visible=True, world_scale=[scale.x, scale.y, scale.z])
    own_view(w)


def ramp_tick(w):
    if 'ramp' in S:
        v = min((time.time() - S['ramp']) / 1.2, 1.0)
        clock(w).call_method('SetDissolveAmount', (max(v, 0.001),))
        if v >= 1.0:
            S.pop('ramp')
            log('clock_dissolved', pile=clock(w).get_editor_property('bPileShown'))


def film_tick(w):
    """Observe LS_WakeUp without supplying missing sequence keys; shots from 17 s to 31 s."""
    if 'film0' not in S:
        return
    t = time.time() - S['film0']
    c = clock(w)
    ring = c.get_editor_property('Ring')
    S['tag'] = 'Wake' if 17.0 <= t <= 31.0 else 'gap'
    if int(t * 2) != S.get('film_log'):
        S['film_log'] = int(t * 2)
        camera = unreal.GameplayStatics.get_player_camera_manager(w, 0)
        controller = unreal.GameplayStatics.get_player_controller(w, 0)
        target = controller.get_view_target()
        pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
        source_anim = pawn.get_editor_property('Mesh').get_anim_instance()
        log('film', at=round(t, 2), ring=round(ring, 2), dissolve=round(c.get_editor_property('DissolveAmount'), 2),
            wake_done=director(w).get_editor_property('bWakeDone'), beat_index=director(w).get_editor_property('BeatIndex'),
            move_ignored=controller.is_move_input_ignored(),
            source_anim=source_anim.get_class().get_name() if source_anim else None,
            camera_location=str(camera.get_camera_location()), camera_rotation=str(camera.get_camera_rotation()),
            view_target=target.get_name(), view_target_transform=str(target.get_actor_transform()),
            pile=c.get_editor_property('bPileShown'),
            pile_visible=c.get_editor_property('Pile').is_visible(),
            pile_scale=str(c.get_editor_property('Pile').get_world_scale()))


def film_start(w):
    S['film0'] = time.time()
    S['vp'] = viewport_rect(w)


def to_beat(w):
    d = director(w)
    d.call_method('ReportEvent', ('KeyTaken',))   # a T3 event: skips ahead like a returning player's shortcut
    amb(w).call_method('Rearm', (200.0,))


def boot_ready(w):
    a = amb(w)
    a.call_method('UpdateState', ())  # Rearm suppresses the normal Step that refreshes the cached beat.
    assert a.get_editor_property('Beat') == director(w).get_editor_property('BeatIndex')
    S['vp'] = viewport_rect(w)
    log('vp', vp=S['vp'], **state(w))


def boot():
    return [(0.3, lambda w: unreal.SystemLibrary.execute_console_command(w, 'viewmode lit'), None, 0),
            (0.3, lambda w: frontend(w).call_method('OnSplashFinished', ()), None, 0),
            (0.6, lambda w: frontend(w).call_method('OnTitleConfirmed', ()), None, 0),
            (0.8, lambda w: frontend(w).call_method('WakeUp', ()), 'film', 12),
            (1.0, lambda w: director(w).call_method('SkipWakeUp', ()), 'T1', 5),
            (0.5, to_beat, 'T4', 4),
            (0.8, boot_ready, None, 0)]


def wait(sec):
    return (sec, None, None, 0)


PLANS = {  # force(fn, part, camera distance from the part, -, camera height, aim height offset, fov)
    'amb': boot() + [(0.0, no_absorb, None, 0), (0.2, force('Ev_Creep', 'Bloom', 170.0, 0, 70.0, 0.0, 55.0, where=lambda v: v.x > 350.0), None, 0), (0.8, settle, None, 0), wait(7.0), (0.0, hide, None, 0),
                     (0.2, force('Ev_Pile', 'Bloom', 170.0, 0, 70.0, 5.0, 55.0), None, 0), (0.8, settle, None, 0), wait(6.5), (0.0, hide, None, 0),
                     (0.2, force('Ev_Trickle', 'Trickle', 260.0, 0, 150.0, -150.0, 70.0), None, 0), (0.8, settle, None, 0), wait(4.5), (0.0, hide, None, 0),
                     (0.2, force('Ev_Drift', 'Drift', 200.0, 0, 120.0, 0.0, 55.0), None, 0), (0.8, settle, None, 0), wait(5.5), (0.0, hide, None, 0),
                     (0.2, force('Ev_ClockDrip', 'ClockDrip', 130.0, 0, 170.0, -30.0, 45.0), None, 0), (0.8, settle, None, 0), wait(4.5), (0.0, hide, None, 0),
                     (0.0, own_view, None, 0)],
    'fore': boot() + [(0.0, no_nightmare, None, 0), (0.0, no_absorb, None, 0),
                      (0.2, force('Ev_Sleeve', 'Sleeve', 150.0, 0, 150.0, 10.0, 45.0), None, 0), (0.8, settle, None, 0), wait(3.2), (0.0, hide, None, 0),
                      (0.2, force('Ev_Shirt', 'Shirt', 170.0, 0, 110.0, 0.0, 55.0, where=lambda v: v.y < -200.0), None, 0), (0.8, settle, None, 0), wait(7.0), (0.0, hide, None, 0),
                      (0.2, force('Ev_Hourglass', 'Hourglass', 90.0, 0, 150.0, 10.0, 40.0), None, 0), (0.8, settle, None, 0), wait(7.0), (0.0, hide, None, 0),
                      (0.0, own_view, None, 0), (0.2, glimpse_face, None, 0), (0.6, glimpse, None, 0), wait(2.0),
                      (0.2, force('Ev_Suit', 'Suit', 280.0, 0, 140.0, 90.0, 60.0, where=lambda v: v.y < -300.0), None, 0), (0.8, settle, None, 0), wait(8.5), (0.0, hide, None, 0),
                      (0.0, own_view, None, 0)],
    'clock': boot() + [(0.0, no_absorb, None, 0), (0.0, clock_reset, None, 0),
                       (0.3, lambda w: (view_on(w, unreal.Vector(325.0, -92.0, 92.0), 200.0, 140.0, 50.0), S.update(tag='gap', next_tag='ClockFar')), None, 0),
                       (0.8, settle, None, 0), (0.0, clock_ring(True), None, 0), wait(3.0),
                       (0.0, lambda w: (view_on(w, unreal.Vector(325.0, -92.0, 92.0), 75.0, 115.0, 45.0), S.update(tag='gap', next_tag='Clock')), None, 0),
                       (0.8, settle, None, 0), wait(3.0), (0.0, clock_slap, None, 0), wait(5.0),
                       (0.0, lambda w: (view_on(w, unreal.Vector(325.0, -92.0, 85.0), 200.0, 140.0, 50.0), S.update(tag='gap', next_tag='ClockPileFar')), None, 0),
                       (0.8, settle, None, 0), wait(3.0), (0.0, clock_persisted, None, 0)],
    'wake': [(0.3, lambda w: unreal.SystemLibrary.execute_console_command(w, 'viewmode lit'), None, 0),
             (0.3, lambda w: frontend(w).call_method('OnSplashFinished', ()), None, 0),
             (0.6, lambda w: frontend(w).call_method('OnTitleConfirmed', ()), None, 0),
             (0.8, lambda w: frontend(w).call_method('WakeUp', ()), 'film', 12),
             (0.0, film_start, None, 0), wait(37.5)],
    'live': boot() + [(0.2, lambda w: (frame(w, unreal.Vector(-110.0, -200.0, 0.0), 1.0, 0.0, 0.0),
                                       unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(
                                           unreal.Rotator(roll=0, pitch=-35.0, yaw=200.0)), S.update(tag='Absorb')), None, 0),
                      wait(15.0),
                      (0.2, lambda w: (view_on(w, unreal.Vector(374.0, 48.0, 89.0), 70.0, 120.0, 40.0), S.update(tag='gap', next_tag='Lock')), None, 0),
                      (0.8, settle, None, 0), wait(2.5),
                      (0.2, lambda w: (own_view(w), amb(w).call_method('Rearm', (0.0,)),
                                       frame(w, unreal.Vector(-150.0, -150.0, 60.0), 250.0, 0.0, 120.0), S.update(tag='Natural')), None, 0),
                      wait(14.0)],
}
STEPS = PLANS[PLAN]


def tick(_dt):
    w = W()
    if not w:
        return finish('pie_gone')
    now = time.time()
    if now - S['t0'] > CAP:
        return finish('cap')
    try:
        keep_aim(w)
        ramp_tick(w)
        film_tick(w)
    except Exception as e:  # never stop the burst over framing
        log('aim_error', err=repr(e))
    if SHOTS == '1' and S['vp'] and now - S['shot'] > 0.4 and S['tag'] not in ('boot', 'gap'):
        S['shot'] = now
        S['n'] += 1
        unreal.SystemLibrary.execute_console_command(w, 'Shot showui')
        log('shot', n=S['n'], tag=S['tag'], aim_err=S.get('aim_err'), aim_pitch=S.get('aim_pitch'),
            **(state(w) if S['n'] % 5 == 0 else {}))
    if S['i'] >= len(STEPS):
        return finish('done')
    delay, act, want, timeout = STEPS[S['i']]
    if S.get('waiting'):
        if want=='film' and SKIP_STORY and not S.get('story_skipped'):
            story=frontend(w).get_editor_property('Story')
            if story and story.is_in_viewport():
                story.call_method('Finish',());S['story_skipped']=True
        b = beat(w)
        met = (unreal.GameplayStatics.get_player_controller(w, 0).get_view_target().get_class().get_name() == 'CineCameraActor'
               if want == 'film' else b == want)
        if met or now - S['mark'] > timeout:
            if not met:
                log('miss', want=want, beat=b)
            S['waiting'] = False
            S['i'] += 1
            S['mark'] = now
        return
    if now - S['mark'] < delay:
        return
    if act:
        try:
            act(w)
        except Exception as e:  # a failed step is logged, the burst goes on
            log('error', step=S['i'], err=repr(e))
    S['mark'] = now
    if want:
        S['waiting'] = True
    else:
        S['i'] += 1


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('world pie scheduled', PLAN, len(STEPS), 'steps ->', OUT)
