# Gameplay contract (cross-lane names)

This is the single source of truth for names that cross lanes. If you need something that isn't here, message the owning lane directly; the addresses are at the bottom. Whoever builds an item updates its line here. All paths are under /Game/FoA.

## Level flow (owner: mech_flow)
- Find the director with `GetActorOfClass(BP_BeatDirector)`.
- **Assets:** `Gameplay/BP_BeatDirector`, `Gameplay/GI_FoA` (the project GameInstance), `Gameplay/SG_FoA`, and `Gameplay/Beats/PDA_Beat` with one data asset per beat, `DA_Beat_T0` to `DA_Beat_T10`. Editor Python can't author UserDefinedStruct or UserDefinedEnum members, so there is no E_Beat, S_Beat or DT_Beats: beat ids are the Names "T0" to "T10".
- **`BP_BeatDirector.BeginMorning()`:** the main menu's Wake Up button calls this (UI lane), and so does every new morning. It plays the wake-up lane's BP_WakeUpCinematic, if it exists; that ends in OnWakeUpFinished. Then StartMorningBeats paces T0 (objective "Wake up.", ShowPhone) : the room first (the hand-off fade-up, then free look); 2.7 s in, OpenMorningPhone plays S_Phone_NightstandBuzz at the phone; 0.5 s later RaiseMorningPhone enters T0 and calls `BP_FoAFrontEnd.OpenPhone()` on the list; T0 completes on the phone's Wake up (PhoneWakeUp). With no front end, T0 completes by itself.
- **`BP_BeatDirector.ReportEvent(Event: Name)`:** the one entry point for interactables, the phone and the encounter. Events that belong to a later beat skip ahead, so knowledge shortcuts work. First steps (T1) are detected by the director. Events:

  | Event | Beat |
  |---|---|
  | PhoneWakeUp | T0 |
  | Searched | T2, any container opened |
  | LookedAtBed | T2 |
  | KeyTaken | T3 |
  | KeySnapped | T4 |
  | LatchFreed | T5, either route |
  | WardrobeFalling | T6 cinematic starts; does not advance the beat |
  | WardrobeLanded | T6 |
  | ShirtTaken | T7 |
  | EncounterWon | T8 |
  | PayoffEnded | T9 |
  | WalkedOut | T10 |

- **`BP_BeatDirector.FailDay()`:** the encounter's lose hand-off. It plays the day rollover.
- **`BP_BeatDirector.RestartDay()`:** pause menu "Restart Day". It's a new day like FailDay, but with no glitch and no mare, and nothing is learned: a fade to black, then T0. Unpause before calling it, because the fade waits on game time.
- **`BP_BeatDirector.ResetToTitle()`:** pause menu "Quit to Title". There's no new day: the house and beat state go back to before T0 and the player returns to the bed. The title then calls BeginMorning() again.
- **Dev keys (not in distribution builds):** F9 reports the current beat's first event (or begins the morning), and F10 fails the day.
- **Dispatcher `OnBeatChanged(Beat: Name, Objective: Text, ShowPhone: bool)`:** the HUD shows Objective. The phone opens when ShowPhone is true (T0 and T10).
- **Dispatcher `OnPhoneChanged()`:** the phone re-reads its data.
- **Phone data:**
  - `BP_BeatDirector.GetPhoneTasks()` returns Labels (Text array) and Ticked (bool array). The tasks are Wake up, Get dressed, Leave the house, Find a job.
  - `GI_FoA.DayCount`: crossed-out days are DayCount - 1, so 17 on the first morning.
  - `GI_FoA.GetNotebook()` returns Lines (Text array): one line per known fact, in the order they were learned.
- **Knowledge:** `GI_FoA.HasKnowledge(Flag: Name) -> Known: bool`. The flags are the Names Knows.KeyInBoot, Knows.KeySnaps, Knows.ScrewdriverInDesk, Knows.WardrobeFalls, Knows.DoorMoves and Knows.ShirtPattern. Only the director sets them; other lanes read them.
- **Dream staging is owned by mech_flow** (inside BP_BeatDirector or a helper it owns): moving the door to another wall at T7, lighting the moved door from under when Knows.DoorMoves is set, refilling the drawer, and putting both back on a new day through the ResetForNewDay sweep.
- **Top-down camera:** a CameraComponent on BP_BeatDirector with SetViewTargetWithBlend.
- **Wardrobe fall:** the real `Interact("Notify", "HandleOff")` row reports `WardrobeFalling`; movement and interaction lock for a 7.2 s scene through the existing director camera. The wardrobe pivot rattles for 2 s before its normal 1.15 s fall; `WardrobeLanded` still advances T6. At impact the player temporarily uses masked sand base materials, loses grain coverage gradually, vanishes only at zero coverage, then reforms beyond the actual fallen bounds through checked capsule placement. Original material slots and groom visibility restore exactly, followed by a sand-shell fade to idle 0.06. Three pooled body bursts repeat during scatter/reform. The oblique camera, HUD visibility and DreamDirector echo are cached and restored; the local key light is enabled only for the scene. T7 moves the same functional door/frame west. `OldDoorWall` reuses the adjacent plaster wall mesh/material and fills the actual original opening with collision; it hides on reset. Director blockers protect the fallen footprint. Reset, failure and early battle start restore the player, camera and light, clear staging/fall timers and stop pending pivot movement before normal day reset.

