"""Read-only: who references each asset in /Game/FoA/UI/Intro (asset registry, the rule-checked way).
  python Tools/Unreal/integration/run_read.py Tools/LookDev/intro_v4/probe_refs.py   -> Saved/QA/lanes/intro/refs.json"""
import json

import unreal

reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.scan_paths_synchronous(['/Game/FoA/UI/Intro'], True)
opts = unreal.AssetRegistryDependencyOptions()
out = {}
for a in reg.get_assets_by_path('/Game/FoA/UI/Intro', recursive=True):
    pkg = str(a.package_name)
    out[pkg] = sorted(str(r) for r in reg.get_referencers(pkg, opts) or [])
with open('P:/FoA/Saved/QA/lanes/intro/refs.json', 'w') as f:
    json.dump(out, f, indent=1)
print(json.dumps({k: v for k, v in out.items()}, indent=0)[:3000])
