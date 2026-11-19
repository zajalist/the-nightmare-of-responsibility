# Audio pass: what plays where (audio lane)

Everything below is a real recording, either CC0 or a royalty-free library already licensed by the project. Sources are
in `P:\FoA-Assets\audio\SOURCES.txt` and `MANIFEST.md`. Every playable sound is a MetaSound preset in
`/Game/FoA/Audio/MetaSounds/<Category>/S_<Category>_<Name>`, built from the shared random template:
- a random take each time, never the same one twice in a row;
- about +-1 semitone of pitch and 0.85-1.0 volume;
- the right SoundClass and attenuation already set.

Play a preset with PlaySoundAtLocation for positional sounds, or PlaySound2D for the 2D ones (Story, Battle, Breath panic,
Dream). The preset table is `Tools/Unreal/horror/audio_table.py`.

## Mix
- **Classes:** SC_Master is the parent of SC_SFX, SC_Ambience, SC_UI, SC_Dialogue and SC_Music. SC_Dialogue and SC_Music are new, for VO and the user's tracks.
- **Submixes:**
  - SFX, Ambience and Dialogue route to `SM_Bedroom`, a small-room reverb: `RVB_Bedroom`, decay 0.55 s, wet 0.22 against dry 1.0.
  - Music routes to `SM_Music`, which is dry.
  - UI stays dry.
- **Ducking:** push `Mix/SMX_StoryDuck` for a stinger or story moment (SFX to 50%, Ambience to 35%, 0.3 s in, 1.5 s out), then pop it. The jumpscare uses its own `SMX_Jumpscare_Hush`.
- **Attenuation:**
  - `ATT_SFX_Near` is for the body, footsteps and props.
  - `ATT_SFX_Room` is for the room, with occlusion on (2.5 kHz low-pass behind walls and the door).
- **Streaming:** loops of 8 s or more stream (load on demand) at compression quality 40.

## Already wired by the audio lane (no action needed)
- **`FOA_Jumpscare` (BP_Jumpscare):** the T5 scare.
- **`FOA_RoomAudio` (`/Game/FoA/Audio/BP_RoomAudio`, placed at the room origin):** reads BP_BeatDirector's public state on a 0.25 s timer. It plays:
  - rain on the bay glass, the radiator under the bay and the distant town hum;
  - house-settling creaks at random spots every 5-18 s, more often as the beats advance;
  - the Nightmare presence drone, following BP_Nightmare while it is visible;
  - the headache pressure and ring while `bHeadacheActive` is true, with the mix ducked;
  - the time-shift and a heartbeat bed while `bRollingOver` is true;
  - panic breathing during T8;
  - the suit tone with a 4 s duck at T9;
  - the outside morning at the door, fading in at T10.
- **`BPL_FoAAudio.PlayFootstep(Location, Surface, Gear, Gait)`:** the whole footstep logic.
  - Surface and gear choose the take: socks, boots or dress shoes, on wood or rug.
  - Gait sets the volume.
  - There's a board creak near the bed foot and the door, and a cloth rustle under the step.

## For the anim/player lane (AN_FoA_FootPlant, BP_FoAPlayer)

| Asset | Event | Call |
|---|---|---|
| AN_FoA_FootPlant | Received_Notify, the non-Sand branch (replaces the S_Footsteps_WoodWalk PlaySound) | `BPL_FoAAudio.PlayFootstep(Location = trace impact point, Surface = 'Rug' if the hit actor has tag Rug else 'Wood', Gear = 'Boots' after SetBootsWorn(true), 'Shoes' after Equip('Suit'), else 'Socks', Gait = ground speed / 250 clamped 0..2)` |
| BP_FoAPlayer | montage notify Grab (AM_FoA_PickUp_Floor/Table) | `S_Foley_Reach` at the hand; `S_Breath_Effort` 40% of the time |
| BP_FoAPlayer | Grip and Pull (AM_FoA_OpenDrawer) | `S_Breath_Effort` (Pull only) |
| BP_FoAPlayer | KneelDown (AM_FoA_KneelScrewdriver) | `S_Foley_Crouch` |
| BP_FoAPlayer | Startle (AM_FoA_Startle) | `S_Dream_Gasp` |
| BP_FoAPlayer | turning faster than about 120 deg/s (0.6 s cooldown) | `S_Foley_ClothTurn` |
| BP_FoAPlayer | an AudioComponent on the head, auto-play, volume 0.3; fade out during SetCinematic(true) and the battle | `S_Breath_TiredIdle_Loop_01` |

## For the story lane (BP_BeatDirector, Encounter)

