"""Screwdriver on the lock-plate screws, solved at MESH level in the Blender twin (anim lane; the user's screenshot
2026-11-10, "Loosen screw 1 of 4: likewise this is unnatural": an underhand hold with the shaft lying along the plate).
Same kneel as the key (main: one stance at the lock plate). Per screw:
- the tool: tip on the screw head, the shaft along the screw's normal (out of the door toward him);
- the hand: a power grip, the handle across the palm, fingers wrapped, thumb along the handle, pushing in; the handle in
  line with the forearm (<= 20 deg), the wrist near neutral (<= 20 deg); the turn (D/A) is forearm roll about the shaft;
- no skin vertex (hand and forearm; the rest of the body at the end) within 1 mm of the tool, the plate or the door;
  finger pads and the palm within 1-3 mm of the handle; the handle's butt in the heel of the palm, >= 1 cm ahead of the wrist;
- the grasp is synthesised (grip_twin.approach + close_digits via knob_twin's Solver), the search is the kneel and the hand;
- from the eye: the shaft and the screw in a 3/4 view (an 8 cm fist 45 cm from the eye is a tenth of the 80-deg frame);
- the elbow bent near square (<= 120 deg): kneeling at the plate, not reaching for it.
Screws (rig's fit_door_lock.py notes): door-local (y, z) = (-86.1|-81.9, 91.5|82.5) around the key point (-84, 87):
+-2.1 cm across and +-4.5 cm up/down from the keyhole, in the door face. The twin places the door face where the key's
tip met it (key_pinch_twin.py), scaled to the unscaled body. Nothing is baked here.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/screwdriver_twin.py screw=0 [rounds=2] [resume=1] [from=0]"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402
import knob_twin as K  # noqa: E402  (the grasp synthesis: Solver, pose_digits)

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
SCREW = int(ARGS.get("screw", 0))
OUT = f"P:/FoA/Saved/RigShots/screwdriver/screw{SCREW}"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = 170.0 / 180.0
KEY_Z = (88.5 - 3.094446780476119) / BODY_SCALE  # the keyhole's height above the Body root (twin cm), as the key twin
DOOR_Y = 48.28 + 3.97 + 1.0  # the door face, twin cm forward of the root at fwd 0 (the key's tip met it)
SCREWS = [(-2.1, 4.5), (2.1, 4.5), (-2.1, -4.5), (2.1, -4.5)]  # (across, up) from the keyhole, door cm
DIG = ("index", "middle", "ring", "pinky")


def stance(rig, st):
    """The lock-plate kneel (same as key_pinch_twin.py): right knee down, left foot forward, lean st['lean']; the free
    hand rests on the raised left knee."""
    G.reset_bones(rig, [b.name for b in rig.ob.pose.bones])
    rig.ob.location.z = 0.0
    bpy.context.view_layer.update()
    floor = min(rig.head("foot_l").z, rig.head("foot_r").z)
    fw, up = Vector((0, -1, 0)), Vector((0, 0, 1))
    rig.aim("thigh_l", fw + up * -0.25 + Vector((0.12, 0, 0)))
    rig.aim("calf_l", -up + fw * 0.05)
    rig.aim("foot_l", fw - up * 0.35)
    rig.aim("thigh_r", -up + fw * 0.12 + Vector((-0.08, 0, 0)))
    rig.aim("calf_r", -fw - up * 0.12)
    rig.aim("foot_r", -fw - up * 0.6)
    for b in rig.spine_chain():
        rig.rot(b, Vector((1.0, 0.0, 0.0)), st["lean"] / len(rig.spine_chain()))
    rig.ob.location.z -= min(rig.head("calf_r").z - 0.05, rig.head("foot_l").z - floor)
    bpy.context.view_layer.update()
    # v1-v21 left the free arm reaching forward with an open hand; now the palm rests on top of the left knee
    G.two_bone(rig, "l", rig.head("calf_l") + up * 0.075 - fw * 0.06, rig.head("upperarm_l") + Vector((0.3, 0.05, -0.3)))
    G.aim_hand(rig, "l", fw, -up)
    G.share_twist(rig, "l")


def screw_point(st):
    """The screw head in Blender world (m) and the door's outward normal (toward him: +Y in Blender)."""
    a, u = SCREWS[SCREW]
    ue = (st["side"] + a / BODY_SCALE, DOOR_Y + st["fwd"], KEY_Z + u / BODY_SCALE)
    return H.ue_to_bl_loc(ue), Vector((0.0, 1.0, 0.0))


