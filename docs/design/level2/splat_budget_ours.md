# Level 2 splat budget: what our splat-mesh pipeline can carry

World lane, 2026-11-10. Offline and read-only (the editor was held for a playtest). Each number below is marked
**measured** (from files, logs or CSVs) or **estimated** (arithmetic from measured inputs). Read with
`splat_feasibility.md`, the research lane's report on the Aholo API, external UE 3DGS plugins and city sources.

## 1. What the pipeline is today

`Tools/Splats/ply_to_splatmesh.py` (PLY) and `glb_to_sandsplats.py` (GLB samples) write **one static mesh per object,
with one quad per splat**: 4 vertices at the splat centre and 2 triangles. The material billboards each quad with World
Position Offset.

- **Shipped master `M_SplatMesh`** (measured from the asset, 11-06): `BLEND_Masked`, `MSM_DefaultLit`. Soft alpha is a
  per-pixel Gaussian against interleaved-gradient noise, a **dithered mask that TSR resolves**. Nothing is sorted and
  nothing is translucent.
  - The 11-06 cost dump (`Saved/PPShots/splat_cost.txt`) still lists `BLEND_TRANSLUCENT`. That predates the slim batch
    (`hayba_batches.py slim_master`), which switched it to Masked.
- **Vertex shader** (measured): the animated sand behaviour (MF_SplatFlow 'Motion': drift, morph, crumble) is
  **4422 DXIL instructions per vertex** after the slim (9287 before; `Tools/Splats/hlsl/bench`). The pixel shader was
  365 instructions in the pre-slim dump.
- **Draw calls:** one per mesh component, per pass. **Nanite is off on all splat meshes** (the WPO billboards need the
  classic path).
- **Vertex channels** (measured, README channel map): POSITION, NORMAL and TANGENT (anisotropy frame, unused by the
  material), TEXCOORD_0 (corner), TEXCOORD_1 (radius, seed), TEXCOORD_2-7 (SH degree 1 + sigmas, all zero for every
  Lux3D file so far) and COLOR_0.

## 2. Measured footprint of the current assets

| Asset (sidecar `P:/FoA-Assets/splatmesh/*.splatmesh.json`) | Splats kept | Source splats | Tris | .bin (glTF) | .uasset |
|---|---|---|---|---|---|
| fear_of_adulthood_clock / briefcase / the_night_mare / nightmare_v1 / sand_hand | 40,000 each | 0.39-1.95 M | 80,000 | 20.2 MB | 3.06 MB (clock) |
| SM_SandStream, SM_SandTrickle_Ceiling, SM_SandTrickle_Clock | 16,000 | n/a | 32,000 | 8.1 MB | 0.80 MB |
| SM_SandMonster | 14,000 | n/a | 28,000 | 7.1 MB | n/a |
| SM_AlarmClockSplats | 12,000 | 827,600 | 24,000 | 6.0 MB | 1.02 MB |
| SM_SandMoundSplats_A/B/C, SM_SandSuit | 9,000 | n/a | 18,000 | 4.5 MB | 0.77 MB |
| SM_SandHourglass | 8,000 | 1,503,936 | 16,000 | 4.0 MB | 0.73 MB |
| SM_SandShirtImprint | 7,000 | n/a | 14,000 | 3.5 MB | n/a |
| crumbs / burst / face drift | 314-1,500 | n/a | 0.6-3k | 0.2-0.8 MB | n/a |

**Per splat** (measured): 4 vertices and 2 triangles. 504 bytes in the glTF .bin (4 x 120 B vertex + 24 B index).
**50 to 85 bytes on disk** in the cooked .uasset (it compresses well).

**Per 100k splats:**
- **Disk:** about 5-8.5 MB uasset, 50.4 MB of glTF interchange.
- **GPU memory** (estimated: UE static mesh vertex buffers = position 12 B + packed tangent basis 8 B + 8 FP16 UVs 32 B
  + colour 4 B = 56 B/vertex, so 224 B + 24 B index per splat): **about 25 MB**.
