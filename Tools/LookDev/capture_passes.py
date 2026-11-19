"""Clean source passes for offline look development (lookdev lane). Runs INSIDE the open editor, one camera per run:
  python Tools/Unreal/ue_remote.py Tools/LookDev/capture_passes.py CAM=Shot_ThirdPerson [POSE=x,y,z,pitch,yaw,fov] [NAME=prefix]
A temporary SceneCapture2D (destroyed afterwards) copies the camera's pose and FOV (or POSE when the camera actor is
gone) and writes to Saved/LookDev/src:
  <cam>_color_0.exr   final colour in linear HDR (SCS_FinalColorHDR: TSR-resolved, before the tone curve) with
                      post-process materials, bloom, grain, vignette, fringe, DOF and motion blur OFF. Show flags only:
                      PP_DreamMono's settings and blendables are never touched. Exposure is normalised offline (a
                      capture's eye adaptation never converges inside one call).
  <cam>_depth_0.exr   scene depth in cm (R)    <cam>_normal_0.exr  world normal    <cam>_base_0.exr  base colour"""
import os

import unreal

E = {k: os.environ.pop(k) for k in ("CAM", "OUT", "SIZE", "POSE", "NAME") if k in os.environ}
CAM, OUT = E["CAM"], E.get("OUT", "P:/FoA/Saved/LookDev/src")
NAME = E.get("NAME", CAM)  # output file prefix
W, H = (int(v) for v in E.get("SIZE", "1600x900").split("x"))
OFF = ("PostProcessMaterial", "Grain", "Vignette", "Bloom", "LensFlares", "SceneColorFringe", "MotionBlur", "DepthOfField")


def run():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cams = {a.get_actor_label(): a for a in eas.get_all_level_actors() if isinstance(a, unreal.CameraActor)}
    if CAM in cams:
        cam = cams[CAM]
        loc, rot = cam.get_actor_location(), cam.get_actor_rotation()
        fov = cam.get_editor_property("camera_component").get_editor_property("field_of_view")
    elif "POSE" in E:
        x, y, z, pitch, yaw, fov = (float(v) for v in E["POSE"].split(","))
        loc, rot = unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)
        print(f"{CAM} not in level, using POSE; cameras: {sorted(cams)}")
    else:
        raise SystemExit(f"{CAM} not found; cameras: {sorted(cams)}")
    print(f"POSE {NAME} {loc.x:.1f},{loc.y:.1f},{loc.z:.1f},{rot.pitch:.2f},{rot.yaw:.2f},{fov:.1f}")
    F, S = unreal.TextureRenderTargetFormat, unreal.SceneCaptureSource
    passes = [("color", F.RTF_RGBA16F, S.SCS_FINAL_COLOR_HDR, 40), ("depth", F.RTF_RGBA32F, S.SCS_SCENE_DEPTH, 2),
              ("normal", F.RTF_RGBA16F, S.SCS_NORMAL, 2), ("base", F.RTF_RGBA16F, S.SCS_BASE_COLOR, 2)]
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot)
    cap.set_actor_label("TMP_lookdev_Capture")  # cleanup rule: temporary things are TMP_<lane>_*
    try:
        c = cap.capture_component2d
        flags = []
        for name in OFF:
            f = unreal.EngineShowFlagsSetting()
            f.set_editor_property("show_flag_name", name)
            f.set_editor_property("enabled", False)
            flags.append(f)
        for k, v in (("capture_every_frame", False), ("capture_on_movement", False), ("fov_angle", fov),
                     ("always_persist_rendering_state", True), ("show_flag_settings", flags)):
            c.set_editor_property(k, v)
        for name, fmt, source, settle in passes:
            c.set_editor_property("texture_target", unreal.RenderingLibrary.create_render_target2d(world, W, H, fmt))
            c.set_editor_property("capture_source", source)
            for _ in range(settle):  # settle TSR history and Lumen
                c.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, c.get_editor_property("texture_target"), OUT,
                                                         f"{NAME}_{name}_0.exr")
            print("wrote", f"{NAME}_{name}_0.exr")
    finally:
        eas.destroy_actor(cap)


run()
