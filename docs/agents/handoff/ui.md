# ui lane handoff (2026-11-09, AAA pass)

## Battle UI B (torn cards), handoff 2026-11-10 (main approved B; to be built by the Codex lane)

**5.9 resume 2026-11-11 14:34:** native sanity passes, old timed-out import was absent. New masks/material instance saved; WBP_Encounter card layout saved at 0 errors / 0 warnings. Motion/intent graphs and proof are still pending. A newer `main:MAINTENANCE hayba 5.9 install` hold (14:28) blocks the next lease. Do not treat the partial UI as complete. Report has tool/API findings and recovery details.

**14:43 checkpoint:** hold still active, no battle-ui lease or background chain. On release, apply the builder's `lookup` step first to adapt RefreshAct to the saved card wrappers, then the remaining presentation functions and hooks. Current saved layout is partial. Offline proof/recorder scripts are prepared but untested; no MP4 or three-turn proof yet.

**Codex battle-ui checkpoint 22:44:** implementation script prepared at `Tools/Unreal/ui/battle_torn_cards.py`, but **not built or proven**. Shared editor stalled at frame 742 after a 03:40:41 UTC handled ensure; first mask import timed out, completion unknown. No WBP edit confirmed. Apply chain has ended and no battle-ui hold remains. Coordinator recovery is required before live validation. Details: `Saved/Codex/battle_ui_report.md`.

The user: "the whole battle UI is a bit boring, make it more interesting" (images/72.png: plain text columns, the right
column clipped). Approved direction: Saved/UIShots/aaa/battle_mock/B_torn_cards.png (+ _guides.png: 5% safe frame at 16:9
in red, the 16:10 crop in blue). Mockup source: Tools/Unreal/ui/battle_mockups.py (PIL, offline, over a real fight frame).

- Spec (main's notes on B): commands are a low fanned hand of sand-edged cards, each a drawn line glyph (sleeve, button,
  breath, mirror, pocket, door) and its name in CLEAN Darker Grotesque (no sand on unfocused names; at most a grain edge on
  the focused one). Focus: the card rises about 52 px, straightens, grows and brightens; costs as pips on the card top (not
  "(10 Resolve)"); the description only for the focused command, in IBM Plex Mono, over the hand. The garment's intent is
  a small card ANCHORED to the targeted garment's screen position (ProjectWorldToScreen of its bounds, following it, clamped
  inside the safe frame). Composure and Resolve as sand columns with visible 0 and max ticks. The target list stays as is.
  Motion: cards assemble from grains at turn start (MF_UI_SandShape / M_UI_SandText exist), the focus lift with a grain
  sheen, confirm sends the card to the garment while the rest crumble. Monochrome, the user's text rules (no middle dots,
  separators, divider lines or eyebrow labels), controller plus mouse, nothing clipped at 16:9 or 16:10.
- Sounds (horror): /Game/FoA/Audio/MetaSounds/Battle/S_Battle_Select (focus moves, keys/pad/hover) and
  /Game/FoA/Audio/MetaSounds/Battle/S_Battle_Confirm (commit), both SC_UI, PlaySound2D bIsUISound true.
- WBP_Encounter (/Game/FoA/Gameplay/Encounter/WBP_Encounter) today: RootCanvas > LogPanel(Txt_Narration), SelfBox
  (Box_Composure/Box_Resolve: Row_*, Icon_*, Txt_*Label, Txt_*, Size_Bar_*/Bar_* ProgressBars), PromptBox (KeyCap,
  Txt_PromptKey, Bar_Window, Pips_Hits PipHit0-2: the timing prompt, keep), Txt_Damage, CommandPanel > BattleCommandHost >
  CommandBox > ActBox (Txt_Target, BattleActRow collapsed, ActCards > ActCard0-2 holding Btn_Act0-2) and CmdButtons
  (UtilityColumns > UtilityLeft/Right: the Btn_* utility commands), EnemyPanel (BattleEnemyHost, Txt_Enemy0-4 /
  Txt_Intent0-4), Txt_BattlePhase, Txt_BattleHelp. Builders that shaped it: Tools/Unreal/encounter/battle_ui_calls.py,
  redesign_battle_choices.py, refine_battle_composition.py, refine_battle_choices_readability.py (read them first).
