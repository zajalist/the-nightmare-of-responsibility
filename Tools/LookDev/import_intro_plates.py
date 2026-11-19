"""Import (or re-import in place) the intro v3 plates as linear BC7 UI textures (story lane).
  $env:FOA_AREAS='/Game/FoA/UI/Intro'; python Tools/Unreal/ue_remote.py Tools/LookDev/import_intro_plates.py
The plates are packed data (luminance, nearness, lit luminance, matte), so sRGB is off, no mips, never streamed."""
import glob
import os

import unreal

DEST = '/Game/FoA/UI/Intro/Textures'
files = sorted(glob.glob('P:/FoA/Saved/StoryShots/intro/plates/T_IntroPlate_*.png'))
assert files, 'run Tools/LookDev/intro_plates.py first'
tasks = []
for f in files:
    t = unreal.AssetImportTask()
    for k, v in (('filename', f), ('destination_path', DEST), ('replace_existing', True), ('automated', True), ('save', False)):
        t.set_editor_property(k, v)
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for f in files:
    path = DEST + '/' + os.path.splitext(os.path.basename(f))[0]
    tex = unreal.load_asset(path)
    assert tex, path
    for k, v in (('srgb', False), ('compression_settings', unreal.TextureCompressionSettings.TC_BC7),
                 ('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI), ('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                 ('never_stream', True), ('max_texture_size', 2048)):
        tex.set_editor_property(k, v)
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    print('plate', path, tex.blueprint_get_size_x(), tex.blueprint_get_size_y())
