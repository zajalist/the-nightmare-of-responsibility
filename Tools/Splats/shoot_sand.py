"""Motion frames of the sand VFX: several high-res shots a few seconds apart from fixed poses, so the stream, the
mound flow and the clock's assemble loop can be compared over time. Same tick pattern as Tools/Unreal/shoot_live.py.
  python Tools/Unreal/ue_remote.py Tools/Splats/shoot_sand.py FOA_SAND_SHOTS=stream,clock FOA_SAND_FRAMES=4
      [FOA_SAND_RES=1920x1080]   (gizmo-free stills and the clock loop: sand_capture.py)
Shots land in Saved/Screenshots/WindowsEditor/FoA_sand_<pose>_<k>.png. A temporary camera actor (_SandShotCam) is
spawned for the poses and destroyed afterwards.
"""
import os
import time

import unreal

POSES = {  # location, (pitch, yaw), fov
    "stream": ((-30.0, 105.0, 150.0), (-24.6, 131.5), 55.0),
    "streamlow": ((-95.0, 160.0, 60.0), (-8.0, 118.0), 60.0),
    "clock": ((-92.0, 178.0, 163.0), (-12.5, 124.0), 50.0),
    "bay": ((40.0, -195.0, 95.0), (-26.3, -124.6), 55.0),
    "path": ((240.0, -120.0, 80.0), (-31.9, 138.4), 55.0),
    "hearth": ((-170.0, -40.0, 90.0), (-30.6, -140.7), 55.0),
    "streamside": ((60.0, 210.0, 70.0), (-1.4, 173.9), 60.0),        # backlit by the desk lamp: the stream in silhouette
    "stream34": ((-60.0, 120.0, 110.0), (-19.5, 127.5), 60.0),
    "pathlow": ((235.0, -95.0, 45.0), (-18.0, 147.0), 50.0),
    "hearthlow": ((-185.0, -60.0, 55.0), (-17.0, -143.0), 50.0),
    "gameplay": ((-40.0, 20.0, 175.0), (-25.6, 116.2), 90.0),          # third-person height, ~2.5 m from the commode
    "thirdperson": ((-60.0, -60.0, 175.0), (-8.1, 18.7), 90.0),        # Dev/ShotCameras Shot_ThirdPerson
}
NAMES = [s for s in os.environ.get("FOA_SAND_SHOTS", "stream,clock").split(",") if s in POSES]
FRAMES = int(os.environ.get("FOA_SAND_FRAMES", "4"))
GAP = float(os.environ.get("FOA_SAND_GAP", "2.5"))
W, H = (int(v) for v in os.environ.get("FOA_SAND_RES", "1280x720").split("x"))
SHOT_DIR = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "WindowsEditor")
unreal.SystemLibrary.execute_console_command(None, "r.HighResScreenshotDelay 8")
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
cam = EAS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, 200))
cam.set_actor_label("_SandShotCam")
cam.set_folder_path("FX/Sand")
plan = [(n, k) for n in NAMES for k in range(FRAMES)]
state = {"t0": time.time(), "i": 0, "next": 2.0, "busy": False, "handle": None, "waiting": None, "cam": cam}


def tick(_dt):
    if state["busy"]:  # a shot pumps Slate and re-enters this callback
        return
    elapsed = time.time() - state["t0"]
    if state["waiting"]:
        path, asked = state["waiting"]
        if not (os.path.exists(path) and os.path.getmtime(path) >= asked) and elapsed - (asked - state["t0"]) < 60:
            return
        state["waiting"] = None
    if elapsed < state["next"]:
        return
    if state["i"] >= len(plan):
        unreal.unregister_slate_post_tick_callback(state["handle"])
        EAS.destroy_actor(state["cam"])
        state["cam"] = None
        unreal.log("[FoA] sand shots done")
        return
    name, k = plan[state["i"]]
    state["i"] += 1
    loc, (pitch, yaw), fov = POSES[name]
    c = state["cam"]
    c.set_actor_location(unreal.Vector(*loc), False, False)
    c.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False)
    c.camera_component.set_editor_property("field_of_view", fov)
    state["next"] = elapsed + GAP
    state["busy"] = True
    try:
        fname = f"FoA_sand_{name}_{k}.png"
        unreal.AutomationLibrary.take_high_res_screenshot(W, H, fname, camera=c)
        state["waiting"] = (os.path.join(SHOT_DIR, fname), time.time())
    finally:
        state["busy"] = False


state["handle"] = unreal.register_slate_post_tick_callback(tick)
print("scheduled", len(plan), "sand shots:", NAMES)
