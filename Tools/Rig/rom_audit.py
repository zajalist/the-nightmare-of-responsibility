"""Range-of-motion audit: the Teen (exactly the FBX that UE imported) and the UE5 Manny, posed identically.
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/rom_audit.py out=<dir> [teen=<body.fbx>] [garments=a.fbx;b.fbx] [poses=a,b]
Poses are built from each skeleton's own joint positions (anatomical axes: limb directions, the knuckle line, the palm
normal), never from bone rolls, so the renders and numbers compare SKINNING only. Writes <out>/<pose>_<shot>_<who>.png
and <out>/metrics.json. Read-only: never saves a .blend."""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

A = dict(x.split("=", 1) for x in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in x)
X = "P:/FoA-Assets/character/mpfb/export/"
TEEN = A.get("teen", X + "teen_chest_flattened/SK_Teen_Body.fbx")
GARMENTS = [g for g in A.get("garments", X + "teen_polo_drape/SK_Teen_Polo.fbx;" + X + "teen_cm/SK_Teen_Pants.fbx;"
                             + X + "teen_cm/SK_Teen_Socks.fbx").split(";") if g]
MANNY = "P:/FoA-Assets/character/v3/manny/SKM_Manny_Simple.fbx"
OUT = A.get("out", "P:/FoA/Saved/RigShots/audit/rom_before")
WHO = A.get("who", "teen,manny").split(",")
os.makedirs(OUT, exist_ok=True)
F, L, U = Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 0, 1))  # both rigs face -Y, left is +X
DIGITS = ("thumb", "index", "middle", "ring", "pinky")


def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def load(path, tag):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o.name = tag + "_" + o.name
    return new


