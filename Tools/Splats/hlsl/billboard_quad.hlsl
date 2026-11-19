// MF_SplatBillboard 'Camera-facing quad': world offset of this corner. The quad faces the camera and stretches along
// its own screen motion over the shutter, so falling grains read as streaks. Cost control, all per vertex: Splat.w
// (density) keeps that share of the splats, each grown by density^-1/4 so the body stays covered (fewer, larger
// splats); a splat smaller than Splat.y pixels survives with probability true / floored area and is drawn at the
// floor (a continuous screen-size LOD: the same ink from a fraction of the pixels). Dropped splats collapse: no pixels.
float3 Ow = TransformLocalVectorToWorld(Parameters, Offset);
float keep = float((asuint(RadiusSeed.y) * 747796405u + 2891336453u) >> 8u) * (1.0 / 16777216.0);
float dens = Splat.w > 0.0 ? min(Splat.w, 1.0) : 1.0;
if (Look.x < 0.004 || keep >= dens) return Ow;                                       // invisible now, or thinned out
float3 Tw = any(OffsetPrev != 0.0) ? Ow - TransformLocalVectorToWorld(Parameters, OffsetPrev) : float3(0.0, 0.0, 0.0);
float3 R = ResolvedView.ViewToTranslatedWorld[0].xyz, Fw = ResolvedView.ViewToTranslatedWorld[2].xyz;
float3 C = GetTranslatedWorldPosition(Parameters) + Ow - ResolvedView.TranslatedWorldCameraOrigin;
float px = 2.0 * max(dot(C, Fw), 1.0) / (ResolvedView.ViewToClip[1][1] * ResolvedView.ViewSizeAndInvSize.y);  // 1 pixel in cm
float r0 = RadiusSeed.x * Splat.x * Look.y * rsqrt(sqrt(dens)) * length(TransformLocalVectorToWorld(Parameters, float3(1.0, 0.0, 0.0)));
float r = max(r0, Splat.y * px);
if (keep >= dens * r0 * r0 / (r * r)) return Ow;                                    // screen-size LOD under the floor
float3 v = Tw - Fw * dot(Tw, Fw);
float L = min(length(v), 40.0 * px);
float3 a1 = L > 0.05 * px ? v / length(v) : R;
float3 a2 = normalize(cross(Fw, a1));
return Ow + a1 * (Corner.x * (r + 0.5 * L) - 0.5 * L) + a2 * Corner.y * r;
