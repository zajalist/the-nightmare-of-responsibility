"""Run a Python file inside an already-open Unreal Editor (no second editor, no asset conflicts).

  $env:FOA_AREAS='VFX,Level'; python Tools/Unreal/ue_remote.py Tools/Unreal/build_x.py [KEY=VALUE ...] [--flag ...]

Areas: the run holds editor_lock leases on FOA_AREAS (comma list, from the environment or a FOA_AREAS=... argument),
plus FOA_ACTORS (actor labels) and FOA_ACTORS_NEW (spawn prefixes), so lanes on other areas run at the same time. FOA_AREAS unset: the areas this lane already holds via
`editor_lock.py acquire`, or else EXCLUSIVE for this run (old scripts stay safe). Owner = HAYBA_AGENT_ID or FOA_AGENT.
Keep each run under ~30 s: a run holds the editor's one game thread, so every lane's Hayba calls and lease requests
wait behind it. Chunk imports and builds into short runs; longer runs print a warning.
KEY=VALUE pairs reach the script as os.environ and are removed again afterwards; --flags reach it as
os.environ["FOA_FLAGS"] (space-separated).

Transport: Hayba's guarded python_exec_file when the installed Hayba has it (SEH-guarded, private namespace, GC after
the run), else Epic's remote execution, which keeps only ONE command connection per editor, so remote-execution runs
take turns on a process-owned file lock for the few seconds a script runs (the editor runs one script at a time anyway).
"""
import msvcrt
import os
import sys
import time

import editor_lock  # same folder
import hayba_call as hc  # same folder

ENGINE_PY = r"C:\Program Files\Epic Games\UE_5.9\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"
sys.path.append(ENGINE_PY)
import remote_execution as rex  # noqa: E402  (Epic's module, found via ENGINE_PY)

RUN_TTL_S = 120  # a run is <30 s; its lease outlives it only by a crash margin
LONG_RUN_S = 30  # one run blocks the editor's single game thread, and with it every other lane
TRANSPORT_LOCK = os.path.join(editor_lock.ROOT, "FoA_remote_exec.lock")
PROJECT = os.path.normcase(os.path.abspath(hc.editor_root()))

# One run, one command: env set + script + env restore + GC, so two lanes' runs can never interleave their env vars.
RUNNER = (
    "def _foa_run(p, env):\n"
    "    import gc, os, sys\n"
    "    saved = {k: os.environ.get(k) for k in env}\n"
    "    os.environ.update(env)\n"
    "    try:\n"
    # Private namespace, not cleared: tick callbacks a script registers (shoot_live.py) still read their globals.
    "        ns = {'__name__': '__main__', '__file__': p}\n"
    "        with open(p, encoding='utf-8') as f:\n"
    "            exec(compile(f.read(), p, 'exec'), ns)\n"
    "    finally:\n"
    "        for k, v in saved.items():\n"
    "            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)\n"
    "        ns = None\n"
    "        sys.last_type = sys.last_value = sys.last_traceback = None\n"
    "        gc.collect()\n"
    "_foa_run(@SCRIPT@, @ENV@)\n"
    "del _foa_run\n"
)


def run_hayba(script, env, keys, owner, token):
    """python_exec_file through Hayba. Returns None when this Hayba (or this path) can't run it."""
    if not os.path.normcase(script).startswith(PROJECT + os.sep):
        return None
    try:
        resp = hc.call("python_exec_file", {"path": script, "env": env, "resources": keys, "allow_blocking":
                                            os.environ.get("FOA_ALLOW_BLOCKING") == "1"}, timeout=3600,
                       owner=owner, lease=token)
    except (OSError, ValueError):
        return None
    err = str(resp.get("error", ""))
    data = resp.get("data") or {}
    if not data and ("Unknown command" in err or "HCR-FILE-00" in err):
        return None  # older Hayba, or the project has not enabled bAllowProjectPythonFiles
    if data.get("output"):
        print(data["output"].rstrip())
    if resp.get("ok") and data.get("ok"):
        return True
    print(data.get("error") or err)  # a failed script: Hayba reports it at both levels
    return False


