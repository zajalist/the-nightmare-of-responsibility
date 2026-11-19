"""Read-only: which Lux3D generations ship. For every item in P:/FoA-Assets/lux3d/_state.json, the /Game assets whose
path or name carries the item's slug, and whether the level (or a Blueprint the level uses) references them.
  $env:FOA_AREAS='/Game/FoA/Lux3D'; python Tools/Unreal/ue_remote.py Tools/Lux3D/lux3d_usage.py
Writes Saved/WorldShots/lux3d/usage.json (feeds docs/design/world/lux3d_log.md)."""
import json

import unreal

EAL = unreal.EditorAssetLibrary

def refs(path):
    """Package referencers from the asset registry (EAL.find_package_referencers_for_asset can come back empty)."""
    return [str(r) for r in (unreal.AssetRegistryHelpers.get_asset_registry().get_referencers(
        str(path).split('.')[0], unreal.AssetRegistryDependencyOptions()) or [])]

state = json.load(open('P:/FoA-Assets/lux3d/_state.json', encoding='utf-8'))
roots = ('/Game/FoA/Lux3D', '/Game/FoA/Props', '/Game/FoA/VFX/Splats/Meshes', '/Game/FoA/Gameplay', '/Game/FoA/Characters')
paths = [p.split('.')[0] for r in roots for p in EAL.list_assets(r, recursive=True, include_folder=False)]
LEVEL = '/Game/FoA/Maps/L_Tutorial_Bedroom'
out = {}
for slug, row in state.items():
    keys = {slug, slug.replace('_', ''), slug.split('_')[0] + '_' + slug.split('_')[-1]}
    hits = [p for p in paths if any(k.lower() in p.lower().replace('-', '_') for k in keys)
            and isinstance(EAL.load_asset(p), (unreal.StaticMesh, unreal.SkeletalMesh))]
    used = []
    for h in hits:
        refs = refs(h)
        used.append({'mesh': h, 'referencers': refs[:6], 'in_level': LEVEL in refs})
    out[slug] = {'task': row.get('task'), 'item': row.get('item'), 'meshes': used}
    print(slug, row.get('task'), [(u['mesh'].rsplit('/', 1)[1], u['in_level'], len(u['referencers'])) for u in used])
with open('P:/FoA/Saved/WorldShots/lux3d/usage.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, indent=1)
