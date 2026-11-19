"""Face lane PIE driver: boots the real front end, then shoots the teen with the in-engine Shot command.
Runs inside a face_burst.sh PIE burst (lane already holds EXCLUSIVE), from a Slate post-tick callback:
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/pie_face_shots.py FOA_RUN=<name> FOA_MODE=play|cine
play: SkipWakeUp, he turns to the room centre, then for each view a still, its mask review (MPC FaceSlip -1) and a
      clean reference (blur weight 0): close front / 3/4 / profile, mid, third-person distance, far, back, the real
      T7 top-down (director TopDownCamera, ceiling hidden); first-person gameplay + its mask; a 50% screen-percentage
      still; an orbit and a walk (frame sequences for GIFs).
cine: lets LS_WakeUp play and shoots every FOA_EVERY s (default 0.4) from FOA_FROM s (default 12) to 34 s.
FOA_BLEND=new swaps M_PP_DreamFace -> M_PP_FaceBlur on the PIE copy of PP_DreamMono only (dev before the real swap).
Output: Saved/FaceShots/<run>/*.png and shots.json. Isolated save slot; PIE-world changes only, nothing saved.
Python cannot spawn into the PIE world, so the PIE copy of Shot_TopDown is the movable camera."""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

RUN = os.environ.get('FOA_RUN', 'face')
MODE = os.environ.get('FOA_MODE', 'play')
EVERY = float(os.environ.get('FOA_EVERY', '0.4'))
FROM = float(os.environ.get('FOA_FROM', '2'))
CAP = float(os.environ.get('FOA_CAP', '44'))
BLEND = os.environ.get('FOA_BLEND', '')
OUT = Path('P:/FoA/Saved/FaceShots') / RUN
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob('*.png'):
    old.unlink()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
find = lambda path: unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))
fe = find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d = find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
pc = unreal.GameplayStatics.get_player_controller(w, 0)
gi = unreal.GameplayStatics.get_game_instance(w)
MPC = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
FACE_PP = ('M_PP_FaceBlur', 'M_PP_DreamFace', 'TMP_face_FaceBlurV10')
old_ctx = (str(gi.get_editor_property('SaveSlot')), set(gi.get_editor_property('Knowledge')), list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext', ('FoA_QA_Face', set(), []))
S = dict(t0=time.time(), h=None, actions=set(), story=False, skip=False, ready=False, done=False, shots=[], step=0,
         wait=0, next_cine=0.0, error=None, yaw=0.0, cam=None, ceiling=False)
SP = unreal.SystemLibrary.get_console_variable_float_value('r.ScreenPercentage')
ROOM = (-360.0, 360.0, -285.0, 285.0, 20.0, 285.0)  # inside the bedroom walls and under the ceiling (cm)


def volume():
    return next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume)
                if a.get_actor_label() == 'PP_DreamMono')


def set_blendables(fn):
    """Rebuild PP_DreamMono's blendables (PIE copy): fn(name, weight) -> (object, weight) or None to drop."""
    vol = volume()
    st = vol.get_editor_property('settings')
    out = []
    for b in st.get_editor_property('weighted_blendables').get_editor_property('array'):
        o = b.get_editor_property('object')
        r = fn(o.get_name() if o else '', o, b.get_editor_property('weight'))
        if r:
            wb = unreal.WeightedBlendable()
            wb.set_editor_property('object', r[0])
            wb.set_editor_property('weight', r[1])
            out.append(wb)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property('array', out)
    st.set_editor_property('weighted_blendables', wbs)
    vol.set_editor_property('settings', st)
    S['blendables'] = [(b.get_editor_property('object').get_name(), b.get_editor_property('weight')) for b in out]


if BLEND == 'new':
    NEW = unreal.load_asset('/Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur')
    set_blendables(lambda n, o, wt: (NEW, wt) if n == 'M_PP_DreamFace' else (o, wt))
else:
    set_blendables(lambda n, o, wt: (o, wt))


def blur_weight(v):
    set_blendables(lambda n, o, wt: (o, v) if n in FACE_PP else (o, wt))


