"""Perf lane: list leftover Python callables from ue_remote scripts and the open asset editors; optionally
turn off the background CPU throttle (3 fps cap when the editor is not the foreground window).
  python Tools/Unreal/ue_remote.py Tools/Unreal/perf_inventory.py [FOA_THROTTLE=0|1]
Read-only unless FOA_THROTTLE is given."""
import gc
import os
import sys
from collections import Counter

import unreal

perf = unreal.find_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")  # class not exposed to Python
PROP = "bThrottleCPUWhenNotForeground"  # Python-name lookup fails for this class; the native name works
if os.environ.get("FOA_THROTTLE") in ("0", "1"):
    perf.set_editor_property(PROP, os.environ["FOA_THROTTLE"] == "1")
print(PROP, "=", perf.get_editor_property(PROP))

# Functions still alive after their exec'd script finished are held by C++ (tick callbacks, delegates).
module_files = {os.path.normcase(getattr(m, "__file__", "") or "") for m in list(sys.modules.values())}
me = os.path.normcase(__file__)
live = Counter()
for obj in gc.get_objects():
    code = getattr(obj, "__code__", None)
    if code is None or not callable(obj):
        continue
    f = os.path.normcase(code.co_filename)
    if f in module_files or f == me or f.startswith("<") or "python3" in f or "\\engine\\" in f:
        continue
    g = getattr(obj, "__globals__", {})
    handles = [f"{k}.{hk}" for k, v in g.items() if isinstance(v, dict) for hk in v if hk in ("h", "handle")]
    live[(code.co_filename, obj.__name__, ",".join(handles))] += 1
print("leftover script callables:", sum(live.values()))
for (f, name, handles), n in sorted(live.items()):
    print(f"  {n}x {name} in {f} handles=[{handles}]")

aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
edited = aes.get_all_edited_assets()
dirty = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
print("open asset editors:", len(edited), "dirty packages:", len(dirty))
for a in edited:
    print("  ", a.get_path_name(), "DIRTY" if a.get_path_name().split(".")[0] in dirty else "")
