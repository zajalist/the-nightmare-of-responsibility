"""Aholo World generation (SpatialGen): one text prompt -> 3DGS SPZ + 360 panorama.

  python Tools/Lux3D/aholo_world.py dream_a "PROMPT"   # creates ONE world (30 credits), polls, downloads
  python Tools/Lux3D/aholo_world.py dream_a            # re-run: polls the recorded worldId, never creates again

Key: as lux3d_batch.py (never printed). Output: P:/FoA-Assets/level2/aholo/<name>/ with world.spz, pano.<ext> and
world.json (worldId, raw list before/after, raw final detail: the API has no credits endpoint, so these raw bodies
are the only charge evidence). A create that times out is recorded as 'unknown' and never retried: check
POST /global/world/v1/list before trying again. API facts: docs/design/level2/splat_feasibility.md section 1.
"""
import json
import os
import sys
import time
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lux3d_batch import Api, load_key  # noqa: E402

BASE = "https://api.aholo.ai/global/world/v1"
OUT = "P:/FoA-Assets/level2/aholo"
POLL_S = 12
TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED", "TIMEOUT", "REJECTED"}


def call(api, method, url, body=None):
    """(http_status, json body). World reports errors as HTTP 4xx with an ApiError body."""
    try:
        return 200, api._call(method, url, body)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")


def main():
    name, prompt = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    state_path = os.path.join(folder, "world.json")
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}
    save = lambda: json.dump(state, open(state_path, "w", encoding="utf-8"), indent=1)  # noqa: E731
    api = Api(load_key())
    if "worldId" not in state:
        if state.get("status") == "unknown":
            sys.exit("a previous create timed out: check /world/v1/list before creating again")
        if not prompt:
            sys.exit("no worldId recorded and no prompt given")
        state["list_before"] = call(api, "POST", f"{BASE}/list", {"pageNum": 0, "pageSize": 20})
        try:
            code, resp = call(api, "POST", f"{BASE}/generations", {"name": f"FoA L2 {name}", "prompt": prompt})
        except (urllib.error.URLError, TimeoutError) as e:
            state.update(status="unknown", error=str(e), prompt=prompt)  # may have been charged: never retry
            save()
            sys.exit(f"create timed out ({e}); recorded as unknown")
        state.update(prompt=prompt, create=[code, resp], created=time.strftime("%Y-%m-%d %H:%M:%S"))
        if code != 200 or "worldId" not in resp:
            save()
            sys.exit(f"create failed: HTTP {code} {resp}")
        state["worldId"] = resp["worldId"]
        save()
        print("created", state["worldId"])
    last = None
    while True:
        code, d = call(api, "GET", f"{BASE}/{state['worldId']}")
        status = d.get("status")
        if (status, d.get("progress")) != last:
            print(time.strftime("%H:%M:%S"), code, status, d.get("progress"))
            last = (status, d.get("progress"))
        if status in TERMINAL or code != 200:
            break
        time.sleep(POLL_S)
    state.update(detail=d, status=status)
    if status == "SUCCEEDED":
        urls = (d.get("assets") or {})
        spz = ((urls.get("splats") or {}).get("urls") or {}).get("spzPath")
        pano = (urls.get("imagery") or {}).get("panoUrl")
        for url, stem in ((spz, "world"), (pano, "pano")):
            if url:
                ext = os.path.splitext(url.split("?")[0])[1] or ".bin"
                api.download(url, os.path.join(folder, stem + ext))
                print("downloaded", stem + ext)
        state["list_after"] = call(api, "POST", f"{BASE}/list", {"pageNum": 0, "pageSize": 20})
    save()


if __name__ == "__main__":
    main()
