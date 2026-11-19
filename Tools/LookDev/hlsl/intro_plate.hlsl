// M_IntroPlate (story lane): one intro panel from one packed plate, all motion in the shader.
// Plate R = luminance (display-encoded), G = nearness 0 far..1 near, B = luminance with the panel's light on,
// A = figure matte. Inputs: UV, Plate, Age (s into the panel), Motion (-0.5..0.5, 0 with reduce motion), Panel (index).
// Depth parallax camera move, light change, black sand grains, sand forming in and crumbling out, film grain.
// Durations mirror WBP_IntroStory Seconds (Tools/LookDev/intro_plates.py writes both).
struct IntroFx
{
    float Hash(float2 p)
    {
        float3 p3 = frac(float3(p.xyx) * 0.1031);
        p3 += dot(p3, p3.yzx + 33.33);
        return frac((p3.x + p3.y) * p3.z);
    }
    float Noise(float2 p)
    {
        float2 i = floor(p), f = frac(p);
        f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + 1.0), f.x), f.y);
    }
    // One layer of falling grains: x = coverage (dark grain), y = glint
    float2 Grains(float2 uv, float cells, float fall, float density, float t, float seed)
    {
        float2 g = float2(uv.x * cells * 1.7778, uv.y * cells - t * fall * cells);
        float2 c = floor(g), f = frac(g);
        float h = Hash(c + seed);
        if (h > density) return 0;
        float2 o = float2(Hash(c + seed + 7.1), Hash(c + seed + 3.7)) * 0.7 + 0.15;
        o.x += sin(t * (1.3 + h * 2.0) + h * 40.0) * 0.12;  // drift in the air
        float r = 0.05 + 0.07 * Hash(c + seed + 1.3);
        float d = length(f - o);
        float grain = smoothstep(r, r * 0.35, d);
        float glint = step(0.9, Hash(c + seed + 9.2)) * pow(saturate(sin(t * 6.0 + h * 60.0)), 8.0) * grain;
        return float2(grain, glint);
    }
};
IntroFx fx;
int panel = (int)round(Panel);
// per panel: x, y drift over the whole panel (UV), push (dolly), seconds
float4 move = panel == 0 ? float4(0.016, -0.004, 0.10, 5.0)
            : panel == 1 ? float4(-0.006, 0.010, 0.07, 4.5)
            : panel == 2 ? float4(0.030, 0.000, 0.05, 4.5)
            : panel == 3 ? float4(-0.004, -0.006, 0.07, 5.5)
            :              float4(0.000, 0.008, 0.42, 1.6);
float m = Motion * 2.0;                                   // -1..1 across the panel
float p01 = saturate(Motion + 0.5);
float push = move.z * (panel == 4 ? p01 * p01 : p01);     // the lunge accelerates
float2 drift = move.xy * m;
// shake on the lunge
if (panel == 4) drift += (float2(fx.Noise(float2(Age * 23.0, 1.0)), fx.Noise(float2(3.0, Age * 23.0))) - 0.5) * 0.012 * p01;
// inverse depth warp: find the source UV whose parallaxed position lands on this pixel
float2 c = float2(0.5, 0.5);
float2 base = c + (UV - c) * 0.9;                         // 10 % overscan for the drift
float2 s = base;
[unroll] for (int i = 0; i < 6; i++)
{
    float n = Texture2DSampleLevel(Plate, PlateSampler, s, 0).g;
    s = c + (base - c) / (1.0 + push * (0.35 + 0.9 * n)) - drift * (n - 0.35);
}
s = clamp(s, 0.001, 0.999);
// the figure tears now and then (the Nightmare's slice glitch), always on the lunge
float4 probe = Texture2DSampleLevel(Plate, PlateSampler, s, 0);
float tearOn = panel == 4 ? 1.0 : step(0.82, fx.Noise(float2(floor(Age * 9.0), panel)));
float band = floor(s.y * 70.0);
s.x += probe.a * tearOn * (fx.Hash(float2(band, floor(Age * 18.0))) - 0.5) * 0.035 * step(0.55, fx.Hash(float2(band, 7.0)));
float4 plate = Texture2DSample(Plate, PlateSampler, s);
// light change
float light = 0.0;
if (panel == 1) light = smoothstep(0.55, 0.95, Age) * (1.0 - 0.6 * step(0.7, Age) * step(Age, 0.78));       // the phone wakes
if (panel == 3) light = 1.0 - 0.8 * step(0.86, fx.Noise(float2(Age * 7.0, 2.0))) * step(2.2, Age);        // the light falters
if (panel == 0 || panel == 2) light = 0.5 + 0.5 * sin(Age * 1.3);                                         // moon behind cloud
if (panel == 4) light = 1.0 - smoothstep(0.6, 1.1, Age);
float lum = lerp(plate.r, plate.b, saturate(light));
// sand forms in, and crumbles out at the end (the lunge cuts in hard)
float secs = move.w;
float grainN = fx.Noise(UV * float2(320.0, 180.0)) * 0.65 + fx.Noise(UV * float2(40.0, 22.0)) * 0.35;
float formIn = panel == 4 ? 1.0 : smoothstep(grainN - 0.12, grainN, Age / 0.55);
float crumble = smoothstep(secs - (panel == 4 ? 0.7 : 0.45), secs, Age);
float fallMask = step(grainN, crumble * 1.15);
lum *= formIn * (1.0 - fallMask);
// black sand in the air, over the lit parts; glints only where there is light
float2 g1 = fx.Grains(UV + drift * 0.6, 70.0, 0.035, 0.10, Age, 1.0);
float2 g2 = fx.Grains(UV + drift * 1.1, 130.0, 0.055, 0.12, Age, 5.0);
float2 g3 = fx.Grains(UV - drift * 0.4, 230.0, 0.025, 0.14, Age, 9.0);
float amount = panel == 0 ? 1.0 : panel == 2 ? 0.9 : panel == 4 ? 1.4 : 0.6;
float dark = saturate((g1.x * 0.9 + g2.x * 0.7 + g3.x * 0.5) * amount);
float glint = saturate(g1.y + g2.y + g3.y) * smoothstep(0.25, 0.6, lum) * amount;
// the shirt and the figure shed sand: grains fall from the matte's edges
if (panel >= 2)
{
    float above = Texture2DSampleLevel(Plate, PlateSampler, s - float2(0, 0.05 + frac(Age * 0.35) * 0.15), 0).a;
    float2 shed = fx.Grains(UV, 260.0, 0.22, 0.45, Age, 13.0);
    dark = saturate(dark + shed.x * above * (1.0 - plate.a));
}
lum = lum * (1.0 - dark * 0.85) + glint * 0.9;
// grade: deep blacks, a soft shoulder, film grain and a vignette
lum = saturate(lum);
lum = lum * lum * (3.0 - 2.0 * lum) * 0.35 + lum * 0.65;
float grain = (fx.Hash(UV * 1931.0 + frac(Age * 24.0) * 97.0) - 0.5) * 0.045;
float2 v = (UV - 0.5) * float2(1.0, 0.85);
lum = saturate(lum + grain) * (1.0 - 0.55 * pow(saturate(length(v) * 1.35), 2.2));
lum *= 1.0 - 0.5 * smoothstep(0.66, 0.97, UV.y);                          // the lower third sinks, so the line reads on any plate
float3 tone = lerp(float3(0.0, 0.0, 0.0), float3(0.94, 0.95, 0.96), lum);   // cold white, true black
return float4(pow(tone, 2.2), 1.0);
