// MF_SplatMorph 'Morph' (vertex): sand flowing from one Lux3D object into the next. Each splat's position in every
// shape is a texel of MorphTex (rows of Cfg.y x Cfg.y texels per shape, xyz in metres; make_sand_morph.py), paired by
// height band then angle, so the flow is coherent. SandEvent (custom primitive data 0-3) = (from row, to row, start s,
// seconds; BP_SandMorph). A per-splat delay sweeps through the shape (bottom first when rising, top first when falling),
// the grains fly along a shared curl-noise flow with a slight sag (sand falling between shapes), then settle. Returns
// the offset from the splat's rest position (the sand row). Cfg = (rows, texels per side, object size cm, curl cm).
struct FM
{
    float3 G3(float3 p)
    {
        p = float3(dot(p, float3(127.1, 311.7, 74.7)), dot(p, float3(269.5, 183.3, 246.1)), dot(p, float3(113.5, 271.9, 124.6)));
        return frac(sin(p) * 43758.5453) * 2.0 - 1.0;
    }
    float3 NG(float3 x)  // gradient of value-weighted gradient noise (cheap, smooth)
    {
        float3 i = floor(x), f = frac(x), u = f * f * (3.0 - 2.0 * f), du = 6.0 * f * (1.0 - f);
        float3 a = G3(i), b = G3(i + float3(1, 0, 0)), c = G3(i + float3(0, 1, 0)), d = G3(i + float3(0, 0, 1));
        return a + u.x * (b - a) + u.y * (c - a) + u.z * (d - a) + du * float3(dot(b - a, f), dot(c - a, f), dot(d - a, f)) * 0.5;
    }
    float3 Curl(float3 p) { return cross(NG(p), NG(p + float3(31.4, -17.3, 9.27))); }
};
FM m;
uint x = asuint(RadiusSeed.y) * 747796405u + 2891336453u;
x = ((x >> ((x >> 28u) + 4u)) ^ x) * 277803737u;
x ^= x >> 22u;
float4 h = float4(x & 255u, (x >> 8u) & 255u, (x >> 16u) & 255u, x >> 24u) / 255.0;
float W = Cfg.y;
float2 cell = float2(fmod(Idx, W), floor(Idx / W));
float2 scale = float2(1.0 / W, 1.0 / (W * Cfg.x));
float3 A = Texture2DSampleLevel(Tex, TexSampler, (cell + float2(0.0, Ev.x * W) + 0.5) * scale, 0).xyz * 100.0;
float3 B = Texture2DSampleLevel(Tex, TexSampler, (cell + float2(0.0, Ev.y * W) + 0.5) * scale, 0).xyz * 100.0;
float life = Ev.w > 0.0 ? saturate((Clock - Ev.z) / Ev.w) : 1.0;
float up = step(A.z, B.z), hA = saturate(A.z / max(Cfg.z, 1.0));
float d = 0.45 * (0.7 * lerp(1.0 - hA, hA, up) + 0.3 * h.x);
float s = smoothstep(d, d + 0.55, life);
float arc = sin(3.14159 * s);
float3 p = lerp(A, B, s * s * (3.0 - 2.0 * s));
p += m.Curl(p * 0.06 + float3(0.0, 0.0, Clock * 0.3)) * arc * Cfg.w;
p.z += arc * (0.25 * Cfg.z * up - 0.12 * Cfg.z * (1.0 - up));             // rising sand bulges up, falling sand sags
p.xy += normalize(p.xy + 1e-3) * arc * 0.15 * Cfg.z * h.y;                 // a loose shell of grains around the flow
return p - Rest;
