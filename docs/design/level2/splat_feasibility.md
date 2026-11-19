# Level 2 splat feasibility: Aholo worlds, a lidar city, splats on integrated GPUs

Research lane, 2026-11-10. This was research only: the editor was not opened, no generating or paid endpoint was
called, and the API key was never printed. The only live API calls were two read-only list endpoints (section 1).
The world lane's measured footprint of our own splat meshes is in `splat_budget_ours.md` next to this file. This
report doesn't repeat it.

Every claim below is tagged:
- **[verified]**: read from a primary source or measured by me.
- **[estimate]**: arithmetic from stated inputs.
- **[unverified]**: I couldn't confirm it.

## Recommendation

**Tools**

1. **Dream worlds (both coloured scenes): Aholo World generation (SpatialGen) API.** Send a text prompt and get back
   SPZ splats plus a 360 panorama. My Lux3D key already authenticates on this service.
   - Pipeline: strip the generated sky shell and use the returned panorama as the sky instead. Decimate the core with
     our existing importance sampler, then convert it into our splat-mesh format.
   - This is a second Manycore tool on screen, on top of Lux3D, which helps the 30% tool criterion.
   - Cost: 30 credits per world, 15 minutes or less per world.
2. **City: aerial lidar, converted offline into static splat cells.**
   - Each cell is one static mesh, 50 x 50 m, holding **view-fixed opaque quads**.
   - At rest there's no World Position Offset and no dither. **The fixed top-down camera makes billboarding
     unnecessary**, so the city renders like plain static geometry.
   - World Position Offset is switched on only for the few cells near a meteor or a dissolving building, with
     `SetEvaluateWorldPositionOffset` (BlueprintCallable on StaticMeshComponent in 5.8).
   - Source data: **Toronto's GTA 2023 lidar plus the City's 3D Massing**. Both are free under attribution-only
     Canadian open-government licences, which need your OK because they are not literally CC-BY. The strict-CC0
     fallback is raw AHN4 Amsterdam (section 3).
3. **Engine: a Low profile for integrated GPUs.** Lumen off, Virtual Shadow Maps off, TSR at Low quality from
   720p to 1080p, unlit splats (section 4).
4. **Hayba C++ spike: a packed-buffer splat plugin** at 16-20 bytes per splat with vertex pulling (section 2.4).
   - If it lands, it replaces the city's static mesh cells. **Disk cost then drops about 8x.**
   - The project doesn't depend on it: everything above ships without it.

**Splat budget per scene** [estimate]. Sized for Intel Iris Xe at 1080p output from 720p internal. GPU times are
estimates; see section 4 for the arithmetic.

| Scene | Visible at once | Total in level | Disk, our mesh format, lean layout | GPU on Iris Xe (60 fps target) |
|---|---|---|---|---|
| Dream A (colour, after the bedroom door) | at most 150k | at most 150k | about 10-20 MB | about 1.2-2.3 ms |
| Dream B (colour, end transition) | at most 150k | at most 150k | about 10-20 MB | about 1.2-2.3 ms |
| City (mono, top-down) | 60-120k | at most 800k in the drive corridor | about 50-110 MB | under 1 ms at rest; plus the live cells |
| Live effect cells (dissolve, shockwave) and hero sand | at most 50k animated | (pooled) | small | about 0.5-1 ms |

**What to build first**

1. **Done on 2026-11-10 (section 7).** Dream A is generated, converted to `SM_DreamA` (150k splats, lean layout)
   and reviewed offline. `ply_to_splatmesh.py` now reads SPZ v2/v3 and has `--max-radius` and `--lean`. Next:
   import `SM_DreamA` with the lean world material, and judge it in the engine.
2. **Write the lean static-world material `M_SplatWorld`:** billboard or view-fixed quad, dissolve, shockwave, and a
   colour/mono crossfade (section 5). Keep `M_SplatMesh` for the hero sand.
3. **Add a stress map and the iGPU profile.** Run 100k, 300k and 1M splats on a real integrated GPU:
   - **In a packaged build, force the motherboard iGPU** under Windows Settings, Display, Graphics, Power saving.
     That only works if the CPU has one.
   - Otherwise run on any Iris Xe or 680M laptop.
   - Replace the estimates in section 4 with measurements.
4. **Convert the city lidar into cells**, after you approve a licence from section 3.
   - `--cells 50 --facing <camera dir> --density N`, written as one glTF per cell plus a manifest.
5. **City events:** a meteor impact sets an MPC vector, and Blueprint turns on WPO for cells within range.

**Risks**

- **SpatialGen outdoor scenes are Beta** [verified, API spec]. Prompt the dream as an enclosed space.
- **Generated worlds are small.** Outdoor ones are a detailed core plus a far shell (section 1.3). Indoor ones are a
  closed room of about 8 x 10 m (section 7). That suits a short walk and a fall, but not a large explorable world.
- **City disk size is the binding constraint on integrated GPUs**, not shading: about 140 B per splat in our mesh
  format against about 16 B per splat in packed formats. Keep the drivable area small, or bake the static
  surroundings (section 4.4).
- **No public UE 3DGS plugin supports 5.8 with an open licence and per-splat material hooks** (section 2.3), so
  dissolve and shockwave stay in our own pipeline.
- **Splat scale:** the outdoor showcase wasn't metric, but indoor Dream A looks metric (section 7). Check each
  world.
- **All iGPU numbers are arithmetic, not measurements.** Step 3 above exists to replace them.

---

## 1. Aholo World generation and reconstruction

### 1.1 What the API offers [verified]

