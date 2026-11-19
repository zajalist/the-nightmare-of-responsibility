"""Structural MPC creation only. Run via ue_remote inside the Level2 lease."""
import unreal


def run():
    path = '/Game/FoA/Level2/Materials/MPC_L2'
    asset = unreal.load_asset(path) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'MPC_L2', '/Game/FoA/Level2/Materials', unreal.MaterialParameterCollection,
        unreal.MaterialParameterCollectionFactoryNew())
    for prop, cls, values in (
        ('scalar_parameters', unreal.CollectionScalarParameter,
         {'AmbientIntensity': 0., 'SandRadius': 0., 'SandProgress': 0., 'TargetBuilding': -1.}),
        ('vector_parameters', unreal.CollectionVectorParameter,
         {'SandCentre': unreal.LinearColor(0, 0, 0, 0), 'Wind': unreal.LinearColor(0, 0, 0, 0),
          'Impact0': unreal.LinearColor(0, 0, -10000, 0)})):
        entries = list(asset.get_editor_property(prop))
        have = {str(p.get_editor_property('parameter_name')) for p in entries}
        previous_count = len(entries)
        for name, value in values.items():
            if name not in have:
                entry = cls()
                entry.set_editor_property('parameter_name', name)
                entry.set_editor_property('default_value', value)
                entries.append(entry)
        if len(entries) != previous_count:
            asset.set_editor_property(prop, entries)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    print('SPLAT_DYN MPC ready', path)


run()
