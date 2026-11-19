"""Root fix of the Teen rig on the as-imported FBXs (the live SK_Teen_* sources), keeping hierarchy, names, every
non-finger bone frame, geometry, UVs, normals, slots and morphs:
  1. finger + thumb joints moved to anatomical places (Buchholz 1992 hand proportions, anchored on the Teen's own wrist
     joint and fingertips); every phalanx gets a clean frame: Y along the bone, local +X = curl hinge, so a positive
     rotation about local X curls toward the palm, the same on both hands;
  2. leaf twist bones lowerarm_twist_01_l/r (child of lowerarm, at 2/3 of the forearm like Manny's), with the forearm
     weights fading onto them toward the wrist (the body and the suit sleeves);
  3. hand weights rebuilt from the new joints: per-finger isolation by distance to each finger's axis, smooth blends
     across knuckle, PIP and DIP; the thumb keeps its thenar region, with its MCP/IP blends moved to the new joints.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/fix_teen_rig.py out=<dir> [pieces=Body,Suit,Pants] [Body=<fbx>] [Suit=<fbx>] [Pants=<fbx>]
Writes <dir>/SK_Teen_<piece>.fbx and <dir>/rigfix_report.json. Never touches the source FBXs or any .blend."""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(__file__))
import fbx_io  # noqa: E402

A = dict(x.split("=", 1) for x in sys.argv[sys.argv.index("--") + 1:] if "=" in x)
X = "P:/FoA-Assets/character/mpfb/export/"
SRC = {"Body": X + "teen_chest_flattened/SK_Teen_Body.fbx", "Suit": X + "teen_cm/SK_Teen_Suit.fbx",
       "Pants": X + "teen_cm/SK_Teen_Pants.fbx"}
SRC.update({k: v for k, v in A.items() if k in SRC})  # e.g. Body=<new export>/SK_Teen_Body.fbx after a fresh export_ue.py
OUT = A.get("out", X + "teen_rigfix")
PIECES = A.get("pieces", "Body,Suit").split(",")
FINGERS = ("index", "middle", "ring", "pinky")
# wrist->knuckle share of wrist->tip, then proximal / middle phalanx shares of knuckle->tip (distal = the rest).
# Buchholz et al. 1992 segment ratios, nudged toward the UE5 Manny so retargeted curls land the same way.
RATIOS = {"index": (0.49, 0.485, 0.283), "middle": (0.46, 0.472, 0.301), "ring": (0.46, 0.455, 0.308),
          "pinky": (0.50, 0.47, 0.27)}
THUMB = (0.40, 0.31)  # CMC->tip: metacarpal, proximal phalanx shares
BLEND = {"k": 1.4, "p": 0.45, "d": 0.35, "t1": 0.7, "t2": 0.4}  # half-widths of the weight blends, cm
TWIST_AT = 0.667


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def at(path, s):
    """Point at arc length s along a polyline (clamped)."""
    for a, b in zip(path, path[1:]):
        seg = (b - a).length
        if s <= seg:
            return a + (b - a) * (s / seg)
        s -= seg
    return path[-1]


def length(path):
    return sum((b - a).length for a, b in zip(path, path[1:]))


def closest(path, p):
    """(distance, arc length) of the closest point of polyline `path` to p; s < 0 extends the first segment back."""
    best, s0 = (1e9, 0.0), 0.0
    for i, (a, b) in enumerate(zip(path, path[1:])):
        d = b - a
        L = d.length
        t = (p - a).dot(d) / (L * L)
        t = t if i == 0 and t < 0 else min(1.0, max(0.0, t))
        q = a + d * t
        dist = (p - q).length
        if dist < best[0]:
            best = (dist, s0 + t * L)
        s0 += L
    return best


def labels(mesh):
    names = {g.index: g.name for g in mesh.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups if g.weight > 1e-6} for v in mesh.data.vertices]


def set_weights(mesh, rows, bones):
    """Write rows (list of {bone: w}) back for the given bone set only."""
    groups = {b: (mesh.vertex_groups.get(b) or mesh.vertex_groups.new(name=b)) for b in bones}
    for i, w in enumerate(rows):
        for b, g in groups.items():
            x = w.get(b, 0.0)
            if x > 1e-5:
                g.add([i], x, "REPLACE")
            else:
                g.remove([i])


