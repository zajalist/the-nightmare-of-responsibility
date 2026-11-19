"""Attach Hayba-created grain components to the animated body; no typed SCS reparent tool exists yet."""
import unreal

bp = unreal.load_asset("/Game/FoA/Characters/Player/BP_FoAPlayer")
unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary
handles = sub.k2_gather_subobject_data_for_blueprint(bp)
parts = {str(lib.get_variable_name(lib.get_data(h))): h for h in handles}
body = lib.get_object_for_blueprint(lib.get_data(parts["Body"]), bp)
pose = unreal.AnimPoseExtensions.get_reference_pose(body.get_skeletal_mesh_asset().get_editor_property("skeleton"))
for name, bone, scale, height in (("FaceDrift", "head", 1.0, 6.0), ("BodyDrift", "spine_03", 1.8, 0.0)):
    assert name in parts, "Add static-mesh component with Hayba first"
    assert sub.attach_subobject(parts["Body"], parts[name]), "Could not attach grain component"
    component = lib.get_object_for_blueprint(lib.get_data(parts[name]), bp)
    transform = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
    q = transform.rotation
    inverse = unreal.Quat(-q.x, -q.y, -q.z, q.w)
    forward = inverse.rotate_vector(unreal.Vector(0, 1, 0))
    component.set_editor_property("relative_rotation", unreal.MathLibrary.make_rot_from_x(forward))
    component.set_editor_property("relative_location", inverse.rotate_vector(unreal.Vector(0, 0, height)))
    component.set_editor_property("relative_scale3d", unreal.Vector(scale, scale, scale))
    component.set_collision_profile_name("NoCollision")
    component.set_visibility(False)
    print("attached", name, "to", bone)
unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