Source: World service OpenAPI spec (https://labs.aholo.ai/api-docs/specifications/services/world/openapi.en.yaml),
the docs index (https://labs.aholo.ai/api-docs/en/llms.txt) and the quick start
(https://labs.aholo.ai/api-docs/en/quickstart).

| | Generation (SpatialGen) | Reconstruction (Reality) |
|---|---|---|
| Endpoint | `POST https://api.aholo.ai/global/world/v1/generations` | `POST https://api.aholo.ai/global/world/v1/reconstructions` |
| Inputs | Text only, one image, or text + one image (.jpg/.jpeg/.png/.webp) | 20 or more images, one video (.mp4/.mov), or Insta360 .insv. `taskQuality` is `low`, `normal` or `high`. `scene` is `model` or `space` (indoor). Optional `useMask` |
| Scope | "Indoor scenes are more mature and stable today; non-indoor input is allowed but still Beta" | Objects or indoor spaces |
| Poll | `GET /global/world/v1/{worldId}` until `SUCCEEDED` / `FAILED` / `CANCELED` / `TIMEOUT` / `REJECTED` | same |
| Outputs | `assets.splats.urls.plyPath`, `spzPath`, `lodMetaPath` (LOD chunk metadata after post-processing), `assets.imagery.panoUrl` (360 panorama), `assets.semanticsMetadata.upAxis` (`Z` for this service) | same, without the panorama |
| Auth | `Authorization: <key>` with no Bearer prefix, same as Lux3D | same |

- **Text prompts:** 20 characters minimum, 50-300 recommended.
- **Image input:** 480x480 to 4000x4000.
- **Timing:** the panorama in 3 minutes or less, Gaussians in 15 minutes or less. Source:
  https://aholo.featurebase.app/help/articles/8004872-create-imagined-3d-worlds-with-ai
- **Image upload:** an image input must first be uploaded (`GET /global/asset/v1/token`, then the OUS upload).
  Text-only skips that step.

### 1.2 Cost, limits, and whether our key works

- **Price** [verified, https://www.aholo.ai/pricing, read 2026-11-10]:
  - SpatialGen World Generation costs **30 credits per task** (listed as "65%+ off").
  - World Panorama Generation costs 10.
  - Reality 3DGS Reconstruction costs 20, 50, 80 or 100 credits per task (Flash, Standard, Professional, Ultra).
  - For comparison, our recent Lux3D G1 text-to-3D tasks consumed 20 credits each (from our own task list).
- **Plans** [verified]:
  - Free: SpatialGen 30 free trials, 1 concurrent task.
  - Pro ($14.9 per month, 1000 credits): 2 concurrent SpatialGen tasks.
  - Pro also lists "Commercial use of generated models" under Lux3D. **Check which plan this account is on before
    shipping** [unverified for our account].
- **The key works** [verified]: `POST /global/world/v1/list` with the existing Lux3D key returned **HTTP 200**
  `{"count":0,...,"result":[]}`. The account is authenticated on World and has no worlds yet.
  - Whether generation draws on the free trials or on credits when called through the API is **[unverified]**.

### 1.3 What a generated world actually contains [verified, measured]

I decoded the public showcase world "Desert Camp" (an outdoor SpatialGen scene, https://spatialgen.aholo.ai/detail/3FO4K4VY2B7V).
Its viewer loads an SPZ from `maas-cos.kujiale.com`.

- **SPZ version 2 (gzip), SH degree 0, 482,211 splats, 7.3 MB (15.1 B per splat).** Colour is view-independent.
- **Core:** 282k splats lie within 20 units of the centre.
  - 90% of the core sits within 2.5 units horizontally, and its height is -3.7 to +2.6.
  - Median sigma is 0.006 units.
- **Shell:** the other 200k (42%) form a dome at a radius of about 105 units, with large splats (median sigma 0.78).
  **That shell is the panorama baked as splats.** Drop it and put `panoUrl` on an unlit sky sphere. That saves 42%
  of the splats for free.
- **Up axis is Z.** That agrees with `upAxis: Z` in the spec.
- **Scale:** the core is a few units across for a "campsite among dunes", so the scale is probably not metric
  [unverified].
- **The PLY that page loaded is not a 3DGS PLY.** It holds 196,287 points with x, y, z and uchar RGB only, from a
  different task id. For our own API world, though, `plyPath` **is** a full 3DGS PLY [verified, Dream A, section
  7]. We consume `spzPath`, which is 4x smaller.

### 1.4 The request for Dream A (needs your OK: 30 credits)

```http
POST https://api.aholo.ai/global/world/v1/generations
Authorization: <key from C:\Users\Admin\.foa\lux3d_api_key>
Content-Type: application/json

{"name": "FoA L2 Dream A",
 "prompt": "A vast enclosed dream hall whose floor, walls and arches are made of flowing coloured sand in deep crimson, amber and teal, a lone wooden bedroom door standing open in the middle, warm hazy light from above, surreal and calm"}
```

- **Prompt shape:** 228 characters, inside the recommended 50-300. It describes an enclosed space on purpose,
  because indoor is the stable path. The open door ties back to level 1's exit.
- **Poll:** `GET https://api.aholo.ai/global/world/v1/{worldId}` every 10-15 s. Download `spzPath` and `panoUrl`
  as soon as the status is `SUCCEEDED`.
- **Image variant:** text + image (a bedroom-door style frame as the single image) needs the asset-upload flow
  first. Try text-only first.
- **Implementation:** a 60-line urllib script modelled on `Tools/Lux3D/lux3d_batch.py`, which already handles the
  key, polling and the 'never auto-retry a timed-out create' rule. No new dependency is needed; the official
  `manycore-aholo-sdk-world` pip package is optional.

---

## 2. Rendering world-scale splats in UE 5.8

### 2.1 How far our splat meshes scale

The world lane measured these (`splat_budget_ours.md`):
- 4 vertices and 2 triangles per splat.
- About 224 B of vertex data plus 24 B of index per splat in GPU memory (about 25 MB per 100k).
- 50-85 B per splat in the editor .uasset.
- Nanite off, one draw call per cell.

What limits it, in order [estimate]:

1. **Disk and memory.** At about 140-250 B per splat, a 1M-splat level costs about 140-250 MB of VRAM and roughly
   70-190 MB cooked. That's acceptable for 150k-splat dream rooms, but it's the wall for a city (section 4.3).
2. **Vertex fetch bandwidth on integrated GPUs.** Every pass re-reads 4 fat vertices.
   - A WPO billboard runs about 3 vertex passes: depth prepass, base pass and velocity.
   - That's about 670 B per splat per frame in today's layout, and about 400 B in a lean layout.
3. **Pixel cost of dithered masked splats.** No early-Z in the prepass, plus 2x2 quad over-shading on tiny quads.
4. **Sorting:** none. Dither plus TSR stands in for blending. That is our advantage: no sort pass and no
   order-dependent blending.

**Scaling tools available in Blueprint and the editor alone:**
- Cells of 10-50 m, one mesh each, giving per-cell frustum and distance culling.
- Static-mesh LODs by importance subsampling.
- Max draw distance.
- `SetEvaluateWorldPositionOffset` per cell [verified in `StaticMeshComponent.h`, UE 5.8, BlueprintCallable] and
  `WorldPositionOffsetDisableDistance`.
- Custom Primitive Data per cell, for event parameters without dynamic material instances.

### 2.2 The lean layout (converter flag, no editor work)

- **Keep:** POSITION, TEXCOORD_0 (corner), TEXCOORD_1 (radius, seed) and COLOR_0.
- **Drop:** TEXCOORD_2..7. SpatialGen is SH degree 0 and lidar has no SH. UE still stores a packed tangent basis.
- **Size** [estimate]: 4 x (12 + 8 + 8 + 4) = 128 B of vertex data plus 12 B of 16-bit index (cells under 16,384
  splats) = **about 140 B per splat**, against about 248 B today.
- **For the top-down city, bake the quad corners** into POSITION, facing the fixed camera, instead of the 0.1 mm
  nudge. Then the material needs no WPO at rest, and a cell renders as ordinary opaque static triangles.

### 2.3 Free UE 3DGS plugins

None fits all of our constraints (UE 5.8, open licence, per-splat material hooks for dissolve and WPO).

| Plugin | Licence [verified from LICENSE] | UE versions | How it renders / composites | Material hooks | Fit |
|---|---|---|---|---|---|
| NanoGS (https://github.com/TimChen1383/NanoGaussianSplatting) | MIT | 5.6, 5.7 | Nanite-style cluster LOD, screen-space error, GPU radix sort, sorted alpha via a global accumulator | Opacity, splat scale, SH order, LOD threshold only | Closest to a world renderer. 5.8 untested. A good reference for the Hayba spike |
| YaGS, Yandex (https://github.com/yandex/yags) | Apache 2.0 (repo archived) | 5.5-5.7 | Billboard quads via mesh shader (vertex-shader fallback), GPU depth sort, optional depth pass. PLY and SOG import | Colour grading, crop volumes | Windows DX12/Vulkan, recommends RTX 3070. Too heavy for iGPUs |
| StarLightGS (https://github.com/CoSTAR-National-Lab/starlightgs) | MIT | 5.7+ | Splats into the GBuffer (relightable, opaque). Claims 10M+ splats, 5M cap by default | none | Beta, no tagged release. Needs normals |
| XV3DGS, XVERSE (https://github.com/xverse-engine/XV3DGS-UEPlugin) | Apache 2.0 | 5.1-5.5 | Niagara-based hybrid | via Niagara | Too old a version, and Niagara (the art direction avoids it) |
| LCC4Unreal, XGRIDS (https://github.com/xgrids/LCC-3DGS-Unreal-Plugin) | Free and Pro tiers, terms not stated | 5.1-5.8 | GPU-driven indirect draw, streaming LOD. PLY, SPZ, SOG, LCC | Colour correction, clipping | Download via a developer portal, licence unclear: excluded |
| Luma AI, OKO, Volinga, Postshot | Free with an account, or paid | various | Niagara (Luma) or proprietary | none | Excluded (account, paid or abandoned) |

Plugin lists: https://radiancefields.com/3d-gaussian-splatting-engine-support.

- **UE 5.8 ships no Gaussian-splat plugin** [verified: none in `Engine/Plugins`]. UEFN 43.00 reportedly added
  experimental PLY/SPZ splat import [unverified], which hints at future engine support, but not in 5.8.
- **UE 5.8 does ship Epic's `LidarPointCloud` plugin** [verified, `Engine/Plugins/Enterprise/LidarPointCloud`]. It
  imports LAS/LAZ/E57, streams an octree with LOD, and draws sprite points with built-in colour adjustment, so
  saturation 0 gives monochrome. It is a fallback city renderer with no conversion work.
  - Its sprites are opaque points, not Gaussians.
  - Whether material WPO works on its vertex factory is [unverified].

**Verdict:** stay on our splat meshes for everything that needs effects, and use the Hayba spike for density. No
external plugin.

### 2.4 Formats and renderers that reach "7M splats on a phone" (input for the Hayba spike)

| Format | Bytes per splat | Layout [verified unless marked] | Source |
|---|---|---|---|
| 3DGS PLY (INRIA) | 248 (SH3), 56 (SH0) | 62 or 14 float32 | reference |
| **SPZ v2** (what Aholo emits today) | 19 raw, **15.1 measured after gzip** (SH0) | 16-byte header (magic `NGSP`, version, count, SH degree, fractionalBits, flags, reserved), all gzipped [verified, decoded]. Then attribute-grouped arrays: positions 3 x 24-bit fixed point (`fractionalBits` in the header), alpha u8, colour 3 x u8, scale 3 x u8 log-encoded, rotation 3 x s8 (xyz, w derived). SH: 8-bit per coefficient, quantised to 5 bits (degree 1) and 4 bits (higher) | https://github.com/nianticlabs/spz (MIT) |
| SPZ v3 / v4 | 20 raw (SH0) | v4 has a 32-byte header with a stream table of contents. Rotation is smallest-three, 3 x 10 bits + 2-bit index (4 B). v4 compresses each stream separately with ZSTD; v1-3 are gzip and read-only in the current library. Default axes RUB | same |
| PlayCanvas compressed PLY | about 16 + 0.3 chunk header | 256-splat chunks with float min/max. Per splat 4 x u32: position 11/10/11 bits, rotation 2+10+10+10, scale 11/10/11, colour 8888. SH u8 [bit widths from a community exporter, unverified against the PlayCanvas spec] | https://blog.playcanvas.com/compressing-gaussian-splats/ |
| PlayCanvas SOG v2 / v3 | 17 / 13 raw before lossless WebP, plus 2-3 B SH palette index; "15-20x smaller than PLY" | WebP data textures: 16-bit positions split low/high with a symmetric log transform, 256-entry log codebook for scale and DC colour, opacity u8, SH through a shared palette. v3 stores rotation as a 24-bit exponential map in alpha channels | https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/ |
| Spark PackedSplats | **16** (SH0), up to 56 with SH | float16 centre x3, u8 log scale x3, octahedral axis u8 x2 + u8 angle, RGBA8 (sRGB colour, linear opacity) | https://sparkjs.dev/docs/packed-splats/ (Spark is MIT) |

**How they composite** [verified unless marked]:
- **PlayCanvas** sorts all splats of all components in one global back-to-front sort.
  - WebGL2: sorted in a background web worker (async, so it can be briefly stale under fast motion).
  - WebGPU: culled and sorted on the GPU every frame.
  - Data lives in GPU textures and is copied into a per-camera work buffer.
  - Source: https://developer.playcanvas.com/user-manual/gaussian-splatting/rendering-architecture/renderers/
- **Spark** "renders multiple splat objects together with correct sorting" on WebGL2. Its sort is in a Rust/WASM
  worker and the draw is instanced quads pulling from a packed data texture [both details unverified].
- **gsplat (nerfstudio)** is the CUDA reference rasteriser: per-tile radix sort of (tile, depth) keys, then
  front-to-back compositing with early termination in compute. It's a training and offline renderer, not a game
  path.
- **The common recipe** behind high counts on weak GPUs:
  - A compact 16-20 B per splat buffer, read by vertex pulling: one instanced quad per splat, attributes fetched
    from a structured buffer or texture by instance id, so the 4 corners share one fetch.
  - A sort: a CPU worker or a GPU radix/counting sort on 16-bit keys.
  - Premultiplied back-to-front blending.
  - Memory, not shading, becomes the limit, which matches your phone experience.
- **For the spike:** read SPZ v3, and v2 and v4 too.
  - **Our own API world (Dream A) came back as SPZ v3** (smallest-three rotations, 4 B). The public showcase world
    was v2.
  - Aholo also ships a LOD pyramid: `lodMetaPath` is JSON, type `lod-splat`, made with PlayCanvas splat-transform,
    with 5 levels as separate SPZ chunk files (100%, 50%, 25%, 5%, 1%). Saved at
    `P:/FoA-Assets/level2/aholo/dream_a/lod_meta.json`.
  - `Tools/Splats/ply_to_splatmesh.py` now decodes v2 and v3. Its `parse_spz` and `spz_quat` are a reference
    decoder, checked against nianticlabs/spz. Keep our dithered, sort-free composite as an option: no sort
  pass at all, and TSR resolves it. That fits the monochrome sand look better than soft blending, and it costs
  nothing on iGPUs.

---

## 3. City source

A helper agent of this lane checked each URL below with HEAD or a 1-4 KB range request. It read point counts and
densities from those LAS headers. Status codes are the ones it got.

**No city-scale 3DGS scan under CC0 or CC-BY was found.** Lidar converted to splats is the path.

**Licence note:** the Toronto sources use Canadian open-government licences (OGL-Toronto, OGL-Canada,
OGL-Ontario). These are attribution-only and allow commercial use, which is CC-BY in effect, **but they are not
literally CC-BY.** You set "CC0 or CC-BY only", so this needs your yes. AHN4 (raw) is the strict-CC0 fallback.

### 3.1 Toronto: yes, it's available

**City of Toronto Open Data publishes no lidar.** It publishes **3D Massing**: https://open.toronto.ca/dataset/3d-massing/

- Licence: OGL-Toronto (https://open.toronto.ca/open-data-licence/), commercial use allowed. Attribution: "Contains
  information licensed under the Open Government Licence – Toronto".
- Content: untextured building solids, no trees.
- Downtown SketchUp tile `50G_SOUTH3` (about 1.0 x 1.4 km, CN Tower to Union Station), 36 MB, status 200:
  https://opendata.toronto.ca/city.planning/3d-massing/2025/SketchUp/50G_SOUTH3.skp. The DWG is 62 MB. The
  citywide multipatch is 145 MB.

**Toronto lidar: TRCA GTA 2023 on NRCan's CanElevation bucket.** Anonymous S3, COPC (LAZ 1.4).

- Licence: OGL-Canada (https://open.canada.ca/en/open-government-licence-canada), commercial use allowed.
  Attribution: "Contains information licensed under the Open Government Licence – Canada". Ontario's catalogue
  lists the same capture under OGL-Ontario, so credit both.
- **24.5 pts/m², intensity and classification, no RGB.** That suits a monochrome city.
- Downtown tile (King/Bay up to Nathan Phillips Square), 24.5M points, 142 MB, status 206:
  https://canelevation-lidar-point-clouds.s3.ca-central-1.amazonaws.com/pointclouds_nuagespoints/TRCA/GTA_2023/ON_TRCA2023_20230511_NAD83CSRS_UTMZ17_1km_E6300_N48340_CLASS.copc.laz
  - I re-checked this exact URL with a 1 KB range request: status 206.
- The CN Tower is in tile `E6300_N48330` (132 MB).
- **A 500 x 500 m crop is about 6M points.** COPC can be cropped over HTTP with PDAL or QGIS.
- Filter low noise below -60 m by classification.
- An older capture, GTA2015 (11 pts/m²), is in the same bucket.

### 3.2 Other candidates

| Source | Licence | What it is | Size | URL (status) |
|---|---|---|---|---|
| AHN4 via GeoTiles, Amsterdam | **Raw AHN4: CC0.** The coloured GeoTiles version is CC BY 4.0, because its colour comes from Beeldmateriaal aerial photos | Aerial lidar, 35-40 pts/m², RGB + NIR in the coloured version | Coloured tile 480-540 MB (1 x 1.25 km); 500 m crop about 9M points. Raw sheets are 9.5 GB | https://geotiles.citg.tudelft.nl/AHN4_T/25GN1_02.LAZ (206) |
| swissSURFACE3D, Zurich | swisstopo free geodata, commercial use allowed. Credit "© swisstopo". Not CC by name | Lidar, 25.5 pts/m², COPC, no RGB | 155 MB per km² | https://data.geo.admin.ch/ch.swisstopo.swisssurface3d/swisssurface3d_2024_2683-1247/swisssurface3d_2024_2683-1247_2056_5728.copc.laz (200) |
| Helsinki 2017 reality mesh | CC BY 4.0, credit "City of Helsinki" | Textured photogrammetry OBJ **with facades** | 2 km tiles, 1-3.5 GB zipped | https://3d.hel.ninja/data/mesh/Helsinki3D-MESH_2017_OBJ_2km-250m_ZIP/Helsinki3D_2017_OBJ_672496x2.zip (200, 1.94 GB) |
| USGS 3DEP, NYC / San Francisco | US public domain [policy page not opened] | EPT. NYC about 10-15 pts/m², RGB in the schema [whether it's filled is unverified]. SF has no RGB | huge; crop with PDAL | https://s3-us-west-2.amazonaws.com/usgs-lidar-public/NY_NewYorkCity/ept.json (200) |

**Excluded** (not commercially usable):
- Toronto-3D: CC BY-NC 4.0.
- KITTI-360: CC BY-NC-SA 3.0.
- MatrixCity: CC BY-NC 4.0 data.
- UrbanScene3D: non-commercial.
- Mill-19: no data licence.
- Prague REALMAP: CC BY-NC-SA [unverified].
- GauU-Scene: licence unknown.

### 3.3 Pick

**Toronto GTA 2023 lidar plus the 3D Massing tile**, pending your licence approval.

- **The look:** aerial lidar is dense on roofs and ground and sparse on facades, which is exactly what a top-down
  camera sees. Intensity gives a natural grey city with no colour work.
- **Per-building identity:** the massing footprints tell us which building each point belongs to.
  - Building points become one splat cell per building, so a building can dissolve and re-form on its own (Custom
    Primitive Data `Phase`).
  - Ground and trees, taken from the lidar classification, go into the 50 m static cells.
  - Massing surfaces can be sampled (`glb_to_sandsplats.py` style) to firm up the facades where lidar is thin.
- **Chosen corridor (2026-11-10):** Queen Street West, from Spadina Avenue 600 m east toward University Avenue,
  with 300 m (about 3 blocks) either side. That's a rotated 600 x 600 m area of 0.36 km².
  - The axis-aligned bounding box in UTM 17N (EPSG:2958) is E 629234-629986, N 4833829-4834582.
  - The buildings are mostly 2-4 storey heritage strip, plus some mid-rise. **I picked it over the King/Bay
    financial district because a top-down camera can't sit above 300 m towers.**
  - **Lidar tiles:**
    - `E6290_N48330`: 143 MB, 24.9M points.
    - `E6290_N48340`: 154 MB, 26.0M points.
    - Both are point format 6 (no RGB), status 206, with header extents E 629000-630000.
    - 297 MB for the whole pair. A COPC crop of the bounding box is about 14.5M points, roughly 85 MB to transfer
      [estimate].
  - **Footprints:** the 2025 citywide Shapefile (footprints with heights), 81.4 MB, status 200. One file is
    simpler than the four SketchUp tiles (`50H_SOUTH1`, `50H_SOUTH2`, `50G_NORTH1`, `50G_NORTH2`), because the
    City's tile grid splits along Queen St. I queried the grid from its ArcGIS layer `3D_Massing_Context_Tile`.
- **Density, and what fits** [estimate]:
  - **The whole 0.36 km² at screen density (about 11 per m²) is about 4M splats**, about 5x the 800k mesh budget.
  - **Plan instead:** make splats only of buildings and trees (lidar classes 6 and 3-5), at about 5-6 per m². At an
    assumed 45% cover, that is **about 0.9M splats**. Then trim to 800k by thinning the outer blocks.
  - **Streets and sidewalks** (class 2) become one baked intensity texture: 0.36 km² at 20 cm per texel is about
    3000² BC1, about 4.5 MB.
  - If the Hayba packed-buffer plugin lands, the whole area can be splats.
- **Strict-licence fallback:** raw AHN4 Amsterdam (CC0, intensity only).
- **The tools are new:** PDAL (crop and thin) or `laspy` + `lazrs` in Python. A 30-line crop/thin script feeds the
  existing converter.

---

## 4. Integrated GPUs (Intel UHD / Iris Xe, AMD Vega / 680M) at 1080p

### 4.1 What UE 5.8 itself needs on an iGPU [verified]

Our `DefaultEngine.ini` today has Lumen GI and reflections (`r.DynamicGlobalIlluminationMethod=1`,
`r.ReflectionMethod=1`), `r.Shadow.Virtual.Enable=1`, and mesh distance fields. **All four are wrong for
integrated GPUs.** From the installed `Engine/Config/BaseScalability.ini` (5.8):

| Setting | Detail |
|---|---|
| **GI Low (`@0`) is the only level that turns Lumen GI off** | `r.Lumen.DiffuseIndirect.Allow=0`, `r.DistanceFieldAO=0`. GI Medium (`@1`) still runs Lumen, with an irradiance-volume final gather |
| **Reflections Low and Medium turn Lumen reflections off** | `r.Lumen.Reflections.Allow=0`, SSR quality 0 or 2 |
| **No shadow level turns Virtual Shadow Maps off** | `r.Shadow.Virtual.Enable` appears nowhere in BaseScalability. Add `r.Shadow.Virtual.Enable=0` to `[ShadowQuality@0]` and `@1` in our `DefaultScalability.ini` |
| **AA Low** | TSR history at 100%, R11G11B10 history, rejection AA off. Auto-detected Low resolution quality is 50% (`PerfIndexValues_ResolutionQuality="50 71 87 100 100"`) |

Epic docs:
- Nanite and Virtual Shadow Maps need "DirectX 12 with Shader Model 6.6 atomics". Software Lumen needs DX12 SM6 and
  names a GTX 1070 or better. Source:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine
- Lumen's own docs say it targets "current-generation consoles and high-end PCs" and suggest distance-field AO for
  legacy PCs. Source:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-technical-details-in-unreal-engine
- TSR runs on any SM5 GPU. Epic's sample costs are about 0.79 ms at 100% screen percentage and 0.43 ms at 50% (the
  platform isn't named), and the Epic AA level costs more. Source:
  https://dev.epicgames.com/documentation/en-us/unreal-engine/temporal-super-resolution-in-unreal-engine

**The iGPU profile** (config only, no C++):
- `[GlobalIlluminationQuality@0]`: Lumen off, as shipped.
- `[ReflectionQuality@0]`: as shipped.
- `[ShadowQuality@0/1]`: add `r.Shadow.Virtual.Enable=0`. One CSM cascade, or no dynamic shadows in the city: the
  splats are unlit anyway.
- `[AntiAliasingQuality@0]`: TSR, as shipped.
- `[ResolutionQuality]`: 67 for 720p to 1080p.
- `r.GenerateMeshDistanceFields`: keep it only if a level needs DFAO.
- **Pick the level at first launch from Blueprint:** `GameUserSettings` has Run Hardware Benchmark, Apply Hardware
  Benchmark Results and Set Overall Scalability Level, all BlueprintCallable [verified, `GameUserSettings.h`, 5.8].
- **The project still cooks `PCD3D_SM5` for D3D11** [verified, DefaultEngine.ini]. That leaves a `-dx11` fallback for
  iGPUs without SM6.6. On that path, Nanite meshes render their fallback mesh and VSM and Lumen are off
  [behaviour on 5.8 unverified]. Our splat meshes don't use Nanite.
- **Post-processing:** run the time-shift echo and the mono pass at half resolution on Low. They are bandwidth
  passes, and bandwidth is the scarce resource on an iGPU.

### 4.2 The hardware

| iGPU | FP32 peak | Memory bandwidth (shared with the CPU) |
|---|---|---|
| Intel UHD 620 (24 EU) | about 0.4 TFLOPS | DDR4-2400 dual channel 38 GB/s; **many laptops are single channel: 19 GB/s** |
| Intel Iris Xe 96 EU | about 1.7-2.2 TFLOPS | LPDDR4x-4266 68 GB/s, DDR4-3200 51 GB/s |
| AMD Vega 8 | about 1.1-1.8 TFLOPS | DDR4 like Iris Xe |
| AMD Radeon 680M (12 CU RDNA2) | about 3.4-3.7 TFLOPS | LPDDR5-6400 about 100 GB/s |
| Reference: GTX 1650 | about 3 TFLOPS | 128 GB/s dedicated |

- FP32 peaks are from https://nanoreview.net/ru/gpu-compare/radeon-680m-vs-intel-iris-xe-graphics-g7-96eu and
  https://www.notebookcheck.net/Radeon-680M-vs-Iris-Xe-G7-96EUs_11124_10364.247598.0.html.
- Bandwidth is arithmetic: channels x 64 bit x transfer rate.
- **Bandwidth is what separates iGPUs from the GTX 1650 class far more than compute.** It is the resource splats
  burn: vertex fetch, overdraw, GBuffer writes.

### 4.3 Splat budgets at 1080p (TSR Low from 720p internal) [estimate]

**Model:**
- **Frame time given to splats:** 5 ms of 16.7 at 60 fps, 12 ms of 33 at 30 fps. The rest goes to the scene, TSR
  (about 2-3 ms on an iGPU, scaled from Epic's 0.4-0.8 ms), post-processing and UI.
- **Cost on Iris Xe**, for the lean WPO billboard (about 150 vertex-shader instructions), dithered and masked, about
  10 px average footprint at 720p, 3 vertex passes:
  - Vertex fetch about 0.4-1.1 ms.
  - Raster and pixel work about 0.3-0.5 ms.
  - **Total about 0.8-1.5 ms per 100k visible splats.**
- **View-fixed opaque quads** (the city at rest, no WPO) drop the velocity pass and the masked clip, and fetch
  about half as much, so **about 2-3x more splats** fit in the same time.
- **Other GPUs are scaled by bandwidth and compute:** UHD 620 at about 0.3x of Iris Xe, Vega 8 at about 0.7x,
  680M at about 1.6x.

| GPU | WPO billboards, 60 fps | WPO billboards, 30 fps | Static view-fixed quads, 60 fps |
|---|---|---|---|
| UHD 620/630 (dual channel) | 80-150k | 200-400k | 200-400k |
| Iris Xe 96 EU / Vega 8 | 250-600k (Vega: about 0.7x) | 0.8-1.5M | 0.7-1.5M |
| Radeon 680M | 500-900k | 1.2-2M | 1.2-2.5M |

These are **arithmetic, not measurements**. Treat the low end of each range as the plan, and measure (Recommendation,
build step 3). Single-channel RAM laptops can halve every number.

**What the fixed top-down camera changes**

- **Screen density caps the need.** At 720p internal (0.92 Mpx), splats with about 2x overlap fully cover the screen
  at:
  - about 260k splats of 3 px,
  - about 95k of 5 px,
  - about 37k of 8 px.
  
  A 6 px "sand grain" city therefore needs only **about 60-120k visible splats**, inside every row of the table
  above.
- **The camera height sets the density.** At about 8 cm per pixel, the view is about 100 x 58 m and the car about
  56 px. A 6 px splat is about 48 cm, so about 11 splats per m² of projected surface.
  - That is roughly native aerial-lidar density (section 3), so the lidar needs thinning, not upsampling.
- **Visible-cell streaming:** a 50 m cell grid means about 3 x 2 to 4 x 3 cells on screen. Load a ring of cells
  around the car (level streaming or simple distance culling). Draw calls stay in the tens.
- **SH 0 and view-independent colour:** nothing per-view to compute. Lidar intensity or RGB goes straight into the
  vertex colour.
- **Opaque view-fixed quads:**
  - The camera doesn't rotate, so quads are pre-oriented in the converter.
  - The material is opaque or binary-masked with no dither, so early-Z works.
  - WPO is off at rest, so there's no velocity pass for static cells.
  - A slight camera roll or pitch change is invisible on blob-shaped splats.

**The dream world on an iGPU:**
- The camera rotates freely in first person, so the dream keeps WPO billboards. Plan **at most 150k on Iris Xe**
  after dropping the sky shell and decimating, and **about 80k on UHD**, using a second, sparser mesh chosen by
  Blueprint on the Low scalability level.
- **During the fall, clamp each splat's screen-space radius in the WPO and fade splats within about 1 m of the
  camera.** Near-camera splats becoming screen-sized quads is the main overdraw spike.

### 4.4 Fallback: bake the static city, keep live splats only for events

If the city exceeds the disk budget or the UHD-class GPU time:

- **Bake:** rasterise the same point cloud top-down offline in Python (numpy, no editor), to albedo plus a height
  map per 50 m cell. Build a 2.5D grid mesh per cell from the height map, with that albedo.
  - Size [estimate]: 1024² BC1 is 0.67 MB per cell with mips, about **32 MB for a 0.12 km² corridor**.
  - Runtime cost is ordinary opaque geometry, about 0.5 ms total even on UHD.
- **Live splats** only for:
  - the buildings that dissolve and re-form (about 10 x 20-40k splats, pooled),
  - meteor impact zones (a pooled 30k-splat crater cell),
  - hero sand.
- **The swap:** when a building starts to dissolve, an MPC circle masks its footprint out of the baked tile (opacity
  mask on the tile material) and its live splat cell turns on.
- **Downsides:**
  - Facades have no data from a straight-down bake. Keep a narrow FOV (about 30-40 degrees) so walls stay
    foreshortened, which a top-down RPG camera does anyway.
  - The baked parts don't shimmer like sand. Add a cheap material grain on the tile so the cut between the two isn't
    obvious.

**City recommendation:** live static splat cells, with WPO only near events. Thin the corridor to at most 800k
splats (lean layout, about 50-110 MB on disk). Use the baked backdrop beyond the drivable corridor, which also covers
the "far city" cheaply. If the Hayba packed-buffer plugin lands, the corridor can go to 3-5M splats for the same
disk cost.

---

## 5. Effects on splat meshes (WPO and colour driven by MPC parameters)

All closed-form and stateless, in the style of `flow_lib.hlsl`. They go in `M_SplatWorld`, not the 4,422-instruction
`M_SplatMesh`. Instruction counts are [estimate].

**1. Shockwave (vertex)**

- **Inputs:** up to 4 impacts in `MPC_Level2`, each `ImpactN = (x, y, t0, strength)`.
- **Per splat:**
  - `d = distance(splat.xy, impact.xy)`, `R = speed * (t - t0)`.
  - `ring = exp(-((d - R) / width)^2) * saturate(1 - (t - t0) / life)`.
  - `offset = ring * strength * (normalize(splat.xy - impact.xy) * kOut + up * kUp) + ring * jitter(seed)`.
  - Add a radius pulse `radius *= 1 + 0.5 * ring` so the wavefront reads as loosened sand.
- **Cost:** about 15-20 instructions per impact, about 70 for 4. On Iris Xe that is about 0.1 ms per 100k splats,
  negligible next to vertex fetch.
- **Blueprint side:** sets the MPC vector on impact. It turns on `SetEvaluateWorldPositionOffset` for cells within
  `speed * life`, and off again after `life`.
- **Bracing:** the gameplay check reuses the same `d` and `R` in Blueprint, so the visible ring and the hit test
  agree.

**2. Dissolve into black sand, then re-form (vertex, plus colour in the vertex shader)**

- **Inputs:** `Phase` from 0 to 1 per building, as Custom Primitive Data. `SetCustomPrimitiveDataFloat` is
  BlueprintCallable [verified, `PrimitiveComponent.h`, 5.8], needs no dynamic material instance, and keeps batching.
- **Per splat:**
  - `q = saturate((Phase - seed * spread) / (1 - spread))`, `e = smoothstep(0, 1, q)`.
  - `offset = e * (fall_to_ground(seed) + swirl(seed, t))`. The fall goes down to z = 0 plus a lateral spread, so the
    building slumps into a pile.
  - `rgb = lerp(rgb, sandBlack(0.015), saturate(3 * q))`, which goes pitch black early, per the art direction.
  - `radius *= lerp(1, 0.6, e)`: grains shrink.
- **Re-forming** is the same function with Phase running back to 0. Ease the first 20% for the "pulled back" feel.
- **Cost:** about 30-40 instructions. The colour is computed per vertex and passed as an interpolant, so pixel cost
  doesn't change.
- **Grain and sheen:** the existing grain and fresnel sheen of the black sand stays a pixel term. On the iGPU
  profile, apply it only to cells in the live state.

**3. Mono to colour crossfade (vertex, plus the existing post-process)**

- **Inputs:** `MPC_Dream.ColorReveal` (it already exists) and a reveal origin.
- **Per splat:** `k = saturate((ColorReveal * Rmax - distance(splat, origin) + seed * jitter) / soft)`, then
  `rgb = lerp(lum(rgb) * Tint, rgb, k)`. That gives a wave of colour sweeping through the sand.
- **Cost:** about 10 instructions per vertex.
- **The global mono post-process** (`M_PP_DreamMono`) keeps colour only where stencil >= 1. Don't render the whole
  dream world into custom depth for that: it adds one more WPO vertex pass. Instead, set the dream level's
  post-process volume to colour-keep, and let the splat material do the mono to colour transition.

**Total** [estimate]: the effect block is about 120 instructions per vertex with every effect live, against 4,422
for the hero flow material. That's under 0.2 ms per 100k splats on Iris Xe. **Vertex fetch and overdraw remain the
real cost, not the effects.**

---

## 6. Unverified items (one list)

- How SpatialGen API calls are billed: free trials or credits, and which plan our account is on (commercial use is
  listed under Pro). **The API exposes none of this** (section 7). Check the account page on aholo.ai.
- SpatialGen units for outdoor scenes. The showcase was not metric; Dream A, indoor, looks metric.
- Every iGPU timing in section 4.3 (arithmetic only).
- Cooked (pak) size per splat in our mesh format. Only the editor .uasset (50-85 B) was measured.
- UE 5.8 behaviour of Nanite meshes on GPUs without SM6.6 and on the `-dx11` path.
- WPO support on the LidarPointCloud vertex factory.
- Spark's sort and draw internals, and the PlayCanvas compressed-PLY bit widths.
- UEFN's experimental splat import (reported, not checked).
- Licence and terms for LCC4Unreal's free tier.

## 7. Dream A, generated 2026-11-10 [verified, measured]

**The call:** one text-only `POST /global/world/v1/generations` with the section 1.4 prompt, made by
`Tools/Lux3D/aholo_world.py`.
- worldId `3FO4K4V8OF4C`. Created 16:43:12, `RUNNING` from 16:43:26, `SUCCEEDED` at 16:53:18: **about 10 minutes**.
- The service labelled it `scene: indoor`.

**Files** (all in `P:/FoA-Assets/level2/aholo/dream_a/`, outside the repo):

| File | What it is |
|---|---|
| `world.spz` | 4.1 MB, **SPZ v3**, 248,427 splats, SH degree 0, 16.7 B per splat |
| `pano.jpg` | 4096 x 2048 equirectangular panorama |
| `lod_meta.json` | the 5-level LOD pyramid metadata |
| `world.json` | raw API bodies: list before and after, the create response, and the final detail |
| `review_SM_DreamA.png` | review render: 4 headings from the capture point plus an outside overview, made with `Tools/Splats/splat_preview.py` from the converted glTF |
| `review_pano_small.jpg` | the panorama, downsized |

Not downloaded: `plyPath` (a full 3DGS PLY, 16.9 MB, the same splats with normals) and the LOD chunk SPZs.

**Charge evidence:**
- Before the call, `/world/v1/list` had 0 worlds. After, it has 1.
- Neither the list nor the detail response has any credit, plan, trial or commercial-use field, and no account
  endpoint is published (checked against the aggregate OpenAPI spec).
- The Lux3D task list is unchanged, with latest task 5400001, so SpatialGen jobs don't appear there.
- **Whether this used a free trial or 30 credits can only be read from the aholo.ai account page** [unverified].

**What came back:**
- **No sky shell.** All splats lie within 5.5 units, unlike the outdoor showcase: indoor worlds are a closed room.
- **The scale looks metric** [estimate]. The room is 7.9 x 10.3 m with 4.7 m to the vaulted ceiling. The
  panorama's capture point sits 1.53 m above the floor, about eye height, so import at x100 (cm) as is.
- **Panorama:**
  - A crimson sand-dune floor and a wavy crimson ceiling, with cream and amber arches.
  - A wooden double door at the end of the central hallway: **closed, and set in a wall**, not freestanding and
    open as prompted.
  - The model added a bed alcove, two sofas, a desk and sculpted props. That ties nicely back to the bedroom.
  - **No teal** appears, though the prompt asked for it.
- **Splats:** the four headings match the panorama's layout in the same turning order (window arcade, sofa, bed,
  door), so the axis mapping isn't mirrored.
  - At 150k splats (60% of the source), surfaces read clearly, the dunes keep their relief, and walls look grainy and
    sandy, which suits the brief.
  - **Defect:** dark speckle on the cream walls and the sofa. Part of it is the preview's order-independent blending,
    which has no occlusion. Part is probably real dark floaters. Re-check in UE with the dither and TSR; if it stays,
    filter by colour and opacity in the converter.

**Converted mesh:**
- `P:/FoA-Assets/splatmesh/SM_DreamA.gltf` / `.bin` / `.splatmesh.json`: 150,000 of 248,427 splats, **lean layout**
  (POSITION, TEXCOORD_0/1, COLOR_0), 28.6 MB glTF, median radius 4.6 cm, `radius_scale_hint` 1.04.
- **Import it with the lean world material, not `M_SplatMesh`.** The current master's SH node reads TEXCOORD_2..6,
  which a lean mesh doesn't have [what UE binds for the missing channels is unverified].
- A Low variant for UHD-class GPUs is one more command: `--count 80000`. Alternatively, use Aholo's 25% LOD chunk.

**Design consequences:**
- The world is a room, not an open dreamscape. The first-person fall should go **through the dune floor**: dissolve
  a disc of floor splats under the player.
- The real door in the room is the natural exit. That suits the "walk through the bedroom door" entry if Dream A's
  door is used as the arrival point.

## Sources

- Aholo World OpenAPI: https://labs.aholo.ai/api-docs/specifications/services/world/openapi.en.yaml
- Aholo API index: https://labs.aholo.ai/api-docs/en/llms.txt
- Aholo quick start: https://labs.aholo.ai/api-docs/en/quickstart
- Aholo pricing: https://www.aholo.ai/pricing
- Aholo help, imagined worlds: https://aholo.featurebase.app/help/articles/8004872-create-imagined-3d-worlds-with-ai
- SpatialGen sample: https://spatialgen.aholo.ai/detail/3FO4K4VY2B7V
- Aholo SDK: https://github.com/manycoretech/aholo-spatial-sdk
- ComfyUI world node: https://comfy.icu/node/aholo-world_wait
- UE docs:
  - https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine
  - https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-technical-details-in-unreal-engine
  - https://dev.epicgames.com/documentation/en-us/unreal-engine/temporal-super-resolution-in-unreal-engine
  - https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine
- Local engine files: `C:/Program Files/Epic Games/UE_5.8/Engine/Config/BaseScalability.ini`,
  `.../Engine/Source/Runtime/Engine/Classes/Components/StaticMeshComponent.h`,
  `.../Engine/Plugins/Enterprise/LidarPointCloud/`
- Splat formats:
  - https://github.com/nianticlabs/spz
  - https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/
  - https://developer.playcanvas.com/user-manual/gaussian-splatting/formats/sog/
  - https://developer.playcanvas.com/user-manual/gaussian-splatting/rendering-architecture/renderers/
  - https://blog.playcanvas.com/compressing-gaussian-splats/
  - https://sparkjs.dev/docs/packed-splats/
  - https://github.com/sparkjsdev/spark
- UE plugins:
  - https://radiancefields.com/3d-gaussian-splatting-engine-support
  - https://github.com/TimChen1383/NanoGaussianSplatting
  - https://github.com/yandex/yags
  - https://github.com/CoSTAR-National-Lab/starlightgs
  - https://github.com/xverse-engine/XV3DGS-UEPlugin
  - https://github.com/xgrids/LCC-3DGS-Unreal-Plugin
- iGPU specs:
  - https://www.notebookcheck.net/Radeon-680M-vs-Iris-Xe-G7-96EUs_11124_10364.247598.0.html
  - https://nanoreview.net/ru/gpu-compare/radeon-680m-vs-intel-iris-xe-graphics-g7-96eu
  - https://nanoreview.net/ru/gpu-compare/intel-uhd-graphics-620-vs-intel-iris-xe-graphics-g7-96eu
