# The Nightmare of Responsibility: level 1 script

Every line the player reads in the tutorial bedroom, in play order. The user approved it on 2026-11-09, with the voice set to North American.

Owner: story lane. If a line isn't here, it shouldn't be on screen.

## The voice

He is seventeen, North American ("Mom", "pants", "Call me"), and has not left his room in seventeen days. He is tired, dry and a bit funny, and every so often he says something sharp. He jokes so he doesn't have to say the real thing.

- **Short and plain.** Most lines are under eight words. He uses contractions, says "like" and "actually", and repeats himself when he's rattled.
- **No aphorisms or theme.** He never explains depression, responsibility or the house. The images and the systems do that.
- **Subtext.** What he says and what we see should disagree a little. "It's just a shirt" plays over a shirt that is clearly not just a shirt.
- **One point of view.** Every thought is first person, present tense. The old lines switched between "you" and "I". The one exception is the battle's RPG text box, which stays second person on purpose: it's an old-RPG narrator, and that's the joke.
- **Fewer lines.** The old intro had seven narrator lines over 51 s. The new one has four lines over 21 s. In play, I cut lines where the action already says it.
- **Banned:** the word "dream", middle dots, separators, "One thing at a time", and anything that would work on a mug.

## What I took from the references

| Game | What it does | What I took |
|---|---|---|
| Firewatch | Henry's lines are short and wry, and the jokes are how he avoids grief. The prologue covers years in a few plain sentences. | Deflecting jokes that give away the pain ("Not that anyone's counting"). The funniest line in a scene is often the saddest. |
| Oxenfree | The teens talk like teens: half sentences, repeats, under-reaction to the uncanny. Nobody explains the ghost. | Fragments and repeats when he's scared ("I'm fine. I'm fine. I'm fine."), flat reactions to impossible things ("That's new."), and nothing explained. |
| Inside | No words at all. The images, the timing and one shock carry everything. | The intro's last beat has no text: the thing that "never does anything" moves. Images first, words second. |
| What Remains of Edith Finch | The text lives in the world: handwriting on objects, letters, notes. Each vignette has one strong idea. | The list on the phone is the line ("Mom made me a list"). Notebook entries are his own phone notes, in his words. |
| P.T. | One ordinary space, looped, a little more wrong each time, with almost no text. | The morning repeats with small wrongness ("The door was on that wall. I know it was."). The Nightmare is never named or explained. |

## Line types

| Tag | What it is | Where it shows |
|---|---|---|
| **THINK** | Inner monologue, his thoughts. | The HUD subtitle slot (BPC_Interactor.Narrate or WBP_HUD.ShowSubtitle), no speaker. |
| **SAY** | Said aloud, under his breath: reactions, swearing-adjacent, counting. The subtitle of a sound he makes. | The same slot. The UI lane can style it at full opacity, with THINK at about 85 %. |
| **CARD** | Intro text over the panels. | WBP_IntroStory Txt_Sub. |
| **SCREEN** | Diegetic text on the phone: list, messages, notes. | WBP_Phone, WBP_DayRollover. |
| **BOX** | The battle's RPG narrator box, second person. | WBP_Encounter's line. |
| **PROMPT / GOAL** | Interaction prompts and HUD objectives. These are UI, not voice: plain imperative, no jokes. | WBP_HUD. |

## 1. The intro (WBP_IntroStory), about 21 s

Four images and four lines, then a hook. Every image comes from the real level, rendered with real depth for parallax, with black sand in the air. It's monochrome, Darker Grotesque, white text low on the frame, and no paper band.

| # | Image and motion | s | Line |
|---|---|---|---|
| 1 | The room at night, wide from the high corner. He's a small shape on the bed. A slow push in, moonbeam grains drifting. | 5.0 | CARD "Seventeen days. Not that anyone's counting." |
| 2 | The nightstand, close. The phone lights up in the dark (light change), and the list is on the screen: Wake up, Get dressed, Leave the house, Find a job. | 4.5 | CARD "Mom made me a list." |
| 3 | A shirt stands up on its own in the moonlight, empty, like a person. A slow lateral drift, and sand runs off its hem. | 4.5 | CARD "It's a shirt. It's just a shirt." |
| 4 | From his pillow: something stands at the foot of the bed, black against the moonlit room. The light falters. | 5.5 | CARD "It never does anything. It just waits for me to give up." |
| 5 | Hook. Hard cut: it is suddenly right over him. A fast push, and the frame crumbles to black sand, then black. | 1.6 | (none) |

