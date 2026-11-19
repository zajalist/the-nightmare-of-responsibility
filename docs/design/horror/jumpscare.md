# The jumpscare (horror lane)

One jumpscare in the bedroom, once per run. Asset: `/Game/FoA/Gameplay/Jumpscare/BP_Jumpscare` (placed as
`FOA_Jumpscare`, outliner folder `Gameplay`). Builder: `Tools/Unreal/horror/build_jumpscare.py`.

## What the references do
The scares people remember share one shape: tension, a false calm, a close reveal on a sharp stinger, and a hard release.
- **P.T.** Long stretches of looping hallway and near-silence. When you turn back, Lisa is in your face for under a second, then the cut.
- **Resident Evil 7.** Slow, quiet exploration. The reveal lands right after a "safe" moment, close to the lens, on a layered hit.
- **Outlast.** Silence and breathing, then a lunge that fills the frame. Loud transient, camera shake, release into panic breathing.
- **Layers of Fear.** The room changes while you look away; the stinger fires as you turn back.

The lessons: earn it with quiet; drop the audio just before the hit so the hit has headroom; put the face at arm's length; hold
it only 0.4-0.8 s; then cut back to normal and let the player's own heartbeat be the tail. Use it once.

## When it fires
At **T5**, right after the key snaps in the door lock (KeySnapped). The player has just found the key and walked to the
door, believing the way out is open. The snap is the frustration beat. The quiet that follows, as they turn away from
the dead door to look for another way, is the earned moment.

## What triggers it
`BP_Jumpscare` owns its own trigger: a box `Zone` over the door approach (x 235 to 375, y -5 to 165). It never
calls into other lanes' Blueprints except their public API. A 0.2 s poll timer reads `BP_BeatDirector` through
`GetActorOfClass`: `BeatIndex`, `bRollingOver`, `bTopDown` and `bWardrobeTransition`. It also checks that the
player's own pawn is the view target, so it can't fire in LS_WakeUp, the phone push-in, the top-down view or the battle.

| Phase | Starts when | What happens |
|---|---|---|
| 0 Idle | | Nothing runs. No Tick. |
| 1 Dread | Beat T4 or T5, the player is in `Zone`, the beat is at least 1.5 s old | The room tone and wind duck to 30% over 3 s (`SMX_Jumpscare_Hush` on `SC_Ambience`). The tension bed fades in over 4 s. |
| 2 False calm | Beat T5, the beat is at least 2.5 s old, and the player leaves `Zone` (or 10 s pass) | The bed fades out in 0.6 s. The ambience stays ducked, so the room is too quiet. A random 1.2-1.9 s wait follows. |
| 3 Hit | End of the wait | The monster is in the player's face. See the choreography below. |
| 4 Release | 0.65 s after the hit | Hard cut: the monster is gone. A sand burst falls where it was. |
| 5 Done | | `bFired` stays true. |

If the beat leaves T4-T5, a rollover or top-down starts, or the view target changes before the hit, it cancels quietly. The
bed fades, the mix pops and it goes back to Idle, still armed. At T4, stepping out of `Zone` before the snap also cancels.

## Choreography (t = 0 at the hit, 60 fps frames)

