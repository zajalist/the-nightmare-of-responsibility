// M_SandSpill 'Feather' (pixel, opacity mask): the spill thins to nothing at its rim as loose grains: a 1.1 mm cell
// survives while the feather (VC = vertex alpha) beats its hash, so the edge becomes scattered grains and a dark
// contact band on the boards; along the floorboard gaps (Gap = gap axis yaw rad, plank pitch cm, offset cm, strength)
// the sand reaches further out. Masked, so the body stays opaque and depth-tested.
float2 gc = floor(WP.xy * 9.0);
float g = frac(sin(dot(gc, float2(12.9898, 78.233))) * 43758.5453);
float2 ax = float2(cos(Gap.x), sin(Gap.x));
float across = dot(WP.xy, float2(-ax.y, ax.x)) - Gap.z;
float d = abs(frac(across / max(Gap.y, 1.0) + 0.5) - 0.5) * Gap.y;                // cm to the nearest gap
float gap = Gap.w * (1.0 - smoothstep(0.08, 0.3, d));
return step(g, saturate(VC * (1.0 + 5.0 * gap)));
