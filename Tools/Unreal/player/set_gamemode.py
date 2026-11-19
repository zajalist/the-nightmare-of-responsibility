"""Points the open level's World Settings GameMode override at GM_FoA (default pawn BP_FoAPlayer), so the player spawns
as BP_FoAPlayer at PlayerStart_WakeUp. The project-wide default (BP_ThirdPersonGameMode) is left alone.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/set_gamemode.py   then Hayba level_save."""
import unreal


def run():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert "L_Tutorial_Bedroom" in world.get_path_name(), "wrong level open: " + world.get_path_name()
    gm = unreal.EditorAssetLibrary.load_blueprint_class("/Game/FoA/Gameplay/GM_FoA")
    pawn = unreal.get_default_object(gm).get_editor_property("default_pawn_class")
    assert pawn and "BP_FoAPlayer" in pawn.get_name(), f"GM_FoA default pawn is {pawn}"
    ws = world.get_world_settings()
    ws.set_editor_property("default_game_mode", gm)
    starts = [a.get_actor_label() for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
              if isinstance(a, unreal.PlayerStart)]
    print("GameMode override:", ws.get_editor_property("default_game_mode").get_name(), "pawn:", pawn.get_name(), "starts:", starts)


run()
