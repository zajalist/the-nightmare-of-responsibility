"""Blender twin for hand interactions (rig lane's tool; anim owns the poses). Import it from a script run with
Tools/MPFB/run_blender.ps1, or run it directly for the self-check:
  pwsh -File Tools/MPFB/run_blender.ps1 Tools/Rig/hand_twin.py selftest=1

Conventions (verified on the Teen: UE hand_l (51.25, 22.14, 116.14) cm = Blender (0.512, -0.221, 1.161) m):
- Blender world = UE world mirrored in Y, in metres: Blender (x, y, z) = UE (x, -y, z) / 100.
- Quaternions convert by the same mirror: UE (x, y, z, w) <-> Blender (-x, y, -z, w).
- Object meshes keep their UE static-mesh frame: Blender's glTF importer and UE Interchange both map glTF (x, y, z),
  and with the mirror above they agree. So an object placed with its UE transform lands where the game has it.
- Bone poses go through REST-RELATIVE world deltas, never bone-local axes, because UE and Blender bone frames differ:
  UE component rotation U -> D = U * U_rest^-1 -> mirror -> applied to the Blender rest bone. export_ue_local() is the
  inverse, and gives the UE local quaternions anim bakes.

API:
  rig, teen = load_teen()                                      rom_audit.Rig of SK_Teen_Body (+ polo by default)
  obj = load_object(name)  /  place(obj, ue_loc, ue_quat, ue_scale)   objects from OBJECTS, at their UE transform
  pose_from_ue_local(rig, {bone: (x, y, z, w)})                anim's UE local rotations (missing bones stay at rest)
  export_ue_local(rig) -> {bone: (x, y, z, w)}                 back to UE local rotations
  ue_point(rig, bone, ue_offset_cm) -> Blender Vector           e.g. the eye: ue_point(rig, 'head', EYE_HEAD)
  report = check(rig, [obj, ...], side='l', min_gap_mm=1.0)    mesh-level clearance and contact per digit
  phone_report(rig, phone, eye) -> thumb pad to glass, fingertips past the right edge, screen unoccluded fraction
  render_fp(eye, target, path) / render_side(target, from_dir, path, dist_m)
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(__file__))

REF_JSON = "P:/FoA/Saved/AnimShots/teen_ref_pose.json"
EYE_HEAD = (0.0, -3.5306, 11.7683)  # FollowCamera on the head socket, UE head-local cm (anim's bake_phone_grip.py)
GAME_FOV = 80.0                     # Tools/Unreal/player/set_camera.py, horizontal
BODY_SCALE = 170.0 / 180.0          # BP_FoAPlayer shows the Body at 170/180 while held objects stay life size (anim, 11-10):
                                    # the twin keeps the body unscaled, so held objects attach at 1/BODY_SCALE and every
                                    # body-space distance is reported in game millimetres (x BODY_SCALE)
L = "P:/FoA-Assets/lux3d/"
PH = "P:/FoA-Assets/polyhaven/models/"
OBJECTS = {  # name: (source, note). Mesh frames are the UE static-mesh frames (see the module docstring).
    "phone": (L + "smartphone_v2/SM_Phone.glb", "SM_Phone: +X up the screen, -Y screen right, -Z out of the glass; "
              "14.7 x 7.1 x 0.98 cm; glass z -0.49; sockets Screen (0,0,-0.51), Thumb_Rest (-2.6,-1.4,-0.51), Palm_L (-1.5,0,0.36)"),
    "key": (L + "door_key/textured.glb", "SM_Lux3D_DoorKey (BP_Door ToolKeyMesh); in-game scale comes from ToolKeyTransform"),
    "lock_plate": (L + "door_lock_plate/textured.glb", "SM_DoorLockPlate; on the door at scale (0.42, 0.20, 0.349), "
                   "door-local centre (-, -84, 87.3) (fit_door_lock.py)"),
    "lock_screw": (L + "lock_screw/textured.glb", "SM_DoorLockScrew; scale 0.42 on the door"),
    "door": (L + "bedroom_door/textured.glb", "the bedroom door, with its handle/knob"),
    "hanger": (L + "wire_hanger/textured.glb", "the wire hanger"),
    "screwdriver": (PH + "screwdriver/screwdriver_1k.gltf", "Poly Haven screwdriver, 27 x 27 x 209 mm"),
    "commode": (PH + "GothicCommode_01/GothicCommode_01_1k.gltf", "the chest of drawers; drawers are separate nodes"),
}
DIGITS = ("thumb", "index", "middle", "ring", "pinky")


# ---- conversions --------------------------------------------------------------------------------------------------
def ue_to_bl_loc(v):
    return Vector((v[0], -v[1], v[2])) / 100.0


def bl_to_ue_loc(v):
    return (v.x * 100.0, -v.y * 100.0, v.z * 100.0)


def ue_to_bl_quat(q):
    """UE (x, y, z, w) -> Blender Quaternion (w, x, y, z), mirrored in Y."""
    return Quaternion((q[3], -q[0], q[1], -q[2]))


def bl_to_ue_quat(q):
    return (-q.x, q.y, -q.z, q.w)


def _qmul(a, b):  # UE-style tuples (x, y, z, w)
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def _qinv(a):
    return (-a[0], -a[1], -a[2], a[3])


# ---- character ----------------------------------------------------------------------------------------------------
def load_teen(garments=("P:/FoA-Assets/character/mpfb/export/teen_polo_drape/SK_Teen_Polo.fbx",)):
    """The live Teen body (teen_rigfix FBX, what UE imported) on a fresh scene."""
    sys.argv += [] if any(a.startswith("out=") for a in sys.argv) else ["out=P:/FoA/Saved/RigShots/audit/_diag"]
    sys.argv += ["who=none", "poses=rest"]
    import rom_audit as R
    R.wipe()
    cam = R.setup_render()
    rig = R.Rig("teen", "P:/FoA-Assets/character/mpfb/export/teen_rigfix/SK_Teen_Body.fbx", list(garments))
    rig.cam = cam
    ref = json.load(open(REF_JSON))
    names = ref["names"]
    rig.ue_rest = {n: tuple(ref["world"][n][1]) for n in names}  # teen_ref_pose.json: {"names", "local", "world"} by name
    rig.ue_names = names
    rig.bl_rest_rot = {b.name: (rig.ob.matrix_world @ b.matrix_local).to_quaternion() for b in rig.ob.data.bones}
    return rig, R


def _order(rig):
    out = []

    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in rig.ob.data.bones:
        if b.parent is None:
            walk(b)
    return out


def pose_from_ue_local(rig, ue_local, translations=None):
    """Set the Blender pose from UE LOCAL bone rotations {bone: (x, y, z, w)}; bones not given keep their UE rest local.
    Optional captured local translations preserve root motion and pelvis offsets during PIE replay."""
    ref = json.load(open(REF_JSON))
    loc_rest = {n: tuple(ref["local"][n][1]) for n in ref["names"]}
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.ob.data.bones}
    comp = {}
    for name in _order(rig):
        q_local = tuple(ue_local.get(name, loc_rest.get(name, (0, 0, 0, 1))))
        p = parent[name]
        comp[name] = _qmul(comp[p], q_local) if p in comp else q_local
    mw = rig.ob.matrix_world
    for name in _order(rig):
        if name not in rig.ue_rest:
            continue
        d_ue = _qmul(comp[name], _qinv(rig.ue_rest[name]))
        d_bl = ue_to_bl_quat(d_ue)
        pb = rig.ob.pose.bones[name]
        head = (mw @ pb.matrix).to_translation()
        if translations is not None and name in translations:
            delta = Vector(translations[name]) - Vector(ref["local"][name][0])
            pq = comp.get(parent[name], (0, 0, 0, 1))
            head += ue_to_bl_quat(pq) @ ue_to_bl_loc(delta)
        world = Matrix.LocRotScale(head, d_bl @ rig.bl_rest_rot[name], mw.to_scale())  # the FBX rig carries scale 0.01
        pb.matrix = mw.inverted() @ world
        bpy.context.view_layer.update()


def export_ue_local(rig):
    """The current Blender pose as UE LOCAL rotations {bone: (x, y, z, w)} (inverse of pose_from_ue_local)."""
    mw = rig.ob.matrix_world
    comp = {}
    for name in _order(rig):
        if name not in rig.ue_rest:
            continue
        cur = (mw @ rig.ob.pose.bones[name].matrix).to_quaternion()
        d_bl = cur @ rig.bl_rest_rot[name].inverted()
        comp[name] = _qmul(bl_to_ue_quat(d_bl), rig.ue_rest[name])
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.ob.data.bones}
    return {n: (_qmul(_qinv(comp[parent[n]]), q) if parent[n] in comp else q) for n, q in comp.items()}


def ue_point(rig, bone, ue_offset):
    """A point fixed to a bone, given in that bone's UE local frame (cm), in Blender world coordinates."""
    mw = rig.ob.matrix_world
    pb = rig.ob.pose.bones[bone]
    cur = (mw @ pb.matrix).to_quaternion()
    d_bl = cur @ rig.bl_rest_rot[bone].inverted()
    u_now = _qmul(bl_to_ue_quat(d_bl), rig.ue_rest[bone])
    # rotate the UE-local offset into UE world with u_now, then mirror into Blender
    x, y, z, w = u_now
    qv = _qmul(_qmul(u_now, (ue_offset[0], ue_offset[1], ue_offset[2], 0.0)), _qinv(u_now))
    return (mw @ pb.matrix).to_translation() + Vector((qv[0], -qv[1], qv[2])) / 100.0