The intro ends on black. LS_WakeUp opens on black with the clock ticking and the alarm at 2.2 s, so the alarm answers the lunge. Skip stays available the whole time.

**Removed**, all narrator voice that explains the theme:
- "There is a man who keeps sleeping through his life."
- "Something stands at the foot of the bed. It is patient."
- "Seventeen days. He crossed out every one."
- "The letters wait. The cup waits..."
- "Here, the chores have grown teeth. They are completely serious."
- "Today, you will get dressed."
- "Today, you will leave the house."

## 2. The wake-up (LS_WakeUp)

No text. The 36 s cinematic plays in silence apart from sound, which is correct. Nothing is added.

## 3. T0: the phone (SCREEN, UI lane applies)

After the wake-up the player gets the room first: the fade-up, then about 2 s of free look. Then the phone buzzes on the nightstand and rises on the list (BP_BeatDirector OpenMorningPhone, then RaiseMorningPhone). The tasks stay as they are: Wake up, Get dressed, Leave the house, Find a job. They are the same list as intro panel 2, and that's the payoff.

**Inbox labels** (portable_phone_ui.py: the sender on line 1, the preview on line 2)
| Sender now | Preview now | Sender new | Preview new |
|---|---|---|---|
| Mum | Before you go | Mom | Your shirt's in the wardrobe |
| Careers office | An open door | Career Center | Reminder: today |
| Unsent | I am awake | Draft | im up |

**Messages**, early version (BeatIndex < 3). Each message's line breaks are kept as separate paragraphs:
- **Mom:** "Morning! Your shirt's in the wardrobe, I ironed it." then, as a new paragraph, "Eat something before you go. Love you"
- **Career Center:** "Reminder: your drop-in appointment is today at 10:30. Reply C to cancel."
- **Draft (unsent):** "im up"

**Messages**, later version (BeatIndex >= 3):
- **Mom:** "Proud of you. Call me when you're out. Love you"
- **Career Center:** "We missed you on Tuesday. Drop in any weekday, 9 to 4. No appointment needed."
- **Draft (unsent):** "sorry about yesterday. and the day before. today's different i promise"

**Notebook, empty state:** "No notes yet."

**Lock screen** (the phone's first page, before the inbox):
- **Clock:** 6:40 when the phone first opens in the morning, then real time: 6:40 plus the whole minutes since that first open, capped at 9:59 (he can still make the 10:30 drop-in). Each new morning starts again at 6:40.
- **Date lines:** "Day 18" and "17 days crossed out", unchanged all morning; "Day one." on the end card is where the count starts over.
- **Notifications** follow the message versions above. Early (BeatIndex < 3): Mom, "Your shirt's in the wardrobe"; Career Center, "Reminder: today". Later (BeatIndex >= 3), when Mom's first message has been read and a new one has come in: Mom, "Call me when you're out"; Career Center, "Drop in any weekday, 9 to 4". Mom's is listed first, as the newest.

## 4. In play, by beat

The monologues are BP_BeatDirector story moments (`Tools/Unreal/flow/build_story_moments.py LINES`), one per beat, said when he's free. The interaction lines are DT_Interactions `Line` (mech_core's data, `Tools/Unreal/gameplay/data_rows.py`). In each table, "Now" is the current text and "New" is the replacement; a dash means the line is cut.

### T1: Take a few steps
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start (monologue) | THINK | Same ceiling. Same morning. Just get up. One thing at a time. | Okay. I'm up. That counts. |

