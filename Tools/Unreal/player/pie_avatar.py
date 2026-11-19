"""Player lane: avatar proof inside a running PIE (in-editor tick callback; reads the PIE world, writes nothing).
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/pie_avatar.py [FOA_WALK=12]
Skips the front end into gameplay, waits until the player has control (or 30 s), takes two stills from the gameplay
camera (behind the shoulder, then a 3/4 front swing of the control yaw), then walks the bedroom for FOA_WALK s: the next
heading is the freest of 12 sphere-traced directions, biased forward; the last 3 s jog. 'Shot' frames about 8/s.
Marks the Output Log with '[avatar] <event>' lines (record_avatar.sh sorts the frames by them); ends PIE when done."""
import math
import os
import time

import unreal

WALK = float(os.environ.get('FOA_WALK', '12'))
FE_C = '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'
S = {'t0': time.time(), 'phase': 'menu', 'mark': time.time(), 'shot': 0.0, 'h': None, 'goal': None, 'yaw': None,
     'last': None, 'stuck': 0.0, 'heading': 0.0, 'jog': False}


def log(msg):
    unreal.log(f'[avatar] {msg} t={time.time() - S["t0"]:.2f}')


def cmd(w, c):
    unreal.SystemLibrary.execute_console_command(w, c)


def free(w, pawn, yaw):
    """Free distance (cm) from the pawn's knees along yaw, a 36 cm sphere sweep, up to 420 cm."""
    p = pawn.get_actor_location()
    a = math.radians(yaw)
    start = unreal.Vector(p.x, p.y, p.z - 35.0)
    end = unreal.Vector(p.x + math.cos(a) * 420.0, p.y + math.sin(a) * 420.0, p.z - 35.0)
    try:
        h = unreal.SystemLibrary.sphere_trace_single(w, start, end, 36.0, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False,
                                                     [pawn], unreal.DrawDebugTrace.NONE, True)
    except Exception as e:  # no trace: a fixed guess still walks him around (bumps re-pick via the stuck timer)
        if not S.get('trace_err'):
            S['trace_err'] = True
            log(f'trace error {e!r}')
        return 200.0
    if isinstance(h, tuple):  # (bool, HitResult) on some builds
        h = h[1] if h[0] else None
    if not h:
        return 420.0
    try:
        t = h.to_tuple()
    except Exception:  # older wrappers: the Blueprint break node gives the same order
        t = unreal.GameplayStatics.break_hit_result(h)
    return 420.0 * t[2] if t[0] else 420.0


def pick(w, pawn):
    best = None
    for i in range(12):
        yaw = S['heading'] + i * 30.0
        d = free(w, pawn, yaw)
        turn = math.cos(math.radians(yaw - S['heading']))
        if d < 110 or turn < -0.6:
            continue
        score = d * (1.0 + 0.6 * turn)
        if not best or score > best[0]:
            best = (score, yaw, d)
    if not best:  # boxed in: turn around
        best = (0, S['heading'] + 180.0, 150.0)
    _, yaw, d = best
    p = pawn.get_actor_location()
    reach = min(d - 70.0, 260.0)
    S['heading'] = yaw
    S['goal'] = unreal.Vector(p.x + math.cos(math.radians(yaw)) * reach, p.y + math.sin(math.radians(yaw)) * reach, p.z)
    S['mark'] = time.time()
    log(f'goal yaw={yaw:.0f} free={d:.0f}')


def finish(w=None):
    if S['h'] is not None:
        unreal.unregister_slate_post_tick_callback(S['h'])
        S['h'] = None
    log('done')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


def in_control(w, pawn, pc):
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, FE_C))
    vt = pc.get_view_target() if pc else None
    return bool(pawn and vt == pawn and (not fe or fe.get_editor_property('bInGameplay')))


def tick(dt):
    try:
        step(dt)
    except Exception as e:  # one bad tick must not spam the log for the rest of the burst
        log(f'error {e!r}')
        finish()


def step(dt):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return finish()
    now, el = time.time(), time.time() - S['mark']
    pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    ph = S['phase']
    if ph == 'menu':  # skip splash, title and menu straight into the wake-up
        if el > 0.5:
            for c in ('viewmode lit', 'ke * OnSplashFinished', 'ke * OnTitleConfirmed', 'ke * WakeUp'):
                cmd(w, c)
            S['phase'], S['mark'] = 'wake', now
            log('wake requested')
    elif ph == 'wake':
        if in_control(w, pawn, pc) and el > 2.0 or el > 30.0:
            S['phase'], S['mark'] = 'settle', now
            S['yaw'] = pawn.get_actor_rotation().yaw
            S['heading'] = S['yaw']
            log(f'control (in control: {in_control(w, pawn, pc)}) view={pc.get_view_target().get_name() if pc else None}')
    elif ph == 'settle':  # camera behind the shoulder, let the boom lag settle, then the two stills
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-12.0, yaw=S['yaw']))
        if el > 1.5:
            cmd(w, 'Shot')
            log('still_back')
            S['phase'], S['mark'] = 'swing', now
    elif ph == 'swing':  # swing the arm around to his 3/4 front: face, hair and brows in frame
        k = min(el / 1.6, 1.0)
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-8.0, yaw=S['yaw'] + 150.0 * (0.5 - 0.5 * math.cos(math.pi * k))))
        if el > 2.6:
            cmd(w, 'Shot')
            log('still_front')
            S['phase'], S['mark'] = 'walk', now
            S['walk0'] = now
            log('walk_start')
    elif ph == 'walk':
        t = now - S['walk0']
        if t > WALK:
            log('walk_end')
            return finish(w)
        if not S['jog'] and t > WALK - 3.0:
            S['jog'] = True
            pawn.call_method('SetJogging', (True,))
            log('jog')
        p = pawn.get_actor_location()
        if S['goal'] is None or (S['goal'] - p).length() < 45.0 or el > 3.5 or S['stuck'] > 0.6:
            S['stuck'] = 0.0
            pick(w, pawn)
        if S['last'] is not None and (p - S['last']).length() < 0.6 * max(dt, 1e-3) * 60.0:  # under 60 cm/s
            S['stuck'] += dt
        else:
            S['stuck'] = 0.0
        S['last'] = p
        g = S['goal'] - p
        g.z = 0.0
        pawn.add_movement_input(g.normal(), 1.0, True)
        # camera trails the walk from behind and a little to the side, eased
        want = math.degrees(math.atan2(g.y, g.x)) + 25.0
        cur = pc.get_control_rotation().yaw
        d = (want - cur + 540.0) % 360.0 - 180.0
        pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-12.0, yaw=cur + d * min(1.0, 1.8 * dt)))
        if now - S['shot'] > 0.125:
            S['shot'] = now
            cmd(w, 'Shot')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('avatar run scheduled, walk', WALK, 's')
