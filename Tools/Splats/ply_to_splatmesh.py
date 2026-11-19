#!/usr/bin/env python3
r"""ply_to_splatmesh.py - 3D Gaussian Splat PLY (Aholo Lux3D) -> cheap billboard "splat mesh" glTF for UE 5.8.

    python ply_to_splatmesh.py IN.ply OUT.gltf [--count 40000] [--seed 1]
    python ply_to_splatmesh.py --selftest

Writes OUT.gltf + OUT.bin (one mesh, one primitive, uint32 indices, double-sided material) and a sidecar
OUT.splatmesh.json (counts, bounds, scale, channel map). Standard library only. The PLY is untrusted data:
header and sizes are validated, values are only parsed, nothing is executed.

Each kept splat becomes one quad: 4 vertices at the splat center, triangles (0,1,2) (0,2,3) facing +Z.
The material (README.md) billboards the quad with World Position Offset, so the object is one static
mesh = one draw call.

CHANNEL MAP - glTF space: meters, +Y up, right-handed, front +Z.
UE's glTF importer turns glTF (x, y, z) into UE local (x, z, y) * 100 cm (GLTF::ConvertVec3, UE 5.8 source).
  POSITION    vec3  splat center [m] + corner * 0.1 mm in the quad's XY plane (nudge, see below)
  NORMAL      vec3  splat local axis 2, unit           \ anisotropy frame = the 3DGS rotation; local axis 1 is
  TANGENT     vec4  splat local axis 0, unit, w = +1   / cross(NORMAL, TANGENT.xyz). Kept by UE only when
                                                         Recompute Normals/Tangents are off at import.
  TEXCOORD_0  (corner_x, corner_y), each -1 or +1
  TEXCOORD_1  (radius_cm, seed)  radius = 2 * geometric_mean(exp(scale_0..2)) * 100; seed uniform in [0, 1)
  TEXCOORD_2  (R.x, R.y)      \  SH degree 1 as three vectors R, G, B in glTF axes:
  TEXCOORD_3  (R.z, G.x)       |    rgb += 0.4886025 * (dot(R, d), dot(G, d), dot(B, d))
  TEXCOORD_4  (G.y, G.z)       |    d = normalize(splat_center - camera_position) in glTF axes
  TEXCOORD_5  (B.x, B.y)       |  all zero when the PLY has no f_rest (true for every Lux3D file so far)
  TEXCOORD_6  (B.z, sigma0_cm) /  the pad slot carries sigma0
  TEXCOORD_7  (sigma1_cm, sigma2_cm)   sigma_i_cm = exp(scale_i) * 100, the std-dev along local axis i
  COLOR_0     float RGBA: rgb = clamp(0.5 + 0.28209479 * f_dc, 0, 1), 3DGS display (sRGB) space, NOT linear;
              a = sigmoid(opacity). UE stores it as 8-bit and its VertexColor node returns these values
              unchanged (importer applies SRGBToLinear, mesh build applies ToFColor(true)).
  Quaternion + 3 scales (7 floats) do not fit the 3 spare UV floats, so the rotation rides in NORMAL/TANGENT
  (UE converts those into its own axes) and the 3 sigmas fill the pad and TEXCOORD_7.

FINDINGS AND DECISIONS
  Axes: Lux3D PLYs use the INRIA 3DGS / OpenCV frame (+Y down, +Z forward), so glTF = (x, -y, -z), a 180 deg
    rotation about X. Proof: the i23d character task ships both a PLY and a GLB
    (P:/FoA-Assets/character/lux3d/nightmare_i23d_*); over all 48 signed axis permutations the best voxel IoU
    between PLY splat centers and GLB vertices is (x, -y, -z) (0.82 at 1 cm), a proper rotation. Text-to-3D
    PLYs agree (clock bells, briefcase handle, horse head end up on top). The suggested bounding-box heuristic
    is not usable: it cannot tell +Y from -Y and Lux3D bounds are symmetric about the origin.
  Units: kept as-is (scale 1.0, meters). PLY and GLB of the same task share units. Text-to-3D objects come out
    at plausible real sizes, but the i23d character is normalized to 0.3 m, so scale actors in UE as needed.
  Radius: 2 * geometric mean of the three sigmas, not the max. Lux3D splats are flattened ellipsoids (median
    axis ratios about 1 : 0.78 : 0.3-0.45). For those, the sphere with the same view-averaged projected area
    has sigma ~0.68-0.75 * max; the geometric mean (0.60-0.71 * max) is within ~10% of it, while max inflates
    every footprint by 1.3-1.5x. Decimation fill is a separate knob: the sidecar's radius_scale_hint, the
    material RadiusScale that restores the original summed footprint (opacity * area).
  Decimation: drop opacity < 0.05 and non-finite/absurd splats, then weighted sampling without replacement
    (Efraimidis-Spirakis, seeded random.Random) with weight = opacity * radius^2, the splat's visual
    footprint. On the test files this keeps 2-3x more of the original coverage than opacity-only weighting
    while still keeping small splats.
  SH layout: INRIA save_ply writes features_rest (N, coeffs, 3) transposed to (N, 3, coeffs), so f_rest is
    channel-major: f_rest[c*m + k], m = n_rest/3 (15 for degree 3, 8 for 2, 3 for 1); degree 1 is k = 0..2.
    computeColorFromSH: dir = normalize(pos - campos); rgb += -C1*y*sh1 + C1*z*sh2 - C1*x*sh3. That equals
    C1 * dot((-k2, -k0, k1), dir), so each channel is stored as that vector, rotated into glTF axes (dot
    products survive any rotation); the material needs no sign juggling and no per-file axis swizzle.
  Nudge: four vertices at exactly one point make zero-area triangles. UE drops them when "Remove Degenerates"
    is on (StaticMeshBuilder.cpp skips triangles whose corners are within THRESH_POINTS_ARE_SAME), so the
    corners sit +-0.1 mm off center: sub-pixel at normal viewing distances, so the material ignores it.
"""
import argparse
import array
import gzip
import heapq
import json
import math
import os
import random
import struct
import sys
import urllib.parse
import zlib

