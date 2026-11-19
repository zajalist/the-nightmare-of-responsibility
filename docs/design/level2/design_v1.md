# Level 2: Find a job

Story lane, 2026-11-10. This is an offline design; nothing is built.

**Decided** (the user and main, 2026-11-10):
- Only the road fails the level; encounters never do.
- The city source is Toronto (the GTA lidar plus the 3D Massing data).
- "Day one." moves onto the threshold's white.
- The Nightmare gets exactly one Level 2 line, "Take your time.", on the restart transition and nowhere else.

Read it alongside `splat_feasibility.md` (research lane, in progress) and `splat_budget_ours.md` (world lane). This design names no splat source, scan or count that those files haven't confirmed. Each splat-dependent beat states the minimum it needs and what it falls back to, so the level still works with far fewer splats than hoped.

## 1. What the level is

He steps out of the bedroom into light, then into a world in colour. He walks a path that builds itself, falls through it, and wakes on the other side of the world, in a monochrome city. He finds his dad's car. The goal on his phone list becomes **Find a job**. He drives the city from above like an old RPG overworld, to three places. Meteors fall on the way. The buildings come apart into black sand and put themselves back. If he loses his composure on the road, the whole level starts again. At the third place he gets an interview, and the world turns to colour again.

**Tone.** The user's words: "a bit of the horror and seriousness as a theme even though none of the story makes sense because it's a dream... an austere, serious tone."
- The world is austere and played completely straight. Nothing winks.
- People speak little and formally. Signs and machines are matter-of-fact about impossible things: meteors are in the forecast, and every aisle is aisle nine.
- His voice is unchanged: dry, tired, true. He jokes so he doesn't have to say the real thing.
- Nothing is explained, there are no theme statements, and the word "dream" never appears on screen.

**Look.**
- Level 1's rules hold for the city: monochrome, warm split-tone, pitch-black sand.
- Colour appears only in the two dream worlds at the level's ends.
- The change from monochrome to colour is the post-process interpolation the user asked for, the MPC_Dream ColorReveal ramp already used for payoff colour, run over seconds instead of a cut.

**The Nightmare** keeps its one rule: it never does anything.
- In the city it is seen and never met: at the end of a street on foot, one junction ahead on the top-down map, at the end of an aisle, and in the rear-view mirror once.
- Its only line in Level 2 is "Take your time.", once, on the restart transition (section 6). Otherwise it is silent.

## 2. Beats and timings

Target length is about 18 to 22 minutes on a first clear. Times are for a first-time player.

| Beat | What happens | Camera | Time |
|---|---|---|---|
| **L2-T0** Threshold | Cutscene. He walks to the bedroom door, opens it, and white light floods in. A dolly-zoom (the vertigo shot) warps the doorway's perspective. He walks through into the white. On the white: "Day one." Then a sharp cut into the colour world, with the post-process easing from monochrome to colour over about 3 s. | Third person (sanctioned cinematic) | 14 s |
| **L2-T1** The colour path | Control returns in the colour world; the room is gone. The short mechanic (section 3): a path of coloured sand builds itself a step ahead of him and crumbles if he stops. At its end it runs out. | First person | 60-90 s |
| **L2-T2** The fall | The ground gives way. First-person fall through coloured sand. The view rolls over, the colour drains back to monochrome, and he hits a city street on his back, under a sun in the wrong place. He gets up. | First person | 10 s |
| **L2-T3** The street | On foot down one city street, about 60-80 m: the phone, a bus stop, a row of figures made of black sand, Dad's car. Three to four interactions, no puzzle. | First person | 2-3 min |
| **L2-T4** The car | He gets in. The camera rises to top-down. The goal on the phone list becomes **Find a job**. The first drive leg doubles as the tutorial: one telegraphed meteor, the brace prompt, then the Career Center. | Top-down | 1.5 min |
| **L2-T5** Career Center | Vignette, then the job-hunt encounter "The Form". Winning it gives two addresses. | First person in, encounter UI | 3-4 min |
| **L2-T6** Drive leg 2, then the grocery | Four meteors; buildings near impacts dissolve into black sand and re-form. Then the All-Night Grocery: vignette and the encounter "The Shelf". He wins it and still doesn't get the job. | Top-down, then first person | 4-5 min |
| **L2-T7** Drive leg 3, then the office | Six meteors, heavier and closer together. Then the office tower: vignette and the encounter "The Interview". He gets the interview. | Top-down, then first person | 5-6 min |
| **L2-T8** Out | Cutscene. Leaving the tower, the street splits along a seam of light and opens into a second colour world, and the level ends. | Third person | 12 s |