def cap_influences(rows, keep=8):
    out = []
    for w in rows:
        if len(w) > keep:
            top = dict(sorted(w.items(), key=lambda kv: -kv[1])[:keep])
            s0, s1 = sum(w.values()), sum(top.values())
            w = {k: v * s0 / s1 for k, v in top.items()}
        out.append(w)
    return out


# ---------------------------------------------------------------------------------------------------------------
def plan_joints(rig, body):
    """New armature-space joint positions and hinge axes per side, from the current joints and the fingertips."""
    inv = rig.matrix_world.inverted()
    rest = {b.name: b.head_local.copy() for b in rig.data.bones}
    w = labels(body)
    co = [inv @ (body.matrix_world @ v.co) for v in body.data.vertices]
    plan = {}
    for s in "lr":
        wrist = rest[f"hand_{s}"]
        P = {}
        for f in FINGERS + ("thumb",):
            j = [rest[f"{f}_0{k}_{s}"] for k in (1, 2, 3)]
            d = (j[2] - j[1]).normalized()
            dist = [i for i, x in enumerate(w) if x and max(x, key=x.get) == f"{f}_03_{s}"]
            tip = j[2] + d * max((co[i] - j[2]).dot(d) for i in dist)
            if f == "thumb":
                path = [j[0], j[1], j[2], tip]
                L = length(path)
                new = [j[0], at(path, THUMB[0] * L), at(path, (THUMB[0] + THUMB[1]) * L), tip]
            else:
                ks, p1, p2 = RATIOS[f]
                path = [wrist, j[0], j[1], j[2], tip]
                L = length(path)
                sk = ks * L
                lf = L - sk
                new = [at(path, sk), at(path, sk + p1 * lf), at(path, sk + (p1 + p2) * lf), tip]
            P[f] = {"old": [list(x) for x in j], "new": new, "tip": tip}
        k = (P["pinky"]["new"][0] - P["index"]["new"][0]).normalized()
        fd = (P["middle"]["new"][1] - P["middle"]["new"][0]).normalized()
        n = k.cross(fd).normalized()
        mid = (P["index"]["new"][0] + P["pinky"]["new"][0]) / 2
        if (P["thumb"]["tip"] - mid).dot(n) < 0:
            n = -n  # palm side: where the thumb sits
        palm = (wrist + P["middle"]["new"][0] + P["pinky"]["new"][0] + P["index"]["new"][0]) / 4 + n * 1.2
        P["_n"], P["_k"], P["_palm"], P["_wrist"] = n, k, palm, wrist
        plan[s] = P
    return plan


def hinge(f, d, joint, P):
    """Curl hinge: positive rotation about it turns the bone toward the palm."""
    toward = P["_n"] if f != "thumb" else (P["_palm"] - joint)
    toward = toward - d * toward.dot(d)
    return d.cross(toward.normalized()).normalized()


def edit_skeleton(rig, plan):
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    report = {}
    for s, P in plan.items():
        for f in FINGERS + ("thumb",):
            pts = P[f]["new"]
            for i in range(3):
                b = eb[f"{f}_0{i + 1}_{s}"]
                b.use_connect = False
                b.head, b.tail = pts[i], pts[i + 1]
                d = (pts[i + 1] - pts[i]).normalized()
                h = hinge(f, d, pts[i], P)
                b.align_roll(h.cross(d))  # Z = h x Y, so local +X = h
                report[b.name] = {"moved_cm": round((Vector(P[f]["old"][i]) - pts[i]).length, 2),
                                  "x_dot_hinge": round(b.x_axis.dot(h), 4)}
        la, hd = eb[f"lowerarm_{s}"], eb[f"hand_{s}"]
        name = f"lowerarm_twist_01_{s}"
        t = eb.get(name) or eb.new(name)
        t.head = la.head + (hd.head - la.head) * TWIST_AT
        t.tail = hd.head.copy()
        t.roll = la.roll
        t.parent, t.use_connect, t.use_deform = la, False, True
        report[name] = {"axis_dot_lowerarm": round(t.y_axis.dot(la.y_axis), 5), "z_dot": round(t.z_axis.dot(la.z_axis), 5)}
    bpy.ops.object.mode_set(mode="OBJECT")
    return report


