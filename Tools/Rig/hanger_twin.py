"""The wire hanger in the right hand (SM_Lux3D_WireHanger, "bent out of shape": a 42 cm triangle whose hook is pulled
straight into an 15 cm stem), solved at MESH level in the Blender twin (anim lane). One hold for both uses: the stem
poked into the door gap at the latch (KNEEL) and under the bed for the shirt. The hand keeps the screwdriver's arm pose
(screw 0's solve: a tool held forward, forearm level), and the HANGER is placed in the hand: its bottom bar across the
palm, the stem pointing forward along the forearm (within 30 deg). The bar approaches the palm until it is 2 mm off
(grip_twin.approach), then every digit closes on it (grip_twin.close_digits). A 9 mm bar is thinner than a fist's tunnel
(v3: index and middle curled fully and still missed it by 17-20 mm), so the hold is the wire in the fingers: index and
middle wrapped over it (middle or distal phalanx within 3 mm), the thumb pad pressing it (within 3 mm), ring and pinky
curled in. No skin within 1 mm of the hanger. The hanger is life size (the glb is 42 cm across) until the editor dump says otherwise.
Writes Saved/RigShots/hanger/{fp,side,grip}.png, check.json and Saved/AnimShots/hanger_grip_solution.json (the pose
and the hanger's transform relative to hand_r: BP_FoAPlayer's attach offset).
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/hanger_twin.py [rounds=2] [resume=1]"""
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

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/hanger"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = 170.0 / 180.0
DIG = ("thumb", "index", "middle", "ring", "pinky")
FULL = {d: (90.0, 100.0, 70.0) for d in DIG[1:]}
FULL["thumb"] = (35.0, 55.0, 75.0)
TARGET = 2.0
ARM = "P:/FoA/Saved/AnimShots/screwdriver_screw0_solution.json"


def pose_digits(rig, p, ang):
    G.reset_bones(rig, [f"{dg}_{j}_r" for dg in DIG for j in G.SEGS])
    rig.spread("thumb_01_r", p["t1s"])
    rig.rot("thumb_01_r", rig.dir("thumb_01_r"), p["t1r"])
    for dg in DIG:
        for j, a in zip(G.SEGS, ang.get(dg, (0.0, 0.0, 0.0))):
            rig.flex(f"{dg}_{j}_r", a)


class Hanger:
    def __init__(self):
        self.frame = H.load_object("hanger")
        vs = [v for o in H.meshes_of(self.frame) for v in (o.matrix_world @ w.co for w in o.data.vertices)]
        zmin = min(v.z for v in vs)
        bar = [v for v in vs if v.z < zmin + 0.01 and abs(v.x) < 0.05]
        self.bar_mid = sum(bar, Vector()) / len(bar)  # import space: the bar runs along X, the stem points +Z
        self.radius_cm = (max(v.z for v in bar) - zmin) * 50
        # the bottom bar alone (away from the corners), for the wrap contacts: v2's index "held" the triangle's side wire
        o = H.meshes_of(self.frame)[0]
        keep = {i for i, w in enumerate(o.data.vertices) if (o.matrix_world @ w.co).z < zmin + 0.012 and abs((o.matrix_world @ w.co).x) < 0.12}
        self.bar_mesh, self.bar_local = o, [o.matrix_world @ o.data.vertices[i].co for i in sorted(keep)]
        idx = {i: k for k, i in enumerate(sorted(keep))}
        self.bar_polys = [tuple(idx[v] for v in pl.vertices) for pl in o.data.polygons if all(v in idx for v in pl.vertices)]
        print("HANGER bar middle", tuple(round(x, 4) for x in self.bar_mid), "radius cm", round(self.radius_cm, 2), flush=True)

    def place(self, rig, p, gap_cm):
        """The bar's point `along` cm from its middle sits gap_cm off the palm centre against the palm normal; the bar
        turned `theta` deg in the palm plane from square across the fingers; the hanger rolled `phi` deg about the bar."""
        d, n = rig.dir("hand_r"), rig.world("hand_r", rig.axes["hand_r"]["n"])
        n = (n - d * n.dot(d)).normalized()
        across = d.cross(n).normalized()
        bar_dir = (Matrix.Rotation(math.radians(p["theta"]), 3, n) @ across).normalized()
        stem0 = (d - bar_dir * d.dot(bar_dir)).normalized()  # phi 0: the stem along the fingers' line, then rolled
        stem = (Matrix.Rotation(math.radians(p["phi"]), 3, bar_dir) @ stem0).normalized()
        palm_c = rig.head("hand_r") + d * p["s"] / 100
        target = palm_c + n * gap_cm / 100
        R = Matrix((bar_dir, stem.cross(bar_dir), stem)).transposed()  # columns: X along the bar, Z up the stem
        Rs = R.to_4x4() @ Matrix.Scale(1.0 / BODY_SCALE, 4)
        grip_local = self.bar_mid + Vector((p["along"] / 100, 0, 0))
        self.frame.matrix_world = Matrix.Translation(target - (Rs @ grip_local)) @ Rs
        bpy.context.view_layer.update()
        self.bar_tree = BVHTree.FromPolygons([self.frame.matrix_world @ v for v in self.bar_local], self.bar_polys)
        return stem


