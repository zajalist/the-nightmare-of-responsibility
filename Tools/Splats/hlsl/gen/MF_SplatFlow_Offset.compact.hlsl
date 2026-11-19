// MF_SplatFlow_Offset - compact copy; documented source: Tools/Splats/hlsl/flow_lib.hlsl + flow_offset.hlsl (offline check: check_hlsl.py)
struct FFlow
{
float4 Hash(float s)
{
uint b = asuint(s);
uint4 v = uint4(b, b ^ 0x9E3779B9u, b * 747796405u, b + 2891336453u) * 1664525u + 1013904223u;
v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
v ^= v >> 16u;
v.x += v.y * v.w; v.y += v.z * v.x; v.z += v.x * v.y; v.w += v.y * v.z;
return float4(v >> 8u) * (1.0 / 16777216.0);
}
float H1(float n)
{
uint x = asuint(n) * 747796405u + 2891336453u;
x = ((x >> ((x >> 28u) + 4u)) ^ x) * 277803737u;
return float((x >> 22u) ^ x) * (1.0 / 4294967296.0);
}
float VN(float x) { float i = floor(x), f = frac(x); return lerp(H1(i), H1(i + 1.0), f * f * (3.0 - 2.0 * f)); }
float3 G3(float3 p)
{
uint3 v = asuint(p) * 1664525u + 1013904223u;
v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
v ^= v >> 16u;
v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
return float3(v >> 8u) * (2.0 / 16777216.0) - 1.0;
}
float3 NoiseGrad(float3 x)
{
float3 i = floor(x), f = frac(x);
float3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0), du = 30.0 * f * f * (f * (f - 2.0) + 1.0);
float3 ga = G3(i), gb = G3(i + float3(1, 0, 0)), gc = G3(i + float3(0, 1, 0)), gd = G3(i + float3(1, 1, 0));
float3 ge = G3(i + float3(0, 0, 1)), gf = G3(i + float3(1, 0, 1)), gg = G3(i + float3(0, 1, 1)), gh = G3(i + float3(1, 1, 1));
float va = dot(ga, f), vb = dot(gb, f - float3(1, 0, 0)), vc = dot(gc, f - float3(0, 1, 0)), vd = dot(gd, f - float3(1, 1, 0));
float ve = dot(ge, f - float3(0, 0, 1)), vf = dot(gf, f - float3(1, 0, 1)), vg = dot(gg, f - float3(0, 1, 1)), vh = dot(gh, f - float3(1, 1, 1));
return ga + u.x * (gb - ga) + u.y * (gc - ga) + u.z * (ge - ga) + u.x * u.y * (ga - gb - gc + gd)
+ u.y * u.z * (ga - gc - ge + gg) + u.z * u.x * (ga - gb - ge + gf) + u.x * u.y * u.z * (-ga + gb + gc - gd + ge - gf - gg + gh)
+ du * (float3(vb - va, vc - va, ve - va) + u.yzx * float3(va - vb - vc + vd, va - vc - ve + vg, va - vb - ve + vf)
+ u.zxy * float3(va - vb - ve + vf, va - vb - vc + vd, va - vc - ve + vg) + u.yzx * u.zxy * (-va + vb + vc - vd + ve - vf - vg + vh));
}
float3 Curl(float3 p) { return cross(NoiseGrad(p), NoiseGrad(p + float3(31.416, -17.3, 9.27))); }
float PackN(float3 n)
{
n /= abs(n.x) + abs(n.y) + abs(n.z) + 1e-6;
float2 e = n.z >= 0.0 ? n.xy : (1.0 - abs(n.yx)) * (step(0.0, n.xy) * 2.0 - 1.0);
e = floor(saturate(e * 0.5 + 0.5) * 4095.0 + 0.5);
return 1.0 + e.x * 4096.0 + e.y;
}
float Mound(float2 q, float4 S)
{
float a = atan2(q.y, q.x), w = sin(4.0 * a + S.w);
float t = length(q) / (50.0 * (1.0 + 0.12 * sin(3.0 * a + S.y) + 0.08 * sin(5.0 * a + S.z)));
float h = 24.0 * pow(saturate(1.0 - t), 1.6) * (1.0 + 0.15 * w * t);
return t < 1.0 / 14.0 ? lerp(S.x, 24.0 * pow(13.0 / 14.0, 1.6) * (1.0 + 0.15 * w / 14.0), t * 14.0) : h;
}
float Ground(float2 p, float4 S, float4 P, float zb)
{
float2 d = p - P.xy;
float c = cos(P.w), s = sin(P.w);
return Mound(float2(c * d.x - s * d.y, s * d.x + c * d.y) / P.z, S) * P.z + zb;
}
float3 Normal(float2 p, float4 S, float4 P, float zb)
{
float e = 0.35 * P.z + 0.05;
float hx = Ground(p + float2(e, 0.0), S, P, zb) - Ground(p - float2(e, 0.0), S, P, zb);
float hy = Ground(p + float2(0.0, e), S, P, zb) - Ground(p - float2(0.0, e), S, P, zb);
return normalize(float3(-hx, -hy, 2.0 * e));
}
float3 Avalanche(float3 c, float4 h, float u, float t, float T, float speed, float breath, float4 S, float4 P, float zb, out float fade)
{
float2 rel = c.xy - P.xy;
float rr = saturate(length(rel) / (50.0 * P.z));
float tg = atan2(rel.y, rel.x) * 1.75 + 3.1;
float x = t / (T * lerp(0.85, 1.15, VN(tg * 0.5 + 8.0))) + VN(tg) * 0.75 + u * 0.25 + rr * 0.35;
float age = frac(x);
float run = step(0.2, H1(floor(tg) * 7.13 + floor(x) * 1.37)) * step(0.001, speed);
float3 n = Normal(c.xy, S, P, zb);
float d = speed * T * 0.5 * run * smoothstep(0.0, 0.55, age) * saturate(length(n.xy) / n.z * 1.6) * saturate((1.12 - rr) * 5.0);
float b = breath * (0.6 * sin(6.2832 * t / 5.5 - rr * 2.4 + VN(tg * 0.6) * 2.0) + 0.4 * sin(t * 0.9 + tg * 1.3 + rr * 5.0)) * (1.0 - 0.5 * rr);
float2 p = c.xy + n.xy / max(length(n.xy), 1e-4) * d + rel / max(length(rel), 1e-3) * b * 0.8;
fade = lerp(1.0, smoothstep(0.0, 0.08, age) * (1.0 - smoothstep(0.9, 1.0, age)), run);
return float3(p, Ground(p, S, P, zb) + c.z - Ground(c.xy, S, P, zb)) + n * b - c;
}
float3 Saltation(float3 c, float4 h, float u, float t, float T, float3 wind, float4 S, float4 P, float zb, out float fade)
{
float Tl = T * 0.45 * lerp(0.7, 1.3, h.y);
float age = frac(t / Tl + u);
float2 w = normalize(wind.xy + float2(1e-3, 0.0)), sd = float2(-w.y, w.x);
float L = (length(wind.xy) * Tl + 6.0) * age * lerp(0.6, 1.4, h.z);
float along = dot(c.xy, w) + L, across = dot(c.xy, sd);
float snake = (VN(along * 0.09 + across * 0.25 - t * 0.35) - 0.5) * 7.0 + sin(along * 0.4 - t * 1.2) * 0.8;
float2 p = c.xy + w * L + sd * snake * smoothstep(0.0, 0.3, age);
float hop = abs(sin(3.14159 * (2.0 + floor(h.w * 4.0)) * age)) * lerp(0.05, 0.3, h.y * h.y) * (1.0 - age);
fade = smoothstep(0.0, 0.1, age) * (1.0 - smoothstep(0.75, 1.0, age));
return float3(p, Ground(p, S, P, zb) + 0.3 + hop) - c;
}
float3 Strand(float3 c, float4 h, float u, float t, float T, float4 F, float4 S, float4 P, float zb, float reach, out float4 look, out float3 cq, out float3 ca)
{
float id = H1(dot(floor(c.xy * 0.5), float2(1.0, 57.0)));
float Ts = T * lerp(0.8, 1.3, id), cyc = t / Ts + id * 7.0, ph = frac(cyc), k = floor(cyc);
float3 n = Normal(c.xy, S, P, zb);
float3 dir = normalize(n * 0.6 + float3(H1(id * 3.7) - 0.5, H1(id * 9.1) - 0.5, 0.9));
float stretch = smoothstep(0.0, 0.7, ph) * (1.0 - smoothstep(0.78, 0.86, ph));
float full = reach * lerp(0.6, 1.4, H1(id * 5.3 + k)), len = full * stretch;
float3 side = normalize(cross(dir, float3(0.0, 0.0, 1.0)) + 1e-3), up2 = cross(side, dir);
float a = h.x * 6.2832, thick = lerp(1.6, 0.5, u) + 1.4 * smoothstep(0.8, 1.0, u);
float3 rn = side * cos(a) + up2 * sin(a), ring = rn * sqrt(h.y);
float3 p = dir * len * u - float3(0.0, 0.0, 0.35 * len * sin(3.14159 * u) * u) + ring * thick * (0.4 + 0.6 * stretch);
if (u > 0.8 && ph > 0.82 && H1(id * 11.0 + k) < 0.4)
{
float fallT = (ph - 0.82) * Ts;
float3 q = dir * full * 0.95 + ring * 1.2 - float3(0.0, 0.0, 73.5 * fallT * fallT);
q.z = max(q.z, Ground((c + q).xy, S, P, zb) - c.z + 0.3);
p = lerp(q, p, smoothstep(0.93, 1.0, ph));
}
cq = (c + p) * 0.04 + float3(0.0, 0.0, t * 0.12);
ca = F.w * u * stretch;
look = float4(1.0, 1.0 + 0.4 * smoothstep(0.8, 1.0, u), 0.0, PackN(rn + dir * smoothstep(0.75, 1.0, u)));
return p;
}
float3 Stream(float3 c, float4 h, float role, float u, float t, float T, float4 F, float4 S, float4 P, float4 K, out float fade, out float3 cq, out float3 ca)
{
const float g = 980.0;
float zb = -K.x;
float Tf = sqrt(2.0 * max(c.z - Ground(P.xy, S, P, zb), 1.0) / g);
float Ts = K.z / max(K.y, 1.0);
float n = 19.0, tight = role < 0.5 ? lerp(0.3, 1.0, h.w * h.w) : 1.0;
float age = frac(t / T + (floor(u * n) + 0.5 + (frac(u * n) - 0.5) * tight) / n) * T;
float jx = (h.w - 0.5) * 1.2;
float3 p;
fade = 1.0;
cq = 0.0;
ca = 0.0;
if (age < Ts)
{
float s = age / Ts;
p = float3(-K.z * (1.0 - s) + jx, c.y * lerp(2.2, 1.0, s), c.z + K.w * pow(1.0 - s, 1.9));
fade = smoothstep(0.0, 0.2, s);
}
else
{
float tau = min(age - Ts, Tf);
float neck = max(sqrt(K.y / sqrt(K.y * K.y + g * g * tau * tau)), 0.3);
float fd = 0.5 * g * tau * tau, bead = 1.0 + 0.55 * sin(6.2832 * fd / 9.0 - t * 3.0) * saturate(fd / 20.0);
float rib = floor(h.x * 5.0), lat = (rib - 2.0) * 0.45 + c.y * 0.35;
float wob = sin(fd * 0.12 - t * 4.0 + rib * 1.7) * 0.35 + sin(fd * 0.05 - t * 1.7) * 0.6;
float fall = saturate(fd / K.x), land = smoothstep(0.85, 1.0, fall);
p = float3(K.y * tau * lerp(0.97, 1.03, h.z) + (jx * 0.4 + wob * 0.5) * neck * bead, (lat + wob) * neck * bead, c.z - fd);
p.xy += normalize(h.xy - 0.5 + 1e-3) * ((role < 0.5 ? 0.4 : 1.5) * tau * (tau / Tf + 0.3)
+ step(h.z, 0.08) * fd * 0.04 + land * 2.5);
fade = step(h.y, 0.78 + 0.22 * sin(6.2832 * (t - tau) * 0.6));
float sp = age - Ts - Tf;
cq = p * 0.07 + float3(0.0, 0.0, (t - max(sp, 0.0)) * 0.9);
ca = F.w * (role < 0.5 ? 0.5 : 1.2) * fall * sqrt(fall);
if (sp > 0.0)
{
float a = 6.2832 * h.z;
float2 d = float2(cos(a) + 0.6, sin(a));
float vs = lerp(4.0, 16.0, h.x * h.x), vz = lerp(2.0, 10.0, h.y * h.y);
float th = 2.0 * vz / g, sh = min(sp, th);
float2 q = p.xy + d * (vs * sh + 3.0 * (1.0 - exp(-max(sp - th, 0.0) * 1.5)));
p = float3(q, Ground(q, S, P, zb) + 0.15 + max(vz * sh - 0.5 * g * sh * sh, 0.0));
ca.z = 0.0;
fade = 1.0 - smoothstep(0.5, 1.0, sp / max(T - Ts - Tf, 0.3));
}
}
return p - c;
}
float3 Dust(float3 c, float4 h, float u, float t, float T, float4 F, out float age, out float3 cq, out float3 ca)
{
float Td = T * 1.6;
age = frac(t / Td + u);
float s = age * Td, a = 6.2832 * h.z;
float3 p = float3(float2(cos(a), sin(a)) * 14.0 * (1.0 - exp(-s * 1.5)) * lerp(0.3, 1.0, h.x),
9.0 * (1.0 - exp(-s * 0.8)) * lerp(0.3, 1.0, h.y));
cq = (c + p) * 0.06 + float3(0.0, 0.0, t * 0.2);
ca = F.w * 0.8 * age;
return p;
}
float3 Assemble(float3 c, float4 h, float t, float T, float4 F, float4 S, float4 P, float4 K, out float4 look, out float3 cq, out float3 ca)
{
float cyc = frac(t / T), hN = saturate(c.z / K.z);
float eA = saturate((cyc / 0.32 - 0.7 * (0.6 * hN + 0.4 * h.x)) / 0.3);
float eD = saturate(((cyc - 0.64) / 0.28 - 0.75 * (0.65 * (1.0 - hN) + 0.35 * h.y)) / 0.25);
float e = eA * eA * (3.0 - 2.0 * eA);
float k = floor(h.z * K.w), va = k * 2.39996 + 0.7;
float2 sxy = float2(cos(va), sin(va)) * K.y * (0.55 + 0.45 * frac(k * 0.618034)) + (h.wx - 0.5) * 3.0;
float3 p = lerp(float3(sxy, Ground(sxy, S, P, K.x) + 0.2), c, e);
float arc = sin(3.14159 * e);
p.z += arc * K.z * 0.12;
p.xy += float2(-p.y, p.x) / max(length(p.xy), 1.0) * arc * (1.0 + 0.5 * h.w);
cq = p * 0.08 + float3(0.0, 0.0, t * 0.25);
ca = F.w * arc;
float sp = frac(h.y * 13.0 + t * (0.03 + 0.04 * h.z));
float shed = smoothstep(0.94, 0.985, sp) * (1.0 - smoothstep(0.99, 1.0, sp)) * smoothstep(0.5, 1.0, length(c.xy) / max(K.z * 0.4, 1.0)) * eA * (1.0 - eD);
p += normalize(F.xyz + float3(0.0, 0.0, 6.0)) * (2.0 + 6.0 * h.x) * shed;
float2 lxy = c.xy * (1.25 + 0.6 * h.x) + (h.zw - 0.5) * 4.0;
if (eD > 0.0)
{
p = float3(lerp(c.xy, lxy, smoothstep(0.4, 1.0, eD)), lerp(c.z, Ground(lxy, S, P, K.x) + 0.15, eD * eD));
cq = c * 0.08 + float3(0.0, 0.0, t * 0.25);
ca = F.w * 0.5 * sin(3.14159 * eD);
}
float form = smoothstep(0.7, 1.0, eA) * (1.0 - smoothstep(0.0, 0.3, eD));
look = float4(smoothstep(0.0, 0.12, eA) * (1.0 - smoothstep(0.8, 1.0, eD)), lerp(0.55, 1.0, form), 0.0, form);
return p - c;
}
float3 Gallop(float3 c, float4 h, float t, float T, float4 F, float4 K, out float4 look, out float3 cq, out float3 ca)
{
float ph = 6.2832 * t / T, zn = saturate(c.z / K.z), pitch = 0.06 * sin(ph);
float2 yz = float2(c.y, c.z - 0.55 * K.z);
float3 p = float3(c.x, yz.x * cos(pitch) - yz.y * sin(pitch), 0.55 * K.z + yz.x * sin(pitch) + yz.y * cos(pitch));
p.z += K.y * (0.5 + 0.5 * sin(ph - 1.2));
float leg = saturate((0.4 - zn) / 0.4), lph = ph + (c.y > 0.0 ? 1.6 : 0.0) + (c.x > 0.0 ? 0.5 : 0.0);
p.y += sin(lph) * K.x * 0.5 * leg;
p.z += max(cos(lph), 0.0) * K.x * 0.25 * leg * leg;
float mane = saturate(smoothstep(0.7, 0.85, zn) * step(0.0, c.y) + smoothstep(-0.3 * K.z, -0.4 * K.z, c.y) * smoothstep(0.4, 0.6, zn));
look = float4(1.0, 1.0, 0.0, 0.55);
cq = 0.0;
ca = 0.0;
if (h.w < K.w * mane)
{
float age = frac(t / (3.0 * T) + h.x), s = age * 3.0 * T;
p += float3(0.0, -18.0 * s, 6.0 * s);
cq = p * 0.03 + float3(0.0, 0.0, t * 0.4);
ca = F.w * age;
look = float4(smoothstep(0.0, 0.1, age) * (1.0 - age), lerp(1.0, 2.5, age), smoothstep(0.1, 0.6, age), 0.55 * (1.0 - smoothstep(0.0, 0.3, age)));
}
return p - c;
}
float3 Burst(float3 c, float4 h, float role, float clk, float4 E, float4 F, float4 K, out float4 look, out float3 cq, out float3 ca)
{
float s = clk - E.y, life = s / max(E.z, 0.01);
look = float4(0.0, 1.0, 0.0, 0.0);
cq = 0.0;
ca = 0.0;
if (life < 0.0 || life > 1.0) return float3(0.0, 0.0, 0.0);
float3 dir = normalize(c + (h.xyz - 0.5) * 3.0 + float3(0.0, 0.0, K.y * 4.0));
float3 p;
if (role < 1.5)
{
float v = lerp(60.0, 240.0, h.w * h.w) * K.x * max(E.x, 0.05);
p = dir * v * (1.0 - exp(-3.0 * s)) / 3.0 - float3(0.0, 0.0, 245.0 * K.z * s * s);
look = float4(smoothstep(0.0, 0.04, life) * (1.0 - smoothstep(0.5, 1.0, life)), 1.0, 0.0, 0.0);
cq = (c + p) * 0.06 + float3(0.0, 0.0, clk * 0.5);
ca = F.w * life;
}
else
{
p = dir * 16.0 * K.x * max(E.x, 0.05) * (1.0 - exp(-2.0 * s)) + float3(0.0, 0.0, K.w * s);
look = float4(0.5 * smoothstep(0.0, 0.08, life) * pow(1.0 - life, 1.5), lerp(1.0, 4.0, sqrt(life)), 1.0, 0.0);
cq = (c + p) * 0.05 + float3(0.0, 0.0, clk * 0.3);
ca = 1.5 * F.w * life;
}
return p;
}
float3 Drift(float3 c, float4 h, float u, float t, float T, float4 F, out float4 look, out float3 cq, out float3 ca)
{
float age = frac(t / (T * lerp(0.7, 1.3, h.x)) + u), s = age * T;
float3 p = normalize(c + 1e-3) * 1.5 * s + F.xyz * 0.5 * s * s;
look = float4(smoothstep(0.0, 0.1, age) * (1.0 - age), lerp(1.0, 0.4, age), 0.6 * smoothstep(0.3, 1.0, age), 0.0);
cq = (c + p) * 0.12 + float3(0.0, 0.0, -t * 0.4);
ca = F.w * age;
return p;
}
float3 Bloom(float3 c, float4 h, float role, float u, float clk, float4 E, float4 F, float4 S, float4 P, float4 K, out float4 look, out float3 cq, out float3 ca)
{
float life = (clk - E.y) / max(E.z, 0.1);
look = float4(0.0, 1.0, 0.0, 0.0);
cq = 0.0;
ca = 0.0;
if (life <= 0.0 || life >= 1.0) return float3(0.0, 0.0, 0.0);
float grow = smoothstep(0.0, 0.25, life), spread = smoothstep(0.2, 0.55, life), van = smoothstep(0.72, 1.0, life);
float crumble = step(0.5, E.w);
float2 rel = c.xy - P.xy;
float rr = saturate(length(rel) / (50.0 * P.z)), ang = atan2(rel.y, rel.x);
float reach = lerp(0.3 * grow, 1.0, spread) * (1.0 - 0.9 * van * (1.0 - crumble));
float R = 50.0 * P.z * max(E.x, 0.1) * reach * (1.0 + 0.18 * (VN(ang * 2.2 + clk * 0.3) - 0.5) + 0.08 * sin(ang * 5.0 + clk));
float2 d = float2(cos(ang), sin(ang));
float top = K.x * min(0.09 / max(reach * reach, 0.09), 1.0) * grow * lerp(1.0 - van, 1.0, crumble);
float3 p = float3(P.xy + d * rr * R, top * (1.0 - rr * rr) + 0.2);
look.w = PackN(float3(d * 2.0 * top * rr / max(R, 1.0), 1.0));
if (role > 1.5 && role < 2.5)
{
float4 sl;
float3 s = Strand(p, h, u, clk, 3.0, F, S, P, -1000.0, K.z * spread * (1.0 - van), sl, cq, ca);
p += s;
look.w = sl.w;
}
float e = crumble * saturate((van * 1.3 - h.z) / 0.3);
if (e > 0.0)
{
p += float3(normalize(h.xy - 0.5 + 1e-3) * 10.0 * e, 6.0 * e - 12.0 * e * e);
cq = p * 0.06 + float3(0.0, 0.0, clk * 0.4);
ca = F.w * e;
}
look.x = step(rr, 0.15 + 0.85 * grow) * (1.0 - smoothstep(0.6, 1.0, e)) * lerp(1.0 - smoothstep(0.85, 1.0, life), 1.0, crumble);
return p - c;
}
float Stutter(float t, float4 h, float G) { float r = lerp(4.0, 12.0, h.x); return h.y < 0.6 * G ? floor(t * r) / r : t; }
float DissolveE(float3 c, float4 h, float d) { return saturate((1.25 * d - (0.7 * h.z + 0.3 * saturate(1.0 - c.z / 300.0))) / 0.25); }
};
FFlow f;
float4 h = f.Hash(RadiusSeed.y);
float role = floor(RadiusSeed.y * 4.0), u = frac(RadiusSeed.y * 4.0), fade = 1.0, age = 0.0, burst = 1.0;
float4 look = float4(1.0, 1.0, 0.0, 0.0);
float3 cq = 0.0, ca = 0.0;
float md = Mode.y > 0.5 ? Mode.y - 1.0 : Mode.x;
float G = Mode.z;
bool isStream = md < 0.5, isMound = md >= 0.5 && md < 1.5;
int kind = isStream ? (role < 1.5 ? 0 : role < 2.5 ? 1 : 4) : isMound ? (role < 0.5 || role > 2.5 ? 4 : role < 1.5 ? 2 : 3)
: md < 2.5 ? 5 : md < 3.5 ? 7 : md < 4.5 ? 6 : md < 5.5 ? 8 : md < 6.5 ? 9 : 10;
float4 Ev = Dissolve;
float calm = (isMound || kind == 9) ? saturate(Ev.w) : 0.0;
float dv = Ev.z > 0.0 ? lerp(Ev.x, Ev.w, saturate((Clock - Ev.y) / Ev.z)) : Ev.x;
float t = f.Stutter((Clock - Prev * TimeCfg.z) * TimeCfg.x + TimeCfg.y, h, G);
if (Prev > 0.5 && TimeCfg.z <= 0.0) return float3(0.0, 0.0, 0.0);
float3 o = 0.0;
if (kind == 0) o = f.Stream(RestPos, h, role, u, t, TimeCfg.w, Flow, Shape, Place, Tune, fade, cq, ca);
else if (kind == 1) o = f.Dust(RestPos, h, u, t, TimeCfg.w, Flow, age, cq, ca);
else if (kind == 2) o = f.Saltation(RestPos, h, u, t, TimeCfg.w, Flow.xyz, Shape, Place, 0.0, fade);
else if (kind == 3) o = f.Strand(RestPos, h, u, t, TimeCfg.w, Flow, Shape, Place, 0.0, Tune.z * (1.0 - calm), look, cq, ca);
else if (kind == 4) o = f.Avalanche(RestPos, h, u, t, TimeCfg.w * (isStream ? 1.5 : 1.0), (isStream ? 2.5 : (role < 0.5 ? Tune.x : 0.0)) * (1.0 - calm),
(isStream ? 0.15 : Tune.y) * (1.0 - calm), Shape, Place, isStream ? -Tune.x : 0.0, fade);
else if (kind == 5) o = f.Assemble(RestPos, h, t, TimeCfg.w, Flow, Shape, Place, Tune, look, cq, ca);
else if (kind == 6) o = f.Gallop(RestPos, h, t, TimeCfg.w, Flow, Tune, look, cq, ca);
else if (kind == 8) o = f.Burst(RestPos, h, role, Clock, Ev, Flow, Tune, look, cq, ca);
else if (kind == 9) o = f.Drift(RestPos, h, u, t, TimeCfg.w, Flow, look, cq, ca);
else if (kind == 10) o = f.Bloom(RestPos, h, role, u, Clock, Ev, Flow, Shape, Place, Tune, look, cq, ca);
if (isMound && Ev.z > 0.0 && Clock >= Ev.y && Clock < Ev.y + Ev.z)
{
float a = 0.8 * (Clock - Ev.y), back = 1.0 - smoothstep(0.55, 1.0, (Clock - Ev.y) / Ev.z);
float2 rel = RestPos.xy - Place.xy;
float rr = saturate(length(rel) / (50.0 * Place.z));
float vz = Ev.x * lerp(60.0, 220.0, h.x * h.x) * (1.0 - 0.6 * rr), vr = Ev.x * lerp(10.0, 70.0, h.y);
o += float3(rel / max(length(rel), 1e-3) * vr * (1.0 - exp(-2.5 * a)) / 2.5, max(vz * a - 490.0 * a * a, 0.0)) * back;
cq = (RestPos + o) * 0.05 + float3(0.0, 0.0, Clock * 0.4);
ca = max(ca, Flow.w * Ev.x * back);
}
float e = (kind >= 5 && kind <= 7) ? f.DissolveE(RestPos, h, dv) : 0.0;
if (e > 0.0)
{
float s = 0.8 * e;
float3 q = RestPos + o;
q.z = max(q.z - 490.0 * s * s, 0.5);
q.xy += normalize(h.xy - 0.5 + 1e-3) * 25.0 * e;
o = q - RestPos;
cq = q * 0.05 + float3(0.0, 0.0, t * 0.3);
ca = max(ca, 2.0 * Flow.w * e);
}
if (any(ca != 0.0)) o += f.Curl(cq) * ca;
if (G > 0.0)
{
float tick = floor(Clock * 8.0), col = floor(RestPos.x / 3.0), row = floor(RestPos.z / 2.0);
o.z += step(f.H1(col * 3.1 + tick * 1.7), 0.15 * G) * (f.H1(col + tick) - 0.5) * 6.0;
o.x += step(f.H1(row * 5.3 + tick * 2.3 + 7.0), 0.08 * G) * (f.H1(row + tick + 3.0) - 0.5) * 5.0;
o += step(f.H1(h.z * 91.0 + tick), 0.08 * G) * (f.Hash(RadiusSeed.y + tick).xyz - 0.5) * 3.0;
if (h.w < 0.6 * G) o = floor(o / 0.35 + 0.5) * 0.35;
}
return o;
