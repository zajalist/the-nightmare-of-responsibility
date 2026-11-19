# Ambient sand and foreshadowing (world lane)

The user: "We need more random sand appearing and disappearing in the room, more foreshadowing."

One placed director does both: `Gameplay/Ambient/BP_SandAmbience`, label `SandAmbience`, outliner `FX/Sand`, at
the world origin. Builder: `Tools/Splats/build_sand_ambience.py`. No Tick, no Niagara: every event wakes one hidden
splat part (the house `M_SplatMesh` sand) and starts its `SandEvent` custom primitive data, and the material does
the motion from game time.

## How it runs

- **Live only when the room is the player's.** `UpdateState` reads `BP_BeatDirector.BeatIndex` and `bRollingOver`,
  `GI_FoA.DayCount`, and whether the player's own pawn is the view target. Nothing happens on the title, in
  LS_WakeUp, on the phone push-in, in the T7 top-down, in the T8 battle (beat 8), in the T9 payoff (beat 9) or under
  the rollover.
- **One event at a time.** `Step` hides the last part, then draws a function name from `Deck` and runs it by timer.
  Each `Ev_*` checks its own beat window and a coin (`Chance`), then plays or draws again.
- **Escalation.** `Level = clamp(0.07 x beat + 0.12 x failed days, 0, 1)`, where failed days = `DayCount - 18`
  (18 is the first morning), capped at 5. The gap between events is `lerp(22-32 s, 6-10 s, Level)`: on the first
  morning at T0 an event comes about every half minute; on a fifth failed morning near T7, every 6-10 s.
  Every foreshadow coin also grows per failed day, and the suit appears a beat earlier per failed day.
- **Only where there is light.** Black goo in an unlit corner is invisible (first PIE burst, 15:11), so every site
  sits in one of the room's lights: the hallway leak under the door, the desk lamp, the moonbeam from the bay,
  the fireplace bounce, the mantel.
- **Never in the way.** Every part is NoCollision, casts no shadow and sits off the walking lines (walls, corners,
  furniture edges, the mantel). Only the Nightmare glimpse has collision, for its 1-1.6 s, in a corner.
- **GPU budget.** Hidden parts cost nothing. At most one event part plus the feet bloom draw at once: 9k-16k splat
  quads each, the same as one of the room's existing spills.

## Ambient sand (the room is alive)

| Event | What the player sees | Where | Beats |
|---|---|---|---|
| `Ev_Creep` | black goo wells out from under the wardrobe or the door, spreads into a lobed puddle with strands, holds, then draws back under | under the wardrobe front (until it falls at T6), under the door (until it moves at T7) | T0-T6 |
| `Ev_Pile` | a pile wells up, slumps into a puddle and drops its grains | the desk lamp's pool, the moonlight before the bay, the hearth stone | all |
| `Ev_Trickle` | a thin pour of sand from the ceiling, landing in a small pile | the bay alcove (through the moonbeam, onto the bay sand), beside the chimney breast (in the fireplace's light) | all |
| `Ev_Drift` | grains hang in the moonbeam from the bay and sink slowly | the bay light shaft | all |
| `WatchStill` | stand still for 4-9 s (sooner as Level rises): goo grows around the feet and the player crawl in `M_SplatMesh` pulls its grains up the legs; walking away makes it recede | at the player's feet | all |

The existing `BP_DreamDirector.AmbientBloomTick` blooms (corners, under the bed and desk) keep running alongside.

## Foreshadowing (the house knows what is coming)

Every foreshadow uses the real thing it points at: the same Lux3D shirt the player fights at T8, the same Lux3D suit
they earn at T9, and the house's own clocks.

| Event | What the player sees | Points at | Beats | Day 1 chance, + per failed day |
|---|---|---|---|---|
| `Ev_Sleeve` | a white shirt sleeve caught in the wardrobe's door seam twitches, then is gone | the garments come alive (T8), from inside the wardrobe that falls (T6) | T0-T5 | 35%, +15% |
| `Ev_Shirt` | a shirt-shaped imprint of black sand forms on the boards in the moonlight, holds, crumbles | the shirt enemy (T8); one site is beside where the shirt appears at T7 | T1-T7 | 35%, +15% |
| `Ev_Glimpse` | the Nightmare stands at the edge of the view (never centre frame) for about a second, facing the player, then bursts into sand | the Nightmare that rides the rollover and watches the fight | T2-T6 | 20%, +20% |
| `Ev_Suit` | a full suit of black sand stands in the moonlit bay or in front of the fireplace, then falls to the floor | the suit payoff (T9) | T7 on day 1; T6, T5, T4, T3 on failed days 1-4 | 40%, +15% |
| `Ev_ClockDrip` | sand runs out of the bottom of the wall clock onto the mantel | time running out; the alarm clock that crumbles in LS_WakeUp | all | 50%, +10% |
| `Ev_Hourglass` | an hourglass of sand forms on the mantel beside the clock, holds, crumbles | the time motif | all | 30%, +10% |

A returning player notices more: by the third failed morning the sleeve, the imprint and the glimpse come about
twice as often, the gaps are a third shorter, and the suit is already standing at T5.

## Assets (lean: reused unless noted)

- Meshes: `SM_SandMoundSplats_B` (blooms, piles, creep, the feet bloom), `SM_SandStream` (trickle, clock leak),
  `SM_SandFaceDrift` (the beam), the Lux3D shirt `/Game/FoA/Lux3D/the_shirt_enemy` (the sleeve).
  New: `SM_SandShirtImprint` and `SM_SandSuit` (surface samples of the Lux3D shirt and suit GLBs,
  `Tools/Splats/glb_to_sandsplats.py`), `SM_SandHourglass` (the Lux3D `sand_hourglass` Gaussian splat,
  `Tools/Splats/ply_to_splatmesh.py`).
- Material instances of `M_SplatMesh` (new, small): `MI_Sand_Trickle`, `MI_Sand_ClockDrip` (children of
  `MI_Sand_Stream`, longer and shorter drops), `MI_Sand_ShaftDrift` (child of `MI_Sand_FaceDrift`),
  `MI_Sand_Imprint`, `MI_Sand_Suit`, `MI_Sand_Hourglass` (children of `MI_Sand_AlarmClock`, static mode).
- Sites are tagged scene components on the actor (`Site.Pile`, `Site.Glimpse` ...): move them in the level to retune.

## Proof

PIE bursts `bash Tools/Splats/pie_ambience.sh amb|fore|live`, media by `python Tools/Splats/pie_ambience_media.py <plan>`
into `Saved/WorldShots/pie_<plan>/` (one GIF and one still per event).
