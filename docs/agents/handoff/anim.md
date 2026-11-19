## 2026-11-10 afternoon anim lane: hand-on-object grips, offline (editor held for the user's playtest)

Nothing below is baked or applied. Every grip is solved at mesh level in rig's Blender twin (`Tools/Rig/hand_twin.py`: game mm, the body unscaled, held objects at 1/BODY_SCALE) and written to `Saved/AnimShots/<grip>_solution.json`: the full pose as UE locals, hand_ue, and the object's component-space frame (object_ue) for the bake.
- **Clearance covers the hand, the forearm and the whole body.** Until 15:50 only hand and finger skin was checked; the screwdriver "passes" hid the handle's butt inside the wrist. HandSkin now includes lowerarm and twist skin. `grip_twin.body_clear_mm` checks the rest of the body near the object (within 30 mm: further out the nearest-face sign is no inside test). Every pass is gated on all three.
- **Grasp synthesis** (`Tools/Rig/grip_twin.py`): HandSkin (numpy skinning of one hand and forearm, asserted against the evaluated mesh), approach() (the whole hand comes in until it is 2 mm off) and close_digits() (GraspIt-style: all three joints close, then 02+03, then 03, each until that segment touches; fingertip vertices are never subsampled). The search covers only the stance and the hand placement. Self-test: `grip_twin.py selftest=1`. Blind searches over finger curls (screwdriver v1-v24, knob v1-v4) got stuck: straight arms, 95-130 deg wrists, fingers inside the door.
- **Screwdriver** (`screwdriver_twin.py`, NOT passing yet): grasp synthesis since v25, with a rule no skin check can catch: the handle's butt sits in the heel of the palm, at least 1 cm ahead of the wrist (v22 had it 6.4 cm behind, along the forearm's underside). Kept from before: one kneel (right knee down, free hand on the raised left knee, only the lean changes between screws), hands beside or over the handle (never under: v8's underhand hold was the one the user rejected), forearm in line <= 20, wrist <= 20, elbow <= 120. `screwdriver_review.jpg` shows the invalid v21 solves and is superseded. Screws 1-3: `from=0` keeps screw 0's kneel, `from=self` refines in place.
- **Door knob** (`knob_twin.py`, PASSES with forearm and body; `Saved/RigShots/knob/knob_review.jpg`): standing a step back, the arm hanging (elbow 162), spherical grip on the knob's right side, pads 2.0 mm, palm 2.55, wrist 22.8. Rules: palm-up is forbidden, and the knob sits at least 32 cm ahead of his root. Needs the real door and knob from the editor dump.
- **Drawer** (`drawer_twin.py`, PASSES; `Saved/RigShots/drawer/drawer_review.jpg`): solved on the commode glTF's right knob of the top drawer (a 3.8 cm mushroom, 98.7 cm up). Index and middle are both hooked behind the head (both required; v1 passed with the index lying straight, pointing), the thumb on top, ring and pinky curled in. Wrist 24.6, elbow 159. The solution's anchor_ue is the knob head. The commode is life size until the editor dump.
- **Hanger hold** (`hanger_twin.py`, PASSES; `Saved/RigShots/hanger/hanger_review.jpg`): one hold for the door gap and under the bed, on screw 0's arm (re-solve whenever screw 0 changes). The 9 mm bottom bar sits in the fingers with index and middle wrapped and the thumb pressing it; the hook end is 22.6 deg off the forearm. A fist cannot hold a 9 mm wire (its tunnel is wider). object_in_hand_bl is the attach.
- **Boot** (`boot_twin.py`, PASSES, placement-free; `Saved/RigShots/boot/boot_review.jpg`): an upright rubber boot on the floor in front of the kneel, fingers hooked over the rim. Re-solve in place after the dump.
- **Shirt** (`shirt_twin.py`, running, placement-free): a grab on the top of the crumple near its edge, kneeling and bent forward. The Lux3D glb stands the shirt up (75 cm tall, 14 cm deep) and place_bedroom only yaws Shirt_T7: in game it may be standing on edge (world lane, check at the dump).
- **Bake** (`player/bake_grips.py`): offline it builds `Saved/AnimShots/grip_bake.json` (finger locals; hand_in_object and root_in_object in game cm for the IK and the warp to Stand), self-checked. In the editor it writes AS_FoA_Grip_<Name>_R on the Teen skeleton. It refuses a solution whose twin did not pass.
- **Editor work after the hold (17:00-17:20):**
  - Phone cradle baked and applied at 16:41: AS_FoA_Grip_Phone_L, PhoneAttachOffset, PhoneHandInEye, PhoneElbowInEye; BP_FoAPlayer and ABP_FoAPlayer_MH compiled 0/0. PIE proof `Saved/AnimShots/phone/20261110_171218/`: the screen faces the eye at 0 deg, the attach and fingers match the solve exactly. The user judged the old hold (their play was 16:25-16:37). pie_phone.py now fails a flipped phone (glass more than 30 deg off the eye). A v2 variant is solving (`phone_cradle_twin.py variant=v2`): lower in frame, steeper forearm, wrist flexed 20-30.
  - Anchor dump `Saved/AnimShots/grip_anchors.json` (`player/dump_grip_anchors.py`, read-only) and the touched static meshes exported as FBX to `P:/FoA-Assets/character/mpfb/ue_export/` (`player/export_grip_meshes.py`). The twin loads them with `grip_twin.load_ue_mesh` (UE frame, asserted against the editor bounds) and places them with `body_matrix` / `place_in_body`. The knob is a 13-vertex lump of SM_Door_Bedroom, 8 cm above the keyhole. Shirt_T7 stands on edge (intended).
  - Teen grip poses AS_FoA_TeenGrip_{Key,Knob,DrawerKnob,Hanger,Boot}_R (`player/bake_grips.py`; the manifest `Saved/AnimShots/grip_bake.json` holds hand_in_object and root_in_object in game cm). Five right-hand layers in ABP_FoAPlayer_MH (`player/right_grip_layer.py`, weights RightGrip_<Name>).
  - BP_FoAPlayer grip runtime: BeginGrip(Anchor, Pose, HandInAnchor) / EndGrip / UpdateGrip on Tick drive the Teen right two-bone IK, the world hand rotation and the finger layer (`player/grip_runtime_graphs.py`, `player/grip_runtime_hooks.py`). SetToolHandTarget / SetToolHandRotation return while a grip is held. Nothing calls BeginGrip yet; the key (BP_Door) is next.
  - Key hooked up (18:00): BP_Door.BeginDoorTool, when ToolMode == Key, warps to the twin stand and calls BeginGrip(ToolMesh, 'Key', KeyGripHand); Finish, Cancel and Restore call EndGrip (`player/door_key_grip_graphs.py`). In PIE (`player/pie_key_grip.py`, `Saved/AnimShots/key_grip/20261110_180111/`) the hand sits 13.9 cm from the key, exactly as solved. Open bug: the Body stays at the door's own spot (325, 48.5) instead of the twin stand (328.1, 23.0); something after the warp moves him back. Fix that first, then replay (`Tools/Rig/replay_pie_grip.py pose=...`) and build the reference sheet.
  - Phone v2 (in progress): `phone_cradle_twin.py variant=v2` closes the fingers onto the phone (close_fingers), with READ lower and the elbow by his side. Reference photos are in `P:/FoA-Assets/reference/{phone_hold,key_turn,screwdriver}/` with sources.json. The thumb still needs a relaxed arc (close it onto the glass). `phone_grasp_twin.py` (fully synthesised) is parked: it never seated the thumb web on the left edge.
  - PIE drivers must use `player/proof_guard.py` (record_anim.sh refuses others). At 16:53 an unguarded pie_phone.py outlived its burst and disrupted world's PIE.
- After the hold: bake the finger poses per grip (pattern: `player/bake_phone_grip.py`), the editor dump of the door, knob, plate, commode, hanger rail, bed and boot transforms, then DT_FoAGrips and Begin/Update/EndGrip as planned.

## 2026-11-10 anim lane (phone hold, steady eye, slap thumb)

Everything below is applied and saved (Blueprints compiled 0 errors / 0 warnings) unless marked.
- **Phone hold, pinned to the camera** (main accepted 02:25, phone10). The cradle (`player/bake_phone_grip.py`: the palm against the phone's left edge, fingers across the back, thumb over the glass from the left edge) is solved offline from `Saved/AnimShots/teen_ref_pose.json` and written as `AS_FoA_Grip_Phone_L`, layered from upperarm_l in ABP_FoAPlayer_MH (`phone_grip_layer.py`). The layer alone inherited the clavicle and spine, so the phone drifted 5-14 cm after the raise and sat at the bottom edge at T10. Now:
  - ABP_FoAPlayer_MH has a left two-bone IK and a hand_l world-rotation replace right after Local To Component (`player/phone_camera_ik.py`), alpha PhoneIKWeight.
  - `BP_FoAPlayer.UpdatePhoneHold` (`player/phone_hold_attach_graphs.py`) sets PhoneHandTarget / Rotation / ElbowTarget each tick from FollowCamera (view pitch held to -40..10) composed with the PhoneHandInEye / PhoneElbowInEye class defaults: the solve's `camera` block, scaled to the 170/180 body.
  - READ (33, -1.5, -5.8) is literal in eye space: 10 deg below, 2.6 deg left, 0.49 of the frame. phone10 (T0) and phone10_t10 (the real T10 raise after EnterBeat 9) both hold 9.4-10.4 deg below. Sheet: `Saved/AnimShots/phone/20261110_022045/phone10_sheet.jpg`.
  - `player/pie_phone.py` FOA_PHONE_T10=1 films and judges the T10 raise. easyocr at 960x540 reads the lock clock as 6:20 at this size (a font quirk; main accepted). 31 cm forward would make it 0.52 of the frame if that check must pass.
- **Steady first-person eye** (`player/fp_steady_eye.py`, main accepted). There was no walk sink: the GASP relaxed walk loop carries a 10.6 cm pelvis/head bob (`player/walk_clip_bob.py`; run 11.9), and FollowCamera rode the head socket. `BP_FoAPlayer.SteadyFPEye` (end of UpdateFirstPersonVisibility): x/y from the head landmark; z = the capsule eased at 10 (held within 5 cm) + the standing eye height (tracked at 12 while still, held while moving) + 12% of the real bob. walk_sink5: 0.9-1.55 cm at walk and run (`Saved/AnimShots/walk_sink/20261110_021150`). `player/pie_walk_sink.py` is the proof (FOA_SINK_SET=1 replays walk_sink3's console 'set' and logs FollowCamera's activity and parent).
- **Slap thumb, Teen side** (`player/slap_thumb.py`): AS_FoA_Slap_Thumb_R (v3: thumb_01 turned 3 deg off the palm plane, 20 deg from the fingers on the index side; the Teen rest thumb hangs 36 deg palm-side), a thumb_01_r layer in ABP_FoAPlayer_MH at SlapThumbWeight, the FoA_SlapThumb curve on AS_FoA_Wake_EdgeReach (1 from edge+0.5 to +2.8 s), pushed by `BP_FoAPlayer.UpdateSlapThumb`. NOT visible yet: the pawn's Body reads weight 1.0 and the new thumb angle, but a 60 deg back-of-hand test pose (FOA_SLAP_TEST=1, hit_insert14) renders identically in Cam_Hit, and the pawn's Body hand_r stays at the lap (z 61) through the slap while the wide shot shows the arm raised. Whatever renders the slapping arm in LS_WakeUp is not the pose Python reads from the PIE pawn's Body. Next: log every SK_Teen_Body component in the PIE world (any actor class) at contact. `player/slap_thumb_angle.py` reads the angle from film.json; `player/slap_thumb_probe.py` checks the asset and layer wiring; `cine/wake_bindings_probe.py` lists LS_WakeUp's bindings (Player spawnable + 'Animation source Mesh' playing the edge clip; nothing on Body).
- **PIE drivers: never notify edits on the pawn.** A notified set_editor_property on a PIE component (pie_walk_sink's max_walk_speed 300) reruns BP_FoAPlayer's construction script, which puts FollowCamera back on CameraBoom:SpringEndpoint (walk_set 02:43). Use PropertyAccessChangeNotifyMode.NEVER (walk_sink6: Face:head throughout).
- **Approach** (`player/pie_approach.py`): pitch limit -65 (a low handle close up reads -58); a target offering only Look at this beat is skipped (story gate). The drawer contact aim comes from BeginEnvironmentContact (`player/environment_contact_graphs.py`): knob = bounds centre +-32% of the width, which assumes a 100 cm facade and lands on the carved centre of Commode_GothicCommode_01_door01. Knob sockets on the drawer meshes: post-playtest.

## 2026-11-09 anim lane (first person, wake-up v4)

Gameplay is first person (the user confirmed it on 2026-11-09). Everything below is applied and saved unless marked.
- **LS_WakeUp v4, 19.1 s.** `cine/retime_wake.py` ripple-cut it in place (no core rebuild, so the user's pose tracks survive). Shot list: `docs/cinematics/wakeup_shotlist.md`. The MPC FaceSlip and ShiftStreak keys had been authored in tick units (all in the first 0.05 s); they now sit at their intended frames.
- **Hand-off into first person.** No camera-cut blend (bCanBlend off). The film ends on a 6-frame blink to black and keys `BP_FoAPlayer.bHandoffFadeIn`; `SetCinematic(false)` fades the head camera up over 0.6 s (`player/handoff_graphs.py`). Proven frame by frame on the normal and skip paths: `Saved/AnimShots/handoff/`. Story set the start yaw to 195 and BedSettleStart to now + 9.37.
- **Breathing** on the user's lying pose (`wakeup/build_breath.py`): frame 0 is the user's pose exactly.
- **Slap from the top** (`wakeup/slap_motion.py` v2 plus `build_anims.py FOA_KEEP_SEAT=1`): a 22 cm raise, one beat, a 2.9 m/s strike, contact 12.47 s (frame 374).
- **True insert for the hit** (`cine/add_hit_insert.py`: Cam_Hit plus L6_HitKey, 12.0 to 13.77 s). The first framing put his shoulder in shot; the v2 camera is written but not yet proven (it waits on the user's playtest).
- **First person:** turn lean (`player/fp_polish_graphs.py`, Reduce Motion read fixed in `fix_lean_exec.py`) and look at what you touch (`player/interaction_look_graphs.py`) are applied. Look-down at -80 with a forward slide and a steady eye (bob clamped to +-2.5 cm) are in `player/fp_lookdown_graphs.py`, NOT applied: the 23 cm eye swing in the walk needs its cause from the tick log first (`player/pie_fp_review.py`).
- **Tired additive v2** (`player/bake_tired.py`): the head is level, the back rounded.
- PIE proof scripts: `player/pie_handoff_strip.py` (every frame), `player/pie_wake_film.py` (film plus a slowed window), `player/pie_fp_review.py`. Run them through `record_anim.sh` with FOA_PIE_SCRIPT. Per-frame shots drop PIE to about 4 fps (measured 77 to 4).

## 2026-11-07 21:33 verification update

Valid window-only wake video: `Saved/WorldShots/wake_video_20261107_212720/wake.mp4`. Reviewed action04/07/08/09/10/12/19: open hand, flat palm strike, follow-through and withdrawal clear; persistent pile visible. Latest contact error1.44cm, palm-normal tilt10°, actual projected unionUV(.332,.116)–(.669,.792), all geometric gates pass. Camera now aimsZ94, with40mm/f5.6 and18%retreat. UI subsequently reduced blown-out L6_Dial0.8→0.12cd; full11cinelights restored and rebuild-safe. Character added measured head-envelope bounds sphere; next wake proof checks it and full handback.

Sleep actual19 rigid occiput points across21poses are~3.1–5.5mm above previous traced pillow surface, removing earlier cm-scale gap/penetration. BlinkLeft/Right andSleepEyeClosure all1.0; any remaining eyelid issue is shape/postprocess.

Native DM proof passed `Saved/AnimShots/dm_live/20261107_212943/native_states.json`:33successful queries observedStart7,WalkRun10,Stop10,Idle6. Single terminalfailure was no-live-PIE after scriptdone, explicitly classified shutdownrace; future runner rejects otherqueryerrors. StartDone now evaluator-phase≥0.65s; first actualtrue after~0.9/.8/.66s frominput, notcapsulespeed0.06s. UniformIndexable +ExplicitTime fixes have no runtimewarnings. **Footmotion visual proof remains pending**, native run unfocused3–8fps. Parentwindowrecorder supports `FOA_VIDEO_PLAN=loco`, no private getters and noShot stalls. Also pending: unexplained thin silverdiagonal in earlier screwdriver closeup.

## 2026-11-07 21:22 — second actual wake revision ready

User stopped PIE; parent installed tested safe-state/dynamic-property Hayba DLL. Applied/saved: UniformIndexable compression on four active start/stop clips; ExplicitTime dynamic on four evaluators; shirt-only spine weights; lyingSKULL5.3; new stagedslap; exact clock geometric top102.081812 from Splats mesh bounds (component bounds were padded to111);40mm/f5.6 insert. Character assigned PA_Teen_Body; sleeping head now visibly renders. UI restored missing L6 lights and corrected QA frame-cropping bug. Do not stop any new user PIE.

First actual wake rejected: PickUp_Table frame0 fingers were clenched, Teen palm retarget drift, tight upper margin and absent lighting. Revised baked edge now uses80%open reference fingers for support and100%open duringraise/contact. Five simultaneous Manny/Teen skin-palm samples give retarget compensation(+2.0463,−5.4878,+3.2657)cm, spread0.081cm (`Saved/WakeUp/teen_palm_calibration.json`). Camera retreated18%, same40mm/f5.6. Assets saved and leases released, parent arranging second proof. Contact not yet approved. First proof skipped25.169→25.396 due Shot stall; verifier now reports unresolved instead of testing postimpact pose against static clocktop. Parent suppresses contact-period shots next pass.

Observer records real sequence timing, arm+distal finger poses, actual camera/lens, shirt weights, plus sleep blink morphs/head bounds. Exact Teen palm skin landmark is in `Saved/CharacterShots/mpfb/shirt_palm_diagnostic.json`. Parent owns proof; UI owns lighting; character owns cloth normal appearance. Locomotion StartDone still incorrectly uses92%capsule speed; measured first valid stance phase≈0.65s in both walk/run and phase-based transition remains pending.

## 2026-11-07 21:12 — user review, offline rework pending

**User-owned PIE began20:54:32 and remains active. Do not stop it, queue editor changes, or hold a lease. Anim lease explicitly released.** Parent coordinates the next safe window. User rejected alarm slap/camera and unnatural shirt-front fold normals; these are priority over cleanup. Existing film is not approved.

Applied and verified: all seven normalized Teen meshes; gameplay source ABP restoration; head CopyPose; suit switching; held screwdriver grip; cloth parameter transport at10Hz. This does **not** establish good acting, normal appearance, or distance matching. MH deletion gate remains unmet. New groom is not approved/active; short-hair cards remain.

Pending source changes (not baked/applied):
- `wakeup/slap_motion.py` + `edge_clip.py`: staged lift with loose wrist, flat contact25.30, give/hold,13cm follow-through with collapsing sand, withdrawal and rest27.30. Anticipation23.80; stand29.40 unchanged. `test_slap_motion.py` passes continuity/contact in two coordinate bases. Actual Teen contact remains unverified: current old assertion measures Manny before retarget.
- `cine/reframe_wake_insert.py`: locked elevated3/4,40mm,f/5.6; corrects template and any focal/aperture/focus tracks; preserves24.2–28.4 cut. Actual camera/path coverage needs proof.
- `wakeup/build_lying.py` SKULL5.3: live asset still3.1. Prior8.5 floated5.40cm;3.1 overshot3.27cm because retarget amplifies neck correction. Actual rigid occiput points in `Saved/CharacterShots/mpfb/sleep_occiput_contact.json`. Bedding at the contact is77.518cm.
- Character generating Body/Head PhysicsAssets after user exits. Current animated Body/Face bounds stay standing and exclude lying head by78cm in X: confirmed reason close shots show empty pillow. Do not hide this with arbitrary huge bounds.
- `player/teen_wrinkle_graphs.py`: upper garments' torso channel now spine-only, preventing seated hip flexion from driving shirtfront. Not applied; character owns correcting shader hard left/right seam and normal amplitude/locality. MID equality was transport evidence only.
- `player/dm_compression.py`: own UniformIndexable codec; current GASP cleanup had set compression None, causing native distance-matching warnings. `gasp_retarget.py`, `gasp_unstage.py`, and verification now preserve/check it. Not applied.
- UI native DLL with safe named-state query + binder `dynamic_properties:['ExplicitTime']` passed native and23TS tests, ready for parent install. Then `dm_activate.py` applies four evaluator flags. Live flags still missing. StartDone92%capsule speed also exits start too early; replace after state/time capture. Existing graph dump confirms ShouldMove includes acceleration, so stop enters on input release.

Evidence/helpers: `Saved/CharacterShots/sleep_side/20261108_015347/` proves culling. Screwdriver frames `Saved/AnimShots/dm_live/20261107_204118/ScreenShot00765.png`,00772,00780 show grip but unexplained extra silver diagonal needs diagnosis. `wakeup/capture_wake_contact.py` is a read-only30Hz observer for coordinator-owned actual wake: logs real sequence seconds, source+Teen bones, cloth and actual camera/focal/aperture; never controls PIE or camera. Run alongside parent proof after PIE starts; writes `Saved/AnimShots/wake_contact_live.json`.

Do not treat `dm_smoke_latest.json` from20:41 as DM success: screwdriver override formerly overwrote it. Runner now names result after the actual proof script. Latest distance matching result remains failing until new codec/dynamic flags are applied and observed.

## 2026-11-07 20:24 normalization applied

Character reimported all seven Teen meshes in centimetres, reference scale1, headZ171.702cm, Head52morphs and correct head bone. Rebuilt IK_FoA_Teen/RTG_Mannequin_to_Teen; refreshed inventory and hand frame; applied grip translation(-2.119,-6.682,.222)cm scale1; rebuilt face_mask publisher from normalized head frame. BP compile0errors/0warnings. `verify_dm_assets.py` passed all four evaluators, correct SetupStartDM/UpdateStartDM/UpdateStopDM and monotonic Distance curves. Evidence `Saved/AnimShots/dm_asset_verified.json`. No-shot smoke remains scheduled20:30, sleep20:30:45, screwdriver20:31:15, parent actualwake20:31:45. Do not claim visual integration or remove MH before proof.

# Anim lane: continuation (2026-11-07 20:02)

### 20:12 verification update

The20:10 no-screenshot PIE smoke exited cleanly on an assertion: every runtime piece is Teen, the source class is ABP_FoAPlayer_C, and stencil4 is correct, but the retargeted head is at worldZ9208cm. Imported reference bones carry scale100. Character lane is correcting FBX centimetre units and reimporting all seven meshes with skeleton reference-pose update; **do not mark swap complete or delete MH yet**. After import, rerun build_teen_rig.py, probe_teen_runtime.py, teen_hand_frame.py, calibrate_teen_grip.py, apply_teen_grip.py and teen_runtime_graphs.py face_mask. Face/grip builders now derive local scaling from the real imported bone frame. Grip orientation uses homologous finger/thumb axes and the weighted Teen palm centroid. Tool, lie/slap and visual movement proof remain required.

The two empty groom components now also have empty OverrideMaterials. Starter legs/socks join sand overlay/capture, and boots trigger coverage refresh. Head preview soft property is unavailable in live reflection; external-reference audit determines any remaining dependency.

- LS_WakeUp clock/audio rebuilt and read back: Ring 2.30–25.2667 then zero25.30; dissolve25.30–26.50; both clock loops stop25.30. `Saved/AnimShots/wake_timing_verified.json`.
- Restart6 distance-matching functions SetupStartDM/UpdateStartDM/UpdateStopDM are bound; Start/Stop transitions and capsule-distance/braking prediction are live. Compiles clean. Runtime movement proof still pending.
- MPFB Teen now assigned to BP_FoAPlayer Body/Face and all garments. Existing ABP_FoAPlayer_MH class retained for IK API casts, with Teen skeleton and RTG_Mannequin_to_Teen. New ABP_FoA_TeenHead uses CopyPose and ARKit curves. Head stencil4 and measured head-local face-mask publisher retained. Starter Polo/Pants/Socks follows Body; equipped matching garments replace starter layers; suit resets reference Teen Body. Groom/binding references explicitly cleared, old assets retained pending proof/deletion gate.
- SetCinematic(false) now explicitly restores the source ABP_FoAPlayer class before publishing state. This is not yet runtime-proven; the Python wrapper type AnimInstance alone does not prove a missing generated class.
- All changed graphs compile/save without errors. `foa_qa.py logs` after recovery: no BP errors, Accessed None, or ensures; pre-existing repeated warning categories remain.
- Never invoke private `GetCurrentStateName(0)` through Python call_method: an unvalidated machine index crashed the editor at19:52. Removed from anim_pie.py. Coordinator owns restart; Hayba safe typed inspection follow-up requested.
- Proof runner `run_dm_proof.py` is bounded40s and runs walk/jog/stop then Suit equip. Uses public properties only. Next run waits for coordinator's clear PIE slot (UI stalled20:00). No anim lease held.

## Prior handoff (2026-11-07 16:20)

Owner id `anim`. The lane writes to:
- Content/FoA/Characters/Player/**
- Content/FoA/Cinematics/WakeUp/** and LS_WakeUp (handed to anim at 16:10; there is no cine lane any more)
- Tools/Unreal/player/**, Tools/Unreal/wakeup/**, Tools/Unreal/cine/**
- Saved/AnimShots/**
- docs/design/anim/**

No editor lease is held, and every asset is compiled and saved. `foa_qa.py logs` shows 0 BP errors, 0 Accessed None and 0 ensures.

## Done and proven in PIE

### 1. Screwdriver hand (main accepted the v3 close-up)
- The proof GIFs are Saved/AnimShots/screw_v3_{game,close,side,kneel}.gif and screw_before_*.gif. The sheets are in Saved/AnimShots/screwdriver/.
- **Grip.** `AS_FoA_Grip_Tool_R` (Anims/Hands) is a power-grip finger pose on the Manny. It is layered onto the finger branches in ABP_FoAPlayer with **GripWeight** and reaches the visible body through the retarget finger chains.
- **Components.** `HeldToolGrip` (scene) and `HeldTool` (static mesh) are on BP_FoAPlayer.
  - SetHeldTool attaches the grip to Body at hand_r.
  - The grip frame is the **ToolGripOffset** CDO default: (-8.26, 3, 1.87) with pitch 20, yaw 180, set for the MetaHuman hand_r.
  - The tool tip sits 16 cm out along the grip axis.
- **SetHeldTool(Mesh, MeshTransform, bShow)** is the new API. BP_Door's BeginDoorTool and RestoreDoorTool call it, with main's approval, and it is documented in docs/mechanics/contract.md.
- **Hand placement.** In tool mode, `SetToolHandRotation` places the hand from the tool frame through the inverse grip offset.
  - The wrist ratchets: each 90° of turn twists -45° to +45° with the tool, then the hand regrips while the tool stays still and the fingers ease.
  - ABP_FoAPlayer_MH has a "Hold the tool" REPLACE world-rotation node on hand_r (HeldToolRotation / HeldToolWeight), placed after the two-bone IK.
- **Kneel.** `AS_FoA_Kneel_Work` is UAL_Fixing_Kneeling with the torso upright, so his head clears the door. AM_FoA_KneelScrewdriver plays it, with times unchanged.
- **Scripts:** bake_tool_grip.py, build_held_tool.py, held_tool_graphs.py (Hayba batches), bake_kneel_work.py, tune_tool_pole.py and pie_screwdriver.py.
- **Open problems:**
  - The forearm rises from a low elbow.
  - The left hand does nothing yet; it should brace on the door.
  - The kneel-in is a 0.3 s blend.
  - The shipped ToolCamera sits on his left.

### 2. GASP locomotion, phase A (main accepted)
- **Clips.** 25 GASP "Relaxed" clips live in Anims/GASP (32 MB). They have sync markers, AN_FoA_FootPlant footsteps and Distance curves on the starts and stops.
  - The pick is in `gasp_scan.py --fixed`. The staging copy and the GASP-only retarget rigs are deleted; `gasp_unstage.py` re-checks them.
- **Walk / Run** blends the relaxed walk and jog by IsJogging in the Loco sync group. WalkPlayRate is speed / 170 and JogPlayRate is speed / 386, both clamped 0.5 to 1.
- **Idle** is the GASP relaxed idle plus six breaks.
- **Movement:** acceleration 300, braking decel 200, separate braking friction 0.6.
- Proof: Saved/AnimShots/gasp_v1_{loco,idle}_small.gif.

### 3. Turn in place (main accepted)
- RootYawOffset feeds Rotate Root Bone. The Turn state blends the four GASP turns by TurnIndex.
- `UpdateTurnInPlace` runs from the update. It un-blends the TurnYaw curve by TurnYawWeight, both baked by bake_turn_curves.py.
- Proof: Saved/AnimShots/turn_v2_small.gif.
- Scripts: dm_graphs.py turn, dm_states.py turn|turnpins|rules.

### 4. Tired layer
- `AS_FoA_Add_Tired` (bake_tired.py) is a local additive applied at TiredWeight 0.7 after Rotate Root Bone.

### 5. Direction doc
- docs/design/anim/animation_direction.md lists every player animation, with its intent, timing and source. Section 5 is the user's download and recording list.

## Built but not live

**Distance-matched Start and Stop states.** They exist in Locomotion with GASP evaluators, but are **unbound and have no transitions**.
- They need Hayba restart 6 from the hayba lane (ab73f962382a0c264): thread-safe anim node functions with a const-ref signature, plus a binder.
- The functions SetupStart, UpdateStart and UpdateStop are already built (dm_graphs.py functions).
- Don't flip thread-safe metadata from Python; main forbids it.
- **Next once restart 6 is in:**
  1. Remake the three functions thread-safe.
  2. Bind them with dm_states.py states, or with the new binder.
  3. Add the transitions:
     - Idle→Start (ShouldMove);
     - Start→Walk/Run (StartDone);
     - Start/Walk→Stop (!ShouldMove);
     - Stop→Start (ShouldMove);
     - Stop→Idle (auto).
  4. Compute DisplacementSinceLastUpdate (GroundSpeed × dt) and StopDistance (PredictGroundMovementStopLocation) in the update.
- **If it breaks:** dm_unbind.py clears the bindings so the ABP compiles.

## In progress at the stop: wake-up (taken over at 16:10)

### The user's notes
- "The laid down animation is broken."
- "The alarm needs to vibrate on the table and shake and you need to hit it from the top, but as you hit it it crumbles into sand that stays on that table."

### Diagnosis
- In Saved/CharacterShots/sleep_side/20261107_033151/full_body_side.png the body floats, the knees are up in the air and the feet are off the duvet.
- The cause is the leg IK targets in Tools/Unreal/wakeup/build_lying.py.
  - It lifts the knees to z 15-21 and pushes the hands to z -8, in the clip space of UAL_LayToIdle frame 0 (stick plot: Saved/WakeUp/lying_sticks.png).
  - The pelvis placement is right: the pelvis joint is 14 cm over a duvet top of 62.1.

### Duvet profile along the bed (x, z)
(190, 61.5) (210, 64.6) (230, 62.9) (250, 62.0) (270, 62.1) (290, 66.1) (310, 64.8) (330, 77.0) (350, 77.0)

The pillow is about 77 at the head end.

### Exact next step: rebake the lying pose in build_lying.py
Clip space has the duvet at z ≈ -9.4 and the pelvis at 4.6.
- Legs: almost straight, with a 10° knee bend. Knee and ankle joints at about -2.4, heels on the duvet.
- Spine: stays at about 3.
- Head: on the pillow. Neck flexion lifts the head joint to about 12 cm with the chin tucked. The face points up and about 15° toward the feet, so the neck is no longer cranked.
- Arms: one hand on the stomach (about z 16 over spine_01/02), the other arm alongside at -6.
- Keep the existing breath.

Then:
1. Run `FOA_AREAS=Cinematics python Tools/Unreal/ue_remote.py Tools/Unreal/wakeup/build_lying.py`.
2. Rebuild the placement with build_anims.py FOA_SLAP=1. Its slap contact is at 25.30 s (24.6 + 0.70).
3. Rebuild LS_WakeUp with build_ls_wakeup.py.
4. Check the result with a PIE side photo (pie_sleep_side_photo.py) or an MRQ draft.

### Agreed with the world lane (a6e8fd667f2e9b4ca), which owns the clock VFX
- The clock is SandClock_WakeUp (BP_SandMaterialize) at (325, -92, 80). The lid is the actor location plus 16 cm, with no socket.
- **Contact is 25.30 s (frame 759), in shot 6.** It is the seated, top-down palm slap (edge_clip slap mode).
- The anim lane keys these in build_ls_wakeup.py (not done yet):
  - **Ring:** 1 from 2.30 to 25.27, then 0 at 25.30. The world lane adds the property with SetRing.
  - **DissolveAmount:** 0 at 25.30, 1 at 26.50. It is currently keyed 25.4 to 26.6.
- In wake_cues.cues_v3, both the alarm bell loop and the tick loop must run 2.3 → 25.30 and stop dead at contact. The bell currently fades 7.4-9.0.
- The pile stays on the nightstand; the world lane builds that.

## Next jobs after the wake-up
- **Interaction pass.** Hand IK onto the real handles: the drawer, the door knob rattle, and a key pinch grip like the screwdriver's.
  - The baseline capture is Saved/AnimShots/interact_before_* and has not been reviewed yet.
  - The hook is BP_FoAPlayer's LockForInteraction(Seconds, Target). Bind the ABP's OnPlayMontageNotifyBegin (Grip/Grab/Rattle) to SetToolHandTarget.
- **MPFB2 teen body** (character lane ade3871a27adfb9b2), arriving in /Game/FoA/Characters/Teen.
  - Its hand_r: +Y runs to the fingers, the palm is about (-0.6, 0, 0.8) in local X/Z, and the root is renamed "root".
  - Retune ToolGripOffset and the foot IK offsets when it lands. The head uses ABP_FoA_TeenHead, a Copy Pose plus ARKit curves.

## Notes and gotchas
- Hayba graph batches don't roll back on failure. held_tool_graphs.Batch.run removes the refs and relinks the cuts, but auto-inserted conversion nodes and comments can be left behind. Run clean_graph_orphans.py on the graph afterwards.
- Pure BP nodes re-evaluate at each consumer. Run setters after all readers, as in UpdateTurnInPlace.
- Tools/Unreal/ui/pie_window.py is broken in 5.8 because LevelEditorPlaySettings is missing. Bursts run in the viewport, which is fine.
- record_anim.sh caps a burst at 45 s and ends PIE at once if the proof script fails. It runs `FOA_PIE_SCRIPT=<script>` with FOA_PLAN set to full, loco, idle, turn or interact.

## 2026-11-10 evening (Codex)

In progress. Checkpoint: `Saved/Codex/anim_hands_report.md`. No final visual acceptance yet.
- Key BeginGrip now follows SetDoorToolPresentation; PIE Body is `(328.0689, 23.0, 3.0944)`, as intended. BP_Door was patched in place.
- Replay fixed: `hand_twin.pose_from_ue_local(..., translations)` and `replay_pie_grip.py` preserve the animated pelvis translation. The old replay falsely showed a gap because it discarded the kneel's 56 cm pelvis offset. Replay asserts the PIE wrist round-trip within 0.1 mm; measured 0.0004 mm. Key contact: index 1.27 mm, thumb 1.77 mm.
- Actual key posture still failed: old montage shoulder placement caused wrist 99.51 deg / elbow 32.89 deg. Existing Key grip clip and layer now carry the twin stance from pelvis, with the root displacement reconstructed and self-checked against the solved hand. Pending PIE proof. UpdateGrip's elbow pole is now shoulder-relative, matching the key twin.
- Phone PID 10488 was stopped after its log stalled at round 0 and a self-test proved the evaluator depended on its prior finger pose. Resetting digits before palm seating fixes that; cold/cached equality self-test passes. Offline thumb variants are still being judged; none applied. No force-baked failures.
- Newer screw-0 solve was already passing at 17:59 (wrist 17.9, inline 17.6). Screw 2 now passes (wrist 17.5, inline 19.4, clearance 1.88 mm). Screws 1/3 still refining. No screwdriver integration yet.
- Key driver JSON Name serialization fixed; guarded run `key_grip/20261110_182102` completed in 31 s. Filename-form Shot produced no images, so a bounded plain-Shot collector is being tested. Runner renews EXCLUSIVE at 20 s and checks ownership before END.
- Latest native compile/save of BP_FoAPlayer, ABP_FoAPlayer_MH and BP_Door: 0/0, saves verified. Never saved the level or committed.

19:06 Codex re-aim: coordinator stopped the previous Blender searches. Latest user report is dorsal (outer) left hand against the phone. Twin replay/readback through its own conversion is insufficient. Pending independent UE CPU-skin diagnosis and real third-person views, implemented in hand_engine_probe.py / pie_phone_flip.py and queued through record_anim.sh. No speculative left quaternion flip or new phone bake applied. Key sheet still has a twin side view and must be replaced with real PIE third-person evidence; screwdriver remains unintegrated. Report: Saved/Codex/anim_hands_report.md.

- **Note from main (11-10 19:40):** `Tools/Unreal/ui/bp_graph.py compile_save` now compiles in-process and saves only if `bp.status` is up to date; a failed compile prints "NOT SAVED: compile failed" and raises RuntimeError (a clean compile still saves, so the contract holds). The door task light (world) waits on the key stand fix: the key grip is live in BP_Door, but the player still kneels at the old spot.

19:35 Codex: native UE diagnosis is Saved/AnimShots/review/phone_flip_diagnosis.{png,json}; skin fixture agrees with actual UE within 0.000288 mm. Four finger curl signs are correct; thumb free-aim construction hyperextends (local +Z versus measured palmward mostly -Z). Shared thumb_chain now uses constrained palmward hinges, with left/right regression test. Native phone candidate clears skin by 1.184 mm and faces palm 26.945 deg; thumb gap 1.470 mm / tap 0.500 mm. Not yet applied or visually accepted: main:MAINTENANCE user replay blocks the queued asset bake. Existing phone asset is still 16:41. Full checkpoint in Saved/Codex/anim_hands_report.md. New right-hand native probe is prepared in pie_key_grip.py for after phone acceptance; screwdriver still pending. Do not trust the old twin side sheet as final evidence.

### 2026-11-10 evening (Codex), 20:02 blocked checkpoint

Two consecutive 900-second asset-lease waits ended behind main:MAINTENANCE user replay. Apply queue ended without a lease; no editor action during replay. Phone asset still has its 16:41:59 bake. The new candidate is NOT in game and NOT visually accepted.

Read Saved/Codex/anim_hands_report.md for the complete state and resume order. Native UE proof is Saved/AnimShots/review/phone_flip_diagnosis.{png,json}: palm 68.656 degrees off the required facing, screen 0.379 degrees, four finger curls palmward but thumb curl moves away by 0.927 cm. Captured UE skin also shows index/middle/ring 8.645/17.710/8.121 mm off the nominal phone box. The independent anatomical plane selects the same palm patch. No blanket left quaternion flip was made.

Shared thumb_chain now constrains hinges to palmward flexion; phone builder uses it. Native skin fixture calibration error is at most 0.000288 mm. phone_native_solution.json and phone_grip_solution.json contain the prepared replacement: palm 26.945 degrees, minimum nominal-box clearance 1.184 mm, thumb pad 1.470 mm / tap 0.500 mm, all four fingertips beyond the far edge. Old input is review/phone_before_native_solution.json. bake_phone_grip.py now validates and bakes only; its obsolete offline solver was removed. Unit regression and native baseline tests passed. The thumb base is near the 85-degree gate, so visual review remains essential.

When replay ends, take an owned Characters lease, bake_phone_grip.py via ue_remote, phone_hold_attach_graphs.py --defaults-only, compile/save 0/0, release. Then guarded record_anim.sh with FOA_PIE_SCRIPT=Tools/Unreal/player/pie_phone_flip.py and FOA_HAND_TAG=phone_flip_after. New proof includes both hinges, thumb-pad normal, a real temporary reversed-phone control, and actual side/base-color diagnostic views; these additions have not run yet. Build phone_vs_reference.png only from real PIE evidence. Then pie_key_grip.py's prepared native right-hand probe and the screwdriver. Existing key_vs_reference.png still uses a twin side and is not final acceptance. Screwdriver remains unintegrated; screw 1 still has the unresolved butt-clearance constraint.

Lighting severely overexposes the hand and was left alone. No lease, driver, queued apply chain or Blender job remains. No level save, player-save manipulation or commit. No grip is marked accepted.

20:25 Codex resumed checkpoint: the corrected native phone is now actually baked (AS_FoA_Grip_Phone_L saved 20:15:18), and PhoneAttachOffset / PhoneHandInEye / PhoneElbowInEye applied to BP_FoAPlayer (saved 20:17:03). Native compile returned 0/0 and save verified. Released the Characters lease. The apply script's nested lease queued behind another lane; stopped only its owned child PID, released, fixed it to reuse a covering parent lease, and successfully retried.

A NEW main:MAINTENANCE user play hold appeared around 20:18, before the 20:20 proof window. The guarded phone after-proof is queued and has not started PIE. No post-bake engine or visual acceptance yet. Native probe now includes actual object-triangle distances and direct joint-angle gates; test_finger_limits.py passes, old phone fails, new hold/tap pass. Key probe now records the actual Body stand, native curl/contact/joint failures and actual side images; it no longer labels measurements as passed. Existing pie_screwdriver.py is an obsolete unguarded driver and must not be run (record_anim.sh refuses it); replace its lifecycle/QA context before screwdriver proof.
20:35: new user-play hold cleared. Corrected phone is already baked/applied; second guarded after-proof queue awaits 20:40 window. The earlier key pose predicts thumb hyperextension from its captured UE bone deltas (both thumb hinges outward), while the other four digits are inward; this is a bone-plane prediction pending actual right-hand skin proof.
21:08 Codex: actual phone proof completed at 20:41 (32 s) and 21:06 (25 s), preflights clean (71/75 assets), guards done and leases released. Corrected palm ~31.2 deg, screen 2.7-3.5 deg, actual thumb pad 1.365 mm, all native captured-hold curl signs and joint limits pass. First run changed pose during later measurements; repeat hold-state timeline stayed fully held and tap passed. Actual triangle contacts exposed middle/ring/pinky ~3.9-4.0 mm gaps; nominal box was insufficient. Exported native phone surface to review/phone_surface.json. Refined only those three fingers to 2.000 mm and improved elbow pole: wrist 44.45 -> 31.57 deg with unchanged hand/finger world positions before contact refinement. Refined phone is now baked/applied, BP_FoAPlayer compile 0/0 and saved, released. Next guarded proof queued for 21:10 with TAG=phone_surface_after. No final acceptance yet. Hand lighting is overexposed; temporary capture now has room Lumen and the far-edge side angle, without changing lighting assets. Native probe uses actual triangle distances for pass/fail; nominal box retained only as a labelled diagnostic. Main report has details. Key native proof and screwdriver still pending.

### 2026-11-10 evening (Codex), 21:33 checkpoint
Phone now applied and native numerical acceptance passes: palm 31.1549 deg, screen under 2 deg, actual contacts index 1.394 / middle-ring-pinky 2.000 / thumb 1.365 mm; all ten native hinge signs and joint limits pass. Tap 0.917 mm, thumb pad normal 33.943 deg; flipped-phone control 179.981 deg. phone_vs_reference.png uses real PIE FP and side. Normal room skin lighting is clipped white in places; review-only exposure was restored. BP_FoAPlayer compile 0/0 saved; last guarded burst ended/released.
Key native proof 21:23 confirms fixed stand (328.068889,23,3.09445) and contact, but both thumb hinges are outward (-0.739 / -0.154 cm); other fingers pass. key_flip_diagnosis.json and right-hand fixture/surface are the evidence. Native thumb fit in progress, no failing candidate baked. key_back.png is blocked by geometry; replace its angle. Old key_vs_reference.png is not accepted. Screw 1 offline fine solve restarted as owned Blender PID 52112; other screwdriver work remains pending. Full current report: Saved/Codex/anim_hands_report.md.

22:08 Codex: Key final native proof passes (key_grip/20261110_220028). Stand exact, index 1.28974 mm, actual thumb pad 1.59949 mm, all ten hinge signs inward, all joint limits pass; wrist 26.88 seated, 20.53 turning. New thumb MCP/IP 52.75/15.90 puts pad on bow. ABPMH compile/save clean, 77-asset preflight, 36 s PIE, guard done/released. key_vs_reference.png now uses actual PIE FP/side; reference/PIE crops are literal. Skin highlights overexposed, lighting untouched. pie_pose_capture now uses named Shot outputs, tested for stale/fresh handling, avoiding a shared numbered-file race. Driver inventory setup now reads the player's component directly; retry completed.
Screwdriver unintegrated. Static screw 1 now only fails butt support 0.99 cm vs 1 cm, all contacts <=2.96 mm/wrist19.9. Last owned Blender16232 finished; no owned Blender left. Guarded screwdriver baseline queued. New pie_screwdriver.py delegates to the shared proof_guard/QA driver; never run its old unguarded form. Runtime mesh size23cm vs raw20.90445cm and wide-sweep wrist violations remain to fix. screw_runtime.py is an unapplied gated experiment, not acceptance. See anim_hands_report.md.

### 2026-11-10 evening (Codex), 23:18 blocked checkpoint

Phone and key are applied and pass native UE checks; final phone_vs_reference.png and key_vs_reference.png use actual PIE first-person and side frames. Normal room skin highlights remain clipped; lighting untouched. Phone palm31.1549deg, screen<2deg, contacts1.365–2.000mm, tap.917mm, all native hinge signs/joint limits pass. Key stand(328.068889,23,3.094448), index1.28974mm/thumb-pad1.59949mm, all hinge signs/joints pass; wrist26.88 seated/20.5 captured turn. Key bound capture is a ~22.18deg phase transition, not a proven full45deg turn.

Screwdriver remains UNAPPLIED. Actual UE baseline wrist60.89deg, penetration11.80mm, runtime size23cm vs actual20.90445cm. All four twin statics now pass, but native checks caught screw2 thumb-base98.11deg and contact gaps up to5.35mm. New native_solution files fix all four: skin gaps1.600–2.021mm, joint/curl gates pass. screw_turn_native.py builds31-frame shoulder-following ratchet clips with planted feet/pelvis: max wrist/inline17.50/17.99/18.03/18.70deg; interpolated worst18.7015, target error<.01mm. These are offline predictions, not engine acceptance.

The editor closed during the queued bake (by23:11 absent; final log23:10 Hayba64-connection limit/audio timeout). No screwdriver bake log or Content asset exists. Stopped only own pending bake tree64524, children54708/39136; release says not held. No active anim job/driver/queue. Never relaunched editor, saved level or touched player save. No commit.

Exact resume chain, paths, limitations and tests are in Saved/Codex/anim_hands_report.md. bake_grips.py now includes the four native motion files; right_grip_layer.py drives time and reuses the phone clip's neutral right fingers for regrip; new screw_grip_graphs.py commands ensure/apply/update/hooks are prepared but NOT RUN. Do not call the integration shipped until UE compile0/0 and all-four guarded proofs pass. test_screw_native.py passed native and mid-frame gates plus five graph batches' endpoint checks. The original failed screw_runtime.py experiment has been superseded by screw_turn_native.py. The screwdriver reference sheet is still missing; full rotated-handle contact/regrip and torso clearance remain unverified.

23:17 follow-up: coordinator relaunched editor PID62652 at23:12:38, but main:MAINTENANCE content cleanup remains and Hayba refuses connections. Anim has no queued bake/proof; wait for normal lease availability. Editor absence in the preceding checkpoint describes the failure at23:11, not the current state.

### 2026-11-11 afternoon (Codex), UE5.9 resume14:36

5.9 sanity passed (review/ue59_sanity.json), no API changes found; startup PSP hotfix ok. Four screwdriver clips baked/saved14:27; ABP_FoAPlayer_MH layers compiled/saved. Runtime integration still queued behind a NEW main:MAINTENANCE hayba5.9 install hold from14:28, root56444. No PIE since restart. Updated full-turn driver FOA_FULL_TURN=1 and invalid-world/actor guard; offline guard test passes.

Quarter-turn actual-mesh check caught screw2 ring clearance.980mm at90/270deg. Relaxed MCP.3deg, nowmin1.221mm. Native source/31turnframes/manifest updated and tests pass, but MUST rebake Screwdriver2 before PIE (currentasset14:27 predates this correction). Then finish screw_grip_graphs ensure/apply/update/hooks underlease, actualallfourfullturnproofs, full-range key withmandatoryreversal, and finalreference sheets. Mainreporthas exactstate.

### 2026-11-11 afternoon (Codex), 14:55 revised diagnosis / maintenance

New main:MAINTENANCE hayba5.9 install hold appeared14:28 afterGO; editor exited14:30:08. Graph acquire timed out900s without editing Player/Door. No anim jobs, queues, holds or drivers remain.5.9 sanity passed, APIs present and PSP hotfix ok; four Screwdriver clips+MH layers actually baked/compiled/saved14:27, but those clips are now STALE and must all be rebaked.

Critical correction to earlier acceptance: actual prior UE phone/key poses have83.2055/-108.7616deg axial wrist twist. Palm/finger/contact checks did not catch that. Evidence review/wrist_twist_diagnosis.json. Shared Hand.untwist_forearm now moves axial rotation into the forearm without moving the hand target; used by phone authoring, Key bake and all screwdriver frames. Bilateral90deg regression and native skin invariants pass. Native probe/proof gates now include axial wrist rotation<=20deg. Old phone/key sheets are prior evidence, not final acceptance.

Also fixed mirrored screwdriver column numbering: runtime source order1,0,3,2, planted Body XY310.316109,23 and identicalfeet acrossallscrews. AuthoringScrew2 ring MCP relaxed.3deg; quarter-turnmin1.221mm. Baked native skin20samples clears, closedcontacts1–3mm. Fullstroke interpolatedwrist/inline max18.705deg; sampledaxialtwist~0, handerror<.01mm. All correctedSaved data regenerated. Phone native/grip solution now untwisted and validated; Key manifest untwisted. NONE of these later corrections has been baked into UE yet.

Read Saved/Codex/anim_hands_report.md for exactre-bake/integration/proof order. Aftermaintenance: allfourScrewdriver clips again; screw_grip_graphs ensure/apply/update/hooks; guardedfullturnallfour; Key rebake+real fullrange reversal proof; phone shared-fix rebake+flip/tap/twist regression; replaceallsheets. New FOA_FULL_TURN=1 driver measures bend+twist per tick andactualskin atcheckpoints. Required0/0,graphcaptures,sceneviewsandfinalreference sheets remain pending. No commit,levelsave,playersaveedit or editorrelaunch byanim.

14:59: maintenance block has exceeded30min; editor stillclosed/Haybarefusing. Anim has no queued acquire, job, driver or lease. Current report is the authoritative resume state. Re-bake ALL four screwdriver clips, not only2; latest source includes forearm untwist AND column remap. Key/phone also require the new shared correction and fresh axial-twist proofs before final acceptance.
