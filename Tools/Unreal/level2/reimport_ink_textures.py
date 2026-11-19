"""Reimport only the two owned procedural UI masks, preserving their references."""
def main():
    import unreal
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    for name in ('T_L2InkPanel','T_L2InkTag'):
        path='/Game/FoA/Level2/UI/'+name
        texture=unreal.load_asset(path);assert texture,path
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(texture)
        task=unreal.AssetImportTask()
        for key,value in dict(filename='P:/FoA/Tools/Textures/level2/'+name+'.png',destination_path='/Game/FoA/Level2/UI',
                              replace_existing=True,automated=True,save=True).items():task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assert task.imported_object_paths,name
        texture=unreal.load_asset(path)
        texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        assert unreal.EditorAssetLibrary.save_loaded_asset(texture,False),path
    print('Two owned UI masks reimported and saved')


if __name__=='__main__':main()