- **A 1 M splat scene is about 250 MB of VRAM** in today's layout.

## 3. Measured frame data we have (RTX 5070, editor PIE at 1286 x 878)

| Run | GPU time median / p95 | Frame time median | Primitives drawn median | Draw calls median |
|---|---|---|---|---|
| wake intro, `Saved/WorldShots/perf/after_intro.csv` | 2.75 / 2.88 ms | 11.2 ms | 256k | 412 |
| gameplay sheet, `gp_after1.csv` | 3.00 / 3.60 ms | 14.5 ms | 306k | 543 |

The bedroom carries about 150k splats in placed meshes, mostly hidden until their beat. Visible at once is
estimated at 30-60k. **The whole frame stays under 4 ms of GPU** on this card.

**We have no isolated per-splat GPU timing.** Measuring one is the first item in section 6. The editor frame is
game-thread bound (Slate), not GPU bound.

## 4. Extrapolated budget (estimated)

Assumptions:
- **Low-tier target:** GTX 1650 / RTX 3050 class, about 1.5 T simple instructions/s, roughly a tenth of the 5070.
- **Resolution:** 1080p with TSR.
- **Frame budget:** 16.6 ms at 60 fps, of which **4 ms for splats**.
- **Vertex passes:** each animated splat vertex runs in about 3 passes (depth prepass, base pass, velocity), because
  WPO re-runs per pass.

**A. Today's material, animated (4422-instruction VS):**
- 100k splats = 400k vertices x 4422 x 3 passes = 5.3 G instructions, about **3.5 ms per 100k on low tier** (0.35 ms
  on the 5070).
- **Low-tier budget: about 100-120k animated splats** on screen. That's fine for hero props and effects, and far too
  small for a world.

**B. A lean static world variant (billboard + dissolve only, about 120 VS instructions):**
- Vertex cost per 1 M splats is about 1.4 G instructions over 3 passes, **about 1 ms on low tier**.
- Pixel cost then dominates. Dithered-masked quads lose early-Z in the prepass, so every covered pixel runs the clip
  test. At an average of 20-40 px per visible splat at 1080p, 1 M visible splats is 20-40 M clip invocations
  (about 60 instructions) plus the base pass on survivors. That's **about 1.5-2.5 ms on low tier**.
- Tiny quads waste 2x2 quad-shading lanes; add **x1.5-2** for distant splats.
- **Low-tier budget: about 0.8-1.2 M visible splats** at 60 fps. About 3-5 M on a 5070-class card.

**C. Memory is the harder wall:**
- In today's vertex layout, 1 M splats is about 250 MB of VRAM and 3 M is 750 MB.
- The <1 GB build target is met on disk (8.5 MB per 100k means 3 M is about 250 MB), but not in VRAM on a 4 GB card.

**D. Translucency with sorting** (the coloured dream world may want true soft blending):
- UE does not sort triangles within one mesh. Correct back-to-front blending needs a per-frame GPU sort of splat
  indices (about 1 ms for 1 M keys on a mid card).
- Every overlapping layer is shaded, with no early-Z, so pixel cost multiplies by depth complexity (4-10x in dense
  scans).
- **Low-tier budget with sorted translucency: about 150-300k splats.** Keep dithered masking unless a specific asset
  needs soft layering, and then only that asset.

## 5. What has to change for world-scale splats

In order of payoff:

1. **A lean static world material** (`M_SplatWorld`): billboard WPO + dissolve + optional shockwave, with no flow
   behaviour. Target VS under 150 instructions. Keep MF_SplatFlow for hero sand.
   - The shockwave and dissolve-to-black-sand can stay closed-form functions of (time, seed, distance to an epicentre
     MPC vector). That's the same stateless style as `flow_lib.hlsl`, so it adds tens of instructions, not thousands.
2. **Chunking:** split world scans into spatial cells (about 10-20 m, 50-150k splats each), one mesh per cell with
   tight bounds plus the WPO bounds extension. That gives frustum and occlusion culling per cell and keeps draw
   counts in the low hundreds.
   - Convert the PLY with a `--cells` option in `ply_to_splatmesh.py` (one glTF per cell plus a manifest), placed like
     `place_trims.py` does.
