"""The boot (Boot_R "Look inside the boot", montage GRAB_FLOOR; the key is in the left boot), solved at MESH level in the
Blender twin (anim lane). Placement-free until the editor dump: a Poly Haven rubber boot (37 cm tall) standing on the
floor in front of him; he kneels (screwdriver_twin's kneel, the lean free up to 45 deg) and his right hand takes the
shaft just below the opening in a power grip, palm on the shaft's side, fingers round it, thumb opposite: the hold
that tips it to look in. knob_twin's grasp synthesis does the hand (the whole hand approaches the shaft cupped, then
every digit closes until it touches); the boot's axis plays the knob's axis.
Checks: no skin (hand and forearm) within 1 mm of the boot; index, middle and thumb pads within 3 mm; wrist <= 25 deg.
Writes Saved/RigShots/boot/{fp,side,grip,body}.png, check.json and Saved/AnimShots/boot_grip_solution.json.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/boot_twin.py [rounds=2] [resume=1]"""
import json
import os
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402
import knob_twin as K  # noqa: E402
import screwdriver_twin as S  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/boot"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = K.BODY_SCALE
SRC = "P:/FoA-Assets/polyhaven/models/rubber_boots/rubber_boots_1k.gltf"
GRIP_DOWN = 4.0  # cm below the opening where the hand takes the shaft


class Boot:
    """The right boot standing on the floor, life size against the game body (1/BODY_SCALE in the twin)."""

    def __init__(self):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=SRC)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type == "MESH" and o.name != "rubber_boots_r" and not (o.parent and o.parent.name == "rubber_boots_r"):
                o.hide_render = True  # one boot (the others stay out of the renders and the check)
        self.mesh = next(o for o in new if o.type == "MESH" and (o.name == "rubber_boots_r" or (o.parent and o.parent.name == "rubber_boots_r")))
        self.frame = bpy.data.objects.new("boot_frame", None)
        bpy.context.scene.collection.objects.link(self.frame)
        mw = self.mesh.matrix_world.copy()
        self.mesh.parent = self.frame
        self.mesh.matrix_world = mw
        vs = [self.mesh.matrix_world @ v.co for v in self.mesh.data.vertices]
        self.top = max(v.z for v in vs)
        c = sum(vs, Vector()) / len(vs)
        self.base = Vector((c.x, c.y, 0.0))  # the boot's footprint centre, import space
        ring = [v for v in vs if v.z > self.top - (GRIP_DOWN + 1.0) / 100 and v.z < self.top - (GRIP_DOWN - 1.0) / 100]
        self.axis_xy = sum(ring, Vector()) / len(ring)
        self.radius_cm = max(((v - self.axis_xy).xy.length for v in ring)) * 100 / BODY_SCALE
        print("BOOT top", round(self.top, 3), "shaft radius (twin cm)", round(self.radius_cm, 2), flush=True)

    def place(self, st):
        """The shaft's axis at (side, fwd) cm from his root, the boot turned `yaw` deg; returns (grip point, axis)."""
        R = Matrix.Rotation(st["yaw"] * 3.14159265 / 180.0, 4, "Z") @ Matrix.Scale(1.0 / BODY_SCALE, 4)
        want = H.ue_to_bl_loc((st["side"], st["fwd"], 0.0))
        a = R @ Vector((self.axis_xy.x, self.axis_xy.y, 0.0))
        self.frame.matrix_world = Matrix.Translation(Vector((want.x - a.x, want.y - a.y, 0.0))) @ R
        bpy.context.view_layer.update()
        grip = self.frame.matrix_world @ Vector((self.axis_xy.x, self.axis_xy.y, self.top - GRIP_DOWN / 100))
        return grip, Vector((0.0, 0.0, 1.0))


