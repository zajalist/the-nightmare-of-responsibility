# Level 2: Find a job

Version 2, Revision 2 (merge), Level 2 design lane, 2026-11-10. Offline proposal for The Nightmare of Responsibility. No gameplay or assets changed. Fixed decisions are distinguished below from proposed numbers and pending story choices.

## Changelog

### Revision 2 (merge)

- User decided that human and Nightmare progressively glitch/merge into each other across Level 2. The visible merged writer replaces implied dictation and the proposed hard player swap at the boss; identity is no longer an open question.
- Linked merge amount to EMPLOYABILITY, with three readable rejection/edit reveals and sustained finale coverage. Reuse existing player sand transitions, Nightmare actor and splat assets; no new character generation or renderer dependency.
- Proposed a sparse merged voice on three lines, explicitly pending user approval of the change to the earlier speech limit.
- Re-derived the two possible endings: perfect lie completes the merge (recommended), honest page separates them. Updated dialogue, VO IDs, resets, scope and lane handoffs.
- Checked encounter source and saved runtime evidence: use the implemented Act/Breathe/Mirror battle, not the unwired rhythm redesign. Flagged the supplied splat mesh versus humanoid actor naming mismatch for asset verification.

### Changes retained from v1

- Three stops now supply information, rejection and a C.V refinement. One finale replaces The Form, The Shelf and The Interview fights, concentrating the new theme and reducing scope.
- Added EMPLOYABILITY as document progress, with explicit gains, losses, gates and displays. Composure remains local to driving and fighting; only driving can reset Level 2.
- Added Write the Perfect Employability C.V using Level 1's encounter system, including the integration work that new data alone cannot cover.
- Kept threshold, colour, fall, Toronto driving, meteors and colour exit. Shortened the colour path to fit the existing enclosed Dream A instead of assuming a 40 m world.
- Replaced the successful interview ending with a proposed completed application. The remaining story choice is the meaning of perfect; Level 1 Tidiness is also optional.
- Added pending dialogue IDs, delivery gates and lane ownership. The untouched original is design_v1.md.

## 1. Fixed decisions and voice

Only the road can fail Level 2. Encounters cannot. The city is Toronto lidar: Queen St W, 600 m east from Spadina toward University, monochrome, top-down while driving. The three employers are fictional destinations within this geography, not representations of real businesses.

The colour world uses the existing Aholo-generated Dream A: crimson sand, arches, a bed and a closed door. Day one. appears on the threshold's white. **Decided by the user:** the human and Nightmare visibly glitch/merge into each other over Level 2; the finale's half-lies come from that merged writer. This replaces the separate silent watcher's role in this level. **Speech change still needs OK:** section 7 proposes three restrained layered lines. Until approved, those lines play in his ordinary voice; the only standalone Nightmare line remains the optional restart Take your time.

Reuse MUS_Dream_Loop, MUS_CityDrive_Loop, MUS_Battle_Loop and stings. This slice requires no generating calls, purchases, downloads or new external sources.

Follow story/script.md: seventeen, tired, dry, short lines. SAY is under his breath; THINK is first-person present tense; BOX is the second-person encounter narrator. No explanatory speeches. Never show the word dream in player text. Darker Grotesque, no decorative separators, divider lines, middle dots or eyebrow labels. Any visible protagonist face retains horizontal slice distortion. Colour belongs to the bookends; the city and C.V fight stay monochrome.

## 2. Spine and sequence

Gather information, get rejected, revise the C.V, drive to the next place. Every rejection teaches a specific requirement. The information is useful; the increasingly inflated wording is the problem. He begins without job experience. Each inflated revision visibly merges him further with the Nightmare. Under the recommended perfect-lie ending, the completed page and the completed merge are the same achievement.

Keep driving and meteors: travel gives the three compact conversations a playable connection and preserves the user's sole failure space. Hazards are environmental, not punishment for lying. Rejection never triggers an unavoidable impact. There is no drive after the finale.

Target first clear: 15-20 minutes, untested. Do not pad content to meet it.

| Beat | Action | View | Target |
|---|---|---|---|
| L2-T0 Threshold | Bedroom door, dolly-zoom, white. Day one. on white, then colour eases in over about 3 s. | Sanctioned third-person cutscene | 14 s |
| L2-T1 Colour path | Near Dream A's closed door, follow 6-8 m of assembling sand toward the bed alcove. Sand subsides behind him; floor gives way. | First person | 30-45 s |
| L2-T2 Fall | Through the dune floor; colour drains; land on the Toronto street and get up. | First person | 10 s |
| L2-T3 Street | Phone, bus stop, still sand figures, Dad's car. Inspect empty C.V. Short 60-80 m strip at most. | First person | 1-2 min |
| L2-T4 Drive one | One teaching meteor; Career Center. | Top-down | 1-1.5 min |
| L2-T5 Career Center | Information, no placement, first C.V revision. His hand breaks into black grains and reforms. EMPLOYABILITY/merge 0 to 20. | Counter and phone | 1.5-2 min |
| L2-T6 Grocery | Drive with four meteors. Shelf interaction, rejection, logistics revision. Nightmare shoulders overlap his. EMPLOYABILITY/merge 20 to 40. | Top-down then one aisle | 2.5-3 min |
| L2-T7 Office | Drive with six meteors. Lobby bed as seat, availability question, rejection, reliability revision. His sliced face overlaps the Nightmare head. EMPLOYABILITY/merge 40 to 60. | Top-down then lobby | 2.5-3 min |
| L2-T8 C.V finale | The merged writer faces the returned document. Its truth attacks undo revisions and briefly restore human coverage. EMPLOYABILITY/merge 60 to 100. | Existing encounter UI | 3-5 min |
| L2-T9 Out | Submit the chosen ending's page. Application received. Complete merge or separation stays visible as the street opens to Dream A colour. | Short cutscene | 12 s |

Fixed route: Career Center, grocery, office. Each confirmed edit opens the next marker. Early turns toward locked destinations loop to the active route without cost. Alternate approaches are optional; no extra quest branch. After the office edit, fight at the same desk, without a fourth destination.

The colour path cannot fail. A solid proxy holds him until the scripted fall, even if visual sand crumbles while he waits. Stepping off also enters the same fall beat. No death volume or return to Level 1. Repeats can skip to the short fall.

## 3. Information, rejection, revision

Each revision is one preview-and-confirm action on the existing phone/C.V surface, not a text editor. Show original and replacement before Revise C.V. Ordinary actions are the seed of truth; the duration and professional title are unearned. These are fictional claims by the character, not real-world C.V advice.

| Place | Information and rejection | True line | Proposed replacement | Kept phone note |
|---|---|---|---|---|
| Career Center | Name an experience section. Household actions can be described. No placement without experience. Clerk gives both addresses, grocery first. | I have no job experience. | 5 Years of Experience in Interior Management. | They want experience. Start with the room. |
| All-Night Grocery | Notice lists stocking, sorting, inventory. One use action faces shelf labels. Thank you. The position has been filled. | I straightened some labels. | 3 Years of Experience in Warehousing and Office Logistics. | Stocking. Sorting. Inventory. |
| Office tower | Asked when he can start; gap in the page exposed. We need someone dependable. | I got out of bed today. | Available Immediately. Reliable Under Pressure. | They want someone who can start. |

