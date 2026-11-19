"""Batch-generate assets with Aholo Lux3D from the prompt table in docs/lux3d-bedroom-prompts.md.

  python Tools/Lux3D/lux3d_batch.py --dry-run                      # show what would be sent, no API calls
  python Tools/Lux3D/lux3d_batch.py --only "Single bed,Chest of drawers"
  python Tools/Lux3D/lux3d_batch.py --selftest                     # offline check of the task state machine
  python Tools/Lux3D/lux3d_batch.py --retopo hooded_figure_b:15000  # Lux3D retopology of a finished job's GLB
  python Tools/Lux3D/lux3d_batch.py --rig hooded_figure_b_retopo    # Lux3D humanoid auto-rig of a finished job's GLB

API key: env LUX3D_API_KEY, or the file ~/.foa/lux3d_api_key. Never commit it.
Results: <out>/<item>/ (default P:/FoA-Assets/lux3d). Task ids are kept in <out>/_state.json so a re-run polls
existing tasks instead of creating (and paying for) new ones. API facts: P:/FoA-Assets/lux3d-api-notes.md.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://api.aholo.ai/global/lux3d/v1"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE = os.path.join(REPO, "docs", "lux3d-bedroom-prompts.md")
MAX_IN_FLIGHT = 3      # free accounts allow 5 concurrent tasks; leave room for other tools on the same key
POLL_S = 12            # docs: poll every 10-15 s
DEFAULT_FACES = 30000  # keeps meshes inside the <1 GB game budget; docs allow 10000-300000
DONE, FAILED, UNKNOWN = "done", "failed", "unknown"
TEXT_TO_3D = "/generate/text-to-3d/task/create"
RETOPO = "/mesh-retopology/task/create"
RIG = "/animations/rig/task/create"
RETARGET = "/animations/retarget/task/create"


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_table(path):
    """Rows of the markdown table: | Item | Beat | Version | Prompt | After generation |"""
    jobs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("|") or line.startswith("|---") or line.startswith("| Item"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 4 or not cells[3]:
                continue
            item, _beat, version, prompt = cells[:4]
            jobs.append({"name": slug(item), "item": item, "body": row_body(version, prompt)})
    return jobs


def row_body(version, prompt):
    """Version cell: 'G1', 'G1-Turbo PLY', or G1 with overrides like 'G1 300k 1800mm' (faces, height in mm)."""
    if "PLY" in version:
        return {"prompt": prompt, "version": "G1-Turbo", "outputFormat": ["ply"]}
    faces = re.search(r"(\d+)k\b", version)
    body = {"prompt": prompt, "version": "G1", "faceCount": int(faces.group(1)) * 1000 if faces else DEFAULT_FACES,
            "outputFormat": ["glb"]}
    height = re.search(r"(\d+)\s*mm\b", version)
    if height:
        body["customSize"] = int(height.group(1))
    return body


def post_job(state, kind, spec):
    """A retopo ('NAME[:QUAD_FACES[:TEXTURE_SIZE]]'), rig ('NAME') or retarget ('NAME:Anim+Anim') job on the GLB of a
    finished job in state. Retarget takes a rig job's output and returns in-place FBX clips, one file per action."""
    src, _, rest = spec.partition(":")
    faces, _, tex = rest.partition(":")
    urls = state.get(src, {}).get("urls") or []
    url = next((u for u in urls if u.split("?")[0].lower().endswith(".glb")), None)
    if kind == "retarget":
        url = url or next((u for u in urls if u.startswith("http")), None)  # a rig output may not end in .glb
    if not url:
        sys.exit(f"{src}: no GLB url in _state.json (job not done, or done before urls were recorded)")
    if kind == "retarget":
        body = {"rigModelUrl": url, "animationIds": rest.split("+"), "animationOutputMode": "separate",
                "outFormat": "fbx", "animateInPlace": True}
        return {"name": f"{src}_anim", "item": f"{src} {rest}", "endpoint": RETARGET, "body": body}
    if kind == "retopo":
        # quad faceLimit ~ half the game triangles; baked 2k BaseColor/Metal/Rough ~ 1024 px/m on a human
        body = {"modelUrl": url, "faceLimit": int(faces or 15000), "quad": True, "bakeTextures": True,
                "textureSize": int(tex or 2048)}
        return {"name": f"{src}_retopo", "item": f"{src} retopo", "endpoint": RETOPO, "body": body}
    return {"name": f"{src}_rig", "item": f"{src} rig", "endpoint": RIG, "body": {"modelUrl": url}}


class Api:
    def __init__(self, key):
        self.key = key

    def _call(self, method, url, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": self.key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    def create(self, body, endpoint=TEXT_TO_3D):
        return self._call("POST", BASE + endpoint, body)

    def get(self, task_id):
        return self._call("GET", f"{BASE}/generate/task/get?taskid={task_id}")

    def download(self, url, dest):
        # Docs don't say whether output URLs need auth; try plain first, then with the key.
        for headers in ({}, {"Authorization": self.key}):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=300) as r, \
                        open(dest, "wb") as fh:
                    fh.write(r.read())
                return
            except urllib.error.HTTPError as e:
                if e.code not in (401, 403):
                    raise
        raise RuntimeError(f"download refused: {url}")


