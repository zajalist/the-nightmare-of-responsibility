"""Neutral hand close-ups for retarget QA: no dream post-process, studio lights, manual exposure.
  python Tools/Unreal/ue_remote.py Tools/Unreal/player/qa_hands_capture.py [FOA_CLIPS=PickUp_Table,Interact,Fixing_Kneeling]
Poses a temporary Manny in an empty spot 200 m below the level, lit by three temporary lights, and renders each panel
with a SceneCapture2D (PostProcessMaterial show flag off) to Saved/GraphShots/qa_hands/<clip>_<ver>_<view>.png.
Runs from a Slate tick callback (each pose needs a tick to apply) and removes its actors when done; then
Tools/Unreal/player/compose_hands.py (plain Python) builds the side-by-side sheets."""
import math
import os

import unreal

P = "/Game/FoA/Characters/Player"
VERSIONS = {"before": P + "/_QA/Before/UAL_", "after": P + "/Anims/UAL/UAL_"}
OUT = os.path.join(unreal.Paths.project_saved_dir(), "GraphShots", "qa_hands").replace("\\", "/")
SPOT = unreal.Vector(0.0, 0.0, -20000.0)
TAG = "TMP_player_QA"
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
AP, W = unreal.AnimPoseExtensions, unreal.AnimPoseSpaces.WORLD


def contact(anim):
    """(time, hand) of the farther-travelling hand's peak displacement from its start pose."""
    n = unreal.AnimationLibrary.get_num_frames(anim)
    opts = unreal.AnimPoseEvaluationOptions()
    poses = [AP.get_anim_pose_at_frame(anim, f, opts) for f in range(n + 1)]
    best = (0.0, 0, "hand_r")
    for b in ("hand_l", "hand_r"):
        p0 = AP.get_bone_pose(poses[0], b, W).translation
        for f, p in enumerate(poses):
            best = max(best, ((AP.get_bone_pose(p, b, W).translation - p0).length(), f, b))
    return best[1], best[2]


def views(anim, t, hand):
    """Camera (location, look-at) pairs: three-quarter (back of hand + thumb side) and palm side, in world space."""
    side = hand[-1]
    pose = AP.get_anim_pose_at_time(anim, t, unreal.AnimPoseEvaluationOptions())
    g = lambda b: AP.get_bone_pose(pose, f"{b}_{side}", W).translation + SPOT  # noqa: E731 (actor at SPOT, yaw 0)
    h, idx, pky, th, mid = g("hand"), g("index_01"), g("pinky_01"), g("thumb_02"), g("middle_02")
    across = (idx - pky)
    along = (mid - h)
    palm = across.cross(along) if side == "l" else along.cross(across)
    palm, across = palm.normal(), across.normal()
    center = (h + mid + th) * (1.0 / 3.0)
    tq = (palm * -1.0 + across * 0.8 + unreal.Vector(0, 0, 0.5)).normal()
    return {"3q": (center + tq * 70.0, center), "palm": (center + palm * 66.0 + unreal.Vector(0, 0, 8), center)}


def build_shots(clips):
    shots = []
    for clip in clips:
        after = unreal.load_asset(VERSIONS["after"] + clip)
        f, hand = contact(after)
        for ver, prefix in VERSIONS.items():
            anim = unreal.load_asset(prefix + clip)
            if not anim:  # "before" exists only for the three clips re-made in _QA
                continue
            for label, frame, kinds in (("reach", max(0, f - 2), ("3q",)), ("contact", f, ("3q", "palm"))):
                t = unreal.AnimationLibrary.get_time_at_frame(anim, frame)
                for k in kinds:
                    shots.append((f"{clip}_{ver}_{label}_{k}", anim, t, hand, k))
    return shots


def light(cls, loc, lumens, label):
    a = EAS.spawn_actor_from_class(cls, loc, unreal.Rotator())
    a.set_actor_label(label)
    a.set_folder_path("Dev/PlayerAnimPreview")
    c = a.get_editor_property("light_component")
    c.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    c.set_editor_property("intensity", lumens)
    c.set_editor_property("attenuation_radius", 600.0)
    c.set_editor_property("cast_shadows", True)
    return a