def make_door(screw, normal):
    me = bpy.data.meshes.new("door")
    across, up = Vector((1, 0, 0)), Vector((0, 0, 1))
    face = screw - normal * 0.002  # the screw head stands 2 mm proud of the face
    c = [face - normal * t + across * sa * 0.45 + up * su * 0.6 for t in (0.0, 0.04) for sa in (-1, 1) for su in (-1, 1)]
    me.from_pydata(c, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    ob = bpy.data.objects.new("door_standin", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


class Tool:
    """The screwdriver mesh: its long axis and which end is the tip (the thin end), in the object's frame."""

    def __init__(self, frame):
        self.frame = frame
        co = [v for o in H.meshes_of(frame) for v in (o.matrix_local @ vv.co for vv in o.data.vertices)]
        ext = [max(v[i] for v in co) - min(v[i] for v in co) for i in range(3)]
        self.ax = max(range(3), key=lambda i: ext[i])
        lo, hi = min(v[self.ax] for v in co), max(v[self.ax] for v in co)
        r = lambda v: math.sqrt(sum(v[i] ** 2 for i in range(3) if i != self.ax))  # noqa: E731
        near_lo = max(r(v) for v in co if v[self.ax] < lo + 0.15 * (hi - lo))
        near_hi = max(r(v) for v in co if v[self.ax] > hi - 0.15 * (hi - lo))
        self.tip_end = lo if near_lo < near_hi else hi  # the shaft end is the thin one
        self.sign = 1.0 if self.tip_end == lo else -1.0  # sign * the axis points from the tip toward the handle
        self.length = hi - lo
        hcoord = [v[self.ax] for v in co if r(v) > 0.6 * max(r(w) for w in co)]
        self.handle_c = sum(hcoord) / len(hcoord)  # the handle's middle along the axis (where it is thick)

    def place(self, tip_world, out_dir, roll_deg):
        """Tip on the screw, axis out of the door (toward him), rolled about the shaft by roll_deg."""
        a = Vector((0, 0, 0))
        a[self.ax] = 1.0
        q = (Vector(a) * self.sign).rotation_difference(out_dir)  # tip -> handle points out of the door, toward him
        # life size against the game's 170/180 body = 1/BODY_SCALE against the twin's unscaled one (as the phone)
        R = Matrix.Rotation(math.radians(roll_deg), 4, out_dir) @ q.to_matrix().to_4x4() @ Matrix.Scale(1.0 / BODY_SCALE, 4)
        tip_local = Vector((0, 0, 0))
        tip_local[self.ax] = self.tip_end
        self.frame.matrix_world = Matrix.Translation(tip_world - (R @ tip_local).to_3d()) @ R
        bpy.context.view_layer.update()

    def handle_point(self, s_cm):
        """A point on the axis, s_cm from the handle's middle toward its butt (world)."""
        v = Vector((0, 0, 0))
        v[self.ax] = self.handle_c + self.sign * s_cm / 100.0
        return self.frame.matrix_world @ v


def place_hand(rig, tool, axis_out, p):
    """Power grip: the palm faces the handle from direction phi around the shaft, the fingers wrap across it at `diag`
    deg from the shaft, the hand bone sits off the handle by (s along, r out); the arm reaches it."""
    ref = Vector((0, 0, 1)) - axis_out * axis_out.z
    ref = ref.normalized() if ref.length > 1e-6 else Vector((1, 0, 0))
    u = (Matrix.Rotation(math.radians(p["phi"]), 3, axis_out) @ ref).normalized()  # from the shaft to the palm
    # the hand points along the shaft toward the screw (wrist neutral behind the handle), turned by diag about the palm normal;
    # the curled fingers then wrap the handle (v1 pointed the hand across the handle: a 154 deg wrist)
    d = (Matrix.Rotation(math.radians(p["diag"]), 3, u) @ -axis_out).normalized()
    n = -u  # the palm faces the shaft
    centre = tool.handle_point(p["s"]) + u * p["r"] / 100
    wrist = centre - d * p["back"] / 100
    G.reset_bones(rig, ["upperarm_r", "lowerarm_r", "hand_r"] + [b for b in rig.names if "twist" in b and b.endswith("_r")])
    sh = rig.head("upperarm_r")  # the elbow swings p["elbow"] deg about the shoulder-wrist line from out-and-down
    pole = sh + Matrix.Rotation(math.radians(p["elbow"]), 3, (wrist - sh).normalized()) @ Vector((-0.3, 0.05, -0.3))
    miss = G.two_bone(rig, "r", wrist, pole)
    G.aim_hand(rig, "r", d, n)
    G.share_twist(rig, "r")
    return miss


SDIG = ("thumb",) + DIG
FULL = {d: (90.0, 100.0, 70.0) for d in DIG}
FULL["thumb"] = (35.0, 55.0, 75.0)
TARGET = 2.0  # game mm: where the approaching hand and each closing digit stop


class Grasp:
    """knob_twin's grasp synthesis on the screwdriver: the whole hand (forearm too) comes in toward the shaft, cupped,
    until it is 2 mm off; the fingers close GraspIt-style on the handle; then the thumb closes onto the handle or over
    the curled index and middle (their skin is an obstacle for it). v1-v24 searched 13 finger curls blindly."""

    def __init__(self, rig):
        self.rig, self.sol = rig, K.Solver(rig)
        sk = self.sol.skin
        pos = {i: r for r, i in enumerate(sk.idx)}
        fs = {r for d in ("index", "middle") for s in ("02", "03") for r in sk.rows.get((d, s), [])}
        self.finger_polys = [tuple(pos[v] for v in p.vertices) for p in rig.body.data.polygons if all(v in pos and pos[v] in fs for v in p.vertices)]
        self.thumb_pad = set(self.sol.pads["thumb_pad"])
        self.thumb_rows = [r for s in G.SEGS for r in sk.rows.get(("thumb", s), [])]

    def fingers_tree(self, co):
        return BVHTree.FromPolygons([Vector(c) for c in co], self.finger_polys)

    def __call__(self, tool, out, door, pl):
        rig, sol = self.rig, self.sol
        tool_tree = H._tree([tool.frame])[0]
        sol.trees = [tool_tree, BVHTree.FromObject(door, bpy.context.evaluated_depsgraph_get())]
        pk = dict(spread=0.0, t1s=pl["t1s"], t1r=pl["t1r"])
        pre = {d: (pl["cup"], pl["cup"], pl["cup"] * 0.7) for d in DIG}
        pre["thumb"] = (0.0, pl["cup"] * 0.5, pl["cup"] * 0.5)
        K.pose_digits(rig, pk, pre)
        miss = [0.0]

        def set_r(r):
            miss[0] = place_hand(rig, tool, out, dict(pl, r=r))
        G.approach(set_r, lambda: sol.dist(sol.skin(), sol.all_rows), 0.8, 7.0, TARGET)

        def seg_dist(digits, segs, extra=None):
            co = sol.skin()
            d = {dg: sol.dist(co, [r for s in segs for r in sol.seg_rows[(dg, s)]]) for dg in digits}
            if extra:  # the thumb stops on the curled fingers too (unsigned: their skin is an open surface)
                ft = self.fingers_tree(co)
                rows = [r for s in segs for r in sol.seg_rows[("thumb", s)]]
                d["thumb"] = min(d["thumb"], min((ft.find_nearest(Vector(co[r]))[3] * 1000 * BODY_SCALE for r in rows), default=99.0))
            return d
        fang = G.close_digits(lambda a: K.pose_digits(rig, pk, dict(a, thumb=pre["thumb"])), lambda segs: seg_dist(DIG, segs),
                              DIG, FULL, TARGET, start=pre)
        tang = G.close_digits(lambda a: K.pose_digits(rig, pk, dict(fang, **a)), lambda segs: seg_dist(("thumb",), segs, True),
                              ("thumb",), FULL, TARGET, start={"thumb": pre["thumb"]})
        co = sol.skin()
        sd = [G.signed_mm(sol.trees, c, BODY_SCALE) for c in co]
        pads = {k: round(min((G.signed_mm([tool_tree], co[r], BODY_SCALE) for r in v), default=99.0), 2) for k, v in sol.pads.items()}
        ft = self.fingers_tree(co)
        on_fingers = min((ft.find_nearest(Vector(co[r]))[3] * 1000 * BODY_SCALE for r in self.thumb_pad), default=99.0)
        pads["thumb_pad"] = round(min(pads["thumb_pad"], on_fingers), 2)  # wrapped over the index counts as placed
        thumb_in = min((ft.find_nearest(Vector(co[r]))[3] * 1000 * BODY_SCALE for r in self.thumb_rows if r not in self.thumb_pad), default=99.0)
        contact = set().union(*sol.pads.values())
        fa = (rig.head("hand_r") - rig.head("lowerarm_r")).normalized()
        ua = (rig.head("lowerarm_r") - rig.head("upperarm_r")).normalized()
        worst = sorted((v, r) for r, v in enumerate(sd) if v < 1.0)[:6]
        return dict(offenders=[round(v, 2) for v, _ in worst], clear_min_mm=round(min(v for r, v in enumerate(sd) if r not in contact), 2),
                    contact_min_mm=round(min(sd[r] for r in contact), 2),
                    pen=round(sum(max(0.0, 1.0 - v) ** 2 for v in sd) + max(0.0, 1.0 - thumb_in) ** 2, 2), pads=pads,
                    inline_deg=round(math.degrees(fa.angle(-out)), 1), wrist_deg=round(math.degrees(fa.angle(rig.dir("hand_r"))), 1),
                    elbow_deg=round(180 - math.degrees(ua.angle(fa)), 1), butt_cm=round(butt_ahead(rig, tool), 2),
                    miss_cm=round(miss[0] * 100, 2), curls={k: [round(x, 1) for x in v] for k, v in dict(fang, **tang).items()})


def butt_ahead(rig, tool):
    """How far the handle's butt end lies ahead of the wrist joint along the forearm (game cm). In a power grip the butt
    sits in the heel of the palm, ahead of the wrist; v22 passed every mesh check with it 6.4 cm BEHIND the wrist, the
    handle lying along the forearm's underside."""
    butt = Vector((0, 0, 0))
    butt[tool.ax] = tool.tip_end + tool.sign * tool.length
    fa = (rig.head("hand_r") - rig.head("lowerarm_r")).normalized()
    return (tool.frame.matrix_world @ butt - rig.head("hand_r")).dot(fa) * 100 * BODY_SCALE


def cost(m):
    c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 40 * max(0.0, 1.0 - m["contact_min_mm"])
    c += 8 * sum(max(0.0, v - 3.0) for k, v in m["pads"].items() if k not in ("thumb_pad", "pinky_pad"))  # wrapped on the handle
    c += 3 * max(0.0, m["pads"]["pinky_pad"] - 3.0) + 3 * max(0.0, m["pads"]["thumb_pad"] - 3.0)
    c += 3.0 * max(0.0, m["inline_deg"] - 18) + 6.0 * max(0.0, m["wrist_deg"] - 18)
    c += 40 * (max(0.0, m["inline_deg"] - 20) + max(0.0, m["wrist_deg"] - 20))
    c += 80.0 * max(0.0, 1.0 - m["butt_cm"])  # the butt in the palm's heel, at least 1 cm ahead of the wrist
    # a kneeling worker's elbow is bent near square; v2-v3 screws reached out at 120-138 (the hand a tenth of the view)
    c += 4.0 * (max(0.0, 85 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 115))
    return c + 500 * m["miss_cm"] + (0 if ok(m) else 1000)  # A softer wrist must never outrank a valid grip.


def ok(m):
    # the pinky rides the handle's butt end: within 3.5 (the rig's check does not ask for it at all)
    return (m["clear_min_mm"] >= 1.0 and m["contact_min_mm"] >= 1.0 and m["pads"]["pinky_pad"] <= 3.5
            and all(v <= 3.0 for k, v in m["pads"].items() if k != "pinky_pad") and m["miss_cm"] < 0.05
            and m["inline_deg"] <= 20 and m["wrist_deg"] <= 20 and 85 <= m["elbow_deg"] <= 120 and m["butt_cm"] >= 1.0)


def main():
    rig, _ = H.load_teen()
    frame = H.load_object("screwdriver")
    tool = Tool(frame)
    st = dict(lean=8.0, side=-22.0, fwd=12.0)  # v21's kneel: the plate 66 cm ahead, 22 cm to his right
    # the hand well back on the handle: the wrist ~7 cm behind the palm point, so the butt can sit in the heel
    place = dict(phi=-90.0, diag=30.0, s=1.0, back=7.0, roll=0.0, elbow=0.0, t1s=20.0, t1r=-60.0, cup=20.0)
    prev = os.path.join(OUT, "check.json")
    passed_json = os.path.join(OUT, "passed.json")  # the last passing solve: a failed rerun never overwrites it
    seed = (prev if ARGS.get("from") == "self" else f"P:/FoA/Saved/RigShots/screwdriver/screw{ARGS['from']}/passed.json") if "from" in ARGS \
        else prev  # from=0: screw 0's grip (kneel kept); from=self: this screw's last solve, kneel kept
    if (ARGS.get("resume") == "1" or "from" in ARGS) and os.path.exists(seed):
        last = json.load(open(seed))
        st, place = last["stand"], {k: last["place"].get(k, v) for k, v in place.items()}
    door = [None]
    grasp = Grasp(rig)
    holder = {}

    def setup(s):
        stance(rig, s)
        tip, out = screw_point(s)
        if door[0]:
            bpy.data.objects.remove(door[0])
        door[0] = make_door(tip, out)
        holder.update(st=dict(s), tip=tip, out=out)

    def ev(s, pl):
        if holder.get("st") != s:
            setup(s)
        tool.place(holder["tip"], holder["out"], pl["roll"])
        m = grasp(tool, holder["out"], door[0], pl)
        return m, cost(m)

    # screws 1-3 keep screw 0's kneel (knees and feet planted at the plate): only the torso's lean and the arm move
    free = ["lean"] if "from" in ARGS else list(st)
    # v26 drifted to fwd -14 (the door 39 cm ahead: elbow 54, the left hand on the knee 18 mm into the door) and phi -150
    lo = dict(lean=0, side=-30, fwd=0, phi=-130, diag=-60, s=-4, back=2.0, roll=-180, elbow=-100, t1s=-40, t1r=-120, cup=0)
    hi = dict(lean=20, side=5, fwd=15, phi=-20, diag=60, s=5, back=11.0, roll=180, elbow=100, t1s=50, t1r=60, cup=45)
    stp = [dict(lean=2, side=3, fwd=3, phi=15, diag=8, s=0.8, back=0.8, roll=20, elbow=15, t1s=10, t1r=15, cup=8),
           dict(lean=1, side=1, fwd=1, phi=5, diag=3, s=0.3, back=0.3, roll=6, elbow=5, t1s=3, t1r=5, cup=3)]
    if ARGS.get("fine") == "1":
        stp = [{k: v * 0.05 for k, v in stp[-1].items()}]
    keys = free + list(place)
    split = lambda b: (dict(st, **{k: b[k] for k in free}), {k: b[k] for k in place})  # noqa: E731
    f = lambda b: ev(*split(b))[1]  # noqa: E731
    both = dict({k: st[k] for k in free}, **place)
    print("SCREW tool axis", tool.ax, "tip end", round(tool.tip_end, 4), "sign", tool.sign, "length", round(tool.length, 4), flush=True)
    if ARGS.get("resume") != "1" and "from" not in ARGS:  # the grip family: where the palm sits round the handle, its turn
        starts = []
        default = [(ph, dg) for ph in (-110.0, -70.0, -30.0) for dg in (-35.0, 35.0)]  # beside the handle to over it, never under
        grid = [tuple(map(float, x.split(":"))) for x in ARGS["starts"].split(",")] if "starts" in ARGS else default
        for ph, dg in grid:  # dg: the handle diagonal in the palm, heel to the index's base
            b, c0 = G.descend(f, dict(both, phi=ph, diag=dg), stp[:1], ["phi", "diag", "s", "back", "roll"], lo, hi)
            starts.append((c0, b))
            print("SCREW start", ph, dg, round(c0, 1), json.dumps(ev(*split(b))[0]), flush=True)
        both = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        both, _ = G.descend(f, both, stp, keys, lo, hi)
        both, _ = G.perturb(f, both, keys, stp[-1], lo, hi, iters=int(ARGS.get("iters", 150)), seed=int(ARGS.get("seed", 7)) + rnd)
        m, c = ev(*split(both))
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("SCREW round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    st, place = split(both)
    hold, _ = ev(st, place)
    tip, out = holder["tip"], holder["out"]
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    verdict = H.check(rig, [tool.frame], "r", contacts={"index_pad": 3.0, "middle_pad": 3.0, "palm": 3.0})
    H.render_fp(rig, eye, tip + out * 0.08, os.path.join(OUT, "fp.png"))
    H.render_side(rig, tip + out * 0.08, Vector((-1, 0.6, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.35)
    H.render_side(rig, tip + Vector((0, 0.25, -0.25)), Vector((-1, 0.15, 0.1)), os.path.join(OUT, "body.png"), dist_m=2.6)  # the kneel
    rig.body.hide_render = True  # the handle alone from the side view: where it lies under the fist
    H.render_side(rig, tip + out * 0.08, Vector((-1, 0.6, 0.3)), os.path.join(OUT, "side_tool.png"), dist_m=0.35)
    rig.body.hide_render = False
    hold["body_clear"] = G.body_clear_mm(rig, grasp.sol.trees, BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, screw=SCREW, hold=hold, verdict=verdict, stand=st, place=place, rounds=rounds)
    json.dump(rep, open(prev, "w"), indent=1)
    if passed:
        json.dump(rep, open(passed_json, "w"), indent=1)
    print("SCREW_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"], contacts=verdict["contacts"])))
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(tool.frame.matrix_world), stand=st, twin=rep),
              open(f"P:/FoA/Saved/AnimShots/screwdriver_screw{SCREW}_solution.json", "w"))


if __name__ == "__main__":  # boot_twin.py imports the kneel
    main()