Keep v1's ticket 18, NOW SERVING 17, still occupied chairs and clerk behind glass. Grocery retains every aisle numbered 9 and the polite PA; its separate Nightmare-at-the-end-of-the-aisle sighting is replaced by the overlap on his own body. Office retains no stairs or elevator and his made bed as its only seat; he sits, never lies down. Reuse the bed, desk, papers and sand figures. Three complete new interiors are unnecessary.

Conversations always permit their revision. No wrong answer blocks progression. Confirm once per stop; rereading or returning cannot farm progress. The grocery truth comes from its mandatory shelf action, not an optional Level 1 search. All three rejections happen even if the player performs every interaction perfectly. The stops are not combat encounters in the must-have slice. Each rejection briefly previews the next merge stage; only confirming the lie commits that stage. The same fixed interaction camera makes his body visible, without a reflection render target or a new exploration camera.

## 4. EMPLOYABILITY and Composure

EMPLOYABILITY measures the page's apparent completeness and suitability for the hiring process, not his worth, skill or chance of employment. Let the rejections and finished page demonstrate this without an explanatory speech.

### EMPLOYABILITY rules

- Start at 0. Each confirmed stop refinement adds 20 once per run: 20, 40, 60.
- The finale has three sections, each Resistance 4. Let P be their summed clamped progress, 0-12. During the fight, EMPLOYABILITY = 60 + floor(40 x P / 12). All sections complete gives exactly 100.
- Successful Rewrite actions raise P; existing perfect timing doubles progress. Setup, Breathe, Mirror, rereading and driving give no EMPLOYABILITY.
- Truth attacks remove section progress and lower the bar through the same formula. Completed sections cannot attack or reopen. Rejection does not erase earlier confirmed refinements.
- Battle defeat resets all section progress on retry, including sections completed in that attempt: EMPLOYABILITY returns to 60. Stop edits remain.
- Road failure clears the run and EMPLOYABILITY to 0. Learned phone notes survive; edits and route unlocks do not.
- No passive drain, no driving penalty to this bar, no permanent rejection penalty. Zero EMPLOYABILITY never fails the level.

Gates: each confirmed edit opens its next route. Three edit flags and 60 open the finale. Three complete sections give 100 and unlock the selected ending's editorial action: Submit C.V for the perfect lie, or Strip the claims followed by Submit C.V for the honest page. The honest ending cannot submit the false draft. Gate on flags/completion, not rounded display numbers. No score threshold can block the encounter needed to regain score. Reaching 100 never grants a job.

| Surface | Display |
|---|---|
| HUD on foot and driving | Compact EMPLOYABILITY bar and integer after first C.V inspection. Frozen during driving. Driving COMPOSURE separately labelled. Hide during cinematics. |
| Phone | Same bar/value above the three C.V lines. Learned notes use the existing notebook, not a new app. |
| C.V preview and encounter | Same bar above the page. Existing target progress becomes Revision. Battle Composure and Resolve retain separate labels. Show changed text alongside progress, without a theme-explaining toast. |

### Merge follows the page

During the job hunt and fight, MergeAmount = EMPLOYABILITY / 100, clamped 0-1. It is a visual driver, not another bar, ability, currency or failure condition. Rejection pulses are temporary previews; driving damage never increases it. Truth attacks lower both draft progress and visible merge; retry returns both to 60%, road restart to 0%. The honest-page ending, if chosen, is the sole terminal exception: the completed truthful page stays at 100 EMPLOYABILITY while a scripted separation takes MergeAmount to 0. Section 7 defines the visual implementation and endings.

### Why keep Composure?

Road Composure is the sole survival resource. Battle Composure preserves Level 1's recovery, Resolve economy and telegraph decisions, but zero ends only a local attempt. Replacing it with EMPLOYABILITY would turn revision progress into health and change the battle's rules. Resolve exists only in battle. Walking, rejection and phone actions drain neither resource.

Drive Composure begins at 100 each leg. Impact costs: avoided 0, correctly braced 0, late brace 15, unbraced 40; clamp at 0. Three unbraced hits fail a leg. The one-meteor teaching leg cannot fail from its meteor alone. Proposed telegraph: 2.5 s, final brace window 0.4 s, longer teaching cue. Avoid with lane change, braking or a signalled turn. Show the actual bound Brace key. Use ring shape, text and sound so monochrome and muted play remain readable.

Start with 1, 4 and 6 finite scheduled meteors. No overlap in the slice. Braking may wait out a hazard; waiting does not respawn punishment. Later overlap needs proof that avoidance or brace is always possible. Never obscure the next cue with impact effects. Buildings dissolve to black sand and re-form over about 3 s; road lanes and collision proxies stay stable.

## 5. Finale: Write the Perfect Employability C.V

Three panels lift out of one page. Letters stretch below its margins; original words bleed through the replacements. The document is the eldritch opponent, without a new humanoid rig, mouth or voice. Use existing page/plane geometry, text widgets and sand effects. Keep the truths readable in the BOX log while world text distorts.

### Existing system, verified offline

Sources: docs/mechanics/contract.md and Tools/Unreal/encounter/{encounter_data.py,build_encounter_data.py,build_encounter_bp.py,build_garment_bp.py,build_move_detail.py,sim_party.py}.

BP_Encounter.StartEncounter(OpponentId) chooses a PDA_Opponent leader and its Party; BP_Garment holds Progress/Resistance. WBP_Encounter supplies commands, targets, narration and timing. Rows are DA_Move_* and DA_Opponent_* data assets, not DT_Moves/DT_Opponents. Move fields include ResolveCost, ComposureDelta, ResolveDelta, ProgressDelta, status flags, bTimedInput, bStuns, bRevealsNext and TelegraphLine.

Reuse Intro, PlayerCommand, ResolvePlayerAction, EnemyPhase, CheckEnd, Victory and Defeat; Act, Breathe, Mirror, target selection, timing prompts, queued telegraphs, status clearing, recovery and dispatchers. No typing minigame or new combat engine.

**Mech lane battle choice:** build the C.V finale on the implemented Level 1 menu-driven turn battle in BP_Encounter, with Act, Breathe, Mirror, Resolve, statuses and timed rewrites. The 11-07 docs/design/battle/battle_redesign.md describes a rhythm replacement, but it is a proposal/offline simulation in the checked source, not a wired replacement: `rg -n 'rhythm_data|DA_Round_|GripNeeded|S_Phrase|S_Dress' Tools docs/mechanics docs/agents -g '*.py' -g '*.md' -g '*.json'` found no encounter builder consuming rhythm_data.py; its only Python importer is sim_rhythm.py. build_encounter_data.py imports encounter_data as D; build_encounter_bp.py still authors PlayerCommand/ResolvePlayerAction/EnemyPhase and ChooseMove; build_encounter_widget.py calls ChooseMove. Saved/PresentationReview/battle_runtime.json (Nov 8) records those states with a passed native-input presentation result; Saved/Integration/cinematic_audit/live_battle_command.json records PlayerCommand at 2026-11-08T11:07:42Z. This is the strongest offline evidence of what L1 actually runs. The simulator's docstring claiming parity with BP_Encounter is not wiring evidence. Do not implement the rhythm rewrite for L2 or change L1's rules; today's binary editor state and a packaged build were not inspected.