def twist_weights(mesh, rig):
    """Forearm weight fades onto the twist bone toward the wrist (0 at 15%, all of it at 85% of the forearm)."""
    inv = rig.matrix_world.inverted()
    rows = labels(mesh)
    moved = 0
    for s in "lr":
        e, wr = rig.data.bones[f"lowerarm_{s}"].head_local, rig.data.bones[f"hand_{s}"].head_local
        ax = wr - e
        for i, v in enumerate(mesh.data.vertices):
            w = rows[i]
            x = w.get(f"lowerarm_{s}", 0.0)
            if x <= 0:
                continue
            p = inv @ (mesh.matrix_world @ v.co)
            frac = smooth(0.15, 0.85, (p - e).dot(ax) / ax.length_squared)
            if frac > 0:
                w[f"lowerarm_{s}"] = x * (1 - frac)
                w[f"lowerarm_twist_01_{s}"] = w.get(f"lowerarm_twist_01_{s}", 0.0) + x * frac
                moved += 1
    bones = [f"lowerarm_{s}" for s in "lr"] + [f"lowerarm_twist_01_{s}" for s in "lr"]
    set_weights(mesh, rows, bones)
    return moved


def bisector_blend(p, a, j, b, width):
    """0 before joint j, 1 after it: signed distance to the plane that bisects the bend at j (continuous everywhere)."""
    n = ((j - a).normalized() + (b - j).normalized()).normalized()
    return smooth(-width, width, (p - j).dot(n))


def chain_profile(p, pts, widths):
    """Weights over [parent, 01, 02, 03] for a digit whose joints are pts[1..3] (pts[0] = parent joint, pts[4] = tip)."""
    a = bisector_blend(p, pts[0], pts[1], pts[2], widths[0])
    b = bisector_blend(p, pts[1], pts[2], pts[3], widths[1])
    c = bisector_blend(p, pts[2], pts[3], pts[4], widths[2])
    return [1 - a, a * (1 - b), a * b * (1 - c), a * b * c]


def smooth_weights(mesh, rows, bones, idx, iters=2):
    """Laplacian smoothing of the given bones' weights over the vertices idx; each vertex keeps its total."""
    nbr = {i: set() for i in idx}
    for e in mesh.data.edges:
        a, b = e.vertices
        if a in nbr and b in nbr:
            nbr[a].add(b)
            nbr[b].add(a)
    for _ in range(iters):
        new = {}
        for i in idx:
            if not nbr[i]:
                continue
            tot = sum(rows[i].get(x, 0.0) for x in bones)
            avg = {x: sum(rows[k].get(x, 0.0) for k in nbr[i]) / len(nbr[i]) for x in bones}
            mix = {x: 0.5 * rows[i].get(x, 0.0) + 0.5 * avg[x] for x in bones}
            s = sum(mix.values())
            new[i] = {x: v * tot / s for x, v in mix.items()} if s > 1e-9 else {}
        for i, w in new.items():
            for x in bones:
                rows[i].pop(x, None)
            rows[i].update({x: v for x, v in w.items() if v > 1e-4})


def hand_weights(body, rig, plan):
    inv = rig.matrix_world.inverted()
    rows = labels(body)
    changed = []
    for s, P in plan.items():
        chains = {f: [P["_wrist"]] + P[f]["new"] for f in FINGERS}
        thumb = [P["_wrist"]] + P["thumb"]["new"]  # wrist, CMC, MCP, IP, tip
        finger_bones = {f: [f"{f}_0{k}_{s}" for k in (1, 2, 3)] for f in FINGERS + ("thumb",)}
        hand = f"hand_{s}"
        for i, v in enumerate(body.data.vertices):
            w = rows[i]
            thumb_mass = sum(w.get(b, 0.0) for b in finger_bones["thumb"])
            fmass = w.get(hand, 0.0) + sum(w.get(b, 0.0) for f in FINGERS for b in finger_bones[f])
            if fmass + thumb_mass <= 1e-6:
                continue
            p = inv @ (body.matrix_world @ v.co)
            new = {hand: 0.0}
            if fmass > 1e-6:
                ds = {f: closest(chains[f][1:], p)[0] for f in FINGERS}
                dmin = min(ds.values())
                m = {f: math.exp(-(x - dmin) / 0.35) for f, x in ds.items()}
                tot = sum(m.values())
                for f in FINGERS:
                    pr = chain_profile(p, chains[f], (BLEND["k"], BLEND["p"], BLEND["d"]))
                    new[hand] += fmass * m[f] / tot * pr[0]
                    for b, x in zip(finger_bones[f], pr[1:]):
                        new[b] = new.get(b, 0.0) + fmass * m[f] / tot * x
            if thumb_mass > 1e-6:  # the thumb keeps its thenar region; only its MCP and IP blends move
                a = bisector_blend(p, thumb[1], thumb[2], thumb[3], BLEND["t1"])
                c = bisector_blend(p, thumb[2], thumb[3], thumb[4], BLEND["t2"])
                for b, x in zip(finger_bones["thumb"], (1 - a, a * (1 - c), a * c)):
                    new[b] = new.get(b, 0.0) + thumb_mass * x
            for b in [hand] + [b for f in finger_bones.values() for b in f]:
                w.pop(b, None)
            w.update({b: x for b, x in new.items() if x > 1e-4})
            changed.append(i)
        bones = [hand] + [b for f in finger_bones.values() for b in f]
        smooth_weights(body, rows, bones, [i for i in changed if any(b in rows[i] for b in bones)])
    rows = cap_influences(rows)
    bones = [f"hand_{s}" for s in "lr"] + [f"{f}_0{k}_{s}" for s in "lr" for f in FINGERS + ("thumb",) for k in (1, 2, 3)]
    set_weights(body, rows, bones)
    return len(changed)