- Keep: every Btn_* and its OnClicked/OnHovered/focus wiring, the Txt_* names BP_Encounter writes, the timing PromptBox and
  BP_Encounter's logic (story/mech own it; restyle and re-parent, never rebuild widget objects or change the events).
  Costs and descriptions come from the encounter data the buttons already carry; read them, don't duplicate them.
- Proof: a PIE run through 3 turns (pie_fight.py / pie_battle_boot.py in Tools/Unreal/encounter show how to reach the fight)
  plus an MP4, frames at 16:9 and a 16:10 check.
- Gotchas learned this week:
  - Hayba blueprint_add_component adds SCS ROOT nodes: the first component becomes the actor's root, so "relative" sets on
    it are world space (BP_ItemInspect's key sat at the level origin). Give actors a plain SceneComponent root
    (SubobjectDataSubsystem.make_new_scene_root + attach_subobject, item_inspect_fix.py 'root').
  - Hayba blueprint_create makes a plain Blueprint, not a function library: BPFL entries get no __WorldContext. Create
    libraries with BlueprintFunctionLibraryFactory (item_inspect_build.py 'lib').
  - Builders that create nodes then link them must re-link on rerun: a failed run left BP_ItemInspect's axis events
    unwired (drag dead) and the idempotent rerun skipped them. Assert the wiring at the end (item_inspect_axis_fix.py).
  - K2Node_InputKey flags (bExecuteWhenPaused) are not Python-visible: set them with Hayba object_set_property.
  - blueprint_graph_batch is not atomic; a failed op leaves the graph half built and a BP that fails to compile blocks
    every lane's PIE (HCR-PIE-001). Compile and save inside the same lease, or stub and save.
  - In PIE every keyboard key also reaches the editor's PlayWorld chords (the game viewport never reports keys handled):
    Esc stops PIE, Alt+P repeats play. Hayba key injection carries the live OS modifiers.
  - ui_build_tree takes slot_props (not slot) and builds under the existing root; Darker Grotesque has no symbol glyphs
    (draw glyphs as images/lines).

## Item inspect and cinematic subtitles, 2026-11-10

- Item inspect (user ask: "the key appears in 3D on the center of your screen and you can rotate it and close it",
  every item you take). Builder: Tools/Unreal/ui/item_inspect_build.py, steps lib (ue_remote, the function-library
  factory: Hayba's blueprint_create makes a plain Blueprint whose entries get no __WorldContext), assets, graphs,
  graphs2, input (ue_remote), flags (bExecuteWhenPaused is not Python-visible), guards, hook, finish.
  - BP_ItemInspect (actor, spawned on first take): Request(Item) opens once per item per morning (Seen string; a new
    morning = BeatIndex went back), not SkipItems "|Shirt|KeyStub|", after OpenDelay 0.55 s. Open: DT_Items row Mesh,
    DisplayName, LookLine; bounds sphere 40% of the visible height 35 cm in front of the camera, yaw 35 pitch -15,
    pause, WBP_ItemInspect (ZOrder 30), SFX_UI_Open_A. TickStep runs while paused on real time: ease in 0.3 s, out
    0.25 s, inertia e^-6t, turntable (yaw about the screen vertical, then pitch about the screen horizontal, +-70),
    the PP (exposure -0.7, vignette 0.6, DOF 35 cm f/1.4) weighted by the ease, hint by device (bPad).
  - Input on the actor (priority 100, consume, execute when paused): E, Esc, pad B, right click close; LMB drag,
    right stick, arrows and D-pad rotate (a tap = 45 deg); P and Tab are swallowed.
  - BPFL_ItemInspect.RequestInspect(Item) (skips None; find or spawn) is the one node in
    BP_Interactable.CommitInteractionRow (Add -> RequestInspect -> UseUp, main's grant, anim's asset).
    IsItemInspecting guards BP_FoAFrontEnd TogglePause, ToggleDebugPanel and OpenPhone.
  - Proof: sweep_intro.py modes inspecttake (real takes via the interactor) and inspectcine; pie_call TAKE, INVDUMP,
    INSPECT, INSPECTREQ, INSPECTSTATE.
- Cinematic subtitles (story, battle intro): BP_FoAFrontEnd.ShowCinematicSubtitle(Line, Seconds, Speaker) and
  HideCinematicSubtitle(); WBP_CineSubtitle at ZOrder 12, a copy of the HUD subtitle (halo, type, size setting, rise),
  Nightmare at 0.7 text opacity, Seconds <= 0 holds. Builder: Tools/Unreal/ui/cine_subtitle_build.py (widget, graphs,
  fe). pie_call CINESUB, CINEHIDE, HUDHIDE, CAMCUT, CAMBACK.
- Tools/Unreal/ui/hayba_batch.py: the shared typed-node batch kit (B.fn/get/set/chain/run).

## AAA pass, 2026-11-09 (supersedes everything below where they differ)

Built in place with Hayba (no builder reruns; every patch script is in Tools/Unreal/ui/aaa_*.py and is idempotent).
Reference per screen: docs/design/ui/aaa_ui_direction.md Part 5. Proof runs: Saved/UIShots/aaa/.

- Boot (WBP_BootSplash): CardSeconds 2.0 (0.2 black, 0.5 in, 0.9 hold, 0.4 out), ease-out cubic via an Ease node,
  FinishAt 6.0, Elapsed -0.1; any key, click or pad button skips the current card. Logos BC7 (were uncompressed).
  The 27 MB logo figure was from a log before the 512 cap (FoA-backup-2026.11.07-21.13.09.log).
- Sand text (M_UI_SandText): MF_UI_SandShape HLSL is Tools/Unreal/ui/hlsl/sand_shape_v4.hlsl: directional gather
  (left to right, grains from a pcg hash blown in from the left) and scatter (to the right); a 3rd MF output Presence
  gates the echo so ghosts never show before letters exist. MF_UI_TimeEcho (hlsl/time_echo_v4.hlsl) never samples past
  the retainer top (that wrap was the "flipped ghost" over the title) and breathes on 5 s. 170 PS instructions.
  All sand-text instances use neutral Ink 0.9 (the warm paper ink showed after the mono post).
- Title: FormStep ramps Ret_Title Reveal 0 to 1 over 1.5 s (60 Hz self-stopping timer, ease-out ^4) and drives the
  echo only during the gather (Calm.B = 0.55 x (1 - reveal)); clean at rest. IsValid guard: a key during the form
  removes the title and the retainer, the timer now stops (the 262 Accessed None in horror's 13:23 burst).
- Main menu: words form from sand 60 ms apart (SetReveal from MenuFadeStep). No datamosh at rest: TitleGlitch is a
  no-op, and SetDreamMenuMode clears BP_DreamDirector's MenuGlitch timer right after SetMenuMode (world lane's asset is
  untouched; the menu preset itself stays, it carries the menu grade). M_PP_MenuV31 Look.y (downward streak) is 0.
  Txt_Build is near-black. Focus: SandButton PushState steps the word 12 px right (RenderFocusRule=Never is on).
- HUD: Txt_Objective sits in Ret_Objective (MI_UI_SandText_HUD) inside Ovl_Objective; ObjectiveStep forms it over
  0.8 s per beat and quiets it to half after 6 s; subtitles (Brd_Narration) sit on a soft T_UI_SoftDot halo and rise
  6 px over 0.26 s (SubStep). Hint rows use the final text ("P Phone    Ctrl Crouch", "D A Turn    Q Release").
- Pause: M_UI_Scrim gained Tear (hlsl/scrim_tear.hlsl, 71 PS instructions); WBP_Pause Event Tick (world timers stop
  while paused) drives the tear settle (0.3 s), header fade and the words forming 50 ms apart. A fresh open is a
  >2.5 FRAME gap (GetFrameCount, aaa_tick_frames.py), not real time: a hitch re-fired the tear mid-pause in rec_hud_r1
  (f0465, f0475). Settings and Phone Ticks use the same test.
- Settings: Music volume and Dialogue volume rows (aaa_audio_rows.py): SG_FoASettings MusicVolume/DialogueVolume,
  ApplySettings overrides SC_Music/SC_Dialogue on SCM_Settings at runtime (no SCM edit), OnMusicChanged/OnDialogueChanged,
  LoadSavedRows fills both. The OnRowValueChanged binds (FOA_STEP=bind, editor Python) were lost in the 22:10 crash and
  wait for main's go after Hayba restart 8: until then the rows show and load but do not apply when moved.
- Rollover: Txt_New sits in Ret_New (MI_UI_SandText_Title); StepRollover drives its Reveal from the same ramp.
- Phone text is final (script.md section 3); "No notes yet." empty state.
- UI sounds (recorded set in /Game/FoA/Audio/SFX/UI, see aaa_sounds.py docstring for the event map).
- Sweeps: sweep_intro.py modes fast, perffast, fastskip, hud, menufast, inputfast; EXCLUSIVE TTL capped at 60 s; each
  input logs the active sounds; focus_sheet.py makes the per-input focus sheet; make_gif.py cuts GIFs.
- Title contrast (QA b on the full logotype region, x 0.02-0.53): Img_TitleShade, a 1500 x 620 soft black falloff
  (T_UI_SoftDot, alpha 0.95) at (150,100) behind the title on WBP_Title and WBP_MainMenu. rec_fast_r4: title 8.53:1,
  menu 12.27:1 (was 2.07-2.13:1).
- Phone (realistic, unbranded): WBP_Phone has a status bar (rounded-box signal and battery), a lock screen (Ovl_Lock,
  big clock, Day N, Mom and Career Center banners) that slides up ~1 s after the phone appears (Tick with the frame
  gap detector), Reminders-style rows (Img_Check0-3), a Messages thread (Txt_ThreadName over Brd_Bubble; body-only texts
  in OpenMessage), the app tabs as a bottom bar. M_UI_PhoneScreen (Surface, Masked, Unlit; hlsl/phone_glass.hlsl):
  rounded corners, edge falloff, Fresnel sheen with smudges. NOT YET APPLIED to BP_Phone: aaa_phone_hold.py
  (hold/taps/glass) and aaa_phone_mouse.py (FOA_STEP=add) wait for main's go after anim's phone3 proof. The glass step
  fits the Screen widget to the Lux3D SM_Phone glass (DrawSize 540x1118, scale 0.01222, z -0.53, stencil 200 so the
  dream echo skips it). Proof: bash Tools/Unreal/ui/aaa_phone_proof.sh (sweep mode 'phone').
- UI sounds: aaa_sounds.py wired the recorded set (one sound per event). audio_active_sounds reads the editor device,
  not PIE's (fixed in a later Hayba DLL); input sweeps turn on au.Debug.SoundWaves in PIE instead (pie_call CONSOLE).
- Layout: bp_layout.py --apply on every UI Blueprint (aaa_layout_all.sh); graph_layout.py + replay_layout.py for
  materials. Graph captures: capture_aaa_graphs.py -> Saved/GraphShots/aaa_*.png.
- Hayba quirks learned (fixed in the next DLL per the hayba lane): snake_case slot props were silently ignored (use
  VerticalAlignment 'VAlign_X' and Padding {Left,Top,Right,Bottom}); SetText InText set_pin did not verify; ui_* MCP
  tools map to ui_mutate_tree / ui_set_widget_properties on TCP.
- Process lesson: TaskStop on a background shell can leave its bash child running; kill leftover chains by PID
  (PowerShell Win32_Process with the chain's command line), or two sweeps run as the same lane and share one EXCLUSIVE.
- Lease rule from main: area leases <= 120 s, one run each, never across the PIE window; check pie_running before
  every compile.
- Overlay focus (aaa_focus_fix.py): FocusUI's SetInputMode(InWidgetToFocus = overlay) ran after the overlay's Construct
  focus, so Settings/Credits/Confirm/Pause roots kept focus and keys and the pad did nothing inside them (red proof:
  Saved/UIShots/aaa/sweep_menufast_r1_prefocus). Fixed with DesiredFocusWidget on each overlay (its first button) and on
  WBP_SandButton (now focusable, forwards to Btn_Hit).
- Sweeps: input only while lease_status shows our EXCLUSIVE (hold_exclusive, checked before PIE and every input); the
  sweep releases only its own EXCLUSIVE (release_exclusive), never `editor_lock.py release ui` (that frees everything the
  lane holds, including a running sweep's EXCLUSIVE). menufast/inputfast reach the menu through a state gate
  ({'menu': True}: Space only until pie_call reports WBP_MainMenu; {'unless_menu': key}); a fixed 4-Space skip landed on
  "Wake up" when the boot ran faster (r2). Perf sweeps skip the per-key sound probe.
- blueprint_graph_batch is NOT atomic: ops before a failing op stay applied. Make every variable a batch reads exist
  and compile BEFORE sending it (b3_encounter_fix.py does this; a 22:55 batch left an entry on a dead-end Branch).
- Granted by main for QA B3 (story's WBP_Encounter): Victory collapses SelfBox and EnemyPanel (else restores
  SelfHitTestInvisible/Visible), LogPanel auto-sizes, the Victory phase line is ''. Story mirrors these in its builders.
- BP_Phone Mesh collision (phone_collision.py): Custom, QueryAndPhysics, WorldDynamic, Pawn/Camera Ignore, Visibility
  Block, CanCharacterStepUpOn No. The placed Phone_Nightstand overrides collision per instance: world resets it.
- Overlays: the screen under an overlay (PauseMenu in gameplay, else Screen) goes HitTestInvisible while the overlay is
  up (BP_FoAFrontEnd.SetUnderlayHitTest, overlay_underlay.py). Before, the main menu's 435 px button hit areas under
  Settings caught Down from Interface volume before the Music slider (audioprobe dumps).
- WBP_SandButton.Img_Vortex slot Bottom -40 -> 0: the focus swirl spilled onto the row below (the "stray tick").
  Music/Dialogue rows have the old rows' 14 px bottom padding.
- Phone lock screen to script.md section 3 (phone_lock_spec.py): MessagePreview(Index) is the one source for inbox rows
  and lock banners (BeatIndex >= 3 switches both); UpdateClock = 6:40 + whole real minutes since the morning's first
  draw, capped 9:59, new morning when BeatIndex goes backwards; ClockDebugMin via SetClockDebugMinutes is proof-only.
  Lock OR home (phone_lock_exclusive.py): Pages hidden until the lock is gone, then 0.15 s in; fresh open = frame gap
  > 10.5 (the world widget redraws at 30 Hz). Proofs: sweep lockproof (pie_call BEAT/PHONEMIN/PHONEDUMP).
- Restart Day hides the HUD (opacity 0) like RolloverCovered; FadeInStep brings it back with the new beats
  (restart_hides_hud.py, QA #17).
- Proof runs: sweep_intro sets GI_FoA.SetProofProgressContext('FoA_QA_UI') right after PIE starts (pie_call PROOFCTX)
  and restores it before PIE stops (PROOFRESTORE); Settings.sav bytes are restored after each run. The LookDev
  intro_runtime_probe.py does the same inline.
- qa_phone_pages.py: fuzzy OCR, lock words and home words in one frame = TWO PAGES (red: anim phone5 shot_06_home).
- BP_Phone.ApplyScreen (phone_apply_screen.py), called from the construction script AND BeginPlay: the placed
  Phone_Nightstand overrides its Screen and PIE copies the editor actor without rerunning construction, so the class sets
  the live components itself (socket attach, M_UI_PhoneScreen, 540 x 1118, one-sided, Screen and Mesh stencil 200).
  Proof: sweep stencilproof (CustomStencil buffer view shows 200 on screen and body; no shaft wash after).
- Phone Today ticks (phone_today_checks.py): done = director TaskTicked OR ByBeat(Index) (Wake up from BeatIndex 1,
  Get dressed from 9); ShowTask dims the row and ShowRowCheck/ShowCheck fill Img_Check<i>. The director's beat data ticks
  on CompleteBeat only (T9 ticks Wake up). Proof: sweep todayproof (beat 10 raises the phone; checks filled 1,1,0,0).
  Hayba connect does not resolve wildcard array pins (Array_Get/Set): use typed nodes; switch_int comes back caseless.
- Settings sliders adjust with Left/Right directly (Sld_Value RequiresControllerLock False); proof: menufast + pie_call
  SETTINGSDUMP reads the saved slot (Music 0.95 after Left, 1.0 after Right). Overlay roots are all focusable
  (ConfirmDialog was not: the pad went to the viewport under "Restart the day?").
- BP_Phone swap applied 2026-11-10 00:47 (aaa_phone_swap.py): anim's BeginPhoneHold/EndPhoneHold, no view-target change,
  PhoneCam deleted, OpenPhone -> WBP_Phone.ResetLock, PhoneTap on every phone function, mouse wheel/click, Screen attached
  to SM_Phone's Screen socket in the construction script (no Blueprint socket attach in Hayba/Python), one-sided,
  540 x 1118 at 0.01222 (fits the glass). Proof rec_phone_swap1: clean raise (no letterbox, no smear), lock first, one
  page at a time; readability fails on the hold framing (anim: screen >= 1/3 of the frame). Phone body text is 1.2x
  (phone_type_bump.py; ui_set_text_style is MCP-only, so Font.Size is rewritten in place).
- Phone hold swap (aaa_phone_hold.py hold, nocam, verify; glass; taps) is approved in principle and waits for anim's
  phone6 (after the first-person head fix); add: the Screen widget one-sided (it drew mirrored on its back face). Was
  phone5: the view stays on the player camera, PhoneCam is deleted, the Screen widget attaches to SM_Phone's Screen
  socket (0,0,-0.51, pitch -90). Proof: aaa_phone_proof.sh (30 fps request) + qa_phone_raise.py (letterbox, smear,
  OCR readability; red-proven on story's T0 frames).


## Current status (supersedes the older open/next-step notes below)

- B5: WakeUp feedback delay is 0.15 s (was 3.07); CutToBlack fade duration is 0.01. Reviewed `Saved/UIShots/regression_r8/frames/f0121.png` (menu) and `f0122.png` (black); the input time is the tool-return time, so do not claim exact input latency from those timestamps.
- B12: Title TryConfirm no longer gates input on bReady. r8/r10/r11 show the first key during the fade opens MainMenu.
- B13: r10/r11 confirm defaults to Stay, Left/Right moves focus, Settings Escape returns focus. Reviewed r10 f0053/f0076/f0080 and r11 sheet_01. Native blue keyboard-focus rectangle is intentionally retained.
- B6: root Back now returns to Title. Regression r10 exposed a stale Overlay reference: CloseOverlay removed the widget without clearing its reference. Fixed with validity guard, clear-reference, then the existing delayed menu focus. r11 exposed a second leak: Confirm had no OnKeyDown override and Main consumed only Escape. Confirm now consumes Escape/B and Main consumes both. **Full r12 state-gated proof passes**, including controller B closing one layer, root Escape to Title, Space to Main, and Wake to black. 110 frames at 4 fps, error:null. Reviewed f0073 (Stay focus), f0086 (Main after B), f0089 (Title fade after Escape), f0098 (black after Wake). Credits already consumed both.
- Patches: `fix_intro_responsiveness.py`, `fix_back_consumption.py`; authored builders mirror changes. Do not rerun all builders: older unrelated runtime patches may not be mirrored elsewhere.
- Three boot-logo texture caps set to 512; actual top mips are Unreal 512x512, Aholo 512x115, Hayba 256x310. BGRA top-mip estimate 38.98 to 1.53 MiB; source images preserved. Readback in `Saved/UIShots/fix_r8/texture_sizes.json`.
- State-gated regression harness now waits for observed Screen/Overlay before each phase, uses a 42 s deadline, and captures at 4 fps. `test_sweep_regression.py` passes. Failed phases abort dependent Wake inputs.
- No-shot `perf_r11_perfintro`: 1968 frames, p50 17.6 ms, p95 24.3 ms, p99 28.5 ms, 3 startup frames >50 ms; zero transition hitches >50 ms. Baseline `perf_r3_perfns`: p99 71.4 ms, 49 hitches. Scene changes and temporary `-DisableAsyncCompute` mean this is **not an isolated causal comparison**. QA still fails its zero-hitch requirement.
- Do not prebuild MainMenu speculatively: baseline 140.6 ms transition hitch was 123 ms ticker self time; actual OnTitleConfirmed/ShowScreen was 3.24 ms. Attribution within ticker remains unresolved. Startup Mass work comes from FMassEditorPhaseTickTask, an editor subsystem that always ticks; specific processors remain unknown.
- r9 GPU stalled; coordinator restarted twice, then temporary `-DisableAsyncCompute` stabilized current tests. No project graphics config changed by UI. Parent owns editor restarts and PIE scheduling.
- v4 remains unapproved and unbuilt. Teen retarget/cinematic correctness belongs to animation; UI black-transition proof does not validate the film.

Hayba crash prevention task is isolated at `O:/Projects/SoftwareIncubator/hayba-safe-anim-query`, branch `feat/anim-instance-safe-inspection`, commit `5a0149d1`, based on restart6. New named `anim_instance_get_state` validates actor/component/world, animation-blueprint class, machine existence, initialization, and state bounds. 21 TS tests pass; UE build and native Safety test pass (1/1, zero warnings/errors). No live DLL installed. Integration branch/worktree `O:/Projects/SoftwareIncubator/hayba-anim-safety-integration` preserves the installed no-modal deletion overlay (`35f8472d`) and adds animation's validated dynamic-properties binder patch (`d4d29643`). Integrated UE build and 23 TypeScript contracts pass; native Safety and DynamicBinding both pass, zero errors. Four warning-severity messages are the existing compile logger reporting errors=0/warnings=0. Final DLL SHA256: `46860782dd764d9dbb6661fdd11663f2d5e77635325588013ccee5aaf17882d5`. Exact source/binary hashes and native report are recorded in host `integration-provenance.json`; coordinator has installation handoff. Disposable host: `O:/Projects/SoftwareIncubator/Saved/hayba-safe-anim-host`; use `-nullrhi -HaybaAutomationChild=<token>` so it cannot publish heartbeat or take FoA's port.

Standalone performance recipe/analyzer: `Tools/Unreal/ui/standalone_perf.py`, using native `-csvCaptureFrames=3000 -ExitAfterCsvProfiling -csvCompression=0`. Coordinator must close the editor first, run one GPU game process, then restore editor. Standalone still unmeasured. Check native focus colour there: PIE's Starship focus brush is blue, UMGCoreStyle defines white; no safe per-UMG-Button brush override exists without a scoped native subclass. Do not suppress keyboard focus globally.

Owner id `ui` (HAYBA_AGENT_ID=ui, FOA_AGENT=ui). Writable: Content/FoA/UI/**, Tools/Unreal/ui/**, Saved/UIShots/**, docs/design/ui/**, plus Content/FoA/Gameplay/BP_BeatDirector.uasset and Tools/Unreal/flow/build_director.py (granted by main for the skip fix).

## Done

**Direction (waiting on the user's approval).**
- Research doc: `docs/design/ui/aaa_ui_direction.md` (ten games, principles, per-screen spec, material kit). Its header says the prototype's tokens win where they differ.
- Live WebGL prototypes of all nine screens: https://claude.ai/artifact/VwkNfHmcAspBtdGQEDzVph. Source: `C:\Users\Admin\AppData\Local\Temp\claude\47e10ba54099b5a9\f6b57ca2-9e47-4dcd-a55a-de7f221fc83c\scratchpad\ui_v4\index.html`. Stills: `Saved/UIShots/v4/proto_*.png`.
- The battle lane has the UI style kit (sent by message).
- The v4 rebuild in UE has NOT started; it waits on approval.

**Intro bug sweep.** Full list with frame numbers: `Saved/UIShots/intro_bugs.md`.

Recorder. `Tools/Unreal/ui/sweep_intro.py` with `sweep_rec.py` record in engine at 16-22 fps: one `Shot showui -nosuffix filename="â€¦bmp"` per request, frames the level editor viewport steals dropped by size, PIE-clock times, keys logged in PIE time.
- Modes: `cold`, `skip`, `menu` (overlays and focus), `perf`, and `input` (pad, keyboard and mouse at every stage; never run yet).
- Post-process a finished run again with `sweep_intro.py <dir> post`.
- Analysis: `analyze_sweep.py <dir>` writes the sheets and flags; `sweep_strips.py <dir> <tag> name:a-b` writes strips.
- Never use a desktop grab. The editor is on another virtual desktop, so a desktop grab recorded the user's own screen; that capture was deleted.

Fixed and proven in PIE (Hayba unless noted, all compiled clean and saved):

| Bug | Fix | Proof |
|---|---|---|
| Hayba card fade | Codex's clock fix, verified | r2_cold f0311-f0425 |
| B2 Aholo logo in colour | `T_UI_Logo_Aholo` AdjustSaturation 0 | r3_skip |
| B7 one-frame flash before LS_WakeUp | FinishWake now drops the black overlay 0.15 s later through a new `BP_FoAFrontEnd.DropBlackOverlay` | r3_cold: max luma 2/255 against 33/255 before |
| B9 film skip flashed another camera | BP_BeatDirector skip cut holds black (fade 1 to 1, Duration 0.01), then a new SkipFadeUp event fades up after 0.15 s | r6_skip f0337 to f0342 |
| B11 focus lost after Esc closes Settings | CloseOverlay sets a 0.05 s timer to the menu's FocusDefault | r6_menu |

Notes on those fixes:
- B9 is folded into `Tools/Unreal/flow/build_director.py`, and an events-step rerun reproduced the graph exactly. Duration 0 never fades: `PlayerCameraManager::UpdateCamera` only updates FadeAmount when FadeTime > 0.
- B13: the Quit confirm opened with no keyboard focus. WBP_ConfirmDialog now focuses Stay via a 0.05 s FocusDefault timer, and `wire_overlays.py` builds every overlay that way. Compiled clean, but **NOT yet proven in PIE**.

## Open problems

- **B5** Wake up gives no feedback for 3.07 s, then a hard cut. **B6** Esc on the bare main menu does nothing. **B12** the title ignores keys during its ~3 s fade-in. All three are designed into v4.
- BP_FoAFrontEnd.CutToBlack also uses a Duration 0 hold fade. It's harmless because WBP_Black covers it; set 0.01 in v4.
- **Esc in PIE with focus on the viewport stops the PIE session**, even though `Saved/Config/WindowsEditor/EditorKeyBindings.ini` maps StopPlaySession to Shift+Esc. That ended the r4, r5, r6 and r7 menu sweeps early, and it may be part of the user's unresponsiveness.
- Hayba gap: blueprint_inspect_graph and blueprint_measure_nodes clip at 50 nodes and give no pin defaults. Routed to Hayba lane ab73f962382a0c264. Until then: read-only scripts `scratchpad\uilane\trace_exec.py`, `snap_graph.py`, `snap_all.py`.
- QA check (b)'s title region in `Tools/QA/layout.json` must change when the v4 menu lands; send main the new rect.

## Exact next step: the user's intro lag spikes ("lots of lag spikes / bugs and unresponsiveness in the intro sequence ui")

Main wants the spike table before any fix.
1. `Saved/UIShots/perf_r1_cold` was recording at 16:01 (perf mode: no shots, per-frame dt to frametimes.csv, `stat dumphitches` at a 50 ms threshold).
   - Run `python Tools/Unreal/ui/perf_spikes.py Saved/UIShots/perf_r1_cold`. It writes spikes.md (every frame over 50 ms with PIE time, its hitch tree and nearby log lines: shader or PSO, GC, loads, streaming) and run_log.txt.
   - If the run failed, rerun `python Tools/Unreal/ui/sweep_intro.py P:/FoA/Saved/UIShots/perf_r1_cold perf` (it waits for a PIE window).
   - Send main the table, including any textures the streaming lines name; main owns the pool and budget.
2. Input sweep: `python Tools/Unreal/ui/sweep_intro.py P:/FoA/Saved/UIShots/input_r1 input`. Its keys.json lists focus per input; list every dropped input. It also proves B13.
3. Fix in territory. Prove each fix with before/after `perf` runs and the input sweep.

Rules learned this session:
- Pass `FOA_STEP=â€¦` to ue_remote as an argument, not a shell variable. Once it silently ran the builder's default step.
- Never run ue_remote while your own sweep holds EXCLUSIVE; the same lane's lease covers both.
- Keep sweeps under ~45 s and put any Esc last.
