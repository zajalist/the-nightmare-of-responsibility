"""PIE capture of the whole LS_WakeUp film (run by record_anim.sh as FOA_PIE_SCRIPT): one Shot at each listed sequence
time, plus every rendered frame of the slap (12.0 to 12.9 s) under 0.2 global time dilation so the strike, contact and give are all
on disk. Each shot logs the sequence time it actually rendered at (shots land on the next frame). Restores time dilation 1.
Ends with '[anim] done'. Output: Saved/AnimShots/wake_film/<stamp>/ (s_<seq>.png, film.json)."""
import datetime
import os
import json
import time
from pathlib import Path

import unreal

import sys as _sys
_sys.path.insert(0, 'P:/FoA/Tools/Unreal/player')
import proof_slot  # noqa: E402  (QA save slot: never the player's FoA.sav)

w = p = pc = fe = d = None  # resolved on the first tick that has a PIE world (PIE can start slower than the runner)


def resolve():
    global w, pc, fe, d
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not w:
        return False
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    fe = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C'))
    d = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C'))
    return bool(w and fe and d)

TIMES = [float(v) for v in os.environ['FOA_TIMES'].split(',')] if os.environ.get('FOA_TIMES') else [1.0, 2.0, 3.2, 4.4, 5.2, 5.9, 6.6, 7.6, 8.4, 9.6, 10.4, 11.1, 11.5, 11.8, 13.0, 13.7, 14.3, 14.8,
         15.4, 16.4, 17.0, 17.6, 18.3, 18.8]
SLOW = tuple(float(v) for v in os.environ.get('FOA_SLOW', '12.0,12.9').split(','))
folder = Path('P:/FoA/Saved/AnimShots/wake_film') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
folder.mkdir(parents=True, exist_ok=True)
S = dict(start=time.monotonic(), phase=0, story=False, next=0, slow=False, rows=[], fin=False, n=0, clock=None, judder=[])


def cmd(c):
    unreal.SystemLibrary.execute_console_command(w, c, pc)


def seq_seconds():
    sp = d.get_editor_property('SeqPlayer')
    if not sp:
        return None
    q = sp.get_current_time()
    return (q.time.frame_number.value + q.time.sub_frame) * q.rate.denominator / q.rate.numerator


def shot(s, label):
    S['rows'].append(dict(label=label, requested_at=round(s, 3)))
    cmd('Shot showui filename=' + str(folder / (label + '.png')) + ' -nosuffix')


def contact_sample(s):
    """Where the visible Teen palm really is versus the clock lid (world lane: 'the palm lands beside the clock')."""
    if S.get('pawn') is None:
        S['pawn'] = unreal.GameplayStatics.get_player_character(w, 0)
    pw = S['pawn']
    body, src = pw.get_editor_property('Body'), pw.get_editor_property('Mesh')
    row = dict(seq=round(s, 3))
    # which BP_FoAPlayer does LS_WakeUp animate? (hit11: the PIE pawn's hand idled 75 cm from the clock while a hand slapped it)
    row['players'] = []
    try:
        for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Game/FoA/Characters/Player/BP_FoAPlayer.BP_FoAPlayer_C')):
            b = a.get_editor_property('Body')
            v = b.get_socket_location('hand_r')
            bo_o, bo_e, _r = unreal.SystemLibrary.get_component_bounds(b)  # render bounds: they follow the pose even if a bone read were stale
            row['players'].append(dict(name=a.get_name(), pawn=a == pw, hand_r=[round(v.x, 1), round(v.y, 1), round(v.z, 1)],
                                       rendered=bool(b.was_recently_rendered(0.2)), hidden=bool(a.get_editor_property('hidden')),
                                       actor=[round(c, 1) for c in (a.get_actor_location().x, a.get_actor_location().y, a.get_actor_location().z)],
                                       body_bounds=[[round(bo_o.x, 1), round(bo_o.y, 1), round(bo_o.z, 1)], [round(bo_e.x, 1), round(bo_e.y, 1), round(bo_e.z, 1)]],
                                       tick=str(b.get_editor_property('visibility_based_anim_tick_option')),
                                       src_tick=str(a.get_editor_property('Mesh').get_editor_property('visibility_based_anim_tick_option'))))
    except Exception as e:  # noqa: BLE001
        row['players'].append(repr(e)[:100])
    for side in ('l', 'r'):
        for bone in ('hand_', 'middle_01_', 'middle_03_'):
            try:
                v = body.get_socket_location(bone + side)
                row['teen_' + bone + side] = [round(v.x, 1), round(v.y, 1), round(v.z, 1)]
            except Exception:
                pass
        v = src.get_socket_location('hand_' + side)
        row['manny_hand_' + side] = [round(v.x, 1), round(v.y, 1), round(v.z, 1)]
    for bone in ('thumb_01_r', 'thumb_02_r', 'thumb_03_r', 'index_01_r', 'pinky_01_r'):  # the slap thumb against the palm (slap_thumb.py)
        v = body.get_socket_location(bone)
        row['teen_' + bone] = [round(v.x, 2), round(v.y, 2), round(v.z, 2)]
    try:  # slap_thumb.py: the Teen thumb layer's weight (source clip curve FoA_SlapThumb, pushed by UpdateSlapThumb)
        row['slap_thumb_w'] = round(body.get_anim_instance().get_editor_property('SlapThumbWeight'), 3)
        row['slap_thumb_curve'] = round(src.get_anim_instance().get_curve_value('FoA_SlapThumb'), 3)
    except Exception as e:  # noqa: BLE001
        row['slap_thumb_w'] = repr(e)[:80]
    if S['clock']:
        v = S['clock'].get_world_location()
        row['clock_splats'] = [round(v.x, 1), round(v.y, 1), round(v.z, 1)]
        o, e = S['clock'].get_owner().get_actor_bounds(False)
        row['clock_bounds'] = [[round(o.x, 1), round(o.y, 1), round(o.z, 1)], [round(e.x, 1), round(e.y, 1), round(e.z, 1)]]
    S.setdefault('contact', []).append(row)


