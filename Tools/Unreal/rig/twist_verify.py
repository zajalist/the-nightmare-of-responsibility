"""(PIE variant: FOA_WORLD=pie spawns the probe in the running game world.) Does ABP_FoA_TeenPost turn the forearm twist bones at runtime? A transient TMP_rig_ SkeletalMeshActor plays the
Teen phone retarget (single node; the mesh's post-process ABP still runs), then a later tick reads the twist of
hand_r and lowerarm_twist_01_r relative to lowerarm_r about the forearm axis. Writes twist_verify.json.
  $env:FOA_AREAS='Characters'; $env:FOA_ACTORS_NEW='TMP_rig_'; python Tools/Unreal/ue_remote.py Tools/Unreal/rig/twist_verify.py"""
import json
import math
import time

import unreal

CLIPS = json.load(open("P:/FoA/Saved/RigShots/audit/clip_retarget.json"))
E = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
import os
w = E.get_game_world() if os.environ.get("FOA_WORLD") == "pie" else E.get_editor_world()
assert w, "no world"
a = c = None
# Transient probe actor only while the scratch phone retarget exists (clip_retarget.py); PIE also reads the real player.
if unreal.EditorAssetLibrary.does_asset_exist(CLIPS["phone"]["target"].split(".")[0]):
    gs = unreal.get_default_object(unreal.GameplayStatics)
    tr = unreal.Transform(location=unreal.Vector(0, 0, 3000))
    a = gs.call_method("BeginDeferredActorSpawnFromClass", (w, unreal.SkeletalMeshActor.static_class(), tr,
                       unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a = gs.call_method("FinishSpawningActor", (a, tr, unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
    a.set_actor_label("TMP_rig_twist")
    c = a.skeletal_mesh_component
    c.set_skeletal_mesh_asset(unreal.load_asset("/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body"))
    c.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    c.set_update_animation_in_editor(True)
    if hasattr(c, "set_disable_post_process_blueprint"):
        c.set_disable_post_process_blueprint(False)
    post = unreal.load_asset("/Game/FoA/Characters/Teen/Anim/ABP_FoA_TeenPost").generated_class()
    if hasattr(c, "set_override_post_process_anim_bp"):
        c.set_override_post_process_anim_bp(post, True)
    anim = unreal.load_asset(CLIPS["phone"]["target"].split(".")[0])
    c.set_animation(anim)
    c.set_position(0.5 * anim.get_play_length(), False)
S = {"t": time.monotonic() + 1.0, "h": None, "n": 0}


def qmul(a, b):
    return unreal.Quat(a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y, a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
                       a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w, a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)


def inv(a):
    return unreal.Quat(-a.x, -a.y, -a.z, a.w)


def twist_about(qa, qb, axis):
    """Signed angle (deg) of rotation qa^-1*qb about axis (in qa's frame)."""
    rel = qmul(inv(qa), qb)
    x, y, z, w_ = rel.x, rel.y, rel.z, rel.w
    p = x * axis[0] + y * axis[1] + z * axis[2]
    ang = math.degrees(2 * math.atan2(p, w_))
    return round((ang + 180) % 360 - 180, 1)


def tick(_dt):
    S["n"] += 1
    if time.monotonic() < S["t"] or S["n"] < 6:
        return
    unreal.unregister_slate_post_tick_callback(S["h"])
    out = {}
    try:
        out["players_only"] = c is None
        if c is not None:
            out.update(transient(c))
        out["player_bodies"] = players()
    except Exception as ex:  # report, never leave the actor behind
        out["error"] = repr(ex)
    if a:
        a.destroy_actor()
    json.dump(out, open("P:/FoA/Saved/RigShots/audit/twist_verify.json", "w"), indent=1)


def refs(k):
    return {b: k.get_ref_pose_transform(k.get_bone_index(b)).rotation for b in ("hand_r", "lowerarm_twist_01_r", "hand_l", "lowerarm_twist_01_l")}


def transient(c):
    out = {"post_process": str(c.get_post_process_instance()) if hasattr(c, "get_post_process_instance") else "n/a"}
    if True:
        la = c.get_socket_transform("lowerarm_r", unreal.RelativeTransformSpace.RTS_COMPONENT).rotation
        tw = c.get_socket_transform("lowerarm_twist_01_r", unreal.RelativeTransformSpace.RTS_COMPONENT).rotation
        hd = c.get_socket_transform("hand_r", unreal.RelativeTransformSpace.RTS_COMPONENT).rotation
        la0 = c.get_ref_pose_transform(c.get_bone_index("lowerarm_r")).rotation
        hd0 = c.get_ref_pose_transform(c.get_bone_index("hand_r")).rotation
        tw0 = c.get_ref_pose_transform(c.get_bone_index("lowerarm_twist_01_r")).rotation
        out["hand_local_twist_vs_ref"] = twist_about(hd0, qmul(inv(la), hd), (0, 1, 0))
        out["twist_local_twist_vs_ref"] = twist_about(tw0, qmul(inv(la), tw), (0, 1, 0))
    return out


def players():
    found = []  # the real player body in PIE uses the mesh's own post-process slot, no override
    if True:
        for actor in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
            for k in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                mesh = k.get_skeletal_mesh_asset()
                if k != c and mesh and mesh.get_name() == "SK_Teen_Body":
                    r = refs(k)
                    row = {"actor": actor.get_name(), "post_process": str(k.get_post_process_instance()) if hasattr(k, "get_post_process_instance") else "n/a"}
                    for sd in "rl":
                        cs = unreal.RelativeTransformSpace.RTS_COMPONENT
                        kla = k.get_socket_transform(f"lowerarm_{sd}", cs).rotation
                        ktw = k.get_socket_transform(f"lowerarm_twist_01_{sd}", cs).rotation
                        khd = k.get_socket_transform(f"hand_{sd}", cs).rotation
                        h = twist_about(r[f"hand_{sd}"], qmul(inv(kla), khd), (0, 1, 0))
                        t = twist_about(r[f"lowerarm_twist_01_{sd}"], qmul(inv(kla), ktw), (0, 1, 0))
                        row[f"hand_twist_{sd}"], row[f"twist_bone_twist_{sd}"] = h, t
                        row[f"share_{sd}"] = round(t / h, 3) if abs(h) > 1 else None
                    found.append(row)
    return found


S["h"] = unreal.register_slate_post_tick_callback(tick)
print("TWIST_VERIFY queued")