### T2: Find something to wear (headache 1)
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start, headache | SAY | Behind my eyes again. Like something is pressing from the other side. | Ow. Not now. |
| Bed, Look | THINK | The bed. Still warm. It would take you back without a word. | Still warm. It'd be so easy. |
| Bed, Look (knows the key) | THINK | The bed. Under it, a pair of boots you suddenly remember. | My boots are under there. The left one. |
| Bed, Use | SAY | No. Not today. Probably not today. | Five more minutes. No. Absolutely not. |
| Sock drawer, Look | THINK | A drawer. It has been closed for a reason. | Sock drawer. Mom rolls them into little balls. |
| Sock drawer, Open | THINK | Socks, folded by someone who believed in you. | Socks. No shirt. |
| Wardrobe (standing), Look | THINK | The wardrobe. Tall, dark, and leaning very slightly. | Has it always leaned like that? |
| Wardrobe, Open | THINK | Shirts. None of them are the shirt. | Hoodie. Hoodie. Where's the good shirt? |
| Desk, Look | THINK | The desk. Someone tidy used to work here. | I used to do homework here. Like, actually do it. |
| Desk, Search | THINK | Papers, a cold cup of tea, and a screwdriver lying very still. | Old worksheets. Cold coffee. A screwdriver, for some reason. |
| Right boot, Look | THINK | The other boot. It has nothing to hide. | The other boot. |
| Right boot, Look inside | THINK | Just a boot. It smells of last winter. | Just a boot. Smells like last winter. |
| Calendar by the door, Look ("Look at the calendar"; optional, any beat) | THINK | (new) | Seventeen crosses. Mom does the crosses now. |
| Calendar by the door, Use ("Count the days"; optional, any beat) | THINK | (new) | Seventeen. Not that anyone's counting. |

