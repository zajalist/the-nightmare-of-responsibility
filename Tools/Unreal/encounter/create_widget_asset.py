"""Creates /Game/FoA/Gameplay/Encounter/WBP_Encounter once, with a CanvasPanel root named RootCanvas (Hayba
ui_build_tree then fills it from gen_encounter_tree.py). Run via ue_remote.py."""
import unreal

PATH = '/Game/FoA/Gameplay/Encounter/WBP_Encounter'
if not unreal.EditorAssetLibrary.does_asset_exist(PATH):
    fac = unreal.WidgetBlueprintFactory()
    fac.set_editor_property('parent_class', unreal.UserWidget)
    try:
        fac.set_editor_property('root_widget_class', unreal.CanvasPanel)
    except Exception as e:  # older factories make no root; ui_build_tree would then need one
        print('root_widget_class not set:', e)
    wbp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_Encounter', '/Game/FoA/Gameplay/Encounter',
                                                                   unreal.WidgetBlueprint, fac)
    assert wbp, 'create failed'
    unreal.EditorAssetLibrary.save_loaded_asset(wbp, False)
print('WBP_Encounter', unreal.EditorAssetLibrary.does_asset_exist(PATH))
