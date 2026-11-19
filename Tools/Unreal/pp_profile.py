"""GPU cost of the dream post-process (post-process lane). No helper actors (editor-rules): it profiles the editor
viewport's next frame, then parse_profile() in plain Python reads the PostProcessMaterial passes from Saved/Logs/FoA.log
and scales them to 1920x1080 by pixel count.
  python Tools/Unreal/ue_remote.py Tools/Unreal/pp_profile.py        (inside the pp hold)
  python Tools/Unreal/pp_profile.py parse                            (a few seconds later, outside the editor)"""
import re
import sys


def request():
    import unreal
    unreal.SystemLibrary.execute_console_command(None, "r.ProfileGPU.ShowUI 0")  # log only: no Visualizer window
    unreal.SystemLibrary.execute_console_command(None, "profilegpu")
    print("profilegpu requested for the next frame")


def parse(log="P:/FoA/Saved/Logs/FoA.log"):
    text = open(log, encoding="utf-8", errors="ignore").read()
    block = text[text.rfind("Profiling the next GPU frame"):]
    rows = [l for l in block.splitlines() if re.search(r"PostProcess|M_PP_Dream|Tonemap|Bloom|DOF|TSR|TemporalSuper|MotionBlur", l)]
    for l in rows[:60]:
        print(l[:220])
    return rows


if __name__ == "__main__":
    parse() if "parse" in sys.argv else None
else:
    request()
