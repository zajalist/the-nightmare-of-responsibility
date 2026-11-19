"""Wake-up head check (face lane, PIE-only reads): boots the real front end into LS_WakeUp (QA save slot) and, every
tick of the sequence, logs what decides whether his own head is seen: the view target, the camera's distance to his
head bone, BP_FoAPlayer's bCameraClose / LastHeadHidden, and Face / Hair / Eyebrows hidden-in-game, visible and
recently rendered (as [hidden_in_game, visible, rendered]) for every BP_FoAPlayer. A Shot at each FOA_TIMES sequence second (default every 0.4 s from 0.4 to 6.4: Cam_POV, where he turns to the clock).
  FOA_DRIVER=Tools/Unreal/face/pie_wake_head.py bash Tools/Unreal/face/face_burst.sh wake_head_<tag> wake
Output: Saved/FaceShots/<run>/s_<seq>.png + shots.json (shots, samples)."""
import json
import os
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

RUN = os.environ.get('FOA_RUN', 'wake_head')
OUT = Path('P:/FoA/Saved/FaceShots') / RUN
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob('*.png'):
    old.unlink()
TIMES = [float(v) for v in os.environ['FOA_TIMES'].split(',')] if os.environ.get('FOA_TIMES') else [0.4 * i for i in range(1, 17)]
HEAD = ('Face', 'Hair', 'Eyebrows', 'Body')  # Body too: its neck and collar are what's left in view once the head hides
S = dict(start=time.monotonic(), phase=0, story=False, next=0, shots=[], samples=[], fin=False, h=None)
w = pc = fe = d = None


def resolve():
    global w, pc, fe, d
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return False
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
    return bool(w and fe and d)


def seq_seconds():
    sp = d.get_editor_property('SeqPlayer')
    if not sp:
        return None
    q = sp.get_current_time()
    return (q.time.frame_number.value + q.time.sub_frame) * q.rate.denominator / q.rate.numerator


def sample(s):
    pawn = unreal.GameplayStatics.get_player_character(w, 0)
    cam = pc.player_camera_manager.get_camera_location()
    vt = pc.get_view_target()
    parent = vt.get_attach_parent_actor() if vt else None
    row = dict(seq=round(s, 3), view_target=vt.get_name() if vt else None, vt_parent=parent.get_name() if parent else None,
               cam=[round(c, 1) for c in (cam.x, cam.y, cam.z)], players=[])
    # every BP_FoAPlayer, not only the pawn: the sequence may animate another instance (wake film hit11)
    for p in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C')):
        head = p.get_editor_property('Body').get_socket_location('head')
        r = dict(name=p.get_name(), pawn=p == pawn, cam_head_cm=round((cam - head).length(), 1),
                 bCameraClose=bool(p.get_editor_property('bCameraClose')), LastHeadHidden=bool(p.get_editor_property('LastHeadHidden')),
                 bCinematic=bool(p.get_editor_property('bCinematic')))
        for n in HEAD:
            c = p.get_editor_property(n)
            r[n] = [int(c.get_editor_property('hidden_in_game')), int(c.is_visible()), int(c.was_recently_rendered(0.05))]
        row['players'].append(r)
    S['samples'].append(row)


def finish(reason, err=None):
    if S['fin']:
        return
    S['fin'] = True
    proof_slot.leave(S)
    unreal.unregister_slate_post_tick_callback(S['h'])
    (OUT / 'shots.json').write_text(json.dumps(dict(reason=reason, error=err, handoff=S.get('handoff'), shots=S['shots'], samples=S['samples']), indent=1))
    unreal.log(f'[face] {RUN} finished: {reason}')


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
            S['start'] = time.monotonic()
            return
        if t > 50:
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
        if s is None or d.get_editor_property('bWakeDone'):
            if S['samples'] and d.get_editor_property('bWakeDone'):  # the hand-off: where the film ended and who has the view
                vt = pc.get_view_target()
                S['handoff'] = dict(last_seq=S['samples'][-1]['seq'], view_target=vt.get_name() if vt else None,
                                    pawn_is_view=vt == unreal.GameplayStatics.get_player_character(w, 0),
                                    wall_s=round(time.monotonic() - S['start'], 2))
                return finish('passed')
            return
        sample(s)
        if S['next'] < len(TIMES) and s >= TIMES[S['next']]:
            label = 's_%05.2f' % TIMES[S['next']]
            unreal.SystemLibrary.execute_console_command(w, f'Shot filename={OUT.as_posix()}/{label}.png -nosuffix', pc)
            S['shots'].append(dict(label=label, seq=round(s, 3)))
            S['next'] += 1
    except Exception as e:  # noqa: BLE001
        import traceback
        finish('error', traceback.format_exc())


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[face] wake head check armed ' + RUN)
