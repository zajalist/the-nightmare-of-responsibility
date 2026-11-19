"""Read-only 5.9 bridge/API sanity check, under a Level2 asset lease."""
import json
from pathlib import Path
import unreal


def run():
    version = unreal.SystemLibrary.get_engine_version()
    checks = {
        'custom_primitive_defaults': hasattr(unreal.PrimitiveComponent, 'set_default_custom_primitive_data_float'),
        'graph_capture': hasattr(unreal, 'FoAGraphToolsLibrary') and hasattr(unreal.FoAGraphToolsLibrary, 'capture_graph_png'),
        'editor_world': hasattr(unreal.UnrealEditorSubsystem, 'get_editor_world'),
        'game_world': hasattr(unreal.UnrealEditorSubsystem, 'get_game_world'),
        'mpc_scalar': hasattr(unreal.MaterialLibrary, 'set_scalar_parameter_value'),
        'no_notify_enum': hasattr(unreal.PropertyAccessChangeNotifyMode, 'NEVER'),
        'performance_settings': bool(unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')),
    }
    assets = {}
    for path in ['/Game/FoA/Level2/Blueprints/BP_SplatFXDirector', '/Game/FoA/Level2/Materials/MF_SplatDynamics',
                 '/Game/FoA/Level2/Materials/MPC_L2', '/Game/FoA/Level2/M_SplatWorld_Lean', '/Game/FoA/Level2/M_SplatCity_Lean']:
        a = unreal.load_asset(path)
        assets[path] = str(a.get_editor_property('status')) if a and isinstance(a, unreal.Blueprint) else bool(a)
    settings = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    result = {'version': version, 'apis': checks, 'assets': assets,
              'direct_performance_class_exposed': hasattr(unreal, 'EditorPerformanceSettings'),
              'background_throttle': settings.get_editor_property('bThrottleCPUWhenNotForeground')}
    Path('P:/FoA/Saved/Codex/splat_dynamics/sanity_59.json').write_text(json.dumps(result, indent=2))
    print('SPLAT 5.9 sanity', result)
    assert version.startswith('5.9.') and all(checks.values()) and all(assets.values()), result


run()
