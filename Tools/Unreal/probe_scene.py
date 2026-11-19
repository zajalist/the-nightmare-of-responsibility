"""Prints the open level and every actor's label, folder and transform (read-only)."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
print("LEVEL", world.get_path_name() if world else None)
for a in sorted(EAS.get_all_level_actors(), key=lambda x: (str(x.get_folder_path()), x.get_actor_label())):
    loc, rot, scl = a.get_actor_location(), a.get_actor_rotation(), a.get_actor_scale3d()
    print(f"{str(a.get_folder_path()):<28} {a.get_actor_label():<44} "
          f"loc=({loc.x:.1f},{loc.y:.1f},{loc.z:.1f}) yaw={rot.yaw:.1f} scale=({scl.x:.2f},{scl.y:.2f},{scl.z:.2f})")
