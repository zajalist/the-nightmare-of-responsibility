# Dream transition lane handoff

2026-11-11: building new assets under `/Game/FoA/Level2/Transition` only. Story's sequences and BP_BeatDirector source remain owned by story.

Integration contract: `BP_DreamThreshold.StartThreshold` takes over after T10's phone closes, while the player is still inside the door. It clears the runtime `CheckWalkedOut` timer, then plays new `LS_DreamThreshold`. Do not invoke `WalkedOut`/`EndLevel` concurrently: those return to title. The new actor will watch T10 when placed; no story graph rebuild is intended.

Approach: dynamically stream existing `L_L2_DreamTest` 200 m away from the persistent bedroom. A sharp camera cut/teleport on white hides the spatial separation. Bedroom is retained as persistent level but is no longer visible. Existing MPC_Dream ColorReveal and BP_SplatFXDirector own the colour/re-form. A non-failing 30-45 s first-person walk leads to a 10 s fall, monochrome landing and city fade handoff.

The design v2 moves `Day one.` from the old black ending to threshold white. New transition owns that card. No VO generation. Final implementation/proof status will be in `Saved/Codex/dream_transition_report.md`.

## Status at 14:44 local

BLOCKED by `main:MAINTENANCE hayba 5.9 install`. Unreal shut down at 14:30. No transition assets have been created or compiled, no bedroom change, no PIE, no film. Source builders are drafts in `Tools/Unreal/level2/threshold*` and `build_threshold.py`; do not treat them as integrated content.

T10 coordination still needed: existing `OpenTheDoor` sends Notify/Open before the phone closes. The draft observer starts after that phone closes, so it would film an already-open door. To meet the requested opening on camera, story should hand off before Notify/Open and route the opening at the new sequence's 3-second mark. Do not run both the old `CheckWalkedOut`/`EndLevel` path and this transition. No story Blueprint or sequence was edited by this lane.

Other integration gates: verify Dream A entry `(0,-260,92)` to exit `(0,340,92)` against geometry; make sure streaming test-map directors do not compete for MPC_L2; verify city streaming follows the relocated camera. The draft keeps the bedroom persistent and streams Dream A at `(20000,0,0)`, city at `(100000,0,0)`; it does not unload the bedroom. Phase 6 and CityReady are the proposed drive handoff state after the final fade, not a wired drive start.

Hayba gap for coordinator: Level Sequence spawnable cameras, component focal-length keys, binding tags, and transform-origin authoring are prepared through short structural editor Python using story's existing helpers. No native Sequencer authoring command was found in the installed Hayba sources. No Hayba repository changes were attempted.
