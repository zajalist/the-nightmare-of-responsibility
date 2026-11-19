# Content cleanup plan (phase 1 audit)

Cleanup lane, 2026-11-09. Nothing has been deleted or moved yet. The machine-readable result is `Saved/Cleanup/audit.json`, and the proposed moves are in `Saved/Cleanup/moves.json`.

## Phase 2 status (13:45)

**Results**

| | Before phase 2 | Now |
|---|---:|---:|
| Content on disk (.uasset/.umap) | 2071.5 MB, 2017 packages | 717.3 MB, 1117 packages |

After the pending quarantine (`quarantine_list_2.txt`), Content will be about 701 MB.

- **Re-audit:**
  - (a): 1038 packages, 677.6 MB, about 586.5 MB cooked;
  - (b): 58 packages, 20.8 MB;
  - (c): 11 packages, the lane keeps plus horror's work in progress;
  - (d): 0;
  - redirectors: 0.
- **Log check:** no missing-reference load lines naming /Game.

**What was done**

- 5 redirectors fixed up.
- 40 T1 assets deleted in the editor.
- 848 packages (1061.2 MB) quarantined offline to `P:\FoA-Assets\_cleanup_quarantine\20261109\` (`manifest_132710.json`; undo with `--restore`). That covers:
  - T1: the rest;
  - T2;
  - the (d)1 template map with its external packages;
  - T3: face, horror, anim minus 5 keeps, world minus 5 keeps.
- 12 story and Garments assets deleted in the editor.
- **Still waiting:**
  - 10 textures (the story intro plates and the Garments basecolors). `delete_asset` reported success but left the files on disk, so they are queued in `Saved/Cleanup/quarantine_list_2.txt` for the next restart.
  - 24 empty folders, to remove offline at the next restart.
  - Move sets A and B, in their own window. The Lux3D slot order is verified (`Saved/Cleanup/lux3d_slots.txt`).

**Lessons**

- Hayba `asset_fix_redirectors` opens a modal report that froze the editor for 4.5 min. It is replaced with a resave-then-delete fix-up.
- In-editor `delete_asset` costs about 4.5 s of shared game thread per heavy asset. Bulk removal goes through the offline quarantine during a restart instead.

## Summary

| | Packages | On disk | Cooked estimate |
|---|---:|---:|---:|
| Content now | 2013 | 2070 MB | |
| (a) used at runtime | 1024 | 664 MB | 582 MB |
| (b) build input only (named by a Tools script) | 63 | 29 MB | not cooked |
| (c) unreferenced: deletion candidates | 845 | 1375 MB | not cooked |
| (d) unsure | 81 | 2.0 MB | 0.8 MB (the template map, which cooks today) |

The deletion candidates (c) fall into these tiers:

| Tier | What it holds | Packages | On disk | Approval needed |
|---|---|---:|---:|---|
| T1 | The retired MetaHuman player (`Characters/Protagonist`, `Fab/MetaHuman`), plus 10 Player assets that only work on the MetaHuman skeleton | 363 | 1219 MB | Already approved by the user |
| T2 | Test leftovers and backups (`_QA`, `_FingerQA`, `*_Before*`, timestamped copies), importer leftovers sitting next to the asset that replaced them, unused copies of textures that are in use, and unused template content | 59 | 39 MB | Coordinator. The face lane must OK its 7 recent items first. |
| T3 | Everything else that nothing references: the audio library, unused animation clips and their source rigs, unused intro plates, unused material instances | 418 | 117 MB | The owning lane, folder by folder (see below) |
| fixup | 5 redirectors | 5 | 0 MB | Coordinator (fix-up, not delete) |

Expected Content size:

| After | On disk |
|---|---:|
| T1 | 851 MB |
| T1, T2 and fixup | 812 MB |
| T1, T2, T3 and fixup | 695 MB |
| All of that, plus the template map in (d) | 693 MB |

### What this does to the build size

The packaged build only cooks what the maps and the config reach. That is class (a), plus the template map while it exists. The deletion candidates are not in the build today. Deleting them shrinks the repo, the editor's load and the content browser, but it barely moves the build.

The runtime content cooks to about **582 MB** before pak compression. About 422 MB of that is textures. This estimate counts mip chains and platform formats, editor-only source data excluded, and audio at about 1/8 of its PCM size. Engine binaries, engine content and the shader library come on top of it. The project targets two shader formats, SM6 for D3D12 and SM5 for D3D11, so every material is compiled twice.

The 1 GB budget is reachable, but it is set by runtime texture choices, not by deletions. These are the levers, each owned by another lane and none part of this cleanup:

| Lever | Cooked saving | Owner |
|---|---:|---|
| Small props on 2K maps, and 1920x1080 intro plates. Set MaxTextureSize to 1024 on the 32 textures flagged below. | ~64 MB | world, story |
| 26 uncompressed G8 roughness, AO and decal masks. Change TC_Grayscale to TC_Alpha (BC4) or pack them into an ORM. | ~31 MB | world |
| Mannequin textures (~62 MB cooked with the mannequin meshes). They cook only because the hidden driver mesh SKM_Manny_Simple and the parent class mesh SKM_Quinn_Simple keep their materials. A 1-node material on the hidden driver, and no mesh on BP_ThirdPersonCharacter, drops most of it. | up to ~55 MB | anim, gameplay |
| Five in-use duplicate textures in desk_lamp_arm_01 and brass_candleholders. Point each MI at one copy. | ~7 MB | world |
| Drop the D3D11 SM5 target if DX11-only cards are not a goal. Note that the low-end-PC rule may want to keep it. | shader library | coordinator |

## How the audit was made

1. **Registry graph, read-only.** `Tools/Cleanup/registry_dump.py` runs through `run_read.py`. It does two chunks of about 1000 packages, 0.1 s each, and loads no asset. For every /Game package it records the classes, the hard and soft package dependencies, and the registry tags: texture dimensions, format, compression, LOD group and max size, and mesh ApproxSize. The registry's 2007 packages matched the 2007 files on disk when it ran.
2. **Roots.**
   - The maps. `L_Tutorial_Bedroom` is the only game map. `Lvl_ThirdPerson` is the template map and is handled under (d).
   - Config: `GameDefaultMap`/`EditorStartupMap` (L_Tutorial_Bedroom), `GameInstanceClass` (GI_FoA) and `GlobalDefaultGameMode` (BP_ThirdPersonGameMode). `TransitionMap` is empty. DefaultGame.ini and DefaultInput.ini name no /Game asset. The world-settings GameMode GM_FoA, the pawn BP_FoAPlayer, the input contexts, UI classes, MPCs and fonts are all reached through those roots.
   - Soft references in the registry.
3. **String references.** Every Blueprint, Widget Blueprint, Anim Blueprint, DataTable, LevelSequence, map and Blueprint-class data asset was scanned for raw `/Game/...` strings, both ANSI and UTF-16, that the registry does not already list. These are the strings that LoadAsset/LoadClass-by-string would use. **No Blueprint loads anything by a string the registry doesn't know about.**
   - Raw paths do appear inside 230 meshes, anim sequences and material instances. They are Interchange and retarget import metadata, not loads, so they are ignored.
   - The one raw string in a map is a metadata copy of `/Game/ThirdPerson/Lvl_ThirdPerson` inside L_Tutorial_Bedroom.
4. **Tools roots.** Every text file under `Tools/` was scanned: 882 .py files, plus .sh, .ps1, .json and .txt. A file can name an asset directly (`'/Game/FoA/X/Y'`), or compose it from a prefix and a literal in the same file (`SFX + "Bed/SFX_Bed_Sit_01"`). Anything named either way, and anything it depends on, is class (b) unless it is already (a).
5. **Textures.** Duplicates were found by hashing the source pixels: the payload hash in each texture's UE5 package trailer, which is the editor bulk data. They were not found by file name. "Small prop" means that every mesh using the texture, up to 5 hops through MI and material, is at most 60 cm by its ApproxSize.
6. Rerun it all with `run_read.py Tools/Cleanup/registry_dump.py` (two chunks) and then `python Tools/Cleanup/audit.py`.

### Limits

- A Tools script that builds a path from a prefix imported from another module is not seen. The only such case found by hand is `Tools/Unreal/gameplay/data_rows.py` (`f"{LUX}/..."`), and its targets are (a) anyway. This is why T3 needs the owners' OK and is not deleted on the audit's word alone.
- The registry is a snapshot. The delete script repeats the live referencer check right before every delete.
- 55 class (c) assets were modified in the last 48 hours. Lanes are active: the face lane in `Teen/Mesh` and `Teen/_QA`, anim on its GASP clips, story on its intro plates. They are marked `recent` in audit.json.

## Deletion tiers in detail

### T1: retired MetaHuman (approved)

These folders go whole: `/Game/FoA/Characters/Protagonist` (323 packages, 937 MB) and `/Game/Fab/MetaHuman` (30, 260 MB). Nothing in (a) reaches them. BP_FoAPlayer now uses `Teen/Mesh/SK_Teen_*` and `GR_Teen_Scalp`.

The audit also pulled in 10 Player assets that are bound to the MetaHuman skeleton. Left behind, they would keep MetaHuman pieces alive through the reference check, or break the moment those pieces go.

| Asset | Size | Why |
|---|---:|---|
| `Characters/Player/Clothing/SK_FoA_Suit` | 10.0 MB | on metahuman_base_skel |
| `Characters/Player/Clothing/SK_FoA_Boots_Worn` | 3.9 MB | on metahuman_base_skel |
| `Characters/Player/Clothing/SK_FoA_Body_Suited` | 3.7 MB | uses the MHC_Protagonist physics asset and DNA mesh |
| `Characters/Player/Clothing/SK_FoA_Shirt`, `SK_FoA_Socks`, `SK_FoA_Trousers`, `SK_FoA_Tie` | 4.4 MB | on metahuman_base_skel; the Teen/Cloth meshes replaced them |
| `Characters/Player/ABP_FoA_Face` | 46 KB | on the MetaHuman Face_Archetype_Skeleton |
| `Characters/Player/Retarget/IK_FoA_MetaHuman`, `RTG_Mannequin_to_MetaHuman` | 0.3 MB | MetaHuman retargeting |

After T1, these Tools scripts are dead and should be retired or archived by their owners: `Tools/Unreal/mh_*.py`, `Tools/Unreal/player/build_protagonist.py`, `export_teen_dna.py`, `finalize_teen_head.py`, `groom_*`, `build_suit_materials.py`, `assign_suit_materials.py`, `assign_modular_clothes.py`, `import_suit_assets.py`, `probe_suit_rigs.py` and `probe_rtg_chains.py`. Also `Tools/Unreal/cine/build_ls_wakeup.py:553` checks `ABP_FoA_Face` with `does_asset_exist` and skips it when it is missing, so it stays safe.

After T1, `M_CharacterCloth`, `MI_Suit_*`, `MI_Socks_Dark` and the `T_Suit_*` textures lose their last user, so the next audit lists them in (c).

Recommendation: once T1 is gone, disable the MetaHumanCharacter plugin in FoA.uproject. That is editor load time only; it does not affect the build.

### T2: leftovers

| Owner | Packages | Size | Content |
|---|---:|---:|---|
| face | 7 | 13.8 MB | `Teen/_QA/*_BeforeCrouch/_BeforeFlatten/_BeforeChest` (5), `Teen/_FingerQA/AS_FingerSource`, and `Teen/Mesh/T_Teen_T_Teen_..._Freckles`, a pixel-identical copy of the Freckles texture that is in use. **All 7 were modified in the last 48 h. Ask face first.** |
| world | 27 | 20.3 MB | Importer leftovers: `*_glass` MIs and their textures on mantel_clock_01, lantern_chandelier_01, wall_clock and hanging_picture_frame_03; `mantel_clock_01_*1` (pixel copies of used maps); the painted_wooden_chair_01 and rubber_boots import materials; the glass_of_water Lux3D MI and textures (its mesh uses another material); `Door/*/Materials/Paint` and `Door/SM_DoorFrame_Bedroom/Materials/Brass`; `Props/DoorLock/Plate/textured/Textures/textured_texture_0` |
| anim | 6 | 2.7 MB | `Player/_QA/Before/*` (3), `Player/_QA/RTG_UAL1_Before`, `Cinematics/LS_WakeUp_ManualPose_BeforeTPose_004428`, `_BeforeFingerFix_010103` |
| (template) | 19 | 2.2 MB | `/Game/LevelPrototyping` content that not even the template map uses: JumpPad, Door, Target interactables, spare meshes and MIs |

### T3: owners decide

| Owner | Packages | Size | Biggest items |
|---|---:|---:|---|
| anim | 122 | 51.8 MB | `Player/Source/UAL1` and `UAL2_Standard`: retarget source rigs and 88 source clips, 36.7 MB, whose retargeted copies under `Player/Anims/UAL` are what the game uses. 8 unused `Anims/GASP` clips (9.9 MB, **recently modified**). 10 unused `Anims/UAL` clips. `Retarget/IK_UAL1`, `IK_UAL2`, `RTG_UAL*_to_Mannequin`. `Montages` (1). `Cinematics/LS_WakeUp_ManualPose` (recent). |
| horror | 237 | 44.5 MB | The audio library that is not wired up: 168 SoundWaves (the biggest is `SFX/Ambience`, 19.9 MB: crickets, distant city, rain on glass) and 71 MetaSounds. The level and the BPs reference 25 MetaSounds and 145 waves. |
| story | 7 | 12.9 MB | `UI/Intro/Textures/T_Intro_BedFar`, `BedNear`, `Calendar`, `Chores`, `Door`, `Dressed`, `Waiting`: the first intro plate set, replaced by `T_Intro_Game0*`. **Recent.** |
| unowned | 15 | 4.4 MB | `Characters/Garments`: 12 unused armature clips, plus the basecolors for sock, tie and trousers. The folder is not in lanes.json; the old character lane kept them for "per-garment MIs". |
| world | 14 | 2.2 MB | `VFX/Sand/BP_SandMound`, `MI_SandFall`, `M_SandImpact`; `VFX/Splats/Meshes/SM_SandMoundSplats_C` (mesh and its importer M_SplatMesh); `PostProcess/M_PP_DreamStreak`, `MF_Dream_ShiftStreak`; 4 unused decal textures and 3 decal MIs |
| face | 23 | 1.4 MB | `Teen/Mesh/Human_*` and `Skin_under_*`: the MPFB per-layer MIs that the shipped teen materials replaced. **All recent.** |

## Top 50 deletions by size

All 50 are tier T1 except the Freckles copy (T2).

| MB | Tier | Type | Asset |
|---:|---|---|---|
| 110.4 | T1 | MetaHumanCharacter | `FoA/Characters/Protagonist/Teen/MHC_Teen` |
| 109.1 | T1 | MetaHumanCharacter | `FoA/Characters/Protagonist/MHC_Protagonist` |
| 101.0 | T1 | MetaHumanCharacter | `FoA/Characters/Protagonist/Faces/MHC_Face_N` |
| 59.9 | T1 | Texture2D | `Fab/MetaHuman/Casual_M_Outfit/Textures/Shirt/T_M_Casual_Shirt_Normal` |
| 57.3 | T1 | Texture2D | `Fab/MetaHuman/Casual_M_Outfit/Textures/Brown_var/T_Casual_Slipper_Normal` |
| 56.9 | T1 | Texture2D | `Fab/MetaHuman/Casual_M_Outfit/Textures/Pant/T_M_Casual_Pant_Normal` |
| 41.8 | T1 | MetaHumanCharacter | `FoA/Characters/Protagonist/Faces/MHC_Face_M` |
| 34.1 | T1 | ChaosOutfitAsset | `Fab/MetaHuman/OA_Casual_M_Outfit` |
| 29.6 | T1 | GroomAsset | `FoA/Characters/Protagonist/Teen/Built/Grooms/GR_Teen_Hair` |
| 19.9 | T1 | ControlRigBlueprint | `FoA/Characters/Protagonist/Common/Common/MetaHuman_ControlRig` |
| 18.4 | T1 | GroomAsset | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Grooms/Hair_S_Messy` |
| 17.8 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_Head` |
| 17.7 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_Head` |
| 17.7 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Common/Face/SKM_Face` |
| 17.1 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Teen/Built_N/Body/MHC_Face_N_FullBody` |
| 17.1 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Mesh/MHC_Protagonist_FullBody` |
| 17.1 | T1 | SkeletalMesh | `Fab/MetaHuman/Casual_M_Outfit/Common/SourceBodies/SK_Metahuman_Tall_Normal_Male` |
| 14.5 | T1 | Texture2D | `FoA/Characters/Protagonist/Common/Lookdev_UHM/Eye/Textures/T_EyeSclera_N` |
| 14.0 | T1 | Texture2D | `Fab/MetaHuman/Casual_M_Outfit/Textures/Brown_var/T_Casual_Slipper_OcclusionRoughnessMetallic` |
| 12.7 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Body/Textures/T_Body_Chest_Cavity` |
| 11.9 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Face/Textures/T_Face_Cavity` |
| 11.9 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Face/Textures/T_Face_Cavity` |
| 11.5 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Clothing/MHC_Protagonist_Outfits` |
| 11.4 | T1 | ControlRigBlueprint | `FoA/Characters/Protagonist/Common/Face/Face_ControlBoard_CtrlRig` |
| 11.3 | T1 | Texture2D | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/Baked/T_Body_BC_VT` |
| 11.1 | T1 | SkeletalMesh | `FoA/Characters/Protagonist/Teen/Built_N/Body/MHC_Face_N_Body` |
| 10.8 | T1 | DNA | `FoA/Characters/Protagonist/Teen/Built_N/DNA/MHC_Face_N_Head` |
| 10.8 | T1 | DNA | `FoA/Characters/Protagonist/Teen/Built/DNA/MHC_Teen_Head` |
| 10.5 | T1 | DNA | `FoA/Characters/Protagonist/Common/Face/SKM_Face_DNA` |
| 10.0 | T1 | SkeletalMesh | `FoA/Characters/Player/Clothing/SK_FoA_Suit` |
| 9.9 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Body/Textures/T_Body_Body_Cavity` |
| 9.8 | T1 | Texture2D | `Fab/MetaHuman/Casual_M_Outfit/Textures/Brown_var/T_Casual_Slipper_Black_Mask_RGB` |
| 9.7 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Body/Textures/T_Body_Body_Cavity` |
| 8.2 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Body/Textures/T_Body_Chest_Normal` |
| 7.3 | T1 | ChaosClothAsset | `Fab/MetaHuman/Casual_M_Outfit/ClothAsset/CA_Casual_M_Outfit` |
| 7.0 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Body/Textures/T_Body_Chest_Cavity` |
| 6.9 | T1 | Texture2D | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/Baked/T_Body_SRMF_VT` |
| 6.7 | T1 | Texture2D | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/Baked/T_Head_LOD3_SRMF_VT` |
| 6.5 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Body/Textures/T_Body_Body_Normal` |
| 6.4 | T1 | Texture2D | `FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/Baked/T_Head_LOD3_N_VT` |
| 6.3 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Face/Textures/T_Face_Normal` |
| 6.2 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Face/Textures/T_Face_Normal` |
| 6.0 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Body/Textures/T_Body_Body_Basecolor` |
| 6.0 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Body/Textures/T_Body_Body_Basecolor` |
| 5.8 | T1 | Texture2D | `FoA/Characters/Protagonist/Common/Lookdev_UHM/Teeth/Textures/T_Teeth_DetailNormal` |
| 5.7 | T1 | Texture2D | `FoA/Characters/Protagonist/Common/Lookdev_UHM/Eye/Textures/Iris/T_iris_H_N` |
| 5.4 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built/MHC_Teen_MaterialsExport/Body/Textures/T_Body_Body_Normal` |
| 5.3 | T1 | Texture2D | `FoA/Characters/Protagonist/Common/Lookdev_UHM/Eye/Textures/Iris/T_iris_I_N` |
| 5.2 | T2 | Texture2D | `FoA/Characters/Teen/Mesh/T_Teen_T_Teen_young_lightskinned_male_diffuse_Freckles` |
| 5.2 | T1 | Texture2D | `FoA/Characters/Protagonist/Teen/Built_N/MHC_Face_N_MaterialsExport/Face/Textures/T_Face_Basecolor` |

## Class (d): unsure

| Packages | Size | What | Why unsure |
|---:|---:|---|---|
| 79 | 0.8 MB | `/Game/ThirdPerson/Lvl_ThirdPerson`, its 65 `__ExternalActors__` and 2 `__ExternalObjects__` packages, `ThirdPerson/MI_ThirdPersonColWay`, and the 10 `LevelPrototyping` meshes, materials and textures it places | The brief treats every map as a root, but this is the UE template level. **It ships today**: no maps-to-cook list is set, so the cooker takes every map. Recommend deleting it. Delete the map **and** its external actor and object packages together, or the actors are orphaned. Keep `/Game/ThirdPerson/Blueprints` (BP_ThirdPersonGameMode, BP_ThirdPersonCharacter, PlayerController): GM_FoA and BP_FoAPlayer inherit from them. |
| 1 | 0.9 MB | `Characters/Teen/_FingerQA/Target/AS_FingerSource` | A test leftover, but `Tools/MPFB/capture_finger_pose.py` still loads it. Face lane decides. |
| 1 | 0.2 MB | `Cinematics/TMP_anim_WakeRetime` | The anim lane's scratch sequence, made after the restart and named by `Tools/Unreal/cine/tmp_dup_wake.py`. By the TMP_ rule it goes when anim is done with it. |

## Class (b): build inputs (keep, listed)

There are 63 packages, 29.4 MB. None of them cook. They are kept because a Tools script loads them by path. Those marked *probe* are named only by probe or read scripts, so the owner could drop them.

- **Characters/Hero** (5 packages, 13 MB): SK_Hero, its skeleton and materials. Named by `import_hero.py`, `player/hero_retarget.py`, `player/build_cloth.py` and `player/compat_skeleton.py`. This is the pre-MetaHuman hero. Anim lane: retire it?
- **Player**: `Anims/BS_FoA_Jog`, `BS_FoA_Walk`, `UAL_LayToIdle`, `UAL_Walk_Formal_Loop` (*probe*: anim_probe.py); `Loco/AS_FoA_Walk_Brisk`, `Wake/AS_FoA_Lie_Breathe`, `UAL_Sitting_Idle_Loop`; `Montages/AM_FoA_WakeUp`; `Clothing/MI_Suit_*`, `MI_Socks_Dark`, `M_CharacterCloth`, `T_Suit_*` (orphaned by T1).
- **Teen/Hair/GB_Teen_Scalp_Head** (`Tools/MPFB/ue_capture_teen.py`). **Cinematics/ManualPose/Manual_A_TPose** (`wakeup/integrate_manual_sleep.py`).
- **UI**: `Fonts/F_FoA_Mono` with 4 FF_IBMPlexMono faces, and `F_FoA_Typography`; `Materials/M_UI_SandButton`, `MI_UI_SandButton_Primary/Secondary`, `MF_UI_SandFlow/Dissolve`; the uimotion library (`Materials/Lib/MF_UI_*` ×7, `M_UI_Meter`, `M_UI_Ring`, `MI_UI_Meter_Garment`, `MI_UI_Ring_Parry`), built by `uimotion/build_ui_lib.py` and not wired yet.
- **Audio**: `MetaSounds/Phone/S_Phone_Buzz` and `S_Phone_Tap` with their 6 waves (`ui/wire_bp_phone.py`, not wired yet).
- **Work in progress, appeared during this audit**:
  - `Gameplay/Jumpscare/SM_Jumpscare_Monster` with its MI and two textures, 9 MB (horror, `horror/shoot_monster.py`). Its 4.7 MB basecolor should be capped at 1K or 2K once it is wired.
  - `PostProcess/FaceBlur/M_PP_FaceBlur` (face).
  - `MetaSounds/Dream/S_Dream_HeartbeatPanic` with its wave (horror, *probe*).
- **Other**: `Materials/M_WorldAligned` (`Devlog/build_devlog.py`); `VFX/Sand/M_SandFall` and `VFX/Textures/T_VFX_Noise` (*probe*).

## Redirectors and empty folders

**Redirectors (5): done in phase 2.** The first attempt used Hayba `asset_fix_redirectors`. It opened a modal "Redirector Update Report" dialog that froze the editor for 4.5 min (13:06 to 13:10), and was closed by clicking "Delete Unreferenced Redirectors". The tool is banned here until Hayba restart 7 makes it unattended. The fix-up is now dialog-free: the referencers are resaved (`EditorAssetLibrary.save_asset`, the non-dialog path), then the redirectors are deleted with the live check.

| Redirector | Referenced by |
|---|---|
| `Props/DoorLock/Plate/textured/Materials/Designer_Logic_PBR` | SM_DoorLockPlate |
| `Props/DoorLock/Screw/textured/Materials/Designer_Logic_PBR` | SM_DoorLockScrew |
| `Props/DoorLock/Plate/textured/StaticMeshes/textured` | (none) |
| `Props/DoorLock/Screw/textured/StaticMeshes/textured` | (none) |
| `Characters/Teen/Mesh/TMP_Teen_Bounds` | (none) |

**Empty folders.**
- On disk now: `Content/FoA/Props/Phone/SM_Phone` and its `Materials`, `StaticMeshes` and `Textures`. `Content/Collections` and `Content/Developers/Admin/Collections` are engine folders; leave them.
- After T1, the whole `Characters/Protagonist` and `Fab` trees empty out.
- Remove empty folders offline during the next editor restart, the same way as the 2026-11-06 pass (`Saved/Cleanup/empty_dirs_removed_2026-11-06.txt`).

## Textures

### Duplicates (same source pixels)

25 groups.

- 14 groups sit entirely inside T1 (MetaHuman) and go with it.
- 5 are a (c) copy of an (a) texture, and are in T2:
  - `Teen/Mesh/T_Teen_T_Teen_..._Freckles`;
  - `mantel_clock_01_diff1`, `_nor_gl1` and `_rough`;
  - `hanging_picture_frame_03_nor_gl_png`.
- 4 groups are two in-use copies, one per material. Repointing one MI and deleting the copy saves about 7 MB cooked (world lane):
  - `desk_lamp_arm_01_diff` / `_diff1`;
  - `desk_lamp_arm_01_nor_gl` / `_nor_gl1`;
  - `desk_lamp_arm_01_metal-..._rough` / `..._rough1`;
  - `brass_candleholders_flame_diff` / `_diff1`.

### Oversized

32 runtime textures. The limit is 2048, or 1024 for UI and for props of 60 cm or less.

- **Small props on 2K maps:**
  - `book_encyclopedia_set_01_2k` (6 maps);
  - the Lux3D `picture_frame`, `bedside_book_stack`, `door_key` and `wire_hanger` (2 each, all 2048).
  - Set MaxTextureSize 1024 on them; the source stays untouched.
- **UI:** the `T_Intro_Game0*` plates and their `_Near` layers, 1920x1080, and `T_Intro_Bed*`, 2048x1152. These are full-screen story plates, so 1920 is the display size. Capping them at 1024 costs sharpness on 1080p screens, so this is the story lane's call. The DXT5 `_Near` layers are the larger half.
- No texture above 2048 is used at runtime. The only 8K map is the MetaHuman `T_Body_BC_VT`, which goes in T1.

### Uncompressed

- **UI:**
  - `T_UI_Logo_Unreal` (512²), `T_UI_Logo_Hayba` and `T_UI_Logo_Aholo` are BGRA8 UserInterface2D, about 1 MB, 0.8 MB and 0.2 MB cooked. Crisp logos justify it. The DXT5/BC7 option would save about 1.5 MB.
  - `T_UI_SoftDot` and `T_UI_FadeV` are tiny, so keep them.
  - `T_Intro_Game01_Sleep_Near` is a 1x1 placeholder that is still referenced. Is the plate missing? (story)
- **World:** 26 G8 TC_Grayscale maps cook to about 62 MB. Most of that is the 2048² AO and roughness maps of `plastered_wall`, `white_stucco`, `old_wooden_floor_02` and `T_FP_Brick_Roughness`, plus the decal masks. BC4 halves it.
- **VFX and PP:** `T_DreamNoise`, `T_SandGrain` and `T_VFX_Noise` are vector-displacement BGRA8 on purpose (noise precision), and small. Keep them.

## Reorganisation

The current `/Game/FoA` taxonomy is already sound:

- Maps, Gameplay, Characters, Cinematics, UI, Audio and VFX;
- PostProcess, Materials and Textures (shared masters and surface sets);
- Props (one folder per prop), Lux3D (one per generated item), Dressing, Fireplace, Art, Decals and Procedural.

Most of the content browser noise disappears with the deletions: `Characters/Protagonist`, `/Game/Fab`, the `_QA` folders, `/Game/LevelPrototyping`, and, if approved, the template map and its `__ExternalActors__`. Moves are kept to two sets, because many builder scripts load by path.

**Target taxonomy (after cleanup and moves):**

- `/Game/FoA/Maps`
- `/Game/FoA/Gameplay`: core BPs, plus `Beats`, `Encounter`, `Ambient` and `Jumpscare`
- `/Game/FoA/Characters`
  - `Player`: BP, ABP, Anims, Montages, Retarget, Input
  - `Teen`: Mesh, Cloth, Hair, Materials, Anim
  - `Garments`
- `/Game/FoA/Cinematics`, `/Game/FoA/UI`, `/Game/FoA/Audio`, `/Game/FoA/VFX`, `/Game/FoA/PostProcess`
- `/Game/FoA/Props/<prop>`: the door and its lock live here (set A)
- `/Game/FoA/Lux3D/<item>`: `SM_Lux3D_<Item>`, `MI_Lux3D_<Item>`, `T_Lux3D_<Item>_*` (set B)
- `/Game/FoA/Dressing`, `/Game/FoA/Fireplace`, `/Game/FoA/Art`, `/Game/FoA/Decals`, `/Game/FoA/Procedural`, `/Game/FoA/Textures`, `/Game/FoA/Materials`
- Outside FoA, keep `/Game/Characters/Mannequins` (the hidden driver mesh, rigs and anims), `/Game/ThirdPerson/Blueprints` (parent classes) and `/Game/Input`.

**Set A: door pieces into Props (11 moves, recommended).** The door's meshes sit in `/Game/FoA/Door/<mesh>/StaticMeshes/`, apart from their material in `Props/Door`. The DoorLock keeps the importer's `textured/<Type>/` nesting.

| From | To |
|---|---|
| `Door/SM_Door_Bedroom/StaticMeshes/SM_Door_Bedroom` | `Props/Door/SM_Door_Bedroom` |
| `Door/SM_DoorFrame_Bedroom/StaticMeshes/SM_DoorFrame_Bedroom` | `Props/Door/SM_DoorFrame_Bedroom` |
| `Door/SM_Door_Bedroom/Materials/Brass` | `Props/Door/MI_Door_Brass` |
| `Props/DoorLock/Plate/T_DoorLockPlate_BaseColor` | `Props/DoorLock/T_DoorLockPlate_BaseColor` |
| `Props/DoorLock/{Plate,Screw}/textured/Textures/T_DoorLock{Plate,Screw}_MetallicRoughness` | `Props/DoorLock/` (same name) |
| `Props/DoorLock/Screw/textured/Textures/T_DoorLockScrew_BaseColor` | `Props/DoorLock/` (same name) |
| `Props/DoorLock/{Plate,Screw}/textured/Materials/MI_DoorLock{Plate,Screw}` | `Props/DoorLock/` (same name) |
| `Props/DoorLock/{Plate,Screw}/textured/StaticMeshes/SM_DoorLock{Plate,Screw}` | `Props/DoorLock/` (same name) |

Tools lines to update after set A (7):
- `Tools/Lux3D/fit_door_lock.py:10-13` (PLATE, PLATE_MI, SCREW, SCREW_MI)
- `Tools/Lux3D/fix_greybox_materials.py:12`
- `Tools/Unreal/gameplay/door_tools_body.py:107` (`Door/SM_Door_Bedroom/Materials/Brass`)
- `Tools/Unreal/gameplay/place_bedroom.py:128` (`Door/SM_Door_Bedroom/StaticMeshes/SM_Door_Bedroom`)

Prerequisites:
- Delete the T2 Door MIs and the DoorLock `textured_texture_0`.
- Fix up the DoorLock redirectors.

**Set B: descriptive Lux3D names (36 moves, optional, worth it for judging).**

Lux3D use is 30% of the score, and today nine different meshes are all called `textured`, with materials `Designer_Logic_PBR` and textures `textured_texture_0/1`. Set B renames each to `SM_Lux3D_<Item>`, `MI_Lux3D_<Item>`, `T_Lux3D_<Item>_BaseColor` and `_MetallicRoughness`, and drops the `textured/<Type>/` nesting. The items are:

- bedside_book_stack, coat_hook_rail, curtains, door_key, picture_frame, radiator, the_shirt_enemy and wire_hanger;
- glass_of_water (mesh only);
- bedding_fixed.

The per-item folder names stay, so the importers (`bedroom_v3.import_once`, `import_dressing.py`, `encounter/import_shirt.py`) remain idempotent: they check for any mesh in `/Game/FoA/Lux3D/<item>`.

The channel suffixes are verified (`Tools/Cleanup/probe_lux3d_slots.py`, read-only, results in `Saved/Cleanup/lux3d_slots.txt`). On all 8 items, `textured_texture_0` feeds `BaseColorTexture` and `textured_texture_1` feeds `MetallicRoughnessTexture`.

Tools lines to update after set B (15):
- `Tools/Splats/build_sand_ambience.py:34, 45`
- `Tools/Unreal/encounter/build_sway_material.py:15`
- `Tools/Unreal/encounter/encounter_data.py:73`
- `Tools/Unreal/flow/clothing_hanger_graphs.py:16`
- `Tools/Unreal/gameplay/build_door_tools.py:52`
- `Tools/Unreal/gameplay/data_rows.py:16, 18, 22, 24` (composed from `{LUX}`, so the automatic scan misses them)
- `Tools/Unreal/gameplay/place_bedroom.py:16, 17, 127`
- `Tools/Unreal/player/build_bed_settle.py:12`
- `Tools/Unreal/player/hayba_bed_material.py:14`

**Not proposed, on purpose:**
- flattening the Poly Haven `<prop>/<prop>_1k/{Materials,StaticMeshes,Textures}` nesting (245 assets, many builder scripts);
- flattening the `VFX/Splats/Meshes/SM_X/SM_X/StaticMeshes` importer nesting;
- moving `/Game/Characters/Mannequins` or `/Game/ThirdPerson` (FoA classes inherit from them).

## Risk notes

1. **Deletes load each package.** `delete_asset` loads the package before deleting it, and the MetaHuman packages are heavy: 8K VT textures, grooms, DNA, MetaHumanCharacter assets of 100 MB or more. Each run therefore stops deleting after a 20 s budget and defers the rest to the next run.
   - At the default declaration of EXCLUSIVE-in-the-PIE-window, T1 needs about 30 runs across many windows.
   - In the maintenance window, set a declaration (`FOA_AREAS` or `FOA_EXCLUSIVE`) that the coordinator grants, and the runs go back to back.
2. **The reference check is live and strict.** An asset is deleted only when every live referencer is in the same batch. Batches are ordered so that referencers go first, and reference cycles stay together. Anything still referenced is kept and listed, never force-deleted. A T2 or T3 asset that is referenced by an unapproved one is kept.
   - Read-only dry runs against the live registry (13:0x, after the restart):
     - T1: all 363 would go.
     - T2: all 59 would go.
     - T3: 411 of 418 would go. The other 7 (`UAL_Idle_FoldArms_Loop`, `IK_UAL1` and the `Source/UAL1` rig) are referenced only by T2 backups (`RTG_UAL1_Before`, `ABP_FoAPlayer_BeforeCrouch_014458`), so run T2 before T3.
3. **Moves resave referencers.** The rename resaves every loaded package that pointed at a moved asset, and the fix-up resaves the rest. That includes `L_Tutorial_Bedroom` (the door, the lock and the Lux3D props are placed there), BP_Door, the door-tool BPs, DT_Items and the encounter data. Run moves only in the maintenance window, with no lane holding the level or those BPs. Otherwise a lane's unsaved edits are saved along with them, or lost.
4. **Builder scripts break after moves** until the Tools lines listed above are updated. Those lines are in other lanes' files: hand each owner its list, or let the coordinator approve a one-pass string update.
5. **Recent assets.** Lanes are working right now. 55 candidates changed in the last 48 h. Approve T3 per owner, and re-run the audit right before executing, because new references may have appeared.
6. **The template map ships today**, and it is the only (d) item with a build impact (about 0.8 MB). If it is deleted, delete its `__ExternalActors__/ThirdPerson` and `__ExternalObjects__/ThirdPerson` packages too. They are in the (d) list.
7. **Rollback.** Every delete is logged with its size to `Saved/Cleanup/deleted_assets_<date>.txt`. Restore from the coordinator's git snapshot.

## Runbook for the combined maintenance window

This covers moves A and B, quarantine_list_2, the empty folders and Hayba restart 7. Use `$env:FOA_AGENT='cleanup'` throughout.

**Editor open.** No lane may hold `L_Tutorial_Bedroom`, `DT_Items`, the encounter data, or the door and door-tool BPs.

1. Move set A, dry run first:

   ```
   python Tools/Cleanup/move_assets.py --plan Saved/Cleanup/moves.json --set A --dry-run
   python Tools/Cleanup/move_assets.py --plan Saved/Cleanup/moves.json --set A
   ```

   Then the same two commands with `--set B`. That is 11 and 36 moves. The renames save the asset and its loaded referencers. Any redirector left over is fixed by resave-then-delete, never by `asset_fix_redirectors`.
2. Retarget the Tools paths:
   - preview: `python Tools/Cleanup/retarget_tools_paths.py --dry-run` (the diff is in `Saved/Cleanup/moves_tools_patch.diff`; 31 paths in 14 files when it was written);
   - apply: `python Tools/Cleanup/retarget_tools_paths.py`;
   - check: `python Tools/Cleanup/retarget_tools_paths.py --check`. It must report 0 problem files and 0 missing. It compiles every touched script and fails on any old path still named.
3. Verify the assets: `python Tools/Unreal/integration/run_read.py Tools/Cleanup/verify_moves.py`. All 47 must be OK: each new path loads, nothing is left at the old path, and its referencers are kept. Then check `editor_get_state` for dirty packages; the coordinator saves all.

**Editor closed.**

4. `python Tools/Cleanup/quarantine.py --list Saved/Cleanup/quarantine_list_2.txt` moves the 10 textures (15.9 MB).
5. `python Tools/Cleanup/quarantine.py --prune-empty` removes 20 empty folders.
6. The coordinator installs Hayba restart 7 and relaunches.

**After the relaunch**

7. Run `verify_moves.py` again: the loads after a restart are the real proof.
8. Re-dump the registry (2 chunks) and run `audit.py`.
9. Grep FoA.log for missing references.
