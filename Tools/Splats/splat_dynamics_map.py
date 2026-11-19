"""Short structural CPD/camera proof operations inside the runner's EXCLUSIVE hold.
No material graph writes. No Level 1 mutations. Manifest is copied offline with python -I.
"""
import json
import os
from pathlib import Path
import unreal

OUT = Path('P:/FoA/Saved/Codex/splat_dynamics')
MODE = os.environ['SPLAT_STEP']
KIND = os.environ.get('SPLAT_MAP', 'dream')
MAP = '/Game/FoA/Level2/Maps/L_L2_' + ('DreamTest' if KIND == 'dream' else 'CityTest')
SUB = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def run():
    world = SUB.get_game_world() if MODE in ('proof', 'state') else SUB.get_editor_world()
    assert world and ('L_L2_DreamTest' if KIND == 'dream' else 'L_L2_CityTest') in world.get_path_name()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    director = next(a for a in actors if a.get_class().get_name() == 'BP_SplatFXDirector_C')
    if MODE == 'cpd':
        manifest = json.loads((OUT / 'city_cpd.json').read_text()) if KIND == 'city' else None
        count = 0
        for a in actors:
            label = a.get_actor_label()
            if (KIND == 'dream' and label != 'DreamA_Splats') or (KIND == 'city' and label not in manifest['chunks']):
                continue
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            c.set_editor_property('bounds_scale', 1.)
            origin, extent, _ = unreal.SystemLibrary.get_component_bounds(c)
            floor = manifest['floor'] if manifest else origin.z - extent.z + 8
            data = manifest['chunks'][label] if manifest else {'seed': .17, 'building': 0, 'exclude': 0}
            for i, value in enumerate([0, data['exclude'], data['seed'], floor, data['building']]):
                c.set_default_custom_primitive_data_float(i, value)
            # Bounds must cover the pile and detached grains as well as the source roof.
            c.set_editor_property('bounds_scale', max(1.15, (origin.z - floor + 80) / max(extent.z, 1)))
            count += 1
        assert count == (514 if KIND == 'city' else 1), count
        print('SPLAT CPD', KIND, count)
    elif MODE == 'proof':
        gi = unreal.GameplayStatics.get_game_instance(world)
        gi.call_method('SetProofProgressContext', ('FoA_QA_Play', set(), []))
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        cam = next(a for a in actors if a.get_class().get_name() == 'CameraActor' and a.get_actor_label() == 'L2_Cam')
        if KIND == 'dream':
            cam.set_actor_location_and_rotation(unreal.Vector(0, 0, 160), unreal.Rotator(pitch=0, yaw=0, roll=0), False, False)
        pc.set_view_target_with_blend(cam, 0)
        director.set_editor_property('EventStartTime', unreal.GameplayStatics.get_time_seconds(world),
                                    notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        settings = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
        (OUT / (KIND + '_cvars.json')).write_text(json.dumps({'csv.GpuStatsEnabled':
            unreal.SystemLibrary.get_console_variable_int_value('csv.GpuStatsEnabled'),
            'throttle': settings.get_editor_property('bThrottleCPUWhenNotForeground')}))
        settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
        unreal.SystemLibrary.execute_console_command(world, 'csv.GpuStatsEnabled 1')
        unreal.SystemLibrary.execute_console_command(world, 'CsvProfile START')
        print('SPLAT proof camera', cam.get_actor_location(), 'start', director.get_editor_property('EventStartTime'))
    elif MODE == 'state':
        state = os.environ.get('SPLAT_STATE', 'on_rest')
        now = unreal.GameplayStatics.get_time_seconds(world)
        on = state.startswith('on')
        if state == 'stop':
            unreal.SystemLibrary.execute_console_command(world, 'CsvProfile STOP')
            for key, value in json.loads((OUT / (KIND + '_cvars.json')).read_text()).items():
                if key == 'throttle':
                    unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground', value)
                else:
                    unreal.SystemLibrary.execute_console_command(world, f'{key} {value}')
        elif state == 'shot':
            label = os.environ['SPLAT_SHOT']
            unreal.SystemLibrary.execute_console_command(world, f'Defer Shot filename={OUT.as_posix()}/{KIND}_{label}_after.png -nosuffix')
        else:
            director.set_actor_tick_enabled(False)
            mpc = unreal.load_asset('/Game/FoA/Level2/Materials/MPC_L2')
            for key, value in [('AmbientIntensity', .8 if on else 0),
                               ('SandRadius', (1800 if KIND == 'city' else 240) if on else 0),
                               ('SandProgress', .65 if state.endswith('sand') else 0)]:
                unreal.MaterialLibrary.set_scalar_parameter_value(world, mpc, key, value)
            # Deferred commands emit the CSV event used to delimit measured frames.
            unreal.SystemLibrary.execute_console_command(world, f'Defer Shot filename={OUT.as_posix()}/{KIND}_{state}_before.png -nosuffix')
        print('SPLAT state', state, 'time', now)


run()
