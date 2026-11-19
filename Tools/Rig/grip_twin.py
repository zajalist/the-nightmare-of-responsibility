"""Anim lane's pose-authoring helpers for the grip twin (rig's hand_twin.py owns loading, conversions, clearance and
renders; anim owns the poses). Blender world, metres; a `rig` is hand_twin.load_teen()'s rom_audit.Rig.
Self-check: pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/grip_twin.py selftest=1"""
import math
import sys

import bpy
from mathutils import Matrix, Vector


def reset_bones(rig, names):
    for b in names:
        if b in rig.ob.pose.bones:
            rig.ob.pose.bones[b].matrix_basis.identity()
    bpy.context.view_layer.update()


def two_bone(rig, side, wrist, pole):
    """Aim upperarm and lowerarm so the wrist lands on `wrist`, the elbow bending toward `pole`. Returns the miss (m)."""
    s, e, w = rig.head(f"upperarm_{side}"), rig.head(f"lowerarm_{side}"), rig.head(f"hand_{side}")
    a, b = (e - s).length, (w - e).length
    to = wrist - s
    d = min(max(to.length, abs(a - b) + 1e-4), a + b - 1e-4)
    dirn = to.normalized()
    x = (a * a - b * b + d * d) / (2 * d)
    h = math.sqrt(max(0.0, a * a - x * x))
    side_v = (pole - s) - dirn * (pole - s).dot(dirn)
    elbow = s + dirn * x + side_v.normalized() * h
    rig.aim(f"upperarm_{side}", elbow - s)
    rig.aim(f"lowerarm_{side}", wrist - rig.head(f"lowerarm_{side}"))
    return (rig.head(f"hand_{side}") - wrist).length


def aim_hand(rig, side, d_want, n_want):
    """Turn the hand (with its fingers) so its anatomical finger direction is d_want and its palm normal n_want."""
    d, n = rig.dir(f"hand_{side}"), rig.world(f"hand_{side}", rig.axes[f"hand_{side}"]["n"])
    n = (n - d * n.dot(d)).normalized()
    n_want = (n_want - d_want * n_want.dot(d_want)).normalized()
    cur = Matrix((d, n, d.cross(n))).transposed()
    want = Matrix((d_want.normalized(), n_want, d_want.normalized().cross(n_want))).transposed()
    axis, ang = (want @ cur.inverted()).to_quaternion().to_axis_angle()
    if abs(ang) > 1e-6:
        rig.rot(f"hand_{side}", axis, math.degrees(ang))


def descend(f, x, steps, keys, lo, hi):
    """Coordinate descent on a dict of parameters, coarse to fine steps; returns (best x, best cost)."""
    best = f(x)
    for st in steps:
        improved = True
        while improved:
            improved = False
            for k in keys:
                for dv in (-st[k], st[k]):
                    y = dict(x)
                    y[k] = min(hi[k], max(lo[k], y[k] + dv))
                    c = f(y)
                    if c < best - 1e-4:
                        best, x, improved = c, y, True
    return x, best


def perturb(f, x, keys, step, lo, hi, iters=300, seed=7):
    """Random joint moves (2-4 parameters at once, fine steps): escapes the coordinate-wise minima descend() stops in."""
    import random
    rnd = random.Random(seed)
    best = f(x)
    for _ in range(iters):
        y = dict(x)
        for k in rnd.sample(keys, rnd.randint(2, min(4, len(keys)))):
            y[k] = min(hi[k], max(lo[k], y[k] + rnd.uniform(-1.5, 1.5) * step[k]))
        c = f(y)
        if c < best - 1e-4:
            best, x = c, y
    return x, best


UE_EXPORT = "P:/FoA-Assets/character/mpfb/ue_export"
ANCHORS = "P:/FoA/Saved/AnimShots/grip_anchors.json"
BODY_Z = 3.094446780476119  # the Body component sits this far above the actor's floor point (key_pinch_capture 'seated')


def load_ue_mesh(name):
    """A static mesh exported from the game (Tools/Unreal/player/export_grip_meshes.py) under an empty frame whose
    local space is the twin's UE-mesh convention (UE local, Y mirrored, metres): the FBX lands that way; UCX collision
    hulls are dropped. Asserts the import against the editor's bounds."""
    import json
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=f"{UE_EXPORT}/{name}.fbx")
    new = [o for o in bpy.data.objects if o not in before]
    frame = bpy.data.objects.new(name + "_frame", None)
    bpy.context.scene.collection.objects.link(frame)
    for o in new:
        if o.name.startswith("UCX_"):
            bpy.data.objects.remove(o)
            continue
        mw = o.matrix_world.copy()
        o.parent = frame
        o.matrix_world = mw
    bpy.context.view_layer.update()
    lo, hi = json.load(open(f"{UE_EXPORT}/index.json"))[name]["local_box"]
    pts = [o.matrix_world @ Vector(c) for o in frame.children if o.type == "MESH" for c in o.bound_box]
    got = [min(p.x for p in pts) * 100, -max(p.y for p in pts) * 100, min(p.z for p in pts) * 100]
    assert all(abs(g - e) < 1.0 for g, e in zip(got, lo)), (name, got, lo)
    return frame


