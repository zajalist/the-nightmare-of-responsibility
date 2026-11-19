"""Taking the shirt (Shirt_T7: SM_Lux3D_ShirtEnemy, the living shirt; it stands on edge at every landing, 75 cm tall and
14 cm deep, pivot at mid-height: main and story, 2026-11-10), solved at MESH level in the Blender twin (anim lane), in
place: the game's own mesh (exported FBX) at its dumped transform. Every landing shares its rotation and scale, so the
solve relative to the shirt holds at each. The take is a quick snatch after the chase ("Got you."): he stands at its
broad side (the room side, +X), his right hand comes down on its top edge and closes on it, thumb on one face, index
and middle over the edge onto the other. knob_twin's grasp synthesis does the hand (the whole hand comes down cupped
until it is 2 mm off the cloth, then every digit closes until it touches); 'out' is up. The stance is where he stands
(dx in front of it, dy along it), his turn and his lean.
Checks: no skin (hand and forearm; the rest of the body near it) within 1 mm of the cloth (a solid crumple, not a sim);
thumb, index and middle pads within 3 mm; wrist <= 25 deg; the palm faces down.
Writes Saved/RigShots/shirt/{fp,side,grip,body}.png, check.json and Saved/AnimShots/shirt_grip_solution.json.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/shirt_twin.py [rounds=2] [resume=1]"""
import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402
import knob_twin as K  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/shirt"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = K.BODY_SCALE


class Shirt:
    def __init__(self):
        dump = json.load(open(G.ANCHORS))["Shirt_T7"]
        mesh = next(c for c in dump["comps"] if c["name"] == "Mesh")
        self.world = G.ue_matrix(mesh["world"]["loc"], mesh["world"]["quat"], mesh["world"]["scale"])
        self.frame = G.load_ue_mesh("SM_Lux3D_ShirtEnemy")
        self.frame.matrix_world = self.world
        bpy.context.view_layer.update()
        self.pts = [o.matrix_world @ v.co for o in self.frame.children if o.type == "MESH" for v in o.data.vertices]
        self.centre = sum(self.pts, Vector()) / len(self.pts)
        self.top = max(p.z for p in self.pts)
        print("SHIRT world box", [round(min(p[i] for p in self.pts) * 100, 1) for i in range(3)],
              [round(max(p[i] for p in self.pts) * 100, 1) for i in range(3)], flush=True)

    def grab_point(self, along_cm):
        """The top of the edge `along_cm` from its middle along the shirt's width (world Y), toward the room side."""
        y = self.centre.y - along_cm / 100  # Blender y = -UE y
        band = [p for p in self.pts if abs(p.y - y) < 0.03 and p.z > self.top - 0.06]
        return max(band, key=lambda p: p.z + 0.2 * p.x)  # high, and toward the room (+X)

    def place(self, st):
        """He stands dx cm in front of its room-side face (+X), dy cm along it, facing it (-X) turned by yaw."""
        c = H.bl_to_ue_loc(self.centre)
        body = G.body_matrix(c[0] + st["dx"], c[1] + st["dy"], 180.0 + st["yaw"])
        G.place_in_body(self.frame, self.world, body)
        return body.inverted() @ self.grab_point(st["along"]), Vector((0.0, 0.0, 1.0))


