"""Read-only: every asset under /Game/FoA/Characters/Protagonist with asset-registry referencer counts, split into
referencers inside the folder and outside it (an asset only referenced from inside goes with the folder).
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/probe_protagonist.py -> Saved/FaceShots/protagonist_refs.json"""
import json

import unreal

ROOT = '/Game/FoA/Characters/Protagonist'


def run():
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    reg.scan_paths_synchronous([ROOT], True)
    assets = reg.get_assets_by_path(ROOT, recursive=True)
    rows = []
    for a in assets:
        pkg = str(a.package_name)
        refs = [str(r) for r in (reg.get_referencers(pkg, unreal.AssetRegistryDependencyOptions()) or []) if str(r) != pkg]
        outside = [r for r in refs if not r.startswith(ROOT + '/')]
        rows.append(dict(path=pkg, cls=str(a.asset_class_path.asset_name), refs=len(refs), outside=outside))
    rows.sort(key=lambda r: (len(r['outside']) == 0, r['path']))
    with open('P:/FoA/Saved/FaceShots/protagonist_refs.json', 'w') as f:
        json.dump(rows, f, indent=1)
    print('protagonist assets', len(rows), 'referenced from outside', sum(1 for r in rows if r['outside']))


run()
