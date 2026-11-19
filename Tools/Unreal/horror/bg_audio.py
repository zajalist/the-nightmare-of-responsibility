"""Editor background audio for sound-on proofs (the editor mutes everything without focus):
  FOA_BG=get  prints the current LevelEditorMiscSettings.bAllowBackgroundAudio into the log ("get" console command)
  FOA_BG=0|1  sets it (in memory only, never saved to config)
record_audio.sh reads the value before the burst and restores exactly that value on every exit path."""
import os

import unreal

v = os.environ.get('FOA_BG', 'get')
cmd = 'get LevelEditorMiscSettings bAllowBackgroundAudio' if v == 'get' else f'set LevelEditorMiscSettings bAllowBackgroundAudio {v}'
unreal.SystemLibrary.execute_console_command(None, cmd)
print('bg_audio', cmd)
