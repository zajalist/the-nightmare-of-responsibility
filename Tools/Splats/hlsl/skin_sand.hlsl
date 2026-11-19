// Rest-pose coordinates keep grains attached to skin while the character moves.
uint3 c = uint3(int3(floor(P * 7.0)));
uint h = c.x * 73856093u ^ c.y * 19349663u ^ c.z * 83492791u;
h = ((h >> 16u) ^ h) * 2246822519u;
h = ((h >> 13u) ^ h) * 3266489917u;
float grain = float(h >> 8u) * (1.0 / 16777216.0);
float phase = frac(Clock / 12.0);
float pulse = smoothstep(0.08, 0.32, phase) * (1.0 - smoothstep(0.58, 0.84, phase));
pulse = lerp(pulse, 0.18, saturate(ReduceMotion));
float force = saturate((Amount - 0.25) / 0.75);
float coverage = max(force, pulse * saturate(Amount * 4.0));
float islands = 0.5 + 0.22 * sin(P.x * 0.12 + P.z * 0.09) + 0.22 * sin(P.y * 0.18 - P.z * 0.07);
float mask = smoothstep(islands - 0.13, islands + 0.13, coverage);
mask = Amount <= 0.0 ? 0.0 : (Amount >= 0.999 ? 1.0 : mask);
float edge = saturate(mask * 1.08 - grain * 0.08);
edge = Transition > 0.5 ? (Amount <= 0.0 ? 0.0 : (Amount >= 1.0 ? 1.0 : step(grain, Amount))) : edge;
float tone = 0.0018 + grain * 0.0032;
return float4(tone.xxx, edge);