def run_remote(script, env):
    with open(TRANSPORT_LOCK, "a+") as fh:
        while True:  # the OS drops this lock when the process dies, so a crashed run never wedges the others
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                time.sleep(0.2)
        remote = rex.RemoteExecution(rex.RemoteExecutionConfig())
        remote.start()
        try:
            deadline = time.time() + 60  # a busy editor answers discovery pings only between game-thread jobs
            while not remote.remote_nodes and time.time() < deadline:
                time.sleep(0.25)
            want = os.path.normcase(os.path.abspath(hc.editor_root()))
            nodes = [n for n in remote.remote_nodes
                     if os.path.normcase(os.path.abspath(str(n.get("project_root", "")) or "?")) == want]
            if not nodes:
                sys.exit("No editor found. Is it open, with Python remote execution enabled?")
            for attempt in range(6):  # the editor answers the handshake from its tick: busy game thread = no answer
                try:
                    remote.open_command_connection(nodes[0]["node_id"])
                    break
                except RuntimeError:
                    if attempt == 5:
                        raise
                    time.sleep(5 * (attempt + 1))
            result = remote.run_command(RUNNER.replace("@SCRIPT@", repr(script)).replace("@ENV@", repr(env)), unattended=True,
                                        exec_mode=rex.MODE_EXEC_FILE)
        finally:
            remote.stop()
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    for line in result.get("output", []):
        print(line.get("output", "").rstrip())
    if not result.get("success"):
        print(result.get("result"))
    return bool(result.get("success"))


def user_playing():
    """PIE is running and no lane holds EXCLUSIVE (the only way lanes may run PIE): the user is playing.
    Each editor Python run stalls the game thread for 0.9-3 s (hitch hunt 2026-11-06), so lanes wait."""
    try:
        if not hc.call("editor_get_state", timeout=20).get("data", {}).get("pie_running"):
            return False
        leases = hc.call("lease_status", timeout=20).get("data", {}).get("leases", [])
    except (OSError, ValueError):
        return False
    return not any(r.get("resource") == "global" for l in leases for r in l.get("resources", []))


def wait_while_user_plays(limit_s=3600):
    told = False
    deadline = time.time() + limit_s
    while user_playing() and time.time() < deadline:
        if not told:
            print("ue_remote: the user is playing in the editor; waiting for PIE to end before running", file=sys.stderr)
            told = True
        time.sleep(10)


# Calls that block the editor's single game thread on ALL pending shader and asset compilation for the whole
# world (UAutomationBlueprintFunctionLibrary::FinishLoadingBeforeScreenshot -> SubmitRemainingJobsForWorld +
# FAssetCompilingManager::FinishAllCompilation). One take_high_res_screenshot froze editor A for 10 min at 00:39 while
# every lane waited, and the user had to kill it. Capture with Hayba editor_capture_viewport / render_camera, or a
# SceneCapture2D, which use whatever shaders are ready. FOA_ALLOW_BLOCKING=1 overrides (inside an EXCLUSIVE hold).
BLOCKING_CALLS = ("take_high_res_screenshot", "take_automation_screenshot", "finish_loading_before_screenshot",
                  "finish_all_compilation", "finish_all_shader_compilation", "compile_all_blueprints")


