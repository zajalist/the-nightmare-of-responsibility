// M_IntroPlate v4 (intro lane): one intro panel as a multiplane shot, all in one pass.
// Plate (2048): R ink-graded luminance, G nearness 0 far..1 near, B luminance with the panel's light on, A subject matte.
// Back (1024): R back luminance with the subject and cutouts filled, G back nearness filled, B back lit, A near cutout.
// Inputs: UV, Plate, Back, Noise (T_UI_SandNoise: R specks, G clumps, B fBm), Age (s into the panel), Motion (-0.5..0.5
// across it, 0 under Reduce Motion), Panel, Calm (MPC_UI.ReduceMotion). Planes: the back (continuous depth warp), the subject and the near cutout (rigid, own rates,
// own focus), then black sand in the air, halation, light leak, etched shadows, paper, grain, and sand sweeps in/out.
// Timing table generated from Tools/LookDev/intro_v4/story.py (build_material_v4.py writes it in).
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
    // one layer of airborne grains: x = coverage, y = glint
    float2 Grains(float2 uv, float cells, float fall, float density, float t, float seed)
    {
        float2 g = float2(uv.x * cells * 1.7778, uv.y * cells - t * fall * cells);
        float2 c = floor(g), f = frac(g);
        float h = Hash(c + seed);
        if (h > density) return 0;
        float2 o = float2(Hash(c + seed + 7.1), Hash(c + seed + 3.7)) * 0.7 + 0.15;
        o.x += sin(t * (1.3 + h * 2.0) + h * 40.0) * 0.12;
        float r = 0.05 + 0.07 * Hash(c + seed + 1.3);
        float grain = smoothstep(r, r * 0.35, length(f - o));
        float glint = step(0.9, Hash(c + seed + 9.2)) * pow(saturate(sin(t * 6.0 + h * 60.0)), 8.0) * grain;
        return float2(grain, glint);
    }
    float2 Rot(float2 v, float a)
    {
        float s = sin(a), c = cos(a);
        return float2(c * v.x - s * v.y, s * v.x + c * v.y);
    }
};
IntroFx fx;
const float AR = 1.7778;
const float2 C0 = float2(0.5, 0.5);
int panel = (int)round(Panel);
// @@TABLE@@
float secs = tim.x, fin = tim.y, fout = tim.z;
float live = 1.0 - saturate(Calm);
float2 wind = normalize(float2(1.0, 0.22));                          // Reduce Motion stills shake, boil and breathing
float p01 = saturate(Motion + 0.5);
float e = p01 * p01 * (3.0 - 2.0 * p01);
// ---- the shot: camera A to B, per-plane depth and zoom, focus pull ----------------------------------------------
// cam: pan x, pan y (UV), zoom far, zoom near; mov: pan to x, pan to y, roll from, roll to; dep: subject d, near d,
// focus from, focus to; foc: focus pull start, end (s), defocus gain, leak
float4 cam = panel == 0 ? float4(0.022, 0.030, 0.05, 0.24)
           : panel == 1 ? float4(0.034, -0.010, 0.03, 0.16)
           : panel == 2 ? float4(-0.030, 0.004, 0.02, 0.10)
           : panel == 3 ? float4(0.004, 0.012, -0.12, 0.16)
           :              float4(0.000, 0.000, 0.10, 0.50);
float4 mov = panel == 0 ? float4(-0.022, -0.012, 0.010, -0.004)
           : panel == 1 ? float4(0.008, 0.010, -0.022, 0.0)
           : panel == 2 ? float4(0.030, -0.006, 0.0, 0.004)
           : panel == 3 ? float4(-0.004, -0.010, 0.0, 0.016)
           :              float4(0.0, 0.010, 0.0, -0.03);
float4 dep = panel == 0 ? float4(0.35, 1.30, 0.22, 0.22)
           : panel == 1 ? float4(0.55, 1.20, 1.20, 0.55)
           : panel == 2 ? float4(0.75, 1.20, 0.75, 0.75)
           : panel == 3 ? float4(0.60, 1.25, 0.60, 0.60)
           :              float4(0.85, 1.20, 0.85, 0.85);
float4 foc = panel == 0 ? float4(0.0, 1.0, 2.4, 0.16)
           : panel == 1 ? float4(1.0, 2.3, 3.4, 0.0)
           : panel == 2 ? float4(0.0, 1.0, 2.6, 0.14)
           : panel == 3 ? float4(0.0, 1.0, 2.4, 0.08)
           :              float4(0.0, 1.0, 1.0, 0.0);