def player():
    p = unreal.GameplayStatics.get_player_character(w, 0)
    body = next(c for c in p.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
    return p, body


def shot(label):
    unreal.SystemLibrary.execute_console_command(w, f'Shot filename={OUT.as_posix()}/{label}.png -nosuffix', pc)
    p, body = player()
    cam = pc.player_camera_manager
    hp = None
    if pc.get_view_target() != p:
        head = body.get_socket_location('head') + unreal.Vector(0, 0, 8)
        up = cam.get_camera_rotation().get_up_vector()

        def proj(v):
            raw = pc.project_world_location_to_screen(v, True)
            return raw if hasattr(raw, 'x') else next((x for x in (raw or []) if hasattr(x, 'x')), None)
        a, b = proj(head), proj(head + up * 16.0)
        if a and b:
            hp = [a.x, a.y, math.hypot(a.x - b.x, a.y - b.y)]
    S['shots'].append(dict(label=label, t=round(time.time() - S['t0'], 2), head_px=hp, viewport=list(pc.get_viewport_size()),
                           cam=list(cam.get_camera_location().to_tuple()), cam_rot=list(cam.get_camera_rotation().to_tuple()),
                           fov=cam.get_fov_angle(), actor_yaw=p.get_actor_rotation().yaw,
                           face_slip=unreal.MaterialLibrary.get_scalar_parameter_value(w, MPC, 'FaceSlip')))


def tmp_cam():
    if not S['cam']:
        c = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.CameraActor)
                 if a.get_actor_label() == 'Shot_TopDown')
        S['cam'] = c
        S['cam_home'] = (c.get_actor_location(), c.get_actor_rotation(), c.camera_component.field_of_view)
        c.camera_component.set_editor_property('constrain_aspect_ratio', False)
    return S['cam']


def inside(look, off):
    """Shorten `off` so look + off stays inside the room (camera never behind a wall)."""
    t = 1.0
    for axis, lo, hi in (('x', ROOM[0], ROOM[1]), ('y', ROOM[2], ROOM[3]), ('z', ROOM[4], ROOM[5])):
        o, l = getattr(off, axis), getattr(look, axis)
        if o > 1e-3:
            t = min(t, (hi - l) / o)
        elif o < -1e-3:
            t = min(t, (lo - l) / o)
    return look + off * max(0.2, t)


def place(loc, look, fov):
    c = tmp_cam()
    c.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, True)
    c.camera_component.set_field_of_view(fov)
    if pc.get_view_target() != c:
        pc.set_view_target_with_blend(c, 0.0)


def view(yaw_off, dist, pitch=-3.0, fov=40.0, look_dz=0.0):
    """Orbit a camera around his head: yaw_off 0 is in front of his face, 180 behind him."""
    p, body = player()
    look = body.get_socket_location('head') + unreal.Vector(0, 0, 8 + look_dz)
    yaw, pr = math.radians(S['yaw'] + yaw_off), math.radians(-pitch)
    off = unreal.Vector(math.cos(yaw) * math.cos(pr), math.sin(yaw) * math.cos(pr), math.sin(pr)) * dist
    place(inside(look, off), look, fov)


def restore_cam():
    p, body = player()
    pc.set_view_target_with_blend(p, 0.0)


def topdown():
    """The game's own T7 top-down: the director's TopDownCamera with the ceiling hidden."""
    d.call_method('SetCeilingHidden', (True,))
    S['ceiling'] = True
    cam = d.get_editor_property('TopDownCamera')
    cam = cam.get_owner() if isinstance(cam, unreal.ActorComponent) else cam
    if not cam:
        cam = tmp_cam()
        loc, rot, fov = S['cam_home']
        cam.set_actor_location_and_rotation(loc, rot, False, True)
        cam.camera_component.set_field_of_view(fov)
    pc.set_view_target_with_blend(cam, 0.0)


def ceiling_back():
    if S['ceiling']:
        d.call_method('SetCeilingHidden', (False,))
        S['ceiling'] = False


def slip(v):
    unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'FaceSlip', v)


def sp(v):
    unreal.SystemLibrary.execute_console_command(w, f'r.ScreenPercentage {v}', None)


def face_centre():
    """He turns to face the room centre, so front views have the room behind the camera."""
    p, body = player()
    a = p.get_actor_location()
    S['yaw'] = math.degrees(math.atan2(-a.y, -a.x))
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=0, yaw=S['yaw']))


