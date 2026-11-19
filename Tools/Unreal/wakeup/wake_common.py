"""Shared by the wake-up build scripts (run inside the editor through ue_remote.py): paths, the timeline, the AnimPose
adapter for edge_clip, room facts read from the live level, and the placement solver.
Placement is computed from the level every run (bed, nightstand, alarm clock, mattress traces), so moving furniture
and rebuilding keeps hands on the mattress and the grab on the clock."""
import json
import math
import os
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib  # noqa: E402

import edge_clip  # noqa: E402
import wake_math as m  # noqa: E402

importlib.reload(m)  # the editor keeps modules cached between runs
importlib.reload(edge_clip)

CIN = "/Game/FoA/Cinematics"
WAKE = CIN + "/WakeUp"
LS_PATH = CIN + "/LS_WakeUp"
EDGE_ANIM = WAKE + "/AS_FoA_Wake_EdgeReach"
UAL = "/Game/FoA/Characters/Player/Anims/UAL/"
PLAYER_BP = "/Game/FoA/Characters/Player/BP_FoAPlayer"
PLACEMENT = "P:/FoA/Saved/WakeUp/placement.json"
FPS = 30

import wake_cues  # noqa: E402

importlib.reload(wake_cues)
T = wake_cues.T  # the timeline lives with the cues (engine-free, shared with mux_audio.py)
SITUP_SPAN = 0.48  # LayToIdle 0..0.48 s: supine to sitting up, both hands pushing on the surface


def frames(sec):
    return int(round(sec * FPS))


# ---------------------------------------------------------------- AnimPose adapter
AP = unreal.AnimPoseExtensions
LOCAL, WORLD = unreal.AnimPoseSpaces.LOCAL, unreal.AnimPoseSpaces.WORLD


class UeAdapter(m.PoseAdapter):
    def __init__(self, clips):
        """clips: {key: AnimSequence}. Parents are recovered once from a pose (AnimPose exposes no hierarchy)."""
        super().__init__()
        self.clips = clips
        self.opts = unreal.AnimPoseEvaluationOptions()
        first = next(iter(clips.values()))
        pose = AP.get_anim_pose_at_frame(first, 0, self.opts)
        self.names = [str(b) for b in AP.get_bone_names(pose)]
        self.parent = self._parents(pose)

    @staticmethod
    def _xf(t):
        return ((t.translation.x, t.translation.y, t.translation.z), (t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w),
                (t.scale3d.x, t.scale3d.y, t.scale3d.z))

    def _parents(self, pose):
        loc = {b: self._xf(AP.get_bone_pose(pose, b, LOCAL)) for b in self.names}
        wor = {b: self._xf(AP.get_bone_pose(pose, b, WORLD)) for b in self.names}
        par = {}
        for i, b in enumerate(self.names):
            if i == 0:
                continue
            lp, lq, _ = loc[b]
            best = None
            for c in self.names[:i]:  # UE bone order: parents always come first
                pp, pq, _ = wor[c]
                err = m.length(m.sub(m.add(pp, m.qrot(pq, lp)), wor[b][0]))
                if best is None or err < best[0]:
                    best = (err, c)
            par[b] = best[1]
        return par

    def raw(self, clip, t):
        pose = AP.get_anim_pose_at_time(self.clips[clip], t, self.opts)
        return m.Pose({b: self._xf(AP.get_bone_pose(pose, b, LOCAL)) for b in self.names}, self.parent)