C0 = 0.28209479177387814      # SH band 0 constant (3DGS)
C1 = 0.4886025119029199       # SH band 1 constant (3DGS)
MIN_OPACITY = 0.05
NUDGE_M = 1e-4                # corner offset, see "Nudge" above
MAX_LOG_SCALE = 5.0           # sanity bound for untrusted input (exp(5) = 148 m); keeps exp() finite
CORNER_UV = (-1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0)
REQUIRED = ('x', 'y', 'z', 'f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity',
            'scale_0', 'scale_1', 'scale_2', 'rot_0', 'rot_1', 'rot_2', 'rot_3')
CHANNELS = {  # attribute order in the file; must match the docstring table
    'POSITION': 'splat center m (+-0.1 mm corner nudge in quad XY plane)',
    'NORMAL': 'splat local axis 2 (anisotropy frame)',
    'TANGENT': 'splat local axis 0, w=+1; axis 1 = cross(NORMAL, TANGENT)',
    'TEXCOORD_0': 'corner x, corner y (each -1 or +1)',
    'TEXCOORD_1': 'radius_cm = 2*geomean(sigma)*100, seed [0,1)',
    'TEXCOORD_2': 'SH1 R.x, R.y', 'TEXCOORD_3': 'SH1 R.z, G.x', 'TEXCOORD_4': 'SH1 G.y, G.z',
    'TEXCOORD_5': 'SH1 B.x, B.y', 'TEXCOORD_6': 'SH1 B.z, sigma0_cm', 'TEXCOORD_7': 'sigma1_cm, sigma2_cm',
    'COLOR_0': 'DC rgb (display/sRGB space, clamped 0..1), opacity',
}
# --lean keeps POSITION, TEXCOORD_0/1 and COLOR_0 only: no SH, no anisotropy (about 140 B/splat in UE instead of 248).
# The material must not read TEXCOORD_2..7 (use the lean world material, not M_SplatMesh's SH node).
LEAN_DROP = ('NORMAL', 'TANGENT', 'TEXCOORD_2', 'TEXCOORD_3', 'TEXCOORD_4', 'TEXCOORD_5', 'TEXCOORD_6', 'TEXCOORD_7')
SPZ_COLOR_SCALE = 0.15        # nianticlabs/spz splat-utils.h colorScale


def to_gltf(x, y, z):
    """Lux3D/3DGS PLY axes (+Y down, +Z forward) -> glTF axes (+Y up, front +Z): 180 deg about X."""
    return x, -y, -z


def parse_ply(data):
    """Validate a binary little-endian 3DGS PLY. Returns (count, {name: float32 column}, sh_names), where
    sh_names lists the 9 degree-1 f_rest columns as R0 R1 R2 G0 G1 G2 B0 B1 B2 (empty without f_rest)."""
    end = data.find(b'end_header', 0, 1 << 16)
    body = data.find(b'\n', end) + 1 if end >= 0 else 0
    if not data.startswith(b'ply') or body == 0:
        raise ValueError('not a PLY file ("ply" magic / end_header missing in the first 64 KB)')
    fmt, elems = None, []
    for line in data[:end].decode('ascii', 'replace').splitlines()[1:]:
        t = line.split()
        if not t or t[0] in ('comment', 'obj_info'):
            continue
        if t[0] == 'format':
            fmt = t[1:]
        elif t[0] == 'element' and len(t) == 3:
            elems.append((t[1], int(t[2]), []))
        elif t[0] == 'property' and elems:
            elems[-1][2].append(t[1:])
        else:
            raise ValueError(f'unexpected PLY header line {line!r}')
    if fmt != ['binary_little_endian', '1.0']:
        raise ValueError(f'unsupported PLY format {fmt}: need binary_little_endian 1.0')
    if not elems or elems[0][0] != 'vertex':
        raise ValueError('the first PLY element must be "vertex"')
    _, n, props = elems[0]
    # shortcut: float32 vertex properties only (the 3DGS layout); add struct decoding if a tool emits others
    bad = [' '.join(p) for p in props if len(p) != 2 or p[0] not in ('float', 'float32')]
    if bad:
        raise ValueError(f'unsupported vertex properties {bad}: only float32 scalars')
    names = [p[1] for p in props]
    missing = [r for r in REQUIRED if r not in names]
    if missing or len(set(names)) != len(names):
        raise ValueError(f'missing or duplicate vertex properties: {missing or names}')
    n_rest = sum(nm.startswith('f_rest_') for nm in names)
    if n_rest % 3 or 0 < n_rest < 9 or any(f'f_rest_{j}' not in names for j in range(n_rest)):
        raise ValueError(f'f_rest_* must be f_rest_0..f_rest_<3m-1> with m >= 3, got {n_rest} values')
    m = n_rest // 3
    sh_names = [f'f_rest_{c * m + k}' for c in range(3) for k in range(3)] if m else []
    need = n * 4 * len(names)
    if n <= 0 or len(data) - body < need:
        raise ValueError(f'vertex data truncated: {n} x {len(names)} floats need {need} bytes, '
                         f'file has {len(data) - body}')
    a = array.array('f')
    a.frombytes(data[body:body + need])
    if sys.byteorder == 'big':
        a.byteswap()
    keep = set(REQUIRED) | set(sh_names)
    return n, {nm: a[i::len(names)] for i, nm in enumerate(names) if nm in keep}, sh_names


