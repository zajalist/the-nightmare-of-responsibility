"""The phone in the left hand by grasp synthesis (anim lane, 2026-11-10; the user on the cradle: "the fingers look broken",
judge it against photos of a real one-handed hold). A real hold, from the reference photos: the phone rests on the
curled fingers and the palm heel; index, middle and ring wrap the right edge with their tips showing; the thumb lies on
the glass in a relaxed arc; the wrist is bent back so the palm heel shows; the forearm rises from the bottom left.
The cradle solved curls and the thumb by construction (flat fingers, a straight thumb). Here the hand is placed
behind the phone and every digit CLOSES until it touches (grip_twin.close_digits on an analytic box: SM_Phone 14.7 x
7.1 x 0.98 cm), so each joint curls naturally; the search is only the hand's placement on the back, its turn, the
elbow and the thumb's base. The phone sits where the game pins it (phone_cradle_twin's READ, variant v2: lower).
Gates: no hand or forearm skin within 1 mm of the phone; >= 2 of index/middle/ring tips past the right edge; the
thumb pad 1-3 mm over the glass inside the screen; screen >= 80% visible from the eye; every finger joint curled
>= 8 deg (no flat-board fingers); wrist bent 15-35 deg; the forearm rising >= 25 deg toward the phone.
Writes Saved/RigShots/phone_grasp/{hold_fp,hold_side,hold_under}.png, check.json and (if it passes, or force=1)
Saved/AnimShots/phone_grasp_solution.json in bake_phone_grip.py's solution format.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/phone_grasp_twin.py [rounds=2] [resume=1] [force=1]"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

sys.argv += [] if "variant=v2" in sys.argv else ["variant=v2"]  # the phone where v2 puts it: lower in frame
sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402
import phone_cradle_twin as PC  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/phone_grasp"
os.makedirs(OUT, exist_ok=True)
K, HX, HY, HZ = PC.K, PC.HX, PC.HY, PC.HZ
DIG = ("thumb", "index", "middle", "ring", "pinky")
FULL = {d: (85.0, 95.0, 65.0) for d in DIG[1:]}
FULL["thumb"] = (55.0, 70.0, 80.0)  # v1 at (30, 50, 60) never reached the glass
TARGET = 2.0


def box_mm(q):
    """Signed distance (game mm) from a phone-local point (m) to the phone box."""
    dx, dy, dz = abs(q.x) - HX, abs(q.y) - HY, abs(q.z) - HZ
    return (Vector((max(dx, 0), max(dy, 0), max(dz, 0))).length + min(max(dx, dy, dz), 0.0)) * 1000 * K


def pose_digits(rig, p, ang):
    G.reset_bones(rig, [f"{dg}_{j}_l" for dg in DIG for j in G.SEGS])
    for i, dg in enumerate(DIG[1:]):
        rig.spread(f"{dg}_01_l", p["spread"] * (i - 1.5))
    rig.spread("thumb_01_l", p["t1s"])
    rig.rot("thumb_01_l", rig.dir("thumb_01_l"), p["t1r"])
    for dg in DIG:
        for j, a in zip(G.SEGS, ang.get(dg, (0.0, 0.0, 0.0))):
            rig.flex(f"{dg}_{j}_l", a)


def place_hand(rig, phone, p, gap_cm):
    """The phone's left edge in the thumb web (the reference photos): the palm faces the eye (-z local) turned `yaw`
    deg about the phone's long axis toward its right edge, so the palm takes the left back corner, the fingers go round
    the back to the right edge and the thumb comes over the glass. The finger line runs toward the right edge turned
    `theta` deg up the phone, rolled `roll` about itself. The palm backs off the point (px, py) cm (phone centre plane)
    along its normal by gap_cm; the wrist `back` cm behind it; the elbow swung `elbow` deg from down-by-his-side.
    v1-v2 had the palm square behind the phone: the thumb closed fully behind it and never reached the glass."""
    M = phone.matrix_world
    X, Y, Z = (M.to_3x3().col[i].normalized() for i in range(3))
    th = math.radians(p["theta"])
    d0 = (Y * math.cos(th) + X * math.sin(th)).normalized()
    turn = Matrix.Rotation(math.radians(p["yaw"]), 3, X)
    d = (turn @ d0).normalized()
    n = (turn @ (Matrix.Rotation(math.radians(p["roll"]), 3, d0) @ -Z)).normalized()
    palm = M @ Vector((p["px"] / 100, p["py"] / 100, 0.0)) - n * gap_cm / 100
    wrist = palm - d * p["back"] / 100
    G.reset_bones(rig, ["upperarm_l", "lowerarm_l", "hand_l"] + [b for b in rig.names if "twist" in b and b.endswith("_l")])
    sh = rig.head("upperarm_l")
    pole = sh + Matrix.Rotation(math.radians(p["elbow"]), 3, (wrist - sh).normalized()) @ Vector((0.12, -0.08, -0.45))
    miss = G.two_bone(rig, "l", wrist, pole)
    G.aim_hand(rig, "l", d, n)
    G.share_twist(rig, "l")
    return miss


class Grasp:
    def __init__(self, rig, phone, eye):
        self.rig, self.phone, self.eye = rig, phone, eye
        self.skin = G.HandSkin(rig, "l")
        sk = self.skin
        self.rows_all = list(range(len(sk.idx)))
        self.approach_rows = sk.rows[("hand",)] + sk.rows[("forearm",)][::2] + [r for d in DIG for s in G.SEGS for r in sk.rows.get((d, s), [])[::2]]
        self.seg_rows = {(d, s): sk.rows.get((d, s), [])[::1 if s == "03" else 2] for d in DIG for s in G.SEGS}
        pos = {i: r for r, i in enumerate(sk.idx)}
        self.polys = [tuple(pos[v] for v in pl.vertices) for pl in rig.body.data.polygons if all(v in pos for v in pl.vertices)]
        self.tips = {d: sk.rows.get((d, "03"), []) for d in DIG}

    def local(self, co):
        inv = self.phone.matrix_world.inverted()
        return [inv @ Vector(c) for c in co]

    def dist(self, rows):
        q = self.local(self.skin())
        return min((box_mm(q[r]) for r in rows), default=99.0)

    def __call__(self, p):
        rig, miss = self.rig, [0.0]
        pre = {d: (p["cup"], p["cup"], p["cup"] * 0.7) for d in DIG[1:]}
        pre["thumb"] = (0.0, p["cup"] * 0.4, p["cup"] * 0.4)
        pose_digits(rig, p, pre)

        def set_gap(g):
            miss[0] = place_hand(rig, self.phone, p, g)
        G.approach(set_gap, lambda: self.dist(self.approach_rows), 0.2, 10.0, TARGET)

        def seg(digits, segs):
            q = self.local(self.skin())
            return {dg: min((box_mm(q[r]) for s in segs for r in self.seg_rows[(dg, s)]), default=99.0) for dg in digits}
        fang = G.close_digits(lambda a: pose_digits(rig, p, dict(a, thumb=pre["thumb"])), lambda s: seg(DIG[1:], s), DIG[1:], FULL, TARGET, start=pre)
        tang = G.close_digits(lambda a: pose_digits(rig, p, dict(fang, **a)), lambda s: seg(("thumb",), s), ("thumb",), FULL, TARGET,
                              start={"thumb": pre["thumb"]})
        co = self.skin()
        q = self.local(co)
        sd = [box_mm(v) for v in q]
        past = [dg for dg in ("index", "middle", "ring") if max((q[r].y for r in self.tips[dg]), default=-1) > HY]
        glass = [r for r in self.tips["thumb"] if q[r].z < 0]
        low = min(glass, key=lambda r: -HZ - q[r].z, default=None)
        pad = None if low is None else round((-HZ - q[low].z) * 1000 * K, 2)
        inside = 0.0 if low is None else min(HX - 0.004 - abs(q[low].x), HY - 0.004 - abs(q[low].y)) * 100 * K
        tree = BVHTree.FromPolygons([Vector(c) for c in co], self.polys)
        seen = n = 0
        for ix in range(-6, 7):
            for iy in range(-3, 4):
                pt = self.phone.matrix_world @ Vector((ix / 6 * (HX - 0.003), iy / 3 * (HY - 0.003), -HZ - 0.0001))
                dv = pt - self.eye
                n += 1
                seen += tree.ray_cast(self.eye, dv.normalized(), dv.length - 1e-4)[0] is None
        fa = (rig.head("hand_l") - rig.head("lowerarm_l")).normalized()
        rise = math.degrees(math.asin(max(-1.0, min(1.0, fa.z))))  # the forearm's climb toward the hand
        flat = [f"{dg}{j + 1}" for dg in DIG[1:] for j, a in enumerate(fang[dg]) if a < 8.0]
        return dict(clear_min_mm=round(min(sd), 2), pen=round(sum(max(0.0, 1.0 - v) ** 2 for v in sd), 2), tips_past=past,
                    pad_mm=pad, pad_inside_cm=round(inside, 2), screen=round(seen / n, 3), flat=flat,
                    wrist_deg=round(math.degrees(fa.angle(rig.dir("hand_l"))), 1), forearm_rise_deg=round(rise, 1),
                    miss_cm=round(miss[0] * 100, 2), curls={k: [round(x, 1) for x in v] for k, v in dict(fang, **tang).items()})


def cost(m):
    c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 150 * max(0, 2 - len(m["tips_past"]))
    c += 80 if m["pad_mm"] is None else 25 * (max(0.0, 1.0 - m["pad_mm"]) + max(0.0, m["pad_mm"] - 3.0))
    c += 60 * max(0.0, 0.6 - m["pad_inside_cm"]) + 300 * max(0.0, 0.82 - m["screen"]) + 20 * len(m["flat"])
    c += 6 * (max(0.0, 15 - m["wrist_deg"]) + max(0.0, m["wrist_deg"] - 35)) + 4 * max(0.0, 25 - m["forearm_rise_deg"])
    return c + 500 * m["miss_cm"]


def ok(m):
    return (m["clear_min_mm"] >= 1.0 and len(m["tips_past"]) >= 2 and m["pad_mm"] is not None and 1.0 <= m["pad_mm"] <= 3.0
            and m["pad_inside_cm"] > 0 and m["screen"] >= 0.80 and not m["flat"] and 15 <= m["wrist_deg"] <= 35
            and m["forearm_rise_deg"] >= 25 and m["miss_cm"] < 0.05)


def main():
    rig, R = H.load_teen()
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    eye_ue = Vector(H.bl_to_ue_loc(eye))
    P, PQ = PC.phone_ue(eye_ue)
    phone = H.load_phone()
    H.place(phone, tuple(P), PC.qt(PQ), (K, K, K))
    g = Grasp(rig, phone, eye)
    place = dict(theta=25.0, yaw=45.0, px=-3.0, py=-2.5, back=5.0, roll=0.0, elbow=0.0, spread=2.0, t1s=20.0, t1r=-40.0, cup=25.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        place.update(json.load(open(prev))["place"])
    lo = dict(theta=-10, yaw=0, px=-7, py=-4.5, back=2.0, roll=-40, elbow=-90, spread=-4, t1s=-40, t1r=-120, cup=0)
    hi = dict(theta=80, yaw=80, px=5, py=1.0, back=9.0, roll=40, elbow=90, spread=10, t1s=50, t1r=60, cup=45)
    stp = [dict(theta=10, yaw=10, px=1.0, py=0.8, back=1.0, roll=10, elbow=15, spread=2, t1s=10, t1r=15, cup=8),
           dict(theta=3, yaw=3, px=0.3, py=0.3, back=0.3, roll=3, elbow=5, spread=1, t1s=3, t1r=5, cup=3)]
    f = lambda pl: cost(g(pl))  # noqa: E731
    if ARGS.get("resume") != "1":
        starts = []  # the fingers across the back to the right edge, turned up the phone by theta
        for th, yw in ((20.0, 35.0), (20.0, 60.0), (45.0, 45.0)):
            b, c0 = G.descend(f, dict(place, theta=th, yaw=yw), stp[:1], list(place), lo, hi)
            starts.append((c0, b))
            print("PHONE start", th, yw, round(c0, 1), json.dumps(g(b)), flush=True)
        place = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        place, _ = G.descend(f, place, stp, list(place), lo, hi)
        place, _ = G.perturb(f, place, list(place), stp[1], lo, hi, iters=int(ARGS.get("iters", 120)), seed=7 + rnd)
        m = g(place)
        rounds.append(dict(round=rnd, cost=round(cost(m), 2), fast=m))
        print("PHONE round", rnd, round(cost(m), 2), json.dumps(m), flush=True)
        if ok(m):
            break
    hold = g(place)
    rig_verdict = dict(phone=H.phone_report(rig, phone, eye), check=H.check(rig, phone, "l", contacts={"thumb_pad": 3.0}))
    hold["body_clear"] = G.body_clear_mm(rig, [H._tree([phone])[0]], 1.0 / K)
    hold_pose = H.export_ue_local(rig)
    hand_p, hand_q = H.ue_bone(rig, "hand_l")
    elbow_p, _ = H.ue_bone(rig, "lowerarm_l")
    centre = phone.matrix_world.translation
    X, Y, Z = (phone.matrix_world.to_3x3().col[i].normalized() for i in range(3))
    H.render_fp(rig, eye, eye + Vector((0, -1, 0)), os.path.join(OUT, "hold_fp.png"))
    H.render_side(rig, centre, Y * 1.0 + Z * 0.15 + X * 0.1, os.path.join(OUT, "hold_side.png"), dist_m=0.3)  # from the right edge
    H.render_side(rig, centre, Z * 1.0 - X * 0.4, os.path.join(OUT, "hold_under.png"), dist_m=0.35)  # from behind and below
    passed = ok(hold) and rig_verdict["phone"]["box_violations"] == 0 and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, rig=rig_verdict, place=place, rounds=rounds)
    json.dump(rep, open(prev, "w"), indent=1)
    print("PHONE_GRASP", "passed" if passed else "FAILED", json.dumps(hold), json.dumps(rig_verdict["phone"]))
    if passed or ARGS.get("force") == "1":
        sol_path = "P:/FoA/Saved/AnimShots/phone_grasp_solution.json"
        PC.write_solution(hold_pose, hold_pose, eye_ue, P, PQ, hand_p, hand_q, elbow_p, dict(rep, hold_fast=hold, tap_fast=hold))
        os.replace("P:/FoA/Saved/AnimShots/phone_cradle_v2_solution.json", sol_path)
        print("PHONE_GRASP_SOLUTION", sol_path)


main()
