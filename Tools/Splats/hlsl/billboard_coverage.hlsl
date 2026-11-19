// MF_SplatBillboard 'Coverage': a streak spreads its grain's ink over the longer quad (energy-conserving, like a
// thin-lens bokeh disc). Thinned and floored splats are dropped whole by the quad, so survivors keep full opacity.
float3 Ow = TransformLocalVectorToWorld(Parameters, Offset);
float3 Tw = any(OffsetPrev != 0.0) ? Ow - TransformLocalVectorToWorld(Parameters, OffsetPrev) : float3(0.0, 0.0, 0.0);
float3 Fw = ResolvedView.ViewToTranslatedWorld[2].xyz;
float3 C = GetTranslatedWorldPosition(Parameters) + Ow - ResolvedView.TranslatedWorldCameraOrigin;
float px = 2.0 * max(dot(C, Fw), 1.0) / (ResolvedView.ViewToClip[1][1] * ResolvedView.ViewSizeAndInvSize.y);
float dens = Splat.w > 0.0 ? min(Splat.w, 1.0) : 1.0;
float r = max(RadiusSeed.x * Splat.x * Look.y * rsqrt(sqrt(dens)) * length(TransformLocalVectorToWorld(Parameters, float3(1.0, 0.0, 0.0))), Splat.y * px);
float L = min(length(Tw - Fw * dot(Tw, Fw)), 40.0 * px);
return r / (r + 0.5 * L);