### Proposed L2 data rows

These IDs are proposals, not existing assets. Keep all L1 rows unchanged.

| Opponent row | Section | Resistance | Act rows | Enemy rows |
|---|---|---|---|---|
| DA_Opponent_CVExperience, leader | Experience | 4 | CVFindDetail, CVRewriteExperience | CVOriginalExperience, CVBlank, CVWait |
| DA_Opponent_CVLogistics | Skills | 4 | CVSortFacts, CVRewriteLogistics | CVOriginalLogistics, CVMisfile, CVWait |
| DA_Opponent_CVReliability | Availability | 4 | CVLoosenClaim, CVRewriteReliability | CVOriginalReliability, CVConstrict, CVWait |

Leader Party: CVLogistics, CVReliability. StartComposure 100, StartResolve 40, DrainPerTurn 2, proposed KnowledgeFlag Knows.CVPattern. No garment equipment IDs or required rigs. Three panels appear together and can be targeted in any order; they form one fight.

| Player command | Existing move model | Proposed effects |
|---|---|---|
| Breathe | DeepBreath unchanged | +5 Composure, +15 Resolve, blocked by Constricted; caps 100 and 40. |
| Mirror, detail Read it back | CheckMirror unchanged | Cost 5 Resolve, +20 Composure, reveal queued intents. Keep the command Mirror; reflect the page. |
| Find a detail | FindArmhole | Cost 0; apply ArmholeFound, clear SleeveLabyrinth. L2 labels: Detail found, Blanked. |
| Rewrite experience | ButtonUp | Cost 10; progress +1, timed; blocked by SleeveLabyrinth; ArmholeFound widens timing, consumed on use. |
| Sort the facts | MatchPair plus existing stun flag | Cost 0; clear Mismatched; stun selected Skills panel for next action. L2 label: Misfiled. |
| Rewrite skills | PullOn | Cost 5; progress +1, untimed, blocked by Mismatched. Reliable progress without timing. |
| Loosen the claim | Loosen | Cost 0; clear Constricted; stun selected Availability panel. L2 label: Cornered. |
| Rewrite availability | TieKnot | Cost 5; progress +1, timed, blocked by Constricted. |

Costs above are Resolve. Timed moves keep three prompts: two hits give +1, three +2, fewer than two no progress. Retain timing widths and boost, not a faster L2 test. Failed timing spends the declared cost. Setup/recovery consume turns. Internal status names can remain, but all displayed descriptions/remedies must refer to the C.V.

| Enemy move | Truth/action | Telegraph before resolution | Effect and response |
|---|---|---|---|
| CVOriginalExperience | I have no job experience. | You see the old line through the ink. | WrongButton model, -8 Composure, -1 own progress; add bTelegraphed. Finish the section first or recover and accept the revision loss. |
| CVBlank | Experience field whites out. | None; status appears when applied. | SleeveLabyrinth model; Find a detail clears it. |
| CVOriginalLogistics | I straightened some labels. | You see the shelf under the heading. | Kick model, -10 Composure; add -1 own progress. Sort the facts cancels its next action. |
| CVMisfile | Skills move to the wrong field. | None. | SwapPlaces status model; Mismatched, but bSwapsTwin false because no twin socks exist. Sort the facts clears it. |
| CVOriginalReliability | I got out of bed today. Seventeen crossed-out days appear. | You see seventeen boxes fill in. | Strike model, -12 Composure; add -1 own progress. Loosen the claim cancels its next action. |
| CVConstrict | Margins close around availability. | None. | Coil model, Constricted; Loosen the claim restores Breathe and Rewrite availability. |
| CVWait | Page holds still. | None. | HangThere, zero deltas, short log hold. |

Starting weights per panel in Plausible/Suspicious/Open: Original 2, status move 1, CVWait 1. PoolEnraged: Original 3, status 1, CVWait 0. Proposed tuning, not measured balance. The original battle's heavy idle weighting would waste this finale. Telegraphs remain visible during the player's decision. Mirror reveals other hidden intents; it is not required to see a dangerous tell.

### Three phases, no new combat state machine

1. **Draft:** all panels stand, showing the phone's edits, each at 0/4 battle progress. Give the first player command before damaging resolution, with queued telegraphs visible. Move details teach setup and rewrite.
2. **Proof:** one or more sections complete. Each folds flat, stops attacking and stays complete for that attempt. Remaining panels use the existing enraged pool below 30% resistance remaining: at progress 3 of 4. Truth attacks become more frequent near completion. No global phase-only move or fixed target order.
3. **Submission:** all complete; existing Victory, EMPLOYABILITY 100 and full visible merge. Page lies flat. Under the recommended perfect-lie ending, Submit C.V accepts both the half-lies and the merged writer. Under the honest-page alternative, one Strip the claims action restores the true lines and visibly separates them before Submit. No final QTE. Both end with Application received and colour; section 7 gives the exact completion conditions.

These phase names are design terms, not extra HUD labels. No fourth opponent, second health pool or forced replay between sections.

### Win and local loss

Battle Composure 0 uses Defeat presentation, then the same lobby desk and Retry draft. Reset Composure, Resolve, statuses and all battle progress on retry. EMPLOYABILITY and merge return to 60%; three stop edits, routes and Knows.CVPattern remain. Restore materials, pose and camera from the interrupted effect before reapplying that baseline. No day increment, road trip, threshold, Nightmare line or FailDay.

Retries are unlimited. Reuse the knowledge system's revealed opener/free first Mirror where supported. After a failed attempt offer Finish without timing: same moves and costs, timed moves give normal +1, never perfect +2. This small L2 assist is proposed work, not existing functionality. It removes timing lockout; recovery and targeting still matter.

CheckEnd currently tests completed targets before zero Composure: preserve victory precedence on simultaneous completion/zero. Route outcomes exactly once. Submit after victory and the selected ending's required editorial action records completion and exits directly to colour. Retain a finale-complete flag in the current run so EMPLOYABILITY stays 100 after encounter actors/UI close. Application received is not an interview or offer: Find a job remains unchecked; phone note becomes C.V sent.

### Necessary integration beyond rows

Mech owns a small L2 context on the shared encounter, defaulting to current L1 behavior. The exact property name is an implementation choice.

