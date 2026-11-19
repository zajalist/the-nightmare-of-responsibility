// MF_SplatFlow 'Motion: look' = flow_lib.hlsl + this. Same timeline as the offset; returns (opacity, size, smoke,
// packed shading normal, see FFlow.PackN).
float t = f.Stutter(Clock * TimeCfg.x + TimeCfg.y, h, G);
float4 L = float4(1.0, 1.0, 0.0, 1.0);                                               // static object: its own colour
if (kind == 0) { f.Stream(RestPos, h, role, u, t, TimeCfg.w, Flow, Shape, Place, Tune, fade, cq, ca); L = float4(fade, 1.0, 0.0, 0.0); }
else if (kind == 1)
{
    f.Dust(RestPos, h, u, t, TimeCfg.w, Flow, age, cq, ca);
    L = float4((h.x < 0.25 ? 0.32 : 0.0) * smoothstep(0.0, 0.1, age) * pow(1.0 - age, 1.5), lerp(1.0, 2.0, sqrt(age)), 0.5, 0.0);  // goo barely dusts: a quarter of the grains, the rest cost nothing
}
else if (kind == 2) { f.Saltation(RestPos, h, u, t, TimeCfg.w, Flow.xyz, Shape, Place, 0.0, fade); L = float4(fade * (1.0 - calm), 1.0, 0.0, 0.0); }
else if (kind == 3)
{
    f.Strand(RestPos, h, u, t, TimeCfg.w, Flow, Shape, Place, 0.0, Tune.z * (1.0 - calm), look, cq, ca);
    L = look;
}
else if (kind == 4)
{
    f.Avalanche(RestPos, h, u, t, TimeCfg.w * (isStream ? 1.5 : 1.0), (isStream ? 2.5 : (role < 0.5 ? Tune.x : 0.0)) * (1.0 - calm),
                (isStream ? 0.15 : Tune.y) * (1.0 - calm), Shape, Place, isStream ? -Tune.x : 0.0, fade);
    L = float4(fade, 1.0, 0.0, 0.0);
}
else if (kind == 5) { f.Assemble(RestPos, h, t, TimeCfg.w, Flow, Shape, Place, Tune, look, cq, ca); L = look; }
else if (kind == 6) { f.Gallop(RestPos, h, t, TimeCfg.w, Flow, Tune, look, cq, ca); L = look; }
else if (kind == 8) { f.Burst(RestPos, h, role, Clock, Ev, Flow, Tune, look, cq, ca); L = look; }
else if (kind == 9) { f.Drift(RestPos, h, u, t, TimeCfg.w, Flow, look, cq, ca); L = look * float4(1.0 - calm, 1.0, 1.0, 1.0); }
else if (kind == 10) { f.Bloom(RestPos, h, role, u, Clock, Ev, Flow, Shape, Place, Tune, look, cq, ca); L = look; }
float e = (kind >= 5 && kind <= 7) ? f.DissolveE(RestPos, h, dv) : 0.0;
L.x *= 1.0 - step(f.H1(h.x * 37.0 + floor(Clock * 8.0)), 0.05 * G);                 // glitch: a grain blinks out for a beat
// Shading normal: a strand or a bloom carries its own; the pour its column's cross-section; an object (assembled,
// galloping or static) the ray from its centre at half its height Tune.z, which reads its silhouette in light;
// everything else 0 = the mesh's rest normal (mound surface, pile, grains).
float nw = (kind == 3 || kind == 10) ? L.w : kind == 0 ? f.PackN(float3((h.w - 0.5) * 1.2, RestPos.y, 0.3))
         : (kind >= 5 && kind <= 7) ? f.PackN(RestPos - float3(0.0, 0.0, 0.5 * Tune.z)) : 0.0;
return float4(L.x * (1.0 - smoothstep(0.7, 1.0, e)), L.y, L.z, nw);
