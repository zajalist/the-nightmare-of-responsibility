"""Renders a view through a transient SceneCapture2D to P:/FoA/Saved/FireplaceShots/<name>.png (no assets, actor removed).
  ue_remote.py Tools/Fireplace/fp_capture.py FOA_NAME=wide FOA_CAM=-340,280,270 FOA_ROT=-16.9,-50.3 [FOA_PPMAT=0|1]
  ue_remote.py Tools/Fireplace/fp_capture.py FOA_NAME=close FOA_CAM=-120,-90,165 FOA_LOOK=-330,0,70 [FOA_FOV=75]
FOA_PPMAT=0 skips post-process materials (exposure and tonemapping still apply), to judge the asset itself.
"""
import math
import os

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
name, cam = os.environ["FOA_NAME"], os.environ["FOA_CAM"]
fov = float(os.environ.get("FOA_FOV", "0") or 0)
if cam.startswith("actor:"):
    src = next(a for a in EAS.get_all_level_actors() if a.get_actor_label() == cam[6:])
    loc, rot = src.get_actor_location(), src.get_actor_rotation()
    fov = fov or src.get_editor_property("camera_component").get_editor_property("field_of_view")
elif os.environ.get("FOA_ROT"):  # a pose from editor-rules: location + (pitch, yaw)
    loc = unreal.Vector(*(float(v) for v in cam.split(",")))
    pitch, yaw = (float(v) for v in os.environ["FOA_ROT"].split(","))
    rot = unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)
    fov = fov or 90.0
else:
    x, y, z = (float(v) for v in cam.split(","))
    tx, ty, tz = (float(v) for v in os.environ["FOA_LOOK"].split(","))
    loc = unreal.Vector(x, y, z)
    rot = unreal.Rotator(roll=0.0, pitch=math.degrees(math.atan2(tz - z, math.hypot(tx - x, ty - y))),
                         yaw=math.degrees(math.atan2(ty - y, tx - x)))
    fov = fov or 75.0

rt = unreal.RenderingLibrary.create_render_target2d(world, 1600, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, loc, rot, transient=True)
cap.set_actor_label("TMP_fireplace_Capture")  # destroyed below; TMP_ prefix per the clean-up rule
cc = cap.capture_component2d
cc.set_editor_property("fov_angle", fov)
cc.set_editor_property("texture_target", rt)
cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
cc.set_editor_property("capture_every_frame", False)
cc.set_editor_property("always_persist_rendering_state", True)  # lets Lumen accumulate across the repeated captures
if os.environ.get("FOA_PPMAT", "1") == "0":
    flag = unreal.EngineShowFlagsSetting()
    flag.set_editor_property("show_flag_name", "PostProcessMaterial")
    flag.set_editor_property("enabled", False)
    cc.set_editor_property("show_flag_settings", [flag])
for _ in range(12):
    cc.capture_scene()
out = "P:/FoA/Saved/FireplaceShots"
os.makedirs(out, exist_ok=True)
unreal.RenderingLibrary.export_render_target(world, rt, out, name + ".png")
EAS.destroy_actor(cap)
print("wrote", f"{out}/{name}.png", "fov", fov)
