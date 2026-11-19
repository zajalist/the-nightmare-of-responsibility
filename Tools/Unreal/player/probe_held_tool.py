"""Read-only: the held-tool defaults on BP_FoAPlayer and BP_Door."""
import unreal
cdo = unreal.get_default_object(unreal.load_asset('/Game/FoA/Characters/Player/BP_FoAPlayer').generated_class())
print('OFFSET', cdo.get_editor_property('ToolGripOffset'), 'HOLD', cdo.get_editor_property('bHoldingTool'))
