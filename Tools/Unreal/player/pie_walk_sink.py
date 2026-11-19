"""PIE proof of the first-person steady eye (fp_steady_eye.py; main 2026-11-10: FP eye within +-1.5 cm walking and
running). Run by record_anim.sh as FOA_PIE_SCRIPT. Skips the wake-up, closes the T0 phone (QA save slot), then walks
down the room and back at 130 cm/s, and runs down and back at 300 cm/s, logging every tick: camera z, Body head and
pelvis z, the Manny source pelvis z, the capsule z, ground speed, bCameraClose and the view target.
Verdict per segment, after it settles (walk 1.0 s, run 1.2 s): the eye's height above the eased capsule (camera z minus
SteadyFPEye's FPActorZ) spans <= 3 cm with the pawn as the view target; camera z span (with floor steps) is reported too.
The diagnosis run (walk_sink3, 20261110_014240) toggled stride warping and foot IK; that A/B is in its sink.json.
Ends with '[anim] done'. Output: Saved/AnimShots/walk_sink/<stamp>/sink.json."""
import datetime
import json
import os
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

folder = Path('P:/FoA/Saved/AnimShots/walk_sink') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
SEGMENTS = (('walk', 130.0, 1, 2.6, 1.0), ('walk_back', 130.0, -1, 2.6, 1.0), ('run', 300.0, 1, 2.0, 1.2), ('run_back', 300.0, -1, 2.0, 1.2))  # name, speed, direction, s, settle
# FOA_SINK_SET=1 (main: why did walk_sink3's run leave FollowCamera?): walk_sink3's third segment ran the console
# 'set ABP_FoAPlayer_C FootIKEnabled False' every frame, and the view sat at capsule +79.7 right after it. Replay that
# segment before the runs, logging the camera's activity and attach parent, to prove or clear it.
SET_TEST = os.environ.get('FOA_SINK_SET') == '1'
if SET_TEST:
    SEGMENTS = SEGMENTS[:2] + (('walk_set', 130.0, 1, 2.6, 1.0),) + SEGMENTS[2:]
SPAN_MAX = 3.0  # cm: +-1.5
START = unreal.Vector(-280.0, 0.0, 87.15)
S = dict(start=time.monotonic(), phase=0, story=False, skipped=False, rows=[], fin=False, seg=-1, seg_t=None, w=None)


