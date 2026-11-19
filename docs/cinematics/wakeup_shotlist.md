# Wake-up: shot list (LS_WakeUp v4, 19.1 s)

`/Game/FoA/Cinematics/LS_WakeUp`. 19.1 s (573 frames) at 30 fps. Owner: anim lane.

## v4 (2026-11-09): the tight cut
The user called v3 (36.4 s) long and boring. v4 keeps every shot that carries a beat and ripple-cuts the holds in
place with `Tools/Unreal/cine/retime_wake.py`, so the user's hand-set pose tracks and flags survive (no rebuild).
Gameplay is first person, so the film ends in his eyes, not over his shoulder.

| # | Time (s) | Shot | What happens |
|---|---|---|---|
| 1 | 0.0 to 1.5 | Black | Tick; the alarm mechanism clicks at 0.70 and the bell starts at 0.80. |
| 2 | 1.5 to 6.2 | POV from the pillow | Eyelids: half open, close, slow open by 3.9. Head turn onto the ringing, juddering clock 4.0 to 5.6, held to 6.2. |
| 3 | 6.2 to 9.37 | Push-in on his face | 2.3 s eased push, heavy-lidded eyes (0.2) with one slow blink at 7.4 to 8.0, sleep breathing. Time-shift dip to black from 8.97 (black 9.33 to 9.40), shift streak and FaceSlip burst. |
| 4 | 9.37 to 11.37 | Bed-edge two-shot | Fade up 9.40 to 9.80; seated; anticipation from 10.97. |
| 5a | 11.37 to 12.0 | Medium (Cam_Insert, high 3/4, 40 mm) | He leans over and raises the hand about 22 cm above the lid. |
| 5b | 12.0 to 14.07 | **True insert (Cam_Hit)**: low and close on the nightstand top, 50 mm f/5.6, 87 to 84 cm from the clock, 28 cm above the table, long-shutter motion blur | The clock rattles alone for 0.33 s, the palm drops in from the top of frame (19 cm in the last 0.12 s, smeared), **contact 12.47 (frame 374)** with a 4-frame camera kick, the fingers splay, the palm drives 5 cm into the caving clock, sinks with the collapse (dissolve 12.47 to 13.67), holds in the pile 13.32 to 13.69, and lifts out by 14.02. `Tools/Unreal/cine/add_hit_insert.py`, `Tools/Unreal/wakeup/slap_motion.py`. |
| 5c | 14.07 to 15.0 | Medium (Cam_Insert) | He sits back; the pile stays. Ring 1 from 0.80 to 12.43, 0 at 12.47. |
| 6 | 15.0 to 19.1 | The stand | Breath hold 15.0 to 16.0, stand 16.0 to 17.7 with the crane, hold, then a 6-frame blink to black 18.9 to 19.1. |
| hand-off | 19.1 + 0.6 | First person | The film ends black (Fade Keep State) and keys BP_FoAPlayer.bHandoffFadeIn. The director's WakeUpDone moves the pawn and sets the control rotation; SetCinematic(false) then fades the head camera up over 0.6 s. No camera-cut blend (bCanBlend off), so the camera never travels into his head. |

2026-11-10: shot 3 (the push-in on his face) was dropped on the user's request ("we can now see his freaking head as it turns to view the alarm clock"). The POV now holds on the clock to 9.37 and cuts straight to the two-shot. Only the Camera Cut track was patched, in place (`Tools/Unreal/face/wake_drop_pushin.py`), and the Cam_PushIn binding stays, unused. `build_ls_wakeup.py` still lists PushIn, so drop it there before any rebuild.

Cut in v4: the room wide (the first gameplay frame establishes the room now), the over-shoulder hand-back, the long
holds. The time shift is at 9.37 s (BP_BeatDirector BedSettleStart = now + 9.37).

## v3 (superseded, kept for reference)
36.4 s at 30 fps, 16:9 (1920x1080). Builder: `Tools/Unreal/cine/build_ls_wakeup.py` (core rebuild is locked; it
would replace the user-edited tracks).

## The scene
A teen wakes at night in a room that is almost right. He strikes the alarm from above; the clock collapses into black sand beneath his palm and leaves a pile on the nightstand. He
gets up anyway.
Arc: suspended, disoriented, alone, dread, the loss of the clock, resignation, resolve.

## Rules for every shot
- Every camera move starts and ends on a held key. Transform keys are Smart Auto, never linear. Nothing moves after a
  move ends.
- Most transitions use held frames, plus one dip through black for the time shift. The 24.2 s insert cuts into the
  raised-arm anticipation, matching its direction and phase. The camera holds without a cut through impact and collapse.
