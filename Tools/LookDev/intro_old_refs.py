"""Read-only: which pre-v3 intro assets still have referencers (cleanup list for main). -> Saved/StoryShots/intro_old_refs.json"""
import json
import unreal
reg = unreal.AssetRegistryHelpers.get_asset_registry()
paths = [str(d.package_name) for d in reg.get_assets_by_path('/Game/FoA/UI/Intro/Textures', False)
         if not str(d.asset_name).startswith('T_IntroPlate_')]
paths += ['/Game/FoA/UI/Materials/M_UI_Panel', '/Game/FoA/UI/Materials/MI_UI_PanelNear']
out = {p: [str(r) for r in unreal.EditorAssetLibrary.find_package_referencers_for_asset(p, False)] for p in paths}
open('P:/FoA/Saved/StoryShots/intro_old_refs.json', 'w').write(json.dumps(out, indent=1))
print({p.rsplit('/', 1)[-1]: len(r) for p, r in out.items()})
