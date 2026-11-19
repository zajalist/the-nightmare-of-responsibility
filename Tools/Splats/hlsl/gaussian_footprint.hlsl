// MF_SplatGaussian 'Gaussian footprint': exp(-k r^2) windowed to exactly 0 at the quad rim (no square edges), so
// the card is already clipped to the splat's support. k = Splat.z (hardness); dust (Smoke) is a little softer.
float k = Splat.z * lerp(1.0, 0.8, Smoke);
float e = exp(-k);
return Alpha * max((exp(-k * dot(Corner, Corner)) - e) / (1.0 - e), 0.0);
