"""PIE review of first-person visuals (run by record_anim.sh as FOA_PIE_SCRIPT). Skips the wake-up early, then shoots:
start (FOA_YAW), look down 45/75 (body awareness), a 2 s walk (bob), crouch, and a wall nudge (near-plane clipping).
Each shot also logs the camera-to-head distance and which head parts render. PIE-only: moves only the PIE pawn.
Ends with '[anim] done'."""
import datetime
import json
import os
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

w = p = pc = fe = d = None  # resolved on the first tick that has a PIE world (PIE can start slower than the runner)


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

YAW = float(os.environ.get('FOA_YAW', '200'))
folder = Path('P:/FoA/Saved/AnimShots/fp_review') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(start=time.monotonic(), phase=0, story=False, skipped=False, done_at=None, step=0, step_t=None, rows=[], fin=False)


def rot(pitch, yaw):
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))


def walk():
    fwd = p.get_actor_forward_vector()
    p.add_movement_input(fwd, 1.0, False)


def tp_cam(yaw_off, dist=170.0):
    """Third-person view of the idle posture through a temporary PIE CameraActor (the head shows: the view target is
    not the pawn). tp_back() restores the pawn view and destroys it."""
    import math
    face = p.get_editor_property('Face')
    head = face.get_socket_location('head')
    yaw = p.get_actor_rotation().yaw + yaw_off
    loc = unreal.Vector(head.x + dist * math.cos(math.radians(yaw)), head.y + dist * math.sin(math.radians(yaw)), head.z - 20.0)
    rot = unreal.MathLibrary.find_look_at_rotation(loc, head - unreal.Vector(0, 0, 50.0))
    if not S.get('cam'):  # the PIE copy of BP_MenuCamera (no runtime spawning from Python): moved, then restored
        cls = unreal.load_class(None, '/Game/FoA/UI/Framework/BP_MenuCamera.BP_MenuCamera_C')
        S['cam'] = unreal.GameplayStatics.get_actor_of_class(w, cls)
        S['cam_home'] = (S['cam'].get_actor_location(), S['cam'].get_actor_rotation())
    S['cam'].set_actor_location_and_rotation(loc, rot, False, True)
    pc.set_view_target_with_blend(S['cam'], 0.0)


def tp_back():
    pc.set_view_target_with_blend(p, 0.0)
    if S.get('cam'):
        S['cam'].set_actor_location_and_rotation(S['cam_home'][0], S['cam_home'][1], False, True); S['cam'] = None


def drawer_setup():
    """Stand 75 cm in front of the first container (the drawer) facing it, with the view level."""
    import math
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Container.BP_Container_C')
    conts = unreal.GameplayStatics.get_all_actors_of_class(w, cls)
    S['cont'] = conts[0] if conts else None
    if not S['cont']:
        return
    o, ext = S['cont'].get_actor_bounds(False)
    f = S['cont'].get_actor_forward_vector()
    spot = unreal.Vector(o.x + f.x * (ext.x + 75.0), o.y + f.y * (ext.x + 75.0), p.get_actor_location().z)
    yaw = math.degrees(math.atan2(o.y - spot.y, o.x - spot.x))
    p.set_actor_location_and_rotation(spot, unreal.Rotator(0, 0, yaw), False, True)
    rot(-8.0, yaw)
    S['rows'].append(dict(drawer=S['cont'].get_actor_label(), spot=str(spot), yaw=yaw))


def drawer_go():
    if not S.get('cont'):
        return
    m = unreal.load_asset('/Game/FoA/Characters/Player/Montages/AM_FoA_OpenDrawer')
    if m:
        p.play_anim_montage(m, 1.0, 'None')
    p.call_method('LockForInteraction', (1.8, S['cont']))


def wall():
    p.set_actor_location_and_rotation(unreal.Vector(300.0, 230.0, p.get_actor_location().z), unreal.Rotator(0, 0, 90), False, True)
    rot(-5.0, 90.0)


