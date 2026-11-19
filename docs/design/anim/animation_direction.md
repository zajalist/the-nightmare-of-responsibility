# Player animation direction

The Nightmare of Responsibility. Owner: anim lane. Last revised 2026-11-07.

This is the director's list of every player animation the game needs. For each one it gives the intent, the timing, the key poses and where the motion comes from. It is the brief for every clip we source, author or retarget, and the checklist main reviews against.

## 1. Who is moving

He is a heavy, tired teenager who does not want to do any of this. Every move has to show three things:

- **Weight.** His mass arrives late and settles late. The pelvis drops 2 to 4 cm into every plant, and heels and hips take the hit. When he stops, the body keeps travelling for 4 to 6 frames, then sinks back. He never stops dead on one frame.
- **Reluctance.** Each action starts late and finishes early. He hesitates for 0.15 to 0.4 s before reaching, takes the shortest path rather than the clean one, and drops his hands as soon as the job is done. He looks at a thing before he touches it.
- **Tiredness.** His shoulders roll forward and his head sits 5 to 10 degrees low. His arms hang a little behind the hips and his feet barely clear the floor. Blinks are slow and he sighs, more on a new day than on the first.

He is never robotic. Nothing moves at a constant speed, and nothing starts or stops on every limb at once: the hips lead, the shoulders follow 2 to 3 frames later and the head last. When a move ends, everything is still within 0.3 s. Nothing drifts or keeps cycling after it finishes.

The comparison to aim for is a person at 7 a.m. in a cold room, not an action hero.

## 2. Rules for every clip

| Rule | Value |
|---|---|
| Animation source skeleton | UE5 Mannequin (`SK_Mannequin`), the hidden `Mesh` on BP_FoAPlayer. Every clip lives on it. |
| Visible body | Retargeted at runtime (`ABP_FoAPlayer_MH`). Today that is the MetaHuman; next it is the MPFB2 game-rig body (character lane). Hand IK, foot IK and the tool grip run after the retarget, on the visible body. |
| Frame rate | 30 fps authored, root motion where the body travels |
| Blend in / out | 0.2 to 0.4 s; 0.3 s by default. Settles out at 0.4 to 0.5 s. |
| Feet | No sliding. Loops carry sync markers (L, R at mid-stance); starts and stops are distance matched; Stride Warping covers speed changes; foot IK plants on uneven ground. |
| End state | Within 0.3 s of a move ending every bone is at rest. No looping layer is left running. |
| Notifies | Gameplay contact frames are `AnimNotify_PlayMontageNotify` with the names in contract.md. Sand footsteps use `AN_FoA_FootPlant`. |
| Naming | `AS_FoA_<Group>_<Name>` for sequences, `AM_FoA_<Name>` for montages, `BS_FoA_<Name>` for blend spaces |
| Folder | `/Game/FoA/Characters/Player/Anims/<Group>/` |
| Budget | All player animation under 100 MB on disk, compressed |
| Licence | CC0, Epic content for UE projects, Mixamo, Rokoko free tier, Plask free tier or ActorCore free motions only. The source and licence of every clip are recorded in `Anims/SOURCES.md`. |

### Sources, in order of preference

1. **UAL** (Universal Animation Library, CC0). It is already in the project as `Anims/UAL/` and retargets cleanly.
2. **Game Animation Sample** (Epic, free for UE projects) at `P:\GameAnimationSample`. It supplies the locomotion: walk and jog loops, starts, stops, pivots, turn-in-place and idles.
3. **Mixamo** (free with an Adobe account; the clips may ship inside games). The user downloads them as FBX with no skin, at 30 fps.
4. **Rokoko Create** (text to motion, 5 free FBX exports a month). Use it for one-off actions that have no library clip.
5. **Plask** (video mocap, 15 s a day free). The user records a reference on a phone and we clean it up. Use it for the hero moments where the acting matters.
6. **iClone 8 / ActorCore** free motions, when a free pack has the move.
7. **Authored.** Control Rig keys in Sequencer, baked to an AnimSequence, or a pose baked from data, as in `bake_lying.py` and `bake_tool_grip.py`. Use it for poses, holds, additive layers and fixes.