Order is fixed: the Career Center first, because it gives the other two addresses. The grocery and the office can be driven to in either order. The office only opens after the grocery ("Come back when you've been somewhere first"), so the shape stays three stops with rising stakes.

## 3. The colour path (L2-T1)

A brief, fun mechanic that teaches nothing the level needs later. Its job is the shock of colour, then the fall.

| Option | How it plays | Build | Risk |
|---|---|---|---|
| **A. The path builds itself** (recommended) | Coloured sand assembles a step ahead of him into a walkway over nothing. If he stops for more than 1.5 s, the tiles under him start to crumble. Walk and it holds; turn back and the tiles behind are already gone. After about 40 m the sand stops arriving. He walks off the end, or it gives way under him if he waits. | A spline of 30-40 tile actors with distance-to-player reveal and a standing-still timer. A dissolve parameter on each tile. Fall trigger at the end. | Low. Works with meshes and a sand material if splats are scarce. |
| B. Hold still | The opposite rule: the world only forms while he stands still; walking dissolves the next stretch. | Same tiles, inverted rule. | Reads as slow, and the fun is in waiting. |
| C. Follow the colour | Colour drains from everything except one object (a coat on a stand, a door). He reaches it, and the colour jumps to the next. Three hops, then the fall. | Three trigger volumes, an MPC colour mask around a point. | Depends on a large coloured environment to drain, so it's the most splat-dependent. |

**Why A:** it's the most readable in first person, it needs no instructions, and its ending is the fall we need. It also rhymes with the house: he has to keep moving or the floor gives way.

**Minimum content:** one coloured environment around a 40 m corridor. The whole world can be one generated or Lux3D colour splat scene, or, if splat counts are tight, coloured fog, a sky, three or four Lux3D colour splat props, and the tiles themselves. The path tiles carry the beat either way.

## 4. Driving: the old-RPG overworld (L2-T4 to T7)

| Option | How it plays | Build | Risk |
|---|---|---|---|
| **A. Road rails with choices** (recommended) | Top-down. The car follows the road on its own. The player controls speed (accelerate and brake), changes between two lanes, and picks a turn at each junction with a direction key (arrows show the options). Destinations show as named markers, like old RPG town labels. | Road splines with junction nodes. The car pawn moves by distance-along-spline plus a lane offset; there are no physics. | Low. No collision tuning, and splat buildings need no collision. |
| B. Grid steps | The car moves one block per input on a road grid (the Dragon Quest overworld). Meteors mark grid cells. | A grid and a tile mover. | Feels slow in real time. Meteors become a puzzle rather than a scare. |
| C. Free arcade driving | A kinematic top-down car with steering, colliding with block volumes. | A custom pawn, block collision proxies, tuning. | Most fun at best, but the most tuning. Collision against splat cities needs invisible proxies everywhere. |

**Why A:** it has the board-game clarity of an old RPG overworld, and the meteors still need real-time reactions. It costs days, not weeks.

**City minimum:** from top-down the city reads as blocks and roads.
- Ideal: the city is a chunked monochrome splat scan, with the street from L2-T3 as the hero chunk.
- Fallback: simple mesh blocks with the shared sand-dissolve material, plus the three destination buildings as Lux3D splat landmarks so the tools stay central. The dissolve and re-form works on both.

## 5. Meteors: brace or avoid (drive legs)

| Option | How it plays | Build | Risk |
|---|---|---|---|
| **A. Avoid or brace, one composure meter** (recommended) | A meteor's shadow grows on the road ahead, with a ring closing over about 2.5 s and a rising sound. Change lane or take another turn to get out of the ring. If you can't, hold **Brace** as the ring closes (a 0.4 s window). Impact: a 0.2 s time-slip (the time-shift blur), a shockwave through the splats, and nearby buildings dissolve into black sand and re-form over 3 s. | BP_Meteor (telegraph decal, timer, impact). An MPC epicentre and time for the dissolve and shockwave. A brace input and a composure value on the car. | Low. Readable from top-down. |
| B. Brace only (a QTE) | Meteors land on a beat; press on the shockwave. | Simplest. | No choices; a reflex test, not a drive. |
| C. Avoid only | Dodge between lanes and turns. | Simple. | Loses the "brace yourself" idea the user named. |

