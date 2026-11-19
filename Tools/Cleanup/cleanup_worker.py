"""In-editor half of delete_assets.py / move_assets.py. Never run by hand: the drivers write a job file and run this
through ue_remote.py (real) or run_read.py (dry run, read-only steps only).

Job (FOA_JOB=<json path>): {"step": "check"|"delete"|"move"|"state", "paths": [...], "moves": [[old, new], ...],
"dry_run": bool, "budget_s": float}. Writes <job>.result.json and prints one line per asset.
  check  live referencer check; a real run also closes the asset editors of loaded assets (rule: before any delete
         or rename). "for_move": true skips the referencer gate (a move keeps references working).
  delete the check again, right before EditorAssetLibrary.delete_asset. Referencers inside the same batch are allowed
         (the drivers order batches referencers-first); any other referencer keeps the asset. Never force-deletes
         a referenced asset.
  move   AssetTools.rename_assets (leaves redirectors; the driver fixes them up with Hayba asset_fix_redirectors).
  state  exists / class / referencers, for verification.
  resave load + save each path (referencers of a redirector), so the redirector loses its referencers.
"""
import json
import os
import time

import unreal


def referencers(path):
    # Not EditorAssetLibrary.find_package_referencers_for_asset: after the 2026-11-09 21:50 restart it returned []
    # for referenced assets (M_Surface: 0 vs registry 3), which would let a delete pass. Registry is the truth.
    pkg = path.split(".")[0]
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=True, include_searchable_names=False,
                                                 include_soft_management_references=False,
                                                 include_hard_management_references=False)
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    return sorted({str(r) for r in (ar.get_referencers(pkg, opts) or [])} - {pkg})


def close_editors(path):
    ad = unreal.EditorAssetLibrary.find_asset_data(path)
    if ad.is_valid() and ad.is_asset_loaded():  # an editor can only be open on a loaded asset; never load just to close
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(ad.get_asset())


def package_file(path):
    rel = path.split(".")[0][len("/Game/"):]
    base = os.path.join(unreal.Paths.project_content_dir(), *rel.split("/"))
    return next((base + e for e in (".uasset", ".umap") if os.path.exists(base + e)), base + ".uasset")


def asset_class(path):
    ad = unreal.EditorAssetLibrary.find_asset_data(path)
    return str(ad.asset_class_path.asset_name) if ad.is_valid() else ""


def run(job):
    eal = unreal.EditorAssetLibrary
    t0, budget = time.time(), float(job.get("budget_s", 20))
    batch = {p.split(".")[0] for p in job.get("allowed") or job.get("paths", [])}  # dry run: the whole selection
    out = {"done": [], "kept": [], "missing": [], "deferred": [], "failed": [], "state": {}}
    step = job["step"]
    if step in ("check", "delete", "state"):
        for p in job["paths"]:
            if not eal.does_asset_exist(p):
                out["missing"].append(p)
                print(f"CLEANUP {step} missing {p}")
                continue
            refs = referencers(p)
            if step == "state":
                out["state"][p] = {"class": asset_class(p), "referencers": refs}
                print(f"CLEANUP state {p} class={asset_class(p)} referencers={refs}")
                continue
            outside = [] if job.get("for_move") else [r for r in refs if r not in batch or r in out["kept"]]
            if outside:
                out["kept"].append(p)
                print(f"CLEANUP {step} KEPT {p} referenced by {outside}")
                continue
            if step == "check":
                if not job.get("dry_run"):
                    close_editors(p)
                out["done"].append(p)
                print(f"CLEANUP check ok {p}" + (f" (referencers: {refs})" if refs else ""))
                continue
            if time.time() - t0 > budget:  # keep each run short: the rest goes in the next run
                out["deferred"].append(p)
                continue
            # delete_asset can return True and leave the package on disk (seen on textures still building after the
            # load it does), so success means the file is gone.
            ok = eal.delete_asset(p) and not os.path.exists(package_file(p))
            (out["done"] if ok else out["failed"]).append(p)
            print(f"CLEANUP delete {'DELETED' if ok else 'FAILED (file still on disk)'} {p}")
    elif step == "resave":  # load and save referencers so they point past a redirector (the fix-up, no dialog)
        for p in job["paths"]:
            if not eal.does_asset_exist(p):
                out["missing"].append(p)
                continue
            close_editors(p)
            eal.load_asset(p)
            ok = eal.save_asset(p, only_if_is_dirty=False)
            (out["done"] if ok else out["failed"]).append(p)
            print(f"CLEANUP resave {'SAVED' if ok else 'FAILED'} {p}")
    elif step == "move":
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        for old, new in job["moves"]:
            if time.time() - t0 > budget:
                out["deferred"].append(old)
                continue
            if not eal.does_asset_exist(old):
                out["missing"].append(old)
                print(f"CLEANUP move missing {old}")
                continue
            if eal.does_asset_exist(new):
                out["kept"].append(old)
                print(f"CLEANUP move KEPT {old}: {new} already exists")
                continue
            folder, name = new.rsplit("/", 1)
            data = unreal.AssetRenameData(asset=eal.load_asset(old), new_package_path=folder, new_name=name)
            ok = tools.rename_assets([data])
            data = None
            if ok:
                eal.save_asset(new, only_if_is_dirty=False)
                if eal.does_asset_exist(old):  # the redirector left at the old path
                    eal.save_asset(old, only_if_is_dirty=False)
            (out["done"] if ok else out["failed"]).append(old)
            print(f"CLEANUP move {'MOVED' if ok else 'FAILED'} {old} -> {new}")
    with open(job["_path"] + ".result.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"CLEANUP {step}: done={len(out['done'])} kept={len(out['kept'])} missing={len(out['missing'])} "
          f"deferred={len(out['deferred'])} failed={len(out['failed'])} in {time.time() - t0:.1f}s")


def main():
    path = os.environ["FOA_JOB"]
    with open(path, encoding="utf-8") as fh:
        job = json.load(fh)
    job["_path"] = path
    run(job)


main()