### The "tired" layer

Most library motion is too upright and too eager. One additive pose, `AS_FoA_Add_Tired`, goes on top of locomotion and idles:

- spine_03 and spine_04 flex 4 degrees;
- the clavicles roll forward 3 degrees;
- neck_01 tilts down 5 degrees;
- the arms gain 2 degrees of internal rotation.

The layer is weighted 0.7 on day 1 and rises with the day count, up to 1.0. This is how a stock walk becomes his walk.

## 3. The list

Priority is **P0** for clips the game loop shows on every run, **P1** for clips the game loop shows once or that matter to judges, and **P2** for polish.

### 3.1 Wake-up (LS_WakeUp and the T0 hand-off)

The cinematic owns the camera. These clips are sequencer-driven on the pawn, and contact frames line up with cine's shot list in `docs/cinematics/wakeup_shotlist.md`.

| # | Clip | P | Intent | Timing | Key poses | Source plan |
|---|---|---|---|---|---|---|
| W1 | `AS_FoA_Wake_Sleep` | P0 | Deep asleep, at peace for the last time | 4 s breath loop | On his side facing the nightstand. The lower arm is under the pillow, the upper arm over the duvet, the knees drawn up and the neck in line with the spine (not cranked). | Authored: a lying pose baked from UAL_LayToIdle frame 0 with the neck fixed, then breathing (extends `bake_lying.py`). Mixamo "Sleeping Idle" as a reference. |
| W2 | `AS_FoA_Wake_Stir` | P0 | The alarm cuts in, and he refuses it | 1.8 s, once | A frown, the shoulder pulled up to the ear, the duvet tugged higher and his face pushed into the pillow. Breathing stops for 0.5 s, then a long exhale. | Plask: the user acts it in bed (10 s). Fallback: Rokoko "person in bed pulls blanket over head annoyed". |
| W3 | `AM_FoA_Wake_Slap` | P0 | He kills the alarm without looking | 1.6 s: reach 0.6, slap 0.15, hold 0.5, withdraw 0.35 | The arm swings out from under the duvet in an arc **over the top**, palm flat and fingers spread, and drops onto the clock from above. The wrist stays loose. At contact (notify `Slap`) the hand flattens and the elbow gives. He holds 0.5 s while the clock crumbles to sand under his palm, then drags the hand back through the sand pile. Two-bone IK puts the palm on the clock's top face (a clock socket), with the pole above the elbow. | Plask: the user slaps a phone on a bedside table from lying on his side. Authored fallback: Control Rig keys on the right arm over W1. The IK target is the clock actor, so the clock can be moved freely. |
| W4 | `AS_FoA_Wake_Lie_Awake` | P1 | Eyes open, staring, 2 s of "do I have to" | 2 s | W1 with the head turned 15 degrees to the ceiling. The eyes are open, with one slow blink. | Authored (W1 plus a head key; the face lane drives the blink). |
| W5 | `AM_FoA_Wake_SitUp` | P0 | Getting up costs him | 2.4 s | He rolls onto his back, the legs swing off the edge as a counterweight, he pushes up on the right forearm and then the hand. He ends seated on the edge, elbows on knees and head hanging, for a 0.8 s hold. | Mixamo "Getting Up From Bed" / "Sitting Up". UAL_LayToIdle's get-up portion is the current fallback. |
| W6 | `AM_FoA_Wake_Stand` | P0 | Up, heavy | 1.6 s | Both hands push on the knees, he stands in two stages (a pause at half height), and finishes with a small sway and a weight shift. It ends exactly on the idle's first frame so locomotion can blend in at 0.3 s. | Mixamo "Stand Up" (from a seated pose) or UAL_Sitting_Exit, slowed to 0.8 with the tired layer on top. |

