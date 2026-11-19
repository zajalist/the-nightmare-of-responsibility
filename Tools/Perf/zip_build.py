"""Zip a packaged build the way a player gets it (deflate, like Explorer's "Compressed folder"), and report sizes.
  python Tools/Perf/zip_build.py P:/FoA-Builds/<Config>_<stamp>   -> P:/FoA-Builds/<Config>_<stamp>.zip
bsdtar's `tar -a -cf x.zip` stored the files uncompressed, so pack.sh calls this instead."""
import sys
import zipfile
from pathlib import Path

build = Path(sys.argv[1])
assert (build / 'Windows').is_dir(), f'not a packaged build: {build}'
dest = build.with_suffix('.zip')
raw = 0
with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for f in sorted((build / 'Windows').rglob('*')):
        if f.is_file():
            raw += f.stat().st_size
            z.write(f, f.relative_to(build))
size = dest.stat().st_size
print(f'{dest}: {size / 1e6:.1f} MB ({size / 2**20:.1f} MiB) from {raw / 1e6:.1f} MB of files')
assert zipfile.ZipFile(dest).testzip() is None
