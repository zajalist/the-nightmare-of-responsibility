// Face blur v11: only his FACE (brow to chin, ear to ear) is smeared, never the hair, the back of the head or the
// background. Mask = Custom Stencil 4 (the head mesh; the hair groom writes stencil 0) where it is the visible
// surface, times a soft oval in head space around MPC FaceOrigin (axes FaceRight, FaceForward, published by
// BP_FoAPlayer), so the back of the head and the scalp under the hair drop out. Inside it, each thin scan line is
// slipped sideways by its own amount (lines tear apart, so features land on the wrong rows) and dragged over a short
// stretch (a third of a face width at most), sampling face pixels only, darkened and combed; the oval edge fades it
// out. Past the face only a slipped line may overhang his silhouette (6% of a face width at most, onto background). Sizes in head heights H (FaceOrigin
// depth), so the look holds at any distance and resolution. FaceSlip below -0.5 is mask review, above 1 a burst.
// Runs after M_PP_DreamLens: colour is the barrel-bent picture, so stencil and depth go through the same barrel
// (keep fb.Lens in step with pp_lens.hlsl).
#define FB_TUV(p, id) ClampSceneTextureUV(ViewportUVToSceneTextureUV(p, id), id)
#define FB_COL(p) SceneTextureLookup(Parameters, FB_TUV(p, PPI_PostProcessInput0), PPI_PostProcessInput0, true).rgb
#define FB_STQ(q, id) SceneTextureLookup(Parameters, FB_TUV(q, id), id, false).r
// Face weight of a screen point: head stencil, visible, inside the face oval.
#define FB_FACE(p) fb.Face(fb.Lens(p, LA, LK), FB_STQ(fb.Lens(p, LA, LK), PPI_CustomStencil), FB_STQ(fb.Lens(p, LA, LK), PPI_CustomDepth), FB_STQ(fb.Lens(p, LA, LK), PPI_SceneDepth), FaceOrigin.xyz, FR, FF, FU)
struct FFaceBlur
{
    float Hash(float2 p)
    {
        uint2 q = uint2(int2(floor(p)) + 65536);
        uint s = q.x * 1664525u + q.y * 2654435761u + 1013904223u;
        s = s * 747796405u + 2891336453u;
        s = ((s >> ((s >> 28u) + 4u)) ^ s) * 277803737u;
        return float((s >> 22u) ^ s) * (1.0 / 4294967295.0);
    }
    float Noise(float x, float seed)
    {
        float i = floor(x);
        float f = x - i;
        f = f * f * (3.0 - 2.0 * f);
        return lerp(Hash(float2(i, seed)), Hash(float2(i + 1.0, seed)), f);
    }
    float2 Lens(float2 p, float2 asp, float k)
    {
        float2 d = (p - 0.5) * asp;
        float r2 = dot(d, d) / dot(0.5 * asp, 0.5 * asp);
        return 0.5 + (p - 0.5) * (1.0 + k * r2) / (1.0 + k);
    }
    // The face oval in head space (cm): 8.5 ear to ear, 10.5 brow to chin (centred 1 cm below FaceOrigin), and only
    // the front of the head (fades out from 6 to 9.5 cm behind the face centre), soft over its outer 30 percent
    // (about 15 percent of a face width at the hairline and ears).
    float Oval(float3 w, float3 o, float3 r, float3 f, float3 u)
    {
        float3 q = w - o;
        float2 e = float2(dot(q, r) / 8.5, (dot(q, u) + 1.0) / 10.5);
        return (1.0 - smoothstep(0.5, 1.0, dot(e, e))) * smoothstep(-9.5, -6.0, dot(q, f));
    }
    // Head stencil, the visible surface (not hidden behind something nearer), then the oval at its world position.
    float Face(float2 q, float st, float cd, float sd, float3 o, float3 r, float3 f, float3 u)
    {
        if (abs(st - 4.0) > 0.5 || cd > sd + max(0.75, 0.003 * sd)) return 0.0;
        float3 w = DFHackToFloat(SvPositionToWorld(float4(ViewportUVToBufferUV(q) * View.BufferSizeAndInvSize.xy, ConvertToDeviceZ(sd), 1.0)));
        return Oval(w, o, r, f, u);
    }
};
FFaceBlur fb;
float2 LA = float2(View.ViewSizeAndInvSize.x * View.ViewSizeAndInvSize.w, 1.0);
float LK = LensLook.z * (0.18 + 0.04 * Breath * (1.0 - saturate(ReduceMotion)));
float3 FF = normalize(FaceForward.xyz);
float3 FR = normalize(FaceRight.xyz);
float3 FU = normalize(cross(FR, FF));
float3 base = FB_COL(UV);
bool review = Amount < -0.5;
float3 dim = float3(0.0, 0.0, 0.25 * dot(base, float3(0.3333, 0.3333, 0.3333)));
if (FaceOrigin.w < 0.5) return review ? dim : base;  // face pose not published: nothing to blur
float2 VS = View.ViewSizeAndInvSize.xy;
float2 px = View.ViewSizeAndInvSize.zw;
float3 rel = FaceOrigin.xyz - CamPos;
float fd = dot(rel, View.ViewForward);
if (fd < 15.0) return review ? dim : base;  // camera at or inside his head (first person)
float2 HC = 0.5 + 0.5 * float2(dot(rel, View.ViewRight) * View.ViewToClip[0][0], -dot(rel, View.ViewUp) * View.ViewToClip[1][1]) / fd;
float H = 27.0 * View.ViewToClip[1][1] * 0.5 * VS.y / fd;
// Far from his face on screen: nothing to do.
if (length((UV - HC) * VS) > 0.7 * H) return review ? dim : base;
float self = FB_FACE(UV);
if (review) return self < 0.002 ? dim : float3(self, self > 0.5 ? 1.0 : 0.0, dim.b);
// Per line: thin lines (2 px at 1080p), smooth slow fields along the face plus a small drifting jitter per line.
float t = View.GameTime * (1.0 - 0.9 * saturate(ReduceMotion));
float burst = saturate(Amount - 1.0);
float yH = (UV.y - 0.5) * VS.y / H;
float lineId = floor(UV.y * VS.y / max(1.0, VS.y / 540.0));
float k0 = t * 0.7 + fb.Hash(float2(lineId, 5.0)) * 9.0;
float jit = lerp(fb.Hash(float2(lineId, floor(k0))), fb.Hash(float2(lineId, floor(k0) + 1.0)), smoothstep(0.0, 1.0, frac(k0)));
float W = 0.6 * H;  // face width
// About one line in eight tears further for a while.
float tear = step(0.88, fb.Hash(float2(lineId, floor(k0 * 0.5) + 41.0)));
float len = (0.12 + 0.14 * fb.Noise(yH * 3.0 + 0.13 * t, 7.0) + 0.08 * (fb.Hash(float2(lineId, 17.0)) - 0.5) + 0.1 * burst) * W;
float off = (0.10 * (fb.Noise(yH * 2.0 - 0.11 * t, 3.0) - 0.5) + 0.08 * (fb.Noise(yH * 8.0 + 0.2 * t, 23.0) - 0.5)
          + (0.22 + 0.3 * tear) * (jit - 0.5)) * (1.0 + burst) * W;
