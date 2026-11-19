"""Point Tools/ scripts at moved assets: mechanical string replacement driven by Saved/Cleanup/moves.json.

  python Tools/Cleanup/retarget_tools_paths.py --dry-run      # unified diff preview, changes nothing
  python Tools/Cleanup/retarget_tools_paths.py                # apply; prints per-file counts and the diff summary
  python Tools/Cleanup/retarget_tools_paths.py --check        # after moves: py_compile every touched file, and fail
                                                              # if an old path is still named or a new one is missing

Rewrites '/Game/old/Path' and '/Game/old/Path.OldName' (object suffix renamed with the asset), plus the one composed
form in use: f"{LUX}/<item>/..." (LUX = "/Game/FoA/Lux3D", Tools/Unreal/gameplay/data_rows.py). Tools/Cleanup is
skipped. Run it in the move window right after move_assets.py, so scripts and Content change together.
"""
import argparse
import difflib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PLAN = os.path.join(ROOT, "Saved", "Cleanup", "moves.json")
EXTS = (".py", ".sh", ".ps1", ".json", ".txt")
PREFIX_VARS = {"{LUX}": "/Game/FoA/Lux3D"}  # composed f-string prefixes found by the audit


def rules(moves):
    out = []
    for old, new in moves:
        oname, nname = old.rsplit("/", 1)[1], new.rsplit("/", 1)[1]
        forms = [(old, new)] + [(var + old[len(pre):], var + new[len(pre):])
                                for var, pre in PREFIX_VARS.items() if old.startswith(pre + "/")]
        for o, n in forms:
            # path, optionally followed by .OldName (object) or .OldName_C; never a longer path or name
            rx = re.compile(re.escape(o) + r"(?:\.(" + re.escape(oname) + r")(_C)?)?(?![A-Za-z0-9_/\-])")
            out.append((rx, n, nname))
    return out


def rewrite(text, rs):
    count = 0
    for rx, new, nname in rs:
        text, k = rx.subn(lambda m: new + (("." + nname + (m.group(2) or "")) if m.group(1) else ""), text)
        count += k
    return text, count


def tool_files():
    for dp, dirs, fs in os.walk(os.path.join(ROOT, "Tools")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "Cleanup")]
        for n in fs:
            if n.endswith(EXTS):
                yield os.path.join(dp, n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--set", help="only this move set (A or B)")
    args = ap.parse_args()
    moves = [(m["from"], m["to"]) for m in json.load(open(PLAN, encoding="utf-8")) if not args.set or m["set"] == args.set]
    rs = rules(moves)
    if args.check:
        bad = 0
        for f in tool_files():
            text = open(f, encoding="utf-8", errors="replace").read()
            rel = os.path.relpath(f, ROOT)
            stale = [o for o, _ in moves if re.search(re.escape(o) + r"(?![A-Za-z0-9_/\-])", text)]
            stale += [v + o[len(p):] for o, _ in moves for v, p in PREFIX_VARS.items()
                      if o.startswith(p + "/") and (v + o[len(p):]) in text]
            if stale:
                bad += 1
                print("STILL OLD", rel, stale[:3])
            if any(n in text for _, n in moves) and f.endswith(".py"):
                try:
                    compile(text, f, "exec")  # syntax only; nothing written (py_compile can't target NUL on Windows)
                except SyntaxError as e:
                    bad += 1
                    print("DOES NOT COMPILE", rel, e)
        missing = [n for _, n in moves if not os.path.exists(os.path.join(ROOT, "Content", n[6:] + ".uasset"))]
        for n in missing:
            print("NEW PATH HAS NO FILE", n)
        print(f"check: {bad} problem files, {len(missing)} moved assets missing on disk")
        sys.exit(1 if bad or missing else 0)
    total, files = 0, 0
    for f in tool_files():
        with open(f, "rb") as fh:  # bytes in, bytes out: keeps line endings and any odd encoding byte-exact
            text = fh.read().decode("utf-8", "surrogateescape")
        new, k = rewrite(text, rs)
        if not k:
            continue
        rel = os.path.relpath(f, ROOT).replace(os.sep, "/")
        total += k
        files += 1
        print(f"{k:3d} path(s)  {rel}")
        if args.dry_run:
            sys.stdout.writelines(difflib.unified_diff(text.splitlines(True), new.splitlines(True),
                                                       "a/" + rel, "b/" + rel, n=0))
        else:
            with open(f, "wb") as fh:
                fh.write(new.encode("utf-8", "surrogateescape"))
    print(f"{'would change' if args.dry_run else 'changed'} {total} paths in {files} files")


if __name__ == "__main__":
    main()