# ---- objects ------------------------------------------------------------------------------------------------------
def load_object(name):
    """Import one interaction object; returns an empty "<name>_frame" (the UE actor frame) parenting its meshes."""
    path, _ = OBJECTS[name]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    frame = bpy.data.objects.new(name + "_frame", None)
    bpy.context.scene.collection.objects.link(frame)
    for o in new:
        if o.parent is None:
            o.parent = frame
    frame["foa_object"] = name
    return frame


def place(frame, ue_loc=(0, 0, 0), ue_quat=(0, 0, 0, 1), ue_scale=(1, 1, 1)):
    """Put an object at its UE world transform (cm, quaternion x y z w, scale)."""
    frame.matrix_world = Matrix.LocRotScale(ue_to_bl_loc(ue_loc), ue_to_bl_quat(ue_quat), Vector(ue_scale))
    bpy.context.view_layer.update()


def ue_bone(rig, bone):
    """The bone's current UE component-space transform: (location cm, rotation (x, y, z, w))."""
    mw = rig.ob.matrix_world
    m = mw @ rig.ob.pose.bones[bone].matrix
    d_bl = m.to_quaternion() @ rig.bl_rest_rot[bone].inverted()
    return bl_to_ue_loc(m.to_translation()), _qmul(bl_to_ue_quat(d_bl), rig.ue_rest[bone])


