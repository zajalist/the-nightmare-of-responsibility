"""Tactile UI set (/Game/FoA/Audio/SFX/UI/SFX_UI_*_A): SoundClass SC_UI, saved.
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/ui_sound_class.py"""
import unreal


def main():
    sc = unreal.load_asset('/Game/FoA/Audio/Mix/SC_UI')
    n = 0
    for p in unreal.EditorAssetLibrary.list_assets('/Game/FoA/Audio/SFX/UI', recursive=False, include_folder=False):
        if not p.split('.')[0].endswith('_A'):
            continue
        w = unreal.load_asset(p)
        w.set_editor_property('sound_class_object', sc)
        unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)
        n += 1
        print(p.split('.')[0], round(w.get_editor_property('duration'), 3))
    print('set SC_UI on', n)


main()
