"""Door knob grip (AM_FoA_TryLockedHandle: grip, rattle), solved at MESH level in the Blender twin (anim lane). Standing.
Right hand, a spherical power grip: the palm on the knob, the fingers round it with their pads 1-3 mm off it, the thumb
opposite; no skin vertex within 1 mm of the knob or the door; wrist <= 25 deg.
Grasp synthesis, not a blind search over curls: for each hand placement the palm APPROACHES along its normal until it is
1.6 mm off (grip_twin.approach), then every digit CLOSES GraspIt-style until it touches (grip_twin.close_digits), so no
finger can end inside the knob. The search is over the stance (where he stands, how far he leans) and the hand's
orientation only. v1 searched the curls too and never left a straight-armed, 95-deg-wrist minimum.
The knob is a stand-in until the editor dump (rig: the bedroom door glb is normalised, its knob not separable): a
5.6 cm ball on a 2.4 cm neck, its centre 6 cm out from the door face, 9 cm above the keyhole (screenshot 67).
Writes Saved/RigShots/knob/{fp,side,grip,body}.png, check.json and Saved/AnimShots/knob_grip_solution.json. Nothing is baked.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/knob_twin.py [rounds=2] [resume=1]"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))
import grip_twin as G  # noqa: E402
import hand_twin as H  # noqa: E402

ARGS = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:] if "=" in a) if "--" in sys.argv else {}
OUT = "P:/FoA/Saved/RigShots/knob"
os.makedirs(OUT, exist_ok=True)
BODY_SCALE = 170.0 / 180.0
KEY_Z = (88.5 - 3.094446780476119) / BODY_SCALE
KNOB_Z = KEY_Z + 9.0 / BODY_SCALE
KNOB_R, NECK_R, KNOB_OUT = 2.8 / BODY_SCALE, 1.2 / BODY_SCALE, 6.0 / BODY_SCALE  # twin cm
DOOR_Y = 48.28 + 3.97 + 1.0
DIG = ("thumb", "index", "middle", "ring", "pinky")
FULL = {d: (90.0, 100.0, 70.0) for d in DIG[1:]}
FULL["thumb"] = (35.0, 55.0, 75.0)
TARGET = 2.0  # game mm: where a closing digit or the approaching palm stops (v5 at 1.6 on every other vertex: 0.2 mm in)


def make_knob(st):
    """The door slab and a knob (ball + neck) as one mesh; returns (object, knob centre, outward normal) in Blender m."""
    face = H.ue_to_bl_loc((st["side"], DOOR_Y + st["fwd"], KNOB_Z))
    out = Vector((0.0, 1.0, 0.0))
    centre = face + out * KNOB_OUT / 100
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=KNOB_R / 100)
    bmesh.ops.translate(bm, verts=bm.verts, vec=centre)
    neck = bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=NECK_R / 100, radius2=NECK_R / 100, depth=KNOB_OUT / 100)
    rot = Matrix.Rotation(math.radians(90), 4, "X")
    bmesh.ops.rotate(bm, verts=neck["verts"], cent=Vector(), matrix=rot)
    bmesh.ops.translate(bm, verts=neck["verts"], vec=face + out * KNOB_OUT / 200)
    door = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((0.9, 0.04, 1.2)), verts=door["verts"])
    bmesh.ops.translate(bm, verts=door["verts"], vec=face - out * 0.02)
    me = bpy.data.meshes.new("knob_door")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("knob_door", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = bpy.data.objects.get("knob_frame") or bpy.data.objects.new("knob_frame", None)  # H.check reads a frame's meshes
    if ob.parent.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(ob.parent)
    return ob, centre, out


class RealDoor:
    """real=1: the game's own SM_Door_Bedroom (exported FBX) at its dumped transform. Its knob is part of the mesh, a
    low-poly lump 6 cm across and 6 cm proud, 8 cm above the keyhole; the twin body stands square to the door (the
    actor facing +X) with the knob at (side, fwd) in his component space, as the stand-in was."""

    def __init__(self):
        import json
        dump = json.load(open(G.ANCHORS))["Door_Bedroom"]
        mesh = next(c for c in dump["comps"] if c["name"] == "Mesh")
        self.world = G.ue_matrix(mesh["world"]["loc"], mesh["world"]["quat"], mesh["world"]["scale"])
        self.frame = G.load_ue_mesh("SM_Door_Bedroom")
        self.frame.matrix_world = self.world
        bpy.context.view_layer.update()
        pts = [o.matrix_world @ v.co for o in self.frame.children if o.type == "MESH" for v in o.data.vertices]
        face_x = next(c for c in dump["comps"] if c["name"] == "ToolContact")["world"]["loc"][0] / 100  # the door face (key contact)
        lump = [p for p in pts if p.x < face_x - 0.008]  # proud of the face on the player's side (-X in the world)
        self.knob = sum(lump, Vector()) / len(lump)  # Blender world
        self.radius_cm = max((p - self.knob).length for p in lump) * 100 / BODY_SCALE * 0.8
        print("KNOB real lump", len(lump), "centre (UE world)", tuple(round(x, 1) for x in H.bl_to_ue_loc(self.knob)), flush=True)

    def place(self, st):
        """The body placed so the knob sits at (side, 6 cm short of DOOR_Y + fwd) in his twin component space."""
        knob_ue = H.bl_to_ue_loc(self.knob)
        f = (DOOR_Y + st["fwd"] - KNOB_OUT) * BODY_SCALE
        body = G.body_matrix(knob_ue[0] - f, knob_ue[1] + st["side"] * BODY_SCALE, 0.0)
        G.place_in_body(self.frame, self.world, body)
        centre = body.inverted() @ self.knob
        out = (body.inverted().to_3x3() @ Vector((-1.0, 0.0, 0.0))).normalized()
        return centre, out


def stance(rig, st):
    """Standing; the spine leans st['lean'] deg forward (a hip-high knob is otherwise a straight-armed reach); the free
    arm hangs at his side."""
    G.reset_bones(rig, [b.name for b in rig.ob.pose.bones])
    for b in rig.spine_chain():
        rig.rot(b, Vector((1.0, 0.0, 0.0)), st["lean"] / len(rig.spine_chain()))
    rig.aim("upperarm_l", Vector((0.1, 0, -1)))
    rig.aim("lowerarm_l", Vector((0.05, -0.15, -1)))


def hand_frame(out, p):
    """Palm normal n: from facing the door (-out), turned by yaw (90: palm to his left, thumb up) and pitch (90: palm
    down, over the knob). Finger line d: `roll` deg about n from 'toward the door'."""
    n = (Matrix.Rotation(math.radians(p["yaw"]), 3, Vector((0, 0, 1))) @ Matrix.Rotation(math.radians(p["pitch"]), 3, Vector((1, 0, 0))) @ -out).normalized()
    ref = -out - n * n.dot(-out)
    ref = ref if ref.length > 1e-3 else Vector((0, 0, 1)) - n * n.z
    return (Matrix.Rotation(math.radians(p["roll"]), 3, n) @ ref.normalized()).normalized(), n


def place_hand(rig, centre, d, n, r, p):
    """The palm point (hand bone + `back` along d, `lift` off the palm) r cm from the knob centre against n; the arm
    reaches it with the elbow swung `elbow` deg about the shoulder-wrist line from out-and-down."""
    wrist = centre - n * r / 100 - d * p["back"] / 100 + n * p["lift"] / 100
    G.reset_bones(rig, ["upperarm_r", "lowerarm_r", "hand_r"] + [b for b in rig.names if "twist" in b and b.endswith("_r")])
    sh = rig.head("upperarm_r")
    pole = sh + Matrix.Rotation(math.radians(p["elbow"]), 3, (wrist - sh).normalized()) @ Vector((-0.3, 0.05, -0.35))
    miss = G.two_bone(rig, "r", wrist, pole)
    G.aim_hand(rig, "r", d, n)
    G.share_twist(rig, "r")
    return miss


def pose_digits(rig, p, ang):
    """Digits from open: the fingers spread, the thumb's metacarpal spread and rolled (its opposition), then the curls."""
    G.reset_bones(rig, [f"{dg}_{j}_r" for dg in DIG for j in G.SEGS])
    for i, dg in enumerate(DIG[1:]):
        rig.spread(f"{dg}_01_r", p["spread"] * (i - 1.5))
    rig.spread("thumb_01_r", p["t1s"])
    rig.rot("thumb_01_r", rig.dir("thumb_01_r"), p["t1r"])
    for dg in DIG:
        for j, a in zip(G.SEGS, ang.get(dg, (0.0, 0.0, 0.0))):
            rig.flex(f"{dg}_{j}_r", a)