**The clock (agreed with the world lane, 2026-11-07).** SandClock_WakeUp (BP_SandMaterialize) is keyed by LS_WakeUp:
- **Ring:** 1 from 2.30 s to 25.27 s, so it rattles and hops on the nightstand while the bell rings. It drops to 0 at contact.
- **Contact:** 25.30 s (frame 759). This is the top-down palm slap in shot 6, played seated at the bed edge (AS_FoA_Wake_EdgeReach, slap mode). The palm lands flat on the bell tops at 101 cm with 0.0 cm error.
- **DissolveAmount:** 0 → 1 from 25.30 to 26.50 s. The black pile it leaves **stays** on the nightstand.
- **Sound:** the bell and the tick stop dead at contact.

He ignores the alarm through the lying shots and the time shift, then sits and slaps it. W3 as written above (a slap while lying) is the alternative if the seated version doesn't read.

**Lying v2 (W1, AS_FoA_Wake_Lying, build_lying.py).** Every contact is solved against the traced bedding:
- heels on the duvet, with relaxed 12° knees;
- the right palm on his stomach, and the left arm loose at his hip;
- the head lifted onto the pillow, the face up and 14° toward his feet, and turned 12° to the nightstand.

The PIE measurement of the face direction is (-0.27, 0.20, 0.94) on the visible body.

### 3.2 Locomotion (ABP_FoAPlayer)

| # | Clip | P | Intent | Timing | Key poses | Source plan |
|---|---|---|---|---|---|---|
| L1 | Idle `AS_FoA_Idle` | P0 | Standing because he has to | 6 to 8 s loop | Weight on one leg, the hip dropped on the other side, arms hanging and the head a little low. Breathing is visible in the chest. | GASP neutral idle plus the tired layer. Now: UAL_Idle_Loop. |
| L2 | Idle breaks (4) `AS_FoA_Idle_Break_*` | P0 | Life in the stillness | 2.5 to 4 s each, one every 8 to 15 s, never the same twice in a row | Yawn with a stretch; rub the eyes with the heel of a hand; neck roll; shift weight and scratch the back of the head. | GASP idle breaks where they fit. Rokoko for "yawn and stretch", Mixamo "Tired" / "Rubbing Eyes". Plays through the existing random sequence player. |
| L3 | Walk loop `AS_FoA_Walk` | P0 | Shuffling, heavy | about 115 cm/s, a 1.1 s cycle | Short stride, feet low, heel strike soft, arm swing small and late. The torso bobs 2 to 3 cm. | GASP M_Neutral walk loop at 0.9 play rate, stride-warped, plus the tired layer. |
| L4 | Jog loop `AS_FoA_Jog` | P1 | Reluctant hurry | about 260 cm/s | A heavy heel-to-toe shuffle-jog with elbows bent at 90 and the head still low. It looks like effort. | GASP jog or run loop with stride warping down to 260 cm/s, plus the tired layer. |
| L5 | Walk starts (F, L90, R90, L180, R180) | P0 | He decides, then goes | 0.6 to 0.9 s | Lean, a first heavy step, then into the cycle. Turning starts lead with the head and the hips follow. | GASP walk starts, distance matched (the `Distance` curve, gasp_retarget.py `post`). |
| L6 | Walk stops | P0 | He runs out of reasons | 0.7 s | The last step lands short and the body overshoots 2 cm, then settles back onto both feet. | GASP walk stops, distance matched to the predicted stop point. |
| L7 | Pivots (L, R) | P1 | Change of mind | 0.6 s | A plant on the outside foot, then the hips swing round. | GASP walk pivots. |
| L8 | Turn in place (L/R 90, L/R 180) | P0 | Turning to look at something | 0.8 s for 90, 1.2 s for 180 | The head leads, then the shoulders, then the feet in two small steps. | GASP turn in place, triggered when the control yaw exceeds 60 degrees from the root while idle. |
| L9 | Jog start and stop | P2 | | | | GASP. |

