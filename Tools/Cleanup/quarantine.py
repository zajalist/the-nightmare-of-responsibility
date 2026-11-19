"""Move approved packages out of Content while the editor is CLOSED (cleanup phase 2, offline quarantine).

  python Tools/Cleanup/quarantine.py --list Saved/Cleanup/quarantine_list.txt --dry-run
  python Tools/Cleanup/quarantine.py --list Saved/Cleanup/quarantine_list.txt
  python Tools/Cleanup/quarantine.py --restore P:/FoA-Assets/_cleanup_quarantine/20261109/manifest_<time>.json

Each /Game package in the list (one per line, # comments) maps to its .uasset/.umap plus any .uexp/.ubulk/.uptnl
siblings under <root>/Content. Every file moves to <dest>/<same path relative to root>, so moving it back restores it.
A manifest (source, destination, bytes, removed folders) is written next to the files and copied to Saved/Cleanup.
Folders the move leaves empty are removed. Nothing is overwritten. While any UnrealEditor process is alive it refuses
to touch the project (a dry run is allowed); --root/--dest point it elsewhere for testing.
"""
import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEST = r"P:\FoA-Assets\_cleanup_quarantine\20261109"
EXTS = (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl", ".m.ubulk")


def editors_alive():
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return sorted({ln.split(",")[0].strip('"') for ln in out.splitlines() if ln.lower().startswith('"unrealeditor')})


def guard(root, dry_run):
    if dry_run or os.path.normcase(os.path.abspath(root)) != os.path.normcase(ROOT):
        return
    alive = editors_alive()
    if alive:
        sys.exit(f"refused: {', '.join(alive)} is running. Quit every editor first (files move under its feet otherwise).")


def files_of(root, pkg):
    base = os.path.join(root, "Content", *pkg[len("/Game/"):].split("/"))
    return [base + e for e in EXTS if os.path.isfile(base + e)]


def prune(dirs, stop):
    """Remove folders left empty, walking up to (not including) `stop`."""
    removed = []
    for d in sorted(dirs, key=len, reverse=True):
        while os.path.normcase(d).startswith(os.path.normcase(stop) + os.sep) and os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            removed.append(d)
            d = os.path.dirname(d)
    return removed


def quarantine(args):
    with open(args.list, encoding="utf-8") as fh:
        pkgs = [ln.split("#")[0].strip() for ln in fh if ln.split("#")[0].strip()]
    bad = [p for p in pkgs if not p.startswith("/Game/") or ".." in p]
    if bad:
        sys.exit(f"refused: not /Game package paths: {bad[:5]}")
    guard(args.root, args.dry_run)
    plan, missing, clash = [], [], []
    for p in pkgs:
        fs = files_of(args.root, p)
        if not fs:
            missing.append(p)
        for f in fs:
            dst = os.path.join(args.dest, os.path.relpath(f, args.root))
            (clash if os.path.exists(dst) else plan).append((f, dst, os.path.getsize(f)))
    total = sum(b for _, _, b in plan)
    print(f"{'DRY RUN: ' if args.dry_run else ''}{len(pkgs)} packages -> {len(plan)} files, {total / 2**20:.1f} MB; "
          f"{len(missing)} packages without a file; {len(clash)} files already in the quarantine (skipped)")
    for p in missing[:20]:
        print("  no file:", p)
    for f, d, _ in clash[:20]:
        print("  already quarantined:", d)
    # Packages saved after the list was checked (the save-all before the quit) may name a listed package by now.
    # shortcut: raw string scan, so a stale import-metadata path also stops it; then re-check that file by hand.
    listed, moving = set(pkgs), {os.path.normcase(f) for f, _, _ in plan}
    newer = [os.path.join(dp, n) for dp, _, fs in os.walk(os.path.join(args.root, "Content")) for n in fs
             if n.endswith((".uasset", ".umap")) and os.path.getmtime(os.path.join(dp, n)) > os.path.getmtime(args.list)
             and os.path.normcase(os.path.join(dp, n)) not in moving]
    hits = {}
    for f in newer:
        with open(f, "rb") as fh:
            data = fh.read()
        names = {m.decode("ascii", "ignore").split(".")[0] for m in re.findall(rb"/Game/[A-Za-z0-9_\-./]+", data)}
        if names & listed:
            hits[f] = sorted(names & listed)
    print(f"{len(newer)} packages saved after the list was checked; {len(hits)} of them name a listed package")
    for f, n in hits.items():
        print("  REFERENCES A LISTED PACKAGE:", os.path.relpath(f, args.root), n[:5])
    if args.dry_run:
        return
    if hits:
        sys.exit("refused: packages saved after the check reference listed packages (above). Drop those from the list, "
                 "or confirm the strings are only import metadata, then run again.")
    done = []
    try:
        for src, dst, size in plan:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            done.append({"src": src, "dst": dst, "bytes": size})
    finally:  # the manifest is written even if a move fails, so everything moved so far can be restored
        removed = prune({os.path.dirname(d["src"]) for d in done}, os.path.join(args.root, "Content"))
        manifest = {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "root": args.root, "dest": args.dest,
                    "packages": len(pkgs), "files": done, "removed_dirs": removed,
                    "bytes": sum(d["bytes"] for d in done)}
        name = time.strftime("manifest_%H%M%S.json")
        os.makedirs(args.dest, exist_ok=True)
        project = os.path.normcase(os.path.abspath(args.root)) == os.path.normcase(ROOT)
        for out in [os.path.join(args.dest, name)] + ([os.path.join(ROOT, "Saved", "Cleanup", "quarantine_" + name)]
                                                      if project else []):
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=1)
        print(f"moved {len(done)} files, {manifest['bytes'] / 2**20:.1f} MB; removed {len(removed)} empty folders; "
              f"manifest {os.path.join(args.dest, name)}")