3. **LOD by subsampling:** per cell, LOD0 100%, LOD1 25% (radius x 2), LOD2 6% (radius x 4), as static-mesh LODs
   (screen-size switching) or HLOD proxies.
   - The converter's importance-weighted `select()` already does this decimation. It needs to run per LOD with
     opacity x radius as the weight.
   - Distance culling (max draw distance per cell) for the far city.
4. **Slimmer vertex layout:** Lux3D files carry no SH and the material ignores the anisotropy frame.
   - Drop NORMAL/TANGENT and TEXCOORD_2..7, and derive the corner from the vertex index (vertex ID % 4).
   - About 24 B/vertex, so roughly **2.3x less VRAM**: about 110 MB per 1 M splats.
   - Keep the full layout only where SH or anisotropic splats are proven to matter.
5. **Keep dithered masking with TSR** as the default. Sorted translucency only for a hero dream asset with a known,
   small splat count.
6. **Colour:** the coloured dream world needs the material's `Mono` switch off and the `PP_DreamMono` colour-keep path
   (stencil 1 or `ColorReveal`) for that level. The monochrome city uses the existing path unchanged.
7. **If a world scene must exceed about 1 M visible splats on low tier:** a GPU-driven path (compute-culled instanced
   quads, or an external UE 3DGS plugin per the research lane) is the next step. That's no longer "our pipeline".

## 6. Proofs to run after the hold (all world lane, about 1 hour)

1. **Per-splat GPU cost:** in PIE, `stat gpu` / `ProfileGPU` A/B with every splat component hidden vs visible in
   the bedroom (about 30-60k visible). Then the same with one 40k mesh duplicated x10 (400k) in an empty test map.
   Report ms per 100k for the prepass, base pass and velocity pass separately.
2. **Lean material:** build `M_SplatWorld` (static billboard + dissolve + shockwave) and re-measure the 400k case.
   This replaces the 3.5 ms vs 1 ms estimate above with numbers.
