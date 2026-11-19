"""Perf lane: one short PIE burst that averages the stats hierarchy and logs frame times, then ends PIE itself.
  editor_lock.py acquire perf ; FOA_EXCLUSIVE=1 ue_remote.py Tools/Unreal/perf_pie.py [FOA_PIE_S=30] ; release
Returns at once; the frame times and 'stat dumpave' land in the log (grep 'perfpie' and 'LogStats')."""
import os
import time

import unreal

LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
S = {"t0": time.time(), "dts": [], "stat": False, "end": float(os.environ.get("FOA_PIE_S", "30"))}


def tick(dt):
    t = time.time() - S["t0"]
    if t > 6 and UES.get_game_world():  # skip PIE startup
        S["dts"].append(dt * 1000.0)
        if not S["stat"]:
            S["stat"] = True
            unreal.SystemLibrary.execute_console_command(UES.get_game_world(), "stat dumpave -num=150 -ms=0.5")
    if t > S["end"]:
        unreal.unregister_slate_post_tick_callback(S["h"])
        d = sorted(S["dts"]) or [0.0]
        print(f"perfpie: frames={len(d)} avg_ms={sum(d) / len(d):.1f} p50={d[len(d) // 2]:.1f} "
              f"p95={d[int(len(d) * 0.95)]:.1f} max={d[-1]:.1f}")
        if UES.get_game_world():
            LES.editor_request_end_play()


LES.editor_request_begin_play()
S["h"] = unreal.register_slate_post_tick_callback(tick)
print("perfpie: PIE begin requested")