def ue_matrix(loc, quat, scale):
    """A UE world transform as a Blender matrix (the Y mirror conjugates rotations, so products carry over)."""
    import hand_twin as H
    sc = scale if hasattr(scale, "__len__") else (scale,) * 3
    return Matrix.LocRotScale(H.ue_to_bl_loc(loc), H.ue_to_bl_quat(quat), Vector(sc))


def body_matrix(x, y, yaw_deg, floor_z=0.0, scale=170.0 / 180.0):
    """The game Body's world transform for an actor standing at (x, y) facing yaw_deg (UE degrees): the mesh is turned
    -90 deg under the actor, BODY_Z above the floor, shown at 170/180."""
    import math
    yaw = math.radians(yaw_deg - 90.0)
    return ue_matrix((x, y, floor_z + BODY_Z), (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2)), scale)


def place_in_body(frame, obj_world, body_world):
    """Put an object frame at its game transform as seen from the unscaled twin body standing at body_world."""
    frame.matrix_world = body_world.inverted() @ obj_world
    bpy.context.view_layer.update()


def ue_frame(m):
    """A Blender world matrix (an object frame) as the UE component-space transform the bake needs: location cm,
    rotation (x, y, z, w), scale. The twin's root is the Body's component origin (the twin body is unscaled: the bake
    multiplies positions by 170/180)."""
    import hand_twin as H
    loc, rot, sc = m.decompose()
    return dict(loc=H.bl_to_ue_loc(loc), quat=H.bl_to_ue_quat(rot), scale=tuple(sc))


def share_twist(rig, side, share=0.6):
    """What the game's ABP_FoA_TeenPost does: the forearm twist bone takes `share` of the hand's roll about the forearm
    (without it the twin's wrist pinches like a candy wrapper)."""
    tw = f"lowerarm_twist_01_{side}"
    if tw not in rig.ob.pose.bones:
        return 0.0
    rig.ob.pose.bones[tw].matrix_basis.identity()
    bpy.context.view_layer.update()
    axis = (rig.head(f"hand_{side}") - rig.head(f"lowerarm_{side}")).normalized()
    lo = rig.mat(f"lowerarm_{side}").to_3x3().normalized()
    hand = rig.mat(f"hand_{side}").to_3x3().normalized()
    rest_rel = rig.rest[f"lowerarm_{side}"].to_3x3().normalized().inverted() @ rig.rest[f"hand_{side}"].to_3x3().normalized()
    q = (hand @ (lo @ rest_rel).inverted()).to_quaternion()  # the hand's turn since rest, relative to the forearm
    twist = 2.0 * math.degrees(math.atan2(Vector((q.x, q.y, q.z)).dot(axis), q.w))
    twist = (twist + 180.0) % 360.0 - 180.0
    rig.rot(tw, axis, share * twist)
    return twist


def thumb_chain(rig, side, j2, j3, along, roll):
    """Aim the metacarpal, then flex the two hinges toward the palm; never free-aim a thumb hinge backwards."""
    rig.aim(f"thumb_01_{side}", j2 - rig.head(f"thumb_01_{side}"))
    rig.rot(f"thumb_01_{side}", rig.dir(f"thumb_01_{side}"), roll)
    for joint, target, limit in ((2, j3-rig.head(f'thumb_02_{side}'), 70), (3, along, 80)):
        bone = f'thumb_0{joint}_{side}'
        d = rig.dir(bone).normalized()
        axis = d.cross(rig.world(bone,rig.axes[bone]['n'])).normalized()
        target = (target-axis*target.dot(axis)).normalized()
        degrees = math.degrees(math.atan2(axis.dot(d.cross(target)),d.dot(target)))
        rig.flex(bone,max(8.,min(limit,degrees)))