def attach(frame, rig, bone, ue_loc, ue_quat, scale=1.0):
    """Put an object at a UE transform RELATIVE to a bone (what BP_FoAPlayer's attach offsets are), e.g. the phone on
    hand_l with phone_grip_solution.json's out.attach."""
    bl, bq = ue_bone(rig, bone)
    v = _qmul(_qmul(bq, (ue_loc[0], ue_loc[1], ue_loc[2], 0.0)), _qinv(bq))
    place(frame, (bl[0] + v[0], bl[1] + v[1], bl[2] + v[2]), _qmul(bq, tuple(ue_quat)), (scale, scale, scale))


def meshes_of(frame):
    return [o for o in frame.children_recursive if o.type == "MESH"]


def _tree(frames):
    co, polys = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    for f in frames:
        for o in meshes_of(f):
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            base = len(co)
            co += [o.matrix_world @ v.co for v in me.vertices]
            polys += [tuple(base + i for i in p.vertices) for p in me.polygons]
            ev.to_mesh_clear()
    return BVHTree.FromPolygons(co, polys), co


def _inside(tree, p):
    """Behind the nearest face = inside. (Ray parity misfires on the Lux3D scans: separate screen quad, open shells.)"""
    loc, nrm, idx, dist = tree.find_nearest(p)
    return loc is not None and (p - loc).dot(nrm) < 0


