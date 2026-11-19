# Wiring audit: does the real game loop trigger each system?

Owner: gameplay (integration), 2026-11-06. The user's ask: "a lot of systems were made but they gotta be wired to the actual game loop".

**Method.**
1. A static pass over every builder script, citing the caller of each system in the loop's own graphs.
2. Asset existence and referencers from the editor's asset registry (`Saved/Integration/wiring_probe.json`, `audio_refs.json`).
3. In-play evidence from PIE playthroughs. Each starts from cold boot and goes through the real front end, the real LS_WakeUp (skipped with its own skip event) and real interactions. The interactor focuses the object, then its Interact input handler runs, so the rows, montages, prompts, sounds and beat events are the game's own.

The driver is `Tools/Unreal/gameplay/pie_play.py`, run by `play_burst.sh <plan>`. Logs are `Saved/Integration/play_<plan>.json`, with the state of every system below at each beat. Frames are in `Saved/Integration/play_<plan>_frames/`, and the contact sheets are `play_<plan>_sheet.png` and `playthrough_sheet.png`.

**Plans.**
- **A:** boot to T7, all by real interactions.
- **B:** T7 (shortcut), take the shirt for real, fight T8 to a win, T9.
- **C:** T9 and T10 (shortcuts), walk out through the doorway, level end.
- **D:** lose T8, the rollover, a new morning, pause and Restart the day, Settings, Credits, Quit to title.

**Status.**
- **LIVE:** triggered in play, with evidence.
- **WIRED NOW:** was not reached; wired in this pass, with evidence.
- **GAP:** not reached; the owner has the exact hook.
- **NOT BUILT:** the asset doesn't exist yet.

