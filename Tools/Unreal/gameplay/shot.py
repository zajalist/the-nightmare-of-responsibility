"""Level screenshots through a temporary SceneCapture2D (the viewport capture can come back black):
  python Tools/Unreal/ue_remote.py Tools/Unreal/gameplay/shot.py FOA_SHOTS="name:x,y,z,pitch,yaw[,fov];..."
Writes P:/FoA/Saved/GameplayShots/<name>.png (final colour with the dream post-process; FOA_SRC=base for unlit
base colour, to check placement in dark corners) and removes the capture.
Editor world only; PIE frames come from Hayba editor_pie_screenshot."""
import os

import unreal

OUT = "P:/FoA/Saved/GameplayShots"
os.makedirs(OUT, exist_ok=True)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rt = unreal.RenderingLibrary.create_render_target2d(world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8)
for spec in [s for s in os.environ.get("FOA_SHOTS", "").split(";") if s]:
    name, nums = spec.split(":")
    x, y, z, pitch, yaw, *fov = (float(v) for v in nums.split(","))
    cap = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
        unreal.SceneCapture2D, unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
    cap.set_actor_label("TMP_gameplay_capture")  # temporary: destroyed below (editor-rules cleanup naming)
    c = cap.capture_component2d
    for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR if os.environ.get("FOA_SRC") == "base"
                                       else unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                 ("capture_every_frame", False), ("capture_on_movement", False), ("fov_angle", fov[0] if fov else 70.0)):
        c.set_editor_property(k, v)
    c.capture_scene()
    unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
    cap.destroy_actor()
    print("shot", f"{OUT}/{name}.png")