def walk():
    """Walk him toward the room centre; a camera ahead and to his side keeps his head in frame."""
    p, body = player()
    yaw = math.radians(S['yaw'])
    fwd = unreal.Vector(math.cos(yaw), math.sin(yaw), 0)
    p.add_movement_input(fwd, 1.0)
    head = body.get_socket_location('head')
    side = unreal.Vector(-fwd.y, fwd.x, 0)
    place(inside(head, fwd * 230 + side * 90 + unreal.Vector(0, 0, 20)), head + unreal.Vector(0, 0, 4), 40)


def freeze(v):
    """Hold his animation (actor time dilation) so the still, mask and clean frames show the same pose."""
    p, body = player()
    p.set_editor_property('custom_time_dilation', v, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)  # notified sets re-run BP_FoAPlayer construction (editor-rules)


def trio(act, label, settle=4):
    return [(lambda: (act(), freeze(0.0)), settle, label), (lambda: slip(-1.0), 3, 'mask_' + label),
            (lambda: (slip(1.0), blur_weight(0.0)), 3, 'clean_' + label), (lambda: (blur_weight(1.0), freeze(1.0)), 2, None)]


# (action, settle ticks, label or None). The action runs once; the shot follows after the settle ticks.
PLAY = [(lambda: None, 50, 'gameplay'), (lambda: slip(-1.0), 3, 'mask_gameplay'), (lambda: (slip(1.0), face_centre()), 20, None)]
PLAY += trio(lambda: view(0, 120, fov=35), 'close_front', 8)
PLAY += trio(lambda: view(40, 120, fov=35), 'close_34')
PLAY += trio(lambda: view(85, 120, fov=35), 'close_profile')
PLAY += trio(lambda: view(30, 180, pitch=-8, fov=45), 'mid_34')
PLAY += trio(lambda: view(150, 300, pitch=-14, fov=60, look_dz=-30), 'tps_34back')
PLAY += trio(lambda: view(10, 430, pitch=-12, fov=50, look_dz=-60), 'far_front')
PLAY += trio(lambda: view(165, 120, pitch=-14, fov=45), 'back')
PLAY += trio(topdown, 'topdown', 8)
PLAY += [(lambda: (ceiling_back(), sp(50), view(40, 120, fov=35)), 8, 'sp50_close_34'), (lambda: sp(SP), 6, 'sp100_close_34')]
for i in range(36):  # orbit at mid distance, 10 degrees a step
    PLAY.append((lambda a=i: view(a * 10, 140, pitch=-6, fov=40), 1, f'orbit_{i:03d}'))
for i in range(30):  # walk toward the room centre, chase camera
    PLAY.append((walk, 1, f'walk_{i:03d}'))
PLAY.append((restore_cam, 4, None))
if MODE == 'ab':
    # v8 (live) against the v10 preview (TMP_face_FaceBlurV10, swapped in on the PIE volume only), same frozen pose:
    # v8_<view>, v10_<view> (also saved as <view> for leak_check), the v10 mask review and the clean frame.
    LIVE = unreal.load_asset('/Game/FoA/PostProcess/FaceBlur/M_PP_FaceBlur')
    PREV = unreal.load_asset('/Game/FoA/PostProcess/FaceBlur/TMP_face_FaceBlurV10')
    assert LIVE and PREV, 'preview material missing'
    use = lambda m: set_blendables(lambda n, o, wt: (m, wt) if n in FACE_PP else (o, wt))

    def ab(act, label, settle=4):
        return [(lambda: (act(), freeze(0.0), use(LIVE)), settle, 'v8_' + label),
                (lambda: use(PREV), 4, 'v10_' + label), (lambda: None, 1, label),
                (lambda: slip(-1.0), 3, 'mask_' + label),
                (lambda: (slip(1.0), blur_weight(0.0)), 3, 'clean_' + label),
                (lambda: (blur_weight(1.0), use(LIVE), freeze(1.0)), 2, None)]
    PLAY = [(lambda: (slip(1.0), face_centre()), 20, None)]
    PLAY += ab(lambda: view(0, 120, fov=35), 'close_front', 8)
    PLAY += ab(lambda: view(40, 120, fov=35), 'close_34')
    PLAY += ab(lambda: view(85, 120, fov=35), 'close_profile')
    PLAY += ab(lambda: view(25, 70, fov=35), 'closeup')
    PLAY += ab(lambda: view(30, 180, pitch=-8, fov=45), 'mid_34')
    PLAY += ab(lambda: view(10, 430, pitch=-12, fov=50, look_dz=-60), 'far_front')
    PLAY += ab(lambda: view(165, 120, pitch=-14, fov=45), 'back')
    PLAY.append((restore_cam, 4, None))
    if os.environ.get('FOA_VIEWS'):  # a slow editor (a few fps) can't fit every view in one burst: shoot a subset
        keep = os.environ['FOA_VIEWS'].split(',')
        PLAY = PLAY[:1] + [s for i in range(1, len(PLAY) - 1, 6) if PLAY[i][2][3:] in keep for s in PLAY[i:i + 6]] + PLAY[-1:]
