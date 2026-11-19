// Time-shift echo, the hero effect, running VERTICALLY (the user's pick): ghosts slip along Dir (MPC EchoDir, screen
// Y by default) like a film frame slipping in the gate, or a vertical slit-scan. A small static slip is always there;
// motion (velocity magnitude) and story beats (Strength) stretch it. Offsets are fixed, so a still frame stays still.
// Shape: x frames of motion per ghost, y static slip, z decay per ghost, w ghost gain. Dark ghosts blend, light ones glow.
// Visible black sand (Custom Stencil 5, depth-gated) keeps a fifth of it, so its moon glints stay crisp points.
// The phone screen (Custom Stencil 200, exact) gets none: no echo on it, and its pixels never ghost into their neighbours.
#define TE_COL(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, true).rgb
float3 base = TE_COL(UV);
float s = Strength * (1.0 - saturate(ReduceMotion));
if (s < 0.001) return base;
float2 vel = SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(UV, PPI_Velocity), PPI_Velocity), PPI_Velocity, false).xy * float2(0.5, -0.5) / clamp(View.DeltaTime * 60.0, 0.5, 4.0);
float2 stepUV = Dir.xy / max(length(Dir.xy), 1e-4) * (Shape.y * 0.004 + length(vel) * Shape.x);
int n = clamp((int)Taps, 2, 8);
float3 acc = 0.0;
float wsum = 0.0, w = 1.0;
#define TE_ST(id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(UV, id), id), id, false).r
#define TE_PH(p) (abs(SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_CustomStencil), PPI_CustomStencil), PPI_CustomStencil, false).r - 200.0) < 0.5)
if (TE_PH(UV)) return base;
[loop] for (int k = 1; k <= n; k++)
{
    w *= Shape.z;
    float2 tp = UV + stepUV * k;
    acc += (TE_PH(tp) ? base : TE_COL(tp)) * w;
    wsum += w;
}
float3 gh = acc / wsum;
float sand = abs(TE_ST(PPI_CustomStencil) - 5.0) < 0.5 && TE_ST(PPI_CustomDepth) <= TE_ST(PPI_SceneDepth) + 2.0 ? 1.0 : 0.0;
float op = saturate(wsum * Shape.w * s) * (1.0 - 0.8 * sand);
#undef TE_ST
#undef TE_PH
#undef TE_COL
return base + (gh - base) * op + max(gh - base, 0.0) * op * 0.6;