"""Bounded real-battle flight/ReduceMotion check. Root owns PIE, timing and cleanup."""
import json
from pathlib import Path
import time
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
cls = unreal.load_class(None, '/Game/FoA/Gameplay/Encounter/BP_Garment.BP_Garment_C')
garments = list(unreal.GameplayStatics.get_all_actors_of_class(world, cls))
assert garments, 'Inject after the real encounter has risen'
mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
original_rm = unreal.MaterialLibrary.get_scalar_parameter_value(world, mpc, 'ReduceMotion')
out = Path('P:/FoA/Saved/EncounterCaptures/clothing_motion')
out.mkdir(parents=True, exist_ok=True)
state = dict(t0=time.time(), ready_at=None, handle=None, stage=0, log=[], error=None)


def sample(label):
    values = []
    for actor in garments:
        pos = actor.get_actor_location()
        values.append(dict(name=actor.get_name(), active=actor.get_editor_property('bMotionActive'),
                           position=[pos.x, pos.y, pos.z]))
    state['log'].append(dict(label=label, t=time.time() - state['t0'], actors=values))
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    unreal.SystemLibrary.execute_console_command(world, f'Shot filename={out.as_posix()}/{label}.png -nosuffix', pc)


def finish(error=None):
    if state['handle'] is not None:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        state['handle'] = None
    unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'ReduceMotion', original_rm)
    state['error'] = str(error) if error else None
    state['result'] = 'FAIL' if error else 'PASS'
    out.joinpath('proof.json').write_text(json.dumps({k: v for k, v in state.items() if k != 'handle'}, indent=2))
    print('CLOTHING MOTION', 'PASS' if not error else str(error))


def tick(_dt):
    try:
        elapsed = time.time() - state['t0']
        if elapsed > 8:
            return finish('8 second cap awaiting garment motion')
        if state['stage'] == 0:
            if not all(a.get_editor_property('bMotionActive') for a in garments):
                return
            state['ready_at'] = time.time()
            sample('flight_start'); state['stage'] = 1
        elif time.time() - state['ready_at'] > 1.0 and state['stage'] == 1:
            sample('flight_moved')
            first, last = state['log'][0]['actors'], state['log'][1]['actors']
            for before, after in zip(first, last):
                distance = sum((a - b) ** 2 for a, b in zip(before['position'], after['position'])) ** 0.5
                assert distance > 0.5, (before['name'], distance)
            unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'ReduceMotion', 1.0)
            state['stage'] = 2
        elif time.time() - state['ready_at'] > 1.8 and state['stage'] == 2:
            sample('reduced_motion')
            for actor in garments:
                home = actor.get_editor_property('MotionHome').translation
                assert (actor.get_actor_location() - home).length() < 7.0, actor.get_name()
            state['stage'] = 3
        elif time.time() - state['ready_at'] > 2.3 and state['stage'] == 3:
            finish()
    except Exception as error:
        finish(error)


state['handle'] = unreal.register_slate_post_tick_callback(tick)