def resolve():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return False
    S.update(w=w, p=unreal.GameplayStatics.get_player_character(w, 0), pc=unreal.GameplayStatics.get_player_controller(w, 0),
             fe=unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')),
             d=unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')))
    return bool(S['p'] and S['fe'] and S['d'])


def parent_of(c):
    par = c.get_attach_parent()
    return (par.get_name() if par else 'none') + ':' + str(c.get_attach_socket_name())


def sample(seg):
    p = S['p']
    body, src = p.get_editor_property('Body'), p.get_editor_property('Mesh')
    vt = S['pc'].get_view_target()
    S['rows'].append(dict(seg=seg, t=round(time.monotonic() - S['seg_t'], 3), cam_z=round(S['pc'].player_camera_manager.get_camera_location().z, 2),
                          head_z=round(body.get_socket_location('head').z, 2), pelvis_z=round(body.get_socket_location('pelvis').z, 2),
                          src_pelvis_z=round(src.get_socket_location('pelvis').z, 2), actor_z=round(p.get_actor_location().z, 2),
                          speed=round(p.get_velocity().length(), 1), close=bool(p.get_editor_property('bCameraClose')),
                          eye_h=round(S['pc'].player_camera_manager.get_camera_location().z - p.get_editor_property('FPActorZ'), 2),
                          pawn_view=vt == p, cam_active=bool(p.get_editor_property('FollowCamera').is_active()),
                          cam_parent=parent_of(p.get_editor_property('FollowCamera'))))


def report():
    out = {}
    for name, _speed, _dir, _len, settle in SEGMENTS:
        late = [r for r in S['rows'] if r.get('seg') == name and r.get('t', -1) >= settle]  # samples only, settled
        if not late:
            continue
        span = lambda k: round(max(r[k] for r in late) - min(r[k] for r in late), 2)  # noqa: E731
        out[name] = dict(eye_span=span('eye_h'), cam_span=span('cam_z'), head_span=span('head_z'), pelvis_span=span('pelvis_z'), actor_span=span('actor_z'),
                         speed=round(sum(r['speed'] for r in late) / len(late), 1), samples=len(late),
                         pawn_view=all(r['pawn_view'] for r in late), close=all(r['close'] for r in late),
                         cam_active=all(r['cam_active'] for r in late), cam_parents=sorted({r['cam_parent'] for r in late}))
        out[name]['ok'] = out[name]['eye_span'] <= SPAN_MAX and out[name]['pawn_view']  # the bob; cam_span adds floor steps (a rug lifts the capsule ~2.7 cm)
    return out


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_slot.leave(S)
    try:
        S['p'].get_editor_property('CharacterMovement').set_editor_property('max_walk_speed', S.get('speed0', 130.0), unreal.PropertyAccessChangeNotifyMode.NEVER)
    except Exception:  # noqa: BLE001
        pass
    unreal.unregister_slate_post_tick_callback(S['h'])
    rep = report()
    if reason == 'passed' and (len(rep) < len(SEGMENTS) or not all(v['ok'] for v in rep.values())):
        reason = 'FAILED ' + '; '.join('%s eye span %s cm (pawn view %s)' % (k, v['eye_span'], v['pawn_view']) for k, v in rep.items() if not v['ok']) or 'FAILED missing segments'
    (folder / 'sink.json').write_text(json.dumps(dict(reason=reason, report=rep, rows=S['rows']), indent=1))
    unreal.log('[anim] walk sink %s %s %s' % (reason, json.dumps(rep), folder))
    unreal.log('[anim] done')


def tick(dt):
    try:
        if not proof_slot.enter_once(S):
            return
        t = time.monotonic() - S['start']
        if S['w'] is None or not unreal.SystemLibrary.is_valid(S['w']):
            if not resolve():
                if t > 25:
                    finish('no PIE world')
                return
            S['start'] = time.monotonic(); return
        if t > 40:
            return finish('time_cap')
        fe, d, p = S['fe'], S['d'], S['p']
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
        if S['seg'] == -1:  # T0 opens the phone by itself; close it the way the player does
            ph = unreal.GameplayStatics.get_actor_of_class(S['w'], unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
            S.setdefault('ready', t)
            if not (ph and ph.get_editor_property('bOpen')) and t - S['ready'] < 5.5:
                return
            if ph and ph.get_editor_property('bOpen'):
                ph.call_method('ClosePhone', ())
            S['speed0'] = p.get_editor_property('CharacterMovement').get_editor_property('max_walk_speed')
            S['seg'] = 0; S['seg_t'] = None
            return
        if S['seg'] >= len(SEGMENTS):
            return finish('passed')
        name, speed, direction, seg_len, _settle = SEGMENTS[S['seg']]
        if S['seg_t'] is None:  # set the segment up: down the room from START, or back from where the last one stopped
            yaw = 0.0 if direction > 0 else 180.0
            if direction > 0:
                p.set_actor_location_and_rotation(START, unreal.Rotator(0, 0, 0), False, True)
            else:
                p.set_actor_rotation(unreal.Rotator(0, 0, yaw), True)
            S['pc'].set_control_rotation(unreal.Rotator(roll=0.0, pitch=-5.0, yaw=yaw))
            # NEVER notify: a notified change on a PIE component reruns BP_FoAPlayer's construction script, which put FollowCamera
            # back on CameraBoom:SpringEndpoint (walk_set 02:43: the parent flipped on the first run tick; walk_sink3's 'run' view)
            p.get_editor_property('CharacterMovement').set_editor_property('max_walk_speed', speed, unreal.PropertyAccessChangeNotifyMode.NEVER)
            S['seg_t'] = time.monotonic() + 0.4  # standing 0.4 s first
            return
        el = time.monotonic() - S['seg_t']
        if el >= 0:
            p.add_movement_input(unreal.Vector(direction, 0, 0), 1.0, False)
        if name == 'walk_set':
            unreal.SystemLibrary.execute_console_command(S['w'], 'set ABP_FoAPlayer_C FootIKEnabled False', S['pc'])
        sample(name)
        if el > seg_len:
            S['seg'] += 1; S['seg_t'] = None
            (folder / 'sink.json').write_text(json.dumps(dict(reason='partial', report=report(), rows=S['rows'])))  # survives a capped burst
            unreal.log('[anim] walk sink segment %s %s' % (name, json.dumps(report().get(name))))
    except Exception as e:  # noqa: BLE001
        S['rows'].append(dict(error=repr(e)))
        finish('error ' + repr(e))


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[anim] walk sink armed')
