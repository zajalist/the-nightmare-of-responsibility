"""Inject into coordinator PIE: exercise cached sensitivity/inversion without writing user settings."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_character(world, 0)
assert player
original = player.get_editor_property("LookScale")
settings = unreal.GameplayStatics.create_save_game_object(unreal.load_class(
    None, "/Game/FoA/UI/Framework/SG_FoASettings.SG_FoASettings_C"))
try:
    for sensitivity, invert, x, y in ((0.5, False, 0.5, 0.5), (0.5, True, 0.5, -0.5),
                                      (100.0, True, 2.5, -2.5), (0.01, False, 0.25, 0.25)):
        settings.set_editor_property("MouseSensitivity", sensitivity)
        settings.set_editor_property("bInvertY", invert)
        player.call_method("ApplyLookSettings", (settings,))
        scale = player.get_editor_property("LookScale")
        assert abs(scale.x - x) < 0.0001 and abs(scale.y - y) < 0.0001, (sensitivity, invert, scale)
    print("PASS look settings: live sensitivity, invert Y, clamps; no settings file changed")
finally:
    player.set_editor_property("LookScale", original)
