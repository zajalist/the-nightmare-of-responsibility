"""PIE proof of the first-person phone hold (run by record_anim.sh as FOA_PIE_SCRIPT). Skips the wake-up and lets T0
open the phone by itself (story: buzz, then rise, about 3.2 s after the hand-off; never forced): shoots that real open,
then ClosePhone (which clears PhoneWakeUp). Then BeginPhoneHold(<the level's BP_Phone>) directly, until UI swaps
OpenPhone onto it: shoots the raise every 0.07 s, the hold, a thumb tap frame by frame, the screen after PhoneDown and
PhoneConfirm, then EndPhoneHold and the lower. FOA_PHONE_T10=1 instead (main / QA B3: the T10 phone sat at the bottom
edge after the payoff): after T0, EnterBeat 9 (QA's plan C shortcut), the T9 payoff plays, and the real T10 raise is
filmed and judged (t10_home at 1.8 s and 2.4 s after it opens). Logs, per shot: the phone's distance and angle
from the eye, the screen axis facing, the left wrist versus its IK target, and the phone mesh bounds.
Ends with '[anim] done'. Output: Saved/AnimShots/phone/<stamp>/."""
import datetime
import json
import math
import os
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)
import pie_pose_capture  # noqa: E402  (the held pose for the twin replay: hand_twin.run_phone)
import importlib
importlib.reload(pie_pose_capture)
import proof_guard  # noqa: E402  (stands down when its own PIE ends; never acts in anyone else's)

w = p = pc = fe = d = None
folder = Path('P:/FoA/Saved/AnimShots/phone') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(start=time.monotonic(), phase=0, story=False, skipped=False, t0=None, n=0, rows=[], fin=False, phone=None, step=0, next=0.0)
PLAN = [(0.0, 'begin'), (0.0, 'shoot'), (0.07, 'shoot'), (0.14, 'shoot'), (0.21, 'shoot'), (0.28, 'shoot'), (0.35, 'shoot'),
        (0.95, 'shoot:home'), (1.3, 'tap'), (1.32, 'shoot:tap_a'), (1.36, 'shoot:tap_b'), (1.4, 'shoot:tap_c'), (1.48, 'shoot:tap_d'),
        (1.6, 'shoot:tap_e'), (1.8, 'down'), (2.1, 'shoot:list'), (2.3, 'confirm'), (2.7, 'shoot:message'), (2.9, 'end'),
        (2.97, 'shoot'), (3.04, 'shoot'), (3.11, 'shoot'), (3.18, 'shoot'), (3.4, 'shoot'), (3.8, 'finish')]  # home once the raise has settled (phone8 shot it mid-raise)
T10 = os.environ.get('FOA_PHONE_T10') == '1'
T10_SHOTS = ((0.0, 't10_a'), (0.3, 't10_b'), (0.6, 't10_c'), (0.9, 't10_d'), (1.2, 't10_e'), (1.8, 't10_home'), (2.4, 't10_home2'))
T0_WAIT = 9.0  # the T0 phone must open by itself within this many seconds of the hand-off


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


def v(x):
    return [round(x.x, 2), round(x.y, 2), round(x.z, 2)]


def project(pos):
    r = unreal.GameplayStatics.project_world_to_screen(pc, pos, False)
    sp = r[1] if isinstance(r, tuple) else r
    return None if sp is None or (isinstance(r, tuple) and not r[0]) else (sp.x, sp.y)