| System | Status | Evidence in play | Owner / action |
|---|---|---|---|
| Boot splash, title, main menu, Wake up | LIVE | play_A.json: screen WBP_BootSplash, then WBP_Title, then WBP_MainMenu, then None; view BP_MenuCamera, then CineCameraActor | ui |
| LS_WakeUp played by BP_BeatDirector, hold-to-skip | LIVE | View CineCameraActor while it plays; SkipWakeUp ends it on the pawn standing at the bed (view BP_FoAPlayer); T0 7.4 s after boot (play_A) | gameplay, cine |
| SetCinematic / SetSuspended in the wake-up | LIVE | anim's PIE check at 11:11 (Saved/AnimShots/v7_events.txt: bCinematic and focus None); the phone run at 11:51 shows the interactor suspended while the film owns the camera | anim, gameplay |
| T0 phone (BP_Phone on the nightstand, WBP_Phone, OpenPhone, DoAction to PhoneWakeUp) | WIRED NOW (ui re-placed it at 11:34 after the accidental cut) | play_A 12:01: at T0 the view becomes BP_Phone_C (the push-in) 7.9 s after cold boot, the phone screen WBP_Phone_C is visible, and its DoAction (what Enter, E, Space and A run) reports PhoneWakeUp: T1 at 10.4 s. The framing that clipped "Wake up" was fixed by ui at 12:09. At T10 the phone opens again ("Leave the house") and DoAction closes it. | ui |
| Phone tasks and notebook | LIVE (tasks); GAP (notebook) | Tasks tick by design: Wake up at the T9 payoff, Get dressed at T8, Leave the house at T10, Find a job never. WBP_Phone.Refresh never fills Txt_Notebook. | ui |
| HUD objective (OnBeatChanged) | LIVE | Every beat's objective line is in frame (play_A_sheet.png, play_B_sheet.png) | ui |
| Interaction prompt, subtitles, item toasts | GAP | BPC_Interactor has the prompt (play_A: "Search the desk", "Use the key again", "Take the wire hanger"), but nothing on WBP_HUD binds OnFocusChanged, OnNarration or OnInventoryChanged, and no prompt is in frame | ui (hook sent) |
| T1 first steps | LIVE | Walking for 1.5 s: FirstSteps, T2 (play_A) | gameplay |
| T2 to T7 interactions (desk, boot, key, hanger, handle, wardrobe) | LIVE | play_A: "Search the desk" T3; "Look inside the boot" T4; "Use the key again" T5; "Take the wire hanger", then "Use the wire hanger on the door gap" T6; "Pull the handle, and mind the wardrobe" T7. The montages play in the frames (kneel, reach, pull). | gameplay |
| Interactable sounds (BP_Interactable.StateSounds via PlayFeedback) | WIRED NOW | All 14 interactables had an empty map, so nothing in the house made a sound. wire_sounds.py fills it from the audio lane's MetaSounds: door key snap, unlock, handle, open; drawer and wardrobe doors; wardrobe fall and impact; boot, key, screwdriver, hanger, shirt. Live sound list in plan C's frames (au.Debug.Sounds). | gameplay (audio lane idle) |
| Room ambience | WIRED NOW | Amb_RoomTone, Amb_NightWind (bay) and Amb_ClockTick (wall clock) placed; is_playing True at every beat (play_A) | gameplay (audio lane idle) |
| Footsteps | WIRED NOW (anim) | S_Footsteps_WoodWalk notifies on every foot plant of the walk clip (anim, 11:4x); the sand step via BPL_SandFX.SpawnSandStep is forwarded to anim | anim |
| Front-end cues (SFX_FE_*, PlayUISound), menu hover and select | LIVE | Referenced by BP_FoAFrontEnd and WBP_SandButton and reached from BeginPlay, WakeUp and pause (static); the story bed and panel cues need StoryClass | ui |
| BP_DreamDirector tiers | LIVE | OpenTier 0 for T0-T6, 0.5 at T7 (play_A); TierGlitch is Tier x 0 by design (look) | look |
| Hue drift over the story | WIRED NOW | Nothing called SetHueDrift. The director's ShowTier now calls SetHueDrift(BeatIndex x 0.06): HueDrift 0, 0.06, 0.12 ... 0.42 at T0-T7 (play_A) | gameplay |
| Echo, face slip | LIVE | EchoStrength animates 0.29-0.42; FaceSlip 1.0, and the face blur is in frame | look |
| Glitch bursts | LIVE (rollover, menu) | PlayGlitch from FailDay; menu-mode datamosh while the title is up | look, gameplay |
| T9 payoff (letterbox, colour reveal, suit) | LIVE | ColorReveal 1.0 and Letterbox 1.0 at the T9 to T10 hand-off (play_B) | gameplay, look |
| Equip / UnequipAll (T8 wins, T9 suit, new day) | LIVE, but no clothes yet | All five garment slots turn visible at T9 (play_B), but every slot's SkeletalMesh is None, so nothing changes on screen. The snap montage and sand play. | character (the worn meshes; waiting on the user) |
| T8 encounter (ShirtTaken, fight, win and lose) | LIVE, one bug fixed | play_B: "Take the shirt", then T8 intro, the fight, Victory, T9. Earlier: Defeat, then FailDay (t8_lose.mp4). **Bug found and fixed (12:15):** taking the shirt during T7's top-down hold let the hold's ExitTopDown timer fire mid-fight, putting the view back on the pawn instead of the battle camera and hiding the T8 Nightmare. StartShirtFight now leaves top-down first. | gameplay |
| Sand bursts (interactables, equip, encounter) | WIRED NOW | BPL_SandFX landed at 11:49 (look). BP_Interactable and BP_Encounter are rebuilt and now depend on it; BurstStates are set on the wardrobe, the door, the key, the hanger and the shirt | look, gameplay |
| Ambient sand blooms | WIRED NOW (look) | The dream director's AmbientBloomTick exists since 11:49; it spawns with CurrentTier from SetTier, which runs on every beat | look |
| Step absorption (MPC_Dream PlayerPos) | LIVE | PlayerPos follows the pawn at every beat (play_A) | anim, look |
| Sand clock in the wake-up (BP_SandMaterialize, SandClock_WakeUp) | WIRED NOW (look placed it; cine keys it) | Placed at (317, -96, 79.7), tag WakeUpClock | look, cine |
| Morph stations, sand overlay | NOT BUILT | BP_SandMorph and M_SandOverlay don't exist yet; nothing to wire | look |
| BP_Nightmare (Appear, Vanish, StalkTo) | WIRED NOW | anim built it (12:10). I placed one (label Nightmare, folder Gameplay, hidden until Appear) and rebuilt the director, so Show, Hide and Ride resolve. play_B 12:13: visible at the T7 doorway (439, 88); visible at the T8 bay alcove (-60, -350); hidden at T9. StalkTo has no caller: no beat asks for it. | anim, gameplay |
| Day rollover with knowledge | LIVE | Defeat, FailDay, card "Day 23 / Day 24", OnRolloverCovered, LS_WakeUp, T0 (t8_lose_rollover_sheet.png; no HUD over the film since ui's 03:07 fix). Knowledge persists: day 28 and all six Knows.* flags at boot (play_A). Known flags shorten rows: "Use the key again" | gameplay, ui |
| Pause, Restart the day, Quit to title | LIVE | Quit to title in the earlier integration burst B (beat None, menu camera); plan D repeats it with Restart the day | ui, gameplay |
| Settings, Credits | NOT BUILT | WBP_Settings and WBP_Credits don't exist, so OpenSettings and OpenCredits do nothing | ui (hook sent) |
| Mouse sensitivity, invert Y | GAP | Never applied to look input | ui (IA_Look modifiers from BPFL_FoASettings) |
| First-start story | GAP | StoryClass is unset | ui |
| Level end | LIVE, one defect | WalkedOut, director fade, BP_FoAFrontEnd.EndOfLevel, title (plan C). The front end restarts its fade from alpha 0 over the director's black, so the room flashes | ui (FromAlpha 1) |
| Save and load (SG_FoA via GI_FoA) | LIVE | DayCount and Knowledge persist across PIE sessions (day 28 at boot, play_A); saved by Learn and StartNewDay | gameplay |

## Fixed in this pass (gameplay)
- **BP_Interactable.GetPrompt:** guarded against a missing player. 462 "Accessed None ... GetInteractor" errors came from a world without a possessed player (the wake-up's spawned pawn in movie renders).
- **BP_BeatDirector:** binds BPC_Interactor.OnBeatEvent each morning instead of at BeginPlay, and LearnFromFailure guards a missing beat. Earlier Accessed None errors.
- **Encounter_T8:** restored after the 11:19 accidental cut to its true transform, (-200, -55, 0) yaw 180, recovered from its old bounds record.
- **Interactable sounds, room ambience, sand bursts, hue drift:** see the table.

## Hooks sent to active owners
ui (11:2x and 11:4x): the T0 phone (done 11:34); HUD prompt, subtitle and toast listeners; WBP_Settings and WBP_Credits; EndOfLevel FromAlpha 1; the notebook; StoryClass; IA_Look sensitivity and invert.
look (11:2x): BPL_SandFX, stage 5, BP_SandMaterialize and the clock (done 11:49); BP_SandMorph, M_SandOverlay (backlog).
anim (11:2x): BP_Nightmare (built); footsteps (done); the sand step; the rebuild trap (fixed).
character: the worn garment meshes (waiting on the user).
