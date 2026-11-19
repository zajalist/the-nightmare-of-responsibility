"""Configure six existing/new owned text components only. Preserve shelf action."""
def main():
    import importlib,json,sys
    from pathlib import Path
    import unreal
    sys.path.insert(0,'P:/FoA/Tools/Unreal/level2')
    import stop_set_data as data
    importlib.reload(data)
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    bp=unreal.load_asset(data.BP);assert bp
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(bp)
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    hs={str(lib.get_variable_name(lib.get_data(h))):h for h in sub.k2_gather_subobject_data_for_blueprint(bp)}
    obj=lambda name:lib.get_object_for_blueprint(lib.get_data(hs[name]),bp)
    source=obj('LabelText0');font=source.get_editor_property('font');material=source.get_material(0)
    rows=[]
    for name,parent,line,at,size in data.SIGNS:
        if not name.startswith(('LabelText','StockText')):continue
        assert name in hs,'Declare stock text with the scoped skeleton step'
        component=obj(name);assert sub.attach_subobject(hs[parent],hs[name])
        component.set_absolute(False,False,True)
        component.set_editor_property('relative_scale3d',unreal.Vector(1,1,1))
        component.set_editor_property('relative_location',unreal.Vector(*((-55,0,0) if name.startswith('LabelText') else at)))
        component.set_editor_property('relative_rotation',unreal.Rotator(yaw=180))
        component.set_font(font);component.set_text_material(material)
        component.set_text(unreal.Text(line));component.set_world_size(size)
        component.set_text_render_color(unreal.Color(245,245,245,255) if name.startswith('StockText') else unreal.Color(12,12,12,255))
        component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
        component.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        rows.append(dict(component=name,parent=parent,text=line,size=size))
    assert len(rows)==6
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp,False)
    Path('P:/FoA/Saved/Integration/city_ui/stock_labels.json').write_text(json.dumps(rows,indent=2))
    print('Three shelf names match three stock fronts; original alignment action untouched')


if __name__=='__main__':main()
