"""Listening list for the user: one line per playable cue with its files, sources, licence and where it fires.
  python Tools/Audio/listening_list.py   ->  docs/design/horror/listening_list.md
Reads the preset table (Tools/Unreal/horror/audio_table.py) and P:/FoA-Assets/audio/MANIFEST.md. Cues outside the table
(the jumpscare stinger and bed, the tactile UI set) are listed from EXTRA."""
import os
import re
import sys

sys.path.insert(0, 'P:/FoA/Tools/Unreal/horror')
import audio_table as T  # noqa: E402

SFX = 'P:/FoA-Assets/audio/SFX'
OUT = 'P:/FoA/docs/design/horror/listening_list.md'
FIRES = {
    'Footsteps': 'every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant)',
    'Foley': 'body moves: step cloth layer (PlayFootstep), reaches, crouches, turns (player notifies)',
    'S_Breath_TiredIdle_Loop_01': 'the player idling (player lane, head AudioComponent)',
    'S_Breath_Effort': 'reaches, pulls, hits taken in the battle',
    'S_Breath_Panic_Loop_01': 'T8 battle bed (FOA_RoomAudio)',
    'S_Props_HangerRail': 'Hanger_CoatRail taken', 'S_Props_ScrewTurn': 'each lock-plate screw coming out (BP_Door)',
    'S_Props_ScrewDrop': 'each screw dropping (BP_Door)', 'S_Props_PaperRustle': 'the desk searched',
    'S_Props_ShirtPickup': 'Shirt_T7 taken', 'S_Props_KeyDrop': 'the key dropped', 'S_Props_VaseBreak': 'the vase-boss scene',
    'S_Door_KeySnap': 'T4 the key snapping in the lock (door KeyJammed); 2D, a lock clack, a metal snap and a short ring',
    'S_Door_LatchSlide': 'T5 LatchFree on the door', 'S_Door_HandleOff': 'the handle coming off',
    'S_Door_FinalOpen': 'T10 the door finally opens', 'S_Door_Close': 'the door closing', 'S_Door_Move': 'T7 the door moves walls',
    'S_Drawer_Open': 'commode drawers opening', 'S_Drawer_Close': 'commode drawers closing',
    'S_Drawer_Slide': 'the desk drawer opening', 'S_Drawer_Stop': 'the desk drawer closing',
    'S_Wardrobe_Rattle': 'T6 the wardrobe rattles before it falls', 'S_Wardrobe_Creak': 'T6 the wardrobe leans',
    'S_Wardrobe_Debris': 'T6 after the wardrobe lands', 'S_Phone_NightstandBuzz': 'T0 the alarm phone on the nightstand',
    'S_Ambience_RainOnGlass_Loop_01': 'always, on the bay glass (FOA_RoomAudio)',
    'S_Ambience_DistantCity_Loop_01': 'always, far town hum at the bay (FOA_RoomAudio)',
    'S_Ambience_Radiator_Loop_01': 'always, under the bay window (FOA_RoomAudio)',
    'S_Ambience_Outside_Loop_01': 'T10 at the open door (FOA_RoomAudio)',
    'S_Creaks_Settle': 'the house settling, random spots every 5-18 s (FOA_RoomAudio)',
    'S_Creaks_Floor': 'board creaks under steps near the bed and door (PlayFootstep)',
    'S_Clock_TickFast_Loop_01': 'clock speed-up moments (story)',
    'Sand': 'sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane)',
    'S_Horror_Presence_Loop_01': 'while the Nightmare is visible, riding it (FOA_RoomAudio)',
    'S_Story_HeadPressure': 'headaches (FOA_RoomAudio)', 'S_Story_HeadRing': 'headaches (FOA_RoomAudio)',
    'S_Story_TimeShift': 'the day rollover (FOA_RoomAudio)', 'S_Story_SuitTone': 'T9 the suit payoff (FOA_RoomAudio)',
    'S_Dream_Heartbeat_Loop_01': 'under the day rollover (FOA_RoomAudio)', 'S_Dream_ReverseSwell': 'battle won (story)',
    'S_Dream_TapeStop': 'time-shift accents', 'S_Dream_Gasp': 'the startle (player)',
    'Battle': 'T8 battle hits, telegraphs, garments equipped (story lane, BP_Encounter)',
}
EXTRA = [
    ('SFX_Horror_Stinger_01 (SoundWave)', 'Horror/SFX_Horror_Stinger_01.wav',
     'designed scream (OpenGameArt "Horror scream1", CC0) + recorded female scream (OpenGameArt node/131040, CC0) + '
     'creature growl (OpenGameArt node/4543, CC0) + cinematic hit, sub boom and cymbal riser (Sonniss GDC)',
     'CC0 + Sonniss', 'T5 jumpscare hit (BP_Jumpscare)'),
    ('SFX_Horror_TensionBed_Loop_01 (SoundWave)', 'Horror/SFX_Horror_TensionBed_Loop_01.wav',
     'OpenGameArt "Ambient horror" node/145577, an octave down', 'CC0', 'T4-T5 dread at the dead door (BP_Jumpscare)'),
    ('SFX_UI_*_A (11 SoundWaves)', 'UI_Tactile/', 'Kenney rpg-audio cloth, book and leather (CC0); Sonniss foley: '
     'wardrobe latch, cupboard thunk, smartphone swipe, book page, wooden clock tick, phone motor buzz',
     'CC0 + Sonniss', 'menus, HUD, phone (UI lane)'),
]