def finish(reason):
    if S['fin']:
        return
    S['fin'] = True
    proof_slot.leave(S)
    unreal.GameplayStatics.set_global_time_dilation(w, 1.0)
    unreal.unregister_slate_post_tick_callback(S['h'])
    j = S['judder']
    span = {k: round(max(r[k] for r in j) - min(r[k] for r in j), 2) for k in ('x', 'y', 'z', 'roll', 'pitch')} if j else None
    (folder / 'film.json').write_text(json.dumps(dict(reason=reason, clock_judder_span_4_to_6s=span, clock_samples=j, contact=S.get('contact', []), rows=S['rows']), indent=1))
    unreal.log('[anim] clock judder span %s over %d samples' % (span, len(j)))
    unreal.log('[anim] wake film %s %d shots %s' % (reason, len(S['rows']), folder))
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
        if t > 43:
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
            if S['rows'] and d.get_editor_property('bWakeDone'):
                return finish('passed')
            return
        if 4.0 <= s <= 6.2:  # the POV holds on the ringing clock: sample its splat mesh to prove the judder
            if S['clock'] is None:
                cls = unreal.load_class(None, '/Game/FoA/VFX/Sand/BP_SandMaterialize.BP_SandMaterialize_C')
                hits = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, cls) if 'SandClock_WakeUp' in a.get_actor_label()]
                S['clock'] = next((c for c in hits[0].get_components_by_class(unreal.StaticMeshComponent) if c.get_name() == 'Splats'), False) if hits else False
            if S['clock']:
                xf = S['clock'].get_world_transform(); r = xf.rotation.rotator(); v = xf.translation
                S['judder'].append(dict(seq=round(s, 3), x=v.x, y=v.y, z=v.z, roll=r.roll, pitch=r.pitch))
        if not S['slow'] and SLOW[0] <= s < SLOW[1]:
            unreal.GameplayStatics.set_global_time_dilation(w, 0.2); S['slow'] = True
        if S['slow'] and s >= SLOW[1]:
            unreal.GameplayStatics.set_global_time_dilation(w, 1.0); S['slow'] = None
        if S['slow'] is True:
            shot(s, 'slap_%03d' % S['n']); S['n'] += 1
            contact_sample(s)
            return
        if S['next'] < len(TIMES) and s >= TIMES[S['next']]:
            shot(s, 's_%05.2f' % TIMES[S['next']])
            S['next'] += 1
    except Exception as e:
        S['rows'].append(dict(error=repr(e)))
        finish('error ' + repr(e))


S['h'] = unreal.register_slate_post_tick_callback(tick)
unreal.log('[anim] wake film armed')
