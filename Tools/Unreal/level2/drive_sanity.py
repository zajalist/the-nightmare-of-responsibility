"""Short read-only API check inside the drive asset lease."""
import json
from pathlib import Path
import unreal

root='/Game/FoA/Level2/Drive/'
bp=unreal.load_asset(root+'BP_L2Car');assert bp
sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles=sds.k2_gather_subobject_data_for_blueprint(bp)
assert handles and hasattr(unreal.SystemLibrary,'is_valid')
result=dict(engine=unreal.SystemLibrary.get_engine_version(),components=len(handles),
            graph_api=hasattr(unreal,'BlueprintGraphEditor'),
            graph_capture=hasattr(unreal,'FoAGraphToolsLibrary'),
            map_api=hasattr(unreal.LevelEditorSubsystem,'load_level'),
            enhanced_input=hasattr(unreal,'EnhancedInputLocalPlayerSubsystem'))
assert all(result[k] for k in ('graph_api','graph_capture','map_api','enhanced_input'))
Path('P:/FoA/Saved/Codex/l2_drive/sanity_59.json').write_text(json.dumps(result,indent=1))
print(json.dumps(result))
