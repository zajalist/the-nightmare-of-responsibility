"""Import (or re-import in place) the intro v4 plates (intro lane). Run in two halves, each well under 30 s:
  $env:HAYBA_AGENT_ID='intro'; $env:FOA_AREAS='/Game/FoA/UI/Intro'
  python Tools/Unreal/ue_remote.py Tools/LookDev/intro_v4/import_v4.py INTRO_SET=main INTRO_ONLY=Room   (one 2048 plate)
  python Tools/Unreal/ue_remote.py Tools/LookDev/intro_v4/import_v4.py INTRO_SET=back   (T_IntroPlate_<P>_Back, 1024)
Packed data, so sRGB off and BC7; mips on with trilinear filtering (the shader's focus pulls read fractional mips;
the UI group's point mip filter would step), clamped (the planes slide to the frame's edge), never streamed."""
import glob
import os

import unreal

DEST = '/Game/FoA/UI/Intro/Textures'
SET = os.environ['INTRO_SET']
ONLY = os.environ.get('INTRO_ONLY')  # one plate per run keeps it under 30 s (a 2k BC7 encode with mips is ~10 s)
files = sorted(f for f in glob.glob('P:/FoA/Saved/StoryShots/intro/v4/T_IntroPlate_*.png') if f.endswith('_Back.png') == (SET == 'back')
               and (not ONLY or os.path.basename(f).split('_')[2].split('.')[0] == ONLY))
assert len(files) == (1 if ONLY else 5), files
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
                 ('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI), ('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE),
                 ('filter', unreal.TextureFilter.TF_TRILINEAR), ('address_x', unreal.TextureAddress.TA_CLAMP),
                 ('address_y', unreal.TextureAddress.TA_CLAMP), ('never_stream', True), ('max_texture_size', 2048)):
        tex.set_editor_property(k, v, unreal.PropertyAccessChangeNotifyMode.NEVER)  # one rebuild below, not one per property
    tex.set_editor_property('max_texture_size', 2048, unreal.PropertyAccessChangeNotifyMode.ALWAYS)  # the one PostEditChange
    unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
    print('plate', path, tex.blueprint_get_size_x(), tex.blueprint_get_size_y(), tex.get_editor_property('filter'))