# (seconds after the previous step, action, shot label)
STEPS = [(0.6, lambda: rot(-10.0, YAW), 'start'), (0.6, None, 'start_settled'), (0.1, lambda: rot(-45.0, YAW), None),
         (0.5, None, 'down45'), (0.1, lambda: rot(-75.0, YAW), None), (0.5, None, 'down75'), (0.05, lambda: body_diag(), None),
         (0.1, lambda: rot(-8.0, YAW), None), (0.4, None, None), ('walk', 0.5, 'walk_05'), ('walk', 0.5, 'walk_10'),
         ('walk', 0.5, 'walk_15'), ('walk', 0.5, 'walk_20'), (0.6, None, 'stopped'), (1.0, lambda: tp_cam(0.0), None), (0.5, None, 'tp_idle_front'),
         (0.1, lambda: tp_cam(90.0), None), (0.5, None, 'tp_idle_side'), (0.1, tp_back, None),
         (0.1, lambda: p.crouch(False), None), (0.8, None, 'crouch'), (0.1, lambda: p.un_crouch(False), None),
         (0.8, None, 'uncrouch'), (0.1, wall, None), (0.6, None, 'wall'), (0.1, drawer_setup, None),
         (0.5, None, 'drawer_before'), (0.1, drawer_go, None), (0.4, None, 'drawer_04'), (0.4, None, 'drawer_08'),
         (0.5, None, 'drawer_13'), (0.8, None, 'drawer_after')]


PARTS = ('Body', 'Face', 'Hair', 'Eyebrows', 'StartOutfit', 'StartPants', 'StartSocks', 'Shirt', 'Trousers', 'BootsWornMesh')


def body_diag():
    out = {}
    for n in PARTS:
        try:
            c = p.get_editor_property(n)
        except Exception:
            continue
        row = dict(visible=c.is_visible())
        for k in ('owner_no_see', 'only_owner_see', 'hidden_in_game'):
            try:
                row[k] = c.get_editor_property(k)
            except Exception:
                pass
        try:
            row['mesh'] = c.get_skeletal_mesh_asset().get_name() if c.get_skeletal_mesh_asset() else None
        except Exception:
            pass
        row['loc'] = str(c.get_world_location())
        out[n] = row
    body = p.get_editor_property('Body')
    out['body_head'] = str(body.get_socket_location('head'))
    out['face_head'] = str(p.get_editor_property('Face').get_socket_location('head'))
    out['body_pelvis'] = str(body.get_socket_location('pelvis'))
    out['source_head'] = str(p.get_editor_property('Mesh').get_socket_location('head'))
    S['rows'].append(dict(label='body_diag', **out))


def walk_sample():
    body = p.get_editor_property('Body')
    cam = pc.player_camera_manager.get_camera_location()
    S.setdefault('walklog', []).append(dict(cam_z=round(cam.z, 1), body_head_z=round(body.get_socket_location('head').z, 1),
        face_head_z=round(p.get_editor_property('Face').get_socket_location('head').z, 1),
        pelvis_z=round(body.get_socket_location('pelvis').z, 1), src_head_z=round(p.get_editor_property('Mesh').get_socket_location('head').z, 1),
        speed=round(p.get_velocity().length(), 1)))


def shot(label):
    face = p.get_editor_property('Face')
    cam = pc.player_camera_manager.get_camera_location()
    row = dict(label=label, cam=[round(cam.x, 1), round(cam.y, 1), round(cam.z, 1)],
               cam_head_cm=round((cam - face.get_socket_location('head')).length(), 1),
               rot=str(pc.player_camera_manager.get_camera_rotation()), pawn=str(p.get_actor_location()),
               crouched=p.get_editor_property('bIsCrouched'), speed=round(p.get_velocity().length(), 1))
    for part in ('Face', 'Hair', 'Eyebrows'):
        try:
            row[part] = p.get_editor_property(part).is_visible()
        except Exception:
            row[part] = 'n/a'
    S['rows'].append(row)
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=' + str(folder / (label + '.png')) + ' -nosuffix', pc)


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_slot.leave(S)
    try:
        tp_back()
    except Exception:
        pass
    unreal.unregister_slate_post_tick_callback(S['h'])
    (folder / 'review.json').write_text(json.dumps(dict(reason=reason, rows=S['rows'], walklog=S.get('walklog', [])), indent=1))
    unreal.log('[anim] fp review %s %s' % (reason, folder))
    unreal.log('[anim] done')


def tick(dt):
    try:
        if not proof_slot.enter_once(S):
            return
        t = time.monotonic() - S['start']
        if w is None or not unreal.SystemLibrary.is_valid(w):
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
        if S['done_at'] is None:
            S['done_at'] = S['step_t'] = t
        if S['step'] >= len(STEPS):
            return finish('passed')
        st = STEPS[S['step']]
        if st[0] == 'walk':
            walk()
            walk_sample()
            wait, act, label = st[1], None, st[2]
        else:
            wait, act, label = st
        if t - S['step_t'] >= wait:
            if act:
                act()
            if label:
                shot(label)
            S['step'] += 1
            S['step_t'] = t
    except Exception as e:
        S['rows'].append(dict(error=repr(e)))
        finish('error ' + repr(e))


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[anim] fp review armed')