def setup():
    for a in EAS.get_all_level_actors():
        if a.get_actor_label().startswith(TAG):
            EAS.destroy_actor(a)
    man = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, SPOT, unreal.Rotator())
    man.set_actor_label(TAG)
    man.set_folder_path("Dev/PlayerAnimPreview")
    comp = man.get_editor_property("skeletal_mesh_component")
    comp.set_skeletal_mesh_asset(unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"))
    comp.set_update_animation_in_editor(True)
    # Seen only by a SceneCapture, the mesh never counts as rendered: the default tick option would freeze its pose.
    comp.set_editor_property("visibility_based_anim_tick_option",
                             unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    k = float(os.environ.get("FOA_LIGHT", "0.007"))  # manual exposure sits at EV0: studio lights of tens of lumens
    lights = [light(unreal.PointLight, SPOT + unreal.Vector(120, 160, 230), 9000.0 * k, TAG + "_Key"),
              light(unreal.PointLight, SPOT + unreal.Vector(-160, 140, 120), 3500.0 * k, TAG + "_Fill"),
              light(unreal.PointLight, SPOT + unreal.Vector(0, -180, 200), 5000.0 * k, TAG + "_Rim")]
    cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, SPOT, unreal.Rotator())
    cap.set_actor_label(TAG + "_Capture")
    cap.set_folder_path("Dev/PlayerAnimPreview")
    cc = cap.get_editor_property("capture_component2d")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    rt = unreal.RenderingLibrary.create_render_target2d(world, 800, 500, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    cc.set_editor_property("texture_target", rt)
    cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cc.set_editor_property("capture_every_frame", False)
    cc.set_editor_property("capture_on_movement", False)
    cc.set_editor_property("fov_angle", 30.0)
    flags = [unreal.EngineShowFlagsSetting(show_flag_name=n, enabled=False)
             for n in ("PostProcessMaterial", "Fog", "VolumetricFog", "Vignette", "Grain", "AmbientOcclusion")]
    cc.set_editor_property("show_flag_settings", flags)
    pp = cc.get_editor_property("post_process_settings")
    for flag, prop, v in (("override_auto_exposure_method", "auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                          ("override_auto_exposure_apply_physical_camera_exposure", "auto_exposure_apply_physical_camera_exposure", False),
                          ("override_auto_exposure_bias", "auto_exposure_bias", float(os.environ.get("FOA_EXPOSURE", "0.0"))),
                          ("override_bloom_intensity", "bloom_intensity", 0.0),
                          ("override_film_grain_intensity", "film_grain_intensity", 0.0),
                          ("override_vignette_intensity", "vignette_intensity", 0.0)):
        pp.set_editor_property(flag, True)
        pp.set_editor_property(prop, v)
    cc.set_editor_property("post_process_settings", pp)
    cc.set_editor_property("post_process_blend_weight", 1.0)
    return world, man, comp, cap, cc, rt, lights


def start():
    os.makedirs(OUT, exist_ok=True)
    clips = [c for c in os.environ.get("FOA_CLIPS", "PickUp_Table,Interact,Fixing_Kneeling,Sitting_Idle_Loop,LayToIdle").split(",") if c]
    shots = build_shots(clips)
    world, man, comp, cap, cc, rt, lights = setup()
    st = {"i": 0, "wait": 0, "handle": None, "busy": False}

    def tick(_dt):
        if st["busy"]:
            return
        st["busy"] = True
        try:
            if st["i"] >= len(shots):
                for a in [man, cap] + lights:
                    EAS.destroy_actor(a)
                unreal.unregister_slate_post_tick_callback(st["handle"])
                open(OUT + "/done.txt", "w").write(f"{len(shots)} shots\n")
                unreal.log("[FoA] qa hands done")
                return
            name, anim, t, hand, kind = shots[st["i"]]
            if st["wait"] == 0:
                comp.override_animation_data(anim, False, False, t, 0.0)
            st["wait"] += 1
            if st["wait"] < 4:  # let the editor tick the new pose onto the mesh
                return
            if st["wait"] == 4:  # capture_scene only enqueues the render: export on a later tick
                loc, target = views(anim, t, hand)[kind]
                cap.set_actor_location_and_rotation(loc, unreal.MathLibrary.find_look_at_rotation(loc, target), False, False)
                cc.capture_scene()
                return
            if st["wait"] < 7:
                return
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
            st["i"] += 1
            st["wait"] = 0
        finally:
            st["busy"] = False

    if os.path.exists(OUT + "/done.txt"):
        os.remove(OUT + "/done.txt")
    st["handle"] = unreal.register_slate_post_tick_callback(tick)
    print("scheduled", len(shots), "hand shots ->", OUT)


start()
