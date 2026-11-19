# Level 2 runtime splat renderer: feasibility spike

Hayba lane, 2026-11-10. Read with `splat_budget_ours.md` (world lane) and `splat_feasibility.md` (research lane, not
written yet when this was). Numbers are marked **exact** (fixed by the data layout), **measured**, or **estimated**.

## Verdict

**GO on memory** (exact). **GPU: pending the bench** (`Tools/test_splat_bench.py` on the scratch host; it needs a
quiet machine with 5 GB of RAM free). This section is updated with the measured numbers when the bench has run.

## What was built

A UE 5.8 runtime code plugin, `HaybaSplats` (hayba repo, branch `feat/splat-runtime-spike`, folder
`unreal/HaybaSplats`). One Runtime module, no editor dependency, loaded at PostConfigInit so its shader folder is
mapped before shaders compile. Nothing is installed in FoA.

- **Data:** one 16-byte record per splat (one `uint4` in a single structured buffer):
  - position: 3 x unorm16 relative to its chunk's bounds (0.5 mm steps over a 32 m chunk);
  - scale: 3 x 8-bit log-quantised, over a per-set range;
  - rotation: quaternion x, y, z as snorm8, w reconstructed positive;
  - colour: RGBA8, spherical harmonics degree 0 (view-independent colour), alpha = opacity.
  Chunks are contiguous runs of up to 65,536 splats with double-precision bounds on the CPU (LWC is resolved per
  view). Splats are shuffled within a chunk, so drawing every k-th one is an unbiased subsample.
- **Draw:** vertex pulling. One instanced draw per visible chunk, a 4-vertex triangle strip per instance, no vertex
  or index buffer. The vertex shader decodes the record, applies the effects, projects the 3D Gaussian to a 2D
  ellipse (EWA: view-space covariance and the screen Jacobian, as in 3DGS) and places the quad on its eigen-axes.
- **Composite:** sort-free stochastic coverage. The pixel shader evaluates the Gaussian and keeps the pixel with
  probability alpha (`clip` against interleaved gradient noise that changes each frame); TSR averages it, the same
  trick as today's masked-dither `M_SplatMesh`. Opaque, depth-tested and depth-writing. No sorting, no translucency.
- **Deferred integration:** a `FSceneViewExtension` draws after the base pass
  (`PostRenderBasePassDeferred_RenderThread`) into SceneColor (colour times pre-exposure) and GBufferB = 0
  (shading model unlit), with the scene depth. Deferred lighting skips unlit pixels, and the whole post-process
  chain (monochrome, ink, colour reveal, TSR) runs on top as it does for any unlit material.
- **Culling and LOD:** CPU frustum test per chunk. LOD by subsampling: per chunk, a stride chosen from its screen
  footprint so the drawn count is about (pixels / `r.HaybaSplats.PixelsPerSplat`). The survivors' radius grows by
  sqrt(stride), so coverage holds. Under the top-down camera this keeps the drawn count near-constant as the view
  zooms out.
- **Effects in the vertex shader:** `DissolveAmount` (per-splat hash order: a splat turns black, then shrinks to
  nothing) and up to 4 radial shockwaves (epicentre, start time, speed, ring width, amplitude, decay: a ring that
  pushes splats outward and up). Console: `hayba.splat.dissolve`, `hayba.splat.shock`.

## Numbers

| | 1 M | 3 M | 7 M |
|---|---|---|---|
| GPU memory, this plugin (exact) | 16 MB | 48 MB | 112 MB |
| GPU memory, today's quad meshes (world lane, estimated) | 250 MB | 750 MB | 1.75 GB |
| GPU memory, world lane's slim layout (estimated) | 100 MB | 300 MB | 700 MB |
| Upload, one-time (estimated) | 2-4 ms | 6-10 ms | 15-25 ms |
| CPU cull + LOD per view (estimated) | < 0.01 ms | < 0.01 ms | 0.01-0.02 ms |
| GPU ms, every splat drawn (measured) | pending | pending | pending |
| GPU ms, LOD at 2 px per splat (measured) | pending | pending | pending |

- Streaming per 65k-splat chunk is 1 MB, about 0.1-0.2 ms each (estimated), which suits World Partition cells.
- On disk (estimated): raw 16 B per splat; an SPZ-style column split with delta-coded positions should reach about
  8-10 B per splat, so 7 M is about 60-70 MB.

## Integration choices (UE 5.8)

1. **Scene view extension (what the spike uses).** Fastest to build, fully runtime, one global pass.
   - Gives: post-process, depth (so splats occlude and are occluded by meshes), TSR via depth reprojection.
   - Doesn't give: shadows cast by splats, custom depth/stencil (FoA's `PP_DreamMono` colour-keep uses stencil 1),
     velocity for moving splats (shockwave displacement ghosts slightly under TSR), per-actor visibility or
     transforms. Those need either extra passes here or option 2.
   - Writes the legacy GBuffer. A Substrate project needs a different write; FoA has Substrate off, and the plugin
     refuses to draw if it's on.
2. **Custom primitive + vertex factory (recommended for production).** A `USplatComponent` with a scene proxy and a
   custom vertex factory that pulls from the same packed buffer, drawn through the normal mesh passes with a regular
   Masked material (dither in the material, like `M_SplatMesh`).
   - Gives everything above for free: custom depth/stencil (`PP_DreamMono` stencil 1), velocity, optional shadows,
     per-component transforms, visibility, culling bounds, World Partition streaming as normal actors, and the
     dissolve/shockwave authored in the material graph (MPC epicentres, as the world lane planned).
   - Cost: a vertex factory in a plugin (about 1-2 days to build and gate) and a material usage flag to piggyback
     on. The packed buffer, LOD and culling from the spike carry over unchanged.
3. **Sorted path for a small hero set:** a GPU radix sort of view depth over the visible hero splats, then real
   alpha blending in a translucent pass. Not built: worth it only for one dream hero asset, with budget about
   150-300k splats (world lane's figure).

## Packaging in FoA

FoA is Blueprint-only but already loads a code plugin (`HaybaMCPToolkit`, editor-only). HaybaSplats is a Runtime
module, so it must ship in the packaged game:
- Build it once with `RunUAT BuildPlugin` for Win64 (Editor, and Game Development + Shipping), and drop the built
  plugin into `P:/FoA/Plugins/HaybaSplats` (or `Engine/Plugins/Marketplace`). A Blueprint-only project then packages
  with the precompiled binaries, the same way Marketplace code plugins work. No C++ in FoA itself.
- Data path: a `.splatpack` (packed records + chunk table) baked offline from PLY by the existing converters, loaded
  as an asset or a raw file per cell.

## What's next if the bench is green

1. Production shape: component + vertex factory (option 2), and a `.splatpack` baker in `Tools/Splats`.
2. Custom stencil for the colour-keep path (free with option 2).
3. Velocity output for shockwave frames (free with option 2).
4. GPU culling and compaction if the chunk count gets into the thousands (CPU culling is fine up to that).
