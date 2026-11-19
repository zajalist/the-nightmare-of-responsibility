"""One-off repair: tick callbacks registered by scripts whose globals were cleared (ue_remote isolation bug, Nov 5)
throw NameError every frame. Give them a 'busy' state so they return immediately; a restart removes them for good."""
import gc

patched = 0
for obj in gc.get_objects():
    code = getattr(obj, "__code__", None)
    if code is None or not callable(obj) or getattr(obj, "__name__", "") != "tick":
        continue
    if code.co_filename.replace("\\", "/").endswith("shoot_live.py") and "state" not in obj.__globals__:
        obj.__globals__["state"] = {"busy": True}
        patched += 1
print("orphan tick callbacks neutralized:", patched)
