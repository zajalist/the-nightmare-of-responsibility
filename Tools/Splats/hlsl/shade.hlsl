// M_SplatMesh 'Shade splat' (vertex): pitch-black goo, read only through light. The material is DefaultLit with
// albedo Sand.x, so the moon, lamps and light shafts light it and their shadows leave it void black. This node picks
// each splat's shading normal and roughness, packed as float4(N * sqrt(roughness), opacity) so one interpolator
// carries both (the pixel takes Normalize and Dot). The normal is the surface's (mesh rest normal, a strand's or the
// pour's cross-section, an object's centre ray: FFlow.PackN), jittered per splat by Sand.w so light breaks into dense,
// dim, grain-sized highlights. A rare Sand.y share are near-mirror glints whose normals wobble: they flash only where
// light falls. Sand.z = goo roughness.
uint x = asuint(RadiusSeed.y) * 747796405u + 2891336453u;
x = ((x >> ((x >> 28u) + 4u)) ^ x) * 277803737u;
x ^= x >> 22u;
float4 h = float4(x & 255u, (x >> 8u) & 255u, (x >> 16u) & 255u, x >> 24u) / 255.0;
float3 n = Parameters.TangentToWorld[2];                                             // mesh rest normal
if (Look.w >= 1.0)                                                                  // the flow's own normal
{
    float v = Look.w - 1.0, a = floor(v / 4096.0);
    float2 e = float2(a, v - a * 4096.0) / 4095.0 * 2.0 - 1.0;
    float3 m = float3(e, 1.0 - abs(e.x) - abs(e.y));
    if (m.z < 0.0) m.xy = (1.0 - abs(m.yx)) * (step(0.0, m.xy) * 2.0 - 1.0);
    n = normalize(TransformLocalVectorToWorld(Parameters, m));
}
float glint = step(h.x, Sand.y);
float w = Time * lerp(2.0, 5.0, h.z) + h.w * 6.2832;
float3 j = lerp((h.yzw * 2.0 - 1.0) * Sand.w, float3(sin(w), cos(w * 1.31), sin(w * 0.73)) * 0.7, glint);
float rough = lerp(Sand.z * lerp(0.75, 1.35, h.y), 0.07, glint);
return float4(normalize(n + j) * sqrt(rough), saturate(Opacity * Look.x * Coverage));
