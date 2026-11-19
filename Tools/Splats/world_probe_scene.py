"""Read-only: every actor's label, folder, class, location, yaw and world bounds -> Saved/WorldShots/scene.txt."""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
with open('P:/FoA/Saved/WorldShots/scene.txt', 'w') as out:
    for a in sorted(EAS.get_all_level_actors(), key=lambda x: (str(x.get_folder_path()), x.get_actor_label())):
        loc, rot = a.get_actor_location(), a.get_actor_rotation()
        o, e = a.get_actor_bounds(True)
        out.write(f"{str(a.get_folder_path()):<26} {a.get_actor_label():<40} {a.get_class().get_name():<28} "
                  f"loc=({loc.x:.0f},{loc.y:.0f},{loc.z:.0f}) yaw={rot.yaw:.0f} hid={a.is_hidden_ed()} "
                  f"bounds=({o.x - e.x:.0f}..{o.x + e.x:.0f}, {o.y - e.y:.0f}..{o.y + e.y:.0f}, {o.z - e.z:.0f}..{o.z + e.z:.0f})\n")
print('ok')
