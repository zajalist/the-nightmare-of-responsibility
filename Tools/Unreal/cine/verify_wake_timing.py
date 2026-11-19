"""Read back the live sequence's clock keys and clock audio sections; assert the slap contract."""
import json
from pathlib import Path
import unreal

seq = unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
rate = seq.get_display_rate().numerator / seq.get_display_rate().denominator
rows = {}
for binding in seq.get_bindings():
    if str(binding.get_display_name()) != 'SandClock':
        continue
    for track in binding.get_tracks():
        if not isinstance(track, unreal.MovieSceneFloatTrack):
            continue
        prop = str(track.get_property_name())
        rows[prop] = [(key.get_time().frame_number.value / rate, key.get_value())
                      for section in track.get_sections() for channel in section.get_all_channels() for key in channel.get_keys()]
audio = {}
for track in seq.get_tracks():
    if isinstance(track, unreal.MovieSceneAudioTrack):
        for section in track.get_sections():
            sound = section.get_sound()
            if sound and sound.get_name() in ('SFX_Clock_Tick_Loop_01', 'SFX_Clock_AlarmRing_Loop_01'):
                audio[sound.get_name()] = [section.get_start_frame_seconds(), section.get_end_frame_seconds()]
assert (25.3, 0.0) in rows['Ring'], rows
assert (25.3, 0.0) in rows['DissolveAmount'] and (26.5, 1.0) in rows['DissolveAmount'], rows
assert len(audio) == 2 and all(abs(s - 2.3) < .001 and abs(e - 25.3) < .001 for s, e in audio.values()), audio
out = dict(clock=rows, audio=audio, verified=True)
Path('P:/FoA/Saved/AnimShots/wake_timing_verified.json').write_text(json.dumps(out, indent=1))
print(out)
