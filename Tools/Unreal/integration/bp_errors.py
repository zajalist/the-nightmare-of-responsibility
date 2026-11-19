"""Integration lane: pull every Blueprint runtime/compile error and warning out of an editor log (offline).
  python Tools/Unreal/integration/bp_errors.py [log] [--since HH.MM.SS] [--pie-only] [--csv out.csv]
Default log: Saved/Logs/FoA.log. Groups identical messages (timestamps and frame counters stripped) and prints the
count, category, asset, function and node per group, most frequent first."""
import argparse
import collections
import csv
import re

PAT = re.compile(r'Blueprint Runtime Error|Accessed None|Infinite loop|LogScript: (Error|Warning)|LogBlueprint: (Error|Warning)'
                 r"|LogBlueprintUserMessages|\[Compiler\]|Failed to find object|Failed to load '/Game|Cast failed|"
                 r'LogK2Compiler|LogBlueprintCompile|Attempted to access .* via property|is not valid|'
                 r'LogUObjectGlobals: Warning|LogLinker: Warning|LogStreaming: Error', re.I)
STAMP = re.compile(r'^\[[^\]]*\]\[[ \d]*\]')


def category(msg):
    for key, name in (('missing NodeGuid', 'NodeGuid'), ('Accessed None', 'AccessedNone'), ('Infinite loop', 'InfiniteLoop'), ('Failed to find', 'MissingAsset'),
                      ('Failed to load', 'MissingAsset'), ('[Compiler]', 'Compile'), ('LogK2Compiler', 'Compile'),
                      ('Cast', 'Cast'), ('Runtime Error', 'Runtime')):
        if key.lower() in msg.lower():
            return name
    return 'Other'


def where(msg):
    bp = re.search(r'(?<!Log)Blueprint:\s+(\S+)', msg)
    fn = re.search(r'Function:\s+(.+?)\s+Blueprint:', msg)
    node = re.search(r'Node:\s+(.+?)\s+Graph:', msg)
    path = re.search(r"/Game/[\w/]+?/(\w+)(?:\.|'|\s|$)", msg) or re.search(r"\\(\w+)\.uasset", msg)
    return (bp.group(1) if bp else (path.group(1) if path else ''), fn.group(1) if fn else '', node.group(1) if node else '')


def scan(log, since=None, pie_only=False):
    groups = collections.Counter()
    first = {}
    with open(log, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if since and line[:1] == '[' and line[12:20] < since:
                continue
            if not PAT.search(line) or 'LogHayba' in line:
                continue
            if pie_only and 'PIE' not in line and 'LogScript' not in line:
                continue
            msg = STAMP.sub('', line.strip())
            groups[msg] += 1
            first.setdefault(msg, line[1:24])
    return groups, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log', nargs='?', default='P:/FoA/Saved/Logs/FoA.log')
    ap.add_argument('--since', help='HH.MM.SS (log clock, UTC)')
    ap.add_argument('--pie-only', action='store_true')
    ap.add_argument('--csv')
    a = ap.parse_args()
    groups, first = scan(a.log, a.since, a.pie_only)
    rows = [(n, category(m), *where(m), first[m], m[:300]) for m, n in groups.most_common()]
    for r in rows:
        print(f'{r[0]:6d} {r[1]:12s} {r[2]:28s} {r[3][:28]:28s} {r[6][:150]}')
    agg = collections.Counter()
    for r in rows:
        agg[(r[1], r[2])] += r[0]
    print('--- by category and asset')
    for (cat, asset), n in sorted(agg.items(), key=lambda kv: -kv[1]):
        print(f'{n:6d} {cat:12s} {asset}')
    print('total', sum(groups.values()), 'unique', len(groups))
    if a.csv:
        with open(a.csv, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['count', 'category', 'asset', 'function', 'node', 'first', 'message'])
            w.writerows(rows)


if __name__ == '__main__':
    main()