off *= self < 0.002 ? 1.0 : 0.35 + 0.65 * self;  // the slip fades in over the soft edge (hairline, ears)
float dirL = fb.Hash(float2(lineId, 71.0)) < 0.6 ? 1.0 : -1.0;
float phase = fb.Hash(float2(floor(UV.x * VS.x), lineId * 3.0 + 29.0));
// Kernel: 10 taps over the stretch, most weight near its start (a dragged copy keeps the dark masses as dashes).
float2 o = float2((off - 0.2 * len * dirL) * px.x, 0.0);
float dx = dirL * len * px.x / 10.0;
if (self < 0.002)
{
    // Outside the face: a slipped line may overhang his silhouette by at most 6% of a face width, and only onto
    // background well behind his face (never hair, ears, neck or clothes, which sit at his depth).
    if (FB_STQ(fb.Lens(UV, LA, LK), PPI_SceneDepth) < fd + 30.0) return base;
    self = smoothstep(0.3, 0.8, FB_FACE(UV + float2(clamp(o.x * VS.x, -0.06 * W, 0.06 * W) * px.x, 0.0)));
    if (self < 0.002) return base;
}
// A line slipped off the face slips the other way instead, so the face edge never keeps clean skin.
else if (FB_FACE(UV + o + float2(5.0 * dx, 0.0)) < 0.25) o.x = (-off - 0.2 * len * dirL) * px.x;
float3 acc = 0.0;
float ws = 0.0;
[unroll] for (int i = 0; i < 10; ++i)
{
    float2 s = UV + o + float2((i + phase) * dx, 0.0);
    float m = FB_FACE(s) * (0.3 + 0.7 * exp2(-0.5 * i));
    acc += FB_COL(s) * m;
    ws += m;
}
float3 smear = lerp(base, acc / max(ws, 1e-3), saturate(ws * 1.5));
// Where the clean pixel is darker than the smear, 40 percent of that darkness stays: shadows smudge, never wash out.
float lb = dot(base, float3(0.3333, 0.3333, 0.3333));
float ls = dot(smear, float3(0.3333, 0.3333, 0.3333));
smear *= lerp(1.0, clamp(lb / max(ls, 1e-4), 0.35, 1.0), 0.4);
// The face keeps its own light and dark (mean within about 10 percent of clean skin), combed lines (each line 0.8 to
// 1.15, every third pixel row 14% darker) and a fine grain.
float row = UV.y * VS.y / max(1.0, VS.y / 1080.0);
smear *= 1.05 * (0.8 + 0.35 * fb.Hash(float2(lineId, 61.0))) * (1.0 - 0.14 * step(2.0, fmod(floor(row), 3.0)));
smear *= 1.0 + 0.1 * (fb.Hash(floor(UV * VS) + float2(0.0, 977.0 * floor(t * 24.0))) - 0.5);
// Only light and dark travel along a line; the hue is the clean pixel's own, so a tap that lands on a coloured
// neighbour (the stencil-1 doorway portal behind his head, the lens's chroma fringe at his silhouette) never tints him.
smear = dot(smear, float3(0.3333, 0.3333, 0.3333)) * (lb > 1e-3 ? clamp(base / lb, 0.0, 2.0) : float3(1.0, 1.0, 1.0));
return lerp(base, smear, self);
