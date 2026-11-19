"""City life lane, read-only: every asset under /Game/FoA/Level2/CityLife has all its package dependencies present
(asset registry), no redirectors remain, and every asset is referenced (from the level, the Blueprint or another of
ours). Writes Saved/QA/lanes/citylife_depcheck.txt."""
import unreal

EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
ROOT = '/Game/FoA/Level2/CityLife'
OPT = unreal.AssetRegistryDependencyOptions()
lines, bad = [], 0
for p in EAL.list_assets(ROOT, recursive=True, include_folder=False):
    pkg = p.split('.')[0]
    a = EAL.load_asset(p)
    cls = a.get_class().get_name()
    deps = [str(d) for d in (AR.get_dependencies(pkg, OPT) or [])]
    missing = [d for d in deps if d.startswith('/Game/') and not EAL.does_asset_exist(d)]
    stale = [d for d in deps if '/Fbx/' in d]
    users = [str(r) for r in (AR.get_referencers(pkg, OPT) or [])]
    flag = 'BAD' if (missing or stale or cls == 'ObjectRedirector') else ('ORPHAN' if not users else 'ok')
    bad += flag != 'ok'
    lines.append(f'{flag} {cls} {pkg} missing={missing} stale={stale} users={users[:3]}')
lines.append(f'{bad} not ok')
open('P:/FoA/Saved/QA/lanes/citylife_depcheck.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
