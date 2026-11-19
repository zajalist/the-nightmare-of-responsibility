"""Imports + saves the UI lane's textures (source PNGs live in Tools/Textures/ui), then reports the fonts lane's
composite fonts so text styles can reference the right typeface names. Run via ue_remote.py."""
import os
import unreal

SRC = 'P:/FoA/Tools/Textures/ui'
DST = '/Game/FoA/UI/Textures'
EAL = unreal.EditorAssetLibrary
SETTINGS = {  # name: (compression, srgb)
    'T_UI_SandNoise': (unreal.TextureCompressionSettings.TC_BC7, False),
    'T_UI_Logo_Unreal': (unreal.TextureCompressionSettings.TC_EDITOR_ICON, True),
}
tasks = []
for name in SETTINGS:
    if not EAL.does_asset_exist(f'{DST}/{name}'):
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', os.path.join(SRC, name + '.png'))
        t.set_editor_property('destination_path', DST)
        t.set_editor_property('automated', True)
        t.set_editor_property('save', True)
        tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for name, (comp, srgb) in SETTINGS.items():
    tex = unreal.load_asset(f'{DST}/{name}')
    tex.set_editor_property('compression_settings', comp)
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('never_stream', True)
    if name.startswith('T_UI_Logo_'):
        tex.set_editor_property('max_texture_size', 512)
    print('saved', name, EAL.save_loaded_asset(tex, False))

for f in ('F_FoA_Display', 'F_FoA_UI', 'F_FoA_Mono', 'F_FoA_Typography'):
    font = unreal.load_asset(f'/Game/FoA/UI/Fonts/{f}')
    cf = font.get_editor_property('composite_font') if font else None
    faces = [str(tf.get_editor_property('name')) for tf in cf.get_editor_property('default_typeface').get_editor_property('fonts')] if cf else []
    subs = [str(s.get_editor_property('typeface').get_editor_property('fonts')[0].get_editor_property('name'))
            for s in cf.get_editor_property('sub_typefaces')] if cf else []
    print(f, 'typefaces:', faces, 'subs:', len(subs))