- **Outcome:** current defeat calls BP_BeatDirector.FailDay directly; victory reports EncounterWon for T9. Route L2 defeat to local retry and victory to submission; retain both L1 paths. OnEncounterLost alone cannot prevent that existing FailDay call.
- **Completion:** current code calls BP_Garment.Equip, OnGarmentEquipped and BP_FoAPlayer.Equip. For L2 fold the panel and record progress; suppress attach/equip and clothing-specific reactions. Empty GarmentId alone is insufficient.
- **Data:** register CVExperience in opponent lookup and add party/move assets. build_encounter_data.py indexes D.RIGS[oid]; add a safe no-rig path for these rows without affecting L1 rigs.
- **UI:** contextual title, status labels, completed state, prompts and move details. build_move_detail.py compares specific DA_Move objects; cloned rows need matching descriptions. Audit choice, monologue, contact/acting and presentation builders for garment-specific lookups.
- **State:** one derived EMPLOYABILITY value feeds HUD/phone/C.V on OnChanged. Bind once, clear timers and input on outcomes, clear L2 context before L1 reuse. Submit/retry wait until EndEncounter releases camera/input locks.
- **Implementation verification:** one small offline self-check for once-only edits, formula bounds and reset paths; L1 win/loss regression; L2 defeat/retry, assist, victory/submission and no-equipment proofs. No code or tests are changed by this design lane.

## 6. Road restart and persistence

Only Drive Composure at 0 requests a Level 2 restart. Fall, rejection, EMPLOYABILITY 0 and battle defeat cannot call it.

Stop car/hazard timers, clear input, drop top-down toward first person, short vertigo/sand transition, Another morning. Optional Take your time. once per Level 2 session on the first road restart only. The optional restart line does not acquire a second layer; the proposed merged delivery is confined to section 7's three approved-only cues. Clear any in-flight merge effect and voice tail before the threshold.

Restart at the L2 threshold, not bedroom gameplay. Clear stop flags, edits, battle progress, EMPLOYABILITY, route unlocks, hazards and submitted state. Keep learned notes, accessibility settings and the L2 road-attempt count. Day one. appears on first white crossing; subsequent cards are Day two., Day three., etc. Increment once per road failure, never per C.V retry.

Threshold/fall have short skippable versions; street interactions become optional, seen conversations can fast-forward to edit confirmation. Notes help anticipation but never pre-award +20 revisions. Restore full road Composure at each leg start. No battle health carries into driving. L2 reset must not call Level 1's room reset. Clear MergeAmount to 0, detach/hide the L2 effect shell, restore cached materials/groom visibility/FaceSlip and release any MPC pulse ownership. Known notes do not carry a merged body into the next run.

Future game-flow proofs must call GI_FoA.SetProofProgressContext('FoA_QA_Play') first and never modify FoA.sav. No runtime proof was performed here.

## 7. The merged writer: decided identity, proposed treatment

The user's decision: "the human and nightmare are gonna be kinda merged so in level 2 we can see them glitch/merge into each other. we had already made a nightmare character with aholo."

Identity is settled. He and the Nightmare gradually occupy the same body; the writer at the desk is both. No implied offscreen dictation, separate puppet-master dialogue or hard possession switch at the boss. Keep his first-person thoughts and player controls continuous. The horror is visible before anyone describes it.

### Cheapest readable visual set

Choose three short rejection/edit transformations plus the finale's persistent merged body. Use a single 0.6-0.8 s dissolve/re-form per cue and a readable hold, not literal one-frame flickers that disappear at low frame rates. Each rejection previews the next stage once, then settles back to current MergeAmount; confirmation commits the new amount. Re-reading does not retrigger it. No pulse changes EMPLOYABILITY. His ordinary sand overlay carries the new baseline between staged views.

| Beat and merge | What appears on screen | Build and owner |
|---|---|---|
| Entry, 0% | Human in the suit, existing face distortion. No independent Nightmare inserted into Dream A. | anim/face retain existing presentation. |
| Career rejection then 20% edit | While the form returns, his visible wrist/hand becomes black grains and reforms in the same place. On confirmation, grain patches remain. | anim reuses the interaction pose/camera; horror/player use SetSandOverlay and a short SetSandTransition pulse with pooled sand. |
| Grocery rejection then 40% edit | Forearms and shoulders become sand; the heavier Nightmare shoulder/head outline overlaps his during the held edit. It settles into the same outline rather than walking away. | anim registers one collisionless BP_Nightmare visual shell to the stationary pose; horror dissolves/re-forms it while the human coverage falls. No new rig or skin weights. |
| Office rejection then 60% edit | Bed-edge/desk view holds both torso and head. Horizontal face slices expose a dark Nightmare head underneath; the outlines share the same eye line. | face drives existing MPC_Dream.FaceSlip treatment; anim aligns the existing head/shoulder silhouette, horror supplies sand reveal. This is masked overlap, not a facial morph. |
| Finale, 60-100% | Existing battle cameras show the writer and page together. Each successful rewrite leaves more Nightmare coverage. A truth attack exposes more human face/suit as the bar falls. At 100 only the combined black silhouette remains, still performing his existing writing/reach pose. | mech passes the derived amount on progress changes; horror/player reuse the same shell and coverage response; face preserves distortion. No camera cut or flash for every keypress. |
| Exit | Perfect lie: the merged outline remains against Dream A colour. Honest page: grains peel off, human reforms and the Nightmare stands separately behind him. | anim/horror reuse the same actors and reverse the effect only for the selected honest ending. ColorReveal belongs to the surroundings/bookend, not merge progress. |

The three interaction views must actually include the affected hand/shoulder/head. Adjust the existing camera framing rather than pretending a first-person face change is visible. A fixed over-shoulder/profile hold at the stop is enough; no mirror render target. During free locomotion retain the player's existing skin/sand overlay and face effect; do not attempt full-time skeletal matching of the two bodies. In battle use the established stationary acting/contact pose windows. Only the shell's visible components follow those transforms; never attach an AI-controlled pawn as a second collision body.

Skip mandatory meteor silhouette overlaps: the driver is too small in the top-down camera. A brief overlap at a braced impact is optional after readability tests, using the current merge amount and no extra gain; it must not cover the road cue. The three rejection/edit views and battle cannot be cut in its place. ReduceMotion uses one slow dissolve and static overlapped hold, without stutter, shake or rapid slice pulses; the merge must still read with sound off.

### Existing assets and honest implementation boundaries

The user supplied `/Game/FoA/VFX/Splats/Meshes/SM_TheNightMare`, `/Game/FoA/VFX/Splats/Instances/MI_Splat_NightMare` and `/Game/FoA/Characters/Player/BP_Nightmare` (L1 actor label Nightmare). Reuse these existing sources; do not generate a replacement character or change the L1 placed actor/CDO for L2 effects.

**Asset identity discrepancy to resolve before visual integration:** Tools/Splats/sand_instances.py labels SM_TheNightMare/MI_Splat_NightMare as the galloping rollover mount, with mane/tail settings. Tools/Unreal/player/build_nightmare.py gives BP_Nightmare a black-sand humanoid Manny mesh, not that splat mesh; the inspected contract agrees. The user confirms an Aholo Nightmare character exists, but these files do not prove that the supplied mesh is its humanoid face. World/anim should identify the existing humanoid source first. Until resolved, the buildable visual baseline is BP_Nightmare's existing humanoid outline plus the player's sand coverage; the supplied splat mesh/material is only suitable as dispersed grains with its mount-specific motion disabled, not as an asserted human head. If its authored shape cannot disappear into a neutral grain pulse cleanly, use the existing pooled burst and leave that mesh unused in the merge. Do not spend days converting a mount into a person. Ask the user for the intended existing character asset only if coordinator/world cannot resolve this mapping; no new generation is needed or authorized.