def run(jobs, api, out_dir, state_path, poll_s=POLL_S, sleep=time.sleep, log=print):
    state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}

    def save():
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)

    queue = [j for j in jobs if j["name"] not in state]
    inflight = [j for j in jobs if state.get(j["name"], {}).get("status") == "running"]
    while queue or inflight:
        while queue and len(inflight) < MAX_IN_FLIGHT:
            job = queue[0]
            try:
                resp = api.create(job["body"], job.get("endpoint", TEXT_TO_3D))
            except (urllib.error.URLError, TimeoutError) as e:
                # A timed-out create may still have been charged: never retry it automatically.
                state[job["name"]] = {"status": UNKNOWN, "error": str(e)}
                save()
                queue.pop(0)
                log(f"[{job['name']}] create timed out; check the task list before retrying ({e})")
                continue
            if resp.get("c") == "GENERATION_CONCURRENCY_LIMIT_EXCEEDED":
                break  # wait for a running task to finish
            queue.pop(0)
            if resp.get("c") != "0":
                state[job["name"]] = {"status": FAILED, "error": f"{resp.get('c')}: {resp.get('m')}"}
                log(f"[{job['name']}] create failed: {resp.get('c')} {resp.get('m')}")
            else:
                state[job["name"]] = {"status": "running", "task": resp["d"], "item": job["item"]}
                inflight.append(job)
                log(f"[{job['name']}] task {resp['d']} created")
            save()
        sleep(poll_s)  # also when the account is at its concurrency limit with nothing of ours in flight
        if not inflight:
            continue
        for job in list(inflight):
            entry = state[job["name"]]
            d = (api.get(entry["task"]) or {}).get("d") or {}
            status = d.get("status")
            if status in (0, 1, None):
                continue
            inflight.remove(job)
            if status != 3:
                # failed rig/retopo tasks put an error JSON string in outputs[].content
                entry.update(status=FAILED, error=f"task status {status}: {d.get('outputs')}")
                log(f"[{job['name']}] task {entry['task']} ended with status {status}")
            else:
                folder = os.path.join(out_dir, job["name"])
                os.makedirs(folder, exist_ok=True)
                files, urls, errors = [], [], []
                for o in d.get("outputs") or []:
                    content = (o or {}).get("content") or ""
                    named = [(content, os.path.basename(content.split("?")[0]))] if content.startswith("http") else []
                    if content.startswith("{"):  # retarget: a JSON object with one entry per action
                        for a in json.loads(content).get("actions") or []:
                            u = a.get("animationGlbUrl") or a.get("fbxUrl") or ""
                            if a.get("status") == "success" and u.startswith("http"):
                                named.append((u, a["animation_id"] + os.path.splitext(u.split("?")[0])[1]))
                            else:
                                errors.append(f"{a.get('animation_id')}: {a.get('error')}")
                    for url, base in named:  # NOT_REQUESTED / "null" placeholders give nothing
                        dest = os.path.join(folder, base or f"output_{len(files)}")
                        api.download(url, dest)
                        files.append(dest)
                        urls.append(url)
                # urls stay valid for 2 h: long enough to chain retopology / auto-rig without re-uploading
                entry.update(status=DONE, files=files, urls=urls, finished=time.strftime("%Y-%m-%d %H:%M:%S"))
                if errors:
                    entry["errors"] = errors
                log(f"[{job['name']}] done: {', '.join(os.path.basename(f) for f in files)}")
            save()
    return state