def regions(rig, side="l"):
    """Named skin regions of one hand, as vertex index sets:
      <bone>                  every vertex dominated by that bone, e.g. index_02_l -> "index_02"
      <digit>_pad             distal phalanx, palmar half (the fixed rig curls about local X toward local +Z)
      <bone>_radial / _ulnar  the thumb side / little-finger side of a phalanx
      palm                    hand-dominated vertices on the palmar side"""
    import rom_audit as R
    dom, _ = R.labels(rig)
    co, _ = R.evaluated(rig.body)
    mw = rig.ob.matrix_world
    out = {}
    thumb = (mw @ rig.ob.pose.bones[f"thumb_01_{side}"].matrix).to_translation()
    n_palm = rig.world(f"hand_{side}", rig.axes[f"hand_{side}"]["n"])
    for i, d in enumerate(dom):
        if not d.endswith("_" + side) or not (d.startswith("hand") or d.split("_")[0] in DIGITS):
            continue
        base = d[:-2]
        out.setdefault(base, set()).add(i)
        m = mw @ rig.ob.pose.bones[d].matrix
        rel = co[i] - m.to_translation()
        x, z = m.to_3x3().normalized().col[0], m.to_3x3().normalized().col[2]
        if d.startswith("hand"):
            if rel.dot(n_palm) > 0:
                out.setdefault("palm", set()).add(i)
            continue
        dig, seg = base.split("_")
        if seg == "03" and rel.dot(z) > 0:
            out.setdefault(f"{dig}_pad", set()).add(i)
        if dig != "thumb":
            radial = 1 if (thumb - m.to_translation()).dot(x) > 0 else -1
            out.setdefault(f"{base}_{'radial' if rel.dot(x) * radial > 0 else 'ulnar'}", set()).add(i)
    return out


def check(rig, frames, side="l", min_gap_mm=1.0, contact_mm=3.0, contacts=None):
    """Every thumb/finger/palm skin vertex of one hand against the objects' real meshes: signed distance (mm; negative =
    inside), minimum per digit, how many violate min_gap_mm, and how many touch (within contact_mm).
    contacts = {region: band_mm} declares expected contacts (regions(): e.g. {"thumb_pad": 3, "index_02_radial": 3});
    each passes when its closest vertex lies in [min_gap_mm, band_mm]. frames: one object frame or a list."""
    import rom_audit as R
    frames = frames if isinstance(frames, (list, tuple)) else [frames]
    tree, _ = _tree(frames)
    dom, _ = R.labels(rig)
    co, _ = R.evaluated(rig.body)
    rep = {"side": side, "min_gap_mm": min_gap_mm, "digits": {}}
    for i, d in enumerate(dom):
        if not d.endswith("_" + side):
            continue
        digit = d.split("_")[0] if d.split("_")[0] in DIGITS else ("palm" if d.startswith("hand") else None)
        if not digit:
            continue
        loc, nrm, idx, dist = tree.find_nearest(co[i])
        if loc is None:
            continue
        signed = -dist if _inside(tree, co[i]) else dist
        mm = signed * 1000.0 * BODY_SCALE  # game millimetres
        r = rep["digits"].setdefault(digit, {"min_mm": 1e9, "violations": 0, "contacts": 0, "verts": 0})
        r["verts"] += 1
        r["min_mm"] = min(r["min_mm"], round(mm, 2))
        r["violations"] += int(mm < min_gap_mm)
        r["contacts"] += int(mm < contact_mm)
    rep["contacts"] = {}
    if contacts:
        reg = regions(rig, side)
        for name, band in contacts.items():
            idx = reg.get(name, set())
            best = 1e9
            for i in idx:
                loc, nrm, _, dist = tree.find_nearest(co[i])
                if loc is not None:
                    best = min(best, (-dist if _inside(tree, co[i]) else dist) * 1000.0 * BODY_SCALE)
            rep["contacts"][name] = {"closest_mm": round(best, 2), "band_mm": [min_gap_mm, band], "verts": len(idx),
                                     "pass": min_gap_mm <= best <= band}
    rep["pass"] = all(r["violations"] == 0 for r in rep["digits"].values()) and all(c["pass"] for c in rep["contacts"].values())
    return rep


def load_phone():
    """Alias anim asked for: the SM_Phone frame (UE mesh frame, sockets in OBJECTS['phone'])."""
    return load_object("phone")


