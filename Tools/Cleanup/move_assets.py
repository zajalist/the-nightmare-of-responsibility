"""Move or rename assets in small batches inside the open editor, then fix up the redirectors (cleanup phase 2).

  $env:FOA_AGENT='cleanup'
  python Tools/Cleanup/move_assets.py --plan Saved/Cleanup/moves.json --set A --dry-run
  python Tools/Cleanup/move_assets.py --move /Game/FoA/Door/X/StaticMeshes/SM_X=/Game/FoA/Props/Door/SM_X
  python Tools/Cleanup/move_assets.py --fixup /Game/A/OldRedirector ...      # only fix up these redirectors

moves.json: [{"from": "/Game/...", "to": "/Game/.../NewName", "set": "A"}, ...]. Per batch: a `check` run (live
state, close editors), a `move` run (AssetTools.rename_assets, saves the asset and the redirector), then the fix-up:
resave the referencers of any redirector left at an old path and delete it (never Hayba asset_fix_redirectors: it
opens a modal report), then a `state` run proving nothing is left at the old paths. Afterwards it prints every Tools/ line that still names an old path:
builder scripts load assets by path and must be updated by hand. --dry-run: read-only check plus the Tools list.
Lease: FOA_EXCLUSIVE=1 for check/move unless FOA_AREAS / FOA_ACTORS / FOA_EXCLUSIVE is set; the fix-up leases the
exact referencer and redirector paths.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Unreal"))
from delete_assets import ROOT, run_job  # noqa: E402


def tools_hits(old_paths):
    """Tools/ lines naming an old path (exact, or as path + '.Object')."""
    pats = [(p, re.compile(re.escape(p) + r"(?![A-Za-z0-9_/])")) for p in old_paths]
    hits = []
    for dp, dirs, fs in os.walk(os.path.join(ROOT, "Tools")):
        dirs[:] = [d for d in dirs if d != "__pycache__" and d != "Cleanup"]
        for n in fs:
            if not n.endswith((".py", ".sh", ".ps1", ".json", ".txt")):
                continue
            f = os.path.join(dp, n)
            for ln, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
                for p, rx in pats:
                    if rx.search(line):
                        hits.append(f"{os.path.relpath(f, ROOT)}:{ln}: {line.strip()[:160]}")
    return hits


def fixup(redirectors):
    """Fix up redirectors without Hayba asset_fix_redirectors: that tool opens the modal "Redirector Update Report",
    which froze every lane for 4.5 min on 2026-11-09. Resave each redirector's referencers (they then point at the
    target), then delete the redirectors with the usual live referencer check. Each run leases exact paths."""
    st = run_job({"step": "state", "paths": sorted(redirectors)}, True).get("state", {})
    reds = [p for p, s in st.items() if s["class"] == "ObjectRedirector"]
    refs = sorted({r for p in reds for r in st[p]["referencers"]} - set(reds))
    if refs:
        run_job({"step": "resave", "paths": refs}, False, refs)
    if reds:
        run_job({"step": "delete", "paths": reds, "budget_s": 15}, False, reds)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--plan", help="moves.json")
    src.add_argument("--move", nargs="+", help="OLD=NEW package paths")
    src.add_argument("--fixup", nargs="+", help="redirector package paths to fix up and remove")
    ap.add_argument("--set", help="only the moves of this set in --plan")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--batch", type=int, default=10)
    args = ap.parse_args()
    if args.fixup:
        if not args.dry_run:
            fixup(args.fixup)
        return
    if args.plan:
        plan = json.load(open(args.plan, encoding="utf-8"))
        moves = [(m["from"], m["to"]) for m in plan if not args.set or m.get("set") == args.set]
    else:
        moves = [tuple(m.split("=", 1)) for m in args.move]
    bad = [m for m in moves if not (m[0].startswith("/Game/") and m[1].startswith("/Game/") and "." not in m[1])]
    if bad:
        sys.exit(f"refused: moves must be /Game package paths without an object suffix: {bad[:5]}")
    print(f"{'DRY RUN: ' if args.dry_run else ''}{len(moves)} moves")
    moved = []
    for i in range(0, len(moves), args.batch):
        batch = moves[i:i + args.batch]
        olds = [o for o, _ in batch]
        chk = run_job({"step": "check", "paths": olds, "for_move": True}, args.dry_run)
        taken = run_job({"step": "state", "paths": [n for _, n in batch]}, True).get("state", {})
        for o, n in batch:
            print(f"  {o} -> {n}" + (" (MISSING source)" if o in chk.get("missing", []) else "")
                  + (" (TARGET EXISTS)" if n in taken else ""))
        if args.dry_run:
            continue
        res = run_job({"step": "move", "moves": batch, "budget_s": 20}, False)
        done = set(res.get("done", []))
        moved += [(o, n) for o, n in batch if o in done]
        fixup(done)  # a rename leaves a redirector only where a referencer was not loaded
        left = run_job({"step": "state", "paths": sorted(done)}, True).get("state", {})
        for o, st in left.items():
            print(f"    still at old path: {o} class={st['class']} referencers={st['referencers']}")
    hits = tools_hits([o for o, _ in (moved or moves)])
    print(f"{len(hits)} Tools/ lines name a {'moved' if moved else 'to-be-moved'} path (update by hand):")
    for h in hits:
        print("   ", h)


if __name__ == "__main__":
    main()