def seg_dist(pt, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    k = max(0.0, min(1.0, ((pt[0] - a[0]) * ax + (pt[1] - a[1]) * ay) / max(1e-6, ax * ax + ay * ay)))
    return math.hypot(pt[0] - a[0] - k * ax, pt[1] - a[1] - k * ay)


FINGERS = ('index', 'middle', 'ring', 'pinky')


def tipw(body, d):
    """World fingertip: the last phalanx continued by 0.8 of itself (a bone ends at the last joint)."""
    a, b = body.get_socket_location(d + '_02_l'), body.get_socket_location(d + '_03_l')
    return b + (b - a) * 0.8


def seg3(p, a, b):
    """Closest points between segment p (2 points) and segment a-b, 3D; returns the distance and the parameter on p."""
    best = (1e9, 0.0)
    for i in range(21):  # sampled along p: plenty for a 2 cm decision
        t = i / 20.0
        q = p[0] + (p[1] - p[0]) * t
        ab = b - a
        k = max(0.0, min(1.0, (q - a).dot(ab) / max(1e-6, ab.dot(ab))))
        d = (q - (a + ab * k)).length()
        if d < best[0]:
            best = (d, t)
    return best


def hand_in_frame(mesh, body, eye, full=True):
    """main's phone5 checks, per shot. Phone frame: +X up the screen, -Y screen right (the far edge from the left hand),
    -Z out of the glass; 14.7 x 7.1 x 1.0 cm.
    over_glass   finger joints or tips (not the thumb) in front of the glass inside the screen rectangle
    far_edge     fingertips on screen within 2 cm (in pixels at the phone's depth) of the screen-right edge
    occluded     fraction of a 19 x 9 grid on the glass whose sight line from the eye passes within 0.9 cm of a hand
                 segment (wrist to each knuckle, each phalanx, each tip) lying nearer the eye than the glass
    screens      visible screen surfaces: the glass, plus the Screen widget component if it renders off the glass"""
    xf = mesh.get_world_transform()
    loc = lambda q: xf.inverse_transform_location(q)  # noqa: E731
    size = unreal.WidgetLayoutLibrary.get_viewport_size(w)
    edge = [project(xf.transform_location(unreal.Vector(x, -3.55, 0.0))) for x in (-7.35, 7.35)]
    c, c2 = project(xf.transform_location(unreal.Vector(0, 0, 0))), project(xf.transform_location(unreal.Vector(0, -2.0, 0)))
    out = dict(over_glass=[], far_edge=0)
    hand = body.get_socket_location('hand_l')
    segs = []
    for d in FINGERS + ('thumb',):
        pts = [hand] + [body.get_socket_location('%s_0%d_l' % (d, i)) for i in (1, 2, 3)] + [tipw(body, d)]
        segs += list(zip(pts, pts[1:]))
        if d != 'thumb':
            for q in pts[1:]:
                l = loc(q)
                if l.z < -0.7 and abs(l.x) < 7.35 and abs(l.y) < 3.55:
                    out['over_glass'].append(d)
                    break
    if c and c2 and all(edge):
        px2 = math.hypot(c2[0] - c[0], c2[1] - c[1])
        for d in FINGERS:
            tw = tipw(body, d)
            lt = loc(tw)
            seen = abs(lt.y) > 3.85 or abs(lt.x) > 7.65 or lt.z < -0.5  # beside the phone or in front: not hidden behind it
            q = project(tw)
            if seen and q and 0 <= q[0] <= size.x and 0 <= q[1] <= size.y and seg_dist(q, *edge) <= px2:
                out['far_edge'] += 1
    hit, n = 0, 1
    for i in (range(19) if full else ()):
        for j in range(9):
            g = xf.transform_location(unreal.Vector(-7.0 + 14.0 * i / 18, -3.2 + 6.4 * j / 8, -0.5))
            n += full
            for a, b in segs:
                dd, t = seg3((eye, g), a, b)
                if dd < 0.9 and t < 0.995:
                    hit += 1
                    break
    out['occluded'] = round(hit / max(1, n - 1), 3) if full else None
    out['thumb_local'] = v(loc(tipw(body, 'thumb')))
    # reading framing (UI 2026-11-10): the glass fully in frame, at least a third of the frame tall, centred or just
    # left, its centre 8-12 deg below the view centre
    corners = [project(xf.transform_location(unreal.Vector(x, y, -0.5))) for x in (-6.9, 6.9) for y in (-3.2, 3.2)]
    if all(corners):
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        out['screen_box'] = [round(min(xs) / size.x, 3), round(min(ys) / size.y, 3), round(max(xs) / size.x, 3), round(max(ys) / size.y, 3)]
        out['screen_in_frame'] = bool(min(xs) >= 0 and min(ys) >= 0 and max(xs) <= size.x and max(ys) <= size.y)
        out['screen_height_frac'] = round((max(ys) - min(ys)) / size.y, 3)
    else:
        out['screen_in_frame'], out['screen_height_frac'] = False, 0.0
    cam = pc.player_camera_manager
    to = mesh.get_world_location() - cam.get_camera_location()
    crot = cam.get_camera_rotation()
    local = unreal.MathLibrary.less_less_vector_rotator(to, crot)  # into camera space: x forward, y right, z up
    out['screen_deg_below'] = round(math.degrees(math.atan2(-local.z, local.x)), 1)
    out['screen_deg_right'] = round(math.degrees(math.atan2(local.y, local.x)), 1)
    th = [loc(body.get_socket_location('thumb_0%d_l' % i)) for i in (2, 3)] + [loc(tipw(body, 'thumb'))]
    out['thumb_behind_glass'] = [v(q) for q in th if abs(q.x) < 7.35 and abs(q.y) < 3.55 and q.z > -0.45]  # pass-through
    # One screen = one layer of UI text. The glass draws the phone UI through its material; any visible world-space
    # widget component is a second layer of text, on the glass (phone5: the lock screen over the Today list) or off it
    # (phone4: a card below the phone). Each layer's text is logged so the sheet can be checked against it.
    glass = [str(mat.get_name()) for mat in mesh.get_materials() if mat]
    layers = [dict(glass_materials=glass)]
    for cmp in S['phone'].get_components_by_class(unreal.WidgetComponent):
        if not cmp.is_visible():
            continue
        wd = cmp.get_widget()
        texts = []
        if wd:  # the widget's own text blocks (UMG's WidgetBlueprintLibrary is not in editor Python: walk the objects)
            try:
                for tb in unreal.ObjectIterator(unreal.TextBlock) if hasattr(unreal, 'ObjectIterator') else []:
                    if wd.get_path_name() in tb.get_path_name() and tb.is_visible():
                        texts.append(str(tb.get_text()))
            except Exception as e:  # noqa: BLE001
                texts.append('text unavailable: %r' % e)
        layers.append(dict(widget=cmp.get_name(), offset_cm=round((cmp.get_world_location() - mesh.get_socket_location('Screen')).length(), 2),
                           text=texts[:8]))
    out['screens'] = len(layers)
    out['screen_layers'] = layers
    return out


def screen_angles(row):
    z, x = row['mesh_axes']['z'], row['mesh_axes']['x']
    to = [row['eye'][i] - row['phone'][i] for i in range(3)]
    n = math.sqrt(sum(t * t for t in to)) or 1.0
    facing = math.degrees(math.acos(max(-1.0, min(1.0, -sum(z[i] * to[i] for i in range(3)) / n))))
    upright = math.degrees(math.acos(max(-1.0, min(1.0, x[2]))))
    return round(facing, 1), round(upright, 1)


def verdict():
    """FAILED unless every held shot (home, list, message) has no finger over the glass, 2+ fingertips at the far edge,
    at most 20% of the screen occluded (the cradle's thumb covers some), no thumb joint behind the glass over the screen.
    One page on screen is judged on the rendered frames (phone_readability.py runs UI's qa_phone_pages): the widget
    tree holds both pages with one collapsed, so counting widget text gave a false 'screens 2'."""
    held = [r for r in S['rows'] if any(k in r.get('label', '') for k in ('home', 'list', 'message'))]
    bad = ['%s: over glass %s, far-edge tips %d, occluded %.0f%%, screens %d, thumb behind glass %s' % (
        r['label'], r.get('over_glass'), r.get('far_edge', 0), 100 * r.get('occluded', 1), r.get('screens', 0), r.get('thumb_behind_glass'))
        for r in held if r.get('over_glass') or r.get('far_edge', 0) < 2 or r.get('occluded', 1) > 0.20
        or r.get('thumb_behind_glass')]
    bad += ['%s: reading framing: in frame %s, height %.2f of the frame, %.1f deg below, %.1f deg right' % (
        r['label'], r.get('screen_in_frame'), r.get('screen_height_frac', 0), r.get('screen_deg_below', 0), r.get('screen_deg_right', 0))
        for r in held if not r.get('screen_in_frame') or r.get('screen_height_frac', 0) < 0.33
        or not 8.0 <= r.get('screen_deg_below', 0) <= 12.0 or not -6.0 <= r.get('screen_deg_right', 0) <= 1.5]
    bad += ['%s: phone world scale %s' % (r['label'], r.get('phone_world_scale')) for r in held
            if any(abs(c - 1.0) > 0.02 for c in r.get('phone_world_scale') or [0])]
    # a flipped or reversed phone (main, 2026-11-10): the glass (mesh -Z) must face the eye within 30 deg, screen-up
    # (mesh +X) within 45 deg of world up
    for r in held:
        r['screen_to_eye_deg'], r['screen_up_deg'] = screen_angles(r)
        flipped = dict(r, mesh_axes=dict(r['mesh_axes'], z=[-v for v in r['mesh_axes']['z']]))
        r['flipped_control_deg'] = screen_angles(flipped)[0]
        assert abs(r['screen_to_eye_deg'] + r['flipped_control_deg'] - 180) <= 0.2
        if r['screen_to_eye_deg'] <= 30:
            assert r['flipped_control_deg'] > 30, 'flipped phone escaped the orientation gate'
        if r['screen_to_eye_deg'] > 30 or r['screen_up_deg'] > 45:
            bad.append('%s: phone flipped: the glass is %.0f deg off the eye, screen-up %.0f deg off up' % (
                r['label'], r['screen_to_eye_deg'], r['screen_up_deg']))
    return 'FAILED ' + '; '.join(bad) if bad or not held else 'passed'


def measure(label):
    ph = S['phone']
    cam = pc.player_camera_manager
    eye, crot = cam.get_camera_location(), cam.get_camera_rotation()
    fwd = crot.get_forward_vector()
    mesh = ph.get_component_by_class(unreal.StaticMeshComponent)
    xf = mesh.get_world_transform()
    c = mesh.get_world_location()
    to = c - eye
    dist = to.length()
    ang = math.degrees(math.acos(max(-1.0, min(1.0, to.normal().dot(fwd)))))
    q = xf.rotation
    axes = {k: v(q.rotate_vector(a)) for k, a in (('x', unreal.Vector(1, 0, 0)), ('y', unreal.Vector(0, 1, 0)), ('z', unreal.Vector(0, 0, 1)))}
    body = p.get_editor_property('Body')
    mh = body.get_anim_instance()
    row = dict(label=label, raise_=round(p.get_editor_property('PhoneRaise'), 3), eye=v(eye), phone=v(c), dist_cm=round(dist, 1),
               phone_world_scale=v(mesh.get_world_scale()), phone_parent=(ph.get_attach_parent_actor().get_name() if ph.get_attach_parent_actor() else None),
               off_axis_deg=round(ang, 1), mesh_axes=axes, hand_l=v(body.get_socket_location('hand_l')),
               middle_01_l=v(body.get_socket_location('middle_01_l')), index_01_l=v(body.get_socket_location('index_01_l')),
               tips={b: v(body.get_socket_location(b)) for b in ('index_03_l', 'middle_03_l', 'ring_03_l', 'pinky_03_l', 'thumb_03_l')},
               pinky_01_l=v(body.get_socket_location('pinky_01_l')), thumb_01_l=v(body.get_socket_location('thumb_01_l')),
               hand_l_rot=str(body.get_socket_rotation('hand_l')),
               body_z={b: round(body.get_socket_location(b).z, 2) for b in ('pelvis', 'spine_05', 'upperarm_l', 'head')},
               actor_z=round(p.get_actor_location().z, 2))  # phone8/9: the phone kept rising with the raise done; which part moved
    try:
        row['ik_target'] = v(mh.get_editor_property('EnvironmentHandTarget'))
        row['ik_weight'] = round(mh.get_editor_property('EnvironmentHandWeight'), 3)
        row['grip'] = [round(mh.get_editor_property('PhoneGripWeight'), 3), round(mh.get_editor_property('PhoneGripTime') * 30, 3)]
    except Exception as e:
        row['ik_read'] = repr(e)
    row.update(hand_in_frame(mesh, body, eye, any(k in label for k in ('home', 'list', 'message', 'tap'))))
    if label.endswith('home') or label.endswith('home2'):  # the settled hold, replayed at mesh level in the twin
        row['pose_json'] = pie_pose_capture.capture_phone(body, mesh, str(folder / ('pose_' + label + '.json')))
    if label.startswith('shot_00'):
        sm = mesh.get_editor_property('static_mesh')
        bb = sm.get_bounding_box() if sm else None
        row['mesh'] = sm.get_path_name() if sm else None
        row['local_bounds'] = [v(bb.min), v(bb.max)] if bb else None
        row['sockets'] = [str(s) for s in mesh.get_all_socket_names()]
    S['rows'].append(row)


def shot(name=None):
    label = 'shot_%02d' % S['n'] + ('_' + name if name else ''); S['n'] += 1
    measure(label)
    pie_pose_capture.request_shot(S, w, folder / (label + '.png'))


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_guard.done(S)
    proof_slot.leave(S)
    (folder / 'phone.json').write_text(json.dumps(dict(reason=reason, rows=S['rows']), indent=1))
    unreal.log('[anim] phone %s %s' % (reason, folder))
    unreal.log('[anim] done')


def tick(dt):
    try:
        if not proof_guard.live(S):  # its own PIE ended or another lane's PIE is running: unregistered, do nothing
            return
        if not proof_slot.enter_once(S):
            return
        if not pie_pose_capture.collect_shot(S):
            return
        t = time.monotonic() - S['start']
        if w is None or w != proof_guard._world():
            if not resolve():
                if t > 25:
                    finish('no PIE world')
                return
            S['start'] = time.monotonic(); return
        if t > 40:
            return finish('time_cap')
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
        if S['phone'] is None:
            cls = unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C')
            ph = unreal.GameplayStatics.get_actor_of_class(w, cls)
            if not ph:
                return finish('no BP_Phone in the level')
            # T0 opens the phone by itself (story's buzz-then-rise); wait for it, film it, then ClosePhone ends T0
            if S.get('ready_t') is None:
                S['ready_t'] = t
            if not ph.get_editor_property('bOpen'):
                if t - S['ready_t'] > T0_WAIT:
                    return finish('FAILED T0 phone never opened by itself within %.1f s of the hand-off' % T0_WAIT)
                return
            if S.get('open_t') is None:
                S['open_t'] = t
                S['rows'].append(dict(t0_open_after_handoff_s=round(t - S['ready_t'], 2)))
            if t - S['open_t'] < 1.2:  # the real open, as the player sees it
                if t - S.get('t0_last', 0) > 0.3:
                    S['t0_last'] = t
                    pie_pose_capture.request_shot(S, w, folder / ('t0_open_%.1f.png' % (t - S['open_t'])))
                return
            ph.call_method('ClosePhone', ())
            S['phone'] = ph
            pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-8.0, yaw=195.0))
            S['t0'] = t + 1.2
            return
        if T10:
            return t10_tick(t)
        el = t - S['t0']
        while S['step'] < len(PLAN) and el >= PLAN[S['step']][0]:
            act = PLAN[S['step']][1]; S['step'] += 1
            if act == 'begin':
                p.call_method('BeginPhoneHold', (S['phone'],))
            elif act == 'end':
                p.call_method('EndPhoneHold', ())
            elif act == 'tap':
                p.call_method('PhoneTap', ())
            elif act == 'down':
                S['phone'].call_method('PhoneDown', ())
            elif act == 'confirm':
                S['phone'].call_method('PhoneConfirm', ())
            elif act.startswith('shoot'):
                shot(act.split(':')[1] if ':' in act else None); return  # one shot per tick
            elif act == 'finish':
                return finish(verdict())
    except Exception as e:
        S['rows'].append(dict(error=repr(e)))
        finish('error ' + repr(e))


def t10_tick(t):
    """After T0: EnterBeat 9, wait for T10 and its phone, film and judge the real raise."""
    ph = S['phone']
    if S.get('t10_sent') is None:
        d.call_method('EnterBeat', (9,)); S['t10_sent'] = t; S['t10_done'] = set()
        S['rows'].append(dict(shortcut='EnterBeat 9: the T9 payoff plays, then T10 raises the phone'))
        return
    b = d.get_editor_property('Beat')
    bid = str(b.get_editor_property('Id')) if b else 'None'
    if not (bid == 'T10' and ph.get_editor_property('bOpen')):
        if t - S['t10_sent'] > 22.0:
            return finish('FAILED the T10 phone never opened within 22 s of EnterBeat 9 (beat %s)' % bid)
        return
    S.setdefault('t10_open', t)
    el = t - S['t10_open']
    for at, label in T10_SHOTS:
        if el >= at and label not in S['t10_done']:
            S['t10_done'].add(label)
            return shot(label)  # one shot per tick
    if el > T10_SHOTS[-1][0] + 0.1:
        return finish(verdict())


proof_guard.arm(S, tick, 'phone')
