"""Install MakeHuman asset-pack zips into the portable Blender's MPFB data dir (what MPFB's 'Install asset pack' button does).
  blender.exe -b --python Tools/MPFB/install_packs.py -- <pack.zip> [<pack.zip> ...]
Refuses a zip with absolute or '..' member paths, and runs MPFB's own pack check first."""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from mpfb_common import args, mpfb  # noqa: E402

LocationService = mpfb("services.locationservice", "LocationService")
AssetService = mpfb("services.assetservice", "AssetService")

data_dir = os.path.realpath(LocationService.get_user_data())
for path in args():
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            dest = os.path.realpath(os.path.join(data_dir, name))
            if os.path.isabs(name) or not dest.startswith(data_dir + os.sep):
                raise SystemExit(f"unsafe member {name!r} in {path}")
        problem = AssetService.check_asset_pack_zip(path)
        if problem:
            raise SystemExit(f"MPFB rejects {path}: {problem}")
        zf.extractall(data_dir)
    print("installed", os.path.basename(path), "->", data_dir)
AssetService.update_all_asset_lists()
print("packs:", AssetService.get_pack_names())
