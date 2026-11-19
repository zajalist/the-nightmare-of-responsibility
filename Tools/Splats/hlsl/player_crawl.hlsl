// M_SplatMesh 'Player crawl' (vertex, added to the billboard's WPO): sand that the player stands in goes into them.
// PlayerPos = MPC_Dream (feet world position, W = influence radius cm; the player lane writes it at 30 Hz). Within W,
// the surface dents under the feet and rings outward, and a share of the grains (more the closer they are) run to the
// feet and climb the legs, ending inside the body where they are hidden, then start over from their rest spot. Stateless.
float3 P = GetTranslatedWorldPosition(Parameters) + TransformLocalVectorToWorld(Parameters, Offset);
float3 Fp = PlayerPos.xyz + WSHackToFloat(GetPreViewTranslation(Parameters));
float2 d = Fp.xy - P.xy;
float dist = length(d);
if (PlayerPos.w <= 0.0 || dist > PlayerPos.w || abs(Fp.z - P.z) > 60.0) return float3(0.0, 0.0, 0.0);
float near = 1.0 - dist / PlayerPos.w;
float hz = float((asuint(RadiusSeed.y) * 2654435761u) >> 8u) * (1.0 / 16777216.0);
float3 o = float3(0.0, 0.0, -2.0 * smoothstep(0.6, 1.0, near) + 0.6 * sin(dist * 0.35 - Time * 5.0) * near * near);
if (hz < 0.55 * near * near)
{
    float ph = frac(Time * lerp(0.2, 0.45, hz) + hz * 7.3);
    float run = smoothstep(0.0, 0.55, ph), climb = smoothstep(0.45, 1.0, ph);
    float2 side = float2(-d.y, d.x) / max(dist, 1e-3) * (frac(hz * 97.0) - 0.5) * 16.0;   // left or right leg
    o = float3((d + side * run) * run, (Fp.z - P.z) * run + 50.0 * climb * climb);
}
return o;