class HandSkin:
    """One hand's skin vertices by numpy linear-blend skinning (what the Armature modifier does): ~1 ms instead of the
    ~0.1 s whole-body evaluated mesh. Built with a check against the evaluated mesh (asserts < 0.05 mm).
    rows: {("index", "02"): [row, ...], ("hand",): [...], ("forearm",): [...]} index the returned array by bone. The
    forearm (lowerarm and its twist bones) is in it for clearance: the screwdriver solves of 2026-11-10 hid the handle's
    butt inside the wrist, where a hand-only check never looked."""

    def __init__(self, rig, side, check=True):
        import numpy as np
        import rom_audit as R
        self.np, self.rig = np, rig
        dom, _ = R.labels(rig)
        digits = ("thumb", "index", "middle", "ring", "pinky")
        self.idx = [i for i, b in enumerate(dom) if b.endswith("_" + side)
                    and (b.split("_")[0] in digits or b.startswith("hand") or b.startswith("lowerarm"))]
        self.rows = {}
        for r, i in enumerate(self.idx):
            parts = tuple(dom[i][:-2].split("_"))
            key = parts if parts[0] in digits else ("forearm",) if parts[0] == "lowerarm" else ("hand",)
            self.rows.setdefault(key, []).append(r)
        me, arm = rig.body.data, rig.ob
        names = {g.index: g.name for g in rig.body.vertex_groups}
        deform = {b.name for b in arm.data.bones if b.use_deform}
        ws = [{names[g.group]: g.weight for g in me.vertices[i].groups if names.get(g.group) in deform and g.weight > 0}
              for i in self.idx]
        self.bones = sorted(set().union(*ws))
        col = {b: k for k, b in enumerate(self.bones)}
        W = np.zeros((len(self.idx), len(self.bones)))
        for r, w in enumerate(ws):
            for b, x in w.items():
                W[r, col[b]] = x
        self.W = W / np.maximum(W.sum(1, keepdims=True), 1e-9)  # the modifier normalises the contributions
        self.rest = np.array([(*me.vertices[i].co, 1.0) for i in self.idx])
        if check:
            co, _ = R.evaluated(rig.body)
            err = float(np.abs(self() - np.array([tuple(co[i]) for i in self.idx])).max())
            assert err < 5e-5, f"HandSkin is {err * 1000:.3f} mm off the evaluated mesh"

    def __call__(self):
        arm, body = self.rig.ob, self.rig.body
        A, Ai, B = arm.matrix_world, arm.matrix_world.inverted(), body.matrix_world
        M = self.np.array([[list(r) for r in A @ arm.pose.bones[b].matrix @ arm.data.bones[b].matrix_local.inverted() @ Ai @ B]
                           for b in self.bones])
        return self.np.einsum("nb,bij,nj->ni", self.W, M, self.rest)[:, :3]


def body_clear_mm(rig, trees, scale=1.0):
    """The closest the rest of the body (torso, legs, the other arm, the upper arm) comes to the objects, mm x scale,
    with the bone it belongs to: the hand checks cover the hand and forearm only, and a 42 cm hanger or a door can
    still run through a knee or a chest. One evaluated-mesh read (final reports only)."""
    import rom_audit as R
    dom, _ = R.labels(rig)
    co, _ = R.evaluated(rig.body)
    best = (99.0, "")
    for i, b in enumerate(dom):
        if b.endswith("_r") and (b.split("_")[0] in ("thumb", "index", "middle", "ring", "pinky") or b.startswith(("hand", "lowerarm"))):
            continue
        d = signed_mm(trees, co[i], scale)
        if abs(d) > 30.0:  # far away the nearest face's normal is no inside test (a slab's end face reads "inside"); a
            continue        # body part crossing a surface always leaves vertices near it, and those are measured
        if d < best[0]:
            best = (d, b)
    return round(best[0], 2), best[1]


def signed_mm(trees, p, scale=1.0):
    """Signed distance (mm x scale; negative = inside) from a world point to the nearest surface of several BVH trees."""
    best, v = None, Vector(p)
    for t in trees:
        loc, nrm, _, dist = t.find_nearest(v)
        if loc is not None and (best is None or dist < best[0]):
            best = (dist, -dist if (v - loc).dot(nrm) < 0 else dist)
    return best[1] * 1000 * scale if best else 99.0


SEGS = ("01", "02", "03")