if MODE == 'hair':
    # The hairline fan under the phone's close screen light, in UI's 3/4 pose (FACEVIEW 163,40,120,-3,35), face blur
    # at 0: each variant shot with the phone light on and off. PIE copy only: a dynamic instance on the Hair groom
    # and the phone light's own flags (the deep-shadow variant is a diagnostic, not a fix this lane makes).
    def mid():
        if not S.get('mid'):
            S['mid'] = player()[0].get_editor_property('Hair').create_dynamic_material_instance(0)
            S['mid0'] = {k: S['mid'].get_scalar_parameter_value(k) for k in ('HairSpecular', 'HairRoughness')}
            S['col0'] = S['mid'].get_vector_parameter_value('HairColor')
        return S['mid']

    def lights():
        cls = unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')
        return [c for ph in unreal.GameplayStatics.get_all_actors_of_class(w, cls) for c in ph.get_components_by_class(unreal.RectLightComponent)]

    def phone(on):
        for c in lights():
            c.set_visibility(on)

    def hair(spec=None, rough=None, k=1.0, deep=False, bd=None, cd=None, z=None, aim=None):
        if 'light0' not in S:  # the phone light as ApplyScreen left it, put back between variants
            S['light0'] = [(c.get_editor_property('barn_door_angle'), c.intensity, c.get_editor_property('relative_location').z,
                            c.get_editor_property('relative_rotation')) for c in lights()]
        for c, (bd0, cd0, z0, r0) in zip(lights(), S['light0']):
            c.set_barn_door_angle(bd0 if bd is None else bd)
            c.set_intensity(cd0 if cd is None else cd)
            loc = c.get_editor_property('relative_location')
            c.set_editor_property('relative_location', unreal.Vector(loc.x, loc.y, z0 if z is None else z))
            c.set_editor_property('relative_rotation', r0)
            if aim is not None:  # aim the cone's axis (the rect light's +X) at his face, aim cm below the head socket
                p, body = player()
                face = body.get_socket_location('head') + p.get_actor_forward_vector() * 9.0 + unreal.Vector(0, 0, -aim)
                c.set_world_rotation(unreal.MathLibrary.find_look_at_rotation(c.get_world_location(), face), False, True)
        m = mid()
        m.set_scalar_parameter_value('HairSpecular', S['mid0']['HairSpecular'] if spec is None else spec)
        m.set_scalar_parameter_value('HairRoughness', S['mid0']['HairRoughness'] if rough is None else rough)
        c = S['col0']
        m.set_vector_parameter_value('HairColor', unreal.LinearColor(c.r * k, c.g * k, c.b * k, c.a))
        for c in lights():
            c.set_cast_shadows(deep)
            c.set_editor_property('cast_deep_shadow', deep)
        head = player()[1].get_socket_location('head')
        S.setdefault('hair_log', []).append(dict(spec=spec, rough=rough, k=k, deep=deep, bd=bd, cd=cd, z=z, aim=aim, base=S['mid0'], lights=[
            dict(intensity=round(c.intensity, 3), barn=round(c.get_editor_property('barn_door_angle'), 1),
                 z=round(c.get_editor_property('relative_location').z, 2), visible=c.is_visible(),
                 cm_to_head=round((c.get_world_location() - head).length(), 1))
            for c in lights()]))

    # base first and last: the run is valid only if both show the fan (the first sweep had none until the screen woke)
    VARIANTS = [('base', {}), ('spec0', dict(spec=0.0)), ('spec004', dict(spec=0.04)), ('rough095', dict(rough=0.95)),
                ('dark05', dict(k=0.5)), ('deep', dict(deep=True)), ('base2', {})]
    if os.environ.get('FOA_HAIR_SET') == 'light2':  # between 60 (no fan, no face light) and 70 (fan): the edge
        VARIANTS = [('base', {})] + [(f'bd{b}_cd{c}_z7p2'.replace('.', 'p'), dict(bd=b, cd=c, z=-7.2)) for b, c in (
            (62, 1.2), (64, 1.2), (66, 1.2), (68, 1.2), (64, 0.6), (66, 0.6), (68, 0.6), (66, 0.3), (68, 0.3))] + [('base2', {})]
    if os.environ.get('FOA_HAIR_SET') == 'aim':  # narrow door, cone axis on his mouth/chin (aim cm below the head socket)
        VARIANTS = [('base', {})] + [(f'aim{a}_bd{b}_cd{c}'.replace('.', 'p'), dict(bd=b, cd=c, z=-7.2, aim=a)) for a, b, c in (
            (4, 60, 1.2), (8, 60, 1.2), (12, 60, 1.2), (4, 55, 1.2), (8, 55, 1.2), (12, 55, 1.2), (8, 60, 0.6), (8, 55, 0.6),
            (8, 70, 1.2))] + [('base2', {})]
    if os.environ.get('FOA_HAIR_SET') == 'light':  # phone light variants: barn door x candela x emitter z (cm)
        VARIANTS = [('base', {})] + [(f'bd{b}_cd{c}_z{abs(z)}'.replace('.', 'p'), dict(bd=b, cd=c, z=z)) for b, c, z in (
            (70, 1.2, -7.2), (70, 0.6, -7.2), (70, 0.3, -7.2), (60, 1.2, -7.2), (60, 0.6, -7.2), (55, 1.2, -7.2),
            (55, 0.6, -7.2), (55, 0.3, -7.2), (70, 1.2, -1.2), (60, 0.6, -1.2), (55, 0.6, -1.2))] + [('base2', {})]
    def gate():
        # the phone must be raised to his face (about 36 cm) before any variant; if not yet, wait 10 more ticks
        head = player()[1].get_socket_location('head')
        far = min(((c.get_world_location() - head).length() for c in lights()), default=999.0)
        S['gate_cm'] = round(far, 1)
        if far > 45.0 and time.time() - S['t0'] < CAP - 25:
            PLAY.insert(S['step'] + 1, (gate, 10, None))

    PLAY = [(lambda: (slip(1.0), face_centre()), 20, None),
            (lambda: (view(40, 120, fov=35), blur_weight(0.0)), int(os.environ.get('FOA_SETTLE', '60')), None),
            (gate, 10, None), (lambda: freeze(0.0), 4, None)]
    for name, kw in VARIANTS:
        PLAY += [(lambda kw=kw: hair(**kw), 3, f'hair_{name}_on'), (lambda: phone(False), 3, f'hair_{name}_off'),
                 (lambda: (phone(True), hair()), 2, None)]
    PLAY.append((lambda: (blur_weight(1.0), freeze(1.0), restore_cam()), 4, None))
