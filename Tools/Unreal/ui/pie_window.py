"""FOA_PIE_WINDOW=on: PIE in its own 1920x1080 window (clean 'Shot showui' frames); =off restores in-viewport PIE."""
import os
import unreal
s = unreal.get_default_object(unreal.LevelEditorPlaySettings)
on = os.environ.get('FOA_PIE_WINDOW', 'on') == 'on'
for k, v in (('new_window_width', 1920), ('new_window_height', 1080)):
    s.set_editor_property(k, v)
s.set_editor_property('last_executed_play_mode_type',
                      unreal.PlayModeType.PLAY_MODE_IN_EDITOR_FLOATING if on else unreal.PlayModeType.PLAY_MODE_IN_VIEWPORT)
print('pie window', on)
