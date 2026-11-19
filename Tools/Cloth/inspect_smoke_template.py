"""Read engine Niagara templates before making a project-owned smoke variant."""
import unreal
for path in ('/Niagara/DefaultAssets/Templates/Systems/FountainLightweight',):
    asset=unreal.load_asset(path)
    assert asset,path
    obj=unreal.load_object(None,path+'.FountainLightweight:Fountain_1')
    assert obj
    for p in ('spawn_infos','emitter_state','modules','renderer_properties'):
        print(p,obj.get_editor_property(p))
    for m in obj.get_editor_property('modules'):
        print('MODULE',m.get_class().get_name(),m.get_path_name())
        for p in ('lifetime_distribution','sprite_size_distribution','color_distribution','velocity_distribution','gravity_distribution'):
            try:print(p,m.get_editor_property(p))
            except Exception:pass
