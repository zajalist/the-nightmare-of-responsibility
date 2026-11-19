"""Deterministic post-process shots without touching the shared level viewport (other lanes pilot it).
Spawns a temporary SceneCapture2D (final LDR colour, so PP_DreamMono's blendables run), keeps its view state so
camera motion between frames yields real velocity for the time-shift echo, writes PNGs, then removes the actor.
  python Tools/Unreal/ue_remote.py Tools/Unreal/shoot_dream_post.py SHOTS="name@x,y,z,pitch,yaw,fov;..."
      [MPC="EchoStrength=1.2,GlitchAmount=0.8"] [BURST="dx,dy,dz,dyaw,frames"] [OUT=P:/FoA/Saved/PPShots]
      [TICKS=n: n frames of the first shot over n editor ticks, for effects that move in time]
MPC overrides apply to the world (the editor viewport shows them too) and are restored afterwards.
"""
import os

import unreal

# ue_remote's KEY=VALUE pairs live on in the editor's os.environ: consume ours so they never leak into the next run
E = {k: os.environ.pop(k) for k in ("SHOTS", "MPC", "MPCV", "BURST", "OUT", "NOPPM", "SIZE", "SEQ", "TICKS") if k in os.environ}
W, H = (int(v) for v in E.get("SIZE", "1280x720").split("x"))
OUT = E.get("OUT", "P:/FoA/Saved/PPShots")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
KML = unreal.MaterialLibrary  # UKismetMaterialLibrary
mpc = unreal.load_asset("/Game/FoA/PostProcess/MPC_Dream")

over = dict(kv.split("=") for kv in E.get("MPC", "").split(",") if "=" in kv)
over_v = {k: unreal.LinearColor(*(float(c) for c in v.split("|")))   # MPCV="FilmLook=0|0|0|0,LensLook=..."
          for k, v in (kv.split("=") for kv in E.get("MPCV", "").split(",") if "=" in kv)}
saved = {k: KML.get_scalar_parameter_value(world, mpc, k) for k in over}
saved_v = {k: KML.get_vector_parameter_value(world, mpc, k) for k in over_v}
for k, v in over.items():
    KML.set_scalar_parameter_value(world, mpc, k, float(v))
for k, v in over_v.items():
    KML.set_vector_parameter_value(world, mpc, k, v)

rt = unreal.RenderingLibrary.create_render_target2d(world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0))
cap.set_actor_label("TMP_pp_Capture")  # editor-rules: temporaries are TMP_<lane>_*, destroyed in this run
c = cap.capture_component2d
for k, v in (("texture_target", rt), ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
             ("capture_every_frame", False), ("capture_on_movement", False),
             ("always_persist_rendering_state", True)):  # keeps last frame's view for velocity + eye adaptation
    c.set_editor_property(k, v)
eye = unreal.EngineShowFlagsSetting()  # captures skip eye adaptation by default; the game view uses it
eye.set_editor_property("show_flag_name", "EyeAdaptation")
eye.set_editor_property("enabled", True)
flags = [eye]
if E.get("NOPPM"):  # debug: skip post-process materials
    off = unreal.EngineShowFlagsSetting()
    off.set_editor_property("show_flag_name", "PostProcessMaterial")
    off.set_editor_property("enabled", False)
    flags.append(off)
c.set_editor_property("show_flag_settings", flags)
pps = c.get_editor_property("post_process_settings")  # captures turn Lumen off by default; the game view uses it
for flag, prop, value in (("override_dynamic_global_illumination_method", "dynamic_global_illumination_method",
                           unreal.DynamicGlobalIlluminationMethod.LUMEN),
                          ("override_reflection_method", "reflection_method", unreal.ReflectionMethod.LUMEN)):
    pps.set_editor_property(flag, True)
    pps.set_editor_property(prop, value)
c.set_editor_property("post_process_settings", pps)


def finish():
    EAS.destroy_actor(cap)
    for k, v in saved.items():
        KML.set_scalar_parameter_value(world, mpc, k, v)
    for k, v in saved_v.items():
        KML.set_vector_parameter_value(world, mpc, k, v)


def ticks(n):
    """Animation in time (heat haze, slips): game time does not move inside one script run, so capture one frame per
    editor tick (unthrottled meanwhile), then clean up from the last tick. Frame times go to <name>_times.txt."""
    name, pose = E["SHOTS"].split(";")[0].split("@")
    x, y, z, pitch, yaw, fov = (float(v) for v in pose.split(","))
    c.set_editor_property("fov_angle", fov)
    cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False, False)
    for _ in range(40):
        c.capture_scene()
    perf = unreal.get_default_object(unreal.EditorPerformanceSettings)
    throttle = perf.get_editor_property("throttle_cpu_when_not_foreground")
    perf.set_editor_property("throttle_cpu_when_not_foreground", False)
    state = {"i": 0, "times": []}

    def tick(dt):
        done = True
        try:
            c.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"{name}_t{state['i']:03d}.png")
            state["times"].append(unreal.GameplayStatics.get_time_seconds(world))
            state["i"] += 1
            done = state["i"] >= n
        finally:
            if done:
                unreal.unregister_slate_post_tick_callback(state["handle"])
                perf.set_editor_property("throttle_cpu_when_not_foreground", throttle)
                finish()
                open(f"{OUT}/{name}_times.txt", "w").write("\n".join(f"{t:.4f}" for t in state["times"]))

    state["handle"] = unreal.register_slate_post_tick_callback(tick)
    print("ticking", n, "frames of", name, "to", OUT)


ticking = False
try:
    if E.get("TICKS"):
        ticks(int(E["TICKS"]))
        ticking = True
    else:
        burst = [float(v) for v in E["BURST"].split(",")] if E.get("BURST") else None
        for shot in E["SHOTS"].split(";"):
            name, pose = shot.split("@")
            x, y, z, pitch, yaw, fov = (float(v) for v in pose.split(","))
            c.set_editor_property("fov_angle", fov)
            cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False, False)
            for _ in range(40):  # settle eye adaptation, Lumen's surface cache and temporal history on a still camera
                c.capture_scene()
            if not burst:
                unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
                print("shot", f"{OUT}/{name}.png")
                continue
            dx, dy, dz, dyaw, frames = burst
            seq = [dict(kv.split("=") for kv in step.split(",")) for step in E["SEQ"].split(";")] if E.get("SEQ") else []
            for i in range(int(frames)):
                x, y, z, yaw = x + dx, y + dy, z + dz, yaw + dyaw
                for k, v in (seq[i % len(seq)] if seq else {}).items():  # SEQ="RetroMix=1|0|0|0;RetroMix=0|1|0|.5" per frame
                    saved_v.setdefault(k, KML.get_vector_parameter_value(world, mpc, k))
                    KML.set_vector_parameter_value(world, mpc, k, unreal.LinearColor(*(float(c) for c in v.split("|"))))
                cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False, False)
                c.capture_scene()
                unreal.RenderingLibrary.export_render_target(world, rt, OUT, f"{name}_{i}.png")
                print("burst", f"{OUT}/{name}_{i}.png")

finally:
    if not ticking:
        finish()