def spz_quat(d, o, ver):
    """SPZ rotation -> (x, y, z, w). v2: first three as u8 (w derived); v3: smallest three, 10 bits each + 2-bit index
    (nianticlabs/spz splat-utils.h unpackQuaternionFirstThree / unpackQuaternionSmallestThree)."""
    if ver == 2:
        x, y, z = (d[o + k] / 127.5 - 1.0 for k in range(3))
        return x, y, z, math.sqrt(max(0.0, 1.0 - x * x - y * y - z * z))
    comp = int.from_bytes(d[o:o + 4], 'little')
    big, q, ss = comp >> 30, [0.0] * 4, 0.0
    for i in (3, 2, 1, 0):
        if i != big:
            v = math.sqrt(0.5) * (comp & 511) / 511.0
            q[i] = -v if (comp >> 9) & 1 else v
            comp >>= 10
            ss += q[i] * q[i]
    q[big] = math.sqrt(max(0.0, 1.0 - ss))
    return tuple(q)


def parse_spz(data):
    """Validate a gzipped SPZ v2/v3 (Niantic; what Aholo World returns) and return parse_ply's (count, columns, []).
    Decoding follows nianticlabs/spz load-spz.cc. Aholo worlds are Z-up (API upAxis Z), so the source (x, y, z) is
    stored as PLY-frame (x, -z, y): to_gltf() then gives glTF (x, z, -y), +Y up. That is a +90 deg turn about X, so
    each quaternion is pre-multiplied by it too. SH bands above DC are skipped (Aholo worlds are SH degree 0)."""
    try:
        d = gzip.decompress(data)
    except (OSError, EOFError, zlib.error) as e:
        raise ValueError(f'not a gzipped SPZ ({e})')
    if len(d) < 16:
        raise ValueError('SPZ header truncated')
    magic, ver, n, deg, frac = struct.unpack_from('<IIIBB', d, 0)
    if magic != 0x5053474E:
        raise ValueError('bad SPZ magic (expected "NGSP")')
    if ver not in (2, 3):
        raise ValueError(f'SPZ version {ver}: only v2/v3 are supported (v4 uses ZSTD streams and a 32-byte header)')
    if deg > 3 or frac > 23:
        raise ValueError(f'unsupported SPZ header: shDegree {deg}, fractionalBits {frac}')
    rb = 3 if ver == 2 else 4  # rotation bytes per splat
    need = 16 + n * (9 + 1 + 3 + 3 + rb + 3 * (0, 3, 8, 15)[deg])
    if len(d) < need:
        raise ValueError(f'SPZ body truncated: {len(d)} < {need} bytes for {n} splats')
    o_alpha, o_col = 16 + 9 * n, 16 + 10 * n
    o_scl, o_rot = o_col + 3 * n, o_col + 6 * n
    unit, c = 1.0 / (1 << frac), math.sqrt(0.5)
    cols = {k: array.array('f') for k in REQUIRED}
    for i in range(n):
        p = 16 + 9 * i
        x, y, z = (int.from_bytes(d[p + 3 * a:p + 3 * a + 3], 'little', signed=True) * unit for a in range(3))
        cols['x'].append(x)
        cols['y'].append(-z)
        cols['z'].append(y)
        a = min(max(d[o_alpha + i] / 255.0, 1.0 / 512), 1.0 - 1.0 / 512)
        cols['opacity'].append(math.log(a / (1.0 - a)))
        for k in range(3):
            cols[f'f_dc_{k}'].append((d[o_col + 3 * i + k] / 255.0 - 0.5) / SPZ_COLOR_SCALE)
            cols[f'scale_{k}'].append(d[o_scl + 3 * i + k] / 16.0 - 10.0)
        qx, qy, qz, qw = spz_quat(d, o_rot + rb * i, ver)
        for k, v in enumerate((c * (qw - qx), c * (qx + qw), c * (qy - qz), c * (qz + qy))):  # (c, c, 0, 0) * q
            cols[f'rot_{k}'].append(v)
    return n, cols, []


