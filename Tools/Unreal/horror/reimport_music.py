"""Audio lane: re-import rebuilt music WAVs over their existing SoundWaves (same asset names, so BP_RoomAudio's Tracks
and the sting keep pointing at them). Hayba's asset_import refuses to overwrite, so this uses editor Python's
AssetImportTask with replace_existing. Then run wave_settings.py (class, looping, streaming).
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/reimport_music.py FOA_MUSIC=MUS_Menu_Loop,..."""
import os

import unreal

names = [n for n in os.environ.get('FOA_MUSIC', '').split(',') if n]
tasks = []
for n in names:
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', f'P:/FoA-Assets/audio/music/processed/{n}.wav')
    t.set_editor_property('destination_path', '/Game/FoA/Audio/Music')
    t.set_editor_property('destination_name', n)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('automated', True)
    t.set_editor_property('save', True)
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for n in names:
    w = unreal.load_asset(f'/Game/FoA/Audio/Music/{n}')
    print('reimported', n, round(w.get_editor_property('duration'), 2) if w else 'MISSING')
