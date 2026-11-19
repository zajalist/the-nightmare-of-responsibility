# Listening list (audio lane)

One line per cue. Files are in `P:\FoA-Assets\audio\SFX\` (the WAVs, playable in any player); the game plays the MetaSound presets of the same names in `/Game/FoA/Audio/MetaSounds/`. Licences: **CC0** (no conditions), **Sonniss** = Sonniss #GameAudioGDC Bundle License (free, commercial use, no attribution; not a Creative Commons licence, see notes).

| Cue | Files | Licence | Source | Fires |
|---|---|---|---|---|
| S_Footsteps_SocksWood | Footsteps\SFX_Footsteps_SocksWood_NN, SFX_Footsteps_WoodWalkSoft_NN | Sonniss | Filmnoise; RYK-Sounds | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_BootsWood | Footsteps\SFX_Footsteps_BootsWood_NN | CC0 | DavidGreck | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_DressShoeWood | Footsteps\SFX_Footsteps_DressShoeWood_NN | CC0 | Owlish Media | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_SocksRug | Footsteps\SFX_Footsteps_SocksRug_NN | Sonniss | Filmnoise; Kenney (kenney.nl) | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_BootsRug | Footsteps\SFX_Footsteps_BootsRug_NN | CC0 | DavidGreck; Kenney (kenney.nl) | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_WoodJog | Footsteps\SFX_Footsteps_WoodJog_NN | Sonniss | Filmnoise | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Footsteps_WoodSneak | Footsteps\SFX_Footsteps_WoodSneak_NN | Sonniss | Levan Nadashvili | every foot plant, through BPL_FoAAudio.PlayFootstep (anim lane wires AN_FoA_FootPlant) |
| S_Foley_ClothMove | Foley\SFX_Foley_ClothMove_NN | CC0 | Kenney (kenney.nl); iochi-glaucus | body moves: step cloth layer (PlayFootstep), reaches, crouches, turns (player notifies) |
| S_Foley_ClothTurn | Foley\SFX_Foley_ClothTurn_NN | CC0 | iochi-glaucus | body moves: step cloth layer (PlayFootstep), reaches, crouches, turns (player notifies) |
| S_Foley_Reach | Foley\SFX_Foley_Reach_NN | CC0 | iochi-glaucus | body moves: step cloth layer (PlayFootstep), reaches, crouches, turns (player notifies) |
| S_Foley_Crouch | Foley\SFX_Foley_Crouch_NN | CC0 | Joseph SARDIN; iochi-glaucus | body moves: step cloth layer (PlayFootstep), reaches, crouches, turns (player notifies) |
| S_Breath_TiredIdle_Loop_01 | Breath\SFX_Breath_TiredIdle_Loop_NN | Sonniss | UberDuo | the player idling (player lane, head AudioComponent) |
| S_Breath_Effort | Breath\SFX_Breath_Effort_NN | CC0 | Owlish Media | reaches, pulls, hits taken in the battle |
| S_Breath_Panic_Loop_01 | Breath\SFX_Breath_Panic_Loop_NN | CC0 | Joseph SARDIN | T8 battle bed (FOA_RoomAudio) |
| S_Props_HangerRail | Props\SFX_Props_HangerRail_NN | CC0 | DavidGreck | Hanger_CoatRail taken |
| S_Props_ScrewTurn | Props\SFX_Props_ScrewTurn_NN | Sonniss | Digital Rain Lab | each lock-plate screw coming out (BP_Door) |
| S_Props_ScrewDrop | Props\SFX_Props_ScrewDrop_NN | CC0 | Joseph SARDIN | each screw dropping (BP_Door) |
| S_Props_PaperRustle | Props\SFX_Props_BookPage_NN, SFX_Props_PaperRustle_NN | CC0 + Sonniss | 344 Audio; Joseph SARDIN | the desk searched |
| S_Props_ShirtPickup | Props\SFX_Bed_Sheets_NN, SFX_Props_ShirtPickup_NN | Sonniss | InMotionAudio | Shirt_T7 taken |
| S_Props_KeyDrop | Props\SFX_Props_KeyDrop_NN | Sonniss | Effectsworks | the key dropped |
| S_Props_VaseBreak | Props\SFX_Props_VaseBreak_NN | CC0 | Joseph SARDIN; Kenney (kenney.nl) | the vase-boss scene |
| S_Door_KeySnap | Door\SFX_Door_KeySnap_NN | CC0 | Joseph SARDIN + Ashley12275; rubberduck + Ashley12275 + Joseph SARDIN | T4 the key snapping in the lock (door KeyJammed); 2D, a lock clack, a metal snap and a short ring |
| S_Door_LatchSlide | Door\SFX_Door_LatchSlide_NN | CC0 | Joseph SARDIN | T5 LatchFree on the door |
| S_Door_HandleOff | Door\SFX_Door_HandleOff_NN | CC0 | Joseph SARDIN; Kenney (kenney.nl) | the handle coming off |
| S_Door_FinalOpen | Door\SFX_Door_FinalOpen_NN | Sonniss | Rogue Waves; West Wolf | T10 the door finally opens |
| S_Door_Close | Door\SFX_Door_Close_NN | Sonniss | 3maze; Coll Anderson; Rogue Waves | the door closing |
| S_Drawer_Open | Drawer\SFX_Drawer_Open_NN, SFX_Drawer_Slide_NN | CC0 + Sonniss | Articulated Sounds; SoundFxwizard; laleksic | commode drawers opening |
| S_Drawer_Close | Drawer\SFX_Drawer_Close_NN, SFX_Drawer_Small_NN | CC0 + Sonniss | 3maze; The Soundcatcher; laleksic | commode drawers closing |
| S_Drawer_Slide | Drawer\SFX_Drawer_Slide_NN | Sonniss | Articulated Sounds | the desk drawer opening |
| S_Drawer_Stop | Drawer\SFX_Drawer_Small_NN | Sonniss | The Soundcatcher | the desk drawer closing |
| S_Wardrobe_Rattle | Wardrobe\SFX_Wardrobe_Rattle_NN, SFX_Wardrobe_Wobble_NN | Sonniss | Antisample; The Soundcatcher | T6 the wardrobe rattles before it falls |
| S_Wardrobe_Creak | Wardrobe\SFX_Wardrobe_DoorCreak_NN | Sonniss | SoundBits | T6 the wardrobe leans |
| S_Wardrobe_Debris | Wardrobe\SFX_Wardrobe_Debris_NN | CC0 + Sonniss | Double Trouble Audio; rubberduck | T6 after the wardrobe lands |
| S_Phone_NightstandBuzz | Phone\SFX_Phone_NightstandBuzz_NN | CC0 | Joseph SARDIN | T0 the alarm phone on the nightstand |
| S_Door_Move | Door\SFX_Creaks_Groan_NN | Sonniss | Russell Gorsky | T7 the door moves walls |
| S_Ambience_RainOnGlass_Loop_01 | Ambience\SFX_Ambience_RainOnGlass_Loop_NN | Sonniss | Jake Fielding | always, on the bay glass (FOA_RoomAudio) |
| S_Ambience_DistantCity_Loop_01 | Ambience\SFX_Ambience_DistantCity_Loop_NN | Sonniss | West Wolf | always, far town hum at the bay (FOA_RoomAudio) |
| S_Ambience_Radiator_Loop_01 | Ambience\SFX_Ambience_Radiator_Loop_NN | CC0 | MKFI; stephan (pdsounds.org) | always, under the bay window (FOA_RoomAudio) |
| S_Ambience_Outside_Loop_01 | Ambience\SFX_Ambience_Outside_Loop_NN | Sonniss | Joseph SARDIN; West Wolf | T10 at the open door (FOA_RoomAudio) |
| S_Creaks_Settle | Creaks\SFX_Creaks_Board_NN, SFX_Creaks_Groan_NN, SFX_Creaks_Settle_NN, SFX_Creaks_Wood_NN | Sonniss | Coll Anderson; Russell Gorsky; SoundBits | the house settling, random spots every 5-18 s (FOA_RoomAudio) |
| S_Creaks_Floor | Creaks\SFX_Creaks_Floor_NN | Sonniss | RDGSFX005 | board creaks under steps near the bed and door (PlayFootstep) |
| S_Clock_TickFast_Loop_01 | Clock\SFX_Clock_TickFast_Loop_NN | Sonniss | Justsoundeffects | clock speed-up moments (story) |
| S_Sand_Hiss_Loop_01 | Sand\SFX_Sand_Hiss_Loop_NN | CC0 | stephan (pdsounds.org) | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Trickle_Loop_01 | Sand\SFX_Sand_Trickle_Loop_NN | Sonniss | Justsoundeffects | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Crumble | Sand\SFX_Sand_Crumble_NN | Sonniss | Pole Position Production | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Shift | Sand\SFX_Sand_Shift_NN | Sonniss | Eiravaein Works; Mechanical Wave | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Pour | Sand\SFX_Sand_Pour_NN | Sonniss | Pole Position Production | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Burst | Sand\SFX_Sand_Burst_NN | Sonniss | Alexander Kopeikin; Eneas Mentzel; Matt Script | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Sand_Footstep | Sand\SFX_Sand_Footstep_NN | CC0 | Fantozzi (via qubodup) | sand events: creep, piles, trickles, the suit, the hourglass, bursts (world lane) |
| S_Horror_Presence_Loop_01 | Horror\SFX_Horror_Presence_Loop_NN | Sonniss | Joseph SARDIN; ShapingWaves | while the Nightmare is visible, riding it (FOA_RoomAudio) |
| S_Story_HeadPressure | Story\SFX_Story_HeadPressure_NN | Sonniss | (see that row); ShapingWaves | headaches (FOA_RoomAudio) |
| S_Story_HeadRing | Story\SFX_Story_HeadRing_NN | CC0 | Joseph SARDIN | headaches (FOA_RoomAudio) |
| S_Story_TimeShift | Story\SFX_Story_TimeShift_NN | (see that row) | (see that row) | the day rollover (FOA_RoomAudio) |
| S_Story_SuitTone | Story\SFX_Story_SuitTone_NN | CC0 | Joseph SARDIN | T9 the suit payoff (FOA_RoomAudio) |
| S_Dream_Heartbeat_Loop_01 | Dream\SFX_Dream_Heartbeat_Loop_NN | Sonniss | ShapingWaves | under the day rollover (FOA_RoomAudio) |
| S_Dream_Gasp | Dream\SFX_Dream_Gasp_NN | Sonniss | UberDuo | the startle (player) |
| S_Dream_ReverseSwell | Dream\SFX_Dream_ReverseSwell_NN | Sonniss | 344 Audio; Airborne Sound; Coll Anderson | battle won (story) |
| S_Dream_TapeStop | Dream\SFX_Dream_TapeStop_NN | Sonniss | Airborne Sound; Soundopolis | time-shift accents |
| S_Battle_ClothSnap | Battle\SFX_Battle_ClothSnap_NN | CC0 | Joseph SARDIN | T8 battle hits, telegraphs, garments equipped (story lane, BP_Encounter) |
| S_Battle_Button | Battle\SFX_Battle_Button_NN | CC0 | Joseph SARDIN & Axeline T. | T8 battle hits, telegraphs, garments equipped (story lane, BP_Encounter) |
| S_Battle_Zipper | Battle\SFX_Battle_Zipper_NN | CC0 | DenisChardonnet; Joseph SARDIN | T8 battle hits, telegraphs, garments equipped (story lane, BP_Encounter) |
| S_Battle_FabricWhoosh | Battle\SFX_Battle_FabricWhoosh_NN | CC0 | Joseph SARDIN | T8 battle hits, telegraphs, garments equipped (story lane, BP_Encounter) |
| SFX_Horror_Stinger_01 (SoundWave) | Horror/SFX_Horror_Stinger_01.wav | designed scream (OpenGameArt "Horror scream1", CC0) + recorded female scream (OpenGameArt node/131040, CC0) + creature growl (OpenGameArt node/4543, CC0) + cinematic hit, sub boom and cymbal riser (Sonniss GDC) | CC0 + Sonniss | T5 jumpscare hit (BP_Jumpscare) |
| SFX_Horror_TensionBed_Loop_01 (SoundWave) | Horror/SFX_Horror_TensionBed_Loop_01.wav | OpenGameArt "Ambient horror" node/145577, an octave down | CC0 | T4-T5 dread at the dead door (BP_Jumpscare) |
| SFX_UI_*_A (11 SoundWaves) | UI_Tactile/ | Kenney rpg-audio cloth, book and leather (CC0); Sonniss foley: wardrobe latch, cupboard thunk, smartphone swipe, book page, wooden clock tick, phone motor buzz | CC0 + Sonniss | menus, HUD, phone (UI lane) |

## Notes

- **Sonniss GDC bundles** are royalty-free for commercial use with no attribution, but they are not Creative Commons. The licence (https://sonniss.com/gdc-bundle-license/) lets the sounds ship inside a game, but you may not redistribute or resell the raw sound files on their own as a library. A public Git repo that contains the source WAVs under `P:\FoA-Assets` or the raw `_libraries` folders would count as redistributing them; a cooked build is fine. Keep FoA-Assets out of any public repo.
- **CC0** files (OpenGameArt, Kenney, BigSoundBank, Wikimedia public domain) carry no conditions; credits are recorded anyway in `P:\FoA-Assets\audio\SOURCES.txt` and `MANIFEST.md`.
- Size: the Content/FoA/Audio folder is about 62 MB in the editor (the .uasset files keep the raw 16-bit PCM). Encoding the same 322 waves to Vorbis at quality 3 gives about 9 MB, so the cooked audio should land near 10-15 MB with the presets (an estimate, not a measured cook).
- In-engine listen: P:/FoA/Saved/BouncedWavFiles/HorrorShots/au10_mix.wav (wake to T7, 50 s, -21.9 LUFS integrated, true peak -4.7 dBFS, at most 11 sounds audible, sand bursts capped at 2). One clock ticks during the wake: the wall clock (Amb_ClockTick, S_Clock_Tick_Loop_01). The anim lane removed the wake film tick, so the double tick is gone (au10 sound list).
- Ending: P:/FoA/Saved/BouncedWavFiles/HorrorShots/au11_mix.wav (wake, then straight to T9 suit tone and T10 door and outside, 48 s, -23.4 LUFS, true peak -6.0 dBFS). The T8 battle is not in either file: the shortcut does not start it. Its cues (ClothSnap, FabricWhoosh, Breath_Effort, the equip sounds, Sand_Burst, ReverseSwell) are wired by story.
- Nothing here was synthesised; nobody has listened to the newest sets yet (picked by waveform and spectrogram).
- Stand-ins marked by the sourcing agents: the radiator (a gas boiler plus relay clicks), the coat hanger (small metal grinding), the screw drop (a nail on tiles, low-passed), the rug steps (layered).
