"""READ-ONLY check after the moves: every new path loads with its class, nothing (or no redirector) is left at the old
path, and the moved asset still has its referencers.
  python Tools/Unreal/integration/run_read.py Tools/Cleanup/verify_moves.py [FOA_SET=A]
Reads Saved/Cleanup/moves.json; writes Saved/Cleanup/verify_moves.txt and prints the totals.
"""
import json
import os

import unreal


def check(old, new):
    eal = unreal.EditorAssetLibrary
    obj = eal.load_asset(new) if eal.does_asset_exist(new) else None
    left = eal.find_asset_data(old)
    left_cls = str(left.asset_class_path.asset_name) if left.is_valid() else ""
    refs = eal.find_package_referencers_for_asset(new, False) or []
    ok = obj is not None and not left_cls
    return ok, f"{'OK  ' if ok else 'BAD '} {new} class={obj.get_class().get_name() if obj else 'NOT LOADED'} " \
               f"referencers={len(refs)} old={'gone' if not left_cls else left_cls}"


def main():
    saved = unreal.Paths.project_saved_dir() + "Cleanup/"
    want = os.environ.get("FOA_SET")
    with open(saved + "moves.json", encoding="utf-8") as fh:
        moves = [(m["from"], m["to"]) for m in json.load(fh) if not want or m["set"] == want]
    lines, bad = [], 0
    for old, new in moves:
        ok, line = check(old, new)
        bad += not ok
        lines.append(line)
    with open(saved + "verify_moves.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"verify_moves: {len(moves) - bad} ok, {bad} bad -> {saved}verify_moves.txt")


main()
