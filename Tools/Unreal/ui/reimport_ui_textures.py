"""Re-imports UI textures from Tools/Textures/ui (replacing existing assets) and saves them. Run via ue_remote.py.
FOA_TEX=name,name to subset. Logos keep mips + trilinear so they stay anti-aliased when shown below native size."""
import os
import unreal

EAL = unreal.EditorAssetLibrary
TC = unreal.TextureCompressionSettings
JOBS = {  # file stem: (destination folder, compression, srgb, mips)
    'T_UI_SandNoise': ('/Game/FoA/UI/Textures', TC.TC_BC7, False, False),
    'T_UI_Logo_Unreal': ('/Game/FoA/UI/Textures', TC.TC_EDITOR_ICON, True, True),   # TC_EDITOR_ICON = UserInterface2D
    'T_UI_Logo_Hayba': ('/Game/FoA/UI/Textures', TC.TC_EDITOR_ICON, True, True),
}
ONLY = [s for s in os.environ.get('FOA_TEX', '').split(',') if s]
JOBS = {k: v for k, v in JOBS.items() if not ONLY or k in ONLY}
REIMPORT = [s for s in os.environ.get('FOA_REIMPORT', '').split(',') if s]  # only these get the source re-read

tasks = []
for stem, (dst, *_rest) in JOBS.items():
    if stem not in REIMPORT and EAL.does_asset_exist(f'{dst}/{stem}'):
        continue
    t = unreal.AssetImportTask()
    for k, v in (('filename', f'P:/FoA/Tools/Textures/ui/{stem}.png'), ('destination_path', dst),
                 ('replace_existing', True), ('automated', True), ('save', False)):
        t.set_editor_property(k, v)
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for stem, (dst, comp, srgb, mips) in JOBS.items():
    tex = unreal.load_asset(f'{dst}/{stem}')
    for k, v in (('compression_settings', comp), ('srgb', srgb), ('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI),
                 ('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE if mips
                  else unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                 ('filter', unreal.TextureFilter.TF_TRILINEAR if mips else unreal.TextureFilter.TF_DEFAULT),
                 ('never_stream', True)):
        tex.set_editor_property(k, v)
    if stem.startswith('T_UI_Logo_'):
        tex.set_editor_property('max_texture_size', 512)
    print(stem, tex.blueprint_get_size_x(), 'mips' if mips else 'no mips', 'saved',
          EAL.save_asset(f'{dst}/{stem}', only_if_is_dirty=False))