def phone_report(rig, phone, eye, side="l"):
    """SM_Phone specifics in its own frame (cm): thumb pad height above the glass and whether it is over the glass,
    fingertips past the screen-right edge, the fraction of the screen visible from the eye, and the box rule (every
    thumb/finger vertex at least 1 mm outside the 14.7 x 7.1 x 0.98 cm box)."""
    import rom_audit as R
    inv = phone.matrix_world.inverted()
    dom, _ = R.labels(rig)
    co, _ = R.evaluated(rig.body)
    hx, hy, hz = 7.35, 3.55, 0.49

    def local_cm(p):
        q = inv @ p
        return Vector((q.x * 100.0, -q.y * 100.0, q.z * 100.0))  # back to the UE mesh frame (cm)

    def box_sdf(q):
        dx, dy, dz = abs(q.x) - hx, abs(q.y) - hy, abs(q.z) - hz
        out = Vector((max(dx, 0), max(dy, 0), max(dz, 0))).length
        return out + min(max(dx, dy, dz), 0.0)
    box_min, box_viol, pad = 1e9, 0, None
    tips = {}
    for i, d in enumerate(dom):
        if not d.endswith("_" + side) or d.split("_")[0] not in DIGITS:
            continue
        q = local_cm(co[i])
        s = box_sdf(q) * 10.0  # mm
        box_min = min(box_min, s)
        box_viol += int(s < 1.0)
        if d == f"thumb_03_{side}" and q.z < 0:  # glass side
            h = (-hz - q.z) * 10.0  # mm above the glass (glass at z = -0.49, out of the glass is -z)
            if pad is None or h < pad[0]:
                pad = (round(h, 2), abs(q.x) < hx - 0.4 and abs(q.y) < hy - 0.4)
        if d.split("_")[1] == "03":
            f = d.split("_")[0]
            tips[f] = min(tips.get(f, 1e9), q.y)  # most screen-right (screen right is -Y)
    past = [f for f, y in tips.items() if f != "thumb" and y < -hy]
    btree = BVHTree.FromPolygons(co, [tuple(p.vertices) for p in rig.body.data.polygons])
    seen = total = 0
    for ix in range(-6, 7):
        for iy in range(-3, 4):
            p_local = Vector((ix * 1.0, iy * 0.9, -0.51))
            p = phone.matrix_world @ Vector((p_local.x / 100.0, -p_local.y / 100.0, p_local.z / 100.0))
            d = (p - eye)
            hit = btree.ray_cast(eye, d.normalized(), d.length - 1e-4)
            total += 1
            seen += int(hit[0] is None)
    return {"box_min_mm": round(box_min, 2), "box_violations": box_viol,
            "thumb_pad_above_glass_mm": pad[0] if pad else None, "thumb_pad_over_glass": pad[1] if pad else None,
            "fingertips_past_right_edge": past, "screen_visible": round(seen / total, 3),
            "pass": box_viol == 0 and pad is not None and pad[0] <= 3.0 and pad[1]}


# ---- renders ------------------------------------------------------------------------------------------------------
def _camera(rig):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    cam = rig.cam
    cam.data.sensor_fit = "HORIZONTAL"
    return cam