class Solver:
    """Approach-and-close grasp of a round knob (radius_cm, twin cm) on a door/drawer face; drawer_twin.py reuses it."""

    def __init__(self, rig, radius_cm=KNOB_R):
        self.rig, self.radius = rig, radius_cm
        self.skin = G.HandSkin(rig, "r")
        reg = H.regions(rig, "r")
        pos = {i: r for r, i in enumerate(self.skin.idx)}
        self.pads = {k: [pos[i] for i in reg.get(k, ()) if i in pos]
                     for k in ("index_pad", "middle_pad", "ring_pad", "pinky_pad", "thumb_pad", "palm")}
        self.all_rows = (self.skin.rows[("hand",)] + self.skin.rows[("forearm",)][::2]
                         + [r for d in DIG for s in G.SEGS for r in self.skin.rows.get((d, s), [])[::2]])
        # every other vertex while closing, except the fingertips (v6: the middle's apex vertex was skipped, 1.8 mm in)
        self.seg_rows = {(d, s): self.skin.rows.get((d, s), [])[::1 if s == "03" else 2] for d in DIG for s in G.SEGS}
        self.trees = []

    def dist(self, co, rows):
        return min((G.signed_mm(self.trees, co[r], BODY_SCALE) for r in rows), default=99.0)

    def grasp(self, centre, out, p):
        """Approach, close, measure; returns the metrics."""
        d, n = hand_frame(out, p)
        rig, miss = self.rig, [0.0]
        pre = {dg: (p["cup"], p["cup"], p["cup"] * 0.7) for dg in DIG[1:]}  # the hand reaches cupped
        pre["thumb"] = (0.0, p["cup"] * 0.5, p["cup"] * 0.5)
        pose_digits(rig, p, pre)

        def set_r(r):
            miss[0] = place_hand(rig, centre, d, n, r, p)

        def seg_dist(segs):
            co = self.skin()
            return {dg: self.dist(co, [r for s in segs for r in self.seg_rows[(dg, s)]]) for dg in DIG}
        # the whole hand approaches (v4 measured only the palm: straight fingers ended 17 mm inside the door)
        G.approach(set_r, lambda: self.dist(self.skin(), self.all_rows), self.radius + 0.3, self.radius + 9.0, TARGET)
        ang = G.close_digits(lambda a: pose_digits(rig, p, a), seg_dist, DIG, FULL, TARGET, start=pre)
        co = self.skin()
        sd = [G.signed_mm(self.trees, c, BODY_SCALE) for c in co]
        contact = set().union(*self.pads.values())
        fa = (rig.head("hand_r") - rig.head("lowerarm_r")).normalized()
        ua = (rig.head("lowerarm_r") - rig.head("upperarm_r")).normalized()
        return dict(clear_min_mm=round(min(v for r, v in enumerate(sd) if r not in contact), 2),
                    contact_min_mm=round(min(sd[r] for r in contact), 2),
                    pen=round(sum(max(0.0, 1.0 - v) ** 2 for v in sd), 2),
                    pads={k: round(min((sd[r] for r in v), default=99.0), 2) for k, v in self.pads.items()},
                    wrist_deg=round(math.degrees(fa.angle(rig.dir("hand_r"))), 1), elbow_deg=round(180 - math.degrees(ua.angle(fa)), 1),
                    miss_cm=round(miss[0] * 100, 2), palm_up=round(n.z, 2), curls={k: [round(x, 1) for x in v] for k, v in ang.items()})


