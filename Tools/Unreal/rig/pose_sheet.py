"""Finger and forearm deformation sheet on the real player mesh (SK_Teen_Body with its shipped materials, the wake
polo and pants as leader-pose followers, covered skin hidden as BP_FoAPlayer hides it). Poses are set bone by bone
on a transient PoseableMesh (TMP_rig_pose*), using the measured finger convention: every phalanx curls toward the
palm about local -X (UE quaternion), spreads about local Z; the forearm twist bone takes 60% of the hand roll, as
ABP_FoA_TeenPost does at runtime (a PoseableMesh runs no post-process ABP). Each pose is shot through a first-person
eye and one close third-person view. Nothing is saved except PNGs under FOA_OUT; every actor is destroyed at the end.
  $env:FOA_AREAS='Characters'; $env:FOA_ACTORS_NEW='TMP_rig_'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/pose_sheet.py [FOA_OUT=...]"""
import math
import os
import time
from pathlib import Path

import unreal

OUT = Path(os.environ.get("FOA_OUT", "P:/FoA/Saved/RigShots/sheet"))
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "done.txt").unlink(missing_ok=True)
M = "/Game/FoA/Characters/Teen/Mesh/"
E = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
w = E.get_game_world() if os.environ.get("FOA_WORLD") == "pie" else E.get_editor_world()
assert w and (os.environ.get("FOA_WORLD") == "pie" or not E.get_game_world()), "world"
gs = unreal.get_default_object(unreal.GameplayStatics)
CS = unreal.BoneSpaces.COMPONENT_SPACE
V = unreal.Vector
ORIGIN = V(0, 0, 3000)
made = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_actor_label().startswith("TMP_rig_"):
        a.destroy_actor()