def manifest():
    rows = {}
    for line in open('P:/FoA-Assets/audio/MANIFEST.md', encoding='utf-8'):
        m = re.match(r'\| `SFX/[^/]+/(SFX_[^`]+)\.wav` \|(.*)', line)
        if m:
            cells = [c.strip() for c in m.group(2).split('|')]
            rows[m.group(1)] = cells  # desc, source, url, author, licence, ...
    return rows


def lic(text):
    t = text.lower()
    return 'Sonniss' if 'sonniss' in t else 'CC0' if ('cc0' in t or 'public domain' in t) else text[:30]


def main():
    rows = manifest()
    lines = ['# Listening list (audio lane)', '',
             'One line per cue. Files are in `P:\\FoA-Assets\\audio\\SFX\\` (the WAVs, playable in any player); the game '
             'plays the MetaSound presets of the same names in `/Game/FoA/Audio/MetaSounds/`. Licences: **CC0** (no '
             'conditions), **Sonniss** = Sonniss #GameAudioGDC Bundle License (free, commercial use, no attribution; not a '
             'Creative Commons licence, see notes).', '',
             '| Cue | Files | Licence | Source | Fires |', '|---|---|---|---|---|']
    for name, spec in T.PRESETS.items():
        cat = name.split('_')[1]
        ws = [w for w in spec['waves'] if os.path.exists(f'{SFX}/{w.split("_")[1]}/{w}.wav')]
        lics = sorted({lic(rows[w][4]) for w in ws if w in rows and len(rows[w]) > 4} or {'see SOURCES.txt'})
        srcs = sorted({s for w in ws if w in rows and len(rows[w]) > 3 for s in (rows[w][3] or rows[w][1][:40]).split('<br>')})
        fires = FIRES.get(name) or FIRES.get(cat, '')
        files = f'{cat}\\' + ', '.join(sorted({re.sub(r"_\d\d$", "_NN", w) for w in ws}))
        lines.append(f'| {name} | {files} | {" + ".join(lics)} | {"; ".join(srcs)[:160]} | {fires} |')
    for row in EXTRA:
        lines.append('| ' + ' | '.join(row) + ' |')
    lines += ['', '## Notes', '',
              '- **Sonniss GDC bundles** are royalty-free for commercial use with no attribution, but they are not '
              'Creative Commons. The licence (https://sonniss.com/gdc-bundle-license/) lets the sounds ship inside a game, '
              'but you may not redistribute or resell the raw sound files on their own as a library. A public Git repo '
              'that contains the source WAVs under `P:\\FoA-Assets` or the raw `_libraries` folders would count as '
              'redistributing them; a cooked build is fine. Keep FoA-Assets out of any public repo.',
              '- **CC0** files (OpenGameArt, Kenney, BigSoundBank, Wikimedia public domain) carry no conditions; credits are '
              'recorded anyway in `P:\\FoA-Assets\\audio\\SOURCES.txt` and `MANIFEST.md`.',
              '- Size: the Content/FoA/Audio folder is about 62 MB in the editor (the .uasset files keep the raw 16-bit PCM). '
              'Encoding the same 322 waves to Vorbis at quality 3 gives about 9 MB, so the cooked audio should land near '
              '10-15 MB with the presets (an estimate, not a measured cook).',
              '- In-engine listen: P:/FoA/Saved/BouncedWavFiles/HorrorShots/au10_mix.wav (wake to T7, 50 s, '
              '-21.9 LUFS integrated, true peak -4.7 dBFS, at most 11 sounds audible, sand bursts capped at 2). One clock '
              'ticks during the wake: the wall clock (Amb_ClockTick, S_Clock_Tick_Loop_01). The anim lane removed the wake '
              'film tick, so the double tick is gone (au10 sound list).',
              '- Ending: P:/FoA/Saved/BouncedWavFiles/HorrorShots/au11_mix.wav (wake, then straight to T9 suit tone and T10 door '
              'and outside, 48 s, -23.4 LUFS, true peak -6.0 dBFS). The T8 battle is not in either file: the shortcut does not '
              'start it. Its cues (ClothSnap, FabricWhoosh, Breath_Effort, the equip sounds, Sand_Burst, ReverseSwell) are wired by story.',
              '- Nothing here was synthesised; nobody has listened to the newest sets yet (picked by waveform and spectrogram).',
              '- Stand-ins marked by the sourcing agents: the radiator (a gas boiler plus relay clicks), the coat hanger '
              '(small metal grinding), the screw drop (a nail on tiles, low-passed), the rug steps (layered).']
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(T.PRESETS) + len(EXTRA), 'cues')


main()
