"""Previz / review stills of LS_WakeUp: one frame per shot, through the shot's own cine camera.
  $env:FOA_AREAS='Cinematics'; $env:FOA_ACTORS_NEW='CINE_'
  python Tools/Unreal/ue_remote.py Tools/Unreal/cine/previz_stills.py [FOA_SHOTS=name@seconds,...] [FOA_OUT=dir]
Opens LS_WakeUp in Sequencer (viewport lock off), scrubs to each time, copies the spawned camera's transform, FOV,
focus and aperture onto a temporary SceneCapture2D (final colour, the level's own post process and exposure),
writes <out>/<name>.png, then destroys the capture and closes Sequencer. Steps run on later ticks (pose and groom
updates need a frame); "[cine] stills done" in the log marks the end (about 2 s per shot)."""
import os
import time

import unreal

SEQ = "/Game/FoA/Cinematics/LS_WakeUp"
OUT = os.environ.get("FOA_OUT", "P:/FoA/Saved/Cinematics/previz")
DEFAULT = "2_POV@5.9,2b_POV_clock@8.8,3_Wide@11.0,4_PushIn@19.0,5_TwoShot@22.0,6_Insert@25.8,7_Stand@32.5,8_HandBack@34.2"
SHOTS = [(s.split("@")[0], float(s.split("@")[1])) for s in os.environ.get("FOA_SHOTS", DEFAULT).split(",") if s]
# Free views for blocking: FOA_VIEWS="name@t@x,y,z@pitch,yaw@hfov;..." replaces the shot cameras.
VIEWS = {v.split("@")[0]: [float(c) for c in ",".join(v.split("@")[2:]).split(",")]
         for v in os.environ.get("FOA_VIEWS", "").split(";") if v}
if VIEWS:
    SHOTS = [(v.split("@")[0], float(v.split("@")[1])) for v in os.environ["FOA_VIEWS"].split(";") if v]
CAM = {"2": "Cam_POV", "3": "Cam_Wide", "4": "Cam_PushIn", "5": "Cam_TwoShot", "6": "Cam_Insert", "7": "Cam_Stand",
       "8": "Cam_HandBack"}
LSB = unreal.LevelSequenceEditorBlueprintLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
os.makedirs(OUT, exist_ok=True)

seq = unreal.load_asset(SEQ)
LSB.open_level_sequence(seq)
LSB.set_lock_camera_cut_to_viewport(False)
cap = EAS.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 150), unreal.Rotator())
cap.set_actor_label("CINE_TMP_Capture")
comp = cap.capture_component2d
rt = unreal.RenderingLibrary.create_render_target2d(world, 1920, 1080, unreal.TextureRenderTargetFormat.RTF_RGBA8)
comp.set_editor_property("texture_target", rt)
comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
comp.set_editor_property("capture_every_frame", False)
comp.set_editor_property("always_persist_rendering_state", True)
state = {"i": 0, "phase": 0, "t": time.time(), "handle": None}


def camera(name):
    """Sequencer's spawned camera keeps its template's label (CINE_<shot>), not the binding name (Cam_<shot>)."""
    shot = name.split("_", 1)[1]
    cams = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CineCameraActor)
    for a in cams:
        if a.get_actor_label() in ("CINE_" + shot, name):
            return a
    unreal.log_warning("[cine] cine cameras present: %s" % [a.get_actor_label() for a in cams])
    return None


def mirror(cam):
    cc = cam.get_cine_camera_component()
    cap.set_actor_location_and_rotation(cam.get_actor_location(), cam.get_actor_rotation(), False, True)
    comp.set_editor_property("fov_angle", cc.get_horizontal_field_of_view())
    pp = comp.get_editor_property("post_process_settings")
    fs = cc.get_editor_property("focus_settings")
    for prop, val in (("depth_of_field_fstop", cc.get_editor_property("current_aperture")),
                      ("depth_of_field_focal_distance", fs.get_editor_property("manual_focus_distance")),
                      ("depth_of_field_sensor_width", cc.get_editor_property("filmback").get_editor_property("sensor_width"))):
        pp.set_editor_property("override_" + prop, True)
        pp.set_editor_property(prop, val)
    cpp = cc.get_editor_property("post_process_settings")
    if cpp.get_editor_property("override_vignette_intensity"):
        pp.set_editor_property("override_vignette_intensity", True)
        pp.set_editor_property("vignette_intensity", cpp.get_editor_property("vignette_intensity"))
    comp.set_editor_property("post_process_settings", pp)


def finish():
    unreal.unregister_slate_post_tick_callback(state["handle"])
    EAS.destroy_actor(cap)
    LSB.close_level_sequence()
    unreal.log("[cine] stills done")


def tick(_dt):
    now = time.time()
    if state["i"] >= len(SHOTS) or now - state["t"] > 90:
        finish()
        return
    name, t = SHOTS[state["i"]]
    if state["phase"] == 0:  # scrub; the pose lands on a later frame
        LSB.set_current_time(int(round(t * 30)))
        state["phase"], state["t0"] = 1, now
    elif state["phase"] == 1 and now - state["t0"] > 1.2 and name in VIEWS:
        x, y, z, pit, yaw, fov = VIEWS[name]
        cap.set_actor_location_and_rotation(unreal.Vector(x, y, z), unreal.Rotator(pitch=pit, yaw=yaw, roll=0.0), False, True)
        comp.set_editor_property("fov_angle", fov)
        for _ in range(3):
            comp.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
        state["i"] += 1
        state["phase"] = 0
    elif state["phase"] == 1 and now - state["t0"] > 1.2:
        cam = camera(CAM.get(name[0], "Cam_None"))
        if cam is None:
            unreal.log_warning("[cine] no camera for %s" % name)
        else:
            mirror(cam)
            for _ in range(3):  # warm-up captures (temporal AA, eye adaptation)
                comp.capture_scene()
            unreal.RenderingLibrary.export_render_target(world, rt, OUT, name + ".png")
            unreal.log("[cine] still %s at %.1f" % (name, t))
        state["i"] += 1
        state["phase"] = 0


state["handle"] = unreal.register_slate_post_tick_callback(tick)
