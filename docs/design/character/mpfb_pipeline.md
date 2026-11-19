# Player character pipeline: MakeHuman / MPFB2 to UE 5.8

This pipeline replaces the MetaHuman player and the dropped Reallusion CC5 plan. The user chose MakeHuman/MPFB2 on 2026-11-07 because its output is CC0 and commercial use is allowed. The licence record is in `P:\FoA-Assets\character\mpfb\SOURCES.txt`.

## Sources of truth (read fresh on every build, never written)
- Wake outfit: `P:\FoA-Assets\character\makehuman_home\makehuman\v1py3\models\foa_teen.mhm`
  - FoA_Polo_Layered over Pants_Wool, plus CrudeLowSocks.
- Suit outfit: `...\models\foa_teen_suit.mhm`
  - male_elegantsuit01 (one mesh, one "Suit" Equip item) plus shoes03.
- Both share the same body:
  - male, about 17.5, weight 0.78, muscle 0.32;
  - game_engine rig, HighPolyEyes brown, freckled toigo skin;
  - the user shaped it with the coordinator in the MakeHuman app.
- Garments are MakeHuman `.mhclo` assets that MPFB auto-fits to the body. FoA variants such as FoA_Polo_Layered carry rest-pose offsets so they drape over the waistband. Copy any new variant folder into MPFB's user data `clothes\`.

