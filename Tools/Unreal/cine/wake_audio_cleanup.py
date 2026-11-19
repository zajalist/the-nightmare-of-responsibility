"""LS_WakeUp audio cleanup (horror's au3 analysis, main 2026-11-09). Re-runnable.
1. Drops every audio section playing SFX_Clock_Tick_Loop_01 (the others on its track stay): the wall clock (Amb_ClockTick) already ticks, so it doubled.
2. Swaps raw waves for the audio lane's random no-repeat presets: SFX_Creaks_Floor_02 -> S_Creaks_Floor,
   SFX_Sand_Pour_01 -> S_Sand_Pour, SFX_Sand_Shift_02 -> S_Sand_Shift. A section that is hand-timed (it starts part-way
   into the wave, or is cut shorter than the wave) keeps its raw wave and is reported instead.
FOA_DRY=1 only reports.
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/wake_audio_cleanup.py FOA_AREAS=Cinematics [FOA_DRY=1]"""
import os

import unreal

SEQ = '/Game/FoA/Cinematics/LS_WakeUp'
DROP = 'SFX_Clock_Tick_Loop_01'
SWAP = {'SFX_Creaks_Floor_02': '/Game/FoA/Audio/MetaSounds/Creaks/S_Creaks_Floor',
        'SFX_Sand_Pour_01': '/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Pour',
        'SFX_Sand_Shift_02': '/Game/FoA/Audio/MetaSounds/Sand/S_Sand_Shift'}
dry = os.environ.get('FOA_DRY') == '1'
seq = unreal.load_asset(SEQ)
rate = seq.get_display_rate()
fps = rate.numerator / rate.denominator
owners = [(None, seq.get_tracks())] + [(b, b.get_tracks()) for b in seq.get_bindings()]
report = []
for owner, tracks in owners:
    for t in [t for t in tracks if isinstance(t, unreal.MovieSceneAudioTrack)]:
        secs = t.get_sections()
        where = str(owner.get_display_name()) if owner else 'master'
        for s in secs:
            snd = s.get_sound()
            if snd and snd.get_name() == DROP:  # one track holds many sounds: drop only the tick's sections
                report.append(('drop section', where, DROP, 'frames', s.get_start_frame(), s.get_end_frame()))
                if not dry:
                    t.remove_section(s)
                continue
            if not snd or snd.get_name() not in SWAP:
                continue
            frames = (s.get_end_frame() - s.get_start_frame()) / fps
            try:
                offset = s.get_start_offset().value
            except Exception:
                offset = 0
            dur = snd.get_editor_property("duration")
            cut = dur < 1000 and frames + 0.05 < dur
            if offset or cut:
                report.append(('keep raw (hand-timed)', where, snd.get_name(), s.get_start_frame(), 'offset', offset,
                               'section %.2f s of %.2f s' % (frames, dur)))
                continue
            new = unreal.load_asset(SWAP[snd.get_name()])
            assert new, SWAP[snd.get_name()]
            report.append(('swap', where, snd.get_name(), '->', new.get_name(), 'at frame', s.get_start_frame(), 'for %.2f s' % frames))
            if not dry:
                s.set_sound(new)
if not dry:
    assert unreal.EditorAssetLibrary.save_loaded_asset(seq, False)
for r in report:
    print('WAKE_AUDIO', *r)
print('WAKE_AUDIO done', 'dry' if dry else 'saved', len(report))
