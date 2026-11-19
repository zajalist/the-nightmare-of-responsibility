# T8 redesign: "Get Dressed"

Owner: battle lane. Data: `Tools/Unreal/encounter/rhythm_data.py`. Balance check: `Tools/Unreal/encounter/sim_rhythm.py`.

The user's verdict on the current fight was "the battle mechanics SUCK its still boring". This redesign keeps BP_Encounter, BP_Garment, the four garment rigs and their clips, the cameras, the dispatchers and the win and lose hand-offs. It replaces the menu-driven RPG rules underneath them.

## 1. Why the current fight is boring

Measured with `sim_party.py` (4000 runs) and from the live screen (`Saved/EncounterCaptures/battle_commands_held.png`):

| Problem | Evidence |
|---|---|
| No tension | A typical player wins 100% of fights, finishes with 52 of 100 Composure, and is never below half. Even a player who misses 60% of keys wins 71%. |
| Too long for what it asks | 15 turns at the median, 22 at p90. Every turn is a menu read, a narration line, a 1.6 s pause and up to five enemy acts. |
| Enemies do nothing | `HangThere` has weight 12 against 0.5 to 3 for every real move, so most enemy acts are "it hangs in the air and waits". |
| The player has nothing to do on their turn | Menu bookkeeping only: clear a status with move A, then press move B. The only skill check is Button Up's three keys, where two of three is enough. |
| No skill expression | A strong player (95% of keys) takes 12 turns, a typical one 15. Being good barely matters. |
| Ten options, two that matter | Find Armhole, Button Up, Deep Breath, Check Mirror, Items, Try to leave, Change target, plus Act moves per garment. Items and Try to leave are jokes with no effect. |
| Every garment plays the same | Each sub-garment is "clear my status, then progress me once". The Sock, Trousers and Tie differ only in text. |
| Knowledge does nothing | Knowing the pattern changes the median from 15 turns to 15 turns. |
| The theme sits in text, not hands | You read that you are getting dressed; you never feel it. |

## 2. What we take from the references

| Game | The lesson we use |
|---|---|
| Undertale and Deltarune | Each enemy's attack is its personality, as a short defence pattern. Some patterns ask you to do nothing (blue attacks), which we use for decoys. |
| Paper Mario | Your attack is a timed command. Doing it well is visibly better, and fumbling it is funny. |
| Hi-Fi Rush | Everything lands on the beat: idles, cues, hits and the HUD pulse. The rhythm teaches the timing. |
| Sekiro | Defence is offence. Perfect timing builds the thing that ends the fight. One perilous attack per phrase hurts much more than the rest. Delayed strikes punish button mashing. |
| Persona | A choice with pressure every turn: push now or wait. A flawless stretch earns a bonus turn. |
| Clair Obscur | Enemy turns are real-time: dodge to survive, parry for the counter. Turn-based structure, action hands. |

## 3. The fight in one paragraph

The clothes you picked up come alive and refuse to be worn. Each garment attacks with a short rhythm phrase, and every defence is a dressing motion: you catch the sock, hop into the trouser leg, catch the cuff, grab the tie. Good defence builds **Grip** on that garment. After each phrase you choose: **Dress** now, a short timed command whose timing gets easier the more Grip you have, or **Breathe** and let it come again. Land the Dress and the garment flies onto you. Fumble it and something stupid happens. Four rounds, dressed in the order people dress, each faster than the last. About three minutes.

## 4. Rules

**Keys.** Four verbs, taught one per round. On a gamepad: stick or D-pad left and right, A, X.

| Key | Verb | When |
|---|---|---|
| A or D | your hand on that side | the thing comes from that side: a sock lands, a leg kicks, a sleeve lashes |
| Space | hop | a trouser leg sweeps low |
| E | grab | the collar lunges, the tie strikes. Missing a grab hurts double |
| nothing | let it pass | a decoy: the odd sock, the tie's feint |

**The beat.** A round has a tempo. A phrase is 8 counts. Each cue shows as a ring closing onto the spot where it will land (left hand, right hand, feet, throat), 2 counts ahead, with its key inside. The garment's clip winds up on the same counts.

**Judgement.** Within 60 ms of the beat is Perfect, within 150 ms is Good, anything else is a miss.

| Result | Effect |
|---|---|
| Perfect | +2 Grip. A white ring burst, 4 frames of hit-stop on the garment, sand chips fly from the garment to you. |
| Good | +1 Grip. A smaller burst. |
| Miss or wrong key | Composure falls by the round's damage, Grip −1. 8 frames of hit-stop, a camera shake and a face-slip pulse. |
| Decoy left alone | +1 Grip. |
| Decoy pressed | The same as a miss. |

**Composure** is your health, 100 at the start. At zero the day is over. Each garment you get on gives back 15: being dressed steadies you.