def knee_weights(mesh, rig, radius=13.0, iters=8):
    """Widen and smooth the thigh/calf blend around each knee so deep flex folds the cloth instead of crossing it."""
    inv = rig.matrix_world.inverted()
    rows = labels(mesh)
    n = 0
    for s in "lr":
        kn = rig.data.bones[f"calf_{s}"].head_local
        bones = [f"thigh_{s}", f"calf_{s}"]
        idx = [i for i, v in enumerate(mesh.data.vertices)
               if (inv @ (mesh.matrix_world @ v.co) - kn).length < radius and any(b in rows[i] for b in bones)]
        smooth_weights(mesh, rows, bones, idx, iters)
        n += len(idx)
    set_weights(mesh, rows, [f"{b}_{s}" for s in "lr" for b in ("thigh", "calf")])
    return n


def main():
    os.makedirs(OUT, exist_ok=True)
    fbx_io.clear()
    rig, meshes = fbx_io.load(SRC["Body"])
    body = meshes[0]
    plan = plan_joints(rig, body)
    report = {"plan": {s: {f: {"old": P[f]["old"], "new": [list(x) for x in P[f]["new"]]} for f in FINGERS + ("thumb",)}
                       for s, P in plan.items()}}
    report["bones"] = edit_skeleton(rig, plan)
    report["hand_verts_reweighted"] = hand_weights(body, rig, plan)
    report["twist_verts_body"] = twist_weights(body, rig)
    rows = labels(body)
    report["body_max_influences"] = max(len(r) for r in rows)
    report["body_weight_sum_range"] = [round(min(sum(r.values()) for r in rows), 4), round(max(sum(r.values()) for r in rows), 4)]
    rig_names = {b.name for b in rig.data.bones}
    edited = {b.name: (b.head_local.copy(), b.tail_local.copy(), b.matrix_local.copy()) for b in rig.data.bones}
    if "Body" in PIECES:
        fbx_io.export(rig, body, os.path.join(OUT, "SK_Teen_Body.fbx"))
    for piece in [p for p in PIECES if p != "Body"]:
        fbx_io.clear()
        r2, ms = fbx_io.load(SRC[piece])
        m = ms[0]
        bpy.context.view_layer.objects.active = r2
        bpy.ops.object.mode_set(mode="EDIT")  # same skeleton as the body: copy the edited rest frames
        for name, (h, t, mtx) in edited.items():
            eb = r2.data.edit_bones.get(name) or r2.data.edit_bones.new(name)
            if name.startswith("lowerarm_twist"):
                eb.parent = r2.data.edit_bones[name.replace("_twist_01", "")]
                eb.use_deform = True
            eb.use_connect = False
            eb.matrix = mtx
            eb.head, eb.tail = h, t
            eb.matrix = mtx
        bpy.ops.object.mode_set(mode="OBJECT")
        report[f"twist_verts_{piece}"] = twist_weights(m, r2)
        if piece in ("Pants", "Suit"):
            report[f"knee_verts_{piece}"] = knee_weights(m, r2)
        assert {b.name for b in r2.data.bones} >= rig_names
        fbx_io.export(r2, m, os.path.join(OUT, f"SK_Teen_{piece}.fbx"))
    with open(os.path.join(OUT, "rigfix_report.json"), "w") as f:
        json.dump(report, f, indent=1, default=list)
    print("RIGFIX done", {k: v for k, v in report.items() if k not in ("plan", "bones")})


main()