- **Human side:** BP_FoAPlayer.SetSandOverlay already supports sparse-to-full coverage (ordinary baseline 0.06, full sand 1). SetSandTransition(Amount, Enable) already caches material slots and groom visibility, uses a masked sand silhouette, then restores them. Its Amount 1 means fully visible sand, 0 invisible; it is not a skeletal-to-splat morph. For held transformations reuse this with pooled BPL_SandFX bursts to bridge the silhouette change. Restore first, then reapply the current merge overlay, because disabling the transition restores the ordinary 0.06 baseline. Keep actual pawn, capsule, input and outfit data unchanged.
- **Nightmare side:** use one L2 instance of BP_Nightmare as a visual shell; stop stalking/movement and collision, register its head/shoulders in the fixed pose. Its Appear currently enables collision and fires a tear timer, so calling Appear alone is unsafe for this overlap: anim/mech must suppress those behaviors in L2 and restore them only for ordinary actor use. Reveal/cull the shell with existing masked-material coverage or a small L2 material adaptation; existing Appear/Vanish is not a blend API. Cache and restore all modified visibility/pose/material state on interruption.
- **Splats and epicentre:** reuse per-splat hash dissolve/re-form and small WPO displacement from the existing sand material pipeline. Horror owns a proposed hero-only MPC epicentre/time pulse, centred on the visible wrist then chest/head, and per-instance merge amount; these hero merge bindings are new wiring, not claimed existing functions. Scope the material response to the shell/hero pulse so a city impact cannot dissolve the writer and a writer pulse cannot dissolve a building. Use the same radial math as city shockwaves with a separate hero channel, or sequence pulses if a shared effect slot is reused. Keep the broad city WPO separate. Verify parameter direction: flow_lib.hlsl uses event dissolve 0 intact to 1 gone, whereas the older Tools/Splats/README.md calls coverage Dissolve 1 visible. Bind to the actual material path, never assume polarity from the name.
- **Face and colour:** retain the human's stencil-4 face slice treatment; BP_Nightmare uses stencil 2 for its tear effect. A component has one stencil value, so do not overwrite one with the other. Align the dark head through the slice gaps, reducing human coverage at peak merge; do not promise a detailed Aholo face until the source mapping is checked. Face lane tunes readable minimum/maximum FaceSlip, with no clean face reveal. Keep body/shell black through the existing sand/mono path while BP_DreamDirector.SetColorReveal returns the surroundings to colour at exit.
- **Renderer:** splat_runtime_plugin.md describes an uninstalled HaybaSplats spike, GPU bench pending. Its current scene-view extension lacks per-actor transforms/visibility, custom stencil and moving-splat velocity: precisely what this moving character effect needs. Use today's component-based static splat meshes and skeletal masked coverage. No installation, runtime plugin or production vertex-factory work is required. Do not treat the spike's console dissolve/shock commands as an existing Blueprint API.
- **Budget:** one reused shell, no copies per limb. The budget report groups the named sources at about 40k splats each; actual chosen asset count needs verification. Include the hero in the existing live-splat budget, not on top of it. Keep stop/finale pulses away from city impacts and cull the city while inside. Only staged transforms need alignment; no new retargeted animation set. No performance claim is made here.

Mech drives one normalized value from existing bar state; horror implements one reusable reveal/re-form cue; anim owns visibility, fixed-pose alignment and reset; face owns the head treatment. On truth loss, ease to the lower value without erasing the player's identity or changing control. On local retry restore the 60% baseline. Road failure cancels effects and restores 0% at the threshold. Ending state persists through the exit shot, then all temporary materials, MPC pulses, timers and actor visibility restore before any next-level/L1 handoff.

### Sparse merged voice: approval needed

**This changes the previous one-line-only Nightmare speech rule and needs the user's OK.** Recommend a second timbre underneath the same first-person line, never a conversation between separate speakers. Process a copy of the protagonist's own recording with a restrained lower/formant-filtered layer, no new synthesis or impersonated voice. Keep the dry voice intelligible, no theatrical growl, echo train or extra words. Audio tuning and intelligibility still need listening tests.

Only three cues may carry the layer: grocery edit at 40% (just the last word), office edit at 60% (quiet under the short line), and the final submission thought at 100% (one coherent blended delivery). Career's 20% reaction stays human. Do not layer every repeated combat move. One subtitle, THINK, no extra NIGHTMARE speaker label. For the honest ending the final thought loses the layer as separation finishes. Candidate IDs/treatments are in section 9, marked pending approval. If not approved, play ordinary human takes and let the visible merge carry the idea. The previously allowed optional Take your time. stays once on the first road restart, never on local retry; no added standalone Nightmare dialogue.

### Remaining ending choice: what does perfect cost?

The C.V fights with the truth. Restoring an exaggerated line increases both EMPLOYABILITY and merger; a truth strike briefly gives him more of his human body back. Thus combat victory can complete the document while completing the frightening change. The merge is never a game-over condition.

| Ending | Completion condition and image | Theme and cost |
|---|---|---|
| Perfect lie completes the merge. Recommended. | Finish all three sections (P=12), reach 100 EMPLOYABILITY/merge, then Submit C.V. The false experience claims remain over faint original text. The writer is one black outline, no separate watcher. Application received. In Dream A colour his outline stays black. | The form accepts a person he has written into existence. No job offer, triumphal reassurance or new branch. Cheapest continuation of the half-lie fight and the user's merge direction. |
| Honest page separates them. | Same fight reaches full draft and peak merge. Before submission, Strip the claims replaces the three lines with No paid work yet. / Shelf tasks. / Available to learn. Human reforms while the Nightmare separates behind him. Submit the corrected page; Application received. | Completing the page requires refusing its inflated identity. EMPLOYABILITY stays 100 as document completion; a terminal HonestPage flag overrides MergeAmount to 0. Reuse the effect in reverse and relocate the same shell; add one confirmation and closing text, not a second boss or moral meter. |

Both keep the existing all-targets-complete battle Victory; Level 2 completes only after the selected ending's final editorial action and submission. Under honest-page rules, Submit stays unavailable until Strip the claims, and victory does not auto-send the false draft. Neither ending rewards battle failure, requires road failure or promises employment. Implement one user-selected ending; these are production alternatives, not two player-selectable routes. Recommend perfect lie: the visible merger is the price of reaching the bar's goal, and the uncelebrated acknowledgement preserves the austere tone. Honesty would deliberately change that payoff. No choice about who writes remains open.

## 8. Level 1 Tidiness

Before this rewrite, offline grep on 2026-11-10:

`rg -n -i 'tidiness' docs Tools/Unreal Config -g '*.md' -g '*.py' -g '*.html' -g '*.ini'`

Only hit: Graph tidiness in docs/agents/HANDOFF_CODEX.md. No gameplay Tidiness bar in searched source/design/config. Encounter data uses Composure/Resolve; the contract uses beats. This is source evidence, not an editor inspection of every binary widget.