# ---------------------------------------------------------------- room facts
# Python never wraps Blueprint instances or CDOs here (editor-rules: a later Hayba compile of that Blueprint would leave
# dangling wrapper types). Actor labels, classes, paths and locations come from Hayba (actor_find) through FOA_ROOM;
# only native StaticMeshActors are loaded by path for their bounds. The player rig comes from Hayba object_get_property
# through FOA_RIG, with set_camera.py's values as defaults.
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
RIG_DEFAULT = {"half_height": 96.0, "mesh_rel": ((0.0, 0.0, -96.0), -90.0),
               "arm": {"rel": (0.0, 0.0, 0.0), "length": 220.0, "socket": (0.0, 45.0, 55.0), "target": (0.0, 0.0, 0.0)},
               "cam": {"rel": (0.0, 0.0, 0.0), "fov": 80.0}}


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def env_json(key, default=None):
    raw = os.environ.get(key)
    if raw and os.path.exists(raw):
        with open(raw, encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(raw) if raw else default


def room_actors():
    """{label: {"class", "path", "location"}} from FOA_ROOM (Hayba results) or, failing that, every native
    StaticMeshActor / light found by class query (native classes only: no Blueprint wrappers)."""
    room = env_json("FOA_ROOM", None)
    if room:
        return room
    out = {}
    for a in EAS.get_all_level_actors():  # Blueprint actors too (the Bed is a BP_Interactable now)
        l = a.get_actor_location()
        out[a.get_actor_label()] = {"class": a.get_class().get_name(), "path": a.get_path_name(), "location": [l.x, l.y, l.z]}
    return out


def native_bounds(info):
    """World bounds of an actor loaded by path. A Blueprint actor's bounds are its largest static mesh component's
    (its other components, triggers and billboards, would inflate the actor bounds)."""
    if not info:
        return None
    a = unreal.find_object(None, info["path"])
    if not a:
        return None
    if info.get("class", "").endswith("_C"):
        boxes = [unreal.SystemLibrary.get_component_bounds(c) for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        if not boxes:
            return None
        o, e, _ = max(boxes, key=lambda b: b[2])
    else:
        o, e = a.get_actor_bounds(False)
    return (o.x, o.y, o.z), (e.x, e.y, e.z)


def trace_down(x, y, top=250.0):
    """First blocking surface z below (x, y), or None. Only the impact point is read, never the hit actor."""
    r = unreal.SystemLibrary.line_trace_single(world(), unreal.Vector(x, y, top), unreal.Vector(x, y, -5.0),
                                               unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                               unreal.DrawDebugTrace.NONE, True)
    hit = r[1] if isinstance(r, tuple) else r
    if not hit:
        return None
    t = hit.to_tuple()  # traces here only land on the bed's native StaticMeshActors
    return t[5].z if t[0] else None


def player_rig():
    rig = json.loads(json.dumps(RIG_DEFAULT))
    bp = unreal.load_asset(PLAYER_BP)
    assert bp, PLAYER_BP
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property('Mesh')
    offset = mesh.get_editor_property('relative_location')
    scale = mesh.get_editor_property('relative_scale3d')
    assert max(scale.x, scale.y, scale.z)-min(scale.x, scale.y, scale.z)<1e-5, 'Wake solver requires uniform character scale'
    rig.update(half_height=cdo.get_editor_property('CapsuleComponent').get_editor_property('capsule_half_height'),
               mesh_rel=((offset.x,offset.y,offset.z),mesh.get_editor_property('relative_rotation').yaw),
               mesh_scale=scale.x)
    rig.update(env_json("FOA_RIG", {}))
    return rig


# ---------------------------------------------------------------- transforms (UE: yaw about +Z, X forward)
Z = (0.0, 0.0, 1.0)


def yaw_q(deg):
    return m.qaxis(Z, deg)


def comp_to_world(p_c, actor_loc, actor_yaw, rig):
    """Component-space point of the pawn's mesh -> world, for an actor at actor_loc with yaw actor_yaw."""
    (ml, myaw) = rig["mesh_rel"]
    p = m.add(m.qrot(yaw_q(myaw), m.mul(p_c, rig.get('mesh_scale',1.0))), ml)
    return m.add(m.qrot(yaw_q(actor_yaw), p), actor_loc)


def actor_q(pitch, yaw):
    """UE rotator (pitch, yaw) as a quaternion: yaw about +Z, then pitch (positive = nose up)."""
    return m.qmul(yaw_q(yaw), m.qaxis((0.0, 1.0, 0.0), -pitch))


def comp_to_world_q(p_c, actor_loc, q, rig):
    (ml, myaw) = rig["mesh_rel"]
    return m.add(m.qrot(q, m.add(m.qrot(yaw_q(myaw), m.mul(p_c,rig.get('mesh_scale',1.0))), ml)), actor_loc)


def comp_dir_to_world(v, actor_yaw, rig):
    return m.qrot(yaw_q(actor_yaw), m.qrot(yaw_q(rig["mesh_rel"][1]), v))


def world_to_comp(p_w, actor_loc, actor_yaw, rig):
    (ml, myaw) = rig["mesh_rel"]
    p = m.qrot(m.qinv(yaw_q(actor_yaw)), m.sub(p_w, actor_loc))
    return m.mul(m.qrot(m.qinv(yaw_q(myaw)), m.sub(p, ml)), 1.0/rig.get('mesh_scale',1.0))


def comp_dirs(rig):
    """Component forward/left/up for a UE mannequin mesh: forward is the direction that maps to actor +X."""
    myaw = rig["mesh_rel"][1]
    fwd = m.qrot(m.qinv(yaw_q(myaw)), (1.0, 0.0, 0.0))
    left = m.qrot(m.qinv(yaw_q(myaw)), (0.0, -1.0, 0.0))  # actor -Y is the character's left (UE is left-handed)
    return fwd, left, Z


def yaw_of(v):
    return math.degrees(math.atan2(v[1], v[0]))


def save_placement(data):
    os.makedirs(os.path.dirname(PLACEMENT), exist_ok=True)
    with open(PLACEMENT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


def load_placement():
    with open(PLACEMENT, encoding="utf-8") as fh:
        return json.load(fh)
