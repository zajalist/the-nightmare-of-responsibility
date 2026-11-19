"""Run inside the coordinator's free-roam PIE proof: a late interaction release must preserve a battle hold."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_character(world, 0)
controller = unreal.GameplayStatics.get_player_controller(world, 0)
assert player and controller and not controller.is_move_input_ignored(), "Run after returning to free roam"
assert not player.get_editor_property("bInteractionLocked")
battle_hold = False
try:
    player.call_method("SetInteractionLocked", (True,))
    player.call_method("SetInteractionLocked", (True,))
    controller.set_ignore_move_input(True)
    battle_hold = True
    player.call_method("EndInteraction")
    player.call_method("EndInteraction")
    assert controller.is_move_input_ignored(), "Interaction timer released the battle lock"
    assert not player.get_editor_property("bInteractionLocked")
    controller.set_ignore_move_input(False)
    battle_hold = False
    assert not controller.is_move_input_ignored(), "Repeated interaction acquire leaked a movement lock"
    print("PASS interaction ownership: repeated acquire/release preserves battle and restores free roam")
finally:
    player.call_method("EndInteraction")
    if battle_hold:
        controller.set_ignore_move_input(False)
