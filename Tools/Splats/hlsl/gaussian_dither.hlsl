// MF_SplatGaussian 'Seeded dither': stochastic alpha for Masked instances (objects that must hide their own back,
// like the clock), resolved by TSR. The per-splat seed decorrelates overlapping splats so their coverage adds up
// (the built-in DitherTemporalAA gives every splat the same pattern, so overlaps would mask the same pixels).
return Opacity > InterleavedGradientNoise(Parameters.SvPosition.xy + RadiusSeed.y * 117.0, View.StateFrameIndexMod8) ? 1.0 : 0.0;
