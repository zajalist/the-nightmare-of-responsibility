"""Animated source passes for the look GIFs (lookdev lane). Runs INSIDE the open editor and returns at once; the
frames are taken on later editor ticks (one frame per tick at most, ~12 fps of wall time, so animated materials such
as the light-shaft bands and the sand advance between frames). Writes Saved/LookDev/seq/f###_{color,depth,normal,
base}_0.exr and poses.json last; the temporary SceneCapture2D is destroyed after the final frame.
  python Tools/Unreal/ue_remote.py Tools/LookDev/capture_seq.py [FRAMES=30] [SIZE=1920x1080] [POSE=x,y,z,pitch,yaw,fov] [OUT=dir]
The move: from Shot_ThirdPerson (or POSE), a slow push (2 cm a frame) with a slight pan (0.12 deg yaw a frame)."""


def main():
    """Everything lives in this closure: ue_remote clears the script's globals after the run, and the tick
    callback outlives it."""
    import json
    import os
    import time

    import unreal

    E = {k: os.environ.pop(k) for k in ("FRAMES", "SIZE", "OUT", "POSE") if k in os.environ}
    N = int(E.get("FRAMES", 30))
    W, H = (int(v) for v in E.get("SIZE", "1920x1080").split("x"))
    OUT = E.get("OUT", "P:/FoA/Saved/LookDev/seq")
    OFF = ("PostProcessMaterial", "Grain", "Vignette", "Bloom", "LensFlares", "SceneColorFringe", "MotionBlur", "DepthOfField")
    os.makedirs(OUT, exist_ok=True)

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    if "POSE" in E:  # x,y,z,pitch,yaw,fov
        x, y, z, pitch, yaw, fov = (float(v) for v in E["POSE"].split(","))
        loc0, rot0 = unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw)
    else:
        cam = next(a for a in eas.get_all_level_actors()
                   if isinstance(a, unreal.CameraActor) and a.get_actor_label() == "Shot_ThirdPerson")
        loc0, rot0 = cam.get_actor_location(), cam.get_actor_rotation()
        fov = cam.get_editor_property("camera_component").get_editor_property("field_of_view")
    F, S = unreal.TextureRenderTargetFormat, unreal.SceneCaptureSource
    PASSES = [("color", unreal.RenderingLibrary.create_render_target2d(world, W, H, F.RTF_RGBA16F), S.SCS_FINAL_COLOR_HDR),
              ("depth", unreal.RenderingLibrary.create_render_target2d(world, W, H, F.RTF_RGBA32F), S.SCS_SCENE_DEPTH),
              ("normal", unreal.RenderingLibrary.create_render_target2d(world, W, H, F.RTF_RGBA16F), S.SCS_NORMAL),
              ("base", unreal.RenderingLibrary.create_render_target2d(world, W, H, F.RTF_RGBA16F), S.SCS_BASE_COLOR)]
    cap = eas.spawn_actor_from_class(unreal.SceneCapture2D, loc0, rot0)
    cap.set_actor_label("TMP_lookdev_Capture")  # cleanup rule: temporary things are TMP_<lane>_*
    comp = cap.capture_component2d
    flags = []
    for name in OFF:
        f = unreal.EngineShowFlagsSetting()
        f.set_editor_property("show_flag_name", name)
        f.set_editor_property("enabled", False)
        flags.append(f)
    for k, v in (("capture_every_frame", False), ("capture_on_movement", False), ("fov_angle", fov),
                 ("always_persist_rendering_state", True), ("show_flag_settings", flags)):
        comp.set_editor_property(k, v)
    st = {"i": 0, "t": 0.0, "busy": False, "h": None, "poses": [], "t0": time.time()}


    def pose(i):
        fwd = rot0.get_forward_vector()
        return (unreal.Vector(loc0.x + fwd.x * 2.0 * i, loc0.y + fwd.y * 2.0 * i, loc0.z + fwd.z * 2.0 * i),
                unreal.Rotator(roll=0.0, pitch=rot0.pitch, yaw=rot0.yaw + 0.12 * i))


    def finish():
        unreal.unregister_slate_post_tick_callback(st["h"])
        eas.destroy_actor(cap)
        with open(f"{OUT}/poses.json", "w", encoding="utf-8") as fh:
            json.dump({"fov": fov, "poses": st["poses"]}, fh)
        unreal.log(f"[FoA lookdev] seq done: {st['i']} frames in {time.time() - st['t0']:.1f}s")


    def tick(_dt):
        if st["busy"] or time.time() - st["t"] < 1 / 12:
            return
        st["busy"] = True
        try:
            i = st["i"]
            if i >= N or time.time() - st["t0"] > 90:  # hard stop: never a long-lived callback
                finish()
                return
            p, r = pose(i)
            cap.set_actor_location_and_rotation(p, r, False, False)
            for name, rt, src in PASSES:
                comp.set_editor_property("texture_target", rt)
                comp.set_editor_property("capture_source", src)
                for _ in range((24 if i == 0 else 2) if name == "color" else 1):  # TSR history carries across frames
                    comp.capture_scene()
                unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"f{i:03d}_{name}_0.exr")
            st["poses"].append([p.x, p.y, p.z, r.pitch, r.yaw, time.time() - st["t0"]])
            st["i"] += 1
            st["t"] = time.time()
        except Exception as e:  # any failure ends the run cleanly
            unreal.log_error(f"[FoA lookdev] seq failed: {e}")
            finish()
        finally:
            st["busy"] = False


    st["h"] = unreal.register_slate_post_tick_callback(tick)
    print("seq scheduled", N, "frames", W, H)


main()