def main():
    rig, _ = H.load_teen()
    shirt = Shirt()
    st = dict(dx=35.0, dy=10.0, yaw=0.0, lean=15.0, along=-10.0)
    place = dict(yaw=0.0, pitch=0.0, roll=0.0, back=6.0, lift=0.0, elbow=0.0, spread=4.0, t1s=10.0, t1r=-40.0, cup=25.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        last = json.load(open(prev))
        st, place = dict(st, **last["stand"]), {k: last["place"].get(k, v) for k, v in place.items()}
    sol = K.Solver(rig, 0.5)  # the approach starts just above the grab point
    holder = {}

    def setup(s):
        K.stance(rig, s)
        holder["c"], holder["n"] = shirt.place(s)
        sol.trees = [H._tree([shirt.frame])[0]]
        holder["st"] = dict(s)

    def ev(s, pl):
        if holder.get("st") != s:
            setup(s)
        m = sol.grasp(holder["c"], holder["n"], pl)
        return m, cost(m)

    def cost(m):
        c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 40 * max(0.0, 1.0 - m["contact_min_mm"])
        c += 8 * sum(max(0.0, m["pads"][k] - 3.0) for k in ("index_pad", "middle_pad", "thumb_pad"))
        c += 4 * max(0.0, m["wrist_deg"] - 25) + 1.0 * (max(0.0, 90 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 170))
        c += 50 * max(0.0, m["palm_up"] + 0.3)  # the palm faces down onto the edge
        return c + 500 * m["miss_cm"]

    def ok(m):
        return (m["clear_min_mm"] >= 1.0 and m["contact_min_mm"] >= 1.0 and m["wrist_deg"] <= 25 and m["miss_cm"] < 0.05
                and m["palm_up"] <= -0.3 and all(m["pads"][k] <= 3.0 for k in ("index_pad", "middle_pad", "thumb_pad")))

    # stance keys are prefixed s_ in the search vector: the stance's yaw and the hand's yaw are different things
    lo_s, hi_s = dict(dx=20, dy=-35, yaw=-35, lean=0, along=-30), dict(dx=60, dy=35, yaw=35, lean=40, along=30)
    st_s = [dict(dx=3, dy=3, yaw=6, lean=3, along=4), dict(dx=1, dy=1, yaw=2, lean=1, along=1.5)]
    lo_p = dict(yaw=-60, pitch=-50, roll=-180, back=3.0, lift=-3.0, elbow=-100, spread=-4, t1s=-40, t1r=-120, cup=0)
    hi_p = dict(yaw=60, pitch=50, roll=180, back=10.0, lift=3.0, elbow=100, spread=10, t1s=50, t1r=60, cup=50)
    st_p = [dict(yaw=10, pitch=10, roll=20, back=1.0, lift=0.8, elbow=15, spread=2, t1s=10, t1r=15, cup=8),
            dict(yaw=3, pitch=3, roll=6, back=0.3, lift=0.3, elbow=5, spread=1, t1s=3, t1r=5, cup=3)]
    pre = lambda d: {"s_" + k: v for k, v in d.items()}  # noqa: E731
    lo, hi = dict(pre(lo_s), **lo_p), dict(pre(hi_s), **hi_p)
    stp = [dict(pre(a), **b) for a, b in zip(st_s, st_p)]
    split = lambda b: ({k: b["s_" + k] for k in st}, {k: b[k] for k in place})  # noqa: E731
    f = lambda b: ev(*split(b))[1]  # noqa: E731
    both = dict(pre(st), **place)
    keys = list(both)
    if ARGS.get("resume") != "1":
        starts = []  # the hand comes down onto the edge, the fingers across it toward the far face / along it / back
        for r0 in (90.0, 0.0, -90.0):
            b, c0 = G.descend(f, dict(both, roll=r0), stp[:1], keys, lo, hi)
            starts.append((c0, b))
            print("SHIRT start", r0, round(c0, 1), json.dumps(ev(*split(b))[0]), flush=True)
        both = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        both, _ = G.descend(f, both, stp, keys, lo, hi)
        both, _ = G.perturb(f, both, keys, stp[1], lo, hi, iters=int(ARGS.get("iters", 100)))
        m, c = ev(*split(both))
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("SHIRT round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    st, place = split(both)
    hold, _ = ev(st, place)
    verdict = H.check(rig, [shirt.frame], "r", contacts={"index_pad": 3.0, "middle_pad": 3.0, "thumb_pad": 3.0})
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    c = holder["c"]
    H.render_fp(rig, eye, c, os.path.join(OUT, "fp.png"))
    H.render_side(rig, c, Vector((-1, 0.7, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.4)
    H.render_side(rig, c, Vector((0.5, 0.6, 0.6)), os.path.join(OUT, "grip.png"), dist_m=0.35)
    H.render_side(rig, c + Vector((0, 0.2, 0.2)), Vector((-1, 0.15, 0.1)), os.path.join(OUT, "body.png"), dist_m=2.6)
    hold["body_clear"] = G.body_clear_mm(rig, sol.trees, BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, verdict=verdict, stand=st, place=place, rounds=rounds,
               shirt=dict(grab_ue=H.bl_to_ue_loc(c), note="in place: Shirt_T7 standing on edge (the dump)"))
    json.dump(rep, open(prev, "w"), indent=1)
    print("SHIRT_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"], contacts=verdict["contacts"])))
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(shirt.frame.matrix_world),
                   anchor_ue=G.ue_frame(Matrix.Translation(c)), stand=st, twin=rep),
              open("P:/FoA/Saved/AnimShots/shirt_grip_solution.json", "w"))


main()
