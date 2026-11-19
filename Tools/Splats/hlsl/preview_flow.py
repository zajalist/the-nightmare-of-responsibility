"""Offline preview of MF_SplatFlow motion (numpy port of flow_lib.hlsl's Stream and Wisp), to check shapes without
the shared editor. Renders splat centres of SM_SandStream (side view) and of mound A's wisps at a few times.
    python Tools/Splats/hlsl/preview_flow.py OUT.png
Shortcut: ports only Stream/Dust (stream) and Wisp; the editor stays the reference for the look.
"""
import json
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw

P = json.load(open("P:/FoA-Assets/splatmesh/sand_vfx_params.json"))


def load(name):
    d = json.load(open(f"P:/FoA-Assets/splatmesh/{name}.gltf"))
    blob = open(f"P:/FoA-Assets/splatmesh/{name}.bin", "rb").read()
    at = d["meshes"][0]["primitives"][0]["attributes"]

    def rd(k, n):
        a = d["accessors"][at[k]]
        v = d["bufferViews"][a["bufferView"]]
        return np.frombuffer(blob[v["byteOffset"]:v["byteOffset"] + v["byteLength"]], np.float32).reshape(-1, n)[::4]
    g = rd("POSITION", 3)
    return np.stack([g[:, 0], g[:, 2], g[:, 1]], 1) * 100.0, rd("TEXCOORD_1", 2)  # glTF m -> UE cm


def hash4(seed):
    b = seed.astype(np.float32).view(np.uint32).astype(np.uint64)
    M = 0xFFFFFFFF
    v = [b & M, (b ^ 0x9E3779B9) & M, (b * 747796405) & M, (b + 2891336453) & M]
    v = [(x * 1664525 + 1013904223) & M for x in v]
    x, y, z, w = v
    x = (x + y * w) & M; y = (y + z * x) & M; z = (z + x * y) & M; w = (w + y * z) & M
    x ^= x >> 16; y ^= y >> 16; z ^= z >> 16; w ^= w >> 16
    x = (x + y * w) & M; y = (y + z * x) & M; z = (z + x * y) & M; w = (w + y * z) & M
    return np.stack([(q >> 8).astype(np.float64) / 16777216.0 for q in (x, y, z, w)], 1)


def g3(p):
    q = np.stack([p @ np.array([127.1, 311.7, 74.7]), p @ np.array([269.5, 183.3, 246.1]), p @ np.array([113.5, 271.9, 124.6])], 1)
    return np.modf(np.sin(q) * 43758.5453)[0] % 1.0 * 2 - 1