def render_fp(rig, eye, target, path, fov_deg=GAME_FOV):
    """The player's view: game horizontal FOV, 16:9, from `eye` looking at `target` (a Blender world point, or an object
    frame: then its origin)."""
    target = target.matrix_world.to_translation() if hasattr(target, "matrix_world") else target
    cam = _camera(rig)
    cam.data.angle = math.radians(fov_deg)
    cam.data.clip_start = 0.02
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def render_side(rig, target, from_dir, path, dist_m=0.35, fov_deg=35.0):
    cam = _camera(rig)
    cam.data.angle = math.radians(fov_deg)
    eye = target + from_dir.normalized() * dist_m
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _selftest():
    """Conversions round-trip; a rest-pose export reproduces the UE rest locals; the phone loads in its frame."""
    q = (0.1, -0.2, 0.3, math.sqrt(1 - 0.14))
    b = bl_to_ue_quat(ue_to_bl_quat(q))
    assert max(abs(x - y) for x, y in zip(q, b)) < 1e-6, b  # mathutils is float32
    rig, R = load_teen(garments=())
    rig.reset()
    ref = json.load(open(REF_JSON))
    loc_rest = {n: ref["local"][n][1] for n in ref["names"]}
    ex = export_ue_local(rig)
    worst = max(min(abs(sum(a * c for a, c in zip(ex[n], loc_rest[n]))), 1.0) for n in ex if n in loc_rest)
    err = max(math.degrees(2 * math.acos(min(abs(sum(a * c for a, c in zip(ex[n], loc_rest[n]))), 1.0))) for n in ex if n in loc_rest)
    pose_from_ue_local(rig, loc_rest)  # setting the rest locals must leave every bone where it was
    hand = rig.head("hand_l")
    ue_hand = ref["world"]["hand_l"][0]
    gap = (ue_to_bl_loc(ue_hand) - hand).length * 100
    phone = load_object("phone")
    place(phone)
    dims = [round(x * 100, 2) for x in (max(c[i] for o in meshes_of(phone) for c in [o.matrix_world @ Vector(v) for v in o.bound_box]) -
                                        min(c[i] for o in meshes_of(phone) for c in [o.matrix_world @ Vector(v) for v in o.bound_box]) for i in range(3))]
    print("HAND_TWIN_SELFTEST rest-export max err deg", round(err, 4), "hand_l position gap cm", round(gap, 3), "phone dims cm (bl x,y,z)", dims)
    assert err < 0.5 and gap < 0.5, (err, gap)
    assert abs(dims[0] - 14.7) < 0.3 and abs(dims[1] - 7.1) < 0.3, dims  # long axis X, width Y in both frames
    print("HAND_TWIN_SELFTEST PASS", worst)


def run_phone(solution, out_dir, tag):
    """Anim's phone solution JSON ({"hold": {bone: [loc, quat, scale]}, "out": {"attach": {location, rotation}}}) ->
    clearance + phone report JSON and the first-person and side renders."""
    os.makedirs(out_dir, exist_ok=True)
    sol = json.load(open(solution))
    rig, R = load_teen()
    rig.reset()
    pose_from_ue_local(rig, {b: v[1] for b, v in sol["hold"].items()}, {b: v[0] for b, v in sol["hold"].items()})
    phone = load_object("phone")
    a = sol["out"]["attach"]
    attach(phone, rig, "hand_l", a["location"], a["rotation"], 1.0 / BODY_SCALE)  # life-size phone on the 170/180 body
    eye = ue_point(rig, "head", EYE_HEAD)
    rep = {"solution": solution, "check": check(rig, phone, "l", contacts={"thumb_pad": 3.0}),
           "phone": phone_report(rig, phone, eye), "eye_to_screen_cm": round((eye - phone.matrix_world.to_translation()).length * 100 * BODY_SCALE, 1)}
    json.dump(rep, open(os.path.join(out_dir, f"{tag}_report.json"), "w"), indent=1)
    print("PHONE_TWIN", json.dumps(rep["phone"]), json.dumps({k: v["min_mm"] for k, v in rep["check"]["digits"].items()}))
    centre = phone.matrix_world.to_translation()
    render_fp(rig, eye, centre, os.path.join(out_dir, f"{tag}_fp.png"))
    x_axis = phone.matrix_world.to_3x3().col[0].normalized()
    render_side(rig, centre, phone.matrix_world.to_3x3().col[1].normalized() + x_axis * 0.2, os.path.join(out_dir, f"{tag}_side.png"))
    return rep


if __name__ == "__main__" and "selftest=1" in sys.argv:
    _selftest()
if __name__ == "__main__" and any(a.startswith("phone=") for a in sys.argv):
    args = dict(a.split("=", 1) for a in sys.argv if "=" in a)
    run_phone(args["phone"], args.get("dir", "P:/FoA/Saved/RigShots/hands"), args.get("tag", "phone"))


def _objects_smoke():
    """Every OBJECTS entry loads; prints its size in its UE frame (cm), to compare with the game's bounds."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for name in OBJECTS:
        f = load_object(name)
        place(f)
        pts = [o.matrix_world @ Vector(v) for o in meshes_of(f) for v in o.bound_box]
        size = [round((max(p[i] for p in pts) - min(p[i] for p in pts)) * 100, 1) for i in range(3)]
        print("HAND_TWIN_OBJECT", name, "size cm (x, y, z)", size, "meshes", len(meshes_of(f)))


if __name__ == "__main__" and "objects=1" in sys.argv:
    _objects_smoke()
