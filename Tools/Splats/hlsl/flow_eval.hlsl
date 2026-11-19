// MF_SplatFlow 'Motion' = flow_lib.hlsl + this. Returns the splat centre's displacement from rest (mesh-local cm) and
// fills two more outputs: OffsetPrev, the displacement one shutter ago (motion streaks; 0 when TimeCfg.z <= 0), and Look
// = (opacity, size, smoke, packed shading normal, see FFlow.PackN). One [loop] body serves both times, so the behaviour
// code is compiled once instead of three times (offset now, offset one shutter ago, look).
float e = (kind >= 5 && kind <= 7) ? f.DissolveE(RestPos, h, dv) : 0.0;          // crumble amount; no time in it
float3 now = 0.0;
float4 L = float4(1.0, 1.0, 0.0, 1.0);
OffsetPrev = 0.0;
int passes = TimeCfg.z > 0.0 ? 2 : 1;                                                // streaks off: one evaluation
[loop] for (int pass = 0; pass < passes; pass++)
{
    float t = f.Stutter((Clock - pass * TimeCfg.z) * TimeCfg.x + TimeCfg.y, h, G);   // dream time; pass 1 rewinds one shutter
    float4 lk = float4(1.0, 1.0, 0.0, 1.0);                                          // static object: its own colour
    float3 o = 0.0;
    fade = 1.0; age = 0.0; look = float4(1.0, 1.0, 0.0, 0.0); cq = 0.0; ca = 0.0;
    if (kind == 0) { o = f.Stream(RestPos, h, role, u, t, TimeCfg.w, Flow, Shape, Place, Tune, fade, cq, ca); lk = float4(fade, 1.0, 0.0, 0.0); }
    else if (kind == 1)
    {
        o = f.Dust(RestPos, h, u, t, TimeCfg.w, Flow, age, cq, ca);
        lk = float4((h.x < 0.25 ? 0.32 : 0.0) * smoothstep(0.0, 0.1, age) * pow(1.0 - age, 1.5), lerp(1.0, 2.0, sqrt(age)), 0.5, 0.0);  // goo barely dusts
    }
    else if (kind == 2) { o = f.Saltation(RestPos, h, u, t, TimeCfg.w, Flow.xyz, Shape, Place, 0.0, fade); lk = float4(fade * (1.0 - calm), 1.0, 0.0, 0.0); }
    else if (kind == 3) { o = f.Strand(RestPos, h, u, t, TimeCfg.w, Flow, Shape, Place, 0.0, Tune.z * (1.0 - calm), look, cq, ca); lk = look; }
    else if (kind == 4)
    {
        o = f.Avalanche(RestPos, h, u, t, TimeCfg.w * (isStream ? 1.5 : 1.0), (isStream ? 2.5 : (role < 0.5 ? Tune.x : 0.0)) * (1.0 - calm),
                        (isStream ? 0.15 : Tune.y) * (1.0 - calm), Shape, Place, isStream ? -Tune.x : 0.0, fade);  // pile, mound or sparkle grains
        lk = float4(fade, 1.0, 0.0, 0.0);
    }
    else if (kind == 5) { o = f.Assemble(RestPos, h, t, TimeCfg.w, Flow, Shape, Place, Tune, look, cq, ca); lk = look; }
    else if (kind == 6) { o = f.Gallop(RestPos, h, t, TimeCfg.w, Flow, Tune, look, cq, ca); lk = look; }
    else if (kind == 8) { o = f.Burst(RestPos, h, role, Clock, Ev, Flow, Tune, look, cq, ca); lk = look; }
    else if (kind == 9) { o = f.Drift(RestPos, h, u, t, TimeCfg.w, Flow, look, cq, ca); lk = look * float4(1.0 - calm, 1.0, 1.0, 1.0); }
    else if (kind == 10) { o = f.Bloom(RestPos, h, role, u, Clock, Ev, Flow, Shape, Place, Tune, look, cq, ca); lk = look; }
    if (isMound && Ev.z > 0.0 && Clock >= Ev.y && Clock < Ev.y + Ev.z)              // Erupt: ballistic launch, lands, slides home
    {
        float a = 0.8 * (Clock - Ev.y), back = 1.0 - smoothstep(0.55, 1.0, (Clock - Ev.y) / Ev.z);
        float2 rel = RestPos.xy - Place.xy;
        float rr = saturate(length(rel) / (50.0 * Place.z));
        float vz = Ev.x * lerp(60.0, 220.0, h.x * h.x) * (1.0 - 0.6 * rr), vr = Ev.x * lerp(10.0, 70.0, h.y);
        o += float3(rel / max(length(rel), 1e-3) * vr * (1.0 - exp(-2.5 * a)) / 2.5, max(vz * a - 490.0 * a * a, 0.0)) * back;
        cq = (RestPos + o) * 0.05 + float3(0.0, 0.0, Clock * 0.4);
        ca = max(ca, Flow.w * Ev.x * back);
    }
    if (e > 0.0)                                                                     // crumble: fall, scatter, swirl
    {
        float s = 0.8 * e;
        float3 q = RestPos + o;
        q.z = max(q.z - 490.0 * s * s, 0.5);
        q.xy += normalize(h.xy - 0.5 + 1e-3) * 25.0 * e;
        o = q - RestPos;
        cq = q * 0.05 + float3(0.0, 0.0, t * 0.3);
        ca = max(ca, 2.0 * Flow.w * e);
    }
    if (any(ca != 0.0)) o += f.Curl(cq) * ca;                                        // one curl-noise sample per splat
    if (G > 0.0)                 // glitch: vertical slip columns (the post's slip direction), sideways slip rows, teleports, pixel steps
    {
        float tick = floor(Clock * 8.0), col = floor(RestPos.x / 3.0), row = floor(RestPos.z / 2.0);
        o.z += step(f.H1(col * 3.1 + tick * 1.7), 0.15 * G) * (f.H1(col + tick) - 0.5) * 6.0;
        o.x += step(f.H1(row * 5.3 + tick * 2.3 + 7.0), 0.08 * G) * (f.H1(row + tick + 3.0) - 0.5) * 5.0;
        o += step(f.H1(h.z * 91.0 + tick), 0.08 * G) * (f.Hash(RadiusSeed.y + tick).xyz - 0.5) * 3.0;
        if (h.w < 0.6 * G) o = floor(o / 0.35 + 0.5) * 0.35;
    }
    if (pass == 0) { now = o; L = lk; }
    else OffsetPrev = o;
}
L.x *= 1.0 - step(f.H1(h.x * 37.0 + floor(Clock * 8.0)), 0.05 * G);                 // glitch: a grain blinks out for a beat
// Shading normal: a strand or a bloom carries its own; the pour its column's cross-section; an object (assembled,
// galloping or static) the ray from its centre at half its height Tune.z; everything else 0 = the mesh's rest normal.
float nw = (kind == 3 || kind == 10) ? L.w : kind == 0 ? f.PackN(float3((h.w - 0.5) * 1.2, RestPos.y, 0.3))
         : (kind >= 5 && kind <= 7) ? f.PackN(RestPos - float3(0.0, 0.0, 0.5 * Tune.z)) : 0.0;
Look = float4(L.x * (1.0 - smoothstep(0.7, 1.0, e)), L.y, L.z, nw);
return now;