| Asset | Event | Sound |
|---|---|---|
| BP_BeatDirector | T0, the first morning, about 0.5 s before the phone rises | `S_Phone_NightstandBuzz` at Phone_Nightstand |
| BP_BeatDirector | BeginWardrobeTransition (the 2 s rattle) | `S_Wardrobe_Rattle` and then `S_Wardrobe_Creak` at the wardrobe |
| BP_BeatDirector | the wardrobe lands (WardrobeLanded), +0.25 s | `S_Wardrobe_Debris` at the fallen wardrobe |
| BP_BeatDirector | MoveDoor (T7) | `S_Door_Move` at DoorFrame, plus `S_Sand_Pour` |
| BP_BeatDirector | OpenTheDoor (T10) | `S_Door_FinalOpen` at Door (BP_RoomAudio adds the outside bed) |
| BP_Encounter | OnStateChanged, a garment going to Telegraph | `S_Battle_FabricWhoosh` |
| BP_Encounter | OnDamage, Who = a garment | `S_Battle_ClothSnap` |
| BP_Encounter | OnDamage, Who = the pawn | `S_Battle_FabricWhoosh` + `S_Breath_Effort` |
| BP_Encounter | OnGarmentEquipped: Shirt / Trousers / Socks / Tie | `S_Battle_Button` / `S_Battle_Zipper` / `S_Foley_ClothMove` / `S_Battle_ClothSnap` |
| BP_Encounter | OnSandBurst | `S_Sand_Burst` at the garment |
| BP_Encounter | OnEncounterWon | `S_Dream_ReverseSwell`, with SMX_StoryDuck pushed for 2 s |

## For the world lane (interactables, sand events, level)

| Asset | Event | Sound |
|---|---|---|
| Dress_Rug_Bedside, Dress_Rug_Door | add actor tag `Rug` | (footsteps read it) |
| BP_Door (Door_Bedroom) | each ToolScrew0-3 turning out | `S_Props_ScrewTurn` at the screw, then `S_Props_ScrewDrop` as it falls |
| BP_Door | LatchFree | `S_Door_LatchSlide` |
| BP_Door | HandleOff | `S_Door_HandleOff` |
| BP_Door | Open (the final open) | `S_Door_FinalOpen` |
| Commode/desk drawers (BP_Container) | Open / Closed | add `S_Drawer_Slide` under the existing Open, and `S_Drawer_Stop` after Close |
| Hanger_CoatRail (BP_Pickup) | Taken | `S_Props_HangerRail` (today it plays KeyPickup) |
| Shirt_T7 (BP_Pickup) | Taken | `S_Props_ShirtPickup` (today it plays Bed_Sheets) |
| Desk (BP_Interactable) | searched or looked at | `S_Props_PaperRustle` |
| Key_Lux3D | dropped (if ever) | `S_Props_KeyDrop` |
| BP_SandAmbience | Ev_Creep, Ev_Pile, Ev_Shirt | `S_Sand_Shift` at the site |
| BP_SandAmbience | Ev_Trickle, Ev_ClockDrip | `S_Sand_Trickle_Loop_01` on the part while it plays |
| BP_SandAmbience | Ev_Drift, WatchStill | `S_Sand_Hiss_Loop_01`, quiet (0.4) |
| BP_SandAmbience | Ev_Suit forming / falling | `S_Sand_Pour` / `S_Sand_Burst` |
| BP_SandAmbience | Ev_Hourglass crumbling | `S_Sand_Crumble` |
| BP_SandAmbience | Ev_Glimpse burst | `S_Sand_Burst` |
| BP_ChairNightmare | StartVision / Crumble | `S_Sand_Pour` / `S_Sand_Crumble` |

## For the cine lane
- **LS_WakeUp:** at 25.4 s, when the clock crumbles in his hand, play `S_Sand_Crumble` (SandClock_WakeUp).

## For the UI lane
- **Tactile UI set** in `/Game/FoA/Audio/SFX/UI/`, already sent: `SFX_UI_Hover_A`, `SFX_UI_Confirm_A`, `SFX_UI_Back_A`, `SFX_UI_Open_A`, `SFX_UI_Close_A`, `SFX_UI_PhoneTap_A`, `SFX_UI_PhoneBuzz_A`, `SFX_UI_PageTurn_A`, `SFX_UI_SliderTick_A`, `SFX_UI_PauseIn_A`, `SFX_UI_PauseOut_A`.
- **Settings:** add Music and Dialogue volume sliders to the settings and `SCM_Settings` (SC_Music, SC_Dialogue).
