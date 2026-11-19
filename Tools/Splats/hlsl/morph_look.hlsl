// MF_SplatMorph 'Morph look' (vertex): (opacity, size, smoke, packed shading normal) for the morph, same timeline as
// 'Morph'. Grains in flight are a little smaller; the formed object's normal is the ray from its centre (reads its
// silhouette in light), the sand row's is straight up. Packed octahedral 12 + 12 bits like FFlow.PackN.
float W = Cfg.y;
float2 cell = float2(fmod(Idx, W), floor(Idx / W));
float2 scale = float2(1.0 / W, 1.0 / (W * Cfg.x));
float3 A = Texture2DSampleLevel(Tex, TexSampler, (cell + float2(0.0, Ev.x * W) + 0.5) * scale, 0).xyz * 100.0;
float3 B = Texture2DSampleLevel(Tex, TexSampler, (cell + float2(0.0, Ev.y * W) + 0.5) * scale, 0).xyz * 100.0;
float life = Ev.w > 0.0 ? saturate((Clock - Ev.z) / Ev.w) : 1.0;
float s = smoothstep(0.2, 0.8, life);
float3 c = lerp(A, B, s);
float3 n = lerp(float3(0.0, 0.0, 1.0), normalize(c - float3(0.0, 0.0, 0.5 * Cfg.z) + 1e-3), saturate(c.z / max(0.15 * Cfg.z, 1.0)));
n /= abs(n.x) + abs(n.y) + abs(n.z) + 1e-6;
float2 e = n.z >= 0.0 ? n.xy : (1.0 - abs(n.yx)) * (step(0.0, n.xy) * 2.0 - 1.0);
e = floor(saturate(e * 0.5 + 0.5) * 4095.0 + 0.5);
return float4(1.0, lerp(1.0, 0.75, sin(3.14159 * s)), 0.0, 1.0 + e.x * 4096.0 + e.y);
