"""Phone cradle, solved at MESH level in the Blender twin (anim lane; the user rejected the old hold 2026-11-10: "the thumb
literally clips into the phone"). Rig's hand_twin.py loads, converts, checks and renders; this script authors the pose.
The user's spec, left hand:
- the phone's LEFT edge in the thumb web, the palm cradling that edge and the lower back;
- index..pinky across the back, tips curled round the RIGHT edge: >= 3 fingertips past it from the eye;
- the thumb ON the glass from the lower left, distal segment toward the screen centre, pad 1-3 mm up (tap: on the glass).
Gates (rig's phone_report box rule and screen rays, on skin vertices): every thumb/finger vertex >= 1 mm outside the
phone box, thumb pad 1-3 mm above the glass and over it, screen >= 80% visible, >= 3 fingertips past the right edge.
The phone sits where the game pins it: READ in the eye frame at 1/BODY_SCALE (the twin's body is unscaled, the game's
is 170/180). A fast in-loop copy of the same rules drives the search; rig's functions give the verdict.
Writes Saved/RigShots/phone_cradle/{hold_fp,hold_side,tap_fp}.png, check.json, and (only if it passes, or force=1)
Saved/AnimShots/phone_cradle_solution.json in bake_phone_grip.py's solution format. Nothing is baked here.
Variant v2 (variant=v2; main's first-person read, 2026-11-10): the phone lower in frame (READ up -10.5), the forearm
steeper from the bottom-left (the elbow pole down and in), the wrist flexed 20-30 deg so the palm heel shows, >= 2
fingertips past the right edge. Writes to Saved/RigShots/phone_cradle/v2/ and phone_cradle_v2_solution.json.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/phone_cradle_twin.py [force=1] [variant=v2]"""
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
V2 = ARGS.get("variant") == "v2"
OUT = "P:/FoA/Saved/RigShots/phone_cradle" + ("/v2_arc" if ARGS.get("arc") == "1" else "/v2" if V2 else "")
os.makedirs(OUT, exist_ok=True)
READ = (31.0, -1.0, -5.8) if V2 else (33.0, -1.5, -5.8)  # Keep the whole screen inside the reading frame.
BODY_SCALE = 170.0 / 180.0
K = 1.0 / BODY_SCALE
HX, HY, HZ = 0.0735, 0.0355, 0.0049  # SM_Phone half extents in its Blender-local frame (m): x up, +y viewer right, -z glass
DIG = ("index", "middle", "ring", "pinky")
FU, RU, UU = Vector((0, 1, 0)), Vector((-1, 0, 0)), Vector((0, 0, 1))  # the eye frame in UE component space


def qt(q):  # mathutils -> UE tuple
    return (q.x, q.y, q.z, q.w)


def phone_ue(eye_ue):
    """The phone's UE transform: screen centre at READ, facing the eye, upright (bake_phone_grip.py's frame)."""
    P = eye_ue + FU * READ[0] + RU * READ[1] + UU * READ[2]
    z = (P - eye_ue).normalized()
    x = (UU - z * UU.dot(z)).normalized()
    y = z.cross(x)  # UE math: x cross y = z; -y is the viewer's right
    assert y.dot(RU) < -0.9
    return P, Matrix((x, y, z)).transposed().to_quaternion()


# ------------------------------------------------------------------------------------------------------------- posing
def place_hand(rig, phone, p, wrist=None):
    """Fingers toward the viewer's right (+y local) tilted up by tilt, palm toward the eye (-z) rolled about the finger
    line by roll; the wrist at `wrist` (the web seating computes it); the arm reaches it, elbow down and out."""
    M = phone.matrix_world
    X, Y, Z = (M.to_3x3().col[i].normalized() for i in range(3))
    # yaw turns the fingers from straight back (+z) toward the right edge (+y); tilt turns them up the phone (+x)
    d = (Matrix.Rotation(math.radians(-p["yaw"]), 3, X) @ Matrix.Rotation(math.radians(p["tilt"]), 3, Y) @ Z).normalized()
    n0 = Y - d * Y.dot(d)
    n = (Matrix.Rotation(math.radians(p["roll"]), 3, d) @ n0).normalized()
    wrist = wrist if wrist is not None else M.translation + X * -0.06 - Y * 0.035 + Z * 0.05  # first guess; ev() seats the thumb base
    G.reset_bones(rig, ["upperarm_l", "lowerarm_l", "hand_l"] + [b for b in rig.names if "twist" in b and b.endswith("_l")])
    pole = Vector((0.12, -0.08, -0.45)) if V2 else Vector((0.25, 0.05, -0.35))  # v2: the elbow down by his side, the forearm steeper
    sh = rig.head("upperarm_l")  # v2 swings the elbow about the shoulder-wrist line (p["elbow"] deg) to bring the wrist in
    pole = Matrix.Rotation(math.radians(p.get("elbow", 0.0)), 3, (wrist - sh).normalized()) @ pole
    miss = G.two_bone(rig, "l", wrist, sh + pole)
    G.aim_hand(rig, "l", d, n)
    G.share_twist(rig, "l")
    return miss