def blocking_calls(script):
    with open(script, encoding="utf-8", errors="replace") as fh:
        src = fh.read().lower()
    return [c for c in BLOCKING_CALLS if c in src]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: ue_remote.py <script.py> [KEY=VALUE ...]")
    script = os.path.abspath(sys.argv[1]).replace("\\", "/")
    found = blocking_calls(script)
    if found and os.environ.get("FOA_ALLOW_BLOCKING") != "1":
        sys.exit(f"ue_remote: refused {script}: it calls {', '.join(found)}, which blocks the editor's game thread on "
                 "every pending shader compile in the world (the 00:39 10-minute freeze). Capture with Hayba "
                 "editor_capture_viewport or render_camera, or a SceneCapture2D, instead. FOA_ALLOW_BLOCKING=1 overrides, "
                 "only inside an EXCLUSIVE hold.")
    a_root, root = os.path.abspath(hc.EDITORS["A"]), os.path.abspath(hc.editor_root())
    if root != a_root and os.path.normcase(os.path.abspath(script)).startswith(os.path.normcase(a_root) + os.sep):
        moved = os.path.join(root, os.path.relpath(script, a_root))  # P:/FoA-B/Tools is a junction to P:/FoA/Tools
        if os.path.exists(moved):
            script = moved.replace("\\", "/")
    # The script runs inside the editor process, which never sees this shell's env vars; pass them explicitly.
    env = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    env.setdefault("FOA_CALLER", hc.agent_id() or os.environ.get("FOA_AGENT", ""))  # see pie_call.py END
    flags = [a for a in sys.argv[2:] if a.startswith("--") and "=" not in a]
    if flags:
        env["FOA_FLAGS"] = " ".join(flags)
    owner = hc.agent_id() or "main"
    def listed(name):
        return [a for a in (env.pop(name, None) or os.environ.get(name, "")).split(",") if a.strip()]
    areas = listed("FOA_AREAS") + editor_lock.actor_keys(listed("FOA_ACTORS"), listed("FOA_ACTORS_NEW"))
    exclusive = (env.pop("FOA_EXCLUSIVE", None) or os.environ.get("FOA_EXCLUSIVE", "")) == "1"
    if exclusive:
        areas = ["EXCLUSIVE"]
    held_file = editor_lock.read()
    # An old file-lock hold counts only while the editor is down (fallback) or for maintenance holds.
    file_mine = (editor_lock._file_owner(held_file) == owner and not editor_lock.stale(held_file)
                 and not editor_lock._hayba_up())
    mine = editor_lock.hayba_leases(owner)
    token = None
    took_file = False
    if not areas and not (mine or file_mine):
        # Undeclared runs used to take EXCLUSIVE silently, and each one stalled every other lane.
        sys.exit("ue_remote: declare what this run touches with FOA_AREAS / FOA_ACTORS / FOA_ACTORS_NEW, "
                 "or FOA_EXCLUSIVE=1 for PIE and deletes (EXCLUSIVE starts only in the PIE window, minutes :x0-:x2).")
    if areas:
        token = editor_lock.acquire(owner, wait_s=1800, ttl=RUN_TTL_S, areas=areas or ["EXCLUSIVE"])
        took_file = not file_mine and editor_lock._file_owner(editor_lock.read()) == owner  # Hayba was down
    elif mine:
        # Renew the caller's existing hold only for this run: EXCLUSIVE stays near the 60 s burst rule, and a crashed
        # caller can't leave a 900 s lease behind that blocks every other lane.
        is_global = any(r.lower() == "global" for _, res in mine for r in res)
        editor_lock._soft(lambda: hc.renew_all(owner, 70 if is_global else RUN_TTL_S), None)
    keys = editor_lock.area_keys(areas or ["EXCLUSIVE"])
    if "global" not in keys:
        wait_while_user_plays()
    started = time.time()
    try:
        ok = run_hayba(script, env, keys, owner, token)
        if ok is None:
            ok = run_remote(script, env)
        took = time.time() - started
        if took > LONG_RUN_S:
            print(f"ue_remote: WARNING this run held the editor's game thread for {took:.0f}s; every lane's Hayba calls "
                  f"and lease requests waited behind it. Split imports and builds into runs under {LONG_RUN_S}s.",
                  file=sys.stderr)
    finally:
        if token:
            editor_lock._soft(lambda: hc.release(owner, token), None)
            editor_lock.forget(owner, token)
        if took_file:
            editor_lock.release_file(owner)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
