"""Four-second visual comparison of global diffusion. Restores every runtime value."""
import json
from pathlib import Path
import time
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
dream = unreal.GameplayStatics.get_actor_of_class(world, unreal.load_class(None,
    '/Game/FoA/PostProcess/BP_DreamDirector.BP_DreamDirector_C'))
assert world and pc and dream
mpc = unreal.load_asset('/Game/FoA/PostProcess/MPC_Dream')
echo = unreal.MaterialLibrary.get_scalar_parameter_value(world, mpc, 'EchoStrength')
lens = unreal.MaterialLibrary.get_vector_parameter_value(world, mpc, 'LensLook')
tick_enabled = dream.is_actor_tick_enabled()
out = Path('P:/FoA/Saved/PPShots/game_clarity')
out.mkdir(parents=True, exist_ok=True)
state = dict(start=time.monotonic(), phase=0, handle=None, error=None, shots=[])


def shot(name):
    unreal.SystemLibrary.execute_console_command(world, f'Shot filename={out.as_posix()}/{name}.png -nosuffix', pc)
    state['shots'].append(name)


def look(amount, values):
    unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'EchoStrength', amount)
    unreal.MaterialLibrary.set_vector_parameter_value(world, mpc, 'LensLook', unreal.LinearColor(*values))


def finish(error=None):
    unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'EchoStrength', echo)
    unreal.MaterialLibrary.set_vector_parameter_value(world, mpc, 'LensLook', lens)
    restored_echo = unreal.MaterialLibrary.get_scalar_parameter_value(world, mpc, 'EchoStrength')
    restored_lens = unreal.MaterialLibrary.get_vector_parameter_value(world, mpc, 'LensLook')
    restored = abs(restored_echo - echo) < .0001 and all(abs(a-b) < .0001 for a,b in
        zip((restored_lens.r, restored_lens.g, restored_lens.b, restored_lens.a), (lens.r, lens.g, lens.b, lens.a)))
    dream.set_actor_tick_enabled(tick_enabled)
    unreal.unregister_slate_post_tick_callback(state['handle'])
    state['handle'] = None
    state['error'] = repr(error) if error else None
    state['original'] = dict(echo=echo, lens=[lens.r, lens.g, lens.b, lens.a], ticking=tick_enabled)
    state['restored'] = restored and dream.is_actor_tick_enabled() == tick_enabled
    assert state['restored'], 'Comparison must restore the exact look and ticking state'
    out.joinpath('proof.json').write_text(json.dumps(state, indent=2))


def tick(_dt):
    try:
        elapsed = time.monotonic() - state['start']
        if elapsed > 4:
            return finish('cap')
        if state['phase'] == 0:
            shot('current'); state['phase'] = 1
        elif state['phase'] == 1 and elapsed > .5:
            dream.set_actor_tick_enabled(False)
            look(0, (0, 0, 0, 0)); state['phase'] = 2
        elif state['phase'] == 2 and elapsed > 1.0:
            shot('without_diffusion'); state['phase'] = 3
        elif state['phase'] == 3 and elapsed > 1.5:
            look(.08, (.08, .10, .16, .08)); state['phase'] = 4
        elif state['phase'] == 4 and elapsed > 2:
            shot('restrained'); state['phase'] = 5
        elif state['phase'] == 5 and elapsed > 2.8:
            finish()
    except Exception as error:
        finish(error)


state['handle'] = unreal.register_slate_post_tick_callback(tick)
