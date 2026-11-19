// M_SandSpill 'Grain' (pixel): fine black sand read only through light (Journey's sand recipe), never repeating, slowly
// alive, textured at every distance, and cheap: the grain is baked in T_SandGrain (Tex: R, G grain tilt at 1.1 mm,
// B smooth clumps, A glint mask; make_sand_grain_tex.py), sampled on two incommensurate tilings (28 cm, and 31 cm
// turned 37 deg) so its 28 cm repeat never lines up, plus once at an 18 m tile for patch-scale variation. Texture filtering and
// mips do the per-octave fading (no LOD line, no square texels); what the mips average away goes into the roughness
// as normal variance (Toksvig). Glints are pin-points that only exist where real light falls; wet strands (VC.g, not on
// plain white vertex colour) are smoother. Distortion: the two tilings drift along a slow flow (out from the spill's
// centre O, turned by the macro noise), strongest at the rim and on strands, half a cycle apart and crossfaded so
// nothing visibly resets; now and then a 4 cm band slips sideways for a third of a second (time-shift). Per actor the
// lattice is turned and shifted by a hash of the object's position. The goo has no specular of its own; four things
// catch light, and all of them face the moon (Rim = its side), so they show where the moonbeam falls and the body
// stays pitch black elsewhere (the unshadowed sand rim light finds nothing to mirror):
//   grain  a continuous, very low specular (Sheen.z) on the grain normals, modulated by the grain itself: the lit
//          patch reads as a granular surface
//   points one candidate per cell (2.5-5 px, power-of-two sizes so nothing swims), jittered inside it, round and
//          soft, sub-pixel to 2 px and mostly tiny; a Sheen.x share is lit at a time, each re-rolling at its own
//          phase ~0.7 times a second; Specular Sheen.y, roughness 0.3
//   glints the brightest tenth of the lit points: Specular 1, roughness 0.06, a crisp point
//   rim    the feathered edge (vertex alpha) and silhouettes turned away from the eye, half turned to the moon,
//          Specular Sheen.w
// Returns float4(N * sqrt(roughness), specular): the graph masks rgb for Normalize and Dot, a for Specular.
// Spill = (albedo, -, roughness, grain tilt); Sheen = (point share, point specular, grain specular, rim specular);
// T = s; O = pivot; V = camera vector; Rim = the moon side (world position); VA = vertex alpha (the feather).
struct FSG   // integer hash (pcg): no sin, so arguments that grow with time or distance keep hashing evenly
{
    float H(float n)
    {
        uint x = asuint(n) * 747796405u + 2891336453u;
        x = ((x >> ((x >> 28u) + 4u)) ^ x) * 277803737u;
        return float((x >> 22u) ^ x) * (1.0 / 4294967296.0);
    }
};
FSG sg;
float3 ho = frac(sin(float3(dot(floor(O.xy), float2(12.99, 78.23)), dot(floor(O.xy), float2(39.35, 11.13)), dot(floor(O.xy), float2(73.16, 52.71)))) * 43758.55);
float ra = ho.x * 6.2832, cr = cos(ra), sr = sin(ra);
float2 q = WP.xy - O.xy;
q = float2(q.x * cr - q.y * sr, q.x * sr + q.y * cr);
float mb = Texture2DSample(Tex, TexSampler, q / 1800.0 + ho.yz).b;                  // macro: ~0.3-1 m patches of character
float wet = VC.g * (1.0 - VC.b);
float2 dir = normalize(q + 1e-3);
float a = (mb - 0.5) * 2.5;
dir = float2(dir.x * cos(a) - dir.y * sin(a), dir.x * sin(a) + dir.y * cos(a));
float amt = 1.2 * (1.0 - 0.6 * saturate(VC.r) + wet);
float ph = T * 0.05, fa = frac(ph), fb = frac(ph + 0.5), w = abs(2.0 * fa - 1.0);
float tick = fmod(floor(T * 3.0), 4096.0), band = floor(q.x / 4.0);
float slip = step(sg.H(band * 12.9898 + tick * 78.233), 0.015) * (sg.H(band * 39.35 + tick * 11.13 + 0.5) - 0.5) * 4.0;
float2 qa = q - dir * fa * amt + float2(0.0, slip), qb = q - dir * fb * amt + float2(0.0, slip);
float2 qb37 = float2(qb.x * 0.7986 - qb.y * 0.6018, qb.x * 0.6018 + qb.y * 0.7986);
float4 sa = Texture2DSample(Tex, TexSampler, qa / 28.16);
float4 sb = Texture2DSample(Tex, TexSampler, qb37 / 31.0 + 0.37);
float4 s = lerp(sa, sb, w);
float px = length(fwidth(q));                                                       // cm per pixel here
float k1 = 1.0 - smoothstep(0.28, 1.1, px * 9.0);                                 // grains resolved
float k2 = 1.0 - smoothstep(0.28, 1.1, px * 2.3);                                 // clumps resolved
float tilt = Spill.w * lerp(0.7, 1.3, mb) * saturate(VC.r + 0.35) * (1.0 - 0.7 * wet);
float3 j = float3(s.r - 0.5, s.g - 0.5, 0.0) * 2.0 * tilt + float3(s.b - 0.5, sa.b - sb.b, 0.0) * 0.8 * tilt;
float r0 = lerp(Spill.z + (mb - 0.5) * 0.15, 0.18, wet);
float var = tilt * tilt * (0.08 * (1.0 - k1) + 0.03 * (1.0 - k2));
float rg = sqrt(saturate(r0 * r0 + var));
float3 hm = normalize(normalize(Rim.xyz - WP) + V);                                 // the moon's mirror normal here
float3 ng = normalize(Nv + j);
float cs = 0.11 * exp2(ceil(log2(max(px * 2.5 / 0.11, 1.0))));                   // point cell, cm: 2.5-5 px
float2 cell = floor(q / cs);
float2 hp = float2(sg.H(dot(cell, float2(12.9898, 78.233))), sg.H(dot(cell, float2(39.35, 11.13))));
float ht = sg.H(dot(cell, float2(26.65, 91.17)) + fmod(floor(T * 0.7 + hp.x * 13.0), 4096.0) * 7.31);
float rad = lerp(0.35, 1.0, hp.y * hp.y * hp.y) * px;                              // point radius: mostly sub-pixel
float pt = step(ht, Sheen.x) * (1.0 - smoothstep(rad * 0.35, rad, length(q - (cell + 0.25 + 0.5 * hp) * cs))) * (1.0 - wet);
float glint = pt * step(ht, Sheen.x * 0.1);
float rim = max(smoothstep(0.3, 0.08, saturate(dot(Nv, V))), smoothstep(0.9, 0.35, VA)) * saturate(VC.r + 0.3);
float grain = Sheen.z * saturate(0.6 + 1.6 * (s.r - 0.5) + 0.8 * (s.b - 0.5));
float spec = max(max(pt * Sheen.y, glint), max(rim * Sheen.w, grain));
float3 n = glint > 0.5 ? hm : pt > 0.02 ? normalize(lerp(ng, hm, pt)) : rim > 0.05 ? normalize(lerp(ng, hm, 0.5 * rim)) : ng;
float rough = glint > 0.5 ? 0.06 : pt > 0.02 ? lerp(rg, 0.3, pt) : rim > 0.05 ? lerp(rg, 0.3, rim) : rg;
return float4(n * sqrt(rough), spec);
