# Character lane (rlchar): status at stop, 2026-11-07 ~16:05

The route is MakeHuman/MPFB2. Reallusion CC5 was dropped because its trial licence is non-commercial. The full pipeline is in `docs/design/character/mpfb_pipeline.md`, and licences are in `P:\FoA-Assets\character\mpfb\SOURCES.txt`.

## Sources of truth (never write them)
- **Wake:** `P:\FoA-Assets\character\makehuman_home\makehuman\v1py3\models\foa_teen.mhm`
  - FoA_Polo_Layered over Pants_Wool, plus CrudeLowSocks;
  - short01 card hair, eyebrow001, HighPolyEyes with `foa_brown.mhmat`;
  - game_engine rig.
- **Suit:** `...\models\foa_teen_suit.mhm`
  - male_elegantsuit01 plus shoes03, on the same body;
  - body: weight 0.556, muscle 0.486, height 0.778, about 182 cm.
- **MPFB user data:** `P:\FoA-Assets\_tools\blender-5.2.3-windows-x64\portable\extensions\.user\blender_org\mpfb\data\`. foa_polo_layered (the latest, copied at 15:58) and `eyes/materials/foa_brown.*` are copied in. Re-copy whenever the coordinator changes them.

## Done
- **Tooling:**
  - Portable Blender 5.2.3 plus MPFB 2.0.18 and the CC0 packs;
  - `Tools/MPFB/*.py`, run with `pwsh -File Tools/MPFB/run_blender.ps1 [-Blend f] <script> args`. That's headless at Idle priority, with logs in `P:\FoA-Assets\character\mpfb\logs\`.
- **T1, garment layering:** `Tools/MPFB/layering.py` plus the `layer_garments.py` driver.
  - The red/green counter runs over 8 poses: rest, idle, walk, sit, crouch, twist ±30°, bend.
  - Proven, before → after:

    | Outfit | Before | After |
    |---|---|---|
    | Original crude tee | 2221 | 0 |
    | Layered tee | 19 | 0 |
    | Original polo | 303 | 0 |
    | FoA_Polo_Layered | 95 | 0 |
    | Suit | 0 | 0 |

  - Those numbers are on the previous body. The reports are `Saved/CharacterShots/mpfb/layering/report*.json`, and the waist stills are in the same folder.
- **T2, strand hair (now SECOND priority):** `Tools/MPFB/build_hair.py`.
  - It uses MPFB's hair editor with basic_short_hair, fitted to his head by a rest-position stand-in surface, then baked, given a scalp lift and a scalp tint. Result: 84,018 strands.
  - v2 comparison: `Saved/CharacterShots/mpfb/hair/hair_comparison_v2.png`. The coordinator's verdict: a bushy mop.
- **T3:** `Tools/MPFB/export_hair_abc.py`. The Alembic round trip is proven: scalp (84018, 2566770), brows (824, 23896). The UE Groom import and binding steps are in mpfb_pipeline.md.

## Running at stop (let it finish; don't kill it unless it hangs)
Two layering rebuilds on the NEW body with short01, eyebrow001 and foa_brown were started at about 16:00. They write:
- `P:\FoA-Assets\character\mpfb\teen\foa_teen_wake_layered.blend`
- `P:\FoA-Assets\character\mpfb\teen\foa_teen_suit_layered.blend`

Check `logs\layer_garments_report=report_wake_save=foa_teen_wake_layered.log` and `logs\layer_garments_foa_teen_suit_report=report_suit_save=foa_teen_suit_layered.log` for the `TOTAL outside verts` line. It must read "after 0".

## Exact next step (the user asked for a quick export)
1. **Update `Tools/MPFB/export_ue.py`.** It's written and ran on an old file, but needs these changes:
   - take `extra=<suit_layered.blend>`;
   - append `Human.male_elegantsuit01` and `Human.shoes03` from it, repointing their Armature modifier to the wake rig;
   - copy the suit body's `Delete.*` vertex groups by index (same topology);
   - turn the inner garments' `Hidden_by.*` groups into `<mat>_under_<outer>` slots, as the body's `Skin_under_*` slots already are;
   - name the pieces SK_Teen_Body, SK_Teen_Head (head + eyes + eyebrow001 + lashes + teeth + tongue + short01 cards + ARKit morphs), SK_Teen_Polo, SK_Teen_Pants, SK_Teen_Socks, SK_Teen_Suit, SK_Teen_Shoes;
   - `shape_key_clear()` on the garments after `FaceService.interpolate_targets`.
2. **Import** into `/Game/FoA/Characters/Teen/Mesh/`, with the hair material under `/Hair/`.
   - Body first, which creates SKEL_Teen; the rest import onto that skeleton.
   - Use placeholder materials. The cloth lane (a4d388ada285dcf07) assigns the ones under Teen/Cloth/.
   - Hair MI: masked or dithered, two-sided, high roughness, no shine.
   - Stencil 4 on the head and hair components.
   - Follow the editor rules: declared ue_remote runs and leases.
3. **UE viewport stills** of both outfits (front, 3/4, side, back), shot with temporary actors (TMP_rlchar_*) that are deleted afterwards. Send them to main. Don't delete the MetaHuman yet.
4. **Then the strand groom v3:** match short01's silhouette and flow by shrink-wrapping the strands into short01's card shell, then run the scalp-spot check.
   - The unapplied style code (fringe pieces, nape taper) never landed. Bash heredocs containing `'` break in the tool wrapper, so write edit scripts with the Write tool instead.
   - A `check_scalp()` render test is in build_hair.py but hasn't run yet. Red-prove it with `redcheck=1`.

## Agreements
- **Anim lane (ae7620936be7fa99d):**
  - SK_Teen_Head runs its own ABP_FoA_TeenHead: Copy Pose From Mesh, then Modify Curve on the ARKit curves. It is not a Leader Pose follower.
  - Hair and garments are Leader Pose followers of the Body.
  - IK_FoA_Teen chains: Spine, Neck, Head, Left/RightArm, Left/RightLeg, and the five fingers 01-03 on each side.
  - Only "Root" is renamed, to "root".
  - hand_r: local +Y points to the fingers, and the palm is about local +Z (tilted −X). The anim lane wants a UE-side gizmo check after import.
- The approved folder is `/Game/FoA/Characters/Teen/`. One "Suit" Equip item is fine.

## Open problems
- The polo is CC0, not CC-BY as main thought: its .mhclo header, pack JSON and pack page all say so. Credit is recorded anyway.
- Strands are film-dense (84k). The game needs groom LODs or cards.
- The game_engine rig has no twist or corrective bones.
- The layering numbers above must be re-confirmed on the new 182 cm body. The run is in progress.