def cost(m):
    c = 10 * m["pen"] + 40 * max(0.0, 1.0 - m["clear_min_mm"]) + 40 * max(0.0, 1.0 - m["contact_min_mm"])
    c += 8 * sum(max(0.0, v - 3.0) for k, v in m["pads"].items() if k != "pinky_pad") + 2 * max(0.0, m["pads"]["pinky_pad"] - 3.0)
    c += 4 * max(0.0, m["wrist_deg"] - 25) + 1.0 * (max(0.0, 130 - m["elbow_deg"]) + max(0.0, m["elbow_deg"] - 165))
    c += 100 * max(0.0, m["palm_up"] - 0.2)  # v5 cupped it from underneath, palm up: nobody turns a knob like that
    return c + 500 * m["miss_cm"]


def ok(m):
    return (m["clear_min_mm"] >= 1.0 and m["contact_min_mm"] >= 1.0 and m["wrist_deg"] <= 25 and m["miss_cm"] < 0.05
            and m["palm_up"] <= 0.2
            and all(v <= 3.0 for k, v in m["pads"].items() if k != "pinky_pad"))


def main():
    rig, _ = H.load_teen()
    st = dict(side=-14.0, fwd=-10.0, lean=8.0)
    place = dict(yaw=60.0, pitch=40.0, roll=0.0, back=6.0, lift=0.0, elbow=0.0, spread=4.0, t1s=10.0, t1r=-40.0, cup=20.0)
    prev = os.path.join(OUT, "check.json")
    if ARGS.get("resume") == "1" and os.path.exists(prev):
        last = json.load(open(prev))
        st, place = dict(st, **last["stand"]), {k: last["place"].get(k, v) for k, v in place.items()}
    real = RealDoor() if ARGS.get("real") == "1" else None
    sol = Solver(rig, real.radius_cm if real else KNOB_R)
    holder = {}

    def setup(s):
        stance(rig, s)
        if real:
            holder["c"], holder["n"] = real.place(s)
            holder["obj"] = real.frame
            sol.trees = [H._tree([real.frame])[0]]
        else:
            if holder.get("obj"):
                bpy.data.objects.remove(holder["obj"])
            holder["obj"], holder["c"], holder["n"] = make_knob(s)
            sol.trees = [BVHTree.FromObject(holder["obj"], bpy.context.evaluated_depsgraph_get())]
        holder["st"] = dict(s)

    def ev(s, pl):
        if holder.get("st") != s:
            setup(s)
        m = sol.grasp(holder["c"], holder["n"], pl)
        return m, cost(m)

    keys_s, keys_p = list(st), list(place)
    lo = dict(side=-30, fwd=-14, lean=0, yaw=-60, pitch=-30, roll=-180, back=3.0, lift=-3.0, elbow=-100, spread=-4, t1s=-40, t1r=-120, cup=0)
    hi = dict(side=0, fwd=0, lean=20, yaw=110, pitch=110, roll=180, back=10.0, lift=3.0, elbow=100, spread=10, t1s=50, t1r=60, cup=45)
    stp = [dict(side=3, fwd=3, lean=3, yaw=12, pitch=12, roll=20, back=1.0, lift=0.8, elbow=15, spread=2, t1s=10, t1r=15, cup=8),
           dict(side=1, fwd=1, lean=1, yaw=4, pitch=4, roll=6, back=0.3, lift=0.3, elbow=5, spread=1, t1s=3, t1r=5, cup=3)]
    split = lambda b: ({k: b[k] for k in keys_s}, {k: b[k] for k in keys_p})  # noqa: E731
    f = lambda b: ev(*split(b))[1]  # noqa: E731
    both = dict(st, **place)
    if ARGS.get("resume") != "1":
        starts = []  # hand families: the palm on its face (fingers up / across), beside it thumb up, between, over it
        for y0, p0, r0 in ((5, 5, 90), (5, 5, 0), (30, 40, 60)):  # v6: across the face (90) was best, then fingers up
            b, c0 = G.descend(f, dict(both, yaw=y0, pitch=p0, roll=r0), stp[:1], list(both), lo, hi)
            starts.append((c0, b))
            print("KNOB start", y0, p0, r0, round(c0, 1), json.dumps(ev(*split(b))[0]), flush=True)
        both = min(starts, key=lambda t: t[0])[1]
    rounds = []
    for rnd in range(int(ARGS.get("rounds", 2))):
        both, _ = G.descend(f, both, stp, list(both), lo, hi)
        both, _ = G.perturb(f, both, list(both), stp[1], lo, hi, iters=int(ARGS.get("iters", 120)))
        m, c = ev(*split(both))
        rounds.append(dict(round=rnd, cost=round(c, 2), fast=m))
        print("KNOB round", rnd, round(c, 2), json.dumps(m), flush=True)
        if ok(m):
            break
    st, place = split(both)
    hold, _ = ev(st, place)
    verdict = H.check(rig, [real.frame if real else holder["obj"].parent], "r", contacts={"index_pad": 3.0, "middle_pad": 3.0, "thumb_pad": 3.0, "palm": 3.0})
    eye = H.ue_point(rig, "head", H.EYE_HEAD)
    H.render_fp(rig, eye, holder["c"], os.path.join(OUT, "fp.png"))
    H.render_side(rig, holder["c"], Vector((-1, 0.7, 0.3)), os.path.join(OUT, "side.png"), dist_m=0.35)
    H.render_side(rig, holder["c"], Vector((0.6, 0.5, 0.8)), os.path.join(OUT, "grip.png"), dist_m=0.25)
    H.render_side(rig, holder["c"] + Vector((0, 0, 0.3)), Vector((-1, 0.2, 0.05)), os.path.join(OUT, "body.png"), dist_m=2.2)
    hold["body_clear"] = G.body_clear_mm(rig, sol.trees, BODY_SCALE)
    passed = ok(hold) and verdict["pass"] and hold["body_clear"][0] >= 1.0
    rep = dict(passed=passed, hold=hold, verdict=verdict, stand=st, place=place, rounds=rounds,
               knob=dict(centre_ue=H.bl_to_ue_loc(holder["c"]), radius_cm=KNOB_R * BODY_SCALE,
                         note="the game's SM_Door_Bedroom" if real else "stand-in until the editor dump"))
    json.dump(rep, open(prev, "w"), indent=1)
    print("KNOB_CHECK", "passed" if passed else "FAILED", json.dumps(dict(hold=hold, rig_pass=verdict["pass"], contacts=verdict["contacts"])))
    json.dump(dict(pose=H.export_ue_local(rig), hand_ue=H.ue_bone(rig, "hand_r"), object_ue=G.ue_frame(Matrix.Translation(holder["c"])),
                   stand=st, twin=rep),
              open("P:/FoA/Saved/AnimShots/knob_grip_solution.json", "w"))


if __name__ == "__main__":
    main()