def close_digits(pose, measure, digits, full, target_mm=1.6, scan=6, bisect=5, start=None):
    """GraspIt-style closing. pose({digit: [a01, a02, a03]}) resets and poses the digits (degrees of curl);
    measure(segs) -> {digit: min signed mm of that digit's skin on those segments}. Stage 1 closes all three joints
    together toward `full` until the digit is target_mm off; stage 2 closes 02 and 03 on, stage 3 03 alone; each stage
    measures only the segments that move, so a proximal contact holds while the distal joints wrap. Returns the angles."""
    ang = {d: list(start[d]) if start else [0.0, 0.0, 0.0] for d in digits}  # start: a pre-shape (e.g. cupped)
    for joints in ((0, 1, 2), (1, 2), (2,)):
        segs = tuple(SEGS[j] for j in joints)
        start = {d: list(ang[d]) for d in digits}

        def at(t):
            return {d: [start[d][j] + (t[d] * (full[d][j] - start[d][j]) if j in joints else 0.0) for j in range(3)]
                    for d in digits}
        lo, hi = {d: 0.0 for d in digits}, {d: None for d in digits}
        for k in range(1, scan + 1):  # coarse first, so a thin object is not jumped: the first touching sample brackets it
            t = {d: (k / scan if hi[d] is None else lo[d]) for d in digits}
            pose(at(t))
            m = measure(segs)
            for d in digits:
                if hi[d] is None:
                    if m[d] >= target_mm:
                        lo[d] = t[d]
                    else:
                        hi[d] = t[d]
            if all(h is not None for h in hi.values()):
                break
        for _ in range(bisect):
            if all(h is None for h in hi.values()):
                break
            t = {d: ((lo[d] + hi[d]) / 2 if hi[d] is not None else lo[d]) for d in digits}
            pose(at(t))
            m = measure(segs)
            for d in digits:
                if hi[d] is not None:
                    if m[d] >= target_mm:
                        lo[d] = t[d]
                    else:
                        hi[d] = t[d]
        ang = at(lo)
    pose(ang)
    return ang


def approach(set_x, gap, lo, hi, target_mm=1.6, steps=8):
    """The smallest x in [lo, hi] whose gap() >= target_mm (gap grows with x, e.g. the palm's distance out from an
    object): bisection. set_x(x) poses; returns x, posed (hi when even hi touches)."""
    set_x(lo)
    if gap() >= target_mm:
        return lo
    a, b = lo, hi
    for _ in range(steps):
        m = (a + b) / 2
        set_x(m)
        if gap() >= target_mm:
            b = m
        else:
            a = m
    set_x(b)
    return b


if __name__ == "__main__" and "selftest=1" in sys.argv:
    sys.path.insert(0, "P:/FoA/Tools/Rig")
    import hand_twin as H
    rig, _ = H.load_teen(garments=())
    target = rig.head("hand_l") + Vector((0.0, -0.15, 0.25))
    miss = two_bone(rig, "l", target, rig.head("upperarm_l") + Vector((0.3, 0.0, -0.3)))
    aim_hand(rig, "l", Vector((0, -1, 0)), Vector((0, 0, 1)))
    d, n = rig.dir("hand_l"), rig.world("hand_l", rig.axes["hand_l"]["n"])
    assert miss < 1e-3, miss
    n = (n - d * n.dot(d)).normalized()  # the anatomical palm normal is not square to the finger line
    assert d.dot(Vector((0, -1, 0))) > 0.999 and n.dot(Vector((0, 0, 1))) > 0.999, (d, n)
    skin = HandSkin(rig, "l")  # asserts against the evaluated mesh
    import bmesh
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=0.035)  # a ball held over the proximal phalanges
    bmesh.ops.translate(bm, verts=bm.verts, vec=(rig.head("middle_01_l") + rig.head("middle_02_l")) / 2 + n * 0.055)
    tree = BVHTree.FromBMesh(bm)
    digits = ("index", "middle", "ring", "pinky")

    def pose(a):
        reset_bones(rig, [f"{d}_{j}_l" for d in digits for j in SEGS])
        for d in digits:
            for j, x in zip(SEGS, a[d]):
                rig.flex(f"{d}_{j}_l", x)

    def measure(segs):
        co = skin()
        return {d: min(signed_mm([tree], co[r]) for sg in segs for r in skin.rows[(d, sg)]) for d in digits}
    ang = close_digits(pose, measure, digits, {d: (90.0, 100.0, 70.0) for d in digits})
    m = measure(SEGS)
    assert all(v >= 1.0 for v in m.values()) and all(m[d] <= 3.5 for d in digits[:3]), (m, ang)  # stopped on it, not in it
    assert all(sum(ang[d]) > 30 for d in digits[:3]), ang
    print("GRIP_TWIN selftest passed", round(miss * 1000, 3), "mm; closed on a ball", {d: round(v, 2) for d, v in m.items()},
          {d: [round(x) for x in a] for d, a in ang.items()})