## Tools
- Portable Blender 5.2.3 at `P:\FoA-Assets\_tools\blender-5.2.3-windows-x64\`: its own `portable\` settings, MPFB 2.0.18, CC0 packs in `portable\extensions\.user\blender_org\mpfb\data`.
- `Tools/MPFB/` scripts. All run headless at Idle priority through `run_blender.ps1 [-Blend file] <script> args`, and none writes the user's files.

| Script | Job |
|---|---|
| `load_teen.py` | `HumanService.deserialize_from_mhm`, game settings: no subdivision, GAMEENGINE skin, UUID deep search. |
| `layering.py` + `layer_garments.py` | T1: automatic garment layering and the red/green clip counter (below). |
| `build_hair.py` | T2: strand hair with MPFB's hair editor (below). |
| `export_hair_abc.py` | T3: Alembic for UE Groom, with a round-trip count check. |
| `export_ue.py` | Per-piece FBX export. Written, not yet run on the final character. |
| `poses.py`, `stage.py` | Test poses on the game rig and a studio stage, used by the checks and stills. |

## T1: Garments that never clip
`layering.layer_all(rig)` runs after MPFB has fitted the clothes.

1. **Skin under each garment.** Skin the garment fully covers, more than 3 cm inside its openings, joins the garment's `Delete.<asset>` group with a Mask.
   - The group is MPFB's own, created when the asset ships none, as wool pants don't.
   - Small visible islands enclosed by hidden skin are closed too, such as the crotch.
   - Holes shorter than 15 cm (a fly) don't count as openings.
   - The garment then eases out 5 mm wherever visible skin still comes within 4 mm.
2. **Garment over garment.**
   - Order: higher mhclo `z_depth` is outer. On a tie, the garment that meets the other with its lower part drapes over it: polo over pants, cuffs over socks.
   - The outer eases out until the inner sits 3 mm under it, faded over 3 rings. The inner doesn't move: sinking the pants exposed skin.
   - Fully covered inner faces deeper than 3 cm go in `Hidden_by.<outer>`.
3. **Weights so the layers move together.**
   - The outer's hem takes up to 50% of the inner's weights within 6 cm of its edge, so the hem rides on the lap when he sits.
   - Then the covered band of the inner takes the outer's weights, fading over 6 rings.
4. **The red/green counter.** `check_pair()` counts visible inner vertices outside the outer surface, inside its covered region.
   - "Outward" is the body normal at rest, carried into each pose by the vertex's own skinning.
   - Inner covers both garment over garment and skin through garment.
   - Poses: rest, idle, walk, sit, crouch, twist ±30°, bend forward.
   - Results go in `Saved/CharacterShots/mpfb/layering/report*.json`.

| Outfit | Outside verts before | After |
|---|---|---|
| Original crude tee + wool pants + socks | 2221 | 0 |
| FoA crude tee variant | 19 | 0 |
| Original polo | 303 | being re-measured after the fly-hole fix |
| FoA_Polo_Layered (wake) | 95 | being re-measured after the fly-hole fix (17 before it) |
| Suit + shoes | 0 | 0 |

- **Export.** `Hidden_by.*` and `Delete.*` become material sections: SK_Teen_Body gets `Skin_under_<garments>`, and inner garments get an `_under_<outer>` slot. BP_FoAPlayer hides a section while the covering garment is worn (`ShowMaterialSection`) and shows it again when it comes off. That's deleted while worn, but intact when unequipped.

## T2: Strand hair
`build_hair.py` does the following:
1. `mpfb.setup_hair_operator`, then `mpfb.apply_hair_operator(hair_asset="basic_short_hair")`. The brows use `wild_eyebrow` from the same CC0 pack (Tomáš Klecer), replacing the MakeHuman card brows.
2. **Fit to his head.** The pack's grooms are made on MPFB's default human. Each groom's Surface Deform modifier is a Deform Curves on Surface node, so it gets a stand-in surface: the same base-mesh topology and UVs, `rest_position` set to the default human, evaluated as our teen. Every strand is carried onto his head, roots and directions. Without this, the top strands sit inside his larger skull and the head looks bald.
3. **Tuning** with MPFB's hair-editor properties (`hairproperties.py`):
   - density 1.0, length 0.9, thickness 0.24 mm;
   - clump 0.15 (tip spread 12 mm), noise 0.35, frizz 0.1;
   - natural dark brown with darker roots (value matters more than hue: the game is monochrome).
4. **Bake**: the evaluated groom is copied into plain curves, attribute by attribute. Applying the modifiers one at a time loses the surface fit.
5. **Scalp lift**: no strand point stays inside the low-poly scalp. Clearance grows with distance from the root, at full strength on the crown and 35% at the nape and sides, which gives volume on top.
6. **Scalp tint**: a `FoA_scalp` mask from the roots darkens the skin under the hair. In UE, bake it into the head base colour or an MI mask.
7. **Counts**: 84,018 scalp strands with about 2.57 M points, plus 824 brow strands. That's heavy for low-end PCs, so plan the game LODs as in T3.

The comparison is `Saved/CharacterShots/mpfb/hair/hair_comparison.png`: cards against strands, each in front, 3/4, side and back, rendered in Cycles.

## T3: Hair into Unreal (Groom)
1. `export_hair_abc.py`, run on `teen/foa_teen_hair.blend`:
   - It writes `SM_Teen_Groom_Scalp.abc` and `SM_Teen_Groom_Brows.abc` to `P:\FoA-Assets\character\mpfb\export\hair\`.
   - Units are Blender metres, and the Alembic is Y-up (Blender converts on export).
   - Strand radius is kept, and it re-imports as `radius`.
   - It re-imports each file and asserts the curve and point counts match. Proven: scalp (84018, 2566770) and brows (824, 23896).
2. **UE plugins and settings:**
   - Groom and Alembic Groom Importer enabled;
   - `r.HairStrands.Enable=1`;
   - Skin Cache on (`r.SkinCache.CompileShaders=1`, `r.SkinCache.Mode=1`), which grooms on skinned meshes need.
3. **Import** each .abc as a Groom asset (`GR_Teen_Scalp`, `GR_Teen_Brows`) in `/Game/FoA/Characters/Teen/Hair/`.
   - Conversion Settings: Rotation X = 90, Scale = (100, -100, 100). That's Epic's Y-up default of (1, -1, 1) times 100 for metres to cm.
   - Check the first import against SK_Teen_Head: the hair must sit on the scalp, not 100x off or mirrored.
4. **Groom asset:**
   - Hair width override if strands look too thin at game resolution;
   - interpolation from guides (UE builds guides);
   - LODs: LOD1 with curve decimation about 0.4 and vertex decimation about 0.5 for the gameplay camera, plus a cards LOD for low-end. MPFB's hair editor can also generate and bake hair cards from these strands (`mpfb.generate_hair_cards_operator`, `mpfb.bake_hair_operator`).
5. **Binding:** right-click the groom, then Create Binding.
   - Target Skeletal Mesh = SK_Teen_Head, the mesh the scalp belongs to. No Source mesh: the groom was authored on this exact rest shape.
   - Num Interpolation Points 100.
   - The results are `GB_Teen_Scalp_Head` and `GB_Teen_Brows_Head`.
6. **BP_FoAPlayer:**
   - Two GroomComponents (HairScalp, HairBrows), attached to the SK_Teen_Head component;
   - Groom Asset and Binding Asset set;
   - Render CustomDepth on, stencil 4 (face slip), the same as the head;
   - Hair material: a Hair-shading-model material with "Used with Hair Strands", dark brown. The monochrome grade does the rest.

## FBX export and skeleton (unchanged plan)
- One armature exported as `Armature`; root bone renamed `root`. All other names stay: hand_l/r, foot_l/r and so on, which the anim lane's IK targets by name.
- **Pieces:**
  - SK_Teen_Body, the leader;
  - SK_Teen_Head: head faces, eyes, lashes and teeth, plus the ARKit face-unit morphs (faceunits01, CC0). It gets `ABP_FoA_TeenHead`: Copy Pose From Mesh from the Body, then Modify Curve. It is not a Leader Pose follower.
  - one SK per garment: Leader Pose followers.
- **Retarget**: Manny stays the source. `RTG_Mannequin_to_Teen` plus `IK_FoA_Teen`, with chains named as in IK_FoA_MetaHuman: Spine, Neck, Head, Left/RightArm, Left/RightLeg, and the five fingers 01-03 on each side.
- **Materials**: one master `M_FoA_Character`. `MI_Teen_Skin` has one swappable base-colour slot. Skin and head textures 2K, garments 1K.
- **Folder**: `/Game/FoA/Characters/Teen/` (approved).

## Rig fix (2026-11-09, rig lane): run it after every export
MakeHuman's game_engine rig puts each finger's knuckle (MCP) joint at the finger web, about 2 cm too far down the
finger, so fingers fold late, fists push fingertips out through the back of the hand and a phone grip turns into a claw.
`Tools/Rig/fix_teen_rig.py` repairs the as-exported FBXs, keeping names, parents, the non-finger bone frames, geometry,
slots and morphs:
- finger and thumb joints at anatomical places (Buchholz 1992 ratios, anchored on the Teen's own wrist and fingertips);
- every phalanx has Y along the bone and curls toward the palm with a positive FRotator Roll in UE (as a quaternion: about
  local -X), the same on both hands, confirmed by anim's grip bake;
- the rest pose is NOT a flat hand: the fingers are already softly curled (knuckles about 9-13 deg, middle joints
  about 13-17 deg, tips straight), and the retarget pose keeps it. Grip targets authored as "wrap past the palm" from a
  flat hand over-close into a fist by 3-6 cm, so author curls relative to this rest curl;
- hand weights rebuilt from the new joints; knee weights smoothed on pants and suit;
- leaf bones `lowerarm_twist_01_l/r`, driven by `ABP_FoA_TeenPost`, the post-process ABP of SK_Teen_Body (60% of the hand's
  roll; the Manny clips carry no twist keys).
- thumb in grips (tested on the real mesh, `Saved/RigShots/thumb_fix_proof.jpg`): the thumb tip must REST on the
  index's middle phalanx, never aim at the palm centre, or it sinks into the fingers and reads as a thin shell. With
  the index-middle-ring-pinky curls of a power grip or fist, these local deltas on top of the rest pose give 1.75 cm
  bone clearance with the tip on the index (each is "local rest x delta", the same on both hands):
  thumb_01 = Roll +20 (quat about -X), then about +Z by 1.25, then about +Y by -40
  (one FRotator: Roll 25.3, Pitch 36.7, Yaw 17.1; quat x -0.1595, y -0.335, z 0.0695, w 0.926);
  thumb_02 = Roll +32.5; thumb_03 = Roll +70.
  Finger curls used with it (MCP, PIP, DIP, as Roll +): screwdriver index 60/75/38, middle 66/80/40, ring 72/82/40,
  pinky 78/85/42; fist index 85/100/65, middle 88/100/65, ring 90/100/65, pinky 92/100/65.
A fresh `export_ue.py` export undoes this, so run `fix_teen_rig.py` on it before reimporting. Then run
`Tools/Unreal/rig/rebuild_rtg.py`, which re-aligns the FoA_MannyAligned retarget pose. Proof and audit:
`Saved/RigShots/audit/` (`rig_audit_board_before.jpg`, `rig_board_before_after.jpg`).

## Known limits
- MakeHuman faces are plain rather than stylised.
- No upper-arm twist bones (the polo sleeves would need them too) and no metacarpals (they would re-parent the fingers), so the palm can't cup.
- The strand groom is film-dense. The game needs the groom LODs or cards above.
