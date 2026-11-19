"""Size report of an IoStore container: biggest folders, packages and asset kinds.
  python Tools/Perf/pak_sizes.py <listing.csv> [--depth 4] [--n 40]
Make the listing with: UnrealPak.exe <Game-Windows.utoc> -List -csv=<listing.csv>
Sizes are stored (compressed) bytes, so they add up to the .ucas size."""
import argparse
import collections
import csv
import re


def load(path):
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh, skipinitialspace=True):
            name = r['Filename'].replace('../../../', '/')
            rows.append((name, int(r['Size'])))
    return rows


def package(name):
    return re.sub(r'\.(uasset|uexp|ubulk|uptnl|umap|m\.ubulk|ushaderbytecode|ufont)$', '', name)


def report(rows, depth=4, n=40):
    total = sum(s for _, s in rows)
    mb = lambda b: f'{b / 1048576:8.1f}'  # noqa: E731
    print(f'total {mb(total)} MB in {len(rows)} chunks')
    for title, key in (('folders', lambda x: '/'.join(x.split('/')[:depth + 1])),
                       ('packages', package),
                       ('kinds', lambda x: x.rsplit('.', 1)[-1])):
        agg = collections.Counter()
        for name, size in rows:
            agg[key(name)] += size
        print(f'== top {title}')
        for k, v in agg.most_common(n):
            print(f'{mb(v)} MB  {k}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--depth', type=int, default=4)
    ap.add_argument('--n', type=int, default=40)
    a = ap.parse_args()
    rows = load(a.csv)
    assert rows and all(s >= 0 for _, s in rows), 'empty or bad listing'
    report(rows, a.depth, a.n)