**The numbers for A:**
- **Composure** is the battle's word, carried over on purpose. It starts at 100 on each drive leg.
- Costs per meteor: avoided 0, braced in time 0, braced late 15, unbraced 40. Three unbraced hits on one leg means failure.
- Meteors per leg: 1 (the tutorial, with a slow ring), then 4, then 6. On leg 3 two meteors can overlap.
- The ring and the brace window never shrink; only the count and the overlap grow.

## 6. Failure and restart

- **What fails:** composure reaching 0 on any drive leg. Encounters can't fail the level. As in the T8 battle, losing an encounter costs the attempt at that place: you drive back out and can return to it.
- **What happens:** the dream-like transition the user described.
  - The top-down camera falls into first person.
  - The FOV pumps (90 down to 30 with a dolly-out, the same vertigo as the threshold), the frame crumbles into black sand, and the box line "Another morning." appears (reused from the battle defeat).
  - Then the threshold again, in its 3 s short version: the door, the white, the colour path.
- **The whole level restarts,** as the user asked. Three things keep it from being punishing:
  1. Cutscenes play short versions and stay skippable.
  2. The street beat (L2-T3) shortens to the car, with the interactions still there but optional.
  3. What he learned is kept as phone notes, like Level 1's Knows flags. For example: "Meteors come in from the east. Brace late, not early." and "Form: previous experience counts as anything." Each makes a repeat a little easier and shows up on the rollover card.
- **Count:** the day counter keeps counting, as in Level 1. A restart is another morning.

## 7. The three places

Each place has a short vignette on foot (first person), then one encounter in the existing T8 battle UI (WBP_Encounter), retitled. "Getting dressed" becomes "Applying".
- His moves are the old ones where they still make sense: Breathe, Mirror ("Look at it. Actually look."), plus two Act moves per place.
- The opponent's moves are the place's dream logic, played straight.
- For mech_encounter this is new data (DA_Opponent and DA_Move rows) plus one header label; the rules are unchanged.

### 7.1 Career Center: "The Form"
**Vignette:**
- A low waiting room. Numbered chairs, all taken by figures of black sand, perfectly still. A clerk sits behind frosted glass; only the voice comes through.
- The display reads NOW SERVING 17. He takes ticket 18. Nobody is called. When he walks to the glass anyway, the clerk is ready for him.

**Encounter, The Form:**
- His Act moves: Write Neatly (timed key prompts, like Button Up) and Read It Properly (reveals the field that is lying).
- Its moves:
  - **Previous Experience:** a box that keeps getting bigger.
  - **Two References:** a field that needs two names.
  - **Sign Here:** the signature line slides away.

**Win:** the form is complete. The clerk passes back a slip with two addresses: the All-Night Grocery, and an office downtown that "wants someone today".

### 7.2 All-Night Grocery: "The Shelf"
**Vignette:**
- Fluorescent and empty. The PA asks for staff to aisle nine. Every aisle sign says 9.
- The manager is only a voice on the PA, polite and tired, and never appears.
- The Nightmare stands at the far end of one aisle and is gone at the next look.

**Encounter, The Shelf:** a trial shift, stocking one shelf.
- His Act moves: Face the Labels and Stack (timed).
- Its moves:
  - **Wrong Aisle:** cans swap places with their neighbours, like the socks.
  - **Restock:** the shelf refills itself in the wrong order.
  - **Inventory:** the PA asks a question with no right answer.

**Win:** the shelf is perfect. The PA says, deadpan: "Thank you. The position has been filled." He gets nothing. The office is now open on the map.

### 7.3 The office tower: "The Interview"
**Vignette:**
- A tall lobby with no stairs and no lift. In the middle of the marble floor stands his bed, made the way Mom makes it, tight corners.
- The receptionist (a sand-figure silhouette behind a long desk, face never resolved) asks him to take a seat. The only seat is the bed. He sits on its edge and does not lie down.