def crop(n, cols, max_radius):
    """Keep splats within max_radius (source units) of the median centre. Aholo worlds bake their panorama as a far
    shell of large splats (about 42% of them, at about 105 units); dropping it lets the returned pano be the sky."""
    med = [sorted(cols[k])[n // 2] for k in ('x', 'y', 'z')]
    r2 = max_radius * max_radius
    keep = [i for i in range(n) if sum((cols[k][i] - m) ** 2 for k, m in zip(('x', 'y', 'z'), med)) <= r2]
    return len(keep), {k: array.array('f', (v[i] for i in keep)) for k, v in cols.items()}


def select(n, cols, sh_names, count, seed):
    """Deterministic weighted sample of up to `count` splats, weight = opacity * radius^2.
    Returns (kept source indices ascending, candidate count, summed candidate footprint, rng)."""
    rng = random.Random(seed)
    logit_min = math.log(MIN_OPACITY / (1.0 - MIN_OPACITY))
    X, Y, Z, O = (cols[k] for k in ('x', 'y', 'z', 'opacity'))
    S0, S1, S2 = (cols[f'scale_{j}'] for j in range(3))
    D0, D1, D2 = (cols[f'f_dc_{j}'] for j in range(3))
    Q0, Q1, Q2, Q3 = (cols[f'rot_{j}'] for j in range(4))
    SH = [cols[k] for k in sh_names]
    cand, keys, total = [], [], 0.0
    for i in range(n):
        o = O[i]
        if not o >= logit_min:  # also rejects NaN
            continue
        s0, s1, s2 = S0[i], S1[i], S2[i]
        qq = Q0[i] * Q0[i] + Q1[i] * Q1[i] + Q2[i] * Q2[i] + Q3[i] * Q3[i]
        chk = X[i] + Y[i] + Z[i] + D0[i] + D1[i] + D2[i] + s0 + s1 + s2 + qq
        for col in SH:
            chk += col[i]
        if not (math.isfinite(chk) and max(s0, s1, s2) < MAX_LOG_SCALE and qq > 1e-12):
            continue
        logw = math.log(1.0 / (1.0 + math.exp(-o))) + (s0 + s1 + s2) * (2.0 / 3.0)  # ln(opacity * r^2) + const
        # Efraimidis-Spirakis in log space: smallest ln(Exp(1)) - ln(w) = largest u^(1/w)
        keys.append(math.log(-math.log(1.0 - rng.random()) + 1e-300) - logw)
        cand.append(i)
        total += math.exp(logw)
    best = heapq.nsmallest(min(count, len(cand)), range(len(cand)), key=keys.__getitem__)
    return sorted(cand[j] for j in best), len(cand), total, rng


def build(cols, sh_names, kept, rng, origin=None, covariance=False):
    """Float32 vertex arrays per CHANNELS key + uint32 indices; base at y=0, centered in x/z."""
    X, Y, Z, O = (cols[k] for k in ('x', 'y', 'z', 'opacity'))
    S = [cols[f'scale_{j}'] for j in range(3)]
    D = [cols[f'f_dc_{j}'] for j in range(3)]
    Q = [cols[f'rot_{j}'] for j in range(4)]
    SH = [cols[k] for k in sh_names]
    cen = [to_gltf(X[i], Y[i], Z[i]) for i in kept]
    lo = [min(c[a] for c in cen) for a in range(3)]
    hi = [max(c[a] for c in cen) for a in range(3)]
    off = tuple(origin) if origin is not None else ((lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2)
    if len(off)!=3 or not all(math.isfinite(v) for v in off):
        raise ValueError('origin must contain three finite glTF-space coordinates')
    A = {key: array.array('f') for key in CHANNELS}
    idx = array.array('I')
    e, footprint, radii, support_max = NUDGE_M, 0.0, [], 0.
    if covariance:
        from dream_ellipse import covariance as source_covariance
    for j, i in enumerate(kept):
        cx, cy, cz = (cen[j][a] - off[a] for a in range(3))
        s0, s1, s2 = S[0][i], S[1][i], S[2][i]
        radius = 200.0 * math.exp((s0 + s1 + s2) / 3.0)  # 2 * geometric-mean sigma, in cm
        alpha = 1.0 / (1.0 + math.exp(-O[i]))
        footprint += alpha * math.exp((s0 + s1 + s2) * (2.0 / 3.0))
        radii.append(radius)
        support_max=max(support_max,300*math.exp(max(s0,s1,s2)))
        w, x, y, z = (Q[k][i] for k in range(4))
        qn = 1.0 / math.sqrt(w * w + x * x + y * y + z * z)
        w, x, y, z = w * qn, x * qn, y * qn, z * qn
        if SH:  # 3DGS: rgb += C1 * (-y*k0 + z*k1 - x*k2) = C1 * dot((-k2, -k0, k1), dir)
            k = [col[i] for col in SH]
            R, G, B = (to_gltf(-k[c + 2], -k[c], k[c + 1]) for c in (0, 3, 6))
        else:
            R = G = B = (0.0, 0.0, 0.0)
        A['POSITION'].extend((cx - e, cy - e, cz, cx + e, cy - e, cz, cx + e, cy + e, cz, cx - e, cy + e, cz))
        A['NORMAL'].extend(to_gltf(2 * (x * z + w * y), 2 * (y * z - w * x), 1 - 2 * (x * x + y * y)) * 4)
        A['TANGENT'].extend((*to_gltf(1 - 2 * (y * y + z * z), 2 * (x * y + w * z), 2 * (x * z - w * y)), 1.0) * 4)
        A['TEXCOORD_0'].extend(CORNER_UV)
        A['TEXCOORD_1'].extend((radius, rng.random()) * 4)
        if covariance:
            packed=source_covariance([100*math.exp(v) for v in (s0,s1,s2)],(w,x,y,z))
            for channel,start in (('TEXCOORD_2',0),('TEXCOORD_3',2),('TEXCOORD_4',4)):
                A[channel].extend(packed[start:start+2]*4)
        else:
            A['TEXCOORD_2'].extend((R[0], R[1]) * 4)
            A['TEXCOORD_3'].extend((R[2], G[0]) * 4)
            A['TEXCOORD_4'].extend((G[1], G[2]) * 4)
        A['TEXCOORD_5'].extend((B[0], B[1]) * 4)
        A['TEXCOORD_6'].extend((B[2], 100.0 * math.exp(s0)) * 4)
        A['TEXCOORD_7'].extend((100.0 * math.exp(s1), 100.0 * math.exp(s2)) * 4)
        A['COLOR_0'].extend((*(min(1.0, max(0.0, 0.5 + C0 * d[i])) for d in D), alpha) * 4)
        b = 4 * j
        idx.extend((b, b + 1, b + 2, b, b + 2, b + 3))
    radii.sort()
    return A, idx, {'centers_min': [lo[a] - off[a] for a in range(3)], 'centers_max': [hi[a] - off[a] for a in range(3)],
                    'offset': off, 'footprint': footprint, 'radii': radii,'support_radius_cm_max':support_max}


def gltf_doc(A, idx, name):
    """glTF JSON dict + binary buffer (one bufferView per attribute, tightly packed, little-endian)."""
    blob, views, accs, attrs = bytearray(), [], [], {}

    def add(arr, target):
        if sys.byteorder == 'big':
            arr = array.array(arr.typecode, arr)
            arr.byteswap()
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(arr) * 4, 'target': target})
        blob.extend(arr.tobytes())
        return len(views) - 1

    for key, arr in A.items():
        nc = {'POSITION': 3, 'NORMAL': 3, 'TANGENT': 4, 'COLOR_0': 4}.get(key, 2)
        acc = {'bufferView': add(arr, 34962), 'componentType': 5126, 'count': len(arr) // nc, 'type': f'VEC{nc}'}
        if key == 'POSITION':
            acc['min'] = [min(arr[a::3]) for a in range(3)]
            acc['max'] = [max(arr[a::3]) for a in range(3)]
        attrs[key] = len(accs)
        accs.append(acc)
    accs.append({'bufferView': add(idx, 34963), 'componentType': 5125, 'count': len(idx), 'type': 'SCALAR'})
    doc = {
        'asset': {'version': '2.0', 'generator': 'FoA ply_to_splatmesh.py'},
        'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': name, 'mesh': 0}],
        'meshes': [{'name': name, 'primitives': [
            {'attributes': attrs, 'indices': len(accs) - 1, 'mode': 4}]}],   # no material: Interchange would make an asset
        'buffers': [{'uri': urllib.parse.quote(name + '.bin'), 'byteLength': len(blob)}],
        'bufferViews': views, 'accessors': accs,
    }
    return doc, bytes(blob)


