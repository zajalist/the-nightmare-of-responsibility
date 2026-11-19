"""Repair only locomotion yaw speed; do not rebuild the Player graph or AnimBlueprints."""
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
path='/Game/FoA/Characters/Player/BP_FoAPlayer'
bp=unreal.load_asset(path)
cdo=unreal.get_default_object(bp.generated_class())
movement=cdo.get_editor_property('character_movement')
before=movement.get_editor_property('rotation_rate')
assert movement.get_editor_property('orient_rotation_to_movement')
movement.set_editor_property('rotation_rate',unreal.Rotator(roll=0.0,pitch=0.0,yaw=300.0))
actual=movement.get_editor_property('rotation_rate')
assert abs(actual.yaw-300)<.001 and abs(actual.pitch)<.001 and abs(actual.roll)<.001
assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
print('Walking RotationRate repaired',before,'->',actual)