float push = panel == 4 ? p01 * p01 : e;                    // the lunge accelerates
float2 pan = lerp(cam.xy, mov.xy, e);
float roll = lerp(mov.z, mov.w, e) * (panel == 4 ? 0.0 : 1.0);
float focus = lerp(dep.z, dep.w, smoothstep(foc.x, foc.y, Age));
// ---- sand in and out: one wind, left to right and a little down (the text kit's direction) -----------------------
float across = 0.5 + dot((UV - C0) * float2(AR, 1.0), wind) / (AR * 1.08);
if (panel == 4) across = length((UV - C0) * float2(AR, 1.0)) * 0.62;          // the hook crumbles from the middle out
float2 wv = (UV - C0) * float2(AR, 1.0);
float2 wp = float2(dot(wv, wind), dot(wv, float2(-wind.y, wind.x)));     // along and across the wind
float4 nz = Texture2DSampleLevel(Noise, NoiseSampler, wp * float2(1.5, 13.0), 0);           // fBm streaked along the wind
float4 nc = Texture2DSampleLevel(Noise, NoiseSampler, wp * float2(0.35, 1.7) + 0.37, 0);
float sandN = nz.b * 0.45 + nc.b * 0.35 + fx.Hash(floor(UV * float2(960.0, 540.0))) * 0.2;
float tIn = fin > 0.0 ? saturate(Age / fin) : 1.0;
float tOut = fout > 0.0 ? saturate((Age - (secs - fout)) / fout) : 0.0;
float frontIn = tIn * 1.5 - 0.25, frontOut = tOut * 1.5 - 0.25;
float edgeIn = frontIn - across, edgeOut = frontOut - across;  // > 0: the front has passed this pixel
float formed = tIn >= 1.0 ? 1.0 : smoothstep(0.0, 0.10, edgeIn + (sandN - 0.5) * 0.22);
float eaten = tOut <= 0.0 ? 0.0 : smoothstep(0.0, 0.10, edgeOut + (sandN - 0.5) * 0.22);
// the frame is blown downwind at the fronts: pixels near a front slide with the sand before they go
float blow = saturate(1.0 - abs(edgeOut) * 8.0) * step(0.001, tOut) + saturate(1.0 - abs(edgeIn) * 8.0) * (1.0 - tIn) * step(0.001, fin);
float2 q = UV - wind * blow * (0.012 + 0.03 * sandN) * float2(1.0 / AR, 1.0);
if (panel == 4)
{
    q += (float2(fx.Noise(float2(Age * 23.0, 1.0)), fx.Noise(float2(3.0, Age * 23.0))) - 0.5) * 0.014 * p01 * live;
    q.y += eaten * eaten * 0.08 * sandN;                      // crumbling grains fall
}
// camera roll and the 10 % overscan the moves live in
float2 v = fx.Rot((q - C0) * float2(AR, 1.0), roll) / float2(AR, 1.0);
float2 scr = C0 + v * 0.9;
// one plane at depth d: where on its texture this screen pixel lands
#define PLANE(d) (C0 + (scr - C0 - pan * ((d) - dep.x) * 2.0) / (1.0 + push * lerp(cam.z, cam.w, saturate((d) / 1.3))))
// ---- back: a continuous depth warp of the filled plate ------------------------------------------------------------
float2 sb = scr;
float nb = 0.3;
[unroll] for (int i = 0; i < 3; i++)
{
    nb = Texture2DSampleLevel(Back, BackSampler, sb, 1).g;
    sb = PLANE(nb);
}
sb = clamp(sb, 0.001, 0.999);
float blurB = clamp(abs(nb - focus) * foc.z, 0.0, 3.5);
float4 bk = Texture2DSampleLevel(Back, BackSampler, sb, blurB * 0.5);
float4 pb = Texture2DSampleLevel(Plate, PlateSampler, sb, blurB);
float hole = saturate(max(Texture2DSampleLevel(Plate, PlateSampler, sb, 3.0).a, Texture2DSampleLevel(Back, BackSampler, sb, 2.0).a) * 5.0);
// light: the moon breathing, the phone waking, the watcher's light faltering
float light = 0.5 + 0.5 * sin(Age * 1.1);
if (panel == 1) light = smoothstep(0.30, 0.75, Age) * (1.0 - 0.7 * step(0.62, Age) * step(Age, 0.70));
float expo = 1.0;
if (panel == 3)  // three blackouts (it moves in each), a nervous flicker between, and the light failing before the hook
    expo = 1.0 - 0.9 * saturate(step(4.2, Age) * step(Age, 4.4) + step(6.14, Age) * step(Age, 6.33) + step(7.6, Age) * step(Age, 7.82))
               - 0.3 * step(0.9, fx.Noise(float2(Age * 7.0, 2.0))) * step(2.6, Age) - 0.6 * smoothstep(8.55, 9.0, Age);