def convert(data, count, seed, name, src='', max_radius=None, lean=False, origin=None,covariance=False):
    """PLY or SPZ bytes -> (glTF dict, bin bytes, sidecar dict)."""
    n, cols, sh_names = parse_spz(data) if data[:2] == b'\x1f\x8b' else parse_ply(data)
    n_src = n
    if max_radius:
        n, cols = crop(n, cols, max_radius)
    kept, n_cand, total, rng = select(n, cols, sh_names, count, seed)
    if not kept:
        raise ValueError(f'no splat has opacity >= {MIN_OPACITY} and sane values')
    if covariance:lean=True
    A, idx, info = build(cols, sh_names, kept, rng, origin=origin,**({'covariance':True} if covariance else {}))
    for k in LEAN_DROP if lean else ():
        if covariance and k in ('TEXCOORD_2','TEXCOORD_3','TEXCOORD_4'):continue
        del A[k]
    doc, blob = gltf_doc(A, idx, name)
    r = info['radii']
    side = {
        'source': src, 'source_splats': n_src, 'after_crop': n, 'max_radius': max_radius, 'candidates': n_cand,
        'splats': len(kept), 'seed': seed, 'sh_degree1': bool(sh_names) and not lean, 'lean': lean,
        'units': 'm, PLY units kept (scale 1.0); UE imports glTF m as cm (x100)',
        'axes': ('glTF (x, y, z) = SPZ Z-up (x, z, -y)' if data[:2] == b'\x1f\x8b' else
                 'glTF (x, y, z) = PLY (x, -y, -z)') + ', then translated by -offset_m',
        'offset_m': [round(v, 6) for v in info['offset']],
        'bounds_m': {'min': [round(v, 5) for v in info['centers_min']],
                     'max': [round(v, 5) for v in info['centers_max']]},
        'radius': 'TEXCOORD_1.x = 2 * geometric mean of exp(scale_i), in cm',
        'radius_cm': {'min': round(r[0], 4), 'median': round(r[len(r) // 2], 4), 'max': round(r[-1], 4)},
        'radius_scale_hint': round(math.sqrt(total / info['footprint']), 2),
        'channels': {k: v for k, v in CHANNELS.items() if k in A},
    }
    if covariance:
        side['covariance']=True
        side['support_radius_cm_max']=info['support_radius_cm_max']
        side['channels'].update(TEXCOORD_2='UE-local covariance Cxx,Cxy in cm²',
            TEXCOORD_3='UE-local covariance Cxz,Cyy in cm²',TEXCOORD_4='UE-local covariance Cyz,Czz in cm²')
    return doc, blob, side


def selftest():
    rnd = random.Random(7)
    f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]

    def ply(rows, names, fmt='binary_little_endian', extra=''):
        head = f'ply\nformat {fmt} 1.0\ncomment synthetic\nelement vertex {len(rows)}\n{extra}'
        head += ''.join(f'property float {p}\n' for p in names) + 'end_header\n'
        return head.encode() + struct.pack(f'<{len(rows) * len(names)}f', *(v for r in rows for v in r))

    def rows_for(names, count, big_every=2):
        out = []
        for i in range(count):
            v = {p: rnd.uniform(-1, 1) for p in names}
            v['opacity'] = rnd.uniform(-6, 6)
            v.update({f'f_dc_{c}': rnd.uniform(-3, 3) for c in range(3)})
            v.update({f'scale_{c}': (-3.0 if i % big_every == 0 else -7.0) + rnd.uniform(-.2, .2) for c in range(3)})
            v.update({f'rot_{c}': rnd.uniform(-2, 2) for c in range(4)})  # unnormalized on purpose
            out.append([v[p] for p in names])
        return out

    # 1. parsing: shuffled property order, unused normals, degree-3 SH in the middle
    rest = [f'f_rest_{j}' for j in range(45)]
    names = ['rot_3', 'opacity', 'nx', 'z', 'y', 'x', 'ny', 'nz', 'f_dc_2', 'f_dc_1', 'f_dc_0'] + rest + \
            ['scale_2', 'scale_1', 'scale_0', 'rot_0', 'rot_1', 'rot_2']
    rows = rows_for(names, 400)
    data = ply(rows, names)
    n, cols, sh = parse_ply(data)
    assert n == 400 and all(list(cols[p]) == [f32(r[names.index(p)]) for r in rows] for p in REQUIRED), 'parse'
    assert sh == [f'f_rest_{c * 15 + k}' for c in range(3) for k in range(3)], 'degree-3 SH: channel-major, 15/channel'
    assert parse_ply(ply(rows_for(list(REQUIRED) + rest[:9], 3), list(REQUIRED) + rest[:9]))[2] == \
        [f'f_rest_{c * 3 + k}' for c in range(3) for k in range(3)], 'degree-1 SH: 3/channel'
    assert parse_ply(ply(rows_for(list(REQUIRED), 3), list(REQUIRED)))[2] == [], 'no f_rest -> no SH'
    for bad in (data[:-4], data.replace(b'binary_little_endian', b'ascii', 1), b'nope' + data,
                ply(rows_for(list(REQUIRED[:-1]), 3), list(REQUIRED[:-1])),
                ply(rows_for(list(REQUIRED) + rest[1:9], 3), list(REQUIRED) + rest[1:9]),
                ply(rows[:3], names, extra='property list uchar int vertex_indices\n')):
        try:
            parse_ply(bad)
        except ValueError:
            continue
        raise AssertionError('malformed PLY accepted')

    # 2. decimation: deterministic, filtered, prefers opaque/large splats
    kept, n_cand, _, _ = select(n, cols, sh, 100, 3)
    assert kept == select(n, cols, sh, 100, 3)[0] and kept != select(n, cols, sh, 100, 4)[0], 'determinism'
    assert len(kept) == 100 and len(select(n, cols, sh, 10 ** 6, 3)[0]) == n_cand < n, 'counts'
    assert all(1 / (1 + math.exp(-cols['opacity'][i])) >= MIN_OPACITY for i in kept), 'opacity filter'
    assert sum(i % 2 == 0 for i in kept) >= 90, 'large splats should dominate the sample'

    # 3. glTF consistency, color/opacity math, SH order and axes, frame, centering
    doc, blob, side = convert(data, 100, 3, 'selftest')
    json.dumps(doc, allow_nan=False)
    accs, views, prim = doc['accessors'], doc['bufferViews'], doc['meshes'][0]['primitives'][0]

    def read(ai):
        a, v = accs[ai], views[accs[ai]['bufferView']]
        arr = array.array('I' if a['componentType'] == 5125 else 'f')
        arr.frombytes(blob[v['byteOffset']:v['byteOffset'] + v['byteLength']])
        return arr

    nv = 400
    assert list(prim['attributes']) == list(CHANNELS) and doc['buffers'][0]['byteLength'] == len(blob)
    for key, ai in prim['attributes'].items():
        nc = int(accs[ai]['type'][-1])
        assert accs[ai]['count'] == nv and len(read(ai)) == nv * nc, f'{key} count'
    I = read(prim['indices'])
    assert accs[prim['indices']]['count'] == len(I) == 600 and max(I) < nv, 'indices'
    assert sum(v['byteLength'] for v in views) == len(blob), 'bufferViews tile the buffer'
    P, U = read(prim['attributes']['POSITION']), {k: read(prim['attributes'][k]) for k in CHANNELS}
    pa = accs[prim['attributes']['POSITION']]
    assert pa['min'] == [min(P[a::3]) for a in range(3)] and pa['max'] == [max(P[a::3]) for a in range(3)], 'bounds'
    cen = [[(P[12 * s + a] + P[12 * s + 6 + a]) / 2 for a in range(3)] for s in range(100)]
    assert abs(min(c[1] for c in cen)) < 1e-6, 'base must sit at y = 0'
    for a in (0, 2):
        assert abs(min(c[a] for c in cen) + max(c[a] for c in cen)) < 1e-5, 'centered horizontally'
    assert len({tuple(P[12 * 7 + 3 * c:12 * 7 + 3 * c + 3]) for c in range(4)}) == 4, 'quad corners distinct'
    assert to_gltf(0, -1, 0) == (0, 1, 0), 'PLY up (-Y) must become glTF +Y'

    def qrot(q, v):  # independent of build(): v' = v + 2w(u x v) + 2u x (u x v)
        n_ = math.sqrt(sum(t * t for t in q))
        w, u = q[0] / n_, [t / n_ for t in q[1:]]
        cr = lambda p, q_: (p[1] * q_[2] - p[2] * q_[1], p[2] * q_[0] - p[0] * q_[2], p[0] * q_[1] - p[1] * q_[0])
        t1 = cr(u, v)
        t2 = cr(u, t1)
        return [v[a] + 2 * w * t1[a] + 2 * t2[a] for a in range(3)]

    for s, i in enumerate(kept):
        c = cols
        rgba = [min(1.0, max(0.0, 0.5 + C0 * c[f'f_dc_{ch}'][i])) for ch in range(3)] + \
               [1 / (1 + math.exp(-c['opacity'][i]))]
        for v in range(4):
            assert all(abs(U['COLOR_0'][16 * s + 4 * v + ch] - rgba[ch]) < 1e-6 for ch in range(4)), 'color/opacity'
        ls = [c[f'scale_{j}'][i] for j in range(3)]
        assert abs(U['TEXCOORD_1'][8 * s] / (200 * math.exp(sum(ls) / 3)) - 1) < 1e-6, 'radius'
        assert len({U['TEXCOORD_1'][8 * s + 2 * v + 1] for v in range(4)}) == 1, 'one seed per splat'
        sig = [U['TEXCOORD_6'][8 * s + 1], U['TEXCOORD_7'][8 * s], U['TEXCOORD_7'][8 * s + 1]]
        assert all(abs(sig[j] / (100 * math.exp(ls[j])) - 1) < 1e-6 for j in range(3)), 'sigmas'
        uv = [U[f'TEXCOORD_{t}'][8 * s + a] for t in range(2, 7) for a in range(2)]
        vec = (uv[0:3], uv[3:6], uv[6:9])
        d = [rnd.uniform(-1, 1) for _ in range(3)]
        for ch in range(3):  # 3DGS formula in PLY axes == stored vector . direction in glTF axes
            k0, k1, k2 = (c[f'f_rest_{ch * 15 + k}'][i] for k in range(3))
            ref = C1 * (-d[1] * k0 + d[2] * k1 - d[0] * k2)
            got = C1 * sum(vec[ch][a] * to_gltf(*d)[a] for a in range(3))
            assert abs(ref - got) < 1e-5, 'SH degree-1 order / sign / axes'
        q = [c[f'rot_{j}'][i] for j in range(4)]
        N, T = U['NORMAL'][12 * s:12 * s + 3], U['TANGENT'][16 * s:16 * s + 4]
        assert all(abs(a - b) < 1e-5 for a, b in zip(N, to_gltf(*qrot(q, (0, 0, 1))))), 'NORMAL = local axis 2'
        assert all(abs(a - b) < 1e-5 for a, b in zip(T, to_gltf(*qrot(q, (1, 0, 0))))) and T[3] == 1.0, 'TANGENT'

    doc0, blob0, side0 = convert(ply(rows_for(list(REQUIRED), 50), list(REQUIRED)), 10, 1, 'sh0')
    sh0 = array.array('f')
    for t in range(2, 6):
        v = doc0['bufferViews'][doc0['accessors'][doc0['meshes'][0]['primitives'][0]['attributes'][f'TEXCOORD_{t}']]['bufferView']]
        sh0.frombytes(blob0[v['byteOffset']:v['byteOffset'] + v['byteLength']])
    assert not any(sh0) and not side0['sh_degree1'], 'missing f_rest -> zero SH'

    # SPZ v2: 3 splats, one far away (the 'shell'). Bytes encode known values (load-spz.cc conventions).
    def fx(v):  # 24-bit fixed point, 12 fractional bits
        return int(round(v * 4096)).to_bytes(3, 'little', signed=True)
    pts = [(1.0, 2.0, 3.0), (-0.5, 0.25, 0.0), (90.0, 0.0, 0.0)]
    body = (b''.join(fx(v) for p in pts for v in p) + bytes((255, 128, 200))
            + bytes((128 + 38, 128, 128) * 3) + bytes((16 * 7, 16 * 7, 16 * 7) * 3)   # f_dc ~1, 0, 0; scale log -3
            + bytes((128, 128, 128) * 3))                                              # xyz ~0 -> identity quat
    spz = gzip.compress(struct.pack('<IIIBBBB', 0x5053474E, 2, 3, 0, 12, 0, 0) + body)
    n, c, sh = parse_spz(spz)
    assert n == 3 and not sh
    assert [(c['x'][0], c['y'][0], c['z'][0])] == [(1.0, -3.0, 2.0)], 'Z-up -> PLY frame (x, -z, y)'
    assert to_gltf(c['x'][0], c['y'][0], c['z'][0]) == (1.0, 3.0, -2.0), 'source z ends up glTF +Y'
    assert abs(c['f_dc_0'][0] - (166 / 255 - 0.5) / 0.15) < 1e-5 and abs(c['scale_0'][0] + 3.0) < 1e-6
    assert c['opacity'][0] > 5 and abs(c['opacity'][1]) < 0.01, 'alpha 255 -> high logit, 128 -> ~0'
    q = [c[f'rot_{k}'][0] for k in range(4)]  # identity turned +90 deg about X: (c, c, 0, 0), up to byte rounding
    assert abs(q[0] - q[1]) < 0.01 and abs(q[0] - math.sqrt(0.5)) < 0.01 and abs(q[2]) < 0.01, q
    try:
        parse_spz(gzip.compress(struct.pack('<IIIBBBB', 0x5053474E, 2, 99, 0, 12, 0, 0) + body))
        raise AssertionError('truncated SPZ accepted')
    except ValueError:
        pass
    # v3: same splats with smallest-three rotations (largest = w, others 0 -> identity), 4 bytes each
    v3 = body[:-9] + bytes((0, 0, 0, 0xC0) * 3)
    n3, c3, _ = parse_spz(gzip.compress(struct.pack('<IIIBBBB', 0x5053474E, 3, 3, 0, 12, 0, 0) + v3))
    assert n3 == 3 and abs(c3['rot_0'][2] - math.sqrt(0.5)) < 1e-6 and abs(c3['rot_1'][2] - math.sqrt(0.5)) < 1e-6
    assert c3['x'][1] == c['x'][1] and c3['opacity'][2] == c['opacity'][2], 'v3 shares the v2 layout up to rotations'
    doc2, blob2, side2 = convert(spz, 10, 1, 'spz', max_radius=10.0, lean=True)
    assert side2['source_splats'] == 3 and side2['after_crop'] == 2, side2
    assert set(doc2['meshes'][0]['primitives'][0]['attributes']) == {'POSITION', 'TEXCOORD_0', 'TEXCOORD_1', 'COLOR_0'}
    print('selftest OK')


def main(argv=None):
    ap = argparse.ArgumentParser(description='3DGS PLY -> billboard splat-mesh glTF (see module docstring).')
    ap.add_argument('input', nargs='?', help='input .ply')
    ap.add_argument('output', nargs='?', help='output .gltf (writes .bin and .splatmesh.json next to it)')
    ap.add_argument('--count', type=int, default=40000, help='target splat count (default 40000)')
    ap.add_argument('--seed', type=int, default=1, help='decimation / per-splat seed (default 1)')
    ap.add_argument('--max-radius', type=float, help='drop splats farther than this (source units) from the median '
                    'centre, e.g. 20 for an Aholo world (removes the baked panorama shell)')
    ap.add_argument('--lean', action='store_true', help='write POSITION, TEXCOORD_0/1, COLOR_0 only (see LEAN_DROP)')
    ap.add_argument('--origin',type=float,nargs=3,help='fixed glTF-space offset in metres; preserve a placed mesh frame when changing density')
    ap.add_argument('--selftest', action='store_true', help='run the built-in checks and exit')
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.input and a.output and a.output.lower().endswith('.gltf') and a.count > 0):
        ap.error('usage: IN.ply|IN.spz OUT.gltf [--count N>0] [--seed S] [--max-radius R] [--lean]')
    with open(a.input, 'rb') as f:
        data = f.read()
    stem = os.path.splitext(a.output)[0]
    name = os.path.basename(stem)
    try:
        doc, blob, side = convert(data, a.count, a.seed, name, src=os.path.abspath(a.input),
                                  max_radius=a.max_radius, lean=a.lean, origin=a.origin)
    except ValueError as e:  # malformed / unsupported PLY: report, don't trace
        ap.error(f'{a.input}: {e}')
    del data
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(stem + '.bin', 'wb') as f:
        f.write(blob)
    with open(a.output, 'w', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'), allow_nan=False)
    with open(stem + '.splatmesh.json', 'w', encoding='utf-8') as f:
        json.dump(side, f, indent=1, allow_nan=False)
    size = os.path.getsize(stem + '.bin') + os.path.getsize(a.output)
    b = side['bounds_m']
    print(f'{name}: {side["splats"]} of {side["source_splats"]} splats ({side["candidates"]} candidates), '
          f'{size / 2**20:.1f} MB, size m {[round(b["max"][k] - b["min"][k], 3) for k in range(3)]}, '
          f'radius_cm median {side["radius_cm"]["median"]}, radius_scale_hint {side["radius_scale_hint"]}')


if __name__ == '__main__':
    sys.exit(main())