The motion model is a speed-driven state machine with distance-matched starts and stops, plus turn-in-place on the root yaw offset. GASP's motion-matching database is too heavy for this budget, so we use its clips, not its Pose Search setup.

### 3.3 Interactions (montages on `DefaultSlot`, through BPI_InteractionHost)

Shared direction: look first (head look-at onto the target, 0.2 s), reach second, contact on the notify, release early. Hand contact uses two-bone IK on the visible body (`ToolHandTarget` / `ToolElbowTarget`). The finger pose comes from a layered grip pose on the source (`GripWeight`).

| # | Montage | P | Intent | Timing | Key poses | Source plan |
|---|---|---|---|---|---|---|
| I1 | `AM_FoA_OpenDrawer` (desk, commode) | P0 | Search without hope | 1.6 s (Grip at 0.55, Pull at 0.9) | A slight crouch to the handle height, four fingers hooked under the handle, a pull from the hips (not the arm), then a lean in to look. | UAL_Interact now. Better: Mixamo "Opening A Drawer" or "Searching Files High/Low", with hand IK on the drawer pull. |
| I2 | `AM_FoA_TryLockedHandle` | P0 | Disbelief, then it is locked | 2.4 s | Grip the lever, push down, two rattles (the second harder), stop, the head drops, a sigh. | UAL_Interact plus UAL_Idle_No_Loop (current). Better: Plask, the user rattling a real handle. |
| I3 | `AM_FoA_PickUp_Table` | P0 | Take it, do not admire it | 1.2 s at 0.75 rate | Reach, close the fingers on the notify, bring it to the hip, not the chest. | UAL_PickUp_Table (current). |
| I4 | `AM_FoA_PickUp_Floor` (boot key, hanger) | P0 | Bending costs him | 2.0 s | A hip hinge plus a knee bend, the free hand on the knee for support, a grunt at the bottom. | UAL_Farm_Harvest at 0.9 (current), or Mixamo "Picking Up Object". |
| I5 | `AM_FoA_LookInBoot` | P1 | A reluctant peek | 2.2 s | Crouch, tip the boot with one hand, look in, shake it, the key drops into the palm (notify `Grab`). | Rokoko "crouch, pick up a boot, shake it, look inside". Fallback: UAL_Crouch_Idle plus hand IK. |
| I6 | Key in the lock (`AM_FoA_TryLockedHandle` contact, door tool Key mode) | P0 | Careful, then forcing | live, input driven | A pinch grip on the key bow, the forearm in line with the key, the wrist rotating up to 45 degrees. Pressure shows in the shoulders. At the snap, the hand jerks back 3 cm and he looks at the stub. | The door tool's Key mode with hand IK. Add a key-pinch pose (`AS_FoA_Grip_Key_R`) the way the screwdriver grip is made. |
| I7 | **Screwdriver** (door tool Screwdriver mode, `AM_FoA_KneelScrewdriver`) | P0 | Methodical, his one competent moment | kneel 0.45 s in, live turning, 1.2 s out | He kneels on the right knee, the left forearm rests on the left knee, the left hand braces on the door. The screwdriver sits in a closed right fist, butt in the palm and shaft along the forearm. The tip stays on the screw. **Turning is a ratchet:** each 90 degrees of input twists the wrist from -45 to +45 with the tool, then the hand regrips (wrist back, tool still, fingers ease). Between screws the hand moves to the next screw over 0.25 s. | **Done 2026-11-07** (`build_held_tool.py`, `held_tool_graphs.py`, `bake_tool_grip.py`). Next: replace UAL_Fixing_Kneeling's kneel-in with a Rokoko "kneel down in front of a door, brace with the left hand", and add a left-hand brace IK onto the door. |
| I8 | `AM_FoA_UseHanger` | P1 | Improvised, fiddly | 3 s loop | Untwist the hanger, feed the wire into the latch gap at chest height, wiggle with small wrist rotations, and lean the shoulder on the door. | Plask: the user mimes it at a door. The hand IK target is the latch point (the same API as the key). |
| I9 | Wardrobe (T6) | P0 | He pulls, it comes down on him | 1.2 s pull plus the cinematic | Both hands on the handle, then a backwards lean that turns into a flinch, the arms up across the face. The sand takes him at impact (director-owned). | Mixamo "Pulling" plus "Cover" or "Flinch". The flinch must land on the director's impact frame. |
| I10 | Boots on (`AM_FoA_PutOnBoots`) | P1 | A chore | 4 s for both | Sit on the bed edge, pull each boot on with both hands, stamp once to seat it. | Rokoko "sit and put on a boot", once per foot (two exports). Uses UAL_Sitting_Enter and Exit around it. |
| I11 | Phone (T0) | P0 | Dread: who is texting | 1.5 s to raise, a loop while reading, 0.8 s to lower | Pick it up from the nightstand, hold it at the chest with both thumbs on the screen and the head well down. The screen lights his face. | UAL_PickUp_Table to raise, then a held authored pose (`AS_FoA_Phone_Hold`) with hand IK onto the BP_Phone widget plane. Mixamo "Texting" for the loop. |
| I12 | Look / narrate (Look verb) | P2 | | 1 s | Head and eyes only, plus a small lean. | The look-at node only, no clip. |