def main():
    rig, _ = H.load_teen()
    arm = json.load(open(ARM))
    H.pose_from_ue_local(rig, arm["pose"])
    hg = Hanger()
    skin = G.HandSkin(rig, "r")
    reg = H.regions(rig, "r")
    pos = {i: r for r, i in enumerate(skin.idx)}
    pads = {k: [pos[i] for i in reg.get(k, ()) if i in pos] for k in ("thumb_pad", "palm")}
    # a finger WRAPS the bar when its middle or distal phalanx is on it (v1: proximal phalanges touching at 3-5 deg of curl passed)
    digit_rows = {dg: [r for s in ("02", "03") for r in skin.rows.get((dg, s), [])] for dg in DIG}
    seg_rows = {(dg, s): skin.rows.get((dg, s), [])[::1 if s == "03" else 2] for dg in DIG for s in G.SEGS}
    trees = []

    def dist(co, rows, tr=None):
        return min((G.signed_mm(tr or trees, co[r], BODY_SCALE) for r in rows), default=99.0)

    def ev(p):
        stem = [None]
        pose_digits(rig, p, {})

        def set_gap(g):
            stem[0] = hg.place(rig, p, g)
            trees[:] = [H._tree([hg.frame])[0]]
        G.approach(set_gap, lambda: dist(skin(), skin.rows[("hand",)]), hg.radius_cm + 0.2, hg.radius_cm + 5.0, TARGET)

        def seg_dist(segs):
            co = skin()
            return {dg: dist(co, [r for s in segs for r in seg_rows[(dg, s)]]) for dg in DIG}
        ang = G.close_digits(lambda a: pose_digits(rig, p, a), seg_dist, DIG, FULL, TARGET)
        co = skin()
        sd = [G.signed_mm(trees, c, BODY_SCALE) for c in co]
        fa = (rig.head("hand_r") - rig.head("lowerarm_r")).normalized()
        m = dict(clear_min_mm=round(min(sd), 2), pen=round(sum(max(0.0, 1.0 - v) ** 2 for v in sd), 2),
                 fingers={dg: round(dist(co, digit_rows[dg], [hg.bar_tree]), 2) for dg in ("index", "middle")},
                 thumb_pad=round(dist(co, pads["thumb_pad"], [hg.bar_tree]), 2),
                 palm=round(min(sd[r] for r in pads["palm"]), 2), stem_vs_forearm_deg=round(math.degrees(stem[0].angle(fa)), 1),
                 curls={k: [round(x, 1) for x in v] for k, v in ang.items()})
        return m

    def cost(m):
        c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"])
        c += 8 * sum(max(0.0, v - 3.0) for v in m["fingers"].values()) + 8 * max(0.0, m["thumb_pad"] - 3.0)
        return c + 2 * max(0.0, m["stem_vs_forearm_deg"] - 30)

    def ok(m):
        return (m["clear_min_mm"] >= 1.0 and all(v <= 3.0 for v in m["fingers"].values()) and m["thumb_pad"] <= 3.0
                and m["stem_vs_forearm_deg"] <= 30)

    place = dict(theta=0.0, phi=0.0, s=8.0, along=0.0, t1s=0.0, t1r=-40.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        place.update(json.load(open(prev))["place"])
    lo = dict(theta=-25, phi=-90, s=3.0, along=-6.0, t1s=-40, t1r=-120)  # the fist round the bar's middle, nearly square
    hi = dict(theta=25, phi=90, s=11.0, along=6.0, t1s=50, t1r=60)
    stp = [dict(theta=10, phi=12, s=0.8, along=3.0, t1s=10, t1r=15), dict(theta=3, phi=4, s=0.3, along=1.0, t1s=3, t1r=5)]
    f = lambda p: cost(ev(p))  # noqa: E731
    if ARGS.get("resume") != "1":
        starts = []
        for th in (-20.0, 0.0, 20.0):
            p, c0 = G.descend(f, dict(place, theta=th), stp[:1], list(place), lo, hi)
            starts.append((c0, p))
            print("HANGER start", th, round(c0, 1), json.dumps(ev(p)), flush=True)
        place = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        place, _ = G.descend(f, place, stp, list(place), lo, hi)
        place, _ = G.perturb(f, place, list(place), stp[1], lo, hi, iters=int(ARGS.get("iters", 100)))
        m = ev(place)
        rounds.append(dict(round=rnd, cost=round(cost(m), 2), fast=m))
        print("HANGER round", rnd, round(cost(m), 2), json.dumps(m), flush=True)
        if ok(m):
            break
    hold = ev(place)
    verdict = H.check(rig, [hg.frame], "r", contacts={"thumb_pad": 3.0})
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    hc = rig.head("hand_r")
    H.render_fp(rig, eye, hc, os.path.join(OUT, "fp.png"))
    H.render_side(rig, hc, Vector((-1, 0.6, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.5)
    H.render_side(rig, hc, Vector((0.3, 0.4, 1.0)), os.path.join(OUT, "grip.png"), dist_m=0.3)
    hold["body_clear"] = G.body_clear_mm(rig, [H._tree([hg.frame])[0]], BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    hand = (rig.ob.matrix_world @ rig.ob.pose.bones["hand_r"].matrix)
    rel = hand.inverted() @ hg.frame.matrix_world  # the hanger in hand_r's frame (Blender); the bake converts to UE
    rep = dict(passed=passed, hold=hold, verdict=verdict, place=place, rounds=rounds, arm_from=ARM)
    json.dump(rep, open(prev, "w"), indent=1)
    print("HANGER_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"])))
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(hg.frame.matrix_world),
                   object_in_hand_bl=[list(r) for r in rel], twin=rep), open("P:/FoA/Saved/AnimShots/hanger_grip_solution.json", "w"))


main()