class Rig:
    """One skeleton with anatomical axes stored in bone-local space, so poses ignore bone roll."""

    def __init__(self, tag, path, garments=()):
        new = load(path, tag)
        self.tag = tag
        self.ob = next(o for o in new if o.type == "ARMATURE")
        meshes = [o for o in new if o.type == "MESH"]
        for o in meshes:
            if "LOD1" in o.name or "LOD2" in o.name or "LOD3" in o.name:
                bpy.data.objects.remove(o)
        self.body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(tag) and "LOD1" not in o.name)
        self.garments = []
        for g in garments:  # each garment FBX carries its own copy of the rig: bind the mesh to ours
            gn = load(g, tag + "g")
            for o in gn:
                if o.type == "MESH":
                    for m in o.modifiers:
                        if m.type == "ARMATURE":
                            m.object = self.ob
                    o.parent = self.ob
                    o.matrix_parent_inverse.identity()
                    self.garments.append(o)
            for o in gn:
                if o.type == "ARMATURE":
                    bpy.data.objects.remove(o)
        self.masked = self._masked_body() if self.garments else None
        bpy.context.view_layer.update()
        self.names = {b.name for b in self.ob.data.bones}
        self.s = self.ob.matrix_world.to_scale()[0]
        self.rest = {b.name: self.ob.matrix_world @ b.matrix_local for b in self.ob.data.bones}
        self.axes = {}
        self._anatomy()

    def _masked_body(self):
        """A copy of the body without the skin the worn garments hide in game (BP_FoAPlayer hides any
        Skin_under_<garments> section whose garment list includes a worn garment)."""
        worn = ("foa_polo_layered", "toigo_wool_pants", "joepal_crude_low_socks")
        m = self.body.copy()
        m.data = self.body.data.copy()
        m.name = self.tag + "_masked"
        bpy.context.scene.collection.objects.link(m)
        hide = {i for i, sl in enumerate(m.material_slots) if sl.material and sl.material.name.startswith("Skin_under_")
                and any(g in sl.material.name for g in worn)}
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(m.data)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in hide], context="FACES_ONLY")
        bm.to_mesh(m.data)
        bm.free()
        m.hide_render = True
        return m

    # world-space helpers ---------------------------------------------------
    def has(self, b):
        return b in self.names

    def mat(self, b):
        return self.ob.matrix_world @ self.ob.pose.bones[b].matrix

    def head(self, b):
        return self.mat(b).to_translation()

    def rest_head(self, b):
        return self.rest[b].to_translation()

    def local(self, b, v):
        return self.rest[b].to_3x3().normalized().inverted() @ v

    def world(self, b, v):
        return (self.mat(b).to_3x3().normalized() @ v).normalized()

    def rot(self, b, axis, deg):
        """Rotate bone b (and its children) about a world axis through its head."""
        if not self.has(b) or deg == 0:
            return
        pb = self.ob.pose.bones[b]
        h = self.head(b)
        mw = self.ob.matrix_world
        r = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis.normalized()) @ Matrix.Translation(-h)
        pb.matrix = mw.inverted() @ r @ mw @ pb.matrix
        bpy.context.view_layer.update()

    def dir(self, b):
        return self.world(b, self.axes[b]["d"])

    def aim(self, b, want):
        cur, want = self.dir(b), want.normalized()
        a = cur.angle(want)
        if a > 1e-4:
            self.rot(b, cur.cross(want), math.degrees(a))

    # anatomy ---------------------------------------------------------------
    def _anatomy(self):
        kids = {}
        for b in self.ob.data.bones:
            if b.parent:
                kids.setdefault(b.parent.name, []).append(b.name)
        pref = {"hand_l": "middle_01_l", "hand_r": "middle_01_r", "lowerarm_l": "hand_l", "lowerarm_r": "hand_r",
                "upperarm_l": "lowerarm_l", "upperarm_r": "lowerarm_r", "thigh_l": "calf_l", "thigh_r": "calf_r",
                "calf_l": "foot_l", "calf_r": "foot_r", "foot_l": "ball_l", "foot_r": "ball_r", "pelvis": "spine_01"}
        for side in "lr":
            for dg in DIGITS:
                if self.has(f"{dg}_metacarpal_{side}"):
                    pref[f"{dg}_metacarpal_{side}"] = f"{dg}_01_{side}"
        for b in self.names:
            c = pref.get(b)
            if not c:
                for j, k in (("01", "02"), ("02", "03")):
                    if b.endswith(f"_{j}_l") or b.endswith(f"_{j}_r"):
                        c = b.replace(f"_{j}_", f"_{k}_")
            if c and self.has(c):
                d = self.rest_head(c) - self.rest_head(b)
            elif b.split("_")[0] in DIGITS and "_03_" in b:
                d = self.rest_head(b) - self.rest_head(b.replace("_03_", "_02_"))
            else:
                continue
            if d.length > 1e-6:
                self.axes[b] = {"d": self.local(b, d.normalized())}
        for side in "lr":
            k = (self.rest_head(f"pinky_01_{side}") - self.rest_head(f"index_01_{side}")).normalized()
            fd = (self.rest_head(f"middle_02_{side}") - self.rest_head(f"middle_01_{side}")).normalized()
            n = k.cross(fd).normalized()
            mid = (self.rest_head(f"index_01_{side}") + self.rest_head(f"pinky_01_{side}")) / 2
            if (self.rest_head(f"thumb_03_{side}") - mid).dot(n) < 0:
                n = -n  # palm side is where the thumb sits
            self.axes[f"hand_{side}"].update(n=self.local(f"hand_{side}", n), k=self.local(f"hand_{side}", k))
            for dg in DIGITS:
                for j in ("01", "02", "03"):
                    b = f"{dg}_{j}_{side}"
                    self.axes[b]["n"] = self.local(b, n)
                    self.axes[b]["k"] = self.local(b, k)

    def flex(self, b, deg):
        """Bend a phalanx toward the palm."""
        if b not in self.axes:
            return
        d, n = self.dir(b), self.world(b, self.axes[b]["n"])
        self.rot(b, d.cross(n), deg)

    def spread(self, b, deg):
        """Abduct a finger in the palm plane (positive = toward the pinky side)."""
        d, k = self.dir(b), self.world(b, self.axes[b]["k"])
        self.rot(b, d.cross(k), deg)

    def reset(self):
        for pb in self.ob.pose.bones:
            pb.matrix_basis.identity()
        bpy.context.view_layer.update()

    def spine_chain(self):
        return [b for b in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05") if self.has(b)]

    def twist_bones(self, limb, side):
        return [b for b in (f"{limb}_twist_01_{side}", f"{limb}_twist_02_{side}") if self.has(b)]

    def twist_forearm(self, side, deg):
        """Pronate: the hand turns about the forearm; Manny's twist bones share it by their place on the forearm."""
        axis = (self.head(f"hand_{side}") - self.head(f"lowerarm_{side}")).normalized()
        e, w = self.head(f"lowerarm_{side}"), self.head(f"hand_{side}")
        for t in self.twist_bones("lowerarm", side):  # rotate twist bones about the same axis, by position
            frac = max(0.0, min(1.0, (self.head(t) - e).dot(axis) / (w - e).length))
            pb = self.ob.pose.bones[t]
            h = self.head(t)
            mw = self.ob.matrix_world
            r = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg * frac), 4, axis) @ Matrix.Translation(-h)
            pb.matrix = mw.inverted() @ r @ mw @ pb.matrix
            bpy.context.view_layer.update()
        self.rot(f"hand_{side}", axis, deg)


