// CPD: local phase, region exclusion, instance seed, ground Z; building ID is CPD4.
float phase = saturate(Local.x);
float distanceToHit = length(Rest.xy - Centre.xy);
if (Radius > 0 && distanceToHit < Radius && Local.y < 0.5 &&
    (Target < 0 || abs(Building - Target) < 0.5))
    phase = max(phase, saturate(Progress * 1.4 - distanceToHit / Radius * 0.4));
float seed = frac(RS.y + Local.z * 0.618034);
float q = saturate((phase - seed * 0.18) / 0.82);
float fall = q * q;
float3 drift = 0;
float breath = 0;
// Impact.xy is the immutable hit centre, z the game-time stamp, w strength.
// The trailing band has zero value and slope at both edges. It amplifies the
// continuous dream carrier rather than dropping buildings into a floor pile.
float age = Clock - Impact.z;
float waveDistance = length(Rest.xy - Impact.xy);
float band = saturate((age * SHOCK_SPEED - waveDistance) / SHOCK_BAND);
float pulse = 16 * band * band * (1 - band) * (1 - band);
float envelope = smoothstep(0, SHOCK_FADE_IN, age) *
                 (1 - smoothstep(SHOCK_DURATION - SHOCK_FADE_OUT, SHOCK_DURATION, age));
float shock = saturate(Impact.w) * pulse * envelope;
// Ground splat tiles explicitly opt in with building ID -2. Existing building
// feet stay anchored over their first 80cm; excluded primitives stay still.
float isGround = Building < -1.5 ? 1 : 0;
float anchor = (Local.y < 0.5 ? 1 : 0) * (1 - saturate(ReduceMotion)) *
               lerp(smoothstep(0, 80, max(Rest.z - Local.w, 0)), 1, isGround);
float amplitude = max(Ambient, 0) * 2.5 + shock * 35;
if (amplitude > 0)
{
    // World-space phase is shared by nearby grains: surfaces sway coherently.
    float p = dot(Rest.xy, float2(0.0011, 0.0007));
    float3 carrier = sin(float3(Clock * 0.72 + p, Clock * 0.91 + p * 0.83 + 1.4,
                               Clock * 0.63 + p * 0.71 + 0.6));
    drift = carrier * amplitude * anchor;
    // Small ground crests preserve wheel readability; physical road collision stays flat.
    drift.z = lerp(drift.z, (max(Ambient, 0) * 2.5 * carrier.z +
                          shock * 12 * (0.5 + 0.5 * carrier.z)) * anchor, isGround);
    breath = anchor * max(Ambient, 0) * carrier.y * 0.006;
}
float2 scatter = float2(frac(seed * 17.13), frac(seed * 31.71)) * 2 - 1;
float ground = min(Rest.z, Local.w + 2 + seed * 5);
float3 offset = drift * (1 - q) + float3(scatter * (12 + Radius * 0.035) * q,
                      (ground - Rest.z) * fall);
offset += CornerOffset * (breath * (1 - q) - q * 0.65);
// shortcut: analytical floor pile, use collision-aware particles only if uneven floors need contact.
return float4(offset, q);
