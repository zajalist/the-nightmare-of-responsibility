"""Read-only: list the MetaHuman Creator Python API (subsystem methods, character methods, preset assets)."""
import unreal
sub = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
print("MH_API sub", [m for m in dir(sub) if not m.startswith("_")])
print("MH_API char", [m for m in dir(unreal.MetaHumanCharacter) if not m.startswith("_")][:120])
reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.scan_paths_synchronous(["/MetaHumanCharacter/Optional/Presets"], True)
print("MH_API presets", [(str(a.asset_name), str(a.asset_class_path.asset_name)) for a in reg.get_assets_by_path("/MetaHumanCharacter/Optional/Presets", recursive=True)][:60])
