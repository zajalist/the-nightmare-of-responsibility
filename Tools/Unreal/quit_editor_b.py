"""Editor B only: quit without saving (coordinator's request; equivalent to File > Exit, Don't Save)."""
import unreal
dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()] + \
        [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
print("B_QUIT dirty (not saved):", dirty[:20])
unreal.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")
