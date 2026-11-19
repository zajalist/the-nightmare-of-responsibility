"""Titles-only tidy of M_Fireplace's comment boxes (the user's rule: short titles, no descriptions), through Hayba.
  $env:HAYBA_AGENT_ID='fireplace'; python Tools/Unreal/editor_lock.py acquire fireplace --assets /Game/FoA/Fireplace
  python Tools/Fireplace/tidy_fireplace_material.py; python Tools/Unreal/editor_lock.py release fireplace"""
import json
import sys
import time

sys.path.insert(0, "P:/FoA/Tools/Unreal")
from hayba_call import call  # noqa: E402

MAT = "/Game/FoA/Fireplace/Materials/M_Fireplace"
TITLES = {"Textures": "Textures", "Masks": "Masks", "Base colour": "Base Colour", "Roughness and metallic": "Roughness and Metallic"}


def hc(cmd, params):
    for attempt in range(6):
        try:
            return call(cmd, params, timeout=60)
        except (ConnectionError, OSError) as e:
            print("retry", cmd, e)
            time.sleep(5 + 5 * attempt)
    raise RuntimeError(cmd + ": Hayba unreachable")


info = hc("material_get_info", {"path": MAT})["data"]
for c in info.get("comments", []):
    old = c.get("text", "")
    title = next((t for prefix, t in TITLES.items() if old.startswith(prefix)), None)
    if not title or old == title:
        continue
    r = None
    for key in ("comment_id", "node_id"):
        r = hc("material_set_comment", {"material_path": MAT, key: c["id"], "text": title})
        if r.get("ok"):
            break
    print(c["id"], "->", title, r.get("ok"), r.get("error"))
v = hc("material_validate", {"material_path": MAT})
print("validate", json.dumps(v.get("data"))[:200])
if (v.get("data") or {}).get("ok") is False:
    sys.exit("validation failed")
c = hc("material_compile", {"material_path": MAT})
d = c.get("data") or {}
print("compile ok", d.get("ok"), "saved", d.get("saved"), "errors", d.get("errors"))
