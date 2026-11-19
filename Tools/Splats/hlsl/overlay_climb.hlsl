// M_SandOverlay 'Climb' (pixel, opacity mask): sand that the player stood in climbs them. Black grains cover the body
// from the feet (MPC_Dream PlayerPos.z) up to Amount x 55 cm (1 = knees, 2 = waist): dense at the feet, thinning in
// 1.1 mm grain cells towards a ragged top edge. Amount 0 = no overlay pixels at all.
float h = WP.z - PlayerPos.z;
float top = Amount * 55.0;
float2 gc = floor(float2(WP.x + WP.y, WP.z) * 0.9);
float g = frac(sin(dot(gc, float2(12.9898, 78.233))) * 43758.5453);
float cover = saturate((top - h) / max(top * 0.4, 4.0));
return Amount > 0.0 ? step(g, cover * 0.92) : 0.0;
