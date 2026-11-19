"""Seven-second observation of real native WASD input after phone close; no movement injection."""
import json
from pathlib import Path
import time
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_character(world, 0)
controller = unreal.GameplayStatics.get_player_controller(world, 0)
assert player and controller and not controller.is_move_input_ignored()
# The test uses clear floor space so furniture does not conceal a working input route.
original = player.get_actor_location()
assert player.teleport(unreal.Vector(0, -40, original.z), player.get_actor_rotation())
keys = {}
for name in 'WASD':
    key = unreal.Key()
    key.set_editor_property('key_name', name)
    keys[name] = key
state = dict(start=time.monotonic(), handle=None, seen=[], travelled=0.0, peak_speed=0.0, samples=[], next_sample=0)
last_position = [player.get_actor_location()]


def finish(error=None):
    unreal.unregister_slate_post_tick_callback(state['handle'])
    state['handle'] = None
    state['error'] = repr(error) if error else None
    state['result'] = 'FAIL' if error else 'PASS'
    Path('P:/FoA/Saved/Integration/movement_runtime.json').write_text(json.dumps(state, indent=2))


def tick(_dt):
    try:
        elapsed = time.monotonic() - state['start']
        position = player.get_actor_location()
        state['travelled'] += (position - last_position[0]).length()
        last_position[0] = position
        state['peak_speed'] = max(state['peak_speed'], player.get_velocity().length())
        down = [name for name, key in keys.items() if controller.is_input_key_down(key)]
        for name in down:
            if name not in state['seen']:
                state['seen'].append(name)
        if elapsed >= state['next_sample']:
            state['samples'].append(dict(t=elapsed, down=down, position=[position.x,position.y,position.z],
                move_ignored=controller.is_move_input_ignored(), look_ignored=controller.is_look_input_ignored()))
            state['next_sample'] = elapsed + .1
        if elapsed > 7:
            assert set(state['seen']) == set('WASD'), state['seen']
            assert state['peak_speed'] > 30 and state['travelled'] > 50, (state['peak_speed'], state['travelled'])
            assert not controller.is_move_input_ignored() and not controller.is_look_input_ignored()
            finish()
    except Exception as error:
        finish(error)


state['handle'] = unreal.register_slate_post_tick_callback(tick)