# ---------------------------------------------------------------------------------------------------------------
def arms_down(r):
    for s, sx in (("l", 1), ("r", -1)):
        r.aim(f"upperarm_{s}", -U + L * (0.2 * sx) + F * 0.02)
        r.aim(f"lowerarm_{s}", -U + L * (0.12 * sx) + F * 0.15)
        r.aim(f"hand_{s}", -U + L * (0.05 * sx) + F * 0.08)


def arms_fwd(r):
    """First-person hands: elbows bent 90 degrees, forearms level in front, so each hand is clear of the body."""
    for s, sx in (("l", 1), ("r", -1)):
        r.aim(f"upperarm_{s}", -U + F * 0.55 + L * (0.12 * sx))
        r.aim(f"lowerarm_{s}", F + U * 0.12 + L * (0.05 * sx))
        r.aim(f"hand_{s}", F + U * 0.05)


def hand_pose(r, s, kind):
    curls = {"fist": (85, 100, 70), "grip": (55, 65, 35), "relaxed": (15, 25, 12), "point": (85, 100, 70),
             "spread": (0, 0, 0), "phone": (40, 35, 20)}[kind]
    for dg in DIGITS[1:]:
        c = curls
        if kind == "point" and dg == "index":
            c = (0, 5, 0)
        if kind == "phone":
            c = {"index": (35, 40, 25), "middle": (50, 45, 25), "ring": (60, 50, 25), "pinky": (65, 55, 30)}[dg]
        for j, deg in zip(("01", "02", "03"), c):
            r.flex(f"{dg}_{j}_{s}", deg)
    if kind == "spread":
        for dg, deg in (("index", -14), ("middle", -3), ("ring", 8), ("pinky", 16)):
            r.spread(f"{dg}_01_{s}", deg)
    th = {"fist": (30, 25, 35), "grip": (25, 20, 25), "relaxed": (5, 8, 10), "point": (30, 25, 35),
          "spread": (-10, 0, 0), "phone": (20, 10, 15)}[kind]
    for j, deg in zip(("01", "02", "03"), th):  # the thumb folds toward the palm, then curls toward the index
        b = f"thumb_{j}_{s}"
        if j == "01":
            r.flex(b, deg)
        else:
            d = r.dir(b)
            tgt = (r.head(f"middle_01_{s}") - r.head(b)).normalized()
            r.rot(b, d.cross(tgt) if d.cross(tgt).length > 1e-4 else d.cross(r.world(b, r.axes[b]["n"])), deg)


def supinate_to(r, s, target):
    """Turn the hand about the forearm (sharing with twist bones) until the palm faces `target` as well as it can."""
    axis = r.dir(f"lowerarm_{s}")
    n = r.world(f"hand_{s}", r.axes[f"hand_{s}"]["n"])
    a, b = n - axis * n.dot(axis), target - axis * target.dot(axis)
    ang = math.degrees(a.angle(b))
    r.twist_forearm(s, ang if a.cross(b).dot(axis) > 0 else -ang)


