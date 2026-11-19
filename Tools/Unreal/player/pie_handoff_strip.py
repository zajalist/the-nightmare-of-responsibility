"""PIE proof of the wake-up hand-off into first person, EVERY rendered frame (run by record_anim.sh as FOA_PIE_SCRIPT).
Fast-forwards the front end (splash, title, Wake up, story), plays LS_WakeUp, and from 0.6 s before its end (or 0.3 s
before a skip with FOA_SKIP=<seq seconds>) caps the game at 12 fps and requests a Shot on every Slate tick, so each
rendered frame lands on disk, until 1.4 s after the director's bWakeDone. Each frame also logs the sequence time, the
view target, the camera-to-head distance and whether Face/Hair/Eyebrows render, to <folder>/frames.json.
Then FOA_YAWS (comma list) sets the control yaw in turn and shoots one frame each (pick the gameplay start yaw).
Never moves the pawn or edits assets. Ends with '[anim] done'."""
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

SKIP = float(os.environ.get('FOA_SKIP', '0') or 0)
YAWS = [float(v) for v in os.environ.get('FOA_YAWS', '').split(',') if v]
DILATE = float(os.environ.get('FOA_DILATE', '0.2'))  # game time runs at this rate while every frame is shot
tag = 'skip' if SKIP else 'normal'
folder = Path('P:/FoA/Saved/AnimShots/handoff') / (datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + tag)
folder.mkdir(parents=True, exist_ok=True)
S = dict(done_game=None, start=time.monotonic(), phase=0, h=None, rows=[], n=0, recording=False, done_at=None, yaw_i=0, yaw_t=None,
         story=False, wake=False, skipped=False, finished=False, end_seq=None, ticks=[], rec_t0=None)


def log(msg):
    unreal.log('[anim] ' + msg)


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def seq_seconds():
    sp = d.get_editor_property('SeqPlayer')
    if not sp:
        return None
    q = sp.get_current_time()
    return (q.time.frame_number.value + q.time.sub_frame) * q.rate.denominator / q.rate.numerator


def shoot(label):
    unreal.SystemLibrary.execute_console_command(w, 'Shot showui filename=' + str(folder / (label + '.png')) + ' -nosuffix', pc)


def frame_row(t, s):
    face = p.get_editor_property('Face')
    cam = pc.player_camera_manager.get_camera_location()
    head = face.get_socket_location('head')
    row = dict(i=S['n'], t=round(t, 3), game_t=round(unreal.GameplayStatics.get_time_seconds(w), 4), seq=None if s is None else round(s, 3), done=d.get_editor_property('bWakeDone'),
               view=pc.get_view_target().get_name(), cam=vec(cam), cam_head_cm=round((cam - head).length(), 1),
               cam_rot=str(pc.player_camera_manager.get_camera_rotation()), ctrl=str(pc.get_control_rotation()),
               pawn=vec(p.get_actor_location()), cinematic=p.get_editor_property('bCinematic'),
               handoff_flag=p.get_editor_property('bHandoffFadeIn'))
    for part in ('Face', 'Hair', 'Eyebrows'):
        try:
            c = p.get_editor_property(part)
            row[part] = bool(c.is_visible() and not c.get_editor_property('hidden_in_game'))
        except Exception as e:  # a part may be missing on this body
            row[part] = 'n/a'
    return row


def finish(reason):
    if S['finished']:
        return
    S['finished'] = True
    proof_slot.leave(S)
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0', pc)
    unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
    unreal.unregister_slate_post_tick_callback(S['h'])
    tk, r0 = S['ticks'], S['rec_t0'] or 0
    before = [x for x in tk if r0 - 2.0 <= x < r0]
    during = [x for x in tk if x >= r0 and (S['done_at'] is None or x <= S['done_at'] + 1.4)]
    fps = dict(before_recording=round(len(before) / 2.0, 1),
               while_shooting=round((len(during) - 1) / max(1e-3, during[-1] - during[0]), 1) if len(during) > 1 else None)
    (folder / 'frames.json').write_text(json.dumps(dict(reason=reason, skip=SKIP, fps=fps, rows=S['rows']), indent=1))
    log('fps %s' % fps)
    log('handoff strip %s %s frames=%d folder=%s' % (tag, reason, S['n'], folder))
    log('done')


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
        if t > 42:
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
        s = seq_seconds()
        done = d.get_editor_property('bWakeDone')
        if s is not None and not done:
            S['wake'] = True
            if S['end_seq'] is None:
                sp = d.get_editor_property('SeqPlayer')
                S['end_seq'] = sp.get_duration().time.frame_number.value / 30.0 if sp else 19.1
        if not S['wake']:
            return
        S['ticks'].append(t)
        start_at = (SKIP - 0.2) if SKIP else (S['end_seq'] - 0.4)
        if not S['recording'] and not done and s is not None and s >= start_at:
            unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 12', pc)
            unreal.GameplayStatics.set_global_time_dilation(w, DILATE)  # frame-accurate in game time despite slow shots
            S['recording'] = True
            S['rec_t0'] = t
            log('recording from seq %.2f' % s)
        if SKIP and not S['skipped'] and s is not None and s >= SKIP:
            d.call_method('SkipWakeUp', ()); S['skipped'] = True
            log('skip at seq %.2f' % s)
        if done and S['done_at'] is None:
            S['done_at'] = t
            S['done_game'] = unreal.GameplayStatics.get_time_seconds(w)
        if S['recording']:
            S['rows'].append(frame_row(t, s))
            if S['n'] % 5 == 0:  # keep the log on disk even if the burst is capped before finish()
                (folder / 'frames.json').write_text(json.dumps(dict(reason='partial', skip=SKIP, rows=S['rows']), indent=1))
            shoot('f%03d' % S['n'])
            S['n'] += 1
            if S['done_at'] is not None and unreal.GameplayStatics.get_time_seconds(w) - S['done_game'] > 0.8:
                S['recording'] = False
                unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0', pc)
                unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
                S['yaw_t'] = t
            return
        if S['yaw_t'] is not None:
            if S['yaw_i'] >= len(YAWS) * 2:
                return finish('passed')
            if t - S['yaw_t'] > 0.6:
                k, half = divmod(S['yaw_i'], 2)
                if half == 0:
                    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=-10.0, yaw=YAWS[k]))
                else:
                    shoot('yaw_%03d' % int(YAWS[k]))
                    S['rows'].append(dict(yaw_shot=YAWS[k], **frame_row(t, s)))
                S['yaw_i'] += 1
                S['yaw_t'] = t
    except Exception as e:
        S['rows'].append(dict(error=repr(e)))
        finish('error ' + repr(e))


S['h'] = unreal.register_slate_post_tick_callback(tick)
log('handoff strip armed %s' % tag)
