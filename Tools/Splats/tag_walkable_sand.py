"""Actor tag "Sand" on every walkable floor sand actor (spills, the pour's pile, crumb layers), for BP_FoAPlayer's
foot-plant test (GetActorLabel is editor-only, tags ship). Idempotent. Prints each actor's floor-plane bounds and
whether its mesh collides with a downward trace.
  $env:FOA_ACTORS='SandMound_Bay,...'; python Tools/Unreal/ue_remote.py Tools/Splats/tag_walkable_sand.py"""
import unreal

WALKABLE = ("SandMound_Bay", "SandMound_Hearth", "SandMound_Path", "SandSpill_Pour", "SandSpill_Pile",
            "SandSplats_Bay", "SandSplats_Hearth", "SandSplats_Path")


def run():
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() not in WALKABLE:
            continue
        if "Sand" not in [str(t) for t in a.tags]:
            a.tags = list(a.tags) + [unreal.Name("Sand")]
        o, e = a.get_actor_bounds(False)
        c = a.get_components_by_class(unreal.StaticMeshComponent)[0]
        print("TAGGED", a.get_actor_label(), "xy", round(o.x - e.x), round(o.y - e.y), round(o.x + e.x), round(o.y + e.y),
              "collision", c.get_collision_profile_name(), c.get_collision_enabled())


run()