if os.environ.get('FOA_PROF') == '1':  # GPU cost: one profiled frame each, worst case (head fills the frame) first
    def prof(tag):
        unreal.SystemLibrary.execute_console_command(w, 'r.ProfileGPU.ShowUI 0', None)
        unreal.SystemLibrary.execute_console_command(w, 'profilegpu', None)
        unreal.log(f'[face] profilegpu {tag}')
    PLAY += [(lambda: (face_centre(), view(0, 70, fov=35)), 10, 'prof_close'), (lambda: prof('close'), 6, None),
             (lambda: view(30, 180, pitch=-8, fov=45), 6, 'prof_mid'), (lambda: prof('mid'), 6, None),
             (restore_cam, 6, 'prof_fp'), (lambda: prof('fp'), 6, None)]


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    try:
        unreal.unregister_slate_post_tick_callback(S['h'])
    finally:
        try:
            slip(1.0)
            sp(SP)
            blur_weight(1.0)
            freeze(1.0)
            ceiling_back()
            if S['cam']:
                loc, rot, fov = S['cam_home']
                S['cam'].set_actor_location_and_rotation(loc, rot, False, True)
                S['cam'].camera_component.set_field_of_view(fov)
                restore_cam()
            gi.call_method('SetProofProgressContext', old_ctx)
            unreal.GameplayStatics.delete_game_in_slot('FoA_QA_Face', 0)
        except Exception:
            S['error'] = (S['error'] or '') + traceback.format_exc()
        (OUT / 'shots.json').write_text(json.dumps(dict(reason=reason, error=S['error'], mode=MODE, sp=SP,
                                                        blendables=S.get('blendables'), diag=S.get('diag'), outfit=S.get('outfit'), hair=S.get('hair_log'), shots=S['shots']), indent=1))
        unreal.log(f'[face] {RUN} finished: {reason}')


