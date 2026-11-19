"""READ-ONLY after the moves: any redirector left anywhere under /Game, and which moved assets the given packages
depend on (old paths would mean a stale reference).
  python Tools/Unreal/integration/run_read.py Tools/Cleanup/probe_after_moves.py FOA_PKGS=/Game/A,/Game/B
"""
import json
import os

import unreal


def main():
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    reds = [str(a.package_name) for a in ar.get_assets_by_path("/Game", recursive=True)
            if str(a.asset_class_path.asset_name) == "ObjectRedirector"]
    print("PROBE redirectors under /Game:", len(reds), reds[:10])
    with open(unreal.Paths.project_saved_dir() + "Cleanup/moves.json", encoding="utf-8") as fh:
        moves = json.load(fh)
    olds, news = {m["from"] for m in moves}, {m["to"] for m in moves}
    opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                                 include_hard_package_references=True)
    for p in filter(None, os.environ.get("FOA_PKGS", "").split(",")):
        deps = {str(d) for d in (ar.get_dependencies(p, opts) or [])}
        print(f"PROBE {p}: on disk={bool(ar.get_assets_by_package_name(p))} depends on moved(new)={sorted(deps & news)} "
              f"old paths={sorted(deps & olds)}")


main()
