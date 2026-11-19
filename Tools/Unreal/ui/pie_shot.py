"""Requests a PIE viewport screenshot WITH the UI ('Shot showui'); the engine writes
Saved/Screenshots/<Platform>/ScreenShot#####.png a frame later (pie_tour.sh renames it)."""
import unreal


def main():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        print('NO_PIE_WORLD')
        return
    unreal.SystemLibrary.execute_console_command(world, 'Shot showui')
    print('shot requested')


main()