def tick(dt):
    try:
        if time.time() - S['t0'] > CAP:
            return finish('timeout')
        if not S['ready']:
            if time.time() - S.get('diag_t', 0) > 2.0:  # why boot stalls, if it does
                S['diag_t'] = time.time()
                p0 = unreal.GameplayStatics.get_player_character(w, 0)
                vt = pc.get_view_target()
                scr = fe.get_editor_property('Screen')
                S.setdefault('diag', []).append(dict(t=round(time.time() - S['t0'], 1), screen=scr.get_class().get_name() if scr else None,
                    gameplay=fe.get_editor_property('bInGameplay'), wake_done=d.get_editor_property('bWakeDone'),
                    seq=bool(d.get_editor_property('SeqPlayer')), view=vt.get_name() if vt else None,
                    cinematic=p0.get_editor_property('bCinematic') if p0 else None, actions=sorted(S['actions']), skip=S['skip']))
            screen = fe.get_editor_property('Screen')
            if screen and screen.is_in_viewport():
                for prop, action in [('SplashClass', 'OnSplashFinished'), ('TitleClass', 'OnTitleConfirmed'), ('MainMenuClass', 'WakeUp')]:
                    if screen.get_class() == fe.get_editor_property(prop) and action not in S['actions']:
                        S['actions'].add(action)
                        fe.call_method(action, ())
                        return
            story = fe.get_editor_property('Story')
            if story and story.is_in_viewport() and not S['story']:
                story.call_method('Finish', ())
                S['story'] = True
                return
            seq = d.get_editor_property('SeqPlayer')
            if MODE == 'cine':
                if seq and fe.get_editor_property('bInGameplay') and not d.get_editor_property('bWakeDone'):
                    S['ready'] = True
                return
            if fe.get_editor_property('bInGameplay') and seq and not d.get_editor_property('bWakeDone') and not S['skip']:
                d.call_method('SkipWakeUp', ())
                S['skip'] = True
                S['skip_t'] = time.time()
                return
            p, body = player()
            # After the skip the T0 phone beat may hold the view (BP_Phone, bCinematic); the stills use their own
            # camera, so wait only for the wake-up to be done and the pawn to settle.
            if d.get_editor_property('bWakeDone') and S['skip'] and time.time() - S.get('skip_t', 0) > 1.5:
                unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
                unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
                S['yaw'] = p.get_actor_rotation().yaw
                S['outfit'] = {c.get_name(): [c.is_visible(), c.get_skeletal_mesh_asset().get_name() if c.get_skeletal_mesh_asset() else None]
                               for c in p.get_components_by_class(unreal.SkeletalMeshComponent)}
                S['outfit']['lights'] = {c.get_name(): [c.is_visible(), c.intensity] for c in p.get_components_by_class(unreal.LightComponent)}
                S['ready'] = True
                S['wait'] = -1
            return
        if MODE == 'cine':
            seq = d.get_editor_property('SeqPlayer')
            st = -1.0
            if seq:
                q = seq.get_current_time()
                st = (q.time.frame_number.value + q.time.sub_frame) * q.rate.denominator / q.rate.numerator
            S['st'] = st
            if st > 34.0 or (d.get_editor_property('bWakeDone') and st < 0):
                return finish(f'cine done at {st:.2f} s, wake done {d.get_editor_property("bWakeDone")}')
            if st >= FROM and st >= S['next_cine']:
                shot(f'cine_{st:05.2f}'.replace('.', '_'))
                S['next_cine'] = st + EVERY
            return
        if S['step'] >= len(PLAY):
            return finish('play done')
        act, settle, label = PLAY[S['step']]
        if S['wait'] < 0:
            act()
            S['wait'] = settle
            return
        if label and label.startswith('walk_'):
            act()
        if S['wait'] > 0:
            S['wait'] -= 1
            return
        if label:
            shot(label)
        S['step'] += 1
        S['wait'] = -1
    except Exception:
        S['error'] = traceback.format_exc()
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('[face] driver registered', RUN, MODE, S.get('blendables'))
