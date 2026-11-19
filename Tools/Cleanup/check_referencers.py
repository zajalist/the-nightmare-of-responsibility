"""READ-ONLY: live AssetRegistry referencers (hard + soft) of the quarantine candidates, one chunk per run.
  python Tools/Unreal/integration/run_read.py Tools/Cleanup/check_referencers.py FOA_CHUNK=0 FOA_NCHUNKS=4
Reads Saved/Cleanup/quarantine_list.txt, writes Saved/Cleanup/registry/referencers_<i>.json.
"""
import json
import os
import time

import unreal


def main():
    t0 = time.time()
    i, n = int(os.environ.get("FOA_CHUNK", "0")), int(os.environ.get("FOA_NCHUNKS", "1"))
    saved = unreal.Paths.project_saved_dir() + "Cleanup/"
    with open(saved + "quarantine_list.txt", encoding="utf-8") as fh:
        pkgs = sorted({ln.split("#")[0].strip() for ln in fh if ln.split("#")[0].strip()})[i::n]
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=True, include_searchable_names=False,
                                                 include_soft_management_references=False,
                                                 include_hard_management_references=False)
    out = {p: {"exists": bool(ar.get_assets_by_package_name(p)),
               "referencers": sorted({str(r) for r in (ar.get_referencers(p, opts) or [])} - {p})} for p in pkgs}
    with open(saved + f"registry/referencers_{i}.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh)
    print(f"check_referencers chunk {i}/{n}: {len(pkgs)} packages in {time.time() - t0:.1f}s")


main()
