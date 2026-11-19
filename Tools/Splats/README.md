# Splat mesh: 3DGS PLY to billboard glTF (UE 5.8)

`ply_to_splatmesh.py` turns a Lux3D Gaussian Splat PLY into one static mesh: one camera-facing quad per splat, drawn with a plain masked material. That means one draw call, no Niagara and no plugins.

```
python ply_to_splatmesh.py IN.ply OUT.gltf [--count 40000] [--seed 1]   # writes OUT.gltf, OUT.bin, OUT.splatmesh.json
python ply_to_splatmesh.py IN.spz OUT.gltf --count 150000 --lean [--max-radius 20]   # Aholo World SPZ v2/v3 (Z-up)
python ply_to_splatmesh.py --selftest
python splat_preview.py OUT.gltf review.png   # offline review render (numpy + PIL), no editor
```

The extra flags:
- `--lean` keeps only POSITION, TEXCOORD_0/1 and COLOR_0. The material must not read the SH channels.
- `--max-radius` drops the far panorama shell that outdoor Aholo worlds bake as splats.
- The Aholo World download comes from `Tools/Lux3D/aholo_world.py`.
- Level 2 notes: `docs/design/level2/splat_feasibility.md`.

The full rationale is in the script docstring. The key facts:

- **Axes:** Lux3D PLYs use the 3DGS/OpenCV frame (+Y down, +Z forward), so the output is glTF `(x, -y, -z)`. This was proven against the matching i23d PLY+GLB pair.
- **Placement:** the base sits at y = 0 and the object is centered in x/z.
- **Units:** units are kept as-is (meters). The i23d character is only 0.3 m tall, so scale the actor.

## Channel map

glTF space, as it ends up in UE. The importer maps glTF `(x, y, z)` to UE local `(x, z, y) * 100`.

| Attribute | Contents |
|---|---|
| POSITION | splat center (m). The 4 corners sit ±0.1 mm apart in the quad plane so UE never deletes them as degenerate. Ignore this offset. |
| NORMAL / TANGENT | anisotropy frame: local axis 2 / local axis 0 (w = +1). Axis 1 = cross(N, T). Unused by the recipe. |
| TEXCOORD_0 | corner (±1, ±1) |
| TEXCOORD_1 | (radius_cm = 2 × geometric-mean sigma, seed in [0,1)) |
| TEXCOORD_2..6 | SH degree 1 as glTF-space vectors: UV2 = (R.x, R.y), UV3 = (R.z, G.x), UV4 = (G.y, G.z), UV5 = (B.x, B.y), UV6 = (B.z, sigma0_cm) |
| TEXCOORD_7 | (sigma1_cm, sigma2_cm) |
| COLOR_0 | rgb = 3DGS DC color in display (sRGB) space, a = opacity. VertexColor returns these values unchanged. |

All current Lux3D PLYs have no `f_rest`, so the SH channels are zero. Keep the SH node anyway; it costs only a few ALU operations.

## Import (Interchange glTF, UE 5.8 defaults checked in engine source)

- **Build Nanite: OFF** (the default is on). Use the classic path for WPO + masked on low-end hardware.
- **Generate Lightmap UVs: OFF** (the default is off). With all 8 UV channels used, it would overwrite UV1.
- **Recompute Normals/Tangents: OFF** only if you want the anisotropy frame. Otherwise it is harmless.
- **Use Full Precision UVs:** optional. FP16 is enough for these channels.
- **Bounds:** on the static mesh, set Positive/Negative Bounds Extension to at least `radius_cm.max × RadiusScale` from the sidecar, plus any drift distance. The quads grow outside the mesh bounds, so without this they pop at the screen edges.
- **Component:** turn Cast Shadow off for the cheap path.

## Material recipe

- **Material settings:** Unlit, Masked, Two Sided.
- **Parameters:**
  - `RadiusScale`: start at the sidecar `radius_scale_hint` (1.9–4.3). This restores the coverage lost to decimation; lower it for a sparser sand look.
  - `Dissolve`: 0..1, where 1 = all splats visible.
  - `DissolveSoftness`: about 0.05.
  - `DriftTime`: seconds since the drift started.
  - `DelaySpread`: seconds.
  - `Gravity`: 980 (cm/s²).
  - `Wind`: float3, cm/s.

