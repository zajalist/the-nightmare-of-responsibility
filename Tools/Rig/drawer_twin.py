"""Drawer pull (AM_FoA_OpenDrawer on the bedroom commode's top drawer, Commode_GothicCommode_01_door01), solved at MESH
level in the Blender twin (anim lane). Standing, right hand on the drawer's right knob (environment_contact_graphs.py
takes the nearer of the two knobs at +-32% of the 100 cm facade).
The knob, measured from the Poly Haven GothicCommode_01 glTF: a mushroom, head 3.8 cm across and 1 cm thick, on a 2 cm
neck, its end 3.7 cm proud of the drawer face, 98.7 cm up; the commode's top overhangs it. The commode is life size
(the game's 100 cm facade) until the editor dump gives its placed scale.
The grasp is knob_twin.py's synthesis (the whole hand approaches cupped, then every digit closes until it touches),
with a pull grip's contacts: thumb, index and middle pads 1-3 mm off the knob, both index and middle on the
head's BACK (between the head and the drawer: index and middle both hooked), no skin within 1 mm of the commode, wrist <= 25 deg.
Writes Saved/RigShots/drawer/{fp,side,grip,body}.png, check.json and Saved/AnimShots/drawer_grip_solution.json.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/drawer_twin.py [rounds=2] [resume=1]"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402
import knob_twin as K  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/drawer"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = K.BODY_SCALE
KNOB_X = 0.3145  # glTF/Blender-import x of the right-hand knob before the commode is turned to face him (metres)
HEAD_R = 1.9 / BODY_SCALE  # twin cm


class Commode:
    """The commode turned to face him (+Y), life size against the game body (1/BODY_SCALE in the twin)."""

    def __init__(self):
        self.frame = H.load_object("commode")
        drawer = next(o for o in H.meshes_of(self.frame) if o.name.endswith("door01"))
        vs = [drawer.matrix_world @ v.co for v in drawer.data.vertices]  # identity frame: import space
        head = [v for v in vs if abs(v.x - KNOB_X) < 0.03 and abs(v.z - 0.986) < 0.03 and v.y < -0.258]
        self.head_local = sum(head, Vector()) / len(head)  # the head's middle (its end face is 0.4 cm further out)
        self.tip_y = min(v.y for v in head)
        print("DRAWER knob head", tuple(round(x, 4) for x in self.head_local), "verts", len(head), flush=True)

    def place(self, st):
        """The knob head's middle at (side, fwd) cm from his root (UE twin cm, as knob_twin), its own height."""
        R = Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Scale(1.0 / BODY_SCALE, 4)
        want = H.ue_to_bl_loc((st["side"], K.DOOR_Y + st["fwd"], 0.0))
        h = R @ self.head_local
        self.frame.matrix_world = Matrix.Translation(Vector((want.x - h.x, want.y - h.y, 0.0))) @ R
        bpy.context.view_layer.update()
        return self.frame.matrix_world @ self.head_local, Vector((0.0, 1.0, 0.0))