- Animation clips blend over 0.4 s and play in Force Custom Mode (the ABP is bypassed while the sequence runs and comes back
  when it ends). The pawn's transform changes only under black.
- Lenses are on a 36 x 20.25 mm filmback. Shallow depth of field and focus tracking apply to cinematic shots only, and
  the hand-back ends with no blur.
- The look is monochrome night. Light comes from two motivated sources: the moon through the bay window (cold, soft,
  high, from the south-west) and the hallway leak around the door (east wall, low, hard). The alarm clock's luminous
  dial is a small third practical.
- His face is never clean (the slice distortion is his identity): MPC_Dream FaceSlip holds the calm baseline 1 (0.6 in the
  50 mm push-in, the close-up value), with one
  burst at the time-shift dip (19.45 to 19.75). Readability comes from the silhouette and the body language.
- Every cinematic light is a spawnable inside LS_WakeUp, alive only for its own shot. Each is shadowless, small in
  radius, and only bright enough that faces and silhouettes read. The level lights are never touched.

## Shots

| # | Time (s) | Shot | Lens | Camera | Action | Light | Beat | Out |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.0 to 3.0 (3.0) | Black | (POV camera behind the fade) | none | The clock ticks in the dark. At 2.2 the alarm mechanism clicks, and at 2.3 the bell starts. | none | Before anything, the clock. | Eyes open (fade track) |
| 2 | 3.0 to 9.2 (6.2) | POV from the pillow | 24 mm, f/1.4 | His eye point on the pillow, looking up past his brow at the ceiling and the unlit lantern. Held from 5.4 to 6.4. An eased head turn of 52 degrees, left and down to the clock, from 6.4 to 8.0, with a 4 degree roll as the head rolls on the pillow. Held from 8.0 to 9.2. | Eyelids: half open (3.0 to 3.6), closed (3.8 to 4.1), slow open to full by 5.4, with the vignette easing from 1.0 to 0.45. Focus pulls from 15 cm to the ceiling (3.4 to 5.2), then onto the clock with the turn (6.4 to 8.0), so 8.0 to 9.2 is a clean hold. | L2_CeilingWash: a rect light from the bay side, aimed up, so the ceiling reads as moonlit plaster. L2_Dial: the clock's dial glow. | Where am I. | Cut on a held frame |
| 3 | 9.2 to 13.2 (4.0) | Wide: the room | 28 mm, f/4 | High in the north-west corner over the desk, looking diagonally across the room to the bed in the far corner. The moon shafts from the bay sit in the middle ground, and the lantern hangs at the top of frame. Locked off. | He lies on the bed, a small shape with too much room around him. | Level moon and shafts. L3_BedKick: a soft rect from the bay direction, so the duvet and his outline separate from the black wall. | Alone and small. | Cut on a held frame |
| 4 | 13.2 to 19.7 (6.5) | The slow push-in | 50 mm, f/2.0, focus on his face | High on the room side of the bed, three-quarter from the foot, about 34 degrees off his face plane, 150 cm from his face (a low angle saw the face edge-on from under the chin). Held for 1.0 s, then a 4.6 s eased push to 100 cm (14.2 to 18.8), then held until the dip starts at 19.3. | He lies on his back, eyes open, looking up, breathing slowly (AS_FoA_Wake_Lying). | L4_MoonKey: a soft rect from the bay side, high, raking across the far side of his face (short lighting, the near cheek in shadow). L4_Eye: a tiny catchlight near the lens. | The dread settles in. | Time shift: a dip to black from 19.3 (black 19.65 to 19.75), with the shift streak and a tape scrub |
| 5 | 19.7 to 24.2 (4.5) | Bed-edge two-shot: him and the clock | 40 mm, f/2.8, focus on him | In front of him and to his right, at seated eye height. He sits on the bed's edge with the nightstand and the ringing clock beside him. Locked off. | He sits and breathes. Anticipation begins at 23.80; the hand gathers through 24.15, then rises. | L5_DoorRim: the hallway leak, hard and low from the door side, rimming his shoulder and the clock. L5_MoonBack: a soft back rim from the bay over his shoulder. | Him and the thing that rules him. | Dip up from black (19.75 to 20.15). Match the rising hand into the insert. |
| 6 | 24.2 to 28.4 (4.2) | Insert: the clock and the sand | 40 mm, f/5.6; focus on contact plane | Locked high three-quarter view. Clock slightly right of center, table in the lower third; the full hand and elbow arc enter from upper left. Include the entire clock and resulting pile with 10% frame margins. | The raised hand reaches its apex at 24.65, hovers/reorients through 25.05, then accelerates downward to palm contact at 25.30. Give through 25.42, pressure hold to 25.65, then follow the collapsing clock to 26.35. Dissolve runs 25.30–26.50. Withdraw clear of the pile by 27.30 and hold the unobstructed pile through 28.40. | L6_Dial: the dial glow. L6_SandRim: a narrow hard spot from the door side, grazing the sand so the pile separates from the table. | He silences the alarm; something remains wrong. | Cut after 1.1 s of readable pile |
| 7 | 28.4 to 33.4 (5.0) | The stand | 32 mm, f/2.8, focus tracks his head | Front three-quarter, low, from the room. Retain the pile at lower right during the opening breath hold (28.4–29.4). As he stands (29.4 to 31.1), an eased crane up from 100 to 140 cm, tilting to keep his eyes; the pile may leave the frame naturally. Held from 31.4 to 33.4. | The breath out, the push off the mattress, and the stand. The standing idle blends in over 0.4 s. The sand pile persists into gameplay. | L7_MoonKey: a soft key from the bay side. L7_DoorRim: the hallway leak rim. | He goes anyway. | Cut on a held frame |
| 8 | 33.4 to 36.4 (3.0) | Hand-back | 35 mm, then the gameplay FOV | Behind his right shoulder, on the gameplay axis (control yaw 55, pitch -10), at 80 % of the spring-arm length. Held for 1.5 s. | He stands, idle (MM_Idle, the clip the ABP's Idle state starts on, blended in over 0.4 s). | L7 continues. | He's ours now. | A 1.5 s eased camera-cut blend into the gameplay spring-arm camera. Depth of field opens to none. |

### Alarm insert framing and acceptance

The prepared camera seed is the clock actor origin plus (-105, +70, +95) cm, aiming at the mesh's visible center
with a small bias toward the approaching arm. The saved `edge.clock` position is a palm contact target at the lid,
not the clock's visual center. Use the actual animated hand/elbow envelope to fit the shot; these coordinates are
a starting point, not proof of coverage. Keep the palm, clock and pile readable together; open to f/8 if necessary.

Review rendered frames before anticipation, at the apex, at 25.30 contact, during the pressure hold, at 26.50 collapse
completion, and during the 27.30–28.40 pile hold. The palm must visibly land from above, remain in contact, and follow
the collapse without passing through the table. No body or clock clipping, empty-wall framing, clean face, or dark
unreadable pile passes review. The stand remains at 29.40 and the sequence remains 36.4 s.

This revision records the agreed repair. The earlier 20:42 capture failed framing and face readability; the revised
camera and acting require a fresh runtime capture after application.

## Sound (audio track, existing SFX from the audio lane)

| Time (s) | Cue |
|---|---|
| 0.0 to 2.2 | Clock tick loop |
| 2.2 | Alarm mechanism click |
| 2.3 to 25.30 | Alarm bell continues until palm contact; stop at 25.30. |
| 3.0, 4.1 | Eyelids |
| 6.4 | Sheets as the head turns |
| 19.4 | Whoosh and tape scrub (the time shift) |
| 19.7 | Bed sit |
| 25.30 | Palm impact and sand shift; sand collapse continues through 26.50. |
| 27.30 to 29.4 | Settling breath; keep the pile readable before the stand. |
| 29.4 | Get up |
| 30.3 | Floor creak |

## Runtime
- **Hand-off from the front end:** pressing Wake Up starts a 0.15 s timer to CutToBlack. That function hard-cuts to
  held black (0.01 s PlayerCameraManager fade), removes the menu, then waits WakeBlackSeconds (default 1.5 s).
  AfterWakeFade plays the story on the first start if configured; otherwise FinishWake calls BP_BeatDirector.BeginMorning.
  Completing or skipping the story also calls FinishWake.
- **PlayWakeUp in BP_BeatDirector (mech_flow):**
  - Before Play: DisableMovement, collision off, SetCinematic(true), and SetViewTargetWithBlend(pawn, 0).
  - CreateLevelSequencePlayer(LS_WakeUp), with movement and look input disabled and the HUD hidden, then
    SetBindingByTag("Player", pawn), then Play.
  - OnFinished: walking, collision and input back on, SetControlRotation(-10, 55), SetCinematic(false), and
    StartMorningBeats.
- **The fade track:** it opens at 1.0 over UI's held black, so the hand-off is invisible. It ends at 0 with Keep State,
  so it never restores black.
- **The camera-cut track:** its last section eases out over 1.5 s with Can Blend on, so the shot blends into the pawn's
  own camera.
