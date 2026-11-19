# FoA: 90-second demo video

**Format.** The cut runs exactly 1:30 at 1920×1080, exported as an H.264 MP4. Ninety seconds is within X's 2:20 upload limit, so the same file can go in the X post.

**Real footage.** The hackathon rule is that "the video must include footage of the actual project running". Every shot except 5a–5c is captured in real time from the packaged Development build (OBS, 1080p60). Shots 5a–5c are process footage, and their captions say what each step is.

**Silent viewing.** X autoplays videos muted. Every beat has to read without sound, so burn the captions into the picture.

**Tone.** "Funny things, filmed sincerely" (concept board). The music never plays a joke sting.

**Hook.** The video opens on the Shirt's boss intro. That single image carries both the premise and the joke (a shirt with a boss level), and a Lux3D asset rises out of black sand within the first second. The key snap and the wardrobe fall follow it, making a three-beat cold open.

**Status tags in the table:**
- **built** or **imported:** exists on Nov 5.
- **generated:** the Lux3D output exists.
- **to build** or **to capture:** not done yet.

| # | Time | On screen | Build feature it needs | On-screen text | Audio |
|---|---|---|---|---|---|
| 1 | 0:00–0:03 | A low third-person angle. The inside-out shirt rises out of a black-sand mound like a boss, and the battle menu slides in. | The Shirt, Lux3D G1 4725759 (generated) · cloth or a simple animation (to build) · sand materialize with a splat mesh (to build) · T8 encounter UI in UMG (to build) | Game UI only: "THE SHIRT (INSIDE OUT) · LV 30" and "FIND ARMHOLE · BUTTON UP · DEEP BREATH · CHECK MIRROR" | One dead-serious orchestral boss hit |
| 2 | 0:03–0:05 | Close-up: the key snaps in the lock, and the figure stares at the stub in its hand. | Door key, Lux3D 4725680 (imported), cut into two halves in UE (to build) · bedroom door (to build) · interaction (to build) | none | A crisp metal snap, then silence and a clock tick |
| 3 | 0:05–0:08 | The wardrobe tips across the doorway in a burst of black sand. | `GothicCabinet_01` from Poly Haven (imported) with physics (to build) · the sand burst as a splat mesh (to build) | none | A crash, then a sand hiss |
| 4 | 0:08–0:12 | The title over an in-engine shot: a black-sand mound in a light shaft, with dust drifting through the bands. | Sand mounds (built) · light shafts using T_Lines (to build) | "FoA – The Nightmare of Responsibility" / "Getting dressed is a boss fight." | The score enters: low piano and strings |
| 5a | 0:12–0:14 | The prompt is typed in (a screen recording of the prompt table or terminal). | `lux3d_batch.py` (built) | "PROMPT: Old wind-up alarm clock with twin bells, sculpted from dark sand" | A soft whoosh per step, under the score |
| 5b | 0:14–0:16 | The raw Lux3D splat turns in a splat viewer. | The PLY from task 4726033 (generated) · the viewer capture (to capture, L02) | "LUX3D G1-TURBO · 1,175,936 SPLATS" | Whoosh |
| 5c | 0:16–0:18 | The baked splat mesh in the UE viewport, first wireframe, then shaded. | The splat-mesh converter (built: `Tools/Splats`) · import and material (to build, G07) | "SPLAT MESH · N QUADS" | Whoosh |
| 5d | 0:18–0:20 | In-game, the clock pours up out of the sand mound, rings once and collapses. | The splat-mesh materialize/dissolve material (to build) | "IN GAME" | An alarm bell, then a sand hiss |
| 5e | 0:20–0:22 | A wall of every Lux3D asset in the game, each with its task ID. | The contact sheet (to capture, L02) | "N LUX3D ASSETS IN ONE BEDROOM" | The score swells |
| 6 | 0:22–0:26 | T0, the phone. The calendar shows 17 crossed-out days, and a black-sand hand reaches in and taps "Wake up". | The phone UI in UMG (to build) · the sand hand, Lux3D 4725644, as a splat mesh (to build) | The phone UI only: the crossed-out days and the task list | A tap, then an alarm buzz cut short |
| 7 | 0:26–0:33 | T1–T2, over the shoulder. The figure rises from the bed with black sand trailing from its steps, finds the door locked and pulls open the commode drawers. | The Lux3D character (to build) · the Poly Haven bed frame with the Lux3D bedding (imported) · interaction (to build) · the sand trail (to build) | "Goal: get dressed. Leave the house." | Floor creaks, a rattling handle, drawers |
| 8 | 0:33–0:39 | T3 and T5. The key turns up in a boot under the bed. Later, the figure kneels at the door with a screwdriver. | `rubber_boots` and `screwdriver` from Poly Haven (imported) · inventory and use (to build) | none | Small, precise foley |
| 9 | 0:39–0:46 | T7, a top-down cut. The door is on another wall, the emptied drawer is full again, and time-shift echoes of the figure trail across the floor. | The dream director moves the door (to build) · the `Shot_TopDown` camera (built) · the time-shift blur (to build) | "The door moved." | The score drops out: a low drone and echo whooshes |
| 10 | 0:46–0:56 | T8, the encounter. A "Button Up" timed input lands, the Shirt's "Wrong Button" undoes it, and then the figure takes a "Deep Breath". | Encounter turn logic and UI (to build) · the Shirt's cloth (to build) | Game UI and damage numbers only | The battle version of the main theme |
| 11 | 0:56–1:02 | The fail loop. The night mare rears out of black sand over the bed (Fuseli's composition) and collapses, and the phone adds a crossed-out day. | The night mare, Lux3D 4725817, as a splat mesh (to build) · day rollover and house reset (to build) | "Fail, and the day starts over." | A roar of sand, then the alarm again |
| 12a | 1:02–1:06 | A split-wipe from one camera: light shafts off, then on. | Light shafts (to build) | "LIGHT SHAFTS: ONE 128×1024 BAND TEXTURE" | The score builds |
| 12b | 1:06–1:10 | A split-wipe of a splat mesh mid-dissolve: wireframe, then shaded. | The splat material (to build) | "LUX3D SPLATS AS MESHES, NOT PARTICLES" | The score builds |
| 12c | 1:10–1:14 | The packaged build on the low-end PC, with the fps counter visible. | The packaged build (to build) · numbers from P00, P01 and P03 (to capture) | "X FPS ON [GPU] · X MB BUILD", using measured numbers only | The score builds |
| 13 | 1:14–1:21 | The T9 build-up. The last button goes through, the figure turns, the camera drops to a low hero angle and the suit settles on. | The suit, Lux3D 4725770, on the character (to build) · the Sequencer shot (to build) | "Dressed." | A swell, then half a beat of silence |
| 14 | 1:21–1:30 | **The payoff.** `ColorReveal` floods the grey world with color within one second, black sand blooms around the feet, and the shot holds. The end card fades in over the color from 1:25, and the last frame stays in color. | `MPC_Dream` ColorReveal (the parameter is built), animated in Sequencer (to build) · the sand bloom (to build) | "FoA – The Nightmare of Responsibility" · "Made with Aholo Lux3D · Unreal Engine 5.8" · "#Manycorehackathon" · the link | A full orchestral hit that rings out to the last frame |

The user has paused music for now ("no music so far"). The Audio column's score cues are placeholders, so cut with SFX only until music is decided.

## Fallbacks if a feature isn't built by the Nov 17 freeze

- **T8 encounter (shots 1 and 10).** Open on shot 2 (the key snap), then 5d (the clock materializing), then the title. Fill shot 10's slot with T5 and T6 gameplay.
- **Splat material (shots 5c, 5d, 11 and 12b).** Show the mesh path instead: the prompt, then the door key GLB, then the key snapping in-game. This takes the main innovation out of the video, so build the splat material first.
- **Suit (shot 13).** Run the color burst on the hooded figure instead. The video still has to end on the color burst.
- **Character.** Use Manny with only the Faceless Mask, socketed to his head.
- **Performance numbers (shot 12c).** Cut the shot. Never show numbers you haven't measured.

## Capture and edit notes

- Record 2–3 takes of each shot, each two to three times as long as its slot, and cut on action.
- Keep debug text out of every shot except 12c.
- Use only sound effects (and later music) licensed for redistribution, and list them on report slide 15.