3. **Chunk/LOD prototype:** convert one public city PLY (chosen from the research lane's sources) with `--cells` and
   three LODs, then measure on a mid card and a capped-clock run (`r.ScreenPercentage` + `t.MaxFPS` as a low-tier
   proxy).

## 7. Integrated-GPU tier: Level 2 on most consumer devices (estimated)

The target is Intel Iris Xe (96 EU) or Radeon 680M class. The brief assumes **about 1/10-1/15 of a GTX 1650**. That's
conservative: published game benchmarks put Iris Xe at roughly 1/2-1/3 of a 1650 and the 680M near it. Both share
system-RAM bandwidth (50-100 GB/s), so pixel and overdraw cost hurts them most. This section budgets to the brief and
treats real devices as headroom.

Our reference: the whole bedroom frame costs **2.8-3.0 ms GPU on the RTX 5070** at 1286 x 878 (measured). The brief's
iGPU is about 1/50 of a 5070, so **the same frame would take about 140-150 ms (about 7 fps)** at today's settings.
Level 2 on an iGPU therefore depends on the whole-game Low profile (section 8), not only on splats.

**iGPU splat targets** (30 fps, 720p internal upscaled by TSR to the display, about 8 ms of GPU for splats):

| Item | Target |
|---|---|
| Visible splats | **about 80-150k** (top-down: depth complexity about 1.5-3, so overdraw stays low) |
| Material | `M_SplatWorld_Lean`: **Unlit**, Masked, dithered, **no sort**, **SH off, view-independent colour** (vertex colour only). VS about 40-60 instructions: billboard from camera right/up (constant per frame in a top-down rig), radius, dissolve gate. PS about 20 instructions: Gaussian + IGN clip + emissive. Velocity off for static cells. One draw per cell. |
| Vertex layout | slim: position 12 B + UV1 (radius, seed) 4 B FP16 + colour 4 B, corner from vertex ID: **about 20 B/vertex, about 100 B/splat**. 150k resident splats is about 15 MB, comfortable in shared memory. |
| Screen-density subsampling (top-down zoom) | Per cell, static-mesh LODs at 100 / 25 / 6 / 1.5 % (importance-sampled, radius x 1 / 2 / 4 / 8). Choose the LOD so **visible splats is about the screen pixels / 12** (about 75k at 720p): zooming out raises the LOD, so the splat count stays flat as the visible area grows. Static-mesh LOD screen sizes are set per cell from the camera height and FOV, and the rig's zoom drives them. |
| Visible-cell streaming around the car | 32 m cells on a World Partition grid. Loading range = the view rectangle's half-diagonal + one cell, in the car's travel direction. About 9-16 cells resident. Cells outside the view are culled by bounds, and nothing behind the camera exists in a top-down view. Cell import costs about 100 B/splat, so a 100k-splat cell streams 10 MB. |
| Effects only near impacts | One material with a **dynamic branch in the VS on distance to an epicentre** (MPC: up to 4 epicentres with start times). Outside the radius the vertex takes the 10-instruction static path, inside it runs the shockwave / dissolve-to-black-sand closed-form motion (`flow_lib.hlsl` style, about 300-500 instructions, not the 4422-instruction hero flow). Branches are coherent per splat cluster, so the cost scales with the splats inside active impact radii (target 20k or fewer animated at once). |

**Fallback if live splats still don't fit: bake the static city to top-down tiles and impostors.**
- **Bake:** per 32 m cell, an orthographic top-down SceneCapture of the lean unlit splats into albedo + height
  (+ optional normal from height): 2048^2 per cell, about 1.6 cm/px, BC1 + BC4 about 3.5 MB per cell, through texture
  streaming.
- **Runtime:** each cell is one unlit tile quad, or a low-poly heightfield for rooftops and parallax. Tall landmarks
  get octahedral impostors (8 x 8 views, 1024^2).
- **Live splats only where needed:** a dissolve or hit swaps the affected cell (or a 10 m sub-cell) from tile to
  splats with a 0.2 s cross-fade. Afterwards the dissolved footprint stays as a black-sand decal or tile variant, so it
  never reverts.
- **Cost:** tiles cost about one textured draw per cell, so the city renders at iGPU cost in the low single
  milliseconds. Live splats cost only where effects play.
- **Quality trade:** no parallax on flat tiles at a steep top-down angle (acceptable for a fixed-pitch rig), and the
  bake must re-run when the scan changes.

## 8. A "Low" scalability profile for the whole game (estimated; proofs after the hold)

Current project settings (measured, DefaultEngine.ini):
- `r.DynamicGlobalIlluminationMethod=1` and `r.ReflectionMethod=1` (Lumen)
- `r.Shadow.Virtual.Enable=1`
- `r.GenerateMeshDistanceFields=True`
- Lumen's mesh-SDF tracing off (global SDF only)
- MegaLights cvars are present in the device profile log.

DefaultScalability.ini only sets texture pools today.

**Proposed `sg.*@0` (Low) overrides** (DefaultScalability.ini belongs to the coordinator, so this is a proposal):

| Area | Low setting | Why |
|---|---|---|
| GI | `r.DynamicGlobalIlluminationMethod=0` (none) plus an **authored fake-bounce light set** (below); SSGI off | Lumen GI is the largest single cost and unaffordable on an iGPU |
| Reflections | `r.ReflectionMethod=2` (SSR at low quality) or 0, plus one box reflection capture in the bedroom | glossy floor / door / brass keep a hint of reflection |
| AO | `r.AmbientOcclusionLevels=1` (SSAO, half resolution), DFAO off | contact darkness that Lumen used to provide |
| Shadows | `r.Shadow.Virtual.Enable=0` (classic shadow maps), `r.ShadowQuality=1`, max 2 shadow-casting lights in view (Light_Moon and Light_DoorGap); desk lamp, fills and cine fills set to no shadows | VSM page cost |
| MegaLights | off | not needed with about 10 lights |
| Resolution | `r.ScreenPercentage=50-67` with TSR (or the platform upscaler), 30 fps target on iGPU | pixel-bound tier |
| Translucency, fog | volumetric fog off, translucency lighting volume low | the light-shaft cards are emissive, so unaffected |
| Post-process | `r.MaterialQualityLevel=0`: the dream materials already carry QualitySwitch nodes (`build_dream_post.quality()`: echo taps 6 to 3, lens taps 16 to 8). Add Low paths: pixel-sort off, ink-edges single tap, face-blur half-resolution taps, local exposure off | PP is a fixed per-pixel cost that scales with resolution |
| Splats | lean unlit material on Low (sections 5 and 7); hero sand keeps the animated flow but at LOD1 density | |
| Hair / characters | groom or hair-card LOD 1, MetaHuman/teen LODs one step down | |

**What Level 1 would look like under Low, and what must be authored so it still reads:**
- **Today's dark mood depends on Lumen bounce.**
  - Measured: T3/T4/T7 are lit mostly by the **moon's bounce**. When Light_Moon was dimmed, T3 fell from 0.137 to
    0.064, as fast as the directly lit bay (moon_d / bay_tune runs).
  - **With Lumen off, those views go near-black** (only the direct moon patch, door gap and desk lamp remain).
  - The gameplay exposure floor would lift them by its maximum 1.8 stops, but a black-shadowed floor lifted is still
    noisy black.
- **Authored for Low** (a `BP_LowGIFill` set: about 4 shadowless, specular-free movable lights, visible only when GI
  is off, read once at BeginPlay from `r.DynamicGlobalIlluminationMethod` or the scalability level; same idea as
  BP_ViewFill):
  1. **Moon bounce off the floor patch:** a large rect (about 200 x 120 cm) at the moon patch, facing up, about
     10-20 lm, with a moonlight temperature. It replaces the floor-to-room bounce that lights T3, the bed side and the
     wardrobe.
  2. **Bay bounce:** the existing Light_MoonFill_Bay raised from 3 lm to about 10-15 lm under Low.
  3. **Fireplace and moon bounce:** the existing Light_MoonBounce_Fireplace (15 lm) kept.
  4. **Door-gap spill:** a weak wide rect inside the door, about 3 lm, so the T10 doorway reads.
  5. **Sky fill:** SkyLight intensity about 0.07 to 0.2 under Low, with SSAO keeping corners dark.
- **Kept as is:**
  - Cine lights (all direct).
  - SandRim (direct, channel 2).
  - Light shafts (emissive cards).
  - The exposure floor and curve. They should need no change, because the curve keys on scene EV and still lifts only
    dark views.
- **Visual cost of Low:**
  - No soft colour bleed or contact GI.
  - Shadows sharper and lower resolution.
  - Glossy reflections largely gone (SSR only on-screen).
  - Dream PP slightly grainier (fewer taps).
- **Expected iGPU result for Level 1 at Low:**
  - About 0.6-1.0 ms on the 5070 at 50% screen percentage (estimated), which is **about 30-50 ms on the brief's
    iGPU**: 20-30 fps.
  - Real Iris Xe or 680M devices, about 3-5x faster than the brief's assumption, would hold 30-60 fps.

## 9. Proofs after the hold (world lane; about 2 hours in all)

1. **Low profile A/B on the 5070:** apply the Low cvars in PIE (no config edit: console only) and shoot the
   gameplay sheet (T3, T4, T7, look-down, yaw 195, bay, phone hold) plus the wake-film frames at Low vs High.
   Record GPU ms per view. This measures how dark Level 1 goes without Lumen.
2. **`BP_LowGIFill`:** author the 4 fills, tune them against the same sheet until the Low frames match the High
   frames' mean luma within about 20% and keep the dark mood, then re-measure GPU ms.
3. **Splat A/B (section 6.1) at both profiles,** plus the lean unlit splat material prototype on a 400k-splat test
   map at 720p internal.
4. **Real iGPU check:** if any Iris Xe or 680M machine is available, a packaged build at Low gives the true number.
   The 5070 times-ratio estimate is only a proxy.
