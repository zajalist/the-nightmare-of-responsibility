"""Hand close-ups for anim QA, taken in the lit bedroom without PIE or render_camera.
  shot:  python Tools/Unreal/ue_remote.py Tools/Unreal/player/preview_hands.py FOA_ANIM=/Game/.../UAL_PickUp_Table FOA_T=0.5 FOA_PNG=name
         Poses a temporary Manny at an open floor spot, aims a temporary camera at both hands, and requests a
         1600x1000 high-res shot. It lands in Saved/Screenshots/WindowsEditor/<name>.png a few ticks later.
  clean: ... FOA_MODE=clean   (removes the temporary actors; run it after the PNG has landed)"""
import math
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
TAGS = ("TMP_player_PreviewHands", "TMP_player_PreviewCam")


def contact_time(anim):
    """Moment the farther-travelling hand is furthest from its start pose (grab / grip / contact)."""
    AP, W = unreal.AnimPoseExtensions, unreal.AnimPoseSpaces.WORLD
    n = unreal.AnimationLibrary.get_num_frames(anim)
    opts = unreal.AnimPoseEvaluationOptions()
    poses = [AP.get_anim_pose_at_frame(anim, f, opts) for f in range(n + 1)]
    best = (0.0, 0)
    for b in ("hand_l", "hand_r"):
        p0 = AP.get_bone_pose(poses[0], b, W).translation
        for f, p in enumerate(poses):
            d = (AP.get_bone_pose(p, b, W).translation - p0).length()
            best = max(best, (d, f))
    return unreal.AnimationLibrary.get_time_at_frame(anim, best[1])


def run():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label() in TAGS:
            EAS.destroy_actor(a)
    if os.environ.get("FOA_MODE") == "clean":
        print("preview actors removed")
        return
    anim = unreal.load_asset(os.environ["FOA_ANIM"])
    t = os.environ.get("FOA_T", "auto")
    t = contact_time(anim) if t == "auto" else float(t)
    mesh = unreal.load_asset(os.environ.get("FOA_MESH", "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"))
    spot, yaw = unreal.Vector(-20.0, 40.0, 0.0), float(os.environ.get("FOA_YAW", "0"))  # open floor mid-room
    man = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, spot, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
    man.set_actor_label(TAGS[0])
    man.set_folder_path("Dev/PlayerAnimPreview")
    comp = man.get_editor_property("skeletal_mesh_component")
    comp.set_skeletal_mesh_asset(mesh)
    comp.set_update_animation_in_editor(True)
    comp.override_animation_data(anim, False, False, t, 0.0)
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, unreal.AnimPoseEvaluationOptions())
    hands = [unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation for b in ("hand_l", "hand_r")]
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def world(v):
        return spot + unreal.Vector(v.x * c - v.y * s, v.x * s + v.y * c, v.z)
    mid = world((hands[0] + hands[1]) * 0.5)
    span = (hands[0] - hands[1]).length()
    fwd = unreal.Vector(-s, c, 0.0)  # the mannequin faces +Y in component space
    dist = max(60.0, span * 1.6)  # FOV 40: both hands fill the frame
    cam_loc = mid + fwd * dist + unreal.Vector(0.0, 0.0, dist * 0.35)
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, cam_loc, unreal.MathLibrary.find_look_at_rotation(cam_loc, mid))
    cam.set_actor_label(TAGS[1])
    cam.set_folder_path("Dev/PlayerAnimPreview")
    cam.get_editor_property("camera_component").set_editor_property("field_of_view", 40.0)
    name = os.environ.get("FOA_PNG", "hands") + ".png"
    unreal.AutomationLibrary.take_high_res_screenshot(1600, 1000, name, camera=cam)
    print("requested", name, "pose", anim.get_name(), "t", t)


run()
