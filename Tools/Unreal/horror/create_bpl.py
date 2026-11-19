"""Creates /Game/FoA/Audio/BPL_FoAAudio as a real Blueprint Function Library (so its functions get a world context and
can be called from anim notifies), if it doesn't exist. build_audio_lib.py then fills it through Hayba.
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/create_bpl.py"""
import unreal


def main():
    if unreal.EditorAssetLibrary.does_asset_exist('/Game/FoA/Audio/BPL_FoAAudio'):
        print('exists')
        return
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BPL_FoAAudio', '/Game/FoA/Audio', unreal.Blueprint,
                                                                 unreal.BlueprintFunctionLibraryFactory())
    unreal.EditorAssetLibrary.save_asset('/Game/FoA/Audio/BPL_FoAAudio', only_if_is_dirty=False)
    print('created', bp.get_path_name(), bp.get_editor_property('blueprint_type'))


main()
