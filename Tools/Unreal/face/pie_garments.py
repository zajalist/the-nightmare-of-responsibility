"""Battle garment stills (face lane, PIE-only changes): boot through the real front end, skip the wake-up, start the
encounter as story's proofs do (StartEncounter('Shirt')), then shoot the battle view every 0.25 s: 12 frames as
shipped (time echo on), then 12 with MPC_Dream EchoStrength 0 on the PIE world, so a trailing echo shows as the
difference. Logs every BP_Garment and its rig mesh and materials.
  FOA_DRIVER=Tools/Unreal/face/pie_garments.py bash Tools/Unreal/face/face_burst.sh garments_<tag> battle
Mode each (FOA_TAG=before|after): one battle still per round instead (Socks, Trousers, Shirt, Tie: <tag>_<Id>.png),
each round started, shot 2.5 s in and ended, for the material A/B of every garment.
Output: Saved/FaceShots/<run>/{echo,noecho}_NN.png + shots.json."""
import json
import os
import time
import traceback
from pathlib import Path

import unreal

RUN = os.environ.get('FOA_RUN', 'garments')
MODE = os.environ.get('FOA_MODE', 'battle')
TAG = os.environ.get('FOA_TAG', 'before')
ROUNDS = ['Socks', 'Trousers', 'Shirt', 'Tie']
OUT = Path('P:/FoA/Saved/FaceShots') / RUN
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob('*.png'):
    old.unlink()
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert w, 'no PIE world'
find = lambda path: unreal.GameplayStatics.get_actor_of_class(w, unreal.load_class(None, path))
fe = find('/Game/FoA/UI/Framework/BP_FoAFrontEnd.BP_FoAFrontEnd_C')
d = find('/Game/FoA/Gameplay/BP_BeatDirector.BP_BeatDirector_C')
enc = lambda: find('/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C')  # not there at PIE start: look it up when used
pc = unreal.GameplayStatics.get_player_controller(w, 0)
gi = unreal.GameplayStatics.get_game_instance(w)
MPC = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
old_ctx = (str(gi.get_editor_property('SaveSlot')), set(gi.get_editor_property('Knowledge')), list(gi.get_editor_property('Notebook')))
gi.call_method('SetProofProgressContext', ('FoA_QA_FaceGarments', set(), []))
S = dict(t0=time.time(), h=None, actions=set(), story=False, skip=False, battle=False, done=False, shots=[], n=0,
         next=0.0, error=None, echo0=unreal.MaterialLibrary.get_scalar_parameter_value(w, MPC, 'EchoStrength'), garments=None)


def shot(label):
    unreal.SystemLibrary.execute_console_command(w, f'Shot filename={OUT.as_posix()}/{label}.png -nosuffix', pc)
    S['shots'].append(dict(label=label, t=round(time.time() - S['t0'], 2),
                           echo=unreal.MaterialLibrary.get_scalar_parameter_value(w, MPC, 'EchoStrength'),
                           state=str(enc().get_editor_property('BattleState'))))


def garments():
    cls = unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Garment.BP_Garment_C')
    rows = S['garments'] or []
    for g in unreal.GameplayStatics.get_all_actors_of_class(w, cls):
        rows.append(dict(actor=g.get_name(), hidden=bool(g.get_editor_property('hidden')), loc=[round(v) for v in g.get_actor_location().to_tuple()]))
        for c in g.get_components_by_class(unreal.MeshComponent):
            asset = c.get_skeletal_mesh_asset() if isinstance(c, unreal.SkeletalMeshComponent) else getattr(c, 'static_mesh', None)
            rows.append(dict(actor=g.get_name(), comp=c.get_name(), mesh=asset.get_name() if asset else None,
                             mats=[m.get_name() if m else None for m in c.get_materials()],
                             stencil=c.get_editor_property('custom_depth_stencil_value'),
                             custom_depth=c.get_editor_property('render_custom_depth'), visible=c.is_visible(),
                             hidden_in_game=c.get_editor_property('hidden_in_game'), rendered=c.was_recently_rendered(0.2),
                             scale=[round(v, 3) for v in c.get_component_scale().to_tuple()],
                             bounds=round(c.bounds.sphere_radius, 1) if hasattr(c, 'bounds') else None))
    return rows


def finish(reason):
    if S['done']:
        return
    S['done'] = True
    unreal.unregister_slate_post_tick_callback(S['h'])
    try:
        unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'EchoStrength', S['echo0'])
        if enc() and enc().get_editor_property('bActive'):
            enc().call_method('EndEncounter', ())
        gi.call_method('SetProofProgressContext', old_ctx)
        unreal.GameplayStatics.delete_game_in_slot('FoA_QA_FaceGarments', 0)
    except Exception:
        S['error'] = (S['error'] or '') + traceback.format_exc()
    (OUT / 'shots.json').write_text(json.dumps(dict(reason=reason, error=S['error'], echo0=S['echo0'], fight_state=S.get('fight_state'),
                                                    garments=S['garments'], shots=S['shots']), indent=1))
    unreal.log(f'[face] {RUN} finished: {reason}')


def tick(dt):
    try:
        t = time.time() - S['t0']
        if t > 44:
            return finish('timeout')
        if not S['battle']:
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
            if d.get_editor_property('bWakeDone') and S['skip'] and t - S['skip_t'] > 2.0 and enc():
                unreal.SystemLibrary.pause_timer(d, 'PollStoryMoment')
                unreal.SystemLibrary.clear_timer(d, 'TryStoryMoment')
                enc().call_method('StartEncounter', (ROUNDS[0] if MODE == 'each' else 'Shirt',))
                S['battle'], S['bt'] = True, t
            return
        if t - S['bt'] < 2.5:
            return
        if MODE == 'each':  # shoot this round, end it a few frames later (the shot lands next frame), start the next
            if not S.get('shot_t'):
                S['garments'] = garments()
                shot(f'{TAG}_{ROUNDS[S["n"]]}')
                S['shot_t'] = t
                return
            if t - S['shot_t'] < 0.4:
                return
            S['shot_t'] = None
            enc().call_method('EndEncounter', ())
            S['n'] += 1
            if S['n'] == len(ROUNDS):
                return finish('done')
            enc().call_method('StartEncounter', (ROUNDS[S['n']],))
            S['bt'] = t
            return
        state = str(enc().get_editor_property('BattleState'))
        if S['garments'] is None and t - S['bt'] < 8.0 and ('None' in state or 'Intro' in state):
            return  # the intro still has the camera: shoot once the fight view is up (or after 8 s)
        if S['garments'] is None:
            S['garments'] = garments()
            S['fight_state'] = state
        if t >= S['next']:
            k = 'echo' if S['n'] < 12 else 'noecho'
            if S['n'] == 12:
                unreal.MaterialLibrary.set_scalar_parameter_value(w, MPC, 'EchoStrength', 0.0)
                S['next'] = t + 0.6  # let the echo history drain before the first clean frame
                S['n'] += 1
                return
            shot(f'{k}_{S["n"]:02d}')
            S['n'] += 1
            S['next'] = t + 0.25
            if S['n'] > 24:
                return finish('done')
    except Exception:
        S['error'] = traceback.format_exc()
        finish('error')


S['h'] = unreal.register_slate_post_tick_callback(tick)
print('[face] garments driver registered', RUN)