### 3.4 Getting dressed (Equip)

Each garment is an `AM_FoA_Equip_<Id>` with a `Snap` notify where that layer becomes visible. Today all five share one chest jolt.

| # | Garment | P | Key poses | Source plan |
|---|---|---|---|---|
| D1 | Shirt (T7, T8 win) | P1 | Arms into the sleeves behind the back, then a shrug and a tug on the hem. Snap on the shrug. | Mixamo "Putting On Shirt" or Rokoko. |
| D2 | Trousers | P1 | Hop on one leg, pull up, a button tug. | Rokoko "put on pants standing, hopping". |
| D3 | Socks | P2 | A seated foot raise, pull. | Rokoko. |
| D4 | Tie | P2 | Loop it round the neck, tug it up, wince. | Rokoko "tie a necktie". |
| D5 | Suit (T9 payoff) | P1 | A jacket swing over the shoulders, then a slow straighten of the lapels, the one upright pose in the game. Hold it 1 s. | Mixamo "Putting On Jacket" plus an authored hold. |

The sand burst (BPL_SandFX) fires on `Snap`.

### 3.5 T8 battle (BP_Encounter, `SetBattle`)

It is turn based against garments. Reactions are short and readable from the battle camera.

| # | Clip | P | Intent | Key poses | Source plan |
|---|---|---|---|---|---|
| B1 | Battle idle | P1 | Dread, not a fighting stance | Feet planted, arms half raised, flinching every 3 s. | Current `build_battle_idle.py` plus a Mixamo "Nervous Idle". |
| B2 | Attack / grab (per move) | P1 | Clumsy effort | A lunge and grab, a pull, stumbling back. 1.2 s. | Mixamo "Grab" and "Pulling". |
| B3 | Dodge | P1 | Barely | A twist and a half step. 0.6 s. | Mixamo "Dodge". |
| B4 | Hit react (light, heavy) | P1 | The garment wins this one | Light: a head snap. Heavy: knocked back a step. | UAL_Hit_Chest, UAL_Hit_Head, UAL_Hit_Knockback (in project). |
| B5 | Victory | P1 | Relief, not triumph | Exhale, hands on the knees. 1.6 s. | Mixamo "Relieved Sigh" or authored. |
| B6 | Defeat | P1 | Collapse into sand | Knees give, falls forward to one hand. The sand takes him. | UAL_Death01 (in UAL1) slowed, with the sand transition on the director's frame. |

### 3.6 T10 walk-out

