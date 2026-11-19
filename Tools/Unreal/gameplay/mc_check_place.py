"""mech_core: numbers behind 'nothing floats' for the placed pickups and the re-pivoted wardrobe (read-only)."""
import unreal

acts = {a.get_actor_label(): a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
for n in ("Screwdriver_DeskDrawer", "Desk", "Hanger_CoatRail", "Dress_CoatRail_Door", "Shirt_T7", "Wardrobe",
          "Wardrobe_GothicCabinet_01_door1", "Door_Bedroom", "Key_Lux3D", "Boot_L"):
    a = acts.get(n)
    if not a:
        print(n, "MISSING")
        continue
    ms = a.get_components_by_class(unreal.StaticMeshComponent)
    o, e, _ = unreal.SystemLibrary.get_component_bounds(ms[0])
    print(f"{n:32s} {a.get_class().get_name():16s} loc=({a.get_actor_location().x:.1f},{a.get_actor_location().y:.1f},"
          f"{a.get_actor_location().z:.1f}) min=({o.x - e.x:.1f},{o.y - e.y:.1f},{o.z - e.z:.1f}) "
          f"max=({o.x + e.x:.1f},{o.y + e.y:.1f},{o.z + e.z:.1f})")