**User choice:** A, leave Level 1 alone (recommended); B, add a derived TIDINESS bar for T2-T7. Those tasks are not cleaning: the door breaks and wardrobe falls. The label may promise something the player cannot do. EMPLOYABILITY needs no paired L1 meter.

If B: reuse HUD bar style and six unique beat completions, no chores, saved resource or battle bonus. T2 search container; T3 obtain key; T4 exhaust key route; T5 free latch by either route; T6 complete handle/wardrobe beat; T7 recover shirt. Value = floor(100 x completed / 6): 16, 33, 50, 66, 83, 100. Use beat transitions, not repeated interaction clicks. Knowledge shortcuts count bypassed required beats once. Reset on new day; never decrease within the day. Gate nothing. Show only on room HUD/phone, hide in battle/cinematics. This requires separate approval/work; it is not implemented here.

## 9. Dialogue and pending VO

These tables are the proposed L2 script. CLERK, PA, RECEPTIONIST and optional RADIO remain v1's offscreen voices; text-only presentation is acceptable for the slice. BOX is text-only. No new C.V voice or cast face. SAY/THINK and offscreen voice candidates have VO_L2_<BEAT>_<NAME> IDs, all **pending**, including retained v1 lines. IDs reserve slots, not recordings. Do not edit vo_script.json in this lane. NIGHTMARE has only the optional standalone restart line. The merged writer keeps SAY/THINK and one subtitle; three THINK rows below propose a second timbre on the same words, explicitly awaiting user OK. Replaced VO IDs are retired from this design only, not deleted from any manifest.

### Threshold, path, fall and street

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| CARD | Day one. | First crossing, on white | Text only |
| THINK | Colour. Since when. | Control returns | VO_L2_PATH_COLOUR pending |
| THINK | Okay. Walk. | First trail patch assembles | VO_L2_PATH_WALK pending |
| SAY | Don't stop. Don't stop. | Trail subsides behind him | VO_L2_PATH_KEEPGOING pending |
| THINK | That's it? | Floor opens | VO_L2_PATH_END pending |
| THINK | The sun's in the wrong place. | On his back in the street | VO_L2_FALL_SUN pending |
| SAY | Still in the suit. Good. | Gets up | VO_L2_FALL_SUIT pending |
| SCREEN (MOM) | Did you go out? | Phone buzz | Text only |
| SAY | Yeah. Sort of. | Reads Mom's message | VO_L2_STREET_REPLY pending |
| GOAL | Find a job | Phone list and HUD | Text only |
| SCREEN | I have no job experience. | First C.V inspection | Text only |
| THINK | That part's finished. | Reads empty experience section | VO_L2_STREET_EMPTY pending |
| SCREEN | Later | Every bus departure, optional look | Text only |
| THINK | Dad's car. | First look at car | VO_L2_STREET_CAR pending |
| THINK | Keys are in it. Of course they are. | Gets in | VO_L2_STREET_KEYS pending |
| RADIO | Meteors are expected after nine. Drive carefully. | Optional first-drive radio | VO_L2_DRIVE_FORECAST pending |

### Drive and arrival

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| THINK | That's a shadow. | First meteor cue | VO_L2_DRIVE_SHADOW pending |
| PROMPT | Hold {BraceKey} to brace | Teaching cue, actual binding | Text only |
| SAY | Okay. Still driving. | First successful brace | VO_L2_DRIVE_BRACED pending |
| SAY | Hands on the wheel. | First unbraced hit | VO_L2_DRIVE_HIT pending |
| THINK | It just put itself back. | First building reforms | VO_L2_DRIVE_REFORM pending |
| THINK | Breathe. In for four. | First low-Composure warning per leg | VO_L2_DRIVE_LOW pending |
| SCREEN | Career Center | First marker/arrival | Text only |
| SCREEN | All-Night Grocery | Second marker/arrival | Text only |
| SCREEN | Office | Third marker/arrival | Text only |

### Career Center, rejection and first revision

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| SCREEN | NOW SERVING 17 | Counter display | Text only |
| THINK | Eighteen. Of course it's eighteen. | Takes ticket | VO_L2_CAREER_TICKET pending |
| CLERK | Previous experience. | At glass | VO_L2_CAREER_ASK pending |
| SAY | I haven't had a job. | Answers | VO_L2_CAREER_NONE pending |
| CLERK | What have you done at home? | Information | VO_L2_CAREER_HOME pending |
| SAY | Mostly stayed there. | Response | VO_L2_CAREER_STAYED pending |
| CLERK | Put it under experience. | Information | VO_L2_CAREER_SECTION pending |
| CLERK | No placement without experience. | Rejection after advice | VO_L2_CAREER_REJECT pending |
| CLERK | These two are taking applications. | Grocery and office addresses | VO_L2_CAREER_ADDRESSES pending |
| SCREEN | I have no job experience. | Original line | Text only |
| SCREEN | 5 Years of Experience in Interior Management. | Replacement preview | Text only |
| THINK | I wrote that. | First edit confirmed; his hand reforms at 20%, human voice only | VO_L2_MERGE_FIRST pending |
| PROMPT | Revise C.V | Confirm, +20 once | Text only |
| SCREEN | They want experience. Start with the room. | Notebook note | Text only |

### Grocery, rejection and second revision

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| PA | Staff to aisle nine. | Enter | VO_L2_GROCERY_CALL pending |
| THINK | Every aisle is aisle nine. | Read signs | VO_L2_GROCERY_AISLES pending |
| SCREEN | Stocking. Sorting. Inventory. | Job notice | Text only |
| PROMPT | Face the labels | One shelf interaction | Text only |
| SAY | They're straight now. | Interaction completes | VO_L2_GROCERY_DONE pending |
| PA | Thank you. The position has been filled. | Rejection | VO_L2_GROCERY_REJECT pending |
| THINK | There's nobody here. | Empty aisle | VO_L2_GROCERY_EMPTY pending |
| SCREEN | I straightened some labels. | Original line | Text only |
| SCREEN | 3 Years of Experience in Warehousing and Office Logistics. | Replacement preview | Text only |
| THINK | That's my hand. | Second edit confirmed; 40% merge, proposed low layer on hand only | VO_L2_MERGE_HAND pending; layered delivery needs OK |
| PROMPT | Revise C.V | Confirm, +20 once | Text only |
| SCREEN | Stocking. Sorting. Inventory. | Notebook note | Text only |

### Office, rejection and third revision

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| THINK | No stairs. No elevator. | Enter lobby | VO_L2_OFFICE_LOBBY pending |
| THINK | That's my bed. Mom made it. | Look at seat | VO_L2_OFFICE_BED pending |
| RECEPTIONIST | Take a seat. | At desk | VO_L2_OFFICE_SEAT pending |
| THINK | Sitting. Not lying down. | Sits on edge | VO_L2_OFFICE_SITTING pending |
| RECEPTIONIST | When can you start? | Information | VO_L2_OFFICE_START pending |
| SAY | Today. I'm here. | Response | VO_L2_OFFICE_TODAY pending |
| RECEPTIONIST | There is a gap in your history. | Reads page | VO_L2_OFFICE_GAP pending |
| SAY | Seventeen days. | Response | VO_L2_OFFICE_DAYS pending |
| RECEPTIONIST | We need someone dependable. | Rejects, returns page | VO_L2_OFFICE_REJECT pending |
| SCREEN | I got out of bed today. | Original line | Text only |
| SCREEN | Available Immediately. Reliable Under Pressure. | Replacement preview | Text only |
| THINK | I can write that. | Third edit confirmed; 60% merge, proposed quiet second timbre under line | VO_L2_MERGE_WRITE pending; layered delivery needs OK |
| PROMPT | Revise C.V | Confirm, +20 once | Text only |
| SCREEN | They want someone who can start. | Notebook note | Text only |