| # | Clip | P | Intent | Key poses | Source plan |
|---|---|---|---|---|---|
| E1 | Suit walk | P1 | Same body, lifted | The L3 walk with the tired layer at 0.2 and a longer stride, head level. This is the payoff for the whole game: the one time he walks like he means it. | GASP walk without the tired layer, 1.0 rate. |
| E2 | Threshold pause | P1 | One last look back | A stop in the doorway, a turn of the head over the right shoulder for 1.2 s, then on. | GASP stop plus a head look-at key, then a walk start. |

### 3.7 First person (the gameplay camera since 2026-11-08; the user confirmed it 2026-11-09)

The camera is his eyes: FollowCamera rides the Face `head` socket at the measured eye point, and Face, Hair and
Eyebrows hide whenever the view target is the pawn (UpdateFirstPersonVisibility). The body, polo, arms and legs stay
visible, so looking down shows him. Every animation above is now judged from inside his head as well as from
the cinematic cameras.

| Rule | How |
|---|---|
| Never enter the head on screen | Cinematics end on a cut or a blink to black, never a camera blend into the eyes. LS_WakeUp ends black and keys `bHandoffFadeIn`; SetCinematic(false) fades the head camera up over 0.6 s. |
| Look first, reach second | LockForInteraction remembers its Target; while the lock holds, the view eases onto it (RInterpTo 4.5), so the hands on the drawer, handle, key and screwdriver are in frame. |
| Weight on turns | The head camera rolls into a turn, at most 1.2 deg, eased; pitch and yaw stay exactly the input. Reduce Motion (MPC_Dream) turns it off. |
| Bob and breath | They come from the animation itself (the camera follows the head bone), so the GASP walk, stops and idle breathing drive them; nothing is faked on the camera. |
| First frame | The wake-up hands over facing into the room (control yaw 195, pitch -10): fireplace, moonbeams, the figure in the window. |

## 4. Production order

1. **Screwdriver hand (I7).** Done; the PIE proof is in `Saved/AnimShots/screw_*`.
2. **GASP locomotion** (L1 and L3 to L8). 25 "Relaxed" clips are retargeted (`Anims/GASP`, 32 MB).
   - Live: the relaxed walk and jog loops (marker-synced), the relaxed idle with six breaks, heavier acceleration and braking, and turn-in-place (RootYawOffset plus the GASP stand turns, `dm_graphs.py turn`).
   - Built but unbound: the distance-matched Start and Stop states. They wait for Hayba's thread-safe anim node functions (restart 6).
3. **The tired layer** (`AS_FoA_Add_Tired`, TiredWeight 0.7): live over locomotion and idle.
4. **Wake-up** (W1 to W6), with cine and look for the clock.
5. **Interactions** I1, I2, I4, I6 and I11 on hand IK, then I5, I8, I9 and I10 as clips arrive.
6. **Dressing**, then **battle**, then the **walk-out**.
7. **MPFB2 body:** re-point the runtime retarget at the new body and retune `ToolGripOffset` and the foot IK offsets. No clip changes, because every clip is on the Manny.

## 5. What the user needs to do

These are routed through main.

- **Mixamo** (Adobe account): download, without skin and at 30 fps, "Sleeping Idle", "Getting Up", "Stand Up", "Tired", "Rubbing Eyes", "Picking Up Object", "Opening A Drawer", "Putting On Shirt", "Putting On Jacket", "Pulling", "Flinch", "Nervous Idle", "Grab", "Dodge" and "Relieved Sigh".
- **Rokoko Create** (5 a month): the boot peek (I5), the kneel at the door (I7 in), boots on (I10), trousers (D2) and the tie (D4).
- **Plask** (15 s a day): record phone videos of the alarm slap from lying on your side (W3), the duvet refusal (W2), the handle rattle (I2) and the hanger at a door (I8). Shoot side-on, full body, in fixed light.

## 6. Proof and review

Each group ships with PIE GIFs from the game viewport (`Tools/Unreal/player/record_anim.sh`, with `FOA_PIE_SCRIPT` set for focused proofs) and `python Tools/QA/foa_qa.py logs` showing 0 Blueprint errors. Main reviews every frame. Captions say what is still wrong.
