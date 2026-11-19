// Monochrome split tone: luminance, the ink contrast (Film.w: black point + contrast around a night mid-grey, the
// A-style punch without flattening low-key frames like the moodboard's (L-0.07)/0.88 crush did) and the ink lines, tinted
// from ShadowTint to HighlightTint. HueDrift (0..1 over the story) walks warm keys: soft yellow > honey > amber > ochre
// as luminance-neutral multipliers on those (unit-luminance) tints: the hue moves, the brightness never does.
// Stencil 1 (where visible) or ColorReveal keep real color; 2 (tear), 4 (face blur), 5 (sand) stay mono; 3 (focus) gets a soft warm rim.
const float3 lw = float3(0.2126, 0.7152, 0.0722);
float L = dot(Color, lw);
float Lc = saturate((L - 0.006) / 0.994);
L = lerp(L, saturate(0.12 * pow(Lc / 0.12, 1.0 + 0.4 * Film.w)), saturate(Film.w)) * (1.0 - Ink);
float p = saturate(HueDrift) * 3.0;
float3 sk = p < 1.0 ? lerp(float3(1.04, 1.00, 0.86), float3(1.06, 1.00, 0.82), p)
          : p < 2.0 ? lerp(float3(1.06, 1.00, 0.82), float3(1.08, 0.99, 0.78), p - 1.0)
                    : lerp(float3(1.08, 0.99, 0.78), float3(1.11, 0.98, 0.72), p - 2.0);
float3 hk = p < 1.0 ? lerp(float3(1.06, 1.03, 0.90), float3(1.07, 1.03, 0.87), p)
          : p < 2.0 ? lerp(float3(1.07, 1.03, 0.87), float3(1.08, 1.02, 0.84), p - 1.0)
                    : lerp(float3(1.08, 1.02, 0.84), float3(1.10, 1.01, 0.79), p - 2.0);
float3 sd = sk / float3(1.04, 1.00, 0.86);
float3 hd = hk / float3(1.06, 1.03, 0.90);
sd /= dot(sd, lw);
hd /= dot(hd, lw);
float3 hiTint = HighlightTint.rgb * hd;
hiTint /= max(hiTint.r, max(hiTint.g, hiTint.b));                              // highlights: hue only, never gain above 1
float3 mono = L * lerp(ShadowTint.rgb / dot(ShadowTint.rgb, lw) * sd, hiTint, saturate(L));
float2 suv = GetViewportUV(Parameters);                                       // unwarped: kept colour misregisters under glitches
#define MT_ST(id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(suv, id), id), id, false).r
// custom stencil/depth draw without the scene's depth test: a stencil only counts where that mesh is the visible surface
#define MT_AT(uv, id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(uv, id), id), id, false).r
#define MT_VS(uv) (MT_AT(uv, PPI_CustomDepth) <= MT_AT(uv, PPI_SceneDepth) + 2.0 ? MT_AT(uv, PPI_CustomStencil) : 0.0)
float st = MT_VS(suv);
// focus highlight (contract: Custom Stencil 3 on the focused mesh): a soft warm-white rim on both sides of its edge
float2 ro = 4.0 * max(View.ViewSizeAndInvSize.y / 1080.0, 0.5) * View.ViewSizeAndInvSize.zw;
float n3 = 0.0;
[unroll] for (int i = 0; i < 8; i++)
    n3 += abs(MT_VS(suv + float2(cos(i * 0.785398), sin(i * 0.785398)) * ro) - 3.0) < 0.5 ? 0.125 : 0.0;   // visible taps only: no grid through occluders
float rim = abs(st - 3.0) < 0.5 ? 1.0 - n3 : n3;
mono += hiTint * saturate(rim * 1.6) * 0.2;
float keep = max(abs(st - 1.0) < 0.5 ? 1.0 : 0.0, saturate(ColorReveal));   // 1 only: 2 tear, 3 focus, 4 face, 5 sand stay mono
return lerp(mono, Color, keep);
#undef MT_VS
#undef MT_AT
#undef MT_ST