"""First-person arm proof (face lane, PIE-only changes): boot through the real front end, close the T0 phone, stand
100 cm from the CommodeDrawer facing it, Use it (the reach), and shoot the first-person view in three variants,
alternating every other frame through the reach:
  A  as shipped;  B  BP_FoAPlayer.CharacterLight off (PIE copy only);  C  B plus skin tint 0.5 (a PIE-only MID)
Run inside face_burst.sh:  bash Tools/Unreal/face/face_burst.sh fp_arm fp  (FOA_MODE is ignored here)
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/pie_fp_arm.py FOA_RUN=fp_arm
Output: Saved/FaceShots/<run>/{A,B,C}_NN.png + shots.json (luma of the arm region is measured afterwards)."""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

RUN = os.environ.get('FOA_RUN', 'fp_arm')
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
old_ctx = (str(gi.get_editor_property('SaveSlot')), set(gi.get_editor_property('Knowledge')), list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext', ('FoA_QA_FaceArm', set(), []))
S = dict(t0=time.time(), h=None, actions=set(), story=False, skip=False, phase='boot', done=False, shots=[], frame=0,
         n=0, error=None, mids=None)


def player():
    return unreal.GameplayStatics.get_player_character(w, 0)


def light(on):
    p = player()
    for c in p.get_components_by_class(unreal.PointLightComponent):
        if c.get_name() == 'CharacterLight':
            c.set_visibility(on)


def tint(v):
    p = player()
    body = next(c for c in p.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')
    if S['mids'] is None:
        S['mids'] = []
        for i in range(body.get_num_materials()):
            m = body.get_material(i)
            if m and 'MI_Teen_Skin' in m.get_name():
                S['mids'].append(body.create_dynamic_material_instance(i, m))
    for mid in S['mids']:
        mid.set_vector_parameter_value('Tint', unreal.LinearColor(v, v, v, 1.0))


def variant(k):
    light(k == 'A')
    tint(0.5 if k == 'C' else 0.66)


def place_at_drawer():
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/BP_Interactable.BP_Interactable_C')
    a = next(x for x in unreal.GameplayStatics.get_all_actors_of_class(w, cls)
             if str(x.get_editor_property('InteractionKey')) == 'CommodeDrawer')
    m = a.get_editor_property('Mesh')
    lo, hi = m.get_local_bounds()
    o = m.get_world_transform().transform_location((lo + hi) * 0.5)
    p = player()
    to_room = unreal.Vector(-o.x, -o.y, 0.0)
    to_room = to_room * (1.0 / max(1.0, to_room.length()))
    spot = unreal.Vector(max(-330.0, min(330.0, o.x + to_room.x * 100.0)), max(-260.0, min(260.0, o.y + to_room.y * 100.0)),
                         p.get_actor_location().z)
    p.set_actor_location_and_rotation(spot, unreal.Rotator(0, 0, math.degrees(math.atan2(o.y - spot.y, o.x - spot.x))), False, True)
    look = unreal.MathLibrary.find_look_at_rotation(pc.player_camera_manager.get_camera_location(), o)
    pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=look.pitch, yaw=look.yaw))
    S['target'] = a


def shot(label):
    unreal.SystemLibrary.execute_console_command(w, f'Shot filename={OUT.as_posix()}/{label}.png -nosuffix', pc)
    S['shots'].append(dict(label=label, t=round(time.time() - S['t0'], 2)))


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        variant('A')
        gi.call_method('SetProofProgressContext', old_ctx)
        unreal.GameplayStatics.delete_game_in_slot('FoA_QA_FaceArm', 0)
    except Exception:
        S['error'] = (S['error'] or '') + traceback.format_exc()
    (OUT / 'shots.json').write_text(json.dumps(dict(reason=reason, error=S['error'], focus=S.get('focus'), shots=S['shots']), indent=1))
    unreal.log(f'[face] {RUN} finished: {reason}')


def tick(dt):
    try:
        t = time.time() - S['t0']
        if t > 46:
            return finish('timeout')
        if S['phase'] == 'boot':
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
            if fe.get_editor_property('bInGameplay') and d.get_editor_property('SeqPlayer') and not d.get_editor_property('bWakeDone') and not S['skip']:
                d.call_method('SkipWakeUp', ())
                S['skip'] = True
                S['skip_t'] = t
                return
            if d.get_editor_property('bWakeDone') and S['skip'] and t - S['skip_t'] > 2.5:
                ph = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
                if ph and ph.get_editor_property('bOpen'):
                    ph.call_method('ClosePhone', ())
                d.call_method('ReportEvent', (unreal.Name('PhoneWakeUp'),))
                unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
                unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
                S['phase'], S['pt'] = 'place', t + 1.2
            return
        if S['phase'] == 'place' and t > S['pt']:
            pc.set_view_target_with_blend(player(), 0.0)
            place_at_drawer()
            S['phase'], S['pt'] = 'use', t + 0.8
            return
        if S['phase'] == 'use' and t > S['pt']:
            it = player().get_component_by_class(unreal.load_class(None, '/Game/FoA/Gameplay/BPC_Interactor.BPC_Interactor_C'))
            if it.get_editor_property('Target') != S['target'] and t - S['pt'] < 2.0:
                return  # let the focus scan pick the drawer up, as the player would
            S['focus'] = str(it.get_editor_property('Target').get_actor_label()) if it.get_editor_property('Target') else None
            it.call_method('Interact', ())
            S['phase'], S['pt'] = 'reach', t
            return
        if S['phase'] == 'reach':
            if t - S['pt'] > 6.5:
                return finish('done')
            k = 'ABC'[(S['frame'] // 3) % 3]
            if S['frame'] % 3 == 0:
                variant(k)
            elif S['frame'] % 3 == 2 and t - S['pt'] > 1.0:
                m = player().get_current_montage()
                S['shots'].append(dict(montage=m.get_name() if m else None, approaching=player().get_editor_property('bApproaching')))
                shot(f'{k}_{S["n"]:02d}')
                if k == 'C':
                    S['n'] += 1
            S['frame'] += 1
    except Exception:
        S['error'] = traceback.format_exc()
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('[face] fp arm driver registered', RUN)