- **Nightmare staging (mech_flow calls the player lane's API):** BP_Nightmare.Appear at arrow markers on BP_BeatDirector: NightmareT1 (the corner by the wardrobe, until first steps), NightmareT7 (the empty doorway, while top-down) and NightmareT8 (the bay alcove, watching the fight). It rides the night mare at rollover (attached to NightmareRide) and calls Vanish at T2, at top-down exit, at T9 and on a new day. T9 calls BP_FoAPlayer.Equip("Suit"); a new day calls UnequipAll(); SetTopDownView(true/false) is called around the director's top-down camera.
- **Per beat, the director also calls** `BP_DreamDirector.SetHueDrift(BeatIndex x 0.06)` after SetTier, so the hue drift grows over the story (0 at T0, 0.6 at T10).
- **BP_BeatDirector instance references:** DoorFrame (DoorFrame_Bedroom) and Door (Door_Bedroom) move at T7: the frame goes to MovedDoorSpot and the door keeps its offset. At T10 the Door gets Interact("Notify", "Open"). RefillActor (Screwdriver_DeskDrawer) gets ResetForNewDay at T7. The Ceiling is hidden while the view is top-down. ShirtActor (Shirt_T7, a hidden mech_core BP_Pickup) gets Interact("Notify", "Open") during the T7 top-down, and taking it reports ShirtTaken.
- **Director-reported events:**
  - FirstSteps: T1, when the pawn walks faster than 30 cm/s.
  - PayoffEnded: T9, 2.7 s after the suit, unconditional. SuitUp cuts (no blend) to the hero shot: the level's CineCameraActor tagged PayoffCam (L_Tutorial_Bedroom, folder Story, focus off, 21 mm), moved each time to the pawn's low three-quarter left front (pawn space (155.6, -109, -37), aimed at (0, 0, 23)). PlayerCinematic(true) runs after the cut, so the face, hair and brows show. Move and look are ignored while it holds 2.5 s and the suit lands. Then a 0.2 s dip to black, a cut back to the pawn, PlayerCinematic(false), input back, PayoffDone and BP_FoAPlayer.HandoffFadeUp. Meanwhile BP_DreamDirector.SetLetterbox(On, 0.8 s / 1.0 s) and SetColorReveal(1 then 0, 1.5 s / 2.0 s) run if they resolve. With no PayoffCam in the level, the payoff stays in first person.
  - T7 hanger: the fall takes Hanger_CoatRail off the rail. StageWrongWall calls DropCoatRailHanger: if the hanger is still Available, it falls and slides to the floor at (135, 165) (0.55 s, S_Props_HangerRail as it lands), within reach of where the fall hands the player back. On the screwdriver route that is where he first needs it, for the bed's ClothingSnag. ResetHouse puts it back on the rail. The door route never consumes it (DT_Items Hanger UsedBecomes None). Once he is back in first person (0.6 s after the fade-up) and only if it still lies there, once per drop, his view glances down at it: 0.6 s ease onto the hanger's visible top (pitch clamped to the camera manager's limits), 0.8 s hold while he says "The hanger's on the floor now. Of course it is.", 0.6 s ease back to where he was looking. Move and look input are held for those 2 s only (ResetHouse releases a glance in progress). BP_BeatDirector Start/Tick/EndHangerGlance (patch_hanger_glance.py).
  - Story cutaways (chase and clue shots, the T9 hero shot) hide BP_FoAFrontEnd.HUD through BP_BeatDirector.SetStoryHUDHidden and restore exactly its previous visibility. They return under a 0.2 s dip to black and the player's fade-up. Every story cut calls PlayerCameraManager.SetGameCameraCutThisFrame on the frame the view changes.
  - Top-down exit: ExitTopDown fades to black over 0.2 s and sets bTopDownCutPending; ExitTopDownCut (on a 0.2 s timer) cuts back under black once. Callers that move on at once (StartShirtFight, ResetHouse) call ExitTopDownCut themselves, so the late timer never pulls the view off the battle camera.
  - WalkedOut: T10, when the pawn steps into the open doorway, measured in DoorFrame's frame (local X > -60, |Y| < 55). After T7 the frame stands against the solid west wall.
- **Level end:** after T10 the director fades to black (1 s), collapses the HUD, and shows the end card `UI/Intro/WBP_EndCard` ("Day one.") for 3 s. It then calls BP_FoAFrontEnd.EndOfLevel() if that resolves; otherwise it calls ResetToTitle() and fades back in.

## Wake-up cinematic (owner: cine)
- **Assets:** `Cinematics/LS_WakeUp` (v3: 36.4 s, 30 fps, 8 shots; the shot list is `docs/cinematics/wakeup_shotlist.md`)
  and `Cinematics/WakeUp/AS_FoA_Wake_EdgeReach` (UAL Sitting_Idle, PickUp_Table and Sitting_Exit composited with IK hands and
  feet; a 5 s seated hold). Builders: `Tools/Unreal/cine/build_ls_wakeup.py` (the sequence) and
  `Tools/Unreal/wakeup/build_anims.py` (the composite and placement.json). `BP_WakeUpCinematic` is retired once mech_flow
  plays LS_WakeUp directly.
- **Flow:** UI hard-cuts to black and holds it, then `BP_FoAFrontEnd.FinishWake` calls `BP_BeatDirector.BeginMorning()`.
- **Who plays it:** BP_BeatDirector.PlayWakeUp, since 02:15. BP_WakeUpCinematic has no referencers and is retired.
- **Skip:** hold Space or gamepad A for 0.8 s to call `BP_BeatDirector.SkipWakeUp()`. The keys don't consume input. WBP_SkipHint is on screen only while the key is held. `ke * SkipWakeUp` skips in tests. The post-wake hold and fade-up (normal end and skip) belong to BP_FoAPlayer; SkipWakeUp has no fade of its own.
- **Safe handoff:** normal completion and skip share `WakeUpDone -> SafeWakeExit`. `WakeBed` references `Bedding_Lux3D` (or `Bed` if bedding is absent). A capsule still inside the bed's front footprint is placed 12 cm beyond its bounds plus capsule radius, at half-height + 2.15 cm. Checked teleport preserves facing and falls back to `WakeUpStart` if obstructed. Furniture stays in place.
  mech_flow's PlayWakeUp does the following:
  - Before Play: DisableMovement, collision off, `SetCinematic(true)`, and SetViewTargetWithBlend(pawn, 0).
  - CreateLevelSequencePlayer(LS_WakeUp), with movement and look input disabled and the HUD hidden, then
    `SetBindingByTag("Player", pawn)`, then Play. Set `MPC_FoAPlayer.BedSettleStart` = now + 19.7 (Now on skip).
  - OnFinished: walking, collision and input back on, SetControlRotation(-10, 55), `SetCinematic(false)`, then
    StartMorningBeats.
- **Inside the sequence (nothing to call):**
  - The fade opens at 1.0 and ends at 0 with Keep State.
  - The camera cuts end with a 1.5 s blend into the pawn's camera.
  - SandClock_WakeUp (possessed) has `DissolveAmount` keyed 0 to 1 from 25.4 s to 26.6 s, with Keep State.
  - `MPC_Dream.ShiftStreak` z is keyed 0 to 2.5 to 0 from 19.25 s to 20.3 s.
  - The sounds sit on an audio track.
- **Beats:** black and the ticking clock with the alarm (0 to 3 s); the POV eyes open and turn to the clock (3 to 9.2 s);
  the wide room (9.2 s); the slow push-in on his face (13.2 s); the time shift (19.7 s); the bed-edge two-shot (19.7 s);
  the insert where the clock crumbles in his hand (24.2 s, grab at 25.4 s); the stand (28.4 s); the hand-back (33.4 s),
  blending to gameplay from 34.9 s to 36.4 s.
- **Binding tags in LS_WakeUp:** `Player` only.
- **Leaves the pawn:** standing beside the bed, walking movement, collision and input restored, its own camera as view target.

## Interaction (owner: mech_core)
- **`Gameplay/BPI_Interactable`:**
  - `GetPrompt() -> Text`
  - `CanInteract(Verb: Name, HeldItem: Name) -> bool`
  - `Interact(Verb: Name, HeldItem: Name)`
  - `ResetForNewDay()`, with no inputs
- **Components:** `Gameplay/BPC_Interactor` and `Gameplay/BPC_Inventory`. BPC_Inventory has the dispatcher `OnInventoryChanged`.
- **The carried set (2026-11-10, the user: no inventory system):** BPC_Inventory is hidden. Add has no capacity, an item already carried is a no-op that returns true, and IsFull is always false. Interactions use the row's Item whenever he carries it (BP_Interactable.FindCarriedRow ahead of the bare-hand row; of the carried rows, the first that changes the state wins). The held/Selected item no longer matters. Tools leave once their job is done (BP_BeatDirector.ToolsDone, first in ReportEvent): KeySnapped removes KeyStub and Key, LatchFreed the Screwdriver, ClothingUnhooked the Hanger. Combine stays as dead code for Level 2. Source: Tools/Unreal/flow/patch_inventory_set.py.
- **`BPC_Interactor.SetSuspended(bSuspended: bool)`:** true pauses the focus scan and clears the focus, the highlight and the prompt; false resumes. BP_FoAPlayer.SetCinematic calls it, so nothing in a cinematic is highlighted.
- **No Blueprint class references from BPC_Interactor or BPC_Inventory to the pawn or the director.** Montages go through BPI_InteractionHost, and beat events go out through the dispatcher `BPC_Interactor.OnBeatEvent(Event)`, which the director binds and forwards to ReportEvent.
- **Actors and data:** `Gameplay/BP_Interactable`, `BP_Pickup`, `BP_Container`, `BP_Door`, `BP_Topple`, `Gameplay/DT_Items`.
- **Focus highlight:** custom stencil value 3 on the focused mesh. The post-process lane renders it as a soft rim.
- **Feedback per instance (gameplay wires it; `Tools/Unreal/gameplay/wire_sounds.py`):** each placed interactable has `StateSounds` (State -> sound) and `BurstStates` (State -> BPL_SandFX.SpawnSandBurst scale). PlayFeedback plays them on a played state change. The sounds are the audio lane's MetaSounds. Room ambience is three AmbientSound actors in outliner folder Audio: Amb_RoomTone, Amb_NightWind and Amb_ClockTick.
- **Wiring audit and in-play proof:** `docs/mechanics/wiring_audit.md`. The playthrough driver is `Tools/Unreal/gameplay/pie_play.py` (plans A-D), run with `bash Tools/Unreal/gameplay/play_burst.sh <plan>`.
- Interactables call `BP_BeatDirector.ReportEvent` with the event names above.

## Encounter (owner: mech_encounter)
- **Assets:** `Gameplay/Encounter/BP_Encounter` (one placed in the bedroom, label Encounter_T8, outliner folder Gameplay, at (-200, -55, 0) yaw 180; `Tools/Unreal/encounter/restore_encounter.py` puts it back if it's deleted), `BP_Garment` (one per enemy, spawned), `WBP_Encounter`, and the data: `PDA_Move` / `PDA_Opponent` classes with `Data/DA_Move_<Id>` and `Data/DA_Opponent_<Id>` (Shirt, Sock, Trousers, Tie). No structs can be authored by script, so these replace DT_Moves / DT_Opponents.
- **`BP_Encounter.StartEncounter(OpponentId: Name)`:** the director calls this after ShirtTaken, with "Shirt" (the leader; its row lists the party). F8 starts it in dev.
- **Outcomes:** win calls `BP_BeatDirector.ReportEvent("EncounterWon")`; lose calls `BP_BeatDirector.FailDay()`.
- **Battle intro (story lane, 2026-11-10):** StartShirtFight -> ShowNightmare(NightmareT8) -> PlayBattleIntro (LS_BattleIntro, 15.9 s, or LS_BattleIntro_Short, 4 s, once GI_FoA knows Knows.BattleIntro). BattleIntroDone (end or the hold-to-skip through SkipWakeUp) starts the encounter under the sequence's held black, sets the camera-cut flag and calls BP_FoAPlayer.HandoffFadeUp. Lines through BP_FoAFrontEnd.ShowCinematicSubtitle. Source: Tools/Unreal/flow/build_battle_intro.py, patch_battle_intro.py.
- **No Flee:** the battle never offers a way out (Btn_Flee stays hidden and disabled). Giving up is the Defeat path: Composure at 0 calls FailDay, "Another morning." `BP_Encounter.Flee()` survives only as a test fixture for the loss path.
- **Reads:** `GI_FoA.HasKnowledge(Leader.KnowledgeFlag)` ("Knows.ShirtPattern"); `BP_FoAPlayer.Equip(GarmentId)` as each garment is won (Shirt, Socks, Trousers, Tie); `BP_DreamDirector.StartStyleCycle / PulseStyle / StopStyleCycle / SetStyleMode`. Each is skipped when absent.
- **Battle state:** `BattleState` (Name): Intro, PlayerCommand, ResolvePlayerAction, EnemyPhase, CheckEnd, Victory, Defeat. A garment's `State` (Name): Idle, Telegraph, Attack, Stunned, Defeated.
- **For the UI (WBP_Encounter) and VFX, dispatchers on BP_Encounter:** `OnChanged()` (re-read everything), `OnStateChanged(State: Name)`, `OnDamage(Who: Actor, Amount: int)` (a garment for progress, the pawn for harm), `OnGarmentEquipped(Garment: Actor)`, `OnSandBurst()` (a garment rose or was won; the sand lane can use `SandBurst` or the garment's location), `OnEncounterWon()`, `OnEncounterLost()`.
- **Player commands (public on BP_Encounter):** `ChooseMove(Move)` (Act moves come from `TargetGarment().Data.ActMoves`; Breathe and Mirror are `BreatheMove` and `MirrorMove`), `Items()`, `CycleTarget(Direction: int)`, `HandleKey(Key)`. HandleKey: during a wind-up it goes to `Brace(Key)`; during a key prompt to SubmitKey; on the player's turn Q moves the target back, E and Tab forward (battle lane, 2026-11-17).
- **Low preset (battle lane, 2026-11-18):** while the encounter is active and `sg.ShadingQuality == 0`, `ApplyLowDepth()` turns custom depth off on stencil-5 sand and marks it with stencil 205. It is applied at StartEncounter, rechecked by a 1 s timer and undone at EndEncounter. Anything that needs stencil 5 in a Low fight must not rely on custom depth.
- **Clarity pass (battle lane, 2026-11-17; Tools/Unreal/encounter/clarity_encounter.py, clarity_widget.py):** every enemy act that does something gets a wind-up first (`WindUp(Garment)`: the garment's Telegraph clip and wind-up sound, `bWindUp`, `WindUpStart`, `WindUpTime` 1.0 s); acts that do nothing (`IsIdleMove`) are skipped. Space or gamepad A in the last 30% (`BraceFrom` 0.7) sets `bBraced`: `IncomingDelta(Move)` halves that Composure hit and ApplySelf skips its status; one press per attack (`bBraceSpent`). `ImpactAt` is the hit's game time. The prompt timer now calls `KeyTimeout` (a miss sound, then AdvancePrompt). The dispatchers and outcome hand-offs are unchanged. WBP_Encounter shows each garment's buttons as pips above it, a parry ring on the hero during a wind-up, one key glyph at a time, and narration only outside the choice and the attacks; the top-right panel, help lines and controls footer are gone. Readable state: `Composure`, `Resolve`, `Statuses` (labels in `StatusLabels`), `Garments`, `Target`, `Narration`, `bPlayerTurn`, `bAwaitingKey`, `InputKeys`, `InputIndex`, `InputHits`, `KeyTimer`, `ActiveWindow`, `bRevealed`. Per garment: `BP_Garment.StatusLine(bRevealed) -> Text`, `Progress`, `Data.Resistance`.

## Dream visuals (owner: pp, the post-process lane)
- **`PostProcess/BP_DreamDirector`:** presentation only. Callers find it with GetActorOfClass and skip quietly if it's absent.
  - `TriggerGlitchBurst(Strength: float 0..1, Seconds: float)`
  - `SetTier(Tier: int 0 Plausible, 1 Suspicious, 2 Open)`
  - `SetMenuMode(Enabled: bool)`
  - `SetHueDrift(Amount: float 0..1)`
  - `SetEchoStrength(Amount: float 0..1)`
  - T8 battle styles: `SetStyleMode(Mode: int 0 Real, 1 Pixel, 2 Dither, 3 CRT; BlendSeconds: float)`, `PulseStyle(Mode: int, Seconds: float)`, `StartStyleCycle(Interval: float)`, `StopStyleCycle()`. Call SetStyleMode or PulseStyle on each turn, big hit and telegraph. ReduceMotion holds the dither style, with no flicker.
  - Shift streak (highlight-only "shutter timing" smear) and letterbox: `SetShiftStreak(Length: float, Angle: float deg 0 vertical, Intensity: float 0..5)`, `PulseShiftStreak(Intensity: float, Seconds: float)` for transitions, and `SetLetterbox(Enabled: bool, Seconds: float)`, which slides 2.39:1 bars with a streak pulse. Use the letterbox for cinematic beats only (T9, L7), never during gameplay.
  - T9 payoff: `SetColorReveal(Amount: float 0..1, BlendSeconds: float)` eases the whole frame toward real colour (MPC `ColorReveal`) and back with Amount 0. For example SetLetterbox(true, 0.8), SetColorReveal(1, 1.5), about 3 s later SetColorReveal(0, 2) and SetLetterbox(false, 1).
  - Ambient sand: the director calls sandvfx's `BPL_SandFX.SpawnAmbientBloom(Tier)` on its own timer (8 to 14 s at tier 0, shorter at higher tiers), using the tier from SetTier. It's skipped until that library exists.
- **Custom stencil table** (one value per primitive; the pp lane renders them): 1 keeps real colour (payoff), 2 is the Nightmare tear mask, 3 is the focus rim (mech_core), 4 is the protagonist face blur, 5 is sand (sandvfx sets it on every sand actor and splat mesh; it gets the sand-only echo, datamosh and banding, driven by MPC `SandFXAmount`). Every value other than 1 stays monochrome.
- **`MPC_Dream` scalars:** ColorReveal, GlitchAmount, ReduceMotion, HueDrift and the rest, as the pp lane documents. Settings UIs write `ReduceMotion` (0 or 1) directly. Vector `PlayerPos` (xyz = the player's feet in world cm, W = influence radius; default (0, 0, -10000, 0)) is written by BP_FoAPlayer for the sand.

## Player (owner: player, the animation lane)
- **Assets:** `Characters/Player/BP_FoAPlayer`, `Characters/Player/ABP_FoAPlayer`, and the game mode `Gameplay/GM_FoA` (default pawn BP_FoAPlayer).
- **Montages:** `Characters/Player/Montages/AM_FoA_*`. Reference them by soft reference. All use slot DefaultSlot; gameplay notifies are AnimNotify_PlayMontageNotify (names in brackets):
  AM_FoA_PickUp_Floor (Grab), AM_FoA_PickUp_Table (Grab), AM_FoA_OpenDrawer (Grip, Pull), AM_FoA_TryLockedHandle (Rattle, Locked),
  AM_FoA_KneelScrewdriver (KneelDown, WorkDone), AM_FoA_Startle (Startle), AM_FoA_WakeUp (WakeStir, SitUp, Standing), AM_FoA_Equip (Snap).
- **`BP_FoAPlayer.PlayInteraction(Montage: AnimMontage)`:** plays it and holds move input until it ends (for the player lane's own use).
- **`Gameplay/BPI_InteractionHost.LockForInteraction(Seconds: float, Target: Actor)`:** implemented by BP_FoAPlayer. It holds move input for Seconds and turns onto Target. BPC_Interactor plays the montage on its owner as an engine Character and then sends this message, so it never references BP_FoAPlayer, which owns it through BP_ThirdPersonCharacter. That reference was a load cycle that raised the ensure "Custom Property List Not Initialized" on every map load.
- **`BP_FoAPlayer.Equip(GarmentId: Name)`:** GarmentId is Shirt, Trousers, Socks, Tie or Suit. Shows that garment layer (a Leader Pose
  skeletal mesh component of the same name on the Manny skeleton) with the equip beat and a black-sand burst. The garment meshes come from
  the character lane; an empty slot just plays the beat. **`BP_FoAPlayer.UnequipAll()`:** back to the bare mannequin (new day).
- **`BP_FoAPlayer.SetTopDownView(bEnable: bool)`:** call it alongside the director's SetViewTargetWithBlend; it freezes look input and
  makes movement screen-relative.
- **Look-at:** the player's head turns toward the nearest actor tagged `Interactable` in reach (BPC_Interactor.GetFocusedActor() later).
- **`BP_FoAPlayer.SetCinematic(bEnable: bool)`:** for sequences that drive the mesh (LS_WakeUp): pauses the look-at scan, eases
  the head weight to 0 and turns foot IK off; false restores them.
- **`BP_FoAPlayer.SetHeldTool(Mesh: StaticMesh, MeshTransform: Transform, bShow: bool)`:** puts a tool in the right palm. HeldTool rides HeldToolGrip on Body at hand_r (`ToolGripOffset`, the grip frame in hand_r space, retuned per body rig); MeshTransform normalises the mesh tip-first along +X and the tip sits 16 cm out along the grip axis. bShow also closes the right fingers (ABP_FoAPlayer `GripWeight`, pose AS_FoA_Grip_Tool_R). While a tool is held, `SetToolHandRotation` places the hand from the tool frame (axis = the pawn forward, grip point = the last SetToolHandTarget) and ratchets the wrist: each 90 deg of turn twists -45 to +45 with the tool, then regrips while the tool stays still. **BP_Door (anim lane edit, 2026-11-07, approved by main):** BeginDoorTool calls SetHeldTool(ToolDriverMesh, ToolDriverTransform, Mode != Key) and shows its own ToolMesh only for the key; RestoreDoorTool calls SetHeldTool(bShow false).
- **`BP_FoAPlayer.SetBattle(bEnable: bool)`:** animation state for the encounter's battle idle. BP_Encounter enables it in
  ShowEncounter and clears it in EndEncounter. The encounter retains ownership of movement and camera locks.
- **Bed dent:** `MPC_FoAPlayer.BedSettleStart` (seconds, game time) starts the duvet relax in `M_FoA_BeddingSettle` on
  Bedding_Lux3D. The wake-up lane sets it when he lifts off (Now on skip); mech_flow's ReturnToBed / ResetForNewDay sets it back
  to 1e7 (dent held).
- **Sand crawl (agreed with sandvfx):** BP_FoAPlayer writes `MPC_Dream.PlayerPos` (Vector: xyz = feet world position, W = influence
  radius in cm, default 60) at 30 Hz; the sand material reads it. **`BP_FoAPlayer.SetSandOverlay(Amount: float)`** puts sandvfx's
  `VFX/Sand/M_SandOverlay` on Body, StartOutfit and visible garment slots. `Amount` 0 clears, 0.06 is the ordinary
  subtle sand level, and 1 forces full sand during transitions. Face receives the overlay only above 0.85; ordinary
  play preserves the real face and hair silhouette. The material has no vertex displacement.
- **`BP_FoAPlayer.SetSandTransition(Amount: float, Enable: bool)`:** true masked silhouette coverage for story transitions. On first enable, cache the original material at every slot of Body, Face, StartOutfit, Shirt, Trousers, Socks, Tie, Suit and BootsWornMesh, use a dedicated sand MID with `Transition=1`, and clear overlays. Amount 1 is a full sand silhouette; 0 is invisible. Groom materials cannot use this skeletal mask: real hair/brows persist until coverage falls below 0.25, reveal above 0.7 during reform, and restore their exact initial visibility on disable. Disable restores all original slots, clears caches and returns the overlay to 0.06. No Tick, assets or persistent camera actors are added.
- **`BP_FoAPlayer.RefreshStarterCoverage()`:** after Equip changes garment visibility, hide the starter outfit's LOD0 material0 for a visible real Shirt and material1 for visible real Trousers. UnequipAll refreshes coverage after its suit/boots cleanup. Footwear materials2/3 remain owned by SetBootsWorn; clothing coverage never hides the body mesh.
- **`Characters/Player/BP_Nightmare`** (the NPC shadow figure, SK_Hero when it lands, Manny placeholder until then):
  `Appear(Location: Vector, Yaw: float)`, `Vanish()`, `StalkTo(Target: Actor)`. Heavier and slower than the player; watches the player;
  appears and vanishes through black sand; tear glitch through custom stencil 2 (the pp lane's TearAmount). It never fights.

## VFX (owner: sandvfx)
- **Splat meshes:** `VFX/Splats/Meshes/SM_*`, using `VFX/Splats/M_SplatMesh` and its MIs.
- **Night-mare rollover:** `VFX/Splats/Meshes/SM_TheNightMare` with `MI_Splat_NightMare` (the sandvfx lane imports it). Reference it by soft path and skip it if it's missing.

## UI (owner: ui)
- **Widgets:** WBP_HUD (prompt, toast, objective, subtitles), WBP_Phone and WBP_MainMenu.
- **Bindings:** the HUD binds BP_BeatDirector.OnBeatChanged and BPC_Inventory.OnInventoryChanged.

## In-game UI (owner: ui)
All UI is event-driven (no Tick). Assets are under `UI/`.
- **Flow manager:** `UI/Framework/BP_FoAFrontEnd`, one per level (placed in L_Tutorial_Bedroom, folder UI). Find it with `GetActorOfClass(BP_FoAFrontEnd)`.
  - It owns the menu camera (`BP_MenuCamera` with `LS_MainMenu_Camera`), screens, input mode and pause.
  - **Public functions:** `WakeUp()`, `TogglePause()`, `Resume()`, `OpenSettings()`, `OpenCredits()`, `CloseOverlay()`, `RequestQuit()`, `RequestRestartDay()`, `RequestQuitToTitle()`.
  - **Variables:** `bInGameplay` (bool) and `HUD` (the live WBP_HUD).
  - `WakeUp()` freezes the menu while SFX_FE_WakeUpPress plays (3.07 s), then hard-cuts to black and holds black for WakeBlackSeconds (1.5 s) with the heartbeat. On the first start ever, the story (below) then plays. Otherwise, and after the story, `FinishWake` hands over to gameplay with the HUD at 0 and calls `BP_BeatDirector.BeginMorning()`. LS_WakeUp owns the camera and the fade back in.
  - Menus call `BP_DreamDirector.SetMenuMode(true/false)`. While the title or main menu is up (until Wake up), the front end calls `TriggerGlitchBurst(0.75 to 1, 0.5 to 1.2 s)` every 4.5 to 9.5 s (datamosh events). In menu mode each burst also runs the v3.1 block drag: in about half the 48 px bands, 26x16 px blocks drag the frame up and sideways for the burst, ramping in over 0.12 s and dropping out block by block over 0.25 s (MPC `MoshStart` and `MoshSeed`, written only by BP_DreamDirector; off in gameplay; MF_Dream_GlitchUV owns it, M_PP_MenuV31 has none).
- **Story hook (look-dev lane):** set `BP_FoAFrontEnd.StoryClass` to the story widget.
  - It is created over black, once ever: SG_FoASettings.bSeenIntro is then saved.
  - When its last panel ends or the player skips, it calls `BP_FoAFrontEnd.OnStoryFinished()`. That removes it and wakes the player.
- **UI sound hooks (audio lane):** every front-end cue goes through `BP_FoAFrontEnd.PlayUISound(Cue: SoundBase)`. It plays 2D, as a UI sound, so it is audible while paused, and None is silent.
  - The looping beds use `StartBed(Loop)` and `StopBed()`. Only one runs at a time, and stopping fades it out over 1.5 s.
  - The cue slots are class defaults under Front End|Sound, filled from /Game/FoA/Audio/SFX/UI_FrontEnd when the assets exist:

    | Slot | Cue | When |
    |---|---|---|
    | SndBootSwell | SFX_FE_BootSwell | The boot black starts |
    | SndSplashThump | SFX_FE_SplashThump | Each splash fade-up |
    | SndSandForm, SndSandScatter | SFX_FE_SandForm, SFX_FE_SandScatter | The Hayba mark forms or dissolves |
    | SndTitleReveal | SFX_FE_TitleReveal | The title fades up |
    | SndTitleBed | SFX_FE_TitleBed | Bed from title to Wake up |
    | SndGlitchStinger | SFX_FE_GlitchStinger | On the same frame as each datamosh burst |
    | SndWakeUpPress | SFX_FE_WakeUpPress | Wake up. The hard cut to black lands 3.07 s later, when it ends |
    | SndHeartbeatBlack | SFX_FE_HeartbeatBlack | The black after the cut (WakeBlackSeconds, 1.5) |
    | SndStoryBed | SFX_FE_StoryBed | Bed from story start to OnStoryFinished |
    | SndPanelTransition | SFX_FE_PanelTransition | The story widget calls PlayUISound(SndPanelTransition) per panel |
    | SndEyelids | SFX_FE_Eyelids | The wake-up lane calls PlayUISound(SndEyelids) on each eyelid open or blink |
    | SndPauseIn, SndPauseOut | SFX_FE_PauseIn, SFX_FE_PauseOut | Pause opens or closes |
    | SndConfirm | SFX_FE_Confirm | A confirmed action |
    | SndBack | SFX_FE_Back | Back closes an overlay |

  - Splash: WBP_BootSplash calls `OnSplashCue(Index)` at each fade. Even indexes are a card fading up; odd ones are a fade-out, which is silent except 5, the Hayba scatter.
  - Menu hover and select are WBP_SandButton's HoverSound (SFX_FE_Hover) and ClickSound (SFX_FE_Select). The Wake up and dialog Confirm buttons have no ClickSound, and the dialog's cancel button uses SFX_FE_Back.
- **HUD:** `UI/Game/WBP_HUD` exposes these functions for other lanes:
  - `ShowSubtitle(Speaker: Text, Line: Text, Seconds: float)`. Speaker may be empty.
  - `ShowToast(ItemId: Name)`. The name, icon and Look line come from DT_Items.
  - `SetObjective(Text)`. This is normally driven by OnBeatChanged.
- **Needed from mech_core:** `BPC_Interactor.OnFocusChanged(Target: Actor, Prompt: Text, Verbs: Name array, VerbIndex: int)`.
  - The HUD shows the prompt as a full sentence with a keycap or gamepad glyph, plus the verb-cycle hint.
  - An empty Prompt hides it.
- **Phone:** `UI/Game/WBP_Phone` opens when OnBeatChanged has ShowPhone true and refreshes on OnPhoneChanged.
  - It reads `BP_BeatDirector.GetPhoneTasks()`, `GI_FoA.DayCount` and `GI_FoA.GetNotebook()`.
  - Its Wake up task calls `BP_BeatDirector.ReportEvent("PhoneWakeUp")`.
- **Day rollover (P13; the director side is owned by gameplay):** `UI/Game/WBP_DayRollover` plays the sand wipe, crosses out a day and shows the next day number.
  - **`BP_FoAFrontEnd.PlayDayRollover(NewDay: int, Learned: Text)`:** `BP_BeatDirector.FailDay()` calls it after the glitch and the night mare (RolloverSeconds).
    - NewDay is the day about to start (GI_FoA.DayCount + 1).
    - Learned is the notebook line this failure just taught (GI_FoA NotebookLines of the beat's flag). It is empty when nothing new was learned. Show it on the card only when it isn't empty.
  - **Dispatcher `BP_FoAFrontEnd.OnRolloverCovered()`:** broadcast once, when the wipe has fully buried the screen in opaque black.
    - The director binds it and runs StartNextMorning under the black: the day is saved, the house resets, the pawn goes back to bed, and BeginMorning plays LS_WakeUp, whose Fade track holds black from 0 to 3 s.
  - **The cut:** after the broadcast, the card stays up for at most 2.5 s, then removes itself with a hard cut and no fade-out of its own. The cut lands inside LS_WakeUp's 3 s black, so the reset and the cut are never seen. Sound may tail out.
  - The widget leaves input mode and pause alone. The director has already frozen input (FreezeForRollover), and the wake-up restores it.
  - Until PlayDayRollover resolves, FailDay falls back to FadeToNextMorning, a camera fade to black. RestartDay always uses the plain fade.
- **Settings:**
  - `UI/Framework/BPFL_FoASettings` provides `LoadSettings()`, `SaveSettings(Settings)`, `ApplySettings(Settings)` and `LoadAndApplySettings()`.
  - The save slot "Settings" is `UI/Framework/SG_FoASettings`, with MasterVolume, EffectsVolume, AmbienceVolume, InterfaceVolume, MouseSensitivity, bInvertY, bSubtitles, SubtitleSize (0 to 2), bReduceMotion, bShowPhotoWarning and bSeenIntro (progress: the story has played).
  - The player lane reads MouseSensitivity and bInvertY through `LoadSettings()`.
  - Graphics stay in the engine's GameUserSettings.
- **Accessibility:** Reduce motion writes `ReduceMotion` to both `UI/Style/MPC_UI` and `PostProcess/MPC_Dream`.
- **Style:**
  - Typography comes from the rows of `UI/Fonts/F_FoA_Typography`. The typeface is Darker Grotesque (OFL): F_FoA_Display is 800, and F_FoA_UI is 600 for menus and prompts and 500 for small UI.
  - The palette is `MPC_UI` (Ink, Soot, Panel).
  - Buttons are `UI/Widgets/Common/WBP_SandButton`, which has the `OnSandClicked` dispatcher.

## Lane addresses (SendMessage `to`)

| Lane | Address |
|---|---|
| mech_flow | a66c4e70b4a07103f |
| mech_core | acb4a93b6c97990e1 |
| mech_encounter | a6d6f804455718fcd |
| pp | a0d31ec6ef904abac |
| sandvfx | a35b0d3e500c83ea5 |
| ui | a10980ff89c3e2898 |
| player (animation) | a97c83975af41524a |
| character | a6b297254e3cd3aca |
| props | ac869fd2465295a49 |
| wear | a9fdae2f2fa58bd03 |
| surfaces | a7b095779476d1dd6 |
| shafts | ad9f43644204e5a51 |
| audio | ad6994316902257d7 |
| trims | a2dad5c9ef79431b3 |
| fireplace | adea8064d76b10378 |
| review | a27025be0f534b723 |
| devlog | a43cd3537b99fe096 |
| cleanup | af51223146fb1d027 |
| layout (graph auto-layout) | a4cd39cfce08cb00b |
| lookdev | a20359f0279738f44 |
| hayba fixes (offline only) | ad99df9853e2155e2 |

Keep messages short and concrete: names and signatures, not essays.

## Custom stencil values (project-wide)

| Value | Meaning | Owner |
|---|---|---|
| 1 | Keeps colour through the monochrome grade (payoffs) | pp |
| 2 | The Nightmare's tear glitch | player/pp |
| 3 | Focus highlight rim on interactables | mech_core/pp |
| 4 | Protagonist face blur ("eaten away") | character/pp |
| 5 | Sand: intense echo, datamosh and glitch (MF_Dream_SandFX) | sandvfx/pp |