def phone_hold(r):
    """Right hand up in front of the face, palm toward the eyes, fingers wrapped around the back of a phone, thumb
    across the screen. Left arm in the first-person rest."""
    arms_fwd(r)
    r.aim("upperarm_r", -U * 0.9 + F * 0.45 - L * 0.1)
    r.aim("lowerarm_r", U * 0.8 + F * 0.5 - L * 0.4)
    r.aim("hand_r", U * 0.85 + F * 0.25 - L * 0.25)
    eye = r.head("head") if r.has("head") else r.head("neck_01") + U * 0.1
    supinate_to(r, "r", (eye - r.head("hand_r")).normalized())
    for dg, c in (("index", (55, 50, 25)), ("middle", (60, 55, 25)), ("ring", (65, 55, 25)), ("pinky", (70, 55, 30))):
        for j, deg in zip(("01", "02", "03"), c):
            r.flex(f"{dg}_{j}_r", deg)
    r.flex("thumb_01_r", 25)
    r.spread("thumb_02_r", 10)


def wrist(r, s, deg):
    n = r.world(f"hand_{s}", r.axes[f"hand_{s}"]["n"])
    d = r.dir(f"hand_{s}")
    r.rot(f"hand_{s}", d.cross(n), deg)


def legs(r, thigh, calf, foot=None):
    for s, sx in (("l", 1), ("r", -1)):
        r.aim(f"thigh_{s}", Vector((thigh[0] * sx, thigh[1], thigh[2])))
        r.aim(f"calf_{s}", Vector((calf[0] * sx, calf[1], calf[2])))
        if foot:
            r.aim(f"foot_{s}", Vector((foot[0] * sx, foot[1], foot[2])))


def spine_twist(r, deg):
    ch = r.spine_chain()
    for b in ch:
        r.rot(b, U, deg / len(ch))


def bend(r, deg):
    ch = r.spine_chain()
    for b in ch:
        r.rot(b, L, -deg / len(ch))


POSES = {
    "rest": lambda r: None,
    "fp_open": lambda r: arms_fwd(r),
    "elbow_flex": lambda r: (arms_down(r), [r.aim(f"lowerarm_{s}", F * 0.35 + U + L * (0.1 if s == "l" else -0.1)) for s in "lr"],
                             [r.aim(f"hand_{s}", F * 0.35 + U) for s in "lr"]),
    "arm_raise": lambda r: [(r.aim(f"upperarm_{s}", U + L * (0.15 if s == "l" else -0.15)), r.aim(f"lowerarm_{s}", U + L * (0.08 if s == "l" else -0.08)),
                             r.aim(f"hand_{s}", U)) for s in "lr"],
    "reach_fwd": lambda r: [(r.aim(f"upperarm_{s}", F + L * (0.15 if s == "l" else -0.15) + U * 0.15), r.aim(f"lowerarm_{s}", F + U * 0.1),
                             r.aim(f"hand_{s}", F + U * 0.05), hand_pose(r, s, "relaxed")) for s in "lr"],
    "sit": lambda r: (arms_down(r), legs(r, (0.12, -1, -0.04), (0.04, -0.12, -1), (0.0, -1, -0.35))),
    "crouch": lambda r: (arms_down(r), bend(r, 25), legs(r, (0.2, -1, 0.35), (0.05, 0.7, -1), (0.0, -1, -0.2))),
    "spine_twist": lambda r: (arms_down(r), spine_twist(r, 45)),
    "wrist_twist": lambda r: (arms_fwd(r), r.twist_forearm("l", 85), r.twist_forearm("r", -85)),
    "wrist_flex": lambda r: (arms_fwd(r), wrist(r, "l", 70), wrist(r, "r", -60)),
    "fist": lambda r: (arms_fwd(r), hand_pose(r, "l", "fist"), hand_pose(r, "r", "fist")),
    "grip": lambda r: (arms_fwd(r), hand_pose(r, "l", "grip"), hand_pose(r, "r", "grip")),
    "point": lambda r: (arms_fwd(r), hand_pose(r, "l", "point"), hand_pose(r, "r", "point")),
    "spread": lambda r: (arms_fwd(r), hand_pose(r, "l", "spread"), hand_pose(r, "r", "spread")),
    "relaxed": lambda r: (arms_fwd(r), hand_pose(r, "l", "relaxed"), hand_pose(r, "r", "relaxed")),
    "phone": phone_hold,
}
POSES = {k: v for k, v in POSES.items() if k in A.get("poses", ",".join(POSES)).split(",")}

