// M_SandSpill 'Rim' (pixel, emissive): the ferrofluid lesson: the void-black body shows itself where a key light
// (Rim = world position, intensity) runs up its edges and strands as a thin Fresnel rim; edges turned away stay black.
float3 Ld = Rim.xyz - WP;
float d2 = dot(Ld, Ld);
float3 L = Ld * rsqrt(max(d2, 1.0));
float fr = pow(1.0 - saturate(dot(N, V)), 5.0);
return (0.025 * Rim.w * fr * saturate(dot(N, L) + 0.2) * (0.5 + 0.5 * VC.g) * saturate(VC.r + 0.3) / (1.0 + d2 * 1e-4)).xxx;
