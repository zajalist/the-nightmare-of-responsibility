"""Read-only: asset-registry referencers of FOA_ASSETS (comma list), the same gate delete_unused.py uses.
  python Tools/Unreal/integration/run_read.py Tools/Unreal/face/probe_refs.py FOA_ASSETS=/Game/A,/Game/B"""
import os

import unreal

reg = unreal.AssetRegistryHelpers.get_asset_registry()
for path in filter(None, os.environ['FOA_ASSETS'].split(',')):
    pkg = path.split('.')[0]
    refs = [str(r) for r in (reg.get_referencers(pkg, unreal.AssetRegistryDependencyOptions()) or []) if str(r) != pkg]
    print('REFS', path, refs)