# shots: (focus bone(s), view dir from focus, distance in body heights)
SHOTS = {
    "full": (("pelvis",), Vector((0.55, -1, 0.15)), 0.75),
    "elbow": (("lowerarm_l",), Vector((1, -0.6, 0.1)), 0.22),
    "shoulder": (("upperarm_l",), Vector((0.9, -0.9, 0.4)), 0.28),
    "wrist": (("hand_l",), Vector((1, -0.4, 0.1)), 0.15),
    "hand_back": (("middle_01_l",), "back", 0.085),
    "hand_palm": (("middle_01_l",), "palm", 0.085),
    "hand_r": (("middle_01_r",), "palm", 0.1),
    "phone_fp": (("middle_01_r",), "fp", 0.1),
    "phone_out": (("middle_01_r",), "back", 0.1),
    "phone_side": (("middle_01_r",), "side", 0.1),
    "hips": (("thigh_l",), Vector((1, -0.9, 0.1)), 0.42),
    "knee": (("calf_l",), Vector((1, -0.3, 0.1)), 0.22),
    "torso": (("spine_02",), Vector((0.3, -1, 0.15)), 0.55),
}
PLAN = {
    "rest": ("full",), "fp_open": ("hand_back", "hand_palm"), "elbow_flex": ("full", "elbow"), "arm_raise": ("full", "shoulder"),
    "reach_fwd": ("full", "shoulder", "hand_back"), "sit": ("full", "hips", "knee"), "crouch": ("full", "hips", "knee"),
    "spine_twist": ("full", "torso"), "wrist_twist": ("wrist", "hand_back"), "wrist_flex": ("wrist",),
    "fist": ("hand_back", "hand_palm"), "grip": ("hand_back", "hand_palm"), "point": ("hand_back", "hand_palm"),
    "spread": ("hand_back",), "relaxed": ("hand_back", "hand_palm"), "phone": ("phone_fp", "phone_out", "phone_side"),
}


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x = sc.render.resolution_y = 560
    sc.render.film_transparent = False
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "SINGLE"
    sh.single_color = (0.78, 0.74, 0.70)
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = False
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.08, 0.08, 0.09)
    sc.display.render_aa = "8"
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.lens = 50
    cam.data.clip_start = 0.005
    return cam


def look(cam, eye, target):
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()


def shoot(cam, r, shot, path):
    bones, view, dist = SHOTS[shot]
    tgt = sum((r.head(b) for b in bones), Vector()) / len(bones)
    height = 1.8
    if shot.startswith("phone"):
        s = "r"
        tgt = (r.head("middle_01_r") + r.head("middle_02_r") + r.head("hand_r")) / 3
        n = r.world("hand_r", r.axes["hand_r"]["n"])
        k = r.world("hand_r", r.axes["hand_r"]["k"])
        eye_pos = r.head("head") if r.has("head") else r.head("neck_01") + U * 0.1
        view = {"fp": (eye_pos - tgt), "back": -n - F * 0.3, "side": k - n * 0.4}[view]
    elif shot.startswith("hand"):
        s = "r" if shot == "hand_r" else "l"
        tgt = (r.head(f"middle_01_{s}") + r.head(f"middle_02_{s}") + r.head(f"index_01_{s}") + r.head(f"pinky_01_{s}")) / 4
        n = r.world(f"hand_{s}", r.axes[f"hand_{s}"]["n"])
        view = (n if view == "palm" else -n) - r.dir(f"hand_{s}") * 0.35 + L * (0.25 if s == "l" else -0.25) + U * 0.2
    eye = tgt + view.normalized() * dist * height * 2.0
    look(cam, eye, tgt)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# metrics -----------------------------------------------------------------------------------------------------------
