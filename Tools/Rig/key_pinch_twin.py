"""Rusted-key turn, solved at MESH level in the Blender twin (anim lane; the user's screenshot 2026-11-10: "the hand here
is also completely broken": a pale blob hovering near the bow). Rig's hand_twin.py loads, converts, checks and
renders; this script authors the pose and the stand.
Why it broke: the pawn stood upright 45.6 cm from a key 89 cm off the floor; the shoulder is about 78 cm from the key
in the twin, past the arm's reach, so the IK fell short. The anchor fixes the stand: the pawn leans in (spine forward,
knees soft), and stands where the right forearm can line up with the key.
Grip (right hand, lateral key pinch): the bow between the thumb pad and the radial side of the index middle phalanx,
both 1-3 mm off the bow; no skin vertex within 1 mm of the key or the door; middle/ring/pinky curled clear.
The turn (D/A, +-45 deg about the key axis) turns the hand with the key; the check repeats at -45, 0, +45.
In-game frame (Saved/Integration/key_pinch_capture.json, 'seated'): Body at (325, 48.5, 3.09), yaw -90, scale 170/180;
key at (370.6, 48.5, 88.5), identity, scale 0.682; key contact (door face) x 374.35. In the twin (unscaled Teen
component space): key (0 + side, 48.28 + forward, 90.43) yaw +90 at scale 0.722.
Writes Saved/RigShots/key_pinch/{fp,side,turn_m45_fp,turn_p45_fp}.png, check.json and key_pinch_solution.json
(UE locals for the stance and the hand, the hand in the key frame, the stand). Nothing is baked here.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/key_pinch_twin.py [rounds=3] [resume=1]"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/key_pinch"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = 170.0 / 180.0
KEY_Z = (88.5 - 3.094446780476119) / BODY_SCALE  # key height above the Body root, twin cm
KEY_SCALE = 0.6818181818181818 / BODY_SCALE
KEY_YAW = (0.0, 0.0, math.sin(math.radians(45)), math.cos(math.radians(45)))  # UE quat, yaw +90: key +X -> twin +Y
KEY_HALF = (5.5, 0.656, 2.089)  # key mesh local half extents (cm), key_local_bounds
BOW_X = -3.4  # key-local x (mesh cm) below which the key is its bow (ring)
GRIP_X = -4.5  # the pinch on the bow's ring (mesh cm; the bow spans -5.5..-3.5). The old in-game target (-2.8) was on the stem
DIG = ("index", "middle", "ring", "pinky")
TURN = [0.0, None]  # the key's current turn (deg) and its unturned axis, for the elbow pole


def stance(rig, st):
    """The lock-plate stance (main 2026-11-10: one kneel for the key and the screwdriver; no standing lean to 89 cm):
    down on the right knee, left foot planted forward, torso upright, leaning in by st['lean'] (deg over the spine).
    The root drops until the right knee and the left sole reach the floor."""
    G.reset_bones(rig, [b.name for b in rig.ob.pose.bones])
    rig.ob.location.z = 0.0
    bpy.context.view_layer.update()
    floor = min(rig.head("foot_l").z, rig.head("foot_r").z)  # the ankles' height above the floor at rest
    fw, up = Vector((0, -1, 0)), Vector((0, 0, 1))
    rig.aim("thigh_l", fw + up * -0.25 + Vector((0.12, 0, 0)))  # front leg: thigh about level, shin upright, foot flat
    rig.aim("calf_l", -up + fw * 0.05)
    rig.aim("foot_l", fw - up * 0.35)
    rig.aim("thigh_r", -up + fw * 0.12 + Vector((-0.08, 0, 0)))  # kneeling leg: thigh down, shin back along the floor
    rig.aim("calf_r", -fw - up * 0.12)
    rig.aim("foot_r", -fw - up * 0.6)
    for b in rig.spine_chain():
        rig.rot(b, Vector((1.0, 0.0, 0.0)), st["lean"] / len(rig.spine_chain()))  # about +X (his left), + bends him forward
    rig.aim("upperarm_l", -up + fw * 0.35 + Vector((0.12, 0, 0)))  # the left hand rests on the left knee
    rig.aim("lowerarm_l", fw * 0.9 - up * 0.45)
    knee = rig.head("calf_r").z - 0.05  # kneecap skin about 5 cm in front of/below the joint
    sole = rig.head("foot_l").z - floor
    rig.ob.location.z -= min(knee, sole)
    bpy.context.view_layer.update()


def key_frame(key):
    M = key.matrix_world
    return M, [M.to_3x3().col[i].normalized() for i in range(3)]


def place_key(key, stand):
    H.place(key, (stand["side"], 48.28 + stand["fwd"], KEY_Z), KEY_YAW, (KEY_SCALE,) * 3)


def make_door(key):
    """A stand-in door slab flush with the key's tip (the knob is not modelled until the editor dump)."""
    M, (kx, ky, kz) = key_frame(key)
    tip = M @ Vector((KEY_HALF[0] / 100, 0, 0))
    me = bpy.data.meshes.new("door")
    w, h, t = 0.45, 0.6, 0.04
    c = [tip + kx * (0.0 if sx == 0 else t) + ky * sy * w + kz * sz * h for sx in (0, 1) for sy in (-1, 1) for sz in (-1, 1)]
    me.from_pydata(c, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    ob = bpy.data.objects.new("door_standin", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


class RealDoor:
    """real=1: the game's door around the key, from the editor dump: SM_Door_Bedroom (with its knob), the lock plate and
    its four screws, each an exported FBX at its world transform, seen from the twin body. The body's world frame is
    whatever puts the twin's key on the game's key (370.6, 48.5, 88.5, identity, scale 0.682: key_pinch_capture
    'seated'). The stand-in slab was a bare mesh object, which H._tree never read (it walks a frame's children): the
    door was never in the old clearance check."""
    KEY_WORLD = ((370.6, 48.5, 88.5), (0.0, 0.0, 0.0, 1.0), 0.6818181818181818)

    def __init__(self):
        dump = json.load(open(G.ANCHORS))["Door_Bedroom"]
        self.parts = []
        for c in dump["comps"]:
            name = (c.get("mesh") or "").split(".")[-1]
            if c.get("visible") and name in ("SM_Door_Bedroom", "SM_DoorLockPlate", "SM_DoorLockScrew"):
                self.parts.append((G.load_ue_mesh(name), G.ue_matrix(c["world"]["loc"], c["world"]["quat"], c["world"]["scale"])))
        self.key_world = G.ue_matrix(*self.KEY_WORLD)

    def place(self, key):
        body = self.key_world @ key.matrix_world.inverted()  # the body's world frame that lands the twin key on the game's
        for frame, world in self.parts:
            G.place_in_body(frame, world, body)
        return [f for f, _ in self.parts]


def place_hand(rig, key, p):
    """The right hand in the key frame: finger line toward the door (key +x) turned by yaw/pitch, palm normal from -ky
    rolled about it, the hand bone at (hx, hy, hz) cm in the key frame; the arm reaches it, elbow down and out."""
    M, (kx, ky, kz) = key_frame(key)
    d = (Matrix.Rotation(math.radians(p["yaw"]), 3, kz) @ Matrix.Rotation(math.radians(p["pitch"]), 3, ky) @ kx).normalized()
    n0 = -ky - d * (-ky).dot(d)
    n = (Matrix.Rotation(math.radians(p["roll"]), 3, d) @ n0).normalized()
    grip = M @ Vector((GRIP_X / 100, 0, 0)) + kz * p["gz"] / 100
    wrist = grip + kx * p["hx"] / 100 + ky * p["hy"] / 100 + kz * p["hz"] / 100
    G.reset_bones(rig, ["upperarm_r", "lowerarm_r", "hand_r"] + [b for b in rig.names if "twist" in b and b.endswith("_r")])
    # the elbow swings out with 70% of the key's turn, so the turn is shared by forearm roll and elbow (D/A)
    pole = rig.head("upperarm_r") + Matrix.Rotation(math.radians(0.7 * TURN[0]), 3, TURN[1] or kx) @ Vector((-0.25, 0.0, -0.35))
    miss = G.two_bone(rig, "r", wrist, pole)
    G.aim_hand(rig, "r", d, n)
    G.share_twist(rig, "r")
    return miss


def fingers(rig, key, c, gz=0.0):
    """Index curled round the bow's far face; middle/ring/pinky tucked; the thumb by construction onto the near face."""
    G.reset_bones(rig, [f"{dg}_{j}_r" for dg in DIG + ("thumb",) for j in ("01", "02", "03")])
    for j, f in zip(("01", "02", "03"), (c["i1"], c["i2"], c["i3"])):
        rig.flex(f"index_{j}_r", f)
    for dg in DIG[1:]:
        for j, f in zip(("01", "02", "03"), (1.0, 1.1, 0.7)):
            rig.flex(f"{dg}_{j}_r", c["tuck"] * f)
    M, (kx, ky, kz) = key_frame(key)
    at = lambda x, y, z: M @ Vector((GRIP_X / 100, 0, 0)) + kx * x / 100 + ky * y / 100 + kz * (z + gz) / 100  # noqa: E731
    G.thumb_chain(rig, "r", at(c["t2x"], c["t2y"], c["t2z"]), at(c["t3x"], c["t3y"], c["t3z"]),
                  (kx * c["along"] + kz * 0.3 - ky * c["press"]).normalized(), c["roll"])


class Fast:
    def __init__(self, rig, R, objects):
        dom, _ = R.labels(rig)
        self.R, self.rig, self.dom = R, rig, dom
        # the forearm too (2026-11-10: the screwdriver hid its handle in the wrist, where a hand-only check never looked)
        self.hand = [i for i, b in enumerate(dom) if b.endswith("_r") and (b.split("_")[0] in H.DIGITS or b.startswith("hand") or b.startswith("lowerarm"))]
        reg = H.regions(rig, "r")
        self.pad, self.radial = sorted(reg.get("thumb_pad", ())), sorted(reg.get("index_02_radial", ()))
        self.objects = objects

    def __call__(self, key):
        tree, _ = H._tree(self.objects)
        co, _ = self.R.evaluated(self.rig.body)
        sd = {}
        for i in self.hand:
            loc, nrm, _, dist = tree.find_nearest(co[i])
            sd[i] = (-dist if (co[i] - loc).dot(nrm) < 0 else dist) * 1000 * BODY_SCALE if loc is not None else 99.0
        bow = self.bow_tree(key)  # the pinch contacts count on the bow's ring only (v3 pinched the stem next to it)

        def to_bow(i):
            loc, nrm, _, dist = bow.find_nearest(co[i])
            return (-dist if (co[i] - loc).dot(nrm) < 0 else dist) * 1000 * BODY_SCALE if loc is not None else 99.0
        contact = set(self.pad) | set(self.radial)
        others = [sd[i] for i in self.hand if i not in contact]
        pen = sum(max(0.0, 1.2 - v) ** 2 for v in sd.values())
        pad = min(to_bow(i) for i in self.pad)
        rad = min(to_bow(i) for i in self.radial)
        M, (kx, ky, kz) = key_frame(key)
        c = M.translation
        side = lambda idx: sum((co[i] - c).dot(ky) for i in idx) / max(1, len(idx))  # noqa: E731
        between = side(self.pad) * side(self.radial) < 0  # the bow is between the thumb pad and the index side
        vis = self.bow_visible(co, key)
        fa = (self.rig.head("hand_r") - self.rig.head("lowerarm_r")).normalized()
        wrist = math.degrees(fa.angle(self.rig.dir("hand_r")))
        ua = (self.rig.head("lowerarm_r") - self.rig.head("upperarm_r")).normalized()
        elbow = 180 - math.degrees(ua.angle(fa))
        eye = H.ue_point(self.rig, "head", H.EYE_HEAD)
        grip = M @ Vector((GRIP_X / 100, 0, 0))
        ray = (grip - eye).normalized()
        view = math.degrees(ray.angle(kx))  # 0 = looking down the key's axis (the 'lollipop'); main wants a 3/4 view
        fwd = ray
        up0 = Vector((0, 0, 1))
        right = fwd.cross(up0).normalized()
        upv = right.cross(fwd).normalized()
        half_v = math.tan(math.radians(40.0)) * 9.0 / 16.0  # the game camera: 80 deg horizontal at 16:9
        ys = [(co[i] - eye).dot(upv) / max(1e-6, (co[i] - eye).dot(fwd)) for i in self.hand[::4]]
        proj = lambda v: Vector(((v - eye).dot(right) / (v - eye).dot(fwd), (v - eye).dot(upv) / (v - eye).dot(fwd)))  # noqa: E731
        tip2 = proj(M @ Vector((KEY_HALF[0] / 100, 0, 0))) - proj(grip)
        img = math.degrees(math.atan2(abs(tip2.x), abs(tip2.y)))  # 0 = the shaft straight up the frame
        fill = (max(ys) - min(ys)) / (2 * half_v)  # the hand's height as a fraction of the frame
        return dict(clear_min_mm=round(min(others), 2), pen=round(pen, 2), pad_mm=round(pad, 2), radial_mm=round(rad, 2),
                    view_deg=round(view, 1), img_deg=round(img, 1), fill=round(fill, 2),
                    between=between, wrist_deg=round(wrist, 1), elbow_deg=round(elbow, 1),
                    forearm_to_key_deg=round(math.degrees(fa.angle(kx)), 1), bow_visible=round(vis, 2))

    def bow_tree(self, key):
        """A BVH of the key's bow faces (key-local x below BOW_X), in the key's current world placement."""
        dg = bpy.context.evaluated_depsgraph_get()
        cos, polys = [], []
        inv = key.matrix_world.inverted()
        for o in H.meshes_of(key):
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(cos)
            w = [o.matrix_world @ v.co for v in me.vertices]
            cos += w
            polys += [tuple(base + i for i in pl.vertices) for pl in me.polygons if all((inv @ w[i]).x * 100 < BOW_X for i in pl.vertices)]
            ev.to_mesh_clear()
        return BVHTree.FromPolygons(cos, polys)

    def bow_visible(self, co, key):
        """The fraction of the bow's vertices the eye sees past the hand (rays; main: at least half)."""
        if not hasattr(self, "bow"):
            tree, kco = H._tree([key])
            inv = key.matrix_world.inverted()
            self.bow = [inv @ v for v in kco if (inv @ v).x * 100 < BOW_X][::max(1, len(kco) // 400)]
        eye = H.ue_point(self.rig, "head", H.EYE_HEAD)
        hs = set(self.hand)
        tree = BVHTree.FromPolygons(co, [tuple(p.vertices) for p in self.rig.body.data.polygons if p.vertices[0] in hs])
        seen = 0
        for lv in self.bow:
            v = key.matrix_world @ lv
            d = v - eye
            seen += tree.ray_cast(eye, d.normalized(), d.length - 0.001)[0] is None
        return seen / max(1, len(self.bow))


def cost(m):
    c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"])
    c += 25 * (max(0.0, 1.2 - m["pad_mm"]) + max(0.0, m["pad_mm"] - 2.8) + max(0.0, 1.2 - m["radial_mm"]) + max(0.0, m["radial_mm"] - 2.8))
    c += 0 if m["between"] else 200
    c += 0.5 * max(0.0, m["wrist_deg"] - 25) + 2.0 * (max(0.0, 87 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 118))  # main: 85-120
    c += 1.5 * (max(0.0, 32 - m["img_deg"]) + max(0.0, m["img_deg"] - 60))  # the shaft diagonal in the frame (3/4), not upright
    c += 150 * (max(0.0, 0.25 - m["fill"]) + max(0.0, m["fill"] - 0.33))  # the hand fills a quarter to a third of the frame
    c += 0.5 * (max(0.0, 30 - m["forearm_to_key_deg"]) + max(0.0, m["forearm_to_key_deg"] - 45))  # seen from above and to the side
    c += 60 * max(0.0, 0.55 - m["bow_visible"])
    return c


def ok(m):
    return (m["clear_min_mm"] >= 1.0 and 1.0 <= m["pad_mm"] <= 3.0 and 1.0 <= m["radial_mm"] <= 3.0 and m["between"]
            and m["wrist_deg"] <= 35 and 85 <= m["elbow_deg"] <= 120 and 28 <= m["forearm_to_key_deg"] <= 47
            and m["bow_visible"] >= 0.5 and 30 <= m["img_deg"] <= 62 and 0.23 <= m["fill"] <= 0.34)


def main():
    rig, R = H.load_teen()
    key = H.load_object("key")
    st = dict(lean=8.0, side=-18.0, fwd=0.0)  # the stand: lean, and the key's offset from the pawn root (cm, twin)
    place = dict(yaw=0.0, pitch=0.0, roll=0.0, hx=-7.0, hy=-1.5, hz=0.0, gz=-0.6)
    grip = dict(i1=55.0, i2=70.0, i3=30.0, tuck=70.0, t2x=-4.0, t2y=2.0, t2z=1.0, t3x=-1.5, t3y=1.6, t3z=0.5, along=1.0,
                press=0.1, roll=0.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        last = json.load(open(prev))
        st, place, grip = last["stand"], last["place"], last["grip"]
        st["fwd"] = min(-3.3, max(-13.3, st["fwd"]))
        st["lean"] = min(10.0, max(5.0, st["lean"]))  # main: a 5-10 deg forward lean
    door = None
    real = RealDoor() if ARGS.get("real") == "1" else None

    def setup(s):
        nonlocal door
        stance(rig, s)
        place_key(key, s)
        if real:
            door = real.place(key)
            return
        if door:
            bpy.data.objects.remove(door)
        door = make_door(key)

    def objects():
        return [key] + (door if real else [door])
    setup(st)
    fast = Fast(rig, R, objects())

    def ev(s, pl, gr, redo_stance=False):
        if redo_stance:
            setup(s)
            fast.objects = objects()
        # the wrist at the ends of the +-45 deg turn (joints only, cheap): main allows about 50
        M0 = key.matrix_world.copy()
        kx0 = M0.to_3x3().col[0].normalized()
        turn0 = list(TURN)
        turn_wrist = []
        for ang in (-45.0, 45.0):
            key.matrix_world = Matrix.Translation(M0.translation) @ Matrix.Rotation(math.radians(ang), 4, kx0) @ Matrix.Translation(-M0.translation) @ M0
            bpy.context.view_layer.update()
            TURN[:] = [ang, kx0]
            place_hand(rig, key, pl)
            fa = (rig.head("hand_r") - rig.head("lowerarm_r")).normalized()
            turn_wrist.append(math.degrees(fa.angle(rig.dir("hand_r"))))
        key.matrix_world = M0
        bpy.context.view_layer.update()
        TURN[:] = turn0
        miss = place_hand(rig, key, pl)
        fingers(rig, key, gr, pl["gz"])
        m = fast(key)
        m["turn_wrist_deg"] = round(max(turn_wrist), 1)
        return m, cost(m) + 5000 * miss + 1.0 * max(0.0, m["turn_wrist_deg"] - 50.0)

    slo, shi = dict(lean=5, side=-35, fwd=-13.3), dict(lean=10, side=0, fwd=-3.3)  # main: the key 35-45 cm from the pawn root
    sst = [dict(lean=5, side=3, fwd=3), dict(lean=2, side=1, fwd=1)]
    plo, phi = dict(yaw=-60, pitch=-60, roll=-200, hx=-14, hy=-6, hz=-6, gz=-1.2), dict(yaw=60, pitch=60, roll=200, hx=-2, hy=6, hz=6, gz=0.6)
    pst = [dict(yaw=10, pitch=10, roll=20, hx=1.0, hy=0.8, hz=0.8, gz=0.3), dict(yaw=4, pitch=4, roll=6, hx=0.4, hy=0.3, hz=0.3, gz=0.1)]
    glo = dict(i1=0, i2=0, i3=0, tuck=20, t2x=-9, t2y=-4, t2z=-4, t3x=-6, t3y=-3, t3z=-3, along=-0.5, press=-0.4, roll=-90)
    ghi = dict(i1=100, i2=110, i3=80, tuck=100, t2x=1, t2y=5, t2z=4, t3x=2, t3y=4, t3z=3, along=1.5, press=0.6, roll=90)
    gst = [dict(i1=10, i2=10, i3=10, tuck=10, t2x=0.8, t2y=0.6, t2z=0.6, t3x=0.6, t3y=0.4, t3z=0.4, along=0.2, press=0.1, roll=15),
           dict(i1=4, i2=4, i3=4, tuck=4, t2x=0.3, t2y=0.2, t2z=0.2, t3x=0.2, t3y=0.15, t3z=0.15, along=0.08, press=0.04, roll=5)]
    rounds = []
    if ARGS.get("resume") != "1":
        starts = []
        for r0 in (-90.0, 0.0, 90.0, 180.0):
            for y0 in (-30.0, 30.0):
                pl = dict(place, roll=r0, yaw=y0)
                pl, c0 = G.descend(lambda q: ev(st, q, grip)[1], pl, pst, list(pl), plo, phi)
                starts.append((c0, pl))
                print("KEY start", r0, y0, round(c0, 2), json.dumps(ev(st, pl, grip)[0]), flush=True)
        place = min(starts, key=lambda t: t[0])[1]
    for rnd in range(int(ARGS.get("rounds", 3))):
        st, _ = G.descend(lambda s: ev(s, place, grip, True)[1], st, sst, list(st), slo, shi)
        ev(st, place, grip, True)
        place, _ = G.descend(lambda pl: ev(st, pl, grip)[1], place, pst, list(place), plo, phi)
        grip, _ = G.descend(lambda gr: ev(st, place, gr)[1], grip, gst, list(grip), glo, ghi)
        both = dict(place, **{"g_" + k: v for k, v in grip.items()})  # joint moves over the hand and the grip together
        split = lambda b: ({k: b[k] for k in place}, {k: b["g_" + k] for k in grip})  # noqa: E731
        blo = dict(plo, **{"g_" + k: v for k, v in glo.items()})
        bhi = dict(phi, **{"g_" + k: v for k, v in ghi.items()})
        bst = dict(pst[1], **{"g_" + k: v for k, v in gst[1].items()})
        both, _ = G.perturb(lambda b: ev(st, *split(b))[1], both, list(both), bst, blo, bhi, iters=int(ARGS.get("iters", 250)))
        place, grip = split(both)
        m, c = ev(st, place, grip)
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("KEY round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    hold, _ = ev(st, place, grip)
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    M, (kx, ky, kz) = key_frame(key)
    grip_pt = M @ Vector((GRIP_X / 100, 0, 0))
    verdict = dict(check=H.check(rig, objects(), "r", contacts={"thumb_pad": 3.0, "index_02_radial": 3.0}))
    H.render_fp(rig, eye, grip_pt, os.path.join(OUT, "fp.png"))
    H.render_side(rig, grip_pt, -kx + ky * 0.6 + kz * 0.3, os.path.join(OUT, "side.png"), dist_m=0.3)
    pose0 = H.export_ue_local(rig)
    hand0 = H.ue_bone(rig, "hand_r")
    turns = {}
    for ang in (-45, 45):  # the key turns about its axis; the hand turns with it (pinch fixed on the bow)
        rot = Matrix.Rotation(math.radians(ang), 4, kx)
        TURN[:] = [ang, kx.copy()]
        pivot = M.translation
        key.matrix_world = Matrix.Translation(pivot) @ rot @ Matrix.Translation(-pivot) @ M
        bpy.context.view_layer.update()
        m, _ = ev(st, place, grip)
        turns[ang] = m
        H.render_fp(rig, eye, grip_pt, os.path.join(OUT, f"turn_{'m' if ang < 0 else 'p'}45_fp.png"))
        key.matrix_world = M
        bpy.context.view_layer.update()
    TURN[:] = [0.0, None]
    ev(st, place, grip)
    # at the ends of a +-45 deg turn the wrist may deviate to 55 deg and the forearm leave the 30-45 band (the hold keeps
    # it: the eye needs to see the bow); a key turned 45 deg about an axis 30 deg off the forearm costs about 20 deg of wrist
    turn_ok = all(m["clear_min_mm"] >= 1.0 and m["between"] and m["wrist_deg"] <= 52 and m["bow_visible"] >= 0.5 for m in turns.values())
    hold["body_clear"] = G.body_clear_mm(rig, [H._tree(fast.objects)[0]], BODY_SCALE)
    passed = ok(hold) and verdict["check"]["pass"] and turn_ok and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, turns=turns, verdict=verdict, stand=st, place=place, grip=grip, rounds=rounds)
    json.dump(rep, open(prev, "w"), indent=1)
    print("KEY_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, turns=turns, rig_pass=verdict["check"]["pass"],
                                                                      contacts=verdict["check"]["contacts"])))
    sol = dict(stand=dict(key_offset_twin_cm=dict(side=st["side"], fwd=st["fwd"]), lean=st["lean"], kneel="right knee down"),
               pose=pose0, hand_ue=dict(location=hand0[0], rotation=hand0[1]),
               key_ue=dict(location=(st["side"], 48.28 + st["fwd"], KEY_Z), rotation=KEY_YAW, scale=KEY_SCALE), twin=rep)
    json.dump(sol, open("P:/FoA/Saved/AnimShots/key_pinch_solution.json", "w"))
    print("KEY_SOLUTION written")


main()