if (panel == 4) expo = 1.0 - 0.35 * smoothstep(0.5, 1.0, Age);
float lum = lerp(lerp(pb.r, pb.b, light), lerp(bk.r, bk.b, light), hole);
// ---- subject: a rigid plane (the phone, the shirt, the figure); the shirt breathes -------------------------------
float hasS = panel == 0 ? 0.0 : 1.0;
float2 vs = scr;
if (panel == 2) vs = C0 + (scr - C0) / (1.0 + 0.010 * sin(Age * 1.7) * live);
float2 ss = PLANE(dep.x) + (vs - scr);
// beats: the empty shirt twitches once, after its line; the watcher comes a step closer in each blackout
float twitch = panel == 2 ? smoothstep(4.35, 4.5, Age) * (1.0 - smoothstep(4.5, 5.8, Age)) * live : 0.0;
ss = float2(0.5, 0.28) + fx.Rot((ss - float2(0.5, 0.28)) * float2(AR, 1.0), twitch * 0.05) / float2(AR, 1.0);
if (panel == 1) ss.x += sin(Age * 95.0) * 0.0022 * (1.0 - smoothstep(0.25, 0.9, Age)) * live;   // it buzzes with BP_RoomAudio's buzz
float near3 = panel == 3 ? 0.05 * (step(4.32, Age) + step(6.25, Age) + step(7.72, Age)) : 0.0;
ss = float2(0.5, 0.62) + (ss - float2(0.5, 0.62)) / (1.0 + near3);
// the figure tears now and then (the Nightmare's slice glitch), always on the hook
float tearOn = panel == 4 ? 1.0 : panel == 3 ? step(0.82, fx.Noise(float2(floor(Age * 9.0), 3.0))) : 0.0;
float band = floor(ss.y * 70.0);
ss.x += tearOn * live * (fx.Hash(float2(band, floor(Age * 18.0))) - 0.5) * 0.022 * step(0.55, fx.Hash(float2(band, 7.0)));
float blurS = clamp(abs(dep.x - focus) * foc.z, 0.0, 3.5);
float4 ps = Texture2DSampleLevel(Plate, PlateSampler, ss, blurS);
float aS = ps.a * hasS * step(abs(ss.x - 0.5), 0.5) * step(abs(ss.y - 0.5), 0.5);
float shS = Texture2DSampleLevel(Plate, PlateSampler, ss + float2(-0.006, -0.012), 3.0).a * hasS;   // paper-cutout shadow
lum *= 1.0 - 0.45 * shS * (1.0 - aS);
lum = lerp(lum, lerp(ps.r, ps.b, light), aS);
lum *= 1.0 - 0.55 * saturate(aS * (1.0 - aS) * 4.0);       // inked rim where the plane's edge is
// ---- near cutout: curtains, books, the plant, the chandelier, nearest and fastest --------------------------------
float2 sn = PLANE(dep.y);
float blurN = clamp(abs(dep.y - focus) * foc.z, 0.0, 3.5);
float aN = Texture2DSampleLevel(Back, BackSampler, sn, max(blurN - 1.0, 0.0)).a * step(abs(sn.x - 0.5), 0.5) * step(abs(sn.y - 0.5), 0.5);
float shN = Texture2DSampleLevel(Back, BackSampler, sn + float2(-0.008, -0.014), 2.5).a;
lum *= 1.0 - 0.4 * shN * (1.0 - aN);
float4 pn = Texture2DSampleLevel(Plate, PlateSampler, sn, blurN);
lum = lerp(lum, lerp(pn.r, pn.b, light) * 0.82, aN);        // the near plane sits a little darker, as foreground does
// ---- etched shadows: fine hatching that rides each plane, boiling a little like a hand-drawn line -------------------
float2 hu = lerp(sb, lerp(ss, sn, aN), max(aS, aN));
float boil = fx.Hash(float2(floor(Age * 6.0), panel)) * 1.2 * live;
float hw = sin((hu.x * AR * 0.80 + hu.y * 0.60) * 880.0 + boil);
float hw2 = sin((hu.x * AR * -0.55 + hu.y * 0.83) * 880.0 - boil);
float shade = 1.0 - smoothstep(0.04, 0.5, lum);                          // engraving: darker tone, wider lines,
float l1 = saturate((hw - (0.95 - 0.7 * shade)) / 0.12);                   // and a cross-hatch in the deep shadow
float l2 = saturate((hw2 - (0.98 - 0.55 * shade)) / 0.12) * step(0.55, shade);
lum *= 1.0 - 0.42 * max(l1, l2) * saturate(shade * 1.6);
// ---- light: halation off the bright parts, a slow light leak, the exposure ----------------------------------------
float4 halo = Texture2DSampleLevel(Back, BackSampler, sb, 5.0);
float hl = lerp(halo.r, halo.b, light);
lum = lum * expo + hl * hl * 0.40 * expo;
float2 lp = panel == 0 ? float2(0.08, 0.20) : panel == 2 ? float2(0.52, -0.05) : panel == 3 ? float2(0.92, 0.25) : float2(0.5, 0.5);
lp += float2(sin(Age * 0.37), cos(Age * 0.29)) * 0.06;
float leak = exp(-dot((UV - lp) * float2(AR, 1.0), (UV - lp) * float2(AR, 1.0)) * 2.2) * foc.w * (0.65 + 0.35 * sin(Age * 0.9 + panel));
lum += leak * (0.6 + 0.4 * nc.b);
// ---- black sand in the air: three depths of grains, and a few out-of-focus grains passing close to the lens --------
float2 drift = pan * 2.0;
float2 g1 = fx.Grains(UV + drift * 0.3, 70.0, 0.035, 0.10, Age, 1.0);
float2 av = float2(UV.x * AR, UV.y);
// the finer grains are the noise pack's brightest specks (about 0.5 % of texels, like the procedural layer's density)
float sp2 = smoothstep(0.88, 0.98, Texture2DSampleLevel(Noise, NoiseSampler, (av + float2(drift.x * 0.8, -Age * 0.055)) * 3.2, 0).r);
float sp3 = smoothstep(0.90, 0.99, Texture2DSampleLevel(Noise, NoiseSampler, (av + float2(-drift.x * 0.2 + 0.31, -Age * 0.025)) * 5.5, 0).r);
float amount = panel == 0 ? 1.0 : panel == 2 ? 0.9 : panel == 4 ? 1.4 : 0.6;
float dark = saturate((g1.x * 0.9 + sp2 * 0.6 + sp3 * 0.45) * amount);
float glint = g1.y * smoothstep(0.25, 0.6, lum) * amount;
// the shirt and the figure shed sand from their lower edges
if (panel >= 2)
{
    float above = Texture2DSampleLevel(Plate, PlateSampler, ss - float2(0, 0.05 + frac(Age * 0.35) * 0.15), 2.0).a;
    float2 shed = fx.Grains(UV, 260.0, 0.22, 0.45, Age, 13.0);
    dark = saturate(dark + shed.x * above * (1.0 - aS));
}
lum = lum * (1.0 - dark * 0.85) + glint * 0.9;
// ---- the sand fronts: the frame forms out of grains and is eaten back into them ------------------------------------
float2 gw = fx.Grains(UV - wind * Age * 0.05, 160.0, 0.0, 0.55, Age, 21.0);
float frontBand = saturate(1.0 - abs(edgeOut) * 6.0) * step(0.001, tOut) + saturate(1.0 - abs(edgeIn) * 6.0) * (1.0 - tIn) * step(0.001, fin);
lum *= formed * (1.0 - eaten);
float ahead = saturate(1.0 + edgeOut * 5.0) * step(edgeOut, 0.0) * step(0.001, tOut) + saturate(1.0 + edgeIn * 5.0) * step(edgeIn, 0.0) * (1.0 - tIn) * step(0.001, fin);
lum *= 1.0 - 0.75 * ahead * smoothstep(0.58, 0.72, sandN);
lum = lum * (1.0 - gw.x * frontBand * 0.9) + gw.y * frontBand * 1.2;
// ---- grade: deep blacks, paper tooth, film grain, a breathing vignette, the lower third kept dark for the line -----
lum = saturate(lum);
lum = lum * lum * (3.0 - 2.0 * lum) * 0.35 + lum * 0.65;
float paper = Texture2DSampleLevel(Noise, NoiseSampler, av * 6.0 + 0.5, 0).g * 0.6 + nc.b * 0.4;
lum *= 0.90 + 0.10 * paper;
lum += (fx.Hash(UV * 1931.0 + frac(Age * 24.0) * 97.0) - 0.5) * 0.05;
float2 vg = (UV - 0.5) * float2(1.0, 0.85);
float breathe = 0.55 + 0.06 * sin(Age * 1.4) * live + 0.25 * (panel == 3 ? smoothstep(4.0, 9.0, Age) : 0.0);
lum = saturate(lum) * (1.0 - breathe * pow(saturate(length(vg) * 1.35), 2.2));
lum *= 1.0 - 0.5 * smoothstep(0.66, 0.97, UV.y);
// monochrome split tone: true black shadows, paper-warm highlights (the dream grade's warm key, kept very slight)
float3 tone = lum * lerp(float3(0.90, 0.91, 0.93), float3(0.97, 0.95, 0.90), saturate(lum));
#undef PLANE
return float4(pow(tone, 2.2), 1.0);