def noise_grad(x):
    i, f = np.floor(x), x - np.floor(x)
    u = f * f * f * (f * (f * 6 - 15) + 10)
    du = 30 * f * f * (f * (f - 2) + 1)
    c = {k: np.array(k, float) for k in [(a, b, e) for e in (0, 1) for b in (0, 1) for a in (0, 1)]}
    G = {k: g3(i + v) for k, v in c.items()}
    V = {k: np.sum(G[k] * (f - c[k]), 1) for k in c}
    ga, gb, gc, gd, ge, gf, gg, gh = (G[k] for k in [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
    va, vb, vc, vd, ve, vf, vg, vh = (V[k][:, None] for k in [(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
    ux, uy, uz = u[:, :1], u[:, 1:2], u[:, 2:]
    yzx, zxy = u[:, [1, 2, 0]], u[:, [2, 0, 1]]
    return (ga + ux * (gb - ga) + uy * (gc - ga) + uz * (ge - ga) + ux * uy * (ga - gb - gc + gd) + uy * uz * (ga - gc - ge + gg)
            + uz * ux * (ga - gb - ge + gf) + ux * uy * uz * (-ga + gb + gc - gd + ge - gf - gg + gh)
            + du * (np.hstack([vb - va, vc - va, ve - va]) + yzx * np.hstack([va - vb - vc + vd, va - vc - ve + vg, va - vb - ve + vf])
                    + zxy * np.hstack([va - vb - ve + vf, va - vb - vc + vd, va - vc - ve + vg])
                    + yzx * zxy * (-va + vb + vc - vd + ve - vf - vg + vh)))


def curl(p):
    return np.cross(noise_grad(p), noise_grad(p + np.array([31.416, -17.3, 9.27])))


def stream(c, rs, t):
    """Port of Stream (roles 0, 1) + Dust (role 2); pile grains (role 3) left at rest."""
    K = P["stream"]["Tune"]; T = 2.2; Fw = 1.6; g = 980.0
    seed = rs[:, 1]; role = np.floor(seed * 4); u = (seed * 4) % 1.0; h = hash4(seed)
    zland = -K[0] + P["stream"]["Shape"][0] * P["stream"]["Place"][2]
    Tf = np.sqrt(2 * np.maximum(c[:, 2] - zland, 1) / g); Ts = K[2] / K[1]
    n = 19.0; tight = np.where(role < 0.5, 0.3 + 0.7 * h[:, 3] ** 2, 1.0)
    age = ((t / T + (np.floor(u * n) + 0.5 + ((u * n) % 1 - 0.5) * tight) / n) % 1.0) * T
    jx = (h[:, 3] - 0.5) * 1.2
    out = c.copy(); alpha = np.ones(len(c))
    sl = age < Ts
    s = age / Ts
    out[sl] = np.stack([-K[2] * (1 - s) + jx, c[:, 1] * (2.2 + (1 - 2.2) * s), c[:, 2] + K[3] * (1 - s) ** 1.9], 1)[sl]
    tau = np.minimum(age - Ts, Tf)
    neck = np.maximum(np.sqrt(K[1] / np.sqrt(K[1] ** 2 + (g * tau) ** 2)), 0.3)
    fd = 0.5 * g * tau ** 2
    bead = 1 + 0.55 * np.sin(6.2832 * fd / 9 - t * 3) * np.clip(fd / 20, 0, 1)
    rib = np.floor(h[:, 0] * 5); lat = (rib - 2) * 0.45 + c[:, 1] * 0.35
    wob = np.sin(fd * 0.12 - t * 4 + rib * 1.7) * 0.35 + np.sin(fd * 0.05 - t * 1.7) * 0.6
    fall = np.clip(fd / K[0], 0, 1); land = np.clip((fall - 0.85) / 0.15, 0, 1); land = land * land * (3 - 2 * land)
    p = np.stack([K[1] * tau * (0.97 + 0.06 * h[:, 2]) + (jx * 0.4 + wob * 0.5) * neck * bead, (lat + wob) * neck * bead, c[:, 2] - fd], 1)
    d2 = h[:, :2] - 0.5 + 1e-3
    d2 /= np.linalg.norm(d2, axis=1, keepdims=True)
    p[:, :2] += d2 * (np.where(role < 0.5, 0.4, 1.5) * tau * (tau / Tf + 0.3) + (h[:, 2] < 0.08) * fd * 0.04 + land * 2.5)[:, None]
    pulse = h[:, 1] < 0.78 + 0.22 * np.sin(6.2832 * (t - tau) * 0.6)
    sp = age - Ts - Tf
    cq = p * 0.07 + np.stack([0 * tau, 0 * tau, (t - np.maximum(sp, 0)) * 0.9], 1)
    ca = (Fw * np.where(role < 0.5, 0.5, 1.2) * fall * np.sqrt(fall))[:, None] * np.ones((1, 3))
    a = 6.2832 * h[:, 2]
    dd = np.stack([np.cos(a) + 0.6, np.sin(a)], 1)
    vs = 4 + 12 * h[:, 0] ** 2; vz = 2 + 8 * h[:, 1] ** 2; th = 2 * vz / g; sh = np.minimum(sp, th)
    q = p[:, :2] + dd * (vs * sh + 3 * (1 - np.exp(-np.maximum(sp - th, 0) * 1.5)))[:, None]
    spl = sp > 0
    p[spl, :2] = q[spl]
    p[spl, 2] = (zland - 1.0 + np.maximum(vz * sh - 0.5 * g * sh * sh, 0))[spl]
    ca[spl, 2] = 0
    p += curl(cq) * ca
    fl = (~sl) & (role < 1.5)
    out[fl] = p[fl]
    alpha[fl & ~spl & ~pulse] = 0.0
    alpha[spl & (role < 1.5)] = (1 - np.clip((sp / max(T - Ts - Tf.mean(), 0.3) - 0.5) / 0.5, 0, 1))[spl & (role < 1.5)]
    return out, alpha, role


FRONT = "--front" in sys.argv


def render(path):
    W, H = 1500, 900
    img = Image.new("L", (W, H), 200)
    dr = ImageDraw.Draw(img)
    c, rs = load("SM_SandStream")
    for k, t in enumerate((10.0, 10.37, 10.74, 11.11, 11.48)):
        pos, alpha, role = stream(c, rs, t)
        ox = 60 + k * 290
        for (x, y, z), a, r in zip(pos, alpha, role):
            if r > 1.5 or a < 0.05:
                continue
            px, py = ox + 90 + (y * 12.0 if FRONT else x * 5.5), 40 + (-z) * 6.5
            v = int(200 - 170 * a * (0.9 if r < 0.5 else 0.5))
            dr.point((px, py), fill=v)
        dr.text((ox + 60, 10), f"t={t:.2f}s (side, x out)", fill=0)
    img.save(path)
    print("wrote", path)


if __name__ == "__main__":
    render(next((a for a in sys.argv[1:] if not a.startswith("--")), "flow_preview.png"))


def wisps(path, label="Bay"):
    """Port of Wisp for one mound's role-2 splats (side view along its local Y, mound-local cm)."""
    m = P["mounds"][label]
    c, rs = load(m["mesh"])
    seed = rs[:, 1]
    sel = np.floor(seed * 4) == 2
    c, seed = c[sel], seed[sel]
    u, h = (seed * 4) % 1.0, hash4(seed)
    F = np.array(list(m["Flow_wind_local"][:2]) + [0.0, 10.0]); T = 9.0; rise = 8.0
    W, H = 1500, 700
    img = Image.new("L", (W, H), 200)
    dr = ImageDraw.Draw(img)
    for k, t in enumerate((20.0, 21.5, 23.0, 24.5, 26.0)):
        Tw = T * 0.8 * (0.9 + 0.2 * h[:, 0])
        age = (t / Tw + u) % 1.0
        s = age * Tw
        idv = np.modf(np.sin((np.floor(c[:, 0] * 0.5) + 57 * np.floor(c[:, 1] * 0.5)) * 127.1) * 43758.5453)[0] % 1.0
        te = t - s
        gg = 0.9 * np.sin(te * 0.37 + idv * 6.2832) + 0.4 * np.sin(te * 0.91 + idv * 17.0)
        p = np.stack([(F[0] * np.cos(gg) - F[1] * np.sin(gg)) * s * 0.5, (F[0] * np.sin(gg) + F[1] * np.cos(gg)) * s * 0.5,
                      rise * s * (1 - 0.4 * age)], 1)
        a = s * 1.9 + h[:, 2] * 6.2832
        p[:, :2] += np.stack([np.cos(a), np.sin(a)], 1) * ((0.3 + 2.2 * age) * (0.4 + 0.6 * h[:, 3]))[:, None]
        p += curl((c + p) * 0.035 + np.stack([0 * s, 0 * s, -t * 0.35 + 0 * s], 1)) * (F[3] * age ** 1.1)[:, None]
        q = c + p
        alpha = np.clip(age / 0.06, 0, 1) * (1 - age) ** 1.4
        size = 1 + 4 * age
        ox = 150 + k * 290
        for (x, y, z), al, sz in zip(q, alpha, size):
            r = max(0.6, 0.35 * sz)
            v = int(200 - 150 * al)
            dr.ellipse((ox + x * 2.2 - r, H - 60 - z * 2.2 - r, ox + x * 2.2 + r, H - 60 - z * 2.2 + r), fill=v)
        dr.line((ox - 110, H - 60, ox + 110, H - 60), fill=120)
        dr.text((ox - 60, 10), f"{label} wisps t={t:.1f}s", fill=0)
    img.save(path)
    print("wrote", path)


def mound_h(q, S):
    """numpy twin of Mound() (mound-local cm)."""
    a = np.arctan2(q[:, 1], q[:, 0]); w = np.sin(4 * a + S[3])
    t = np.hypot(q[:, 0], q[:, 1]) / (50 * (1 + 0.12 * np.sin(3 * a + S[1]) + 0.08 * np.sin(5 * a + S[2])))
    h = 24 * np.clip(1 - t, 0, 1) ** 1.6 * (1 + 0.15 * w * t)
    return np.where(t < 1 / 14, S[0] + (24 * (13 / 14) ** 1.6 * (1 + 0.15 * w / 14) - S[0]) * t * 14, h)


def clock(path):
    """Port of Assemble for the Lux3D clock (front view, clock-local cm) at phases of its 16 s loop."""
    C = P["clock"]; S, Pl, K = C["Shape"], C["Place"], C["Tune"]; T = 16.0; Fw = 2.5
    c, rs = load("fear_of_adulthood_clock")
    seed = rs[:, 1]; h = hash4(seed)
    W, H = 1600, 520
    img = Image.new("L", (W, H), 200)
    dr = ImageDraw.Draw(img)
    for k, t in enumerate((1.5, 3.0, 4.2, 7.0, 11.0, 12.5, 14.0)):
        cyc = (t / T) % 1.0; hN = np.clip(c[:, 2] / K[2], 0, 1)
        eA = np.clip((cyc / 0.32 - 0.7 * (0.6 * hN + 0.4 * h[:, 0])) / 0.3, 0, 1)
        eD = np.clip(((cyc - 0.64) / 0.28 - 0.75 * (0.65 * (1 - hN) + 0.35 * h[:, 1])) / 0.25, 0, 1)
        e = eA * eA * (3 - 2 * eA)
        kk = np.floor(h[:, 2] * K[3]); va = kk * 2.39996 + 0.7
        sxy = np.stack([np.cos(va), np.sin(va)], 1) * (K[1] * (0.55 + 0.45 * ((kk * 0.618034) % 1)))[:, None] + (h[:, [3, 0]] - 0.5) * 3
        d = sxy - np.array(Pl[:2]); cs, sn = np.cos(Pl[3]), np.sin(Pl[3])
        q = np.stack([cs * d[:, 0] - sn * d[:, 1], sn * d[:, 0] + cs * d[:, 1]], 1) / Pl[2]
        start = np.hstack([sxy, (mound_h(q, S) * Pl[2] + K[0] + 0.2)[:, None]])
        p = start + (c - start) * e[:, None]
        arc = np.sin(np.pi * e)
        p[:, 2] += arc * K[2] * 0.25
        rl = np.maximum(np.hypot(p[:, 0], p[:, 1]), 1)
        p[:, :2] += np.stack([-p[:, 1], p[:, 0]], 1) / rl[:, None] * (arc * (3 + 1.5 * h[:, 3]))[:, None]
        p += curl(p * 0.08 + np.stack([0 * rl, 0 * rl, t * 0.25 + 0 * rl], 1)) * (Fw * arc)[:, None]
        lxy = c[:, :2] * (1.25 + 0.6 * h[:, 0])[:, None] + (h[:, 2:4] - 0.5) * 4
        d = lxy - np.array(Pl[:2]); q = np.stack([cs * d[:, 0] - sn * d[:, 1], sn * d[:, 0] + cs * d[:, 1]], 1) / Pl[2]
        land = np.hstack([lxy, (mound_h(q, S) * Pl[2] + K[0] + 0.15)[:, None]])
        sm = np.clip((eD - 0.4) / 0.6, 0, 1); sm = sm * sm * (3 - 2 * sm)
        pd = np.hstack([c[:, :2] + (land[:, :2] - c[:, :2]) * sm[:, None], (c[:, 2] + (land[:, 2] - c[:, 2]) * eD * eD)[:, None]]) + curl(c * 0.08 + np.stack([0 * rl, 0 * rl, t * 0.25 + 0 * rl], 1)) * (Fw * 0.5 * np.sin(np.pi * eD))[:, None]
        p = np.where((eD > 0)[:, None], pd, p)
        op = np.clip(eA / 0.12, 0, 1) * (1 - np.clip((eD - 0.8) / 0.2, 0, 1))
        form = np.clip((eA - 0.7) / 0.3, 0, 1) * (1 - np.clip(eD / 0.3, 0, 1))
        ox = 110 + k * 225
        dr.text((ox - 50, 8), f"t={t:.1f}s ({cyc:.2f})", fill=0)
        for (x, y, z), o, f in zip(p[::2], op[::2], form[::2]):
            if o < 0.05:
                continue
            dr.point((ox + x * 6, H - 70 - z * 13), fill=int(200 - o * (90 + 60 * (1 - f))))
    img.save(path)
    print("wrote", path)


def strands(path, label="Bay", reach=12.0, T=10.0, Fw=1.5):
    """Port of Strand for one mound's role-2 splats (side view, mound-local cm)."""
    m = P["mounds"][label]
    S = m["Shape"]
    c, rs = load(m["mesh"])
    seed = rs[:, 1]
    sel = np.floor(seed * 4) == 2
    c, seed = c[sel], seed[sel]
    u, h = (seed * 4) % 1.0, hash4(seed)
    H1 = lambda n: np.modf(np.sin(n * 127.1) * 43758.5453)[0] % 1.0  # noqa: E731
    idv = H1(np.floor(c[:, 0] * 0.5) + 57 * np.floor(c[:, 1] * 0.5))

    def ground(q):
        return mound_h(q, S)

    def normal(q):
        e = 0.4
        hx = ground(q + [e, 0]) - ground(q - [e, 0]); hy = ground(q + [0, e]) - ground(q - [0, e])
        n = np.stack([-hx, -hy, 2 * e * np.ones_like(hx)], 1)
        return n / np.linalg.norm(n, axis=1, keepdims=True)
    W, Hh = 1500, 520
    img = Image.new("L", (W, Hh), 200)
    dr = ImageDraw.Draw(img)
    n = normal(c[:, :2])
    for k, t in enumerate((30.0, 32.5, 35.0, 37.5, 40.0)):
        Ts = T * (0.8 + 0.5 * idv); cyc = t / Ts + idv * 7; ph = cyc % 1; kk = np.floor(cyc)
        d = n * 0.6 + np.stack([H1(idv * 3.7) - 0.5, H1(idv * 9.1) - 0.5, 0.9 * np.ones_like(idv)], 1)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        sm = lambda a, b, x: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))  # noqa: E731
        stretch = sm(0.0, 0.7, ph) * (1 - sm(0.78, 0.86, ph))
        full = reach * (0.6 + 0.8 * H1(idv * 5.3 + kk)); ln = full * stretch
        side = np.cross(d, [0, 0, 1]) + 1e-3; side /= np.linalg.norm(side, axis=1, keepdims=True); up2 = np.cross(side, d)
        a = h[:, 0] * 6.2832
        thick = (1.6 + (0.5 - 1.6) * u) + 1.4 * sm(0.8, 1.0, u)
        ring = (side * np.cos(a)[:, None] + up2 * np.sin(a)[:, None]) * np.sqrt(h[:, 1])[:, None]
        p = d * (ln * u)[:, None] - np.stack([0 * u, 0 * u, 0.35 * ln * np.sin(np.pi * u) * u], 1) + ring * (thick * (0.4 + 0.6 * stretch))[:, None]
        tear = (u > 0.8) & (ph > 0.82) & (H1(idv * 11 + kk) < 0.4)
        fallT = (ph - 0.82) * Ts
        q = d * (full * 0.95)[:, None] + ring * 1.2 - np.stack([0 * u, 0 * u, 73.5 * fallT ** 2], 1)
        q[:, 2] = np.maximum(q[:, 2], ground((c + q)[:, :2]) - c[:, 2] + 0.3)
        mix = sm(0.93, 1.0, ph)[:, None]
        p = np.where(tear[:, None], q + (p - q) * mix, p)
        p += curl((c + p) * 0.04 + np.stack([0 * u, 0 * u, t * 0.12 + 0 * u], 1)) * (Fw * u * stretch)[:, None]
        w = c + p
        ox = 160 + k * 290
        xs = np.linspace(-50, 50, 200)
        prof = ground(np.stack([xs, np.zeros_like(xs)], 1))
        for x0, z0 in zip(xs, prof):
            dr.point((ox + x0 * 2.6, Hh - 50 - z0 * 2.6), fill=90)
        for (x, y, z), uu in zip(w, u):
            r = 1.2 + 1.2 * (uu > 0.8)
            dr.ellipse((ox + x * 2.6 - r, Hh - 50 - z * 2.6 - r, ox + x * 2.6 + r, Hh - 50 - z * 2.6 + r), fill=25)
        dr.text((ox - 50, 8), f"{label} goo strands t={t:.1f}", fill=0)
    img.save(path)
    print("wrote", path)