### Finale, moves and phases (merged writer; perfect-lie ending proposed)

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| GOAL | Write the Perfect Employability C.V | Encounter title | Text only |
| BOX | You put the page down. It stands up. | Intro | Text only |
| THINK | My name. Still my name. | Merged writer sees the panels rise; ordinary voice | VO_L2_MERGE_NAME pending |
| BOX | You see the old line through the ink. | Experience telegraph | Text only |
| BOX | You read it again. I have no job experience. | CVOriginalExperience resolves | Text only |
| BOX | You lose the whole line. | CVBlank | Text only |
| BOX | You see the shelf under the heading. | Logistics telegraph | Text only |
| BOX | You read it again. I straightened some labels. | CVOriginalLogistics resolves | Text only |
| BOX | You find the words in another box. | CVMisfile | Text only |
| BOX | You see seventeen boxes fill in. | Reliability telegraph | Text only |
| BOX | You read it again. I got out of bed today. | CVOriginalReliability resolves | Text only |
| BOX | You have less room to write. | CVConstrict | Text only |
| BOX | You wait. So does the page. | CVWait, brief hold | Text only |
| SAY | In for four. Out for four. | Breathe | VO_L2_CV_BREATHE pending |
| THINK | Read it. All of it. | Mirror | VO_L2_CV_MIRROR pending |
| THINK | There's something here. | Find a detail | VO_L2_CV_DETAIL pending |
| SAY | Interior management. | Rewrite experience | VO_L2_CV_EXPERIENCE pending |
| THINK | Same shelf. Different heading. | Sort the facts | VO_L2_CV_SORT pending |
| SAY | Warehousing. Office logistics. | Rewrite skills | VO_L2_CV_SKILLS pending |
| SAY | Give me some room. | Loosen the claim | VO_L2_CV_LOOSEN pending |
| SAY | Reliable under pressure. | Rewrite availability | VO_L2_CV_AVAILABLE pending |
| BOX | You lose your place. | Failed timing | Text only |
| BOX | You finish a section. It lies flat. | Each section completes | Text only |
| THINK | The rest's still moving. | First section complete, phase two | VO_L2_CV_PROOF pending |
| BOX | You press harder. The old words show through. | First surviving section enters enraged pool | Text only |
| BOX | You fill the last box. Nothing moves. | Victory, phase three | Text only |
| THINK | That sounds like me. | Perfect-lie submission thought at 100%; proposed blended delivery, once | VO_L2_MERGE_COMPLETE pending; layered delivery needs OK |
| PROMPT | Submit C.V | After victory | Text only |
| SCREEN | Application received. | Submission completes once | Text only |
| SCREEN | C.V sent. | Note, Find a job stays unchecked | Text only |
| SAY | Sent. | Submission acknowledgement; dry human take, no extra layer | VO_L2_EXIT_SENT pending |
| None | Silence | Street opens to colour; merged black writer against Dream A, or separated human/Nightmare if honest ending selected | No VO |

### Local retry and road restart

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| BOX | You put the pen down. The page stays. | C.V Composure 0 only | Text only |
| THINK | Still here. Try again. | Lobby desk after defeat, restored 60% merge; no layered repeat | VO_L2_RETRY_AGAIN pending |
| PROMPT | Retry draft | Local retry | Text only |
| PROMPT | Finish without timing | Optional assist after failed attempt | Text only |
| SCREEN | Read the old words. Watch the margins. | Knows.CVPattern note | Text only |
| NIGHTMARE | Take your time. | Optional first road restart only | VO_L2_RESTART_NIGHTMARE pending |
| BOX | Another morning. | Road failure only | Text only |
| CARD | Day two. | Second crossing, later use current count | Text only |
| THINK | Again. Okay. | Short restarted threshold | VO_L2_RESTART_AGAIN pending |
| SCREEN | Watch the shadow. Brace before it lands. | First meteor note | Text only |

### Honest-ending replacements, only if selected by the user

Replace the perfect-lie submission thought with these beats. The first two proposed layered cues at the grocery and office remain the same; this final cue becomes the third, fading to human instead of completing the blended voice. Do not implement both endings or add a voice explaining the merge.

| Speaker | Line | Trigger | VO ID / status |
|---|---|---|---|
| PROMPT | Strip the claims | Combat clear; required before honest-page Submit | Text only |
| SCREEN | No paid work yet. | Corrected experience | Text only |
| SCREEN | Shelf tasks. | Corrected skills, grounded in mandatory grocery action | Text only |
| SCREEN | Available to learn. | Corrected availability | Text only |
| THINK | That's what I've got. | Honest-page separation; proposed layer fades out, ending on dry human voice | VO_L2_MERGE_SEPARATE pending; layered delivery needs OK |
| None | Silence | Human reforms; the same Nightmare shell stands behind him | No VO |

New merge cues retire the earlier design-only IDs VO_L2_CAREER_YEARS, VO_L2_GROCERY_SHELF, VO_L2_OFFICE_CLAIM, VO_L2_CV_OPEN and VO_L2_CV_PERFECT. The former alternative identity/ending IDs VO_L2_ALT_B_NAME, VO_L2_ALT_C_TRUTH and VO_L2_ALT_C_PAGE are also retired. Story must reconcile these names with its VO manifest during implementation; no manifest was touched here.

## 10. World, performance and audio

Use splat_feasibility.md's Recommendation and later Dream A findings over its older approval-pending notes. This brief approves Toronto and the government open licences. credits_level2.md supplies the attribution: preserve its exact Canada/Toronto licence lines and producer credits in the eventual game/report. No logos or implied endorsement. No new sources were acquired here.

Dream A source: 248,427 splats, converted to 150,000 in a lean mesh; room approximately 7.9 x 10.3 m (scale estimate), with a closed door. Use that door as apparent arrival point and dissolve a floor disc for the fall; no door animation required. World must later check scale, clearance, floor masking and proxies in-engine. Reuse the same scene at exit from another camera. Separate Dream B generation is optional and requires separate exact-call authorization.

For Toronto, start with the Recommendation's fixed-camera opaque 50 x 50 m cells and WPO only near impacts. Target 60-120k visible city splats, at most 800k total, at most 50k live effect splats: estimates, not measured performance promises. splat_budget_ours.md also has an earlier 32 m/dithered plan and 80-150k visible iGPU target. Do not combine both cell schemes; world owns one measured choice, starting with the later Recommendation. Never apply the 4422-instruction hero flow material to the whole city.