**1. World Position Offset.** Custom node, output Float3. Inputs:

- `Corner` = TexCoord[0]
- `RadiusCm` = TexCoord[1].r
- `Seed` = TexCoord[1].g
- `ObjScale` = length(TransformVector Local→World of (0,0,1))
- the parameters above

```hlsl
float3 right = ResolvedView.ViewToTranslatedWorld[0].xyz;          // camera right (world)
float3 up    = ResolvedView.ViewToTranslatedWorld[1].xyz;          // camera up (world)
float grow = saturate((Dissolve - Seed) / max(DissolveSoftness, 1e-4)); // dissolve threshold: seed vs Dissolve; 0 = collapsed quad, no pixel cost
float3 wpo = (right * Corner.x + up * Corner.y) * (RadiusCm * RadiusScale * ObjScale * grow);
float t = max(0.0, DriftTime - Seed * DelaySpread);                // gravity drift: seed-based delay, then fall
wpo += Wind * t - float3(0, 0, 0.5 * Gravity * t * t);             // UE world is Z-up, cm
return wpo;
```

**2. SH degree 1 (vertex).** Custom node, output Float3. Pass the result through a **VertexInterpolator**. Inputs:

- `DirLocal` = TransformVector World→Local of (Absolute World Position *excluding material offsets* − Camera Position)
- `SH2..SH6` = TexCoord[2..6]

3DGS evaluates `rgb += C1·(−y·sh1 + z·sh2 − x·sh3)` with `d = normalize(splat − camera)` in PLY axes. The converter already folded those signs and the axis change into the stored vectors, so only dot products remain:

```hlsl
float3 d = normalize(DirLocal).xzy;                 // UE local (x,y,z) -> glTF (x,z,y)
float3 R = float3(SH2.x, SH2.y, SH3.x);
float3 G = float3(SH3.y, SH4.x, SH4.y);
float3 B = float3(SH5.x, SH5.y, SH6.x);
return 0.4886025 * float3(dot(R, d), dot(G, d), dot(B, d));   // C1
```

**3. Emissive (pixel).** Custom node, output Float3. Inputs:

- `Rgb` = VertexColor.rgb
- `SH` = output of the interpolator
- `Tint` (float3)
- `Mono` (0/1)

FoA is monochrome, so keep the true colors in the data and tint here:

```hlsl
float3 lin = pow(saturate(Rgb + SH), 2.2);          // 3DGS colors are display-space; UE emissive is linear
float lum = dot(lin, float3(0.2126, 0.7152, 0.0722));
return lerp(lin, lum * Tint, Mono);
```

**4. Opacity Mask (pixel).** Custom node, output Float1. Leave the clip value at the default. Inputs:

- `Corner` = TexCoord[0]
- `Opacity` = VertexColor.a
- `Seed` = TexCoord[1].g

```hlsl
float a = Opacity * exp(-2.0 * dot(Corner, Corner));    // gaussian; quad edge = 2 sigma
float n = InterleavedGradientNoise(Parameters.SvPosition.xy + Seed * 117.0, View.StateFrameIndexMod8); // seed decorrelates overlapping splats
return a > n ? 1.0 : 0.0;                               // dithered alpha, no sorting; TAA/TSR resolves it
```

## Known limitations

- **Isotropic billboards:** elongated or flat splats render as round blobs. The anisotropy data ships in the mesh but the recipe ignores it.
- **No depth sorting:** soft alpha is stochastic dither. With TSR/TAA it resolves to smooth transparency. Without them (FXAA or no AA) it stays grainy: fine for sand, poor for thin smoke.
- **Decimation:** 40k of 0.4–2M splats loses fine detail. `RadiusScale` fills the gaps at the cost of softness.
- **Precision:** vertex color is 8-bit. UVs are FP16 unless Full Precision UVs is on.
- **Lighting:** unlit splats get no scene lighting or shadows.
- **SH:** the SH path is verified only by `--selftest` against the INRIA convention, because no current Lux3D file contains SH.
- **Facing:** the front direction varies per Lux3D asset. The character and horse face +Z; rotate props in the level.