def main():
    rig, _ = H.load_teen()
    boot = Boot()
    st = dict(side=-18.0, fwd=40.0, lean=30.0, yaw=0.0)
    # the shaft's axis is 'out' (up): the palm normal starts facing down it; yaw -90 / pitch 80 puts the palm on the
    # shaft's right side facing left, yaw 0 / pitch -80 on its near side facing forward; roll +-90 wraps the fingers round
    place = dict(yaw=-90.0, pitch=80.0, roll=90.0, back=6.0, lift=0.0, elbow=0.0, spread=3.0, t1s=10.0, t1r=-40.0, cup=20.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        last = json.load(open(prev))
        st, place = dict(st, **last["stand"]), {k: last["place"].get(k, v) for k, v in place.items()}
    sol = K.Solver(rig, boot.radius_cm)
    holder = {}

    def setup(s):
        S.stance(rig, dict(s, side=0.0, fwd=0.0))  # the kneel; where the boot stands is the boot's placement
        holder["c"], holder["n"] = boot.place(s)
        sol.trees = [H._tree([boot.frame])[0]]
        holder["st"] = dict(s)

    def ev(s, pl):
        if holder.get("st") != s:
            setup(s)
        m = sol.grasp(holder["c"], holder["n"], pl)
        return m, cost(m)

    def cost(m):
        c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 40 * max(0.0, 1.0 - m["contact_min_mm"])
        c += 8 * sum(max(0.0, m["pads"][k] - 3.0) for k in ("index_pad", "middle_pad", "thumb_pad"))
        c += 4 * max(0.0, m["wrist_deg"] - 25) + 1.0 * (max(0.0, 90 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 165))
        return c + 500 * m["miss_cm"]

    def ok(m):
        return (m["clear_min_mm"] >= 1.0 and m["contact_min_mm"] >= 1.0 and m["wrist_deg"] <= 25 and m["miss_cm"] < 0.05
                and all(m["pads"][k] <= 3.0 for k in ("index_pad", "middle_pad", "thumb_pad")))

    keys_s, keys_p = list(st), list(place)
    lo = dict(side=-35, fwd=20, lean=10, yaw=-90, pitch=-140, roll=-180, back=3.0, lift=-3.0, elbow=-100, spread=-4, t1s=-40, t1r=-120, cup=0)
    hi = dict(side=5, fwd=60, lean=45, yaw=90, pitch=140, roll=180, back=10.0, lift=3.0, elbow=100, spread=10, t1s=50, t1r=60, cup=45)
    stp = [dict(side=3, fwd=3, lean=4, yaw=20, pitch=12, roll=20, back=1.0, lift=0.8, elbow=15, spread=2, t1s=10, t1r=15, cup=8),
           dict(side=1, fwd=1, lean=1.5, yaw=6, pitch=4, roll=6, back=0.3, lift=0.3, elbow=5, spread=1, t1s=3, t1r=5, cup=3)]
    split = lambda b: ({k: b[k] for k in keys_s}, {k: b[k] for k in keys_p})  # noqa: E731
    f = lambda b: ev(*split(b))[1]  # noqa: E731
    both = dict(st, **place)
    if ARGS.get("resume") != "1":
        starts = []  # the palm on the shaft's right side or its near side, the fingers round it either way
        for y0, p0, r0 in ((-90, 80, 90), (-90, 80, -90), (0, -80, 90), (0, -80, -90)):
            b, c0 = G.descend(f, dict(both, yaw=y0, pitch=p0, roll=r0), stp[:1], list(both), lo, hi)
            starts.append((c0, b))
            print("BOOT start", y0, p0, r0, round(c0, 1), json.dumps(ev(*split(b))[0]), flush=True)
        both = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        both, _ = G.descend(f, both, stp, list(both), lo, hi)
        both, _ = G.perturb(f, both, list(both), stp[1], lo, hi, iters=int(ARGS.get("iters", 120)))
        m, c = ev(*split(both))
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("BOOT round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    st, place = split(both)
    hold, _ = ev(st, place)
    verdict = H.check(rig, [boot.frame], "r", contacts={"index_pad": 3.0, "middle_pad": 3.0, "thumb_pad": 3.0})
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    c = holder["c"]
    H.render_fp(rig, eye, c, os.path.join(OUT, "fp.png"))
    H.render_side(rig, c, Vector((-1, 0.7, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.4)
    H.render_side(rig, c, Vector((0.6, -0.8, 0.5)), os.path.join(OUT, "grip.png"), dist_m=0.35)
    H.render_side(rig, c + Vector((0, 0.2, 0.3)), Vector((-1, 0.15, 0.1)), os.path.join(OUT, "body.png"), dist_m=2.6)
    hold["body_clear"] = G.body_clear_mm(rig, sol.trees, BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, verdict=verdict, stand=st, place=place, rounds=rounds,
               boot=dict(grip_ue=H.bl_to_ue_loc(c), note="placement-free: upright on the floor in front of him, until the editor dump"))
    json.dump(rep, open(prev, "w"), indent=1)
    print("BOOT_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"], contacts=verdict["contacts"])))
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(boot.frame.matrix_world),
                   anchor_ue=G.ue_frame(Matrix.Translation(c)), stand=st, twin=rep),
              open("P:/FoA/Saved/AnimShots/boot_grip_solution.json", "w"))


main()