| Time | Frame | Picture | Sound |
|---|---|---|---|
| -2.3 to -0.40 s | | The room, too quiet: ambience ducked, bed gone | Near silence, room tone at 30% |
| -0.40 s | -24 | | `SFX_Horror_Stinger_01` starts: its first 0.40 s is the riser (a reversed-cymbal swell under the scream's own growl-to-shriek crescendo) |
| 0 | 0 | The monster appears 95 cm in front of the lens, centre frame, keyed from below and rimmed from behind. Camera shake starts. FOV punches in by 12 deg. The frame is kept free of post-process noise so the face reads. | The stinger's hit: cinematic hit, sub boom, designed scream, real female scream and a creature growl, all on one sample |
| 0 to 0.12 s | 0-7 | It lunges from 95 cm to 38 cm (ease out): the skull face and raised claws fill the frame | |
| 0.12 to 0.65 s | 7-39 | It holds at 38 cm with a fast tremble (about 1.5 cm and 3 deg at 15-17 Hz). The shake decays. FOV eases back. | The shriek tail |
| 0.65 s | 39 | Hard cut: the monster is hidden in a single frame. `TriggerGlitchBurst(0.6, 0.2)` tears the frame, and a black-sand burst falls where its face was | The stinger rings out. The heartbeat-panic tail starts. |
| 0.65 to 1.5 s | | FOV back to normal by 1.5 s | The ambience returns over 4 s |

- **Camera shake** `CS_Jumpscare` (LegacyCameraShake): 0.55 s, no blend in, 0.35 s blend out. Rotation pitch 2.5 deg at 22 Hz, yaw 2 deg at 17 Hz, roll 4 deg at 9 Hz. Location 4 cm at 12 Hz along the view axis.
- **FOV punch**: the pawn's camera drops by 12 deg in the hit frame, then eases back over about 0.9 s.
- **Post-process**: the pp lane's public `TriggerGlitchBurst(0.6, 0.2)` fires on the cut, not the hit, in the game's own datamosh language. In PIE burst js2, a burst of 1.0 for 0.7 s on the hit buried the face in blocks.
- **Light**: two shadowless point lights in camera space, on only from 0 to 0.65 s. `FaceLight` is a 0.12 cd key under the chin, 10 cm in front of the lens. `RimLight` is a 7.5 cd rim behind the head, upper left, that catches the skull, teeth and claws. Volumetric scattering is off, so they don't glow in the fog. Both are on lighting channel 1 only, as is the monster, so they never light the pawn or the room.
- **Reduce motion**: when `MPC_Dream.ReduceMotion` is 1, the shake plays at 0.3 scale and the FOV punch is skipped.
- **The monster**: a Lux3D bust (`SM_Jumpscare_Monster`, about 40 cm, 37k tris): an emaciated skull face, jaw unhinged mid-scream, needle teeth, skeletal hands raised on either side of the face. It's attached to the player camera manager, so it sits in camera space with no lag in third person or first person.
  - Surface: black wet sand. `MI_Jumpscare_Monster` darkens the Lux3D albedo to 1.8%, and the fireplace's tileable grunge normal (reused, tiled 4x) crumbles the specular.
  - Baked maps (`Tools/Unreal/horror/make_monster_maps.py`): black voids for the eye sockets (eyeballs included) and the mouth interior (tongue included), AO cavities, curvature roughness, and ridge-only specular. Only the brow, cheekbones, teeth tips and knuckles catch light.
  - The pawn is hidden for the hold, because over the shoulder it sits closer to the lens than the monster. The Release timer shows it again.
  - It uses custom stencil 200, so the time echo skips it and no ghost trails behind it.
  - At the cut a black-sand burst falls where it was, through `BPL_SandFX.SpawnSandBurst`. A second burst on the hit read as a white puff over the face in js3, so it was removed.

## Audio layers
All recorded library audio, no synthesis. Sources and licences are in `P:\FoA-Assets\audio\SOURCES.txt`.

| Layer | Asset | Played by |
|---|---|---|
| Room tone, wind (ducked) | the existing `Amb_RoomTone`, `Amb_NightWind` | `SMX_Jumpscare_Hush` |
| Tension bed | `SFX_Horror_TensionBed_Loop_01` | `Bed` AudioComponent, FadeIn 4 s, FadeOut 0.6 s |
| Stinger (0.40 s riser, then hit, shrieks, growl and sub) | `SFX_Horror_Stinger_01` | PlaySound2D at -0.40 s; the reveal timer lands on its hit |
| Tail | the existing `S_Dream_HeartbeatPanic` | PlaySound2D at 0.65 s, volume 0.6 |

## Never twice in a run
`bFired` is set on the hit frame and never cleared. The director's new-day sweep (`SweepInteractables`, `ResetHouse`) and
`ResetToTitle` don't reload the level, and BP_Jumpscare isn't an interactable, so nothing re-arms it. Failing the day,
restarting it or quitting to the title in the same session can't replay it. Only a fresh launch, which is a new run, can.
