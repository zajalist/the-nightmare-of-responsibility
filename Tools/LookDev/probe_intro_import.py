import json,unreal
from pathlib import Path
ar=unreal.AssetRegistryHelpers.get_asset_registry();p='/Game/FoA/UI/Intro/Textures/T_Intro_Game01_Sleep'
r={'registry':[str(a.object_path) if hasattr(a,'object_path') else str(a.package_name) for a in ar.get_assets_by_path('/Game/FoA/UI/Intro/Textures',False)],'exists':unreal.EditorAssetLibrary.does_asset_exist(p),'package':str(unreal.find_object(None,p)),'object':str(unreal.find_object(None,p+'.T_Intro_Game01_Sleep'))}
Path('P:/FoA/Saved/LookDev/intro_ingame/import_probe.json').write_text(json.dumps(r,indent=1))