def main():
    rig, _ = H.load_teen()
    com = Commode()
    st = dict(side=-16.0, fwd=-10.0, lean=8.0)  # a step back from the commode (knob_twin v5 stood with its belly at the knob)
    place = dict(yaw=5.0, pitch=5.0, roll=0.0, back=6.0, lift=0.0, elbow=0.0, spread=2.0, t1s=10.0, t1r=-40.0, cup=20.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        last = json.load(open(prev))
        st, place = dict(st, **last["stand"]), {k: last["place"].get(k, v) for k, v in place.items()}
    sol = K.Solver(rig, HEAD_R)
    holder = {}

    def setup(s):
        K.stance(rig, s)
        holder["c"], holder["n"] = com.place(s)
        tree, _ = H._tree([com.frame])
        sol.trees = [tree]
        holder["st"] = dict(s)

    def hooked(out):
        """Both index and middle pads on the head's back (the surface they pull on faces the drawer): the worse of the two.
        v1 passed with the middle hooked and the index lying straight over the head, pointing."""
        co = sol.skin()
        worst = 0.0
        for k in ("index_pad", "middle_pad"):
            best = 99.0
            for r in sol.pads[k]:
                loc, nrm, _, dist = sol.trees[0].find_nearest(Vector(co[r]))
                if loc is not None and nrm.dot(-out) > 0.5:
                    best = min(best, dist * 1000 * BODY_SCALE)
            worst = max(worst, best)
        return round(worst, 2)

    def ev(s, pl):
        if holder.get("st") != s:
            setup(s)
        m = sol.grasp(holder["c"], holder["n"], pl)
        m["hook_mm"] = hooked(holder["n"])
        return m, cost(m)

    def cost(m):
        c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 40 * max(0.0, 1.0 - m["contact_min_mm"])
        c += 8 * sum(max(0.0, m["pads"][k] - 3.0) for k in ("index_pad", "middle_pad", "thumb_pad"))
        c += 4 * max(0.0, m["hook_mm"] - 3.0)
        c += 4 * max(0.0, m["wrist_deg"] - 25) + 1.0 * (max(0.0, 120 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 165))
        return c + 500 * m["miss_cm"]

    def ok(m):
        return (m["clear_min_mm"] >= 1.0 and m["contact_min_mm"] >= 1.0 and m["wrist_deg"] <= 25 and m["miss_cm"] < 0.05
                and m["hook_mm"] <= 3.0 and all(m["pads"][k] <= 3.0 for k in ("index_pad", "middle_pad", "thumb_pad")))

    keys_s, keys_p = list(st), list(place)
    lo = dict(side=-30, fwd=-14, lean=0, yaw=-30, pitch=-30, roll=-180, back=3.0, lift=-3.0, elbow=-100, spread=-4, t1s=-40, t1r=-120, cup=0)
    hi = dict(side=0, fwd=0, lean=25, yaw=110, pitch=110, roll=180, back=10.0, lift=3.0, elbow=100, spread=10, t1s=50, t1r=60, cup=45)
    stp = [dict(side=3, fwd=3, lean=3, yaw=12, pitch=12, roll=20, back=1.0, lift=0.8, elbow=15, spread=2, t1s=10, t1r=15, cup=8),
           dict(side=1, fwd=1, lean=1, yaw=4, pitch=4, roll=6, back=0.3, lift=0.3, elbow=5, spread=1, t1s=3, t1r=5, cup=3)]
    split = lambda b: ({k: b[k] for k in keys_s}, {k: b[k] for k in keys_p})  # noqa: E731
    f = lambda b: ev(*split(b))[1]  # noqa: E731
    both = dict(st, **place)
    if ARGS.get("resume") != "1":
        starts = []  # the palm on the knob's end (fingers up, over the head and behind it), from above (claw), thumb up
        for y0, p0, r0 in ((5, 5, 0), (10, 50, 0), (60, 30, 30), (80, 10, 0)):
            b, c0 = G.descend(f, dict(both, yaw=y0, pitch=p0, roll=r0), stp[:1], list(both), lo, hi)
            starts.append((c0, b))
            print("DRAWER start", y0, p0, r0, round(c0, 1), json.dumps(ev(*split(b))[0]), flush=True)
        both = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        both, _ = G.descend(f, both, stp, list(both), lo, hi)
        both, _ = G.perturb(f, both, list(both), stp[1], lo, hi, iters=int(ARGS.get("iters", 120)))
        m, c = ev(*split(both))
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("DRAWER round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    st, place = split(both)
    hold, _ = ev(st, place)
    verdict = H.check(rig, [com.frame], "r", contacts={"index_pad": 3.0, "middle_pad": 3.0, "thumb_pad": 3.0})
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    c = holder["c"]
    H.render_fp(rig, eye, c, os.path.join(OUT, "fp.png"))
    H.render_side(rig, c, Vector((-1, 0.7, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.35)
    H.render_side(rig, c, Vector((0.6, 0.5, 0.8)), os.path.join(OUT, "grip.png"), dist_m=0.25)
    H.render_side(rig, c + Vector((0, 0, 0.3)), Vector((-1, 0.2, 0.05)), os.path.join(OUT, "body.png"), dist_m=2.2)
    hold["body_clear"] = G.body_clear_mm(rig, sol.trees, BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, verdict=verdict, stand=st, place=place, rounds=rounds,
               knob=dict(head_ue=H.bl_to_ue_loc(c), head_radius_cm=1.9, note="commode life size until the editor dump"))
    json.dump(rep, open(prev, "w"), indent=1)
    print("DRAWER_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"], contacts=verdict["contacts"])))
    rot = com.frame.matrix_world.to_3x3().normalized().to_4x4()
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(com.frame.matrix_world),
                   anchor_ue=G.ue_frame(Matrix.Translation(c) @ rot), stand=st, twin=rep),  # anchor: the knob head, the commode's turn
              open("P:/FoA/Saved/AnimShots/drawer_grip_solution.json", "w"))


main()
