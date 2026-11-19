"""Pre-cook check: packages saved recently that reference a /Game package missing on disk (a rename saved without its
redirector). On 11-18 at 14:39 four Level 2 animations still pointed at /Fbx/*_Skeleton after the skeletons were
renamed, and the cook crashed (AnimSequence.cpp !Hash.IsZero()).
  python Tools/Perf/ref_check.py [--hours 24] [--root P:/FoA/Content]
Exit 1 and a list when anything dangles."""
import argparse
import re
import sys
import time
from pathlib import Path

REF = re.compile(rb'/Game/[A-Za-z0-9_/\-]+')


def missing_refs(path, content):
    """/Game package paths named in this package that exist neither as a package nor as a folder."""
    out = set()
    for m in set(REF.findall(path.read_bytes())):
        rel = m.decode()[len('/Game/'):].rstrip('/')
        base = content / rel
        if base.with_suffix('.uasset').exists() or base.with_suffix('.umap').exists() or base.is_dir():
            continue
        # FNames keep a numeric suffix outside the string: textured_texture_0 is stored as "textured_texture" + 1
        if base.parent.is_dir() and any(re.fullmatch(re.escape(base.name) + r'_\d+\.(uasset|umap)', f.name)
                                        for f in base.parent.iterdir()):
            continue
        out.add(m.decode())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=float, default=24)
    ap.add_argument('--root', default='P:/FoA/Content')
    a = ap.parse_args()
    content = Path(a.root)
    since = time.time() - a.hours * 3600
    bad = {}
    n = 0
    for p in content.rglob('*'):
        if p.suffix in ('.uasset', '.umap') and p.stat().st_mtime >= since:
            n += 1
            miss = missing_refs(p, content)
            if miss:
                bad[str(p.relative_to(content))] = sorted(miss)
    print(f'{n} packages saved in the last {a.hours:g} h; {len(bad)} reference missing packages')
    for k, v in sorted(bad.items()):
        print(f'  {k}: {", ".join(v)}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