Aerial lidar is not proven eye-height facade coverage. Use reused proxies/controlled views for the short foot strip and interiors. If live-city performance misses budget, bake the same Toronto data to top-down tiles with local live impact splats and 3 s re-formation. Do not replace the city source or add a packed-renderer project. Follow the existing Low-profile plan; actual target-hardware performance remains unverified.

MUS_Dream_Loop covers colour bookends. MUS_CityDrive_Loop covers driving and reduces under arrivals. MUS_Battle_Loop covers the finale and stops before retry/submission. Horror assigns existing sting slots to rejection/merge, impact, truth reveal, draft defeat and submission. Reuse the rejection sting for the body change; no separate explanatory voice or new music slot. Slots are not proof that final sound is delivered. Text carries critical cues without VO/audio. ReduceMotion keeps telegraphs readable while suppressing FOV pumps, shakes and flickering style changes.

## 11. Deadline and lane split

Deadline: **2026-11-19 06:00 ET**, nine calendar days from this draft, not nine full build days. Complete the full loop and both failure outcomes before expanding visual detail.

**MUST-HAVE vertical slice**

- Short threshold with Day one. on white; existing Dream A walk/fall; short Toronto street and car entry.
- One reusable two-lane spline drive over three legs, with accelerate/brake and signalled turns; no vehicle physics. Readable avoid/brace meteor, three markers and full road-restart rules.
- Three compact reused sets, each with information, rejection and one visible true-to-half-lie refinement.
- One EMPLOYABILITY value on HUD/phone/C.V, three stop flags and learned notes; no farming or progression softlock.
- One three-section C.V fight on BP_Encounter, reused effects/telegraphs/UI, correct labels, local retry and timing assist; preserve L1 behavior.
- The decided gradual merge: three readable stop reveals, persistent sand baseline and visible writer during the finale, driven by EMPLOYABILITY; correct restoration on truth loss/retry/restart. One existing shell, no new generated character or renderer.
- One user-approved ending, direct submission-to-colour exit reusing Dream A. Text-complete beats/music slots; optional layered delivery stays off until approved and does not block the visual slice.
- Attribution, readable monochrome UI, ReduceMotion, reset/outcome proof and packaged performance check.

**Nice-to-have after slice acceptance:** optional bus/radio detail, impact-time merge silhouette if readable from top-down, richer page animation, alternate road approaches, overlapping meteors, more facade detail, separately authorized Dream B, final offscreen NPC VO. No independent watcher sightings during the merger; only the honest ending separates the figures. Tidiness is a separate user choice. Exclude three stop fights, job simulation, free-text C.V editor, branching endings, additional hires and a new splat renderer.

| Lane | Ownership | Reuse and handoff |
|---|---|---|
| story | Decided merged-writer continuity; user ending and layered-voice decisions; final beats/VO IDs and notes | L1 first-person script voice and beat rows. Retire superseded IDs in a later manifest pass. Move Day one. from L1 black card to threshold once. |
| mech, including mech_encounter | Progression/drive/road restart, edits/bar, C.V context/data/assist; derived MergeAmount and reset/ending override | Implemented menu BP_Encounter/PDA system, not rhythm prototype. Own outcome/equip/RIGS/UI audit and L1 regression; pass merge changes to one visual owner, without changing pawn possession or combat stats. |
| world | Toronto/proxies, small sets, Dream A entry/exit; verify supplied Nightmare/mount asset mapping and live-splat budget | Existing lidar/Massing, Aholo sources, bed/desk/papers/sand and credits. Identify the existing humanoid character with anim; no new generation or runtime-plugin dependency. |
| ui | Shared EMPLOYABILITY display, retry/submit, contextual move details/status labels, route and brace cues, subtitles | WBP_HUD, WBP_Phone, WBP_Encounter, WBP_DayRollover, existing font/input navigation. No new C.V app framework. |
| anim | Threshold/fall, car/bed poses, page motion; three merge camera holds, one shell alignment and visibility/collision restoration | Existing player and BP_Nightmare poses/components, SetSandTransition restoration. No hard player swap, new rig or full-time skeletal retarget. |
| horror, with sound/pp coordination | Merge dissolve/re-form and hero epicentre pulse; truth bleed, city impacts, colour/restart, sound and ReduceMotion | Existing sand pipeline/overlay, scoped MPC channels, BP_DreamDirector, loops/stings. Three same-line voice layers only if approved; no new Nightmare speeches. |
| face | Readable human-to-dark-head overlap at 60-100%, existing FaceSlip range, mandatory distortion | Current face/head assets and slice effect, separate human/Nightmare stencil handling. No topology morph, new sculpt, new NPC face or MetaHuman work. |

| Gate | Required evidence |
|---|---|
| Nov 10-11 | Identity decided. User chooses ending/voice treatment; world/anim verify existing character asset mapping. Menu battle baseline retained. Freeze merge/reset contract; placeholders sufficient. |
| Nov 12-14 | All stops and finale playable; road restart, local retry, bar to 100 and exit work. |
| Nov 15-16 | Integrate Toronto/Dream A, three stop merge views and battle body coverage, UI/audio. Measure performance; cut optional effects first. |
| Nov 17 | L1 regression, L2 clear, road failure/local retry and repeated confirms. Prove merge at 0/20/40/60/100 and on truth loss; materials, groom, pose, stencil/MPC and input restore. Check muted audio, ReduceMotion and remapped inputs. |
| Nov 18 | Packaged run, credits and text/VO pass; release blockers only. Buffer before 06:00 ET Nov 19. |

Acceptance for later implementation: confirmations grant once; 0/20/40/60/100 are reproducible; truth attacks lower unfinished draft progress; road reset preserves notes but clears run; C.V defeat preserves run and never calls FailDay; no page equips on the character; L1 win/loss still works; every exit restores input/camera; QA never touches player saves. Also prove no overlapping Nightmare collision, no hero/city epicentre cross-talk, no effect leaking into L1, readable merge with VO muted, and the chosen ending's final body state. None of those runtime outcomes was tested by this offline lane.

## 12. Remaining decisions and integration checks

**Settled:** the writer is the human and Nightmare gradually merged on screen. Do not reopen implied dictation or a hard boss-time identity swap.

1. **What is perfect?** Perfect lie completes the merge (recommended), or honest page separates them. Both end with Application received, no job offer. Select one production ending before final closing VO/animation.
2. **Level 1 Tidiness?** No new bar (recommended), or derived T2-T7 progress as in section 8. No L1 change is assumed.
3. **New speech approval:** allow the three sparse same-line voice layers in section 7 (recommended), or keep ordinary human delivery throughout plus the already optional restart line. Visible merging is decided regardless; layered speech is not yet approved.

Coordinator/world/anim check: identify the existing Aholo humanoid Nightmare asset, since source describes the supplied SM_TheNightMare/MI as the rollover mount and BP_Nightmare as a separate humanoid. Use the existing actor/sand baseline while resolving this; ask the user for the intended source only if the asset mapping cannot be resolved internally. No generation request.

Mech: use the implemented menu battle identified in section 5; rhythm_data.py has no discovered BP builder consumer. The remaining check is binary parity when editor work is later authorized, not a request to choose between two battle redesigns. No editor operation occurred in this pass.
