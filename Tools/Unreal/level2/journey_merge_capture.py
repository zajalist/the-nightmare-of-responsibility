"""Readback and graph captures for the visual shell, under its scoped asset lease."""
import json
from pathlib import Path
import unreal

assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
path = '/Game/FoA/Level2/Journey/BP_L2Merge'
bp = unreal.load_asset(path)
out = Path('P:/FoA/Saved/Integration/journey_merge')
out.mkdir(parents=True, exist_ok=True)
for name in ('Initialize', 'SetAmount', 'SetVisible', 'Restore'):
    unreal.FoAGraphToolsLibrary.capture_graph_png(bp, name, str(out/(name+'.png')), True)
cdo = unreal.get_default_object(bp.generated_class())
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handle = next(h for h in sds.k2_gather_subobject_data_for_blueprint(bp)
              if str(lib.get_variable_name(lib.get_data(h))) == 'Shell')
shell = lib.get_object_for_blueprint(lib.get_data(handle), bp)
data = dict(blueprint_status=str(bp.get_editor_property('status')), hidden=cdo.get_editor_property('hidden'),
            collision=str(shell.get_collision_enabled()), overlaps=shell.get_editor_property('generate_overlap_events'),
            stencil=shell.get_editor_property('custom_depth_stencil_value'),
            mesh=shell.get_editor_property('skeletal_mesh_asset').get_path_name(),
            materials=[shell.get_material(i).get_path_name() for i in range(shell.get_num_materials())])
(out/'readback.json').write_text(json.dumps(data, indent=2))
print(json.dumps(data))
