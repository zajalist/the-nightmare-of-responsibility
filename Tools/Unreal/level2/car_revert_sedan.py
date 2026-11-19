"""The player's car shows the original SM_L2Sedan again (the user's pick, 2026-11-19: the Lux3D player_sedan looked
lumpy). car_visual_setup.apply_to_components: the mesh at scale 1, paint and trim instances, Roof hidden; the Collision
box, handling and camera are untouched. Traffic keeps the Lux3D models. Compiles and saves BP_L2Car.
  $env:FOA_AREAS='/Game/FoA/Level2/Drive/BP_L2Car,/Game/FoA/Level2/Drive/SM_L2Sedan'
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/car_revert_sedan.py"""
import sys

import unreal

sys.path.insert(0, 'P:/FoA/Tools/Unreal/level2')
import car_visual_setup as cv  # noqa: E402

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE first'
mesh = cv.find_sedan()
assert mesh, 'SM_L2Sedan missing'
bp = unreal.load_asset(cv.CAR)
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
cs = {str(lib.get_variable_name(lib.get_data(h))): lib.get_object_for_blueprint(lib.get_data(h), bp)
      for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
cv.apply_to_components(cs, mesh)
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert unreal.EditorAssetLibrary.save_loaded_asset(mesh, False)
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
body = cs['Body']
print('CAR body', body.static_mesh.get_name(), body.get_editor_property('relative_scale3d'),
      [m.get_name() for m in body.get_editor_property('override_materials')])
