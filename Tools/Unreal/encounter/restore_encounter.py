"""Re-places Encounter_T8 (BP_Encounter) where it stood before the 11:19 accidental cut, in the Gameplay outliner folder.
The only record of the old placement is its bounds in an earlier probe (FoA.log 07:57:42): centre (105, -140, 175),
extent (1185, 1095, 1035). Tries the four yaws, keeps the one whose extent matches, then moves the actor so its bounds
centre lands on the recorded centre.
  FOA_ACTORS=Encounter_T8 FOA_ACTORS_NEW=Encounter_T8 python Tools/Unreal/ue_remote.py Tools/Unreal/encounter/restore_encounter.py"""
import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CENTRE, EXTENT = unreal.Vector(105.0, -140.0, 175.0), (1185.0, 1095.0, 1035.0)
have = [a for a in EAS.get_all_level_actors() if a.get_actor_label() == "Encounter_T8"]
if not have:
    a = EAS.spawn_actor_from_class(unreal.load_class(None, "/Game/FoA/Gameplay/Encounter/BP_Encounter.BP_Encounter_C"),
                                   CENTRE, unreal.Rotator(0.0, 0.0, 0.0))
    a.set_actor_label("Encounter_T8")
    have = [a]
a = have[0]
best = None
for yaw in (0.0, 90.0, 180.0, 270.0):  # keyword Rotator: its positional order is (roll, pitch, yaw)
    a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw), False)
    o, e = a.get_actor_bounds(False)
    origin = a.get_actor_location() + (CENTRE - o)
    inside = -375 <= origin.x <= 375 and -300 <= origin.y <= 300  # the staging's root stands in the room
    err = abs(e.x - EXTENT[0]) + abs(e.y - EXTENT[1]) + abs(e.z - EXTENT[2]) + (0 if inside else 1000)
    print("yaw", yaw, "extent", round(e.x), round(e.y), round(e.z), "origin", round(origin.x), round(origin.y), "err", round(err))
    if best is None or err < best[0]:
        best = (err, yaw)
a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=best[1]), False)
o, e = a.get_actor_bounds(False)
a.set_actor_location(a.get_actor_location() + (CENTRE - o), False, False)
a.set_folder_path("Gameplay")
o, e = a.get_actor_bounds(False)
l = a.get_actor_location()
print("FOA_ENCOUNTER yaw", best[1], "err", round(best[0]), "loc", round(l.x), round(l.y), round(l.z), "bounds centre",
      round(o.x), round(o.y), round(o.z), "extent", round(e.x), round(e.y), round(e.z))
