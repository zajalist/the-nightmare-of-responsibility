"""Reference shots from the Dev/ShotCameras inside an open editor; never reloads the level or quits.
  python Tools/Unreal/ue_remote.py Tools/Unreal/shoot_live.py
Shots land in Saved/Screenshots/WindowsEditor/FoA_<camera>.png about 30 s later (they're taken on later ticks)."""
import os
import time

import unreal

SHOTS = [s for s in os.environ.get("FOA_SHOTS", "").split(",") if s] or \
        ["Shot_ThirdPerson", "Shot_Wide", "Shot_Window", "Shot_TopDown"]
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = EAS.get_all_level_actors()
cams = {a.get_actor_label(): a for a in actors if isinstance(a, unreal.CameraActor)}
ceiling = [a for a in actors if a.get_actor_label() == "Ceiling"]
unreal.SystemLibrary.execute_console_command(None, "r.HighResScreenshotDelay 24")
SHOT_DIR = os.path.join(unreal.Paths.project_saved_dir(), "Screenshots", "WindowsEditor")
state = {"t0": time.time(), "i": 0, "next": 4.0, "busy": False, "handle": None, "waiting": None}


def tick(_dt):
    if state["busy"]:  # taking a shot pumps Slate and re-enters this callback
        return
    elapsed = time.time() - state["t0"]
    # An unfocused editor ticks slowly; a new request cancels the pending one, so wait for each file to land.
    if state["waiting"]:
        path, asked = state["waiting"]
        if not (os.path.exists(path) and os.path.getmtime(path) >= asked) and elapsed - (asked - state["t0"]) < 60:
            return
        state["waiting"] = None
        state["next"] = elapsed + 1.0
    if elapsed < state["next"]:
        return
    if state["i"] >= len(SHOTS):
        for c in ceiling:
            c.set_actor_hidden_in_game(False)
        unreal.unregister_slate_post_tick_callback(state["handle"])
        unreal.log("[FoA] shots done")
        return
    name = SHOTS[state["i"]]
    state["i"] += 1
    state["next"] = elapsed + 6.0
    state["busy"] = True
    try:
        for c in ceiling:
            c.set_actor_hidden_in_game(name == "Shot_TopDown")
        if name in cams:
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, f"FoA_{name}.png", camera=cams[name])
            state["waiting"] = (os.path.join(SHOT_DIR, f"FoA_{name}.png"), time.time())
    finally:
        state["busy"] = False


state["handle"] = unreal.register_slate_post_tick_callback(tick)
print("scheduled", len(SHOTS), "shots")