def selftest():
    import tempfile

    class FakeApi:
        def __init__(self):
            self.created, self.polls, self.busy_once = 0, {}, True

        def create(self, body, endpoint=TEXT_TO_3D):
            if self.busy_once:
                self.busy_once = False
                return {"c": "GENERATION_CONCURRENCY_LIMIT_EXCEEDED", "d": None}
            self.created += 1
            return {"c": "0", "d": 1000 + self.created}

        def get(self, task_id):
            n = self.polls[task_id] = self.polls.get(task_id, 0) + 1
            if n < 2:
                return {"c": "0", "d": {"taskId": task_id, "status": 1, "outputs": []}}
            if task_id == 1002:
                return {"c": "0", "d": {"taskId": task_id, "status": 4}}
            return {"c": "0", "d": {"taskId": task_id, "status": 3, "outputs": [
                {"content": f"https://x/{task_id}/results.zip"}, {"content": f"https://x/{task_id}/pbr_mesh.glb"},
                {"content": "NOT_REQUESTED"}]}}

        def download(self, url, dest):
            open(dest, "wb").close()

    jobs = [{"name": n, "item": n, "body": {"prompt": n, "version": "G1"}} for n in ("bed", "door", "lamp")]
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, "_state.json")
        api = FakeApi()
        state = run(jobs, api, tmp, state_path, sleep=lambda s: None, log=lambda m: None)
        assert state["bed"]["status"] == DONE and len(state["bed"]["files"]) == 2, state["bed"]
        assert state["door"]["status"] == FAILED, state["door"]
        assert state["lamp"]["status"] == DONE
        before = api.created
        run(jobs, api, tmp, state_path, sleep=lambda s: None, log=lambda m: None)
        assert api.created == before, "re-run must not create (pay for) tasks again"
    table_jobs = parse_table(TABLE)
    assert table_jobs and all(j["body"]["prompt"] for j in table_jobs)
    assert any(j["body"]["outputFormat"] == ["ply"] for j in table_jobs)
    hero = row_body("G1 300k 1800mm", "p")
    assert hero["faceCount"] == 300000 and hero["customSize"] == 1800, hero
    plain = row_body("G1", "p")
    assert plain["faceCount"] == DEFAULT_FACES and "customSize" not in plain, plain
    st = {"fig": {"status": DONE, "urls": ["https://x/a/result.zip", "https://x/a/textured.glb?sig=1"]}}
    rt = post_job(st, "retopo", "fig:12000")
    assert rt["endpoint"] == RETOPO and rt["body"]["modelUrl"].endswith("sig=1") and rt["body"]["faceLimit"] == 12000
    assert rt["body"]["textureSize"] == 2048 and post_job(st, "retopo", "fig:5200:1024")["body"]["textureSize"] == 1024
    assert post_job(st, "rig", "fig")["body"] == {"modelUrl": "https://x/a/textured.glb?sig=1"}
    rg = post_job({"fig_rig": {"status": DONE, "urls": ["https://x/r/rigged?sig=2"]}}, "retarget", "fig_rig:Walk_Loop+Idle_Loop")
    assert rg["endpoint"] == RETARGET and rg["name"] == "fig_rig_anim", rg
    assert rg["body"]["animationIds"] == ["Walk_Loop", "Idle_Loop"] and rg["body"]["animateInPlace"] is True, rg

    class RetargetApi(FakeApi):  # one action delivered, one failed: keep the file, record the error
        def get(self, task_id):
            acts = {"actions": [{"animation_id": "Walk_Loop", "status": "success", "fbxUrl": "https://x/w/animation.fbx"},
                                {"animation_id": "Idle_Loop", "status": "failed", "error": {"code": "E"}}]}
            return {"c": "0", "d": {"taskId": task_id, "status": 3, "outputs": [{"content": json.dumps(acts)}]}}
    with tempfile.TemporaryDirectory() as tmp:
        api = RetargetApi()
        api.busy_once = False
        state = run([rg], api, tmp, os.path.join(tmp, "_state.json"), sleep=lambda s: None, log=lambda m: None)
        entry = state["fig_rig_anim"]
        assert entry["status"] == DONE and [os.path.basename(f) for f in entry["files"]] == ["Walk_Loop.fbx"], entry
        assert entry["errors"] and entry["errors"][0].startswith("Idle_Loop"), entry
    print(f"selftest OK ({len(table_jobs)} jobs parsed from the prompt table)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated item names from the table")
    ap.add_argument("--out", default=os.environ.get("FOA_LUX3D_OUT", "P:/FoA-Assets/lux3d"))
    ap.add_argument("--retopo", default="", help="NAME[:QUAD_FACES],... of done jobs (within 2 h): retopologize their GLBs")
    ap.add_argument("--rig", default="", help="NAME,... of done jobs (within 2 h): auto-rig their humanoid GLBs")
    ap.add_argument("--retarget", default="", help="RIGJOB:Anim+Anim,... of done rig jobs (within 2 h): in-place FBX clips")
    ap.add_argument("--table", default=TABLE, help="prompt table (default docs/lux3d-bedroom-prompts.md)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    state_path = os.path.join(args.out, "_state.json")
    if args.retopo or args.rig or args.retarget:
        state = json.load(open(state_path, encoding="utf-8")) if os.path.exists(state_path) else {}
        jobs = ([post_job(state, "retopo", x) for x in args.retopo.split(",") if x] +
                [post_job(state, "rig", x) for x in args.rig.split(",") if x] +
                [post_job(state, "retarget", x) for x in args.retarget.split(",") if x])
    else:
        jobs = parse_table(args.table)
    if args.only:
        wanted = {slug(x) for x in args.only.split(",")}
        jobs = [j for j in jobs if j["name"] in wanted]
    if args.dry_run:
        for j in jobs:
            print(f"{j['name']:<20} {json.dumps(j['body'])}")
        return
    os.makedirs(args.out, exist_ok=True)
    run(jobs, Api(load_key()), args.out, state_path)


def load_key():
    """The Aholo API key (Lux3D and World share it). Never print it."""
    key = os.environ.get("LUX3D_API_KEY")
    key_file = os.path.join(os.path.expanduser("~"), ".foa", "lux3d_api_key")
    for candidate in (key_file, key_file + ".txt"):  # Notepad tends to add .txt
        if not key and os.path.exists(candidate):
            key = open(candidate, encoding="utf-8-sig").read().strip()
    if not key:
        sys.exit(f"No API key: set LUX3D_API_KEY or put it in {key_file}")
    return key


if __name__ == "__main__":
    main()