**Grip** is per garment and caps at its need. It is the one bar on the garment.

**Your move**, after each phrase. Two words on screen, no menu.

| Choice | Key | Effect |
|---|---|---|
| Dress | E | Play the garment's Dress command. Its windows scale from 0.6x at no Grip to 1.5x at full Grip. Land three beats in four and it is on. |
| Breathe | Space | +10 Composure, and the garment attacks again |

A fumbled Dress costs 8 Composure, halves Grip, plays the garment's flub line and pose, and the garment attacks again. So the choice is real: dress early on low Grip with tight timing, or take another phrase to make the Dress easy.

**Flawless.** A phrase with every beat Perfect stuns the garment. It skips to Dress at full Grip (Persona's one more).

## 5. The garments

Each has a verb, a clip (all four rigs carry Lash, Kick, CoilStrike and Hop) and a joke. Phrases use `L R H G X .` as in section 4.

| Round | Tempo | Their phrases (in order, then repeating) | Clip | Your Dress | The hook |
|---|---|---|---|---|---|
| 1. Socks, a pair that isn't | 84 | `L...R...` `L.R.L.R.` `L.X.R.X.` | Hop | `L.R.G` left foot, right foot, pull | You catch socks out of the air with the hand they land on. The third phrase sends the odd sock: leave it. |
| 2. Trousers | 96 | `H...H...` `H.H.H.HH` `HH.L.HHR` | Kick | `H.L.H.R.G` hop, left leg, hop, right leg, zip | You jump rope over its legs. Stepping into trousers is hopping on one foot anyway. |
| 3. The Shirt, inside out | 104 | `L.R.L.R.` `LL.R.RG.` `R.RL.LRG` | Lash | `G.G.L.R` grab the hem, turn it, left arm, right arm | The sleeves lash from the side that rears back. Catching the cuff is putting your arm in. |
| 4. The Tie, on the Shirt's collar | 112 | `...G...G` `L.R.X.G.` `LR..X..G` `H.L.R..G` | CoilStrike | `GGGGGG.LRLG` six buttons, then over, under, around, through | It coils on the beat and strikes on the count after. It feints and goes very still. The H is your own trousers, which you are wearing, kicking you. |

**Lines.** One typed line per round start, per Dress win and per fumble. No narration during a phrase.

| Round | Enters | Fumble | On |
|---|---|---|---|
| Socks | Two socks hop out of the sand. They are not a pair. | You put a sock on your hand. It waves at you. | Socks on. They are warm, and somehow that is worse. |
| Trousers | The trousers stand up on their own and start to skip. | Both feet in one leg. You hop in a small, sad circle. | Trousers on. Both legs agree, for once. |
| Shirt | The shirt is inside out, and it knows. | Your head goes through a sleeve. It is very dark in there. | It is the right way round. It does not like that. |
| Tie | The tie uncoils from the collar like something that has waited all night. | A perfect knot. Around your wrist. | A full Windsor. You did not know you could. |

Win: "You are dressed. Nobody will ever know what it took." Lose: "You sit down on the bed, half dressed. The day is over."

## 6. Escalation, the win and the loss

- **Escalation.** The tempo climbs 84, 96, 104, 112. Each round adds one verb, then the Tie round mixes all four. Grab beats, the ones that hurt double, only arrive in rounds 3 and 4. Decoys arrive after the player trusts the pattern. In the last round your own trousers join in.
- **Each garment won.** 10 frames of hit-stop, the garment bursts to sand and flies onto you (`BP_FoAPlayer.Equip`), one large sentence, +15 Composure, and the next garment rises out of the sand.
- **The finish.** The sixth button and the knot play at 0.3x time for 0.6 s of real time, then a white flash, the full outfit and the victory line, then `ReportEvent("EncounterWon")`.
- **Low Composure.** Below 30: a heartbeat, the rings tremble, the face-slip holds higher. You feel close.
- **The loss.** Composure at zero: the garments drop limp into the sand, the lose line, then `FailDay()`.

## 7. Knowledge across days

The phrases are authored, never random, so tomorrow's fight is today's fight. Your memory is the main carry-over. The director already sets `Knows.ShirtPattern` when T8 fails, and the fight reads it:

- "You remember how this goes." The Socks and Trousers skip straight to Dress at full Grip, so a retry gets to the hard part in about 20 s.
- Practice: every window is 1.3x wider, and cues show 3 counts ahead instead of 2.
- The notebook line for mech_flow to use on the rollover card: "The tie strikes on the count after it coils. The odd sock is the grey one."

## 8. Numbers

`python Tools/Unreal/encounter/sim_rhythm.py 4000`. A player is a timing spread, a lapse rate and a decoy-press rate; the miss rate is per beat. Fight length includes the intro, lines and equip beats.

| Player | Misses | First day: win, median length, lowest Composure | Knowing the pattern: win, length |
|---|---|---|---|
| Strong | 3% | 100%, 2.2 min, 91 | 100%, 1.5 min |
| Typical | 15% | 98%, 2.7 min, 66 | 100%, 1.7 min |
| Struggling | 32% | 27%, 3.5 min, 23 | 95%, 1.9 min |
| Very weak | 49% | 0%, loses at 3.3 min | 32%, 2.1 min |

Old fight, for comparison: typical 100% in 15 turns, strong and typical barely different, knowledge no help. Here the time and the danger both follow skill, and a lost day buys a real advantage. These player models are guesses; the real tuning is hands on the prototype, then in PIE.

## 9. Screen

No menus and no party list. Darker Grotesque only, monochrome, using the ui lane's kit (`M_UI_Meter`, `M_UI_Ring`, `M_UI_Panel`, `M_UI_SandText`, `WBP_InputHint`).

- The garment's name and its Grip meter, top centre.
- Composure, bottom left, as a meter with its number.
- Cue rings on the player's body: left, right, feet, throat. Up to four live at a time.
- The choice: two words with key glyphs, centre, after a phrase.
- One typed line at a time, top, only between phrases.

## 10. Building it in Blueprint (about 3 days)

**Kept as is:** BP_Encounter's actor, components, cameras, ShowEncounter, CutTo, EndEncounter, SpawnParty and ClearParty, the outcome hand-offs, every dispatcher in the contract, BP_Garment with its rigs, clips and sway, `restore_encounter.py`, `pie_fight.py`'s driver pattern.

**Day 1: data and the beat engine.**
- `PDA_Opponent` gains Tempo, GripNeeded, Damage, Phrases (String array), Dress (String), DressLine, FlubLine, Clip. Four `DA_Round_*` assets come from `rhythm_data.py` (the old Opponent assets are renamed in place).
- The beat engine in BP_Encounter, Tick-free: `StartTrack(Pattern, Tempo, Scale)` stores the start time and sets a looping timer at half a count. Each tick cues the ring for the count `Lead` ahead (`OnCue(Index, Key, BeatTime)`) and expires any beat whose window has closed (a miss, or a passed decoy). `HandleKey` judges the earliest open beat: Perfect, Good or Wrong, and broadcasts `OnJudged(Result, Key)`.
- The states become Intro, Phrase, Choice, Dress, Equip, Victory and Defeat, through the same SetState pattern.

**Day 2: feel.**
- WBP_Encounter rebuilt to section 9: a pool of four ring images on `MI_UI_Ring_Parry`, two meters, the choice, the line. It binds `OnCue`, `OnJudged` and `OnChanged`.
- BP_Garment plays its clip so the strike frame lands on the beat (play rate from tempo), and a flub pose.
- Hit-stop with CustomTimeDilation on the garment and the pawn, the camera shake, the face-slip and sand-burst calls that already exist.
- The anim lane's reaction clips on the pawn if they land (catch, hop, flinch). Without them the pawn holds its battle idle.

**Day 3: wire and prove.**
- Knowledge path, finish slow-motion, low-Composure heartbeat.
- PIE win and lose videos through the real T7 shirt pickup, `foa_qa.py logs` with 0 Blueprint errors.
- Delete what is dead: the 20 `DA_Move_*` assets, `PDA_Move`, `sim_party.py`, `M_OpponentSway` if unused, the old command widgets.

**Cut from the old design:** Resolve, statuses, Items, Try to leave, Check mirror, Change target, enemy move weights, tiers and enrage, the party list, the command menu and its icons.

**Contract changes** (to land in `docs/mechanics/contract.md` with the build):
- `StartEncounter("Shirt")`, `ReportEvent("EncounterWon")`, `FailDay()`, `Equip(GarmentId)`, `OnChanged`, `OnDamage`, `OnGarmentEquipped`, `OnSandBurst`, `OnEncounterWon` and `OnEncounterLost` are unchanged.
- New dispatchers `OnCue(Index, Key, BeatTime)` and `OnJudged(Result, Key)`.
- `BattleState` values change to the seven above. Resolve, Statuses, Target, ChooseMove, Items, Flee and CycleTarget go away.

## 11. Risks

- **Timer resolution.** A half-count timer can report a miss up to a quarter second late. If that reads badly, run the expiry check from a per-beat one-shot timer instead.
- **Input latency.** UE input plus a 60 fps frame is about 30 to 50 ms. The 150 ms Good window absorbs it; if the Perfect window feels unfair in PIE, calibrate an offset rather than widen it.
- **Clip sync.** The rigs' strike frames are not marked. Day 2 measures them once per clip and stores the offset in the data.
- **Audio.** The beat needs a tick. The fabric snap and metronome come from the audio lane; until then the prototype's synthesized ticks are the reference.