def prune_empty(args):
    guard(args.root, args.dry_run)
    content = os.path.join(args.root, "Content")
    keep = {os.path.normcase(os.path.join(content, d)) for d in ("Collections", "Developers")}
    empty, full = [], set()
    for dp, dirs, fs in os.walk(content, topdown=False):  # bottom-up: empty = no file anywhere below
        if fs or any(os.path.normcase(os.path.join(dp, d)) in full for d in dirs):
            full.add(os.path.normcase(dp))
        elif dp != content and not any(os.path.normcase(dp).startswith(k) for k in keep):
            empty.append(dp)
    print(f"{'DRY RUN: ' if args.dry_run else ''}{len(empty)} empty folders under Content")
    for d in empty:
        print("  ", os.path.relpath(d, args.root))
    if args.dry_run:
        return
    for d in empty:  # bottom-up order, so children go first
        os.rmdir(d)
    if os.path.normcase(os.path.abspath(args.root)) == os.path.normcase(ROOT):
        with open(os.path.join(ROOT, "Saved", "Cleanup", time.strftime("empty_dirs_removed_%Y-%m-%d.txt")), "a",
                  encoding="utf-8") as fh:
            fh.write("\n".join(empty) + "\n")
    print(f"removed {len(empty)} empty folders")


def restore(args):
    with open(args.restore, encoding="utf-8") as fh:
        manifest = json.load(fh)
    guard(manifest["root"], args.dry_run)
    back, clash, lost = [], [], []
    for d in manifest["files"]:
        if os.path.exists(d["src"]):
            clash.append(d["src"])
        elif not os.path.exists(d["dst"]):
            lost.append(d["dst"])
        else:
            back.append(d)
    print(f"{'DRY RUN: ' if args.dry_run else ''}restore {len(back)} files, {sum(d['bytes'] for d in back) / 2**20:.1f} MB; "
          f"{len(clash)} would overwrite (skipped); {len(lost)} missing from the quarantine")
    for f in (clash + lost)[:20]:
        print("  skipped:", f)
    if args.dry_run:
        return
    for d in back:
        os.makedirs(os.path.dirname(d["src"]), exist_ok=True)
        shutil.move(d["dst"], d["src"])
    print(f"restored {len(back)} files")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--list", help="text file of /Game package paths to quarantine")
    src.add_argument("--restore", help="a manifest written by a previous run")
    src.add_argument("--prune-empty", action="store_true", help="remove every empty folder under Content (not the "
                     "engine's Collections/Developers); logs them to Saved/Cleanup/empty_dirs_removed_<date>.txt")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default=ROOT, help="project root (testing only)")
    ap.add_argument("--dest", default=DEST, help="quarantine folder (testing only)")
    args = ap.parse_args()
    if args.prune_empty:
        prune_empty(args)
    else:
        restore(args) if args.restore else quarantine(args)


if __name__ == "__main__":
    main()