**Encounter, The Interview:**
- His Act moves:
  - Answer Honestly (strong but costs Resolve).
  - Deflect (a joke; it works once, then it's a wasted turn).
- Its moves:
  - **Tell Me About Yourself**
  - **Where Do You See Yourself**
  - **There Is a Gap In Your History.** This is its big move, telegraphed a turn early like the tie's Strike.

**Win:** "Tomorrow. Nine o'clock." This leads to L2-T8.

## 8. Dialogue

The script voice rules apply: short, plain, first person, no aphorisms, no "dream". Types are as in `story/script.md`.

Other speakers are new, and each is a separate voice for the user to cast or record. Each is austere: formal, unhurried, never jokey.
- **CLERK** (voice behind glass)
- **PA** (the grocery manager)
- **RECEPTIONIST**
- **RADIO** (a calm announcer)
- **MOM** (phone text only; SCREEN)

The BOX narrator returns in the encounters.

### L2-T0 Threshold
| Trigger | Type | Line |
|---|---|---|
| On the white, after he steps through | CARD | Day one. |

This moves "Day one." from Level 1's black end card to the white of the threshold, so the count starts as he crosses. Decided; Level 1's end card is to be removed when L2-T0 is built.

### L2-T1 The colour path
| Trigger | Type | Line |
|---|---|---|
| Control returns | THINK | Colour. Since when. |
| The first tiles assemble ahead | THINK | Okay. Walk. |
| He stops and it starts to crumble | SAY | Don't stop. Don't stop. |
| He looks back and the path is gone | THINK | Not going back that way, then. |
| The sand stops arriving at the end | THINK | That's it? That's where it ends? |

### L2-T2 The fall
| Trigger | Type | Line |
|---|---|---|
| Lying on the street, looking up | THINK | The sun's in the wrong place. |
| Getting up | SAY | Still in the suit. Good. |
| Looking down the street | THINK | This isn't my street. This isn't anyone's street. |

### L2-T3 The street
| Trigger | Type | Line |
|---|---|---|
| The phone buzzes | SCREEN (MOM) | Did you go out? |
| Reading it | SAY | Yeah. Sort of. |
| The list on the phone, "Find a job" now next | THINK | Find a job. Okay. Today, apparently. |
| Bus stop timetable, Look | SCREEN | Every departure reads: Later |
| Bus stop, Look | THINK | Every bus says later. I know the feeling. |
| The sand figures, mid-stride | THINK | Don't look at them. They're not looking at you. |
| One of them has turned its head when he looks back | THINK | That one was facing the other way. |
| The car, Look | THINK | Dad's car. |
| The car, Look again | THINK | Keys are in it. Of course they are. |
| A parking ticket on the windscreen | THINK | Seventeen days on the meter. Same. |
| Getting in | THINK | I have a learner's permit. That's basically a license. |
| The radio comes on by itself | RADIO | Traffic is light this morning. Meteors are expected after nine. Drive carefully. |
| After the radio | THINK | After nine. It's after nine. |

### L2-T4 to T7 Driving
| Trigger | Type | Line |
|---|---|---|
| The goal | GOAL | Find a job |
| The first shadow grows on the road | THINK | That's a shadow. Why is there a shadow. |
| The brace prompt appears | PROMPT | Hold Space to brace |
| Braced, impact | SAY | Okay. Okay. Still driving. |
| Unbraced, impact | SAY | No no no. Hands on the wheel. |
| Buildings dissolve and re-form (first time) | THINK | It just put itself back. Like nothing happened. |
| Composure low | THINK | Breathe. In for four. You can't do four, do two. |
| The Nightmare at a junction ahead (first sighting from above) | THINK | It's on the corner. It's just standing on the corner. |
| The Nightmare in the rear-view mirror (once) | (none) | (silence, one beat) |
| Arriving at a place | (location banner) | CAREER CENTER / ALL-NIGHT GROCERY / OFFICE |

### L2-T5 Career Center
| Trigger | Type | Line |
|---|---|---|
| The display, Look | SCREEN | NOW SERVING 17 |
| Taking a ticket | THINK | Eighteen. Of course it's eighteen. |
| The sand figures in the chairs | THINK | Nobody's moved. Nobody's even breathing. |
| At the glass | CLERK | Name. |
| His answer | SAY | It's on the form. Probably. |
| The encounter starts | BOX | A form slides under the glass. It wants everything in block capitals. |
| Previous Experience | BOX | The box for previous experience grows larger. |
| His answer to it (Write Neatly) | SAY | Previous experience. Getting dressed. That counts. |
| Two References | BOX | It asks for two references. |
| His answer to it | THINK | Mom. And Mom, but in pen. |
| Sign Here | BOX | The signature line slides out from under the pen. |
| Win | BOX | The form is complete. It has never been complete before. |
| The clerk after | CLERK | The grocery on Fifth is hiring nights. And an office downtown wants someone today. |
| Leaving | THINK | Someone today. That's me. Maybe that's me. |

### L2-T6 All-Night Grocery
| Trigger | Type | Line |
|---|---|---|
| Entering | PA | Staff to aisle nine. |
| Aisle signs, Look | THINK | Every aisle is aisle nine. |
| The Nightmare at the end of an aisle | (none) | (silence) |
| The encounter starts | BOX | One shelf. One shift. The manager is watching from somewhere. |
| Wrong Aisle | BOX | The cans trade places while you aren't looking. |
| His reaction | SAY | These were in order. These were just in order. |
| Inventory | PA | Can you work nights. Can you work days. Can you work. |
| His answer | SAY | Yes. Yes. I think so. |
| Win | BOX | The shelf is perfect. |
| The PA after | PA | Thank you. The position has been filled. |
| Leaving | THINK | Filled. By who. There's nobody here. |

### L2-T7 Office tower
| Trigger | Type | Line |
|---|---|---|
| The lobby | THINK | No stairs. No elevator. Great building. |
| The bed, Look | THINK | That's my bed. Mom made it. |
| The bed, Sit | THINK | Sitting. Not lying down. Sitting. |
| The receptionist | RECEPTIONIST | Do you have an appointment? |
| His answer | SAY | No. Yes. I'd like one. |
| The encounter starts | BOX | The receptionist folds her hands. The interview has started. |
| Tell Me About Yourself | RECEPTIONIST | Tell me about yourself. |
| His answer (Answer Honestly) | SAY | I'm seventeen. I'm good at, um. I'm good at getting up. Recently. |
| Where Do You See Yourself | RECEPTIONIST | Where do you see yourself? |
| His answer (Deflect, first use) | SAY | Here? Sitting on my bed in a lobby, apparently. |
| The telegraph for the big move | BOX | The receptionist turns a page and goes very still. |
| There Is a Gap In Your History | RECEPTIONIST | There is a gap in your history. |
| His answer (Answer Honestly) | SAY | Yeah. It's seventeen days long. |
| Win | RECEPTIONIST | Tomorrow. Nine o'clock. |
| His reaction | THINK | Nine. I can do nine. |

### L2-T8 Out
| Trigger | Type | Line |
|---|---|---|
| The street splits into light | (none) | (silence; the colour returns) |

### The restart
| Trigger | Type | Line |
|---|---|---|
| Composure reaches 0 | BOX | Another morning. |
| Back at the threshold (short version) | THINK | Again. Okay. |
| Over the crumble to sand, before "Another morning." | NIGHTMARE | Take your time. |

## 9. Who builds what

| Lane | Builds |
|---|---|
| **story** (me) | The beat data L2-T0 to T8 (DA_Beat rows on the same director pattern) and every line above in story_text. The threshold and exit cutscene shot lists. The restart rule and the phone notes. The encounter text (BOX, moves, openers) for the three places. The VO entries for the new lines in vo_script.json. |
| **anim / cinematics** | LS_Threshold and LS_Out: the dolly-zoom (a CineCamera dolly with keyed focal length, then cut), the walk to the door, sitting on the bed's edge. The fall in first person and the get-up (UAL_LayToIdle exists). A seated driving pose. |
| **world / splats** | The colour world (source per `splat_feasibility.md`), chunked; at minimum the colour path's surroundings. The city: the hero street chunk for L2-T3, and top-down blocks (splat chunks, or mesh blocks with the sand-dissolve material). The three landmark buildings as Lux3D splats. Collision proxies for the street. |
| **pp** (post-process) | The monochrome-to-colour interpolation (ColorReveal over about 3 s) and back. The restart transition (FOV pump, perspective swing, crumble to sand). The top-down style for the map. |
| **mech** | The colour path (tiles, reveal, stand-still crumble, fall trigger). The car and the road rails (spline follow, two lanes, junction choice, speed). BP_Meteor (telegraph, ring, brace window, impact, MPC epicentre for the shockwave and dissolve). Composure on the car. Restart wiring. |
| **mech_encounter** | Three new opponents and their moves as data, plus the "Applying" label. Losing an encounter returns you to the car instead of FailDay. |
| **ui** | The "Find a job" goal. Destination labels on the map. The brace prompt and the composure bar on the driving HUD. The location banners. The phone (Mom's text, the updated list). Subtitles for the new speakers. |
| **sound / horror** | Meteor whistle, impact and shockwave through sand. City ambience with no people. The PA, the radio and the clerk behind glass (VO slots). The car. The colour world's sound, as different from the house as the colour is. |
| **Lux3D assets** (the 30 % criterion) | Dad's car, the ticket machine and display, the form, grocery cans and shelf, the reception desk, the meteors, the landmark buildings. The bed and the sand figures are reused. |

## 10. Open questions

None at the moment. The four decisions are recorded at the top of this file. Splat counts still follow `splat_feasibility.md`.