def box_mm(q):
    """Signed distance (game mm) from a phone-local point (m) to the phone box."""
    dx, dy, dz = abs(q.x) - HX, abs(q.y) - HY, abs(q.z) - HZ
    return (Vector((max(dx, 0), max(dy, 0), max(dz, 0))).length + min(max(dx, dy, dz), 0.0)) * 1000 * K


def close_fingers(rig, phone, skin, spread):
    """v2: index..pinky close GraspIt-style onto the phone (grip_twin.close_digits): each joint curls until its segment
    is 2 mm off, so the fingers bend at every knuckle and the tips wrap the right edge (the user, 2026-11-10: "the
    fingers look broken"; the reference photos curl every joint). The constructed thumb is left as it is."""
    rows = {(d, s_): skin.rows.get((d, s_), [])[::1 if s_ == "03" else 2] for d in DIG for s_ in G.SEGS}

    def pose(a):
        G.reset_bones(rig, [f"{dg}_{j}_l" for dg in DIG for j in G.SEGS])
        for i, dg in enumerate(DIG):
            rig.spread(f"{dg}_01_l", spread * (i - 1.5))
            for j, deg in zip(G.SEGS, a[dg]):
                rig.flex(f"{dg}_{j}_l", deg)

    def measure(segs):
        inv, co = phone.matrix_world.inverted(), skin()
        return {dg: min(box_mm(inv @ Vector(co[r])) for s_ in segs for r in rows[(dg, s_)]) for dg in DIG}
    return G.close_digits(pose, measure, DIG, {d: (80.0, 95.0, 65.0) for d in DIG}, 2.0)


def curl(rig, c, phone, thumb_only=False):
    """Fingers by curl; the thumb by construction (v1's free thumb angles passed it through the phone): its knuckle
    (thumb_02) just outside the LEFT edge in front of the glass, the next joint (thumb_03) over the glass, the distal
    phalanx along the glass toward the centre, then the whole thumb rolled about its metacarpal (pad toward the glass)."""
    G.reset_bones(rig, [f"{dg}_{j}_l" for dg in (("thumb",) if thumb_only else DIG + ("thumb",)) for j in ("01", "02", "03")])
    for i, dg in enumerate(() if thumb_only else DIG):
        rig.spread(f"{dg}_01_l", c["spread"] * (i - 1.5))
        for j, deg in zip(("01", "02", "03"), (c[dg], c[dg + "_tip"] * c["pip"], c[dg + "_tip"])):  # knuckle; the tip curls round the edge
            rig.flex(f"{dg}_{j}_l", deg)
    M = phone.matrix_world
    X, Y, Z = (M.to_3x3().col[i].normalized() for i in range(3))
    at = lambda x, y, z: M.translation + X * x / 100 + Y * y / 100 + Z * z / 100  # noqa: E731  (cm, phone frame)
    j2 = at(c["k2x"], -HY * 100 * K - c["k2out"], -HZ * 100 * K - c["k2front"])
    j3 = at(c["k3x"], c["k3y"], -HZ * 100 * K - c["k3h"])
    if "arc_pip" in c:
        # Keep the two thumb hinges flexed in their anatomical planes instead of aiming each joint independently.
        rig.flex("thumb_02_l", c["arc_pip"])
        rig.flex("thumb_03_l", c["arc_dip"])
        rig.aim("thumb_01_l", j2 - rig.head("thumb_01_l"))
        rig.rot("thumb_01_l", rig.dir("thumb_01_l"), c["roll"])
        return
    toward = j3-j2 if ARGS.get("natural") == "1" else (M.translation - j3)
    toward = (toward - Z * toward.dot(Z)).normalized()  # along the glass, toward the centre
    G.thumb_chain(rig, "l", j2, j3, (toward - Z * c["dip"]).normalized(), c['roll'])


