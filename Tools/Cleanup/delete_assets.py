"""Delete the approved assets in small batches inside the open editor (cleanup phase 2).

  $env:FOA_AGENT='cleanup'
  python Tools/Cleanup/delete_assets.py --tiers T1 --dry-run           # class c, tier T1 from Saved/Cleanup/audit.json
  python Tools/Cleanup/delete_assets.py --list Saved/Cleanup/approved.txt   # one /Game path per line, # comments
  python Tools/Cleanup/delete_assets.py --paths /Game/A/X,/Game/B/Y [--batch 25] [--budget 20]

Order comes from the audit graph: referencers first, reference cycles kept in one batch. Each batch is two ue_remote
runs: `check` (live referencer check, close the asset editors) and then `delete` (the check repeated right before
EditorAssetLibrary.delete_asset; any referencer outside the batch keeps the asset). Kept or deferred assets get up to
two more passes. --dry-run makes read-only check runs through run_read.py and deletes nothing.
--declare /Game/A,/Game/B leases those folders whole when a batch reaches into them and every other asset by its exact
path (per batch). Without it, runs declare FOA_EXCLUSIVE=1 unless FOA_AREAS / FOA_ACTORS / FOA_EXCLUSIVE is set. Every deletion is appended to Saved/Cleanup/deleted_assets_<date>.txt.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AUDIT = os.path.join(ROOT, "Saved", "Cleanup", "audit.json")
WORKER = "Tools/Cleanup/cleanup_worker.py"


def run_job(job, dry_run, areas=None):
    """Run one worker job in the editor; returns its result dict (empty on a failed run). `areas`: the run's
    FOA_AREAS declaration (exact paths), overriding the environment."""
    path = os.path.join(ROOT, "Saved", "Cleanup", f"_job_{os.getpid()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(job, dry_run=dry_run), fh)
    env = dict(os.environ)
    env.setdefault("FOA_AGENT", "cleanup")
    if areas:
        env["FOA_AREAS"] = ",".join(areas)
        env.pop("FOA_EXCLUSIVE", None)
    if not dry_run and not any(env.get(k) for k in ("FOA_AREAS", "FOA_ACTORS", "FOA_ACTORS_NEW", "FOA_EXCLUSIVE")):
        env["FOA_EXCLUSIVE"] = "1"
    runner = "Tools/Unreal/integration/run_read.py" if dry_run else "Tools/Unreal/ue_remote.py"
    proc = subprocess.run([sys.executable, runner, WORKER, f"FOA_JOB={path}"], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    for line in (proc.stdout + proc.stderr).splitlines():
        if line.strip():
            print("   ", line)
    try:
        with open(path + ".result.json", encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        print("    run failed: no result file")
        return {}
    finally:
        for f in (path, path + ".result.json"):
            if os.path.exists(f):
                os.remove(f)


def ordered_batches(paths, deps, size):
    """Referencers before what they reference; each reference cycle (SCC) stays inside one batch."""
    sys.setrecursionlimit(20000)
    sel = set(paths)
    index, low, stack, on, sccs = {}, {}, [], set(), []

    def visit(v):
        index[v] = low[v] = len(index)
        stack.append(v)
        on.add(v)
        for w in deps.get(v, ()):
            if w not in sel:
                continue
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(sorted(comp))

    for v in sorted(sel):
        if v not in index:
            visit(v)
    batches, cur = [], []
    for comp in reversed(sccs):  # Tarjan emits dependencies first; reversed = referencers first
        if cur and len(cur) + len(comp) > size:
            batches.append(cur)
            cur = []
        cur += comp
    return batches + ([cur] if cur else [])


def declared(batch, roots):
    """Lease keys for a batch: a root folder when the batch reaches into it, else the exact asset path."""
    return sorted({next((r for r in roots if p == r or p.startswith(r + "/")), p) for p in batch})


def select(args, audit):
    if args.paths:
        return [p.strip() for p in args.paths.split(",") if p.strip()]
    if args.list:
        with open(args.list, encoding="utf-8") as fh:
            return [ln.split("#")[0].strip() for ln in fh if ln.split("#")[0].strip()]
    tiers = set(args.tiers.split(","))
    return sorted(p for p, a in audit.get("assets", {}).items() if a["class"] == "c" and a.get("tier") in tiers)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tiers", help="comma list of audit tiers (class c): T1,T2,T3")
    src.add_argument("--list", help="text file, one /Game package path per line")
    src.add_argument("--paths", help="comma list of /Game package paths")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--budget", type=float, default=15.0, help="seconds of deleting per run before deferring")
    ap.add_argument("--declare", default=None, help="comma list of folders to lease whole (e.g. /Game/Fab/MetaHuman); "
                    "every other asset is leased by its exact path ('' = exact paths only). Default: FOA_AREAS/FOA_EXCLUSIVE from the env")
    args = ap.parse_args()

    audit = json.load(open(AUDIT, encoding="utf-8")) if os.path.exists(AUDIT) else {}
    assets = audit.get("assets", {})
    paths = select(args, audit)
    roots = [r.rstrip("/") for r in (args.declare or "").split(",") if r.strip()]
    risky = [p for p in paths if assets.get(p, {}).get("class") in ("a", "b")]
    if risky:  # the audit says these are used: never delete them through this script
        sys.exit("refused: the audit classes these as used (a/b): " + ", ".join(risky[:10]))
    deps = {p: assets.get(p, {}).get("deps", []) for p in paths}
    size = lambda p: assets.get(p, {}).get("bytes", 0)
    print(f"{'DRY RUN: ' if args.dry_run else ''}{len(paths)} assets, {sum(map(size, paths)) / 2**20:.1f} MB on disk")
    log = os.path.join(ROOT, "Saved", "Cleanup", time.strftime("deleted_assets_%Y-%m-%d.txt"))
    todo, deleted, missing = list(paths), [], []
    for attempt in range(3):
        progress = False
        batches = ordered_batches(todo, deps, args.batch)
        left = []
        for n, batch in enumerate(batches, 1):
            print(f"pass {attempt + 1} batch {n}/{len(batches)}: {len(batch)} assets")
            areas = declared(batch, roots) if args.declare is not None else None
            chk = run_job({"step": "check", "paths": batch, "allowed": paths if args.dry_run else None},
                          args.dry_run, areas)
            missing += chk.get("missing", [])
            ready = chk.get("done", [])
            left += chk.get("kept", [])
            if args.dry_run or not ready:
                continue
            while ready:  # each run stops at the time budget; the deferred rest goes in the next run, same order
                res = run_job({"step": "delete", "paths": ready, "budget_s": args.budget}, False, areas)
                done = res.get("done", [])
                deleted += done
                progress |= bool(done)
                left += res.get("kept", []) + res.get("failed", [])
                missing += res.get("missing", [])
                with open(log, "a", encoding="utf-8") as fh:
                    for p in done:
                        fh.write(f"{p}\t{size(p)}\n")
                ready = res.get("deferred", []) if done else []
                left += [] if done else res.get("deferred", [])
        todo = sorted(set(left))
        if args.dry_run or not todo or not progress:
            break
    print(f"{'would delete' if args.dry_run else 'deleted'}: "
          f"{len(paths) - len(todo) - len(set(missing)) if args.dry_run else len(deleted)}; "
          f"kept (still referenced or failed): {len(todo)}; missing: {len(set(missing))}")
    for p in todo:
        print("  KEPT", p)
    if deleted:
        print(f"log: {log}")


if __name__ == "__main__":
    main()
