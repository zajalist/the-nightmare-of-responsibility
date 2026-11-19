"""Stable eye-height first-person gameplay camera on a character Blueprint.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/set_camera.py FOA_BP=/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter
Edits the CameraBoom / FollowCamera component templates owned or inherited by that Blueprint, then compiles and saves."""
import os

import unreal

BOOM = {"target_arm_length": 0.0, "socket_offset": unreal.Vector(0.0, 0.0, 0.0), "target_offset": unreal.Vector(0.0, 0.0, 0.0),
        "relative_location": unreal.Vector(0.0, 0.0, 68.0), "use_pawn_control_rotation": True,
        "do_collision_test": False, "enable_camera_lag": False, "enable_camera_rotation_lag": False}
FOV = 80.0


def apply(bp_path):
    bp = unreal.load_asset(bp_path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    found = {}
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        d = lib.get_data(h)
        name = str(lib.get_variable_name(d))
        if name in ("CameraBoom", "FollowCamera"):
            found[name] = lib.get_object_for_blueprint(d, bp)
    assert set(found) == {"CameraBoom", "FollowCamera"}, f"camera components not found on {bp_path}: {sorted(found)}"
    for k, v in BOOM.items():
        found["CameraBoom"].set_editor_property(k, v)
    found["FollowCamera"].set_editor_property("field_of_view", FOV)
    found["FollowCamera"].set_editor_property("relative_location", unreal.Vector(0, 0, 0))
    found["FollowCamera"].set_editor_property("use_pawn_control_rotation", True)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("jump_max_count", 0)
    cdo.get_editor_property("character_movement").set_editor_property("orient_rotation_to_movement", False)
    for h in sds.k2_gather_subobject_data_for_blueprint(bp):
        comp = lib.get_object_for_blueprint(lib.get_data(h), bp)
        if isinstance(comp, unreal.PrimitiveComponent):
            comp.set_editor_property("owner_no_see", False)
    # compile with Hayba blueprint_compile afterwards (no Python compiles: editor-rules 20:42)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    print(bp_path, "boom", found["CameraBoom"].get_editor_property("target_arm_length"),
          found["CameraBoom"].get_editor_property("socket_offset"), "fov", found["FollowCamera"].get_editor_property("field_of_view"))


if __name__ != "set_camera":  # imported by build_player_bp.py only for BOOM / FOV
    apply(os.environ["FOA_BP"])
