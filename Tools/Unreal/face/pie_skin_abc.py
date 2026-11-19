"""Skin and lighting A/B/C in PIE (face lane, PIE-only changes): boot through the real front end, skip the wake-up,
then for each view shoot the clean frame (face blur weight 0) in three variants, plus one mask frame for the head:
  A  as shipped;  B  BP_FoAPlayer.CharacterLight off;  C  B plus skin tint 0.5 (PIE-only MIDs on Body and Face)
Views: fp_down (first person looking down at his chest, arms and hands), close_front, mid_34, far_front.
Run inside face_burst.sh:  FOA_DRIVER=Tools/Unreal/face/pie_skin_abc.py bash Tools/Unreal/face/face_burst.sh skin_abc abc
Output: Saved/FaceShots/<run>/{view}_{A,B,C}.png, mask_{view}.png, shots.json."""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal

RUN = os.environ.get('FOA_RUN', 'skin_abc')
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
old_ctx = (str(gi.get_editor_property('SaveSlot')), set(gi.get_editor_property('Knowledge')), list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext', ('FoA_QA_FaceSkin', set(), []))
S = dict(t0=time.time(), h=None, actions=set(), story=False, skip=False, ready=False, done=False, shots=[], step=0,
         wait=-1, error=None, mids=None, cam=None, yaw=0.0)


def player():
    p = unreal.GameplayStatics.get_player_character(w, 0)
    return p, next(c for c in p.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == 'Body')


def set_blur(v):
    vol = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PostProcessVolume) if a.get_actor_label() == 'PP_DreamMono')
    st = vol.get_editor_property('settings')
    out = []
    for b in st.get_editor_property('weighted_blendables').get_editor_property('array'):
        o = b.get_editor_property('object')
        wb = unreal.WeightedBlendable()
        wb.set_editor_property('object', o)
        wb.set_editor_property('weight', v if o and o.get_name() == 'M_PP_FaceBlur' else b.get_editor_property('weight'))
        out.append(wb)
    wbs = unreal.WeightedBlendables()
    wbs.set_editor_property('array', out)
    st.set_editor_property('weighted_blendables', wbs)
    vol.set_editor_property('settings', st)


def variant(k):
    p, body = player()
    for c in p.get_components_by_class(unreal.PointLightComponent):
        if c.get_name() == 'CharacterLight':
            c.set_visibility(k == 'A')
    if S['mids'] is None:
        S['mids'] = []
        for comp in p.get_components_by_class(unreal.SkeletalMeshComponent):
            if comp.get_name() not in ('Body', 'Face'):
                continue
            for i in range(comp.get_num_materials()):
                m = comp.get_material(i)
                if m and 'MI_Teen_Skin' in m.get_name():
                    S['mids'].append(comp.create_dynamic_material_instance(i, m))
    v = 0.5 if k == 'C' else 0.66
    for mid in S['mids']:
        mid.set_vector_parameter_value('Tint', unreal.LinearColor(v, v, v, 1.0))
    S['variant'] = k


def tmp_cam():
    if not S['cam']:
        S['cam'] = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.CameraActor) if a.get_actor_label() == 'Shot_TopDown')
        S['home'] = (S['cam'].get_actor_location(), S['cam'].get_actor_rotation())
        S['cam'].camera_component.set_editor_property('constrain_aspect_ratio', False)
    return S['cam']


def view(yaw_off, dist, pitch, fov, look_dz=0.0):
    p, body = player()
    look = body.get_socket_location('head') + unreal.Vector(0, 0, 8 + look_dz)
    yaw, pr = math.radians(S['yaw'] + yaw_off), math.radians(-pitch)
    off = unreal.Vector(math.cos(yaw) * math.cos(pr), math.sin(yaw) * math.cos(pr), math.sin(pr)) * dist
    loc = look + off
    loc = unreal.Vector(max(-360, min(360, loc.x)), max(-285, min(285, loc.y)), max(20, min(285, loc.z)))
    c = tmp_cam()
    c.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, look), False, True)
    c.camera_component.set_field_of_view(fov)
    pc.set_view_target_with_blend(c, 0.0)


def fp_down():
    p, body = player()
    pc.set_view_target_with_blend(p, 0.0)
    pc.set_control_rotation(unreal.Rotator(roll=0, pitch=-55, yaw=S['yaw']))


def slip(v):
    unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'FaceSlip', v)


def freeze(v):
    p, body = player()
    p.set_editor_property('custom_time_dilation', v, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)  # notified sets re-run BP_FoAPlayer construction (editor-rules)


def shot(label):
    unreal.SystemLibrary.execute_console_command(w, f'Shot filename={OUT.as_posix()}/{label}.png -nosuffix', pc)
    S['shots'].append(dict(label=label, t=round(time.time() - S['t0'], 2), variant=S.get('variant')))


def views():
    steps = []
    for name, act in (('fp_down', fp_down), ('close_front', lambda: view(0, 120, -3, 35)),
                      ('mid_34', lambda: view(30, 180, -8, 45)), ('far_front', lambda: view(10, 430, -12, 50, -60))):
        steps.append((lambda a=act: (a(), freeze(0.0), variant('A'), set_blur(1.0), slip(-1.0)), 8, 'mask_' + name))
        for k in 'ABC':
            steps.append((lambda k=k: (slip(1.0), set_blur(0.0), variant(k)), 4, f'{name}_{k}'))
    steps.append((lambda: (variant('A'), set_blur(1.0), slip(1.0), freeze(1.0)), 2, None))
    return steps


PLAN = views()


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        variant('A')
        set_blur(1.0)
        slip(1.0)
        freeze(1.0)
        if S['cam']:
            S['cam'].set_actor_location_and_rotation(S['home'][0], S['home'][1], False, True)
        gi.call_method('SetProofProgressContext', old_ctx)
        unreal.GameplayStatics.delete_game_in_slot('FoA_QA_FaceSkin', 0)
    except Exception:
        S['error'] = (S['error'] or '') + traceback.format_exc()
    (OUT / 'shots.json').write_text(json.dumps(dict(reason=reason, error=S['error'], shots=S['shots']), indent=1))
    unreal.log(f'[face] {RUN} finished: {reason}')


def tick(dt):
    try:
        t = time.time() - S['t0']
        if t > 44:
            return finish('timeout')
        if not S['ready']:
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
                S['skip'], S['skip_t'] = True, t
                return
            if d.get_editor_property('bWakeDone') and S['skip'] and t - S['skip_t'] > 2.5:
                ph = unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, '/Game/FoA/UI/Game/BP_Phone.BP_Phone_C'))
                if ph and ph.get_editor_property('bOpen'):
                    ph.call_method('ClosePhone', ())
                d.call_method('ReportEvent', (unreal.Name('PhoneWakeUp'),))
                unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
                unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
                p, body = player()
                a = p.get_actor_location()
                S['yaw'] = math.degrees(math.atan2(-a.y, -a.x))
                pc.set_control_rotation(unreal.Rotator(roll=0, pitch=0, yaw=S['yaw']))
                S['ready'], S['wait'] = True, -1
                S['settle_until'] = t + 1.5
            return
        if t < S.get('settle_until', 0):
            return
        if S['step'] >= len(PLAN):
            return finish('done')
        act, settle, label = PLAN[S['step']]
        if S['wait'] < 0:
            act()
            S['wait'] = settle
            return
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
print('[face] skin abc driver registered', RUN)
