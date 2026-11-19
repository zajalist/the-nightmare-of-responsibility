# World lane handoff (2026-11-07 16:03, stopped by the usage limit)

Lane id `world` (HAYBA_AGENT_ID=world). No lease held, no TMP_world_ actors left in the level, level saved at 15:44.

## Done
- **Lock (the user's "rectangle with no texture").** Door_Bedroom's ToolPlate, ToolScrew0-3 and ToolKeyhole are now a Lux3D escutcheon plate and Lux3D slotted screws.
  - They are per-instance overrides on the placed door; BP_Door's template is untouched.
  - Script: `Tools/Lux3D/fit_door_lock.py`. It re-fetches the component for every property, because each edit re-runs the construction script.
  - The plate's blue texel islands were inpainted into `/Game/FoA/Props/DoorLock/Plate/T_DoorLockPlate_BaseColor`.
  - Proof: `Saved/WorldShots/lock_before_close.png` and `lock_after_close_base_v2.png`.
- **Greybox audit and fix.** Audit: `Tools/Lux3D/prop_audit.py`, output `Saved/WorldShots/prop_audit.json`.
  - The door, the door frame and 21 window sills, sashes and muntins were on M_Greybox children (MI_Trim_Paint, MI_Metal).
  - Door and frame now use `Props/Door/MI_Prop_DoorPaint` (child of MI_Trim_Baseboard, flat ornament normal) plus the plate's aged-brass MI for the knob and hinges.
  - The windows now use MI_Trim_PaintedWood.
  - Script: `Tools/Lux3D/fix_greybox_materials.py`.
  - Left as is, on purpose: the glass panes (cube boxes, M_Glass), the room shell cubes (already textured), the light-shaft planes, and the Nightmare's Manny placeholder (player lane).
- **BP_SandAmbience** (`/Game/FoA/Gameplay/Ambient`, placed as SandAmbience at the origin, folder FX/Sand). It compiles with 0 errors and 0 warnings.
  - Builder: `Tools/Splats/build_sand_ambience.py`, phases assets / helpers / events.
  - Design: `docs/design/world/foreshadowing.md`.
  - Events: creep, pile, trickle, drift, clock drip, sleeve, shirt imprint, Nightmare glimpse, suit, hourglass, and WatchStill (the feet bloom).
- **New assets.**
  - Splat meshes: SM_SandShirtImprint, SM_SandSuit, SM_SandHourglass, SM_SandTrickle_Ceiling, SM_SandTrickle_Clock.
  - MIs: MI_Sand_Imprint, Suit, Hourglass, Trickle, ClockDrip, ShaftDrift.
  - Tools: `glb_to_sandsplats.py`, `make_trickle.py`.
  - Lux3D prompt table: `docs/design/world/lux3d-world-prompts.md`. `lux3d_batch.py` gained a `--table` option.
- **QA.** `foa_qa.py logs` at 15:53: the last PIE session had 0 Blueprint errors, 0 Accessed None and 0 ensures. `Failed to compile Material` appeared 0 times. The "Chance was pruned" lines in the log predate the fix that made Chance pure.

## PIE proof status (honest)
- Bursts: `bash Tools/Splats/pie_ambience.sh amb|fore|live`, then `python Tools/Splats/pie_ambience_media.py <plan>`. Output goes to `Saved/WorldShots/pie_<plan>/` (GIF and still per event).
- Every forced event plays through its real Ev_* gates. The natural Step also fired an event on its own (pie_amb.json).
- **The frames are not good enough yet.**
  - Framing is the main problem. The 16:00 fore burst ran with the new closed-loop camera (`keep_aim`). Its media cut hadn't been checked when the lane stopped. Check `pie_fore.json` `aim_err` and `aim_pitch`.
  - The wardrobe creep is in an unlit spot, so it's invisible. The door creep reads against the hallway light.
  - The trickle meshes were rebuilt at 15:45 and look right in the editor (`pe_trickle_bay.png`). They haven't been re-shot in PIE.
  - Blooms never rendered in editor-world captures: probably a clock mismatch with SceneCapture. In PIE they do render: the shirt imprint and the pile showed.
  - The glimpse failed in the 15:50 run (the camera read stale). Since fixed by `glimpse_face` plus a later draw, but not re-run.

## Next steps, in order
1. Cut and check the fore burst: `python Tools/Splats/pie_ambience_media.py fore`, then a contact sheet. Then re-run `amb`, then `live`. One per PIE window.
2. **Alarm clock (main's job).** Agreed with anim (ae7620936be7fa99d):
   - Ring is keyed 1 from 2.30 to 25.27 s and 0 at 25.30 s.
   - DissolveAmount is keyed 0 at 25.30 s and 1 at 26.50 s; anim keys both.
   - The palm targets actor + (0, 0, 16).
   - The pile must stay within 14 cm of the actor origin, and the rattle must read from 2 m.
   - Builder written, **not run yet**: `Tools/Splats/build_clock_wakeup.py`. It adds the Pile part, Ring with SetRing, RingJitter, and a new SetDissolveAmount that shows the pile once. Before running it:
     - create `MI_Sand_ClockPile` (child of MI_Sand_AlarmClock, Tune (0,0,22,0), Splat (2.5,0.9,1,0.9));
     - check that `S_Clock_AlarmMechanism` is long or looping enough for a rattle;
     - after the build, make `build_sand_bps.py graphs_a` stop rebuilding SetDissolveAmount (it would clobber the pile hook).
   - Proof: a PIE GIF of ring, shake, slap, crumble and the pile staying.
3. Rename the Interchange-named lock assets (textured, Designer_Logic_PBR) to SM_/MI_/T_ in one run with referencer fixup, then save the level.
4. Send main GIFs, the QA log and captions. Log deliverables to `P:\FoA-Devlog\media_log.jsonl`; the lock and material lines are already logged.
