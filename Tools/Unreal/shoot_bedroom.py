"""Opens the bedroom, waits for shaders, takes reference shots from the Dev/ShotCameras, then quits.
  UnrealEditor.exe P:/FoA/FoA.uproject -ExecCmds="py P:/FoA/Tools/Unreal/shoot_bedroom.py"
Use -ExecCmds, not -ExecutePythonScript: the latter closes the editor as soon as the script returns,
before the tick callback below gets to run.
Shots land in Saved/Screenshots/. Nothing is saved to the level."""
import os
import time

import unreal

LEVEL = "/Game/FoA/Maps/L_Tutorial_Bedroom"
SHOTS = ["Shot_ThirdPerson", "Shot_Wide", "Shot_Window", "Shot_TopDown"]
WAIT_FOR_SHADERS_S = float(os.environ.get("FOA_SHOT_WAIT", "75"))
GAP_S = 8.0

LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

LES.load_level(LEVEL)
actors = EAS.get_all_level_actors()
cams = {a.get_actor_label(): a for a in actors if isinstance(a, unreal.CameraActor)}
ceiling = [a for a in actors if a.get_actor_label() == "Ceiling"]
state = {"t0": time.time(), "i": 0, "next": WAIT_FOR_SHADERS_S, "done": None, "handle": None, "busy": False}
# extra frames before each capture so Lumen/TSR history settles (less noise)
unreal.SystemLibrary.execute_console_command(None, "r.HighResScreenshotDelay 24")


def tick(_dt):
    # take_high_res_screenshot pumps Slate, which re-enters this callback; ignore nested calls
    if state["busy"]:
        return
    elapsed = time.time() - state["t0"]
    if state["done"] is not None:
        if elapsed > state["done"] + 12.0:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.SystemLibrary.quit_editor()
        return
    if elapsed < state["next"]:
        return
    if state["i"] >= len(SHOTS):
        state["done"] = elapsed
        return
    name = SHOTS[state["i"]]
    state["i"] += 1
    state["next"] = elapsed + GAP_S
    state["busy"] = True
    try:
        for c in ceiling:  # top-down looks through the ceiling, like the in-game cutaway will
            c.set_actor_hidden_in_game(name == "Shot_TopDown")
        cam = cams.get(name)
        if cam:
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, f"FoA_{name}.png", camera=cam)
            unreal.log(f"[FoA] requested {name}")
        else:
            unreal.log_warning(f"[FoA] missing camera {name}")
    finally:
        state["busy"] = False


state["handle"] = unreal.register_slate_post_tick_callback(tick)
