"""Read-only graph layout plans, stats and captures. Run one step under a Level2 lease."""
import json
import os
import sys
from pathlib import Path
import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal')
import graph_layout

OUT = Path('P:/FoA/Saved/Codex/splat_dynamics')
PATHS = ['/Game/FoA/Level2/Materials/MF_SplatDynamics', '/Game/FoA/Level2/M_SplatWorld_Lean',
         '/Game/FoA/Level2/M_SplatCity_Lean', '/Game/FoA/Level2/Blueprints/BP_SplatFXDirector']


def run():
    step = os.environ.get('SPLAT_INSPECT', 'layout')
    if step == 'layout':
        for path in PATHS[:3]:
            plan = graph_layout.layout_material(path)
            print('SPLAT layout', path, plan['plan_file'])
    elif step == 'capture':
        path = PATHS[int(os.environ.get('SPLAT_GRAPH', '0'))]
        asset = unreal.load_asset(path)
        unreal.FoAGraphToolsLibrary.capture_graph_png(asset, 'EventGraph' if 'BP_' in path else '',
                                                     str(OUT / (asset.get_name() + '.png')), True)
        print('SPLAT capture', path)
    elif step == 'close':
        for path in PATHS:
            asset = unreal.load_asset(path)
            unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    elif step == 'stats':
        stats = {}
        for path in PATHS[1:3]:
            asset = unreal.load_asset(path)
            stats[path] = {'statistics': str(unreal.MaterialEditingLibrary.get_statistics(asset)),
                           'expressions': unreal.MaterialEditingLibrary.get_num_material_expressions(asset),
                           'scalar_parameters': [str(x) for x in unreal.MaterialEditingLibrary.get_scalar_parameter_names(asset)]}
        (OUT / 'shader_statistics.json').write_text(json.dumps(stats, indent=2))
        print('SPLAT statistics', stats)


run()
