"""Reimport assets (SoundWaves, textures) in place from new source files (same asset path, so every reference keeps working).
  $env:FOA_AREAS='Audio'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/reimport_waves.py FOA_WAVES=/Game/.../SFX_X@P:/.../SFX_X.wav,...
Prints each wave's duration (or texture size) before and after; existing import settings are kept."""
import os

import unreal


def info(a):
    if isinstance(a, unreal.SoundWave):
        return f"{a.get_editor_property('duration'):.3f} s"
    if isinstance(a, unreal.Texture2D):
        return f'{a.blueprint_get_size_x()}x{a.blueprint_get_size_y()} srgb={a.get_editor_property("srgb")}'
    return a.get_class().get_name() if a else None


def main():
    for spec in [s for s in os.environ['FOA_WAVES'].split(',') if s]:
        asset, src = spec.split('@')
        old = unreal.load_asset(asset)
        before = info(old)
        folder, name = asset.rsplit('/', 1)
        t = unreal.AssetImportTask()
        for k, v in (('filename', src), ('destination_path', folder), ('destination_name', name), ('automated', True),
                     ('replace_existing', True), ('replace_existing_settings', False), ('save', True)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        new = unreal.load_asset(asset)
        print('reimported', asset, before, '->', info(new))


main()
