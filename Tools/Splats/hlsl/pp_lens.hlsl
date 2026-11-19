// The dream lens, one pass over the finished mono image (one shared radius and tap disc, so one function):
//   barrel    edges bow out like an old wide lens, corners stay in frame, the breath swells it a hair
//   edge haze vision goes soft toward the edges (golden-angle disc, wider toward the corners)
//   halation  highlights bleed a soft glow (bright pass of the same disc); Pro-Mist screen of the soft copy
//   chroma    the palette splits at the edges: a warm copy pushed out, a cold one pulled in; Glitch spikes it
//   black sand visible sand (Custom Stencil 5, depth-gated like MF_Dream_SandWarp) swallows the glow: no haze, Pro-Mist or
//             halation on it, so the goo stays pitch black inside a bright moonbeam (only its own rims and glints show)
//   phone     the phone screen (Custom Stencil 200, exact) keeps its text crisp: no haze, halation or chroma split
//   night     Night (MPC CineNight, 0 in gameplay, keyed by cinematics): the film base and veil crushed to black, the mids
//             pulled down along a 1.6 power, highlights (the moon key, a lamp, a lit face) kept, so it reads as night
// Look: x halation, y edge softness, z barrel, w chroma split. The milky veil is even across the frame (no grey corners).
#define DL_COL(p) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0), PPI_PostProcessInput0, true).rgb
#define DL_ST(p, id) SceneTextureLookup(Parameters, ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, id), id), id, false).r
const float3 lw = float3(0.2126, 0.7152, 0.0722);
float m = 1.0 - saturate(ReduceMotion);
float2 asp = float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0);
float2 d = (UV - 0.5) * asp;
float r = sqrt(dot(d, d) / dot(0.5 * asp, 0.5 * asp));
float k = Look.z * (0.18 + 0.04 * Breath * m);
float2 uv = 0.5 + (UV - 0.5) * (1.0 + k * r * r) / (1.0 + k);
float3 c0 = DL_COL(uv);
float e = saturate((r - 0.25) / 0.75);
e *= e;
float2 rad = View.ViewSizeAndInvSize.zw * (View.ViewSizeAndInvSize.y / 1080.0) * (18.0 + 18.0 * e);
int n = clamp((int)Taps, 4, 16);
float3 blur = 0.0;
[loop] for (int i = 0; i < n; i++)
{
    float a = i * 2.3999632;
    blur += DL_COL(uv + float2(cos(a), sin(a)) * sqrt((i + 0.5) / n) * rad);
}
blur /= n;
float cd = DL_ST(uv, PPI_CustomDepth);
float st = DL_ST(uv, PPI_CustomStencil);
float phone = abs(st - 200.0) < 0.5 ? 1.0 : 0.0;
float sand = max(abs(st - 5.0) < 0.5 && cd <= DL_ST(uv, PPI_SceneDepth) + 2.0 ? 1.0 : 0.0, phone);
float3 col = lerp(c0, blur, e * Look.y * (1.0 - sand));
col += Look.y * 0.012 * (1.0 - col);
float3 glow = 1.0 - (1.0 - col) * (1.0 - blur * Look.x * 0.45);
col = lerp(glow + max(blur - 0.45, 0.0) * Look.x * 1.2, col, sand);
float sh = (Look.w * 0.004 + 0.02 * Glitch * m) * r * r * (1.0 - phone);
float2 dir = d / max(length(d), 1e-4) / asp;
float l0 = dot(c0, lw);
col += float3(1.0, 0.72, 0.42) * (dot(DL_COL(uv + dir * sh), lw) - l0) + float3(0.0, 0.28, 0.58) * (dot(DL_COL(uv - dir * sh), lw) - l0);
float nn = saturate(Night);
col = lerp(col, pow(saturate((col - 0.06) / 0.94), 1.0 + 0.6 * nn) * (1.0 - 0.05 * nn), nn);
#undef DL_COL
#undef DL_ST
return col;