# ------------------------------------------------------------------------------------------------------------- fast rules
class Fast:
    """The phone rules on skin vertices, with the vertex labels computed once (rig's functions recompute them per call)."""

    def __init__(self, rig, R):
        dom, _ = R.labels(rig)
        self.R, self.rig, self.dom = R, rig, dom
        self.hand = [i for i, b in enumerate(dom) if b.endswith("_l") and (b.split("_")[0] in H.DIGITS or b.startswith("hand"))]
        self.digits = [i for i in self.hand if not self.dom[i].startswith("hand")]
        self.tip = {dg: [i for i in self.hand if dom[i] == f"{dg}_03_l"] for dg in DIG + ("thumb",)}
        hs = set(self.hand)
        self.tris = [tuple(p.vertices) for p in rig.body.data.polygons if p.vertices[0] in hs]
        co, _ = R.evaluated(rig.body)  # the web: the skin vertex nearest the middle of the thumb and index knuckles, at rest
        mid = (rig.head("thumb_02_l") + rig.head("index_01_l")) / 2
        cand = [i for i in self.hand if dom[i] in ("hand_l", "thumb_01_l", "index_01_l")]
        self.web = min(cand, key=lambda i: (co[i] - mid).length)
        n_palm = rig.world("hand_l", rig.axes["hand_l"]["n"])
        palm = [i for i in self.hand if dom[i] == "hand_l" and (co[i] - rig.head("hand_l")).dot(n_palm) > 0]
        centre = sum((co[i] for i in palm), Vector()) / len(palm)
        self.palm_c = min(palm, key=lambda i: (co[i] - centre).length)  # the palm's centre skin vertex

    def __call__(self, phone, eye):
        co, _ = self.R.evaluated(self.rig.body)
        inv = phone.matrix_world.inverted()
        q = {i: inv @ co[i] for i in self.hand}

        def sd(v):
            dx, dy, dz = abs(v.x) - HX, abs(v.y) - HY, abs(v.z) - HZ
            return Vector((max(dx, 0), max(dy, 0), max(dz, 0))).length + min(max(dx, dy, dz), 0.0)
        sds = {i: sd(q[i]) * 1000 * K for i in self.hand}  # mm in the game's scale
        box = min(sds[i] for i in self.digits)
        palm = min(sds.values())
        dig = set(self.digits)  # thumb and fingers keep 1.25 mm (main's 1 mm rule, with margin); the palm may cradle (touch) the phone
        pen = sum(max(0.0, (1.25 if i in dig else 0.2) - v) ** 2 for i, v in sds.items())
        glass_side = [i for i in self.tip["thumb"] if q[i].z < 0]  # rig's phone_report: the LOWEST thumb_03 vertex must be over the glass
        low = min(glass_side, key=lambda i: -HZ - q[i].z, default=None)
        pad = None if low is None else (-HZ - q[low].z) * 1000 * K
        inside = 0.0 if low is None else min(HX - 0.004 - abs(q[low].x), HY - 0.004 - abs(q[low].y)) * 100 * K  # cm inside the 4 mm margin
        over = [low] if low is not None and inside > 0 else []
        past = [dg for dg in DIG if max((q[i].y for i in self.tip[dg]), default=-1) > HY]  # past the right edge (rig's phone_report rule)
        tree = BVHTree.FromPolygons(co, self.tris)
        seen = n = 0
        for ix in range(-6, 7):  # 13 x 7 rays: rig's phone_report gives the final figure
            for iy in range(-3, 4):
                pt = phone.matrix_world @ Vector((ix / 6 * (HX - 0.003), iy / 3 * (HY - 0.003), -HZ - 0.0001))
                dv = pt - eye
                n += 1
                seen += tree.ray_cast(eye, dv.normalized(), dv.length - 1e-4)[0] is None
        t3, t2 = self.rig.head("thumb_03_l"), self.rig.head("thumb_02_l")
        toward = (t3 - t2).normalized().dot((phone.matrix_world.translation - t3).normalized())
        reach = sum(min(5.0, max(0.0, (max((q[i].y for i in self.tip[dg]), default=-1) - HY) * 1000 * K)) for dg in DIG)
        # smooth: how far each fingertip still falls short of 3 mm past the right edge (0 once it is there)
        short = sum(max(0.0, (HY + 0.003 / K - max((q[i].y for i in self.tip[dg]), default=-1)) * 1000 * K) for dg in DIG[:3])
        touch = {dg: round(min(sds[i] for i in self.tip[dg]), 2) for dg in DIG}  # each fingertip's gap to the phone (cradle: touching)
        web = round(sds[self.web], 2)  # the thumb web's gap to the phone (the left edge sits in it)
        worst = sorted(self.hand, key=lambda i: sds[i])[:40]
        at = [(self.dom[i], round(sds[i], 1), [round(c * 100 * K, 1) for c in q[i]]) for i in worst[:6:2]]  # phone-local cm (x up, +y right, -z glass)
        offenders = {}
        for i in worst:
            if sds[i] < 1.0:
                offenders[self.dom[i]] = min(offenders.get(self.dom[i], 9.0), round(sds[i], 2))
        return dict(pad_inside_cm=round(inside, 2), box_min_mm=round(box, 2), palm_min_mm=round(palm, 2), pen=round(pen, 2), reach_mm=round(reach, 1), short_mm=round(short, 1), touch=touch, web_mm=web, offenders=offenders, worst_at=at,
                    pad_mm=None if pad is None else round(pad, 2),
                    tips_past=past, screen=round(seen / n, 3), thumb_toward_centre=round(toward, 2))


def cost(m, tap=False):
    c = 10.0 * m["pen"] + 40 * max(0.0, (0.0 if tap else 1.0) - m["box_min_mm"]) + 10 * max(0.0, 15.0 - m["reach_mm"]) + 3.0 * m["short_mm"]
    c += 4.0 * sum(max(0.0, g - 3.0) for g in m["touch"].values())  # fingertips rest on the phone, not hover
    c += 8.0 * max(0.0, m["web_mm"] - 3.0)  # the web on the left edge
    lo, hi = (-0.2, 0.4) if tap else (1.3, 2.7)
    c += 80 if m["pad_mm"] is None else 25 * (max(0.0, lo - m["pad_mm"]) + max(0.0, m["pad_mm"] - hi))
    c += 300 * max(0.0, 0.82 - m["screen"]) + 150 * max(0, 3 - len(m["tips_past"])) + 30 * max(0.0, 0.5 - m["thumb_toward_centre"])
    c += 60 * max(0.0, 0.6 - m["pad_inside_cm"])  # the pad well on the glass, not at its edge
    if ARGS.get("natural") == "1":
        c += 20 * max(0.0, m["thumb_base_deg"] - 65)
        c += 10 * max(0.0, -15 - m["thumb_slope_deg"])
        c += 12 * max(0.0, m["thumb_mcp_deg"] - 65) + 12 * max(0.0, m["thumb_ip_deg"] - 45)
        c += 8 * max(0.0, 12 - m["thumb_ip_deg"])
    return c


def ok(m, tap=False):
    pad = m["pad_mm"]
    pad_ok = pad is not None and ((-0.3 <= pad <= 1.0) if tap else (1.0 <= pad <= 3.0))
    box_ok = m["box_min_mm"] >= (-0.3 if tap else 1.08)  # the tap presses the pad onto the glass; 1.08: margin for rig's own box
    wrist_ok = 20 <= m.get("wrist_deg", 25) <= 30 if V2 else True
    natural = ARGS.get("natural") != "1" or (m["thumb_base_deg"] <= 65 and m["thumb_mcp_deg"] <= 65 and 12 <= m["thumb_ip_deg"] <= 45)
    return pad_ok and box_ok and m["palm_min_mm"] >= 0 and m["screen"] >= 0.80 and len(m["tips_past"]) >= (2 if V2 else 3) and m["pad_inside_cm"] > 0 and wrist_ok and natural


def descend(f, x, steps, keys, lo, hi):
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


# ------------------------------------------------------------------------------------------------------------- main
def main():
    rig, R = H.load_teen()
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    eye_ue = Vector(H.bl_to_ue_loc(eye))
    P, PQ = phone_ue(eye_ue)
    phone = H.load_phone()
    H.place(phone, tuple(P), qt(PQ), (K, K, K))
    fast = Fast(rig, R)
    skin, closed = (G.HandSkin(rig, "l") if V2 else None), [None]
    cached = {}
    place = dict(yaw=40.0, tilt=15.0, roll=0.0, cx=-2.5, cz=1.0)  # fingers back and toward the right edge, palm on the left side
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("arc") == "1" and not os.path.exists(prev):
        prev = "P:/FoA/Saved/RigShots/phone_cradle/v2/check.json"
    last = {}
    if ARGS.get("resume") == "1" and os.path.exists(prev):  # continue from the last search
        last = json.load(open(prev))
        place = last["place"] if "yaw" in last["place"] else place
        place.setdefault("elbow", 0.0)
    grip = dict(index=25.0, middle=25.0, ring=30.0, pinky=30.0, index_tip=45.0, middle_tip=50.0, ring_tip=50.0, pinky_tip=50.0,
                pip=0.8, spread=3.0,
                k2x=-3.0, k2out=0.6, k2front=0.6, k3x=-2.0, k3y=-1.5, k3h=1.2, dip=0.15, roll=0.0)
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        grip.update({k: v for k, v in last["grip"].items() if k in grip})
    if ARGS.get("arc") == "1":
        grip.update(arc_pip=25.0, arc_dip=20.0)
        grip.update({k: v for k, v in last.get("grip", {}).items() if k in ("arc_pip", "arc_dip")})
        if ARGS.get("pre_shape") == "1":
            place.update(cx=-3.0, tilt=25.0)
            grip.update(k2x=0.0, k2out=0.3, k2front=1.2, roll=0.0, arc_pip=25.0, arc_dip=20.0)

    def ev(pl, gr, tap=False):
        """Seat the web on the left edge (main: the left edge in the thumb web): place, measure where the web skin
        landed, move the wrist by the difference, place again (the hand turns about the wrist, so two passes)."""
        M = phone.matrix_world
        seat = M @ Vector((pl["cx"] / 100 / K, -HY - (0.0018 + pl.get("cy", 0.0) / 100) / K, pl["cz"] / 100 / K))
        key = tuple(sorted(pl.items())), gr["spread"]
        if V2 and cached.get("key") == key:
            for b, mat in cached["pose"].items():
                rig.ob.pose.bones[b].matrix_basis = mat.copy()
            bpy.context.view_layer.update()
            miss = cached["miss"]
            curl(rig, gr, phone, thumb_only=True)
        else:
            # Palm vertices share finger weights; seat from rest so prior candidates cannot shift the next solve.
            G.reset_bones(rig, [f"{dg}_{j}_l" for dg in DIG + ("thumb",) for j in G.SEGS])
            wrist = None
            for _ in range(2):
                miss = place_hand(rig, phone, pl, wrist)
                co, _ = R.evaluated(rig.body)
                wrist = rig.head("hand_l") + (seat - co[fast.palm_c])
            miss = place_hand(rig, phone, pl, wrist)
            curl(rig, gr, phone)
            if V2:
                closed[0] = close_fingers(rig, phone, skin, gr["spread"])
                cached.update(key=key, miss=miss, pose={b.name: b.matrix_basis.copy() for b in rig.ob.pose.bones})
        m = fast(phone, eye)
        fa = (rig.head("hand_l") - rig.head("lowerarm_l")).normalized()
        m["wrist_deg"] = round(math.degrees(fa.angle(rig.dir("hand_l"))), 1)
        m["thumb_mcp_deg"] = round(math.degrees(rig.dir("thumb_01_l").angle(rig.dir("thumb_02_l"))), 1)
        base_angle = math.degrees(rig.ob.pose.bones["thumb_01_l"].matrix_basis.to_quaternion().angle)
        m["thumb_base_deg"] = round(min(base_angle, 360 - base_angle), 1)
        m["thumb_slope_deg"] = round(math.degrees(math.asin(max(-1, min(1, rig.dir("thumb_02_l").dot(M.to_3x3().col[0].normalized()))))), 1)
        m["thumb_ip_deg"] = round(math.degrees(rig.dir("thumb_02_l").angle(rig.dir("thumb_03_l"))), 1)
        extra = 6.0 * (max(0.0, 20 - m["wrist_deg"]) + max(0.0, m["wrist_deg"] - 30)) if V2 else 0.0  # the palm heel shows
        return m, cost(m, tap) + 5000 * miss + extra

    place.setdefault("cy", 0.0)
    plo, phi = dict(yaw=0, tilt=-15, roll=-50, cx=-5, cy=0, cz=-1.0, elbow=-90), dict(yaw=80, tilt=55, roll=50, cx=3, cy=1.5, cz=3.5, elbow=90)
    if ARGS.get("reference") == "1":
        phi["cx"] = -1.0
        plo["tilt"] = 15.0
    pst = [dict(yaw=8, tilt=8, roll=10, cx=1.0, cy=0.3, cz=0.5, elbow=15), dict(yaw=3, tilt=3, roll=4, cx=0.4, cy=0.1, cz=0.2, elbow=5)]
    place.setdefault("elbow", 0.0)
    glo = dict(index=-10, middle=-10, ring=-10, pinky=-10, index_tip=0, middle_tip=0, ring_tip=0, pinky_tip=0, pip=0.3, spread=0, k2x=-7, k2out=0.0, k2front=-0.5, k3x=-6, k3y=-3.5, k3h=0.6,
               dip=-0.3, roll=-60)  # k2front, k3h: cm in front of the glass; dip: the distal phalanx's slope toward the glass
    ghi = dict(index=80, middle=80, ring=80, pinky=80, index_tip=95, middle_tip=95, ring_tip=95, pinky_tip=95, pip=1.6, spread=8, k2x=2, k2out=2.5, k2front=2.5, k3x=3, k3y=1.5, k3h=2.5,
               dip=0.6, roll=60)
    gst = [dict(index=10, middle=10, ring=10, pinky=10, index_tip=10, middle_tip=10, ring_tip=10, pinky_tip=10, pip=0.15, spread=2, k2x=1.0, k2out=0.4, k2front=0.4, k3x=1.0, k3y=0.6,
                k3h=0.3, dip=0.1, roll=15),
           dict(index=4, middle=4, ring=4, pinky=4, index_tip=4, middle_tip=4, ring_tip=4, pinky_tip=4, pip=0.05, spread=1, k2x=0.4, k2out=0.15, k2front=0.15, k3x=0.4, k3y=0.25,
                k3h=0.1, dip=0.04, roll=5)]
    if ARGS.get("arc") == "1":
        glo.update(arc_pip=12.0, arc_dip=10.0, roll=-180.0)
        ghi.update(arc_pip=50.0, arc_dip=45.0, roll=180.0)
        for step in gst:
            step.update(arc_pip=5.0, arc_dip=5.0)
    if ARGS.get("selftest") == "1":
        first = ev(place, grip)[0]
        second = ev(place, grip)[0]
        assert first == second, (first, second)
        cached.clear()
        third = ev(place, grip)[0]
        assert first == third, ("evaluation depends on the previous pose", first, third)
        print("CRADLE cached pose selftest passed", flush=True)
        return
    rounds = []
    if ARGS.get("grid") == "1":
        cands = []
        for yaw in (30.0, 55.0):
            for cz in (0.3, 1.2, 2.2):
                for cx in (-3.0, -1.0):
                    for tilt in (10.0, 30.0):
                        pl = dict(place, yaw=yaw, cz=cz, cx=cx, tilt=tilt)
                        cands.append((ev(pl, grip)[1], pl))
        cands.sort(key=lambda t: t[0])
        best = None
        for c0, pl in cands[:4]:
            pl, c1 = G.descend(lambda q: ev(q, grip)[1], pl, pst, list(pl), plo, phi)
            print("CRADLE grid", round(c0, 1), "->", round(c1, 1), json.dumps(pl), flush=True)
            if best is None or c1 < best[0]:
                best = (c1, pl)
        place = best[1]
    if ARGS.get("probe") == "1":  # sweep one placement parameter at a time from the resumed pose, print the rules
        m0, c0 = ev(place, grip)
        print("PROBE base", round(c0, 1), json.dumps(m0), flush=True)
        for k, span in (("yaw", 15), ("cz", 0.6), ("roll", 20), ("tilt", 15), ("cx", 1.5)):
            for f in (-1, -0.5, 0.5, 1):
                pl = dict(place, **{k: place[k] + f * span})
                m, c = ev(pl, grip)
                print("PROBE", k, round(pl[k], 2), round(c, 1), json.dumps({x: m[x] for x in ("box_min_mm", "pen", "offenders", "worst_at", "web_mm", "pad_mm")}), flush=True)
        return
    for rnd in range(int(ARGS.get("rounds", 3))):  # place the hand for the grip, then the grip for the hand
        place, _ = descend(lambda pl: ev(pl, grip)[1], place, pst, list(place), plo, phi)
        grip, _ = descend(lambda gr: ev(place, gr)[1], grip, gst, list(grip), glo, ghi)
        m, c = ev(place, grip)
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("CRADLE round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    polish_only = ARGS.get("polish_only") == "1"  # from the resumed pose: only the clearance polish below
    # the thumb alone, multi-start: its proximal phalanx must clear the glass edge by its own thickness (v3 left
    # thumb_02 4 mm inside: one-at-a-time steps could not lift the knuckle without lifting the pad off the glass)
    tkeys = ["k2x", "k2out", "k2front", "k3x", "k3y", "k3h", "dip", "roll"]
    if ARGS.get("arc") == "1":
        tkeys = ["k2x", "k2out", "k2front", "roll", "arc_pip", "arc_dip"]
    best = (ev(place, grip)[1], grip)
    if ARGS.get("arc") == "1" and not polish_only:
        for roll in (-180.0, -90.0, 0.0, 90.0, 180.0):
            start = dict(grip, roll=roll, arc_pip=25.0, arc_dip=20.0)
            g2, c2 = G.descend(lambda gr: ev(place, gr)[1], start, gst, tkeys, glo, ghi)
            print("CRADLE arc", roll, round(c2, 2), flush=True)
            if c2 < best[0]:
                best = c2, g2
    for k2f in (() if polish_only or ARGS.get("arc") == "1" else (0.9, 1.3, 1.8)):
        for k3h in (1.0, 1.4, 1.9):
            for dip in (0.2, 0.45):
                start = dict(grip, k2front=k2f, k3h=k3h, dip=dip, k2out=max(grip["k2out"], 0.8))
                g2, c2 = G.descend(lambda gr: ev(place, gr)[1], start, gst[1:], tkeys, glo, ghi)
                if c2 < best[0]:
                    best = (c2, g2)
    grip = best[1]
    print("CRADLE thumb", round(best[0], 2), json.dumps(ev(place, grip)[0]), flush=True)
    # joint moves over the hand placement and the grip together: seat the left edge in the web (main: the next step)
    both = dict(place, **{"g_" + k: v for k, v in grip.items()})
    split = lambda b: ({k: b[k] for k in place}, {k: b["g_" + k] for k in grip})  # noqa: E731
    blo, bhi = dict(plo, **{"g_" + k: v for k, v in glo.items()}), dict(phi, **{"g_" + k: v for k, v in ghi.items()})
    bst = dict(pst[1], **{"g_" + k: v for k, v in gst[1].items()})
    pw = float(ARGS.get("polish_w", 60)) if polish_only else 0.0  # polish: the joint moves also weigh the 1 mm rule up
    both, cb = G.perturb(lambda b: (lambda mc: mc[1] + pw * mc[0]["pen"])(ev(*split(b))), both, list(both), bst, blo, bhi,
                         iters=int(ARGS.get("iters", 400)))
    place, grip = split(both)
    print("CRADLE joint", round(cb, 2), json.dumps(ev(place, grip)[0]), flush=True)
    # clearance polish: the fingers alone, with the 1 mm rule weighted up (v11 rested the fingertips ON the back at 0 mm)
    fkeys = [k for k in grip if k.startswith(DIG) or k in ("pip", "spread")] + tkeys
    if ARGS.get("thumb_only") == "1":  # keep the wrap (three tips past the edge) and clear the thumb's knuckle alone
        fkeys = tkeys
    grip, cp = G.descend(lambda gr: (lambda mc: mc[1] + float(ARGS.get("polish_w", 60)) * mc[0]["pen"])(ev(place, gr)), grip, gst[1:], fkeys, glo, ghi)
    print("CRADLE polish", round(cp, 2), json.dumps(ev(place, grip)[0]), flush=True)
    hold_fast, _ = ev(place, grip)
    hold_pose = H.export_ue_local(rig)
    hand_p, hand_q = H.ue_bone(rig, "hand_l")
    elbow_p, _ = H.ue_bone(rig, "lowerarm_l")
    verdict = dict(hold_phone=H.phone_report(rig, phone, eye), hold_check=H.check(rig, phone, "l", contacts={"thumb_pad": 3.0}))
    centre = phone.matrix_world.translation
    X, Y = (phone.matrix_world.to_3x3().col[i].normalized() for i in range(2))
    H.render_fp(rig, eye, eye + Vector((0, -1, 0)), os.path.join(OUT, "hold_fp.png"))  # straight ahead, as the game camera
    H.render_side(rig, centre, Y + X * 0.15 + phone.matrix_world.to_3x3().col[2].normalized() * 0.2,
                  os.path.join(OUT, "hold_side.png"), dist_m=0.35)
    tgrip, _ = descend(lambda gr: ev(place, gr, tap=True)[1], grip, gst[1:], tkeys if "arc_pip" in grip else ["k3h", "dip", "roll", "k3x", "k3y"], glo, ghi)
    tap_fast, _ = ev(place, tgrip, tap=True)
    tap_pose = H.export_ue_local(rig)
    verdict["tap_phone"] = H.phone_report(rig, phone, eye)
    H.render_fp(rig, eye, eye + Vector((0, -1, 0)), os.path.join(OUT, "tap_fp.png"))
    passed = ok(hold_fast) and ok(tap_fast, tap=True) and verdict["hold_phone"]["box_violations"] == 0
    rep = dict(passed=passed, hold_fast=hold_fast, tap_fast=tap_fast, verdict=verdict, place=place, grip=grip, tap_grip=tgrip, curls=closed[0],
               rounds=rounds)
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w"), indent=1)
    print("CRADLE_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold_fast, tap=tap_fast, rig=verdict["hold_phone"])))
    if passed or ARGS.get("force") == "1":
        write_solution(hold_pose, tap_pose, eye_ue, P, PQ, hand_p, hand_q, elbow_p, rep)


def write_solution(hold_pose, tap_pose, eye_ue, P, PQ, hand_p, hand_q, elbow_p, rep):
    """bake_phone_grip.py's solution format (UE locals, unscaled body) plus its out.attach and out.camera blocks."""
    ref = json.load(open(H.REF_JSON))

    def locals_(pose):
        return {b: [ref["local"][b][0], list(pose.get(b, ref["local"][b][1])), ref["local"][b][2]] for b in ref["names"]}
    hQ = Quaternion((hand_q[3], hand_q[0], hand_q[1], hand_q[2]))
    att_loc = hQ.inverted() @ (P - Vector(hand_p))
    att_rot = (hQ.inverted() @ PQ).normalized()
    CQ = Matrix((FU, RU, UU)).transposed().to_quaternion()
    rel = lambda p: [round((Vector(p) - eye_ue).dot(a), 4) for a in (FU, RU, UU)]  # noqa: E731
    sol = dict(names=ref["names"], hold=locals_(hold_pose), tap=locals_(tap_pose),
               out=dict(hold="cradle, mesh-checked in the twin", twin=dict(passed=rep["passed"], hold=rep["hold_fast"], tap=rep["tap_fast"]),
                        eye=list(eye_ue), phone_centre=list(P), screen_distance_cm=round((P - eye_ue).length, 1),
                        attach=dict(location=list(att_loc), rotation=list(qt(att_rot))),
                        camera=dict(hand_location=rel(hand_p), hand_rotation=list(qt((CQ.inverted() @ hQ).normalized())),
                                    elbow_location=rel(elbow_p))))
    path = "P:/FoA/Saved/AnimShots/phone_cradle%s_solution.json" % ("_v2_arc" if ARGS.get("arc") == "1" else "_v2" if V2 else "")
    json.dump(sol, open(path, "w"))
    print("CRADLE_SOLUTION", path)


if __name__ == "__main__":  # phone_grasp_twin.py imports the phone frame and the solution writer
    main()