### T3: Find the key
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start (monologue) | THINK | I put the key somewhere safe. Safe from me, apparently. | I hid the key somewhere safe. Safe from me, I guess. |
| Left boot, Look | THINK | A boot by the bed. It looks like it is hiding something. | Something's in my boot. |
| Left boot, Look inside | SAY | There is a key in the boot. Of course there is. | The key. In my boot. Sure. Why not. |
| Left boot, Put on | THINK | You pull on the boots. The day gets no easier. | Boots on. Still in pajamas, but boots on. |
| Boots, Check (worn) | THINK | They are on your feet. One thing done. | Boots are on. That's something. |
| Key, item Look (DT_Items LookLine, the pickup inspect view's line; its title, DisplayName, is "Door key") | THINK | Brass, cold, older than the door. It looks sure of itself. | The door key. I hid it from myself, and it worked. |

### T4: Unlock the door
| Trigger | Type | Now | New |
|---|---|---|---|
| Door (locked), Look | THINK | The door to the rest of the day. It is locked, which feels personal. | Locked. I locked it. Why did I lock it. |
| Door, Try the handle | SAY | Locked. Of course it is. | Locked. From the inside. By me. |
| Door, Use key (first time) | SAY | It turns halfway, then it doesn't. Then it snaps. | Come on. Come on. No. It snapped. |
| Door, Use key (knows it snaps) | SAY | Again. It snaps again. You knew it would. | Snapped. Again. I knew it would. |
| Door, Use screwdriver (before key) | THINK | You could take the lock apart. You have a key somewhere. You are almost sure. | I could take the lock apart. Or find the key like a normal person. |
| Door, Use hanger (before key) | THINK | There is a key for this. You have seen it somewhere. Probably. | There's a key. I definitely had a key. |
| Half key, item Look | THINK | Half a key. The other half is the door's now. | Half a key. The door kept the rest. |

### T5: Open the lock another way (headache 2)
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start, headache | THINK | It gets worse when I think about leaving. That's probably nothing. | Why is it always worse by the door. |
| Door (key jammed), Look | THINK | Half a key sticks out of the lock like a tongue. | Half a key, stuck in the lock. Great. |
| Door (jammed), Try the handle | THINK | Half a key in the lock is not going anywhere. Neither are you. | It's not going anywhere. |
| Door (jammed), Use half key | THINK | Two halves do not make a key. You checked. | Two halves don't make a key. I checked. |
| Door (jammed), Use screwdriver | SAY | Four screws. Each one takes longer than the last. | Four screws. Why is it always four screws. |
| Door (jammed), Use hanger | SAY | You fish through the gap. Something clicks that should not have. | Wiggle it. Wiggle it. There. |
| Door, Use screwdriver (knows it snaps) | THINK | You skip the key this time. Four screws. | Not trying the key again. Screwdriver. |
| Door, Use hanger (knows it snaps) | THINK | You skip the key this time. The latch gives. | Skip the key. Hanger in the gap. There. |
| Door (plate off), Look | THINK | The lock plate is off. The latch looks back at you. | Plate's off. I can see the latch. |
| Door (plate off), Push the latch | THINK | The latch slides back under one finger. It was that easy all along. | Oh. It just slides. |
| Screwdriver, Look | THINK | A flathead screwdriver, lying very still among the papers. | Why is there a screwdriver on my desk. |
| Screwdriver, Take | THINK | You take the screwdriver. It feels like a plan. | A screwdriver. That's basically a plan. |
| Screwdriver, item Look (title "Screwdriver") | THINK | A flathead screwdriver. The handle is worn smooth by other people's problems. | Flathead. No idea why it lives on my desk. |
| Hanger, Look | THINK | A wire hanger on a hook. It has been waiting for a job. | A wire hanger. |
| Hanger, Take | THINK | It comes off the hook with a small, guilty sound. | Got it. |
| Hanger, item Look (title "Wire hanger") | THINK | A wire hanger, bent into a question nobody asked. | Bent out of shape. Same. |

### T6: Open the door
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start (monologue) | THINK | The handle, then the door. One thing at a time. | Almost. Don't get excited. |
| Door (latch free), Look | THINK | The latch is free. All that is left is the handle. | Latch is free. Just the handle now. |
| Door, Pull the handle | SAY | The handle comes off in your hand. The door stays exactly where it is. | The handle came off. The whole handle. |
| Door, Pull (knows the wardrobe falls) | THINK | You know what happens next. It happens anyway. | Don't look at the wardrobe. Don't look at the wardrobe. |
| Door (no handle), Look | THINK | A door with no handle is a wall with ambitions. | No handle. Awesome. |
| Door (no handle), Push | THINK | Without a handle the door has nothing to say to you. | Push. Nothing. |
| Wardrobe (standing), Look | THINK | The wardrobe. Tall, dark, and leaning very slightly toward the door. | It's leaning toward the door. Was it always? |
| Wardrobe lands | SAY | The wardrobe lies down across the door, as if it had been waiting to. | I'm fine. I'm fine. I'm fine. |
| Wardrobe (fallen), Look | THINK | The wardrobe has made its position clear. | Right across the door. Of course. |

The fall starts in first person (LS_WardrobeFall). At impact, WardrobeFallDone releases the sequence's pawn transform and cuts to the wardrobe camera. The existing sand transition then reforms him behind the wardrobe; FinishWardrobeTransition returns control at 7.2 s.

| Time (s) | What the player sees | Sound |
|---|---|---|
| 0.0 | First person at the door, the handle in his hand. | the rattle starts behind him |
| 0.6 | The view turns to the wardrobe: it leans, its doors chatter. | creak rising |
| 2.0 | It tips toward him; he stumbles back. | panicked breath, two steps |
| 2.3 | Low side shot from the bed's corner: it comes down across the way to the door as he scrambles clear (impact 3.15). | debris, thud |
| 3.15 | Cut to the wardrobe camera as his body starts scattering into sand. | impact, breath |
| 4.15 | He disappears; the old doorway becomes wall. | sand |
| 5.05 | He reforms on the accessible side behind the wardrobe. | sand settling |
| 7.2 | His body is whole again; control returns for the clothing search. | |

The first-person fall must preserve the disappearance, teleport and visible reintegration (user correction, 2026-11-11).

### T7: Find the missing shirt (headache 3, the door moves, the search, the chase)
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start, headache | THINK | For a second I couldn't remember which wall the door was on. I was looking right at it. | The door was on that wall. I know it was. |
| Back from the top-down, if the fall knocked the hanger to the floor and it's still there (director; his view glances down at it while he says it, then back) | THINK | (new) | The hanger's on the floor now. Of course it is. |
| Screwdriver back on the desk after the fall (refilled, spent; Look only, it can't be taken again) | THINK | (new) | It's back. I didn't put it back. |
| Fallen wardrobe, Look | THINK | My shirt was in there. Something has dragged it out. | The good shirt was in there. Something dragged it out. |
| Wardrobe clue (director) | THINK | A thread caught in the splintered wood. It trails towards the papers. | A thread, caught on the wood. It goes toward the desk. |
| Broken wood, Look | THINK | A pale thread catches the light. It leads towards the papers. | A thread. From the shirt. |
| Broken wood, Check | THINK | The thread leads away from here, towards the desk. | It goes toward the desk. |
| Papers, Look | THINK | The papers have shifted. There is something small underneath. | Something's under the papers. |
| Desk clue (director) | THINK | A button under the papers. Mine. Those marks lead back towards the bed. | One of its buttons. And drag marks, to the bed. |
| Trail, Check | THINK | The marks run from the desk to the darkness beneath the bed. | Under the bed. Obviously under the bed. |
| Dust, Look | THINK | I should follow the marks under the bed. | Under the bed. Great. |
| Under the bed, Look | THINK | A thin line in the dust disappears beneath the bed frame. | The thread goes under the bed. |
| Bed clue (director), shirt, Look | THINK | Too far. I need something to reach it. | Too far back. I need something long. |
| Reach without the hanger (director) | THINK | Too far. A wire hanger could reach it. There was one by the coat rail. | Can't reach. The hanger on the coat rail might. |
| Shirt freed, Check | THINK | It is loose now. The shirt is at the foot of the bed. | It's out. It's at the foot of the bed. |
| Under the bed (freed), Look | THINK | Nothing underneath now. Just the shirt by my feet. | Just dust now. |
| Desk or bed, before the wardrobe | THINK | Nothing here tells me where it went. I should start with the fallen wardrobe. | Start where it was. The wardrobe. |
| Chase, pockets full (director) | THINK | My pockets are full. | (cut 2026-11-10: he carries any number of things now, so his hands are never full; was "My hands are full.") |
| Shirt, Look | THINK | The shirt. It is facing the wrong way, on purpose. | It's inside out. It wasn't inside out. |
| Shirt, Take | THINK | The shirt. Ironed, buttoned, and watching you. | Got you. |
| Shirt, item Look | THINK | The shirt. Ironed, buttoned, and watching you. | Mom ironed it. It's still warm. |

### T8 intro: "It won't come" (LS_BattleIntro, the user's pick A, 2026-11-10)
The final grab hands straight into the fight; no sand figure, no fade. LS_BattleIntro (3.5 s, build_wont_come.py) is the same cut on every morning; LS_BattleIntro_Short is identical, and only his line changes on a replay. Skippable with the wake-up's hold-to-skip (the vase still breaks).

| Time (s) | What the player sees | Sound |
|---|---|---|
| 0.0 | First person at the sill, his hands on the shirt. It pulls back, twice: a sleeve is caught on the vase. | breath, two cloth snaps |
| 0.8 | The vase tips off the sill and shatters (RoomTakeover.BreakVaseOnly). | shatter, sand pour |
| 0.95 | Black sand pours over the shirt and drags it off across the floor; the view whip-pans after it. | fabric whoosh, sand hiss |
| 2.2 | The shirt sinks into the mound mid-room. Cut to the room from behind the line, easing out to the battle framing while he hurries after it. | sand shift, footsteps |
| 3.2 | The fight starts on that same picture. The others are dragged in from where he has seen them: the socks from the open commode drawer, the pants from the fallen wardrobe, the tie from the chair back; the shirt stands up out of the mound. | the battle's own sand bursts |

| Time after the cut (s) | Speaker | Type | Line |
|---|---|---|---|
| 2.0 | the Nightmare | SAY | Get dressed. |
| 2.9 | him | SAY | Okay. Shirt first. |
| 2.4 (a replay) | him | SAY | Again. Shirt first. |

The Nightmare says one line, over the shot; it is never cut to. Retired with the sand-figure version: "No. No no no. I had it.", "It's just a shirt. It's just a shirt.", "The bed is still warm.", "Take your time." (still used in Level 2), "Seventeen days.", "Not eighteen."

### T8: the battle, "Getting dressed" (encounter data, story lane applies)
The BOX lines are the RPG narrator. The moves are his thoughts as he acts or as he's hit.

**Openers and closers** (DA_Opponent_*). The Trousers opponent is now "The Pants" everywhere the player reads it (DisplayName, captions, move hints); its asset ids stay Trousers.
| Garment | Line | Now | New |
|---|---|---|---|
| Shirt | BOX intro | The Shirt (inside out) blocks your way. | The Shirt (inside out) blocks the way. It has been ironed. |
| Shirt | BOX win | The last button closes. The shirt is only a shirt again. | Last button. It's just a shirt again. |
| Shirt | BOX lose | You sit down on the bed, half dressed. The day is over. | You sit back down on the bed, half dressed. There goes today. |
| Shirt | BOX victory | You are dressed. Nobody will ever know what it took. | You're dressed. Nobody will ever know what that took. |
| Sock | BOX intro | A sock arrives. Then another, which is not its pair. | A sock appears. Then another sock. They are not a pair. |
| Sock | BOX win | The sock is on. It is warm, and somehow that is worse. | One sock on. It's warm. Why is it warm. |
| Pants | BOX intro | The trousers stand up on their own. One leg is twisted. | The pants stand up by themselves. That's new. |
| Pants | BOX win | The trousers are on. Both legs agree, for once. | Pants on. Both legs, same direction. |
| Tie | BOX intro | The tie uncoils from the collar like something that has waited all night. | The tie uncoils. It's been waiting all night. |
| Tie | BOX win | A full Windsor. You did not know you could. | A full Windsor. Since when can you do a Windsor? |

**Telegraphs** (BOX)
| Move | Now | New |
|---|---|---|
| Kick | The trousers draw one leg back. | The pants pull one leg back. |
| Strike | The tie rears back and goes very still. | The tie rears back and goes very still. (kept) |

**His moves** (DA_Move_* Narration)
| Move | Type | Now | New |
|---|---|---|---|
| Deep Breath | SAY | In. Out. I can do this. | In for four. Out for four. Like the video said. |
| Check Mirror | THINK | Don't look away. Watch what moves first. | Look at it. Actually look. |
| Find Armhole | SAY | There. That's the opening. | Armhole. Found it. |
| Button Up | SAY | One. Then the next. Keep going. | One button. Next button. Don't think. |
| Match the Pair | SAY | They're the same. Stop moving. | These two. These are a pair. Stay. |
| Pull On | SAY | Heel first. Come on. | Heel. Heel. Come on. |
| Untwist the Leg | SAY | Let go. Turn back. | Other way. Other way round. |
| Step In | THINK | Steady. One foot at a time. | Left leg. Don't fall over. Right leg. |
| Loosen | SAY | Too tight. Get off. | Get off my neck. |
| Tie the Knot | THINK | Over. Under. Like Dad showed me. | Over, under, through. Like Dad showed me. |

**What they do to him** (DA_Move_* Narration)
| Move | Type | Now | New |
|---|---|---|---|
| Hang There | THINK | It's waiting for me. | It's just hanging there. |
| Sleeve Labyrinth | THINK | Where did the opening go? | There was a sleeve. Where's the sleeve. |
| Static Cling | THINK | It's sticking to me. | Why is it sticking to me. |
| Wrong Button | SAY | No. I just did that one. | Wrong hole. Start again. |
| Cold Toes | THINK | Why is the floor so cold? | The floor's freezing. |
| Swap Places | THINK | They were together a second ago. | That's not the same sock. |
| Twist | THINK | That's the wrong way round. | It's twisted. How is it twisted. |
| Kick | SAY | My leg. Watch the leg. | Ow. My shin. |
| Coil | SAY | I can't breathe. | Too tight. Can't breathe. |
| Strike | SAY | Keep it away from my face. | Not the face. |

The battle UI labels (WBP_Encounter: "Getting dressed", "Your move", "Watch the sleeves", the hint sentences) and the move descriptions (BP_Encounter MoveDetail) are functional UI and stay as they are. The one exception: "Complete the trousers if the timing succeeds." becomes "Complete the pants if the timing succeeds."

### T9: the payoff, the suit and the colour
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start (monologue) | THINK | They are just clothes. They weren't just clothes a minute ago. | I look like I have somewhere to be. |

### T10: Leave the house
| Trigger | Type | Now | New |
|---|---|---|---|
| Beat start (monologue) | THINK | The headache is still here. I can open the door anyway. | Head still hurts. Going anyway. |
| Door (open), Look | THINK | Open. The hallway is very bright. | It's so bright out there. |

## 5. The ending
At WalkedOut, the director fades to black (1 s). Then, for 2.5 s on black before EndOfLevel:

| Type | Line |
|---|---|
| CARD (centre, the intro's text style) | Day one. |

This is the bookend to "Seventeen days." The count starts over, and this time it counts. Approved. BP_BeatDirector shows it through the HUD subtitle on the black, in the end path before EndOfLevel.

## 6. The day rollover and his notes (SCREEN)
The notebook is his own phone notes, so they're terse, in his words, and useful the next morning. The rollover card shows the newly learned note. These are GI_FoA NotebookLines.

| Flag | Now | New |
|---|---|---|
| Knows.KeyInBoot | The key was in my left boot, under the bed. | Key's in my left boot. Under the bed. |
| Knows.KeySnaps | The key snaps in the lock. I don't need it. | The key snaps. Don't bother with it. |
| Knows.ScrewdriverInDesk | There is a screwdriver on the desk. | Screwdriver on the desk. |
| Knows.WardrobeFalls | Pulling the handle brings the wardrobe down. | Don't pull the handle. The wardrobe comes down. |
| Knows.DoorMoves | The door does not stay on its wall. | The door moves. Don't trust it. |
| Knows.ShirtPattern | The shirt hides the armhole first. | The shirt hides the armhole first. Find it, then button. |
| Knows.ClothingThread | A thread in the fallen wardrobe leads towards the papers on the desk. | Thread in the wardrobe, goes to the desk. |
| Knows.ClothingTrail | A button beneath the papers and marks in the dust point towards the bed. | Button under the papers. Marks to the bed. |
| Knows.ClothingSnag | The shirt is too far under the bed. A wire hanger can reach it. | Shirt's under the bed. Use the hanger. |

## 7. Prompts and objectives (UI and mech data, for main)
These stay plain imperatives. Only these change:

| Where | Now | New | Why |
|---|---|---|---|
| Door prompt (knows the wardrobe falls) | Pull the handle, and mind the wardrobe | Pull the handle | The thought now carries the warning. |
| Chase prompt | Grab the shirt beside the vase | Grab the shirt | Shorter. The shirt is highlighted. |
| Shirt prompt | Watch the shirt | Look at the shirt | Matches every other Look prompt. |
| HUD hint row | P Phone / Ctrl Crouch | P Phone    Ctrl Crouch | The "/" is a banned separator. |
| HUD tool hint | D / A Turn     Q Release | D A Turn    Q Release | The same separator rule. |

The objectives (DA_Beat_T0 to T10) stay as they are: "Wake up.", "Take a few steps.", "Find something to wear.", "Find the key.", "Unlock the door.", "Open the lock another way.", "Open the door.", "Find the missing shirt.", "Put on the shirt.", none at T9, and "Leave the house."

## 8. Who applies what
| Text | Asset | Builder | Applies |
|---|---|---|---|
| Intro | UI/Intro/WBP_IntroStory | Tools/LookDev | story |
| Beat monologues, director clothing lines, the ending card | Gameplay/BP_BeatDirector | Tools/Unreal/flow | story |
| Battle lines | Gameplay/Encounter/Data | Tools/Unreal/encounter/encounter_data.py | story |
| Interaction lines and prompts | Gameplay/DT_Interactions, DT_Items | Tools/Unreal/gameplay/data_rows.py plus Tools/Unreal/flow/apply_story_text.py (by-row patch) | story |
| The calendar lines (T2 table) | Gameplay/DT_Interactions, rows 900 and 901 (InteractionKey Calendar) | Tools/Unreal/level1/calendar_note.py FOA_STEP=rows (by-row append) | level1 |
| Notes | Gameplay/GI_FoA NotebookLines | Tools/Unreal/flow/apply_story_text.py | story |
| Phone messages, inbox, HUD hints | UI/Game/WBP_Phone, WBP_HUD | Tools/Unreal/ui | ui |