def spawn(cls, label):
    tr = unreal.Transform(location=ORIGIN)
    a = gs.call_method("BeginDeferredActorSpawnFromClass", (w, cls.static_class(), tr, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
                                                            None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a = gs.call_method("FinishSpawningActor", (a, tr, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a.set_actor_label("TMP_rig_" + label)
    made.append(a)
    return a


host = spawn(unreal.Actor, "pose")
pm = host.call_method("AddComponentByClass", (unreal.PoseableMeshComponent.static_class(), False, unreal.Transform(), False))
host.set_actor_location(ORIGIN, False, True)
pm.set_skinned_asset_and_update(unreal.load_asset(M + "SK_Teen_Body"), True)
worn = ("foa_polo_layered", "toigo_wool_pants", "joepal_crude_low_socks")
for i, n in enumerate(pm.get_material_slot_names()):
    if str(n).startswith("Skin_under_") and any(g in str(n) for g in worn):
        pm.show_material_section(i, 0, False, 0)
followers = []
for piece in ("SK_Teen_Polo", "SK_Teen_Pants"):
    fa = spawn(unreal.SkeletalMeshActor, piece)
    fa.skeletal_mesh_component.set_skeletal_mesh_asset(unreal.load_asset(M + piece))
    fa.skeletal_mesh_component.set_leader_pose_component(pm)
    followers.append(fa)
names = [str(pm.get_bone_name(i)) for i in range(pm.get_num_bones())]
REF = {b: pm.get_ref_pose_transform(pm.get_bone_index(b)).rotation for b in names}
PARENT = {b: str(pm.get_parent_bone(b)) for b in names}


def qmul(a, b):
    return unreal.Quat(a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y, a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
                       a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w, a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)


def axis_angle(ax, deg):
    s = math.sin(math.radians(deg) / 2)
    return unreal.Quat(ax[0] * s, ax[1] * s, ax[2] * s, math.cos(math.radians(deg) / 2))


def between(u, v):
    """Shortest-arc quaternion taking unit vector u to v."""
    u, v = u.normal(), v.normal()
    c = u.cross(v)
    q = unreal.Quat(c.x, c.y, c.z, 1 + u.dot(v))
    n = math.sqrt(q.x ** 2 + q.y ** 2 + q.z ** 2 + q.w ** 2) or 1
    return unreal.Quat(q.x / n, q.y / n, q.z / n, q.w / n)


BASE = {}


class _T:
    def __init__(self, t, q):
        self.translation, self.rotation = t, q


def rot(q, v):
    """Rotate vector v by unit quaternion q."""
    p = qmul(qmul(q, unreal.Quat(v.x, v.y, v.z, 0)), unreal.Quat(-q.x, -q.y, -q.z, q.w))
    return V(p.x, p.y, p.z)


# Our own forward kinematics: a PoseableMesh only refreshes its bones on a later tick, so reading them back between
# sets would see stale parents. LOCAL holds each bone's local rotation; translations stay at the reference.
TREF = {b: pm.get_ref_pose_transform(pm.get_bone_index(b)).translation for b in names}
ORDER = [b for b in names]  # bone indices are parent-before-child
LOCAL = {}


def cs(b):
    chain = []
    while b in REF:
        chain.append(b)
        b = PARENT[b]
    t, q = V(0, 0, 0), unreal.Quat(0, 0, 0, 1)
    for x in reversed(chain):
        t = t + rot(q, TREF[x])
        q = qmul(q, LOCAL[x])
    return _T(t, q)


def set_local(b, q_local):
    LOCAL[b] = q_local


def inv(q):
    return unreal.Quat(-q.x, -q.y, -q.z, q.w)


def bend(b, deg, ax=(-1, 0, 0)):
    """Rotate a bone in its own frame from the reference: curl = local -X, spread = local Z, roll = local Y."""
    set_local(b, qmul(REF[b], axis_angle(ax, deg)))


def aim(b, child, want):
    cur = cs(child).translation - cs(b).translation
    new_cs = qmul(between(cur, want), cs(b).rotation)
    parent = cs(PARENT[b]).rotation if PARENT[b] in REF else unreal.Quat(0, 0, 0, 1)
    LOCAL[b] = qmul(inv(parent), new_cs)


def reset():
    BASE.clear()
    for x in names:
        LOCAL[x] = REF[x]


def flush():
    """Push the whole pose to the PoseableMesh, parent before child, as component-space rotations."""
    for x in ORDER:
        pm.set_bone_rotation_by_name(x, cs(x).rotation.rotator(), CS)


def frame_axes():
    f = cs("ball_r").translation - cs("foot_r").translation
    f.z = 0
    f = f.normal()
    left = (cs("upperarm_l").translation - cs("upperarm_r").translation)
    left.z = 0
    return f, left.normal(), V(0, 0, 1)


F, L, U = None, None, None


def arms_fwd(sides="lr"):
    for s in sides:
        o = L * (1 if s == "l" else -1)  # outward
        aim(f"upperarm_{s}", f"lowerarm_{s}", U * -0.9 + F * 0.6 + o * 0.12)
        aim(f"lowerarm_{s}", f"hand_{s}", F + U * 0.25 - o * 0.15)
        aim(f"hand_{s}", f"middle_01_{s}", F + U * 0.1 - o * 0.05)


BASE.clear()  # each hand's local rotation after aiming, so repeated rolls start from the aimed wrist, not the reference


def local_now(b):
    return LOCAL[b]


def roll(s, deg):
    """Forearm roll: the hand turns about its own long axis, the twist bone takes 60% (ABP_FoA_TeenPost)."""
    h = f"hand_{s}"
    BASE.setdefault(h, local_now(h))
    bend(f"lowerarm_twist_01_{s}", 0.6 * deg, (0, 1, 0))
    set_local(h, qmul(BASE[h], axis_angle((0, 1, 0), deg)))


def fingers(s, table, thumb):
    for f, angles in table.items():
        for j, deg in enumerate(angles):
            bend(f"{f}_0{j + 1}_{s}", deg)
    for j, deg in enumerate(thumb):
        bend(f"thumb_0{j + 1}_{s}", deg)


THUMB_FIT = {}  # side -> fitted angles and clearance, written to thumb_fit.json
TIP = {"thumb": 2.9, "index": 2.3, "middle": 2.4}  # distal joint to fingertip, cm (Teen hand, rig audit)


def tip(f, s):
    t = cs(f"{f}_03_{s}")
    return t.translation + rot(t.rotation, V(0, 1, 0)) * TIP[f]


def seg_dist(p1, p2, q1, q2):
    """Closest distance between segments p1p2 and q1q2 (sampled; fine at finger scale)."""
    best = 1e9
    for i in range(6):
        a = p1 + (p2 - p1) * (i / 5.0)
        for j in range(6):
            b = q1 + (q2 - q1) * (j / 5.0)
            best = min(best, (a - b).length())
    return best


def clearance(s):
    th = [cs(f"thumb_02_{s}").translation, cs(f"thumb_03_{s}").translation, tip("thumb", s)]
    out = 1e9
    for f in ("index", "middle"):
        fp = [cs(f"{f}_0{k}_{s}").translation for k in (1, 2, 3)] + [tip(f, s)]
        for a, b in zip(th, th[1:]):
            for c, d in zip(fp, fp[1:]):
                out = min(out, seg_dist(a, b, c, d))
    return out


def set_thumb(s, a, b, c, d, e=0.0):
    q = qmul(qmul(REF[f"thumb_01_{s}"], axis_angle((-1, 0, 0), a)), axis_angle((0, 0, 1), b))
    set_local(f"thumb_01_{s}", qmul(q, axis_angle((0, 1, 0), e)))  # e: roll of the thumb metacarpal (opposition)
    set_local(f"thumb_02_{s}", qmul(REF[f"thumb_02_{s}"], axis_angle((-1, 0, 0), c)))
    set_local(f"thumb_03_{s}", qmul(REF[f"thumb_03_{s}"], axis_angle((-1, 0, 0), d)))


def fit_thumb(s, gap=1.7):
    """Thumb tip resting ON the index's middle phalanx (its outer face, away from the fist's centre), never inside a
    finger: coordinate descent on thumb_01 curl/spread, thumb_02 and thumb_03 curl, with a clearance penalty."""
    i2, i3 = cs(f"index_02_{s}").translation, cs(f"index_03_{s}").translation
    centre = (cs(f"hand_{s}").translation + cs(f"index_01_{s}").translation + cs(f"pinky_01_{s}").translation) * (1 / 3.0)
    mid = (i2 + i3) * 0.5
    target = mid + (mid - centre).normal() * gap

    def cost(x):
        set_thumb(s, *x)
        return (tip("thumb", s) - target).length() + 10 * max(0.0, gap - clearance(s))
    lo, hi = [-10, -40, -20, -20, -60], [80, 40, 70, 70, 60]
    gbest, x = 1e9, None
    for start in ([30.0, 0.0, 20.0, 20.0, 0.0], [55.0, -15.0, 35.0, 25.0, 20.0], [60.0, 10.0, 45.0, 30.0, -20.0],
                  [45.0, 20.0, 25.0, 15.0, 30.0]):  # several starts: the thumb has local minima beside the index
        y0, best = list(start), cost(start)
        for step in (10, 5, 2.5, 1.25):
            improved = True
            while improved:
                improved = False
                for k in range(5):
                    for dv in (-step, step):
                        y = list(y0)
                        y[k] = min(hi[k], max(lo[k], y[k] + dv))
                        c = cost(y)
                        if c < best - 1e-4:
                            best, y0, improved = c, y, True
        if best < gbest:
            gbest, x = best, y0
    set_thumb(s, *x)
    THUMB_FIT[s] = {"thumb_01_curl": x[0], "thumb_01_spread": x[1], "thumb_02_curl": x[2], "thumb_03_curl": x[3],
                    "thumb_01_roll": x[4],
                    "tip_to_target_cm": round((tip("thumb", s) - target).length(), 2), "clearance_cm": round(clearance(s), 2)}


GRIP_THUMB = [float(v) for v in os.environ.get("FOA_THUMB", "20,1.25,32.5,70,-40").split(",")]  # curl, spread, 02, 03, roll


def fixed_thumb(s, key):
    set_thumb(s, *GRIP_THUMB)
    if key:
        THUMB_FIT[key] = {"angles": GRIP_THUMB, "clearance_cm": round(clearance(s), 2)}


def copy_thumb(src, dst):
    """Same angles on the other hand: the curl, spread and roll axes have the same sign on both hands."""
    f = THUMB_FIT[src]
    set_thumb(dst, f["thumb_01_curl"], f["thumb_01_spread"], f["thumb_02_curl"], f["thumb_03_curl"], f["thumb_01_roll"])


def all4(t):
    return {f: t for f in ("index", "middle", "ring", "pinky")}


RELAX = ({"index": (12, 20, 8), "middle": (15, 25, 10), "ring": (18, 28, 12), "pinky": (22, 30, 15)}, (5, 8, 10))
FIST = ({"index": (85, 100, 65), "middle": (88, 100, 65), "ring": (90, 100, 65), "pinky": (92, 100, 65)}, (35, 30, 40))
POINT = ({"index": (0, 0, 0), "middle": (88, 100, 65), "ring": (90, 100, 65), "pinky": (92, 100, 65)}, (30, 30, 20))
PHONE = ({"index": (50, 45, 20), "middle": (58, 50, 22), "ring": (64, 52, 24), "pinky": (70, 55, 28)}, (15, -5, 5))
TOOL = ({"index": (60, 75, 38), "middle": (66, 80, 40), "ring": (72, 82, 40), "pinky": (78, 85, 42)}, (40, 25, 30))


def splay(s):
    fingers(s, all4((0, 0, 0)), (0, 0, 0))
    mid = cs(f"middle_02_{s}").translation
    for f, deg in (("index", 15), ("ring", 10), ("pinky", 20), ("thumb", 20)):
        b = f"{f}_01_{s}"
        bend(b, deg, (0, 0, 1))
        d_plus = (cs(f"{f}_02_{s}").translation - mid).length()
        bend(b, -deg, (0, 0, 1))
        if (cs(f"{f}_02_{s}").translation - mid).length() < d_plus:  # keep whichever sign moves it away from the middle finger
            bend(b, deg, (0, 0, 1))


def phone_left():
    arms_fwd("r")
    aim("upperarm_l", "lowerarm_l", U * -0.85 + F * 0.5 + L * 0.1)
    aim("lowerarm_l", "hand_l", U * 0.75 + F * 0.55 - L * 0.35)
    aim("hand_l", "middle_01_l", U * 0.8 + F * 0.3 - L * 0.2)
    # supinate until the palm faces the eyes (roll about the hand's long axis, twist bone 60%)
    eye = cs("head").translation
    best, best_d = 0, -2
    for deg in range(-180, 181, 15):
        roll("l", deg)
        k = cs("pinky_01_l").translation - cs("index_01_l").translation
        d = cs("middle_02_l").translation - cs("middle_01_l").translation
        n = k.cross(d).normal()
        if (cs("thumb_03_l").translation - cs("middle_01_l").translation).dot(n) < 0:
            n = n * -1.0
        score = n.dot((eye - cs("hand_l").translation).normal())
        if score > best_d:
            best, best_d = deg, score
    roll("l", best)
    fingers("l", *PHONE)
    fingers("r", *RELAX)
    return "l"


POSES = [
    ("open_relaxed", lambda: (arms_fwd(), fingers("l", *RELAX), fingers("r", *RELAX)) and "r"),
    ("fist_thumb_on_index", lambda: (arms_fwd(), fingers("l", *FIST), fingers("r", *FIST), fit_thumb("r"), copy_thumb("r", "l")) and "r"),
    ("fist_thumb_grip_angles", lambda: (arms_fwd(), fingers("l", *FIST), fingers("r", *FIST), fixed_thumb("r", "fist_thumb_grip_angles"),
                                        fixed_thumb("l", None)) and "r"),
    ("screwdriver_thumb_on_index", lambda: (arms_fwd(), fingers("r", *TOOL), fingers("l", *RELAX), fit_thumb("r")) and "r"),
    ("full_fist", lambda: (arms_fwd(), fingers("l", *FIST), fingers("r", *FIST)) and "r"),
    ("phone_grip_left", phone_left),
    ("screwdriver_grip_right", lambda: (arms_fwd(), fingers("r", *TOOL), fingers("l", *RELAX)) and "r"),
    ("index_point", lambda: (arms_fwd(), fingers("r", *POINT), fingers("l", *RELAX)) and "r"),
    ("wide_splay", lambda: (arms_fwd(), splay("r"), splay("l")) and "r"),
    ("wrist_roll_plus60", lambda: (arms_fwd(), fingers("l", *RELAX), fingers("r", *RELAX), roll("r", 60), roll("l", 60)) and "r"),
    ("wrist_roll_minus60", lambda: (arms_fwd(), fingers("l", *RELAX), fingers("r", *RELAX), roll("r", -60), roll("l", -60)) and "r"),
    ("slap_elbow_right", lambda: slap_arm() and "r"),
]


def slap_arm():
    """The wake-up slap's reaching right arm: upper arm down and forward, elbow opened about 30 deg."""
    o = L * -1.0
    aim("upperarm_r", "lowerarm_r", F * 0.45 - U * 0.75 + o * 0.25)
    aim("lowerarm_r", "hand_r", F * 0.85 - U * 0.45 + o * 0.1)
    aim("hand_r", "middle_01_r", F * 0.9 - U * 0.6)
    fingers("r", *RELAX)
    return True


VIEWS = {"slap_elbow_right": ("elbow_sleeve", "elbow_nosleeve"), "fist_thumb_on_index": ("tp", "thumbside"),
         "fist_thumb_grip_angles": ("tp", "thumbside"),
         "screwdriver_thumb_on_index": ("tp", "thumbside")}
WANT = [p for p in os.environ.get("FOA_POSES", "").split(",") if p]
if WANT:
    POSES = [p for p in POSES if p[0] in WANT]
cap = spawn(unreal.SceneCapture2D, "cap")
cc = cap.capture_component2d
cc.texture_target = unreal.RenderingLibrary.create_render_target2d(w, 960, 960, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.capture_source = unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR
cc.capture_every_frame = True
cc.always_persist_rendering_state = True
cc.override_custom_near_clipping_plane = True
cc.custom_near_clipping_plane = 4.0
cc.primitive_render_mode = unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST
pp = cc.post_process_settings
pp.override_auto_exposure_method = True
pp.auto_exposure_method = unreal.AutoExposureMethod.AEM_MANUAL
pp.override_auto_exposure_apply_physical_camera_exposure = True
pp.auto_exposure_apply_physical_camera_exposure = False
pp.override_auto_exposure_bias = True
pp.auto_exposure_bias = -4.0
cc.post_process_settings = pp
cc.clear_show_only_components()
for a in [host] + followers:
    cc.show_only_actor_components(a)
lights = []
for i in range(2):
    lt = spawn(unreal.PointLight, f"light{i}")
    lc = lt.point_light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)  # a spawned static light lights nothing in PIE
    for k, v in (("intensity_units", unreal.LightUnits.CANDELAS), ("intensity", 7 if i == 0 else 2.5),
                 ("attenuation_radius", 400), ("source_radius", 25)):
        lc.set_editor_property(k, v)
    lights.append(lt)
shots = [(p, view) for p in POSES for view in VIEWS.get(p[0], ("fp", "tp"))]
S = {"i": 0, "stage": 0, "ready": time.monotonic() + 0.5, "ticks": 0, "h": None, "side": "r", "error": None}


def finish():
    unreal.unregister_slate_post_tick_callback(S["h"])
    for a in reversed(made):
        a.destroy_actor()
    if THUMB_FIT:
        import json
        (OUT / "thumb_fit.json").write_text(json.dumps(THUMB_FIT, indent=1))
    (OUT / "done.txt").write_text(S["error"] or "complete %d shots" % S["i"])


def tick(_dt):
    global F, L, U
    S["ticks"] += 1
    if time.monotonic() < S["ready"] or S["ticks"] < 4:
        return
    S["ticks"] = 0
    try:
        (name, fn), view = shots[S["i"]]
        if S["stage"] == 0:
            reset()
            F, L, U = frame_axes()
            S["side"] = fn() or "r"
            flush()
            S["stage"], S["ready"] = 1, time.monotonic() + 0.3
        elif S["stage"] == 1:
            s = S["side"]
            hand = (cs(f"hand_{s}").translation + cs(f"middle_01_{s}").translation) * 0.5 + ORIGIN
            cc.clear_show_only_components()
            for a in [host] + [f for f in followers if not (view == "elbow_nosleeve" and "Polo" in f.get_actor_label())]:
                cc.show_only_actor_components(a)
            if view.startswith("elbow"):  # same camera both ways: polo shown, then hidden
                tgt = cs("lowerarm_r").translation + ORIGIN
                eye = tgt + (F * 0.8 + L * -0.45 + U * 0.25).normal() * 45
                cc.fov_angle = 40
            elif view == "thumbside":  # from the index side, level with the knuckles: shows thumb over index
                k = (cs(f"index_01_{s}").translation - cs(f"pinky_01_{s}").translation).normal()
                tgt = hand
                eye = hand + (k * 0.85 + U * 0.3 + F * 0.25).normal() * 40
                cc.fov_angle = 40
            elif view == "fp":
                eye = cs("head").translation + F * 9 + U * 4 + ORIGIN
                tgt = hand if name in ("phone_grip_left",) else ((cs("hand_l").translation + cs("hand_r").translation) * 0.5 + ORIGIN
                                                                if name in ("open_relaxed", "full_fist", "wide_splay") else hand)
                cc.fov_angle = 80
            else:
                o = L * (1 if s == "l" else -1)
                eye = hand + (o * 0.75 + F * 0.55 + U * 0.35).normal() * 52
                tgt = hand
                cc.fov_angle = 40
            cap.set_actor_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, tgt), False, True)
            side = (tgt - eye).normal().cross(U).normal()
            lights[0].set_actor_location(eye + U * 25 + side * 15, False, True)  # key light beside the lens
            lights[1].set_actor_location(eye - side * 60 + U * -10, False, True)  # soft fill from the other side
            S["stage"], S["ready"] = 2, time.monotonic() + 0.5
        else:
            unreal.RenderingLibrary.export_render_target(w, cc.texture_target, str(OUT), f"{[p[0] for p in POSES].index(name):02d}_{name}_{view}.png")
            S["i"] += 1
            if S["i"] == len(shots):
                return finish()
            nxt = shots[S["i"]][0][0]
            S["stage"] = 0 if nxt != name else 1
            S["ready"] = time.monotonic() + 0.05
    except Exception as ex:
        S["error"] = repr(ex)
        finish()


S["h"] = unreal.register_slate_post_tick_callback(tick)
print("POSE_SHEET queued", len(shots), "shots ->", OUT)
