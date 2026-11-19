"""BP_Phone Mesh collision (main, 2026-11-09): world proved the boot carry and the bed climb were the player standing on
his own phone (BlockAllDynamic, so the capsule stepped up onto it). Custom profile on the class template: Pawn and Camera
Ignore, Visibility Block (interaction traces), everything else as before (Block), CanCharacterStepUpOn = No.
  python Tools/Unreal/ue_remote.py Tools/Unreal/ui/phone_collision.py FOA_AREAS=/Game/FoA/UI/Game/BP_Phone
  then compile and save with Hayba (blueprint_compile, asset_save) and check the .uasset timestamp"""
import unreal

bp = unreal.load_asset('/Game/FoA/UI/Game/BP_Phone')
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
by = {str(lib.get_variable_name(lib.get_data(h))): h for h in sds.k2_gather_subobject_data_for_blueprint(bp)}
mesh = lib.get_object(lib.get_data(by['Mesh']))
mesh.set_collision_profile_name('Custom')
# 'Custom' on the template left NoCollision / WorldStatic (read back 23:05): keep BlockAllDynamic's enable and object type
mesh.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
mesh.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_DYNAMIC)
for channel, response in ((unreal.CollisionChannel.ECC_PAWN, unreal.CollisionResponseType.ECR_IGNORE),
                          (unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_IGNORE),
                          (unreal.CollisionChannel.ECC_VISIBILITY, unreal.CollisionResponseType.ECR_BLOCK)):
    mesh.set_collision_response_to_channel(channel, response)
mesh.set_editor_property('can_character_step_up_on', unreal.CanBeCharacterBase.ECB_NO)
got = {c: str(mesh.get_collision_response_to_channel(getattr(unreal.CollisionChannel, c)))
       for c in ('ECC_PAWN', 'ECC_CAMERA', 'ECC_VISIBILITY', 'ECC_WORLD_STATIC')}
print('profile', mesh.get_collision_profile_name(), got, 'step up', mesh.get_editor_property('can_character_step_up_on'),
      'enabled', mesh.get_collision_enabled())
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)  # compile follows through Hayba (crash-safe path)