def evaluated(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    co = [obj.matrix_world @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return co, polys


def labels(r):
    """Dominant deform bone per vertex, and per-bone weights."""
    me, names = r.body.data, {g.index: g.name for g in r.body.vertex_groups}
    dom, wts = [], []
    for v in me.vertices:
        w = {names[g.group]: g.weight for g in v.groups if g.weight > 1e-4}
        wts.append(w)
        dom.append(max(w, key=w.get) if w else "")
    return dom, wts


def digit(b):
    p = b.split("_")[0]
    return p if p in DIGITS else ("palm" if b.startswith("hand") or "metacarpal" in b else None)


def finger_xpen(r, co, polys, dom, side):
    """Face pairs from DIFFERENT digits (or digit vs palm) of one hand that intersect each other."""
    lab = []
    for p in polys:
        ds = [digit(dom[i]) if dom[i].endswith("_" + side) else None for i in p]
        lab.append(max(set(ds), key=ds.count))
    idx = [i for i, l in enumerate(lab) if l]
    if not idx:
        return 0
    tree = BVHTree.FromPolygons(co, [polys[i] for i in idx], all_triangles=False, epsilon=0.0)
    n = 0
    for a, b in tree.overlap(tree):
        pa, pb = polys[idx[a]], polys[idx[b]]
        if a < b and lab[idx[a]] != lab[idx[b]] and not set(pa) & set(pb):
            n += 1
    return n


def self_xpen(co, polys, sel):
    """Intersecting face pairs (not sharing a vertex) among faces touching `sel` vertices."""
    idx = [i for i, p in enumerate(polys) if any(v in sel for v in p)]
    if not idx:
        return 0
    tree = BVHTree.FromPolygons(co, [polys[i] for i in idx], all_triangles=False, epsilon=0.0)
    return sum(1 for a, b in tree.overlap(tree) if a < b and not set(polys[idx[a]]) & set(polys[idx[b]]))


def ring_area(co, ring, axis):
    """Area of the convex hull of the ring's vertices projected on the plane perpendicular to `axis`."""
    if len(ring) < 4:
        return 0.0
    axis = axis.normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    pts = sorted({(round((co[i]).dot(u), 6), round((co[i]).dot(v), 6)) for i in ring})

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    return abs(sum(hull[i][0] * hull[i - 1][1] - hull[i - 1][0] * hull[i][1] for i in range(len(hull)))) / 2


def ring_of(wts, a_bones, b_bones):
    """Vertices on the seam between two weight regions (both sides carry at least 25%)."""
    out = []
    for i, w in enumerate(wts):
        wa = sum(w.get(b, 0) for b in a_bones)
        wb = sum(w.get(b, 0) for b in b_bones)
        if wa >= 0.25 and wb >= 0.25:
            out.append(i)
    return out


def edge_stretch(co0, co, polys, sel):
    worst, bad = 1.0, 0
    seen = set()
    for p in polys:
        if not any(v in sel for v in p):
            continue
        for a, b in zip(p, p[1:] + p[:1]):
            e = (min(a, b), max(a, b))
            if e in seen:
                continue
            seen.add(e)
            l0 = (co0[a] - co0[b]).length
            if l0 < 1e-7:
                continue
            k = (co[a] - co[b]).length / l0
            worst = max(worst, k, 1 / max(k, 1e-6))
            if k > 1.6 or k < 0.45:
                bad += 1
    return round(worst, 2), bad


def metrics(r, pose, co0, co, polys, dom, wts):
    m = {}
    hand = {i for i, d in enumerate(dom) if digit(d) and d.endswith("_l")}
    m["finger_xpen_l"] = finger_xpen(r, co, polys, dom, "l")
    m["finger_xpen_r"] = finger_xpen(r, co, polys, dom, "r")
    m["hand_stretch_worst"], m["hand_edges_over_limit"] = edge_stretch(co0, co, polys, hand)
    fa = ["lowerarm_l"] + r.twist_bones("lowerarm", "l")
    wring = ring_of(wts, fa, ["hand_l"])
    eaxis0 = r.rest_head("hand_l") - r.rest_head("lowerarm_l")
    eaxis = r.head("hand_l") - r.head("lowerarm_l")
    a0, a1 = ring_area(co0, wring, eaxis0), ring_area(co, wring, eaxis)
    m["wrist_area_ratio"] = round(a1 / a0, 3) if a0 else None
    ua = ["upperarm_l"] + r.twist_bones("upperarm", "l")
    elb = ring_of(wts, ua, fa)
    m["elbow_xpen"] = self_xpen(co, polys, set(elb))
    m["elbow_stretch_worst"], m["elbow_edges_over_limit"] = edge_stretch(co0, co, polys, set(elb))
    kn = ring_of(wts, ["thigh_l"] + r.twist_bones("thigh", "l"), ["calf_l"] + r.twist_bones("calf", "l"))
    m["knee_xpen"] = self_xpen(co, polys, set(kn))
    m["knee_stretch_worst"], _ = edge_stretch(co0, co, polys, set(kn))
    hp = ring_of(wts, ["pelvis"], ["thigh_l"] + r.twist_bones("thigh", "l"))
    m["hip_stretch_worst"], m["hip_edges_over_limit"] = edge_stretch(co0, co, polys, set(hp))
    sh = ring_of(wts, ["clavicle_l"] + r.spine_chain(), ua)
    m["shoulder_stretch_worst"], m["shoulder_edges_over_limit"] = edge_stretch(co0, co, polys, set(sh))
    return m


def static_weights(r):
    """Pose-independent skin facts."""
    dom, wts = labels(r)
    cross = 0
    for w in wts:
        dw = {}
        for b, x in w.items():
            d = digit(b)
            if d and d != "palm":
                dw[d] = dw.get(d, 0) + x
        s = sorted(dw.values(), reverse=True)
        if s and s[0] > 0.25 and sum(s[1:]) > 0.12:
            cross += 1
    return {"verts": len(wts), "max_influences": max(len(w) for w in wts), "cross_digit_verts_over_12pct": cross,
            "bones": len(r.names), "twist_bones": sorted(b for b in r.names if "twist" in b),
            "metacarpals": sorted(b for b in r.names if "metacarpal" in b)}


def main():
    wipe()
    cam = setup_render()
    rigs = []
    if "teen" in WHO:
        rigs.append(Rig("teen", TEEN, GARMENTS))
    if "manny" in WHO:
        rigs.append(Rig("manny", MANNY))
    for i, r in enumerate(rigs):  # side by side, never in each other's shot (renders hide the other rig)
        r.ob.location.x += i * 3.0
    bpy.context.view_layer.update()
    for r in rigs:
        r.rest = {b.name: r.ob.matrix_world @ b.matrix_local for b in r.ob.data.bones}
    report = {"teen_fbx": TEEN, "garments": GARMENTS, "static": {}, "poses": {}}
    for r in rigs:
        report["static"][r.tag] = static_weights(r)
    for r in rigs:
        others = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith(r.tag)]
        for o in others:
            o.hide_render = True
        mine = [r.body] + r.garments
        for o in mine:
            o.hide_render = False
        dom, wts = labels(r)
        r.reset()
        co0, polys = evaluated(r.body)
        for pose, fn in POSES.items():
            r.reset()
            fn(r)
            bpy.context.view_layer.update()
            co, _ = evaluated(r.body)
            report["poses"].setdefault(pose, {})[r.tag] = metrics(r, pose, co0, co, polys, dom, wts)
            for shot in PLAN[pose]:
                clothed = shot in ("full", "shoulder", "hips", "torso", "elbow", "knee")
                for g in r.garments:
                    g.hide_render = not clothed
                if r.masked:  # clothed shots show what the game shows: covered skin hidden
                    r.masked.hide_render, r.body.hide_render = not clothed, clothed
                shoot(cam, r, shot, os.path.join(OUT, f"{pose}_{shot}_{r.tag}.png"))
                if r.garments and clothed:  # skin view of the same shot, garments off
                    for g in r.garments:
                        g.hide_render = True
                    r.masked.hide_render, r.body.hide_render = True, False
                    shoot(cam, r, shot, os.path.join(OUT, f"{pose}_{shot}_{r.tag}skin.png"))
            print("pose", pose, r.tag, report["poses"][pose][r.tag])
        for o in others:
            o.hide_render = False
    with open(os.path.join(OUT, "metrics.json"), "w") as f:
        json.dump(report, f, indent=1)
    print("wrote", os.path.join(OUT, "metrics.json"))


main()
