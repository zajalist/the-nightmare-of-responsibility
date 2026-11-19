"""Build-size levers on world-owned runtime textures (cleanup_plan.md, 2026-11-09):
  FOA_TEX=cap    MaxTextureSize 1024 on the small props that ship 2K maps (the source stays 2K on disk).
  FOA_TEX=probe  Read-only: for every world G8 grayscale map, the materials that sample it and their sampler types
                 (BC4 needs the sampler type changed from Grayscale to Alpha in the same step, or the materials fail).
  $env:FOA_AREAS='/Game/FoA/Props,/Game/FoA/Lux3D'; python Tools/Unreal/ue_remote.py Tools/Lux3D/texture_levers.py FOA_TEX=cap
Prints before -> after for each texture; saves only what it changed."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
REG = unreal.AssetRegistryHelpers.get_asset_registry()


def referencers(path):
    """Package referencers from the asset registry (EAL.find_package_referencers_for_asset came back empty after the
    2026-11-09 21:50 restart while the registry was right)."""
    return [str(r) for r in (REG.get_referencers(path.split('.')[0], unreal.AssetRegistryDependencyOptions()) or [])]
CAP = [  # audit.json 'oversized' (class a, small prop, 2048 > 1024 limit)
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_cover_metallic-book_encyclopedia_set_01_cover_roughness',
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_paper_nor_gl',
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_cover_diff',
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_paper_diff',
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_cover_nor_gl',
    '/Game/FoA/Props/book_encyclopedia_set_01/book_encyclopedia_set_01_2k/Textures/book_encyclopedia_set_01_paper_roughness',
    '/Game/FoA/Lux3D/picture_frame/T_Lux3D_PictureFrame_BaseColor',
    '/Game/FoA/Lux3D/picture_frame/T_Lux3D_PictureFrame_MetallicRoughness',
    '/Game/FoA/Lux3D/bedside_book_stack/T_Lux3D_BedsideBookStack_BaseColor',
    '/Game/FoA/Lux3D/bedside_book_stack/T_Lux3D_BedsideBookStack_MetallicRoughness',
    '/Game/FoA/Lux3D/door_key/T_Lux3D_DoorKey_BaseColor',
    '/Game/FoA/Lux3D/door_key/T_Lux3D_DoorKey_MetallicRoughness',
    '/Game/FoA/Lux3D/wire_hanger/T_Lux3D_WireHanger_BaseColor',
    '/Game/FoA/Lux3D/wire_hanger/T_Lux3D_WireHanger_MetallicRoughness',
]
G8_ROOTS = ('/Game/FoA/Textures', '/Game/FoA/Fireplace', '/Game/FoA/Decals')


def cap():
    for p in CAP:
        t = EAL.load_asset(p)
        if not t:
            print('missing', p)
            continue
        before = t.get_editor_property('max_texture_size')
        if before != 1024:
            t.set_editor_property('max_texture_size', 1024)
            EAL.save_asset(p, only_if_is_dirty=False)
        print(f'{p.rsplit("/", 1)[1]}: max {before} -> 1024')


def g8_textures():
    for root in G8_ROOTS:
        for p in EAL.list_assets(root, recursive=True, include_folder=False):
            t = EAL.load_asset(p)
            if isinstance(t, unreal.Texture2D) and t.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_GRAYSCALE:
                yield p.split('.')[0], t


def probe():
    """Every G8 map, its sRGB flag, and every material expression that samples it (directly or as a parameter
    default), with the sampler type. Material instances are listed with the parent they override."""
    tex = dict(g8_textures())
    users = {}
    for p, t in tex.items():
        print('G8', p, t.blueprint_get_size_x(), 'srgb', t.get_editor_property('srgb'))
        for u in referencers(p):
            users.setdefault(str(u), set()).add(p)
    for u, ts in sorted(users.items()):
        a = EAL.load_asset(u)
        if isinstance(a, unreal.MaterialInstanceConstant):
            print('  MI', u, 'parent', a.get_editor_property('parent').get_path_name().split('.')[0], 'uses', sorted(x.rsplit('/', 1)[1] for x in ts))
        elif isinstance(a, (unreal.Material, unreal.MaterialFunction)):
            print('  MAT', u, 'uses', sorted(x.rsplit('/', 1)[1] for x in ts))
        else:
            print('  OTHER', u, a.get_class().get_name())


DUPES = [  # audit.json duplicate_textures (same source pixels): (keep, drop)
    ('/Game/FoA/Props/brass_candleholders/brass_candleholders_1k/Textures/brass_candleholders_flame_diff',
     '/Game/FoA/Props/brass_candleholders/brass_candleholders_1k/Textures/brass_candleholders_flame_diff1'),
    ('/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_diff',
     '/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_diff1'),
    ('/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_metal-desk_lamp_arm_01_rough',
     '/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_metal-desk_lamp_arm_01_rough1'),
    ('/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_nor_gl',
     '/Game/FoA/Props/desk_lamp_arm_01/desk_lamp_arm_01_1k/Textures/desk_lamp_arm_01_nor_gl1'),
]


def dedupe():
    """Point every material instance that samples a duplicate copy at the surviving texture; list the orphans."""
    MEL = unreal.MaterialEditingLibrary
    for keep, drop in DUPES:
        k = EAL.load_asset(keep)
        for pkg in referencers(drop):
            mi = EAL.load_asset(str(pkg))
            if not isinstance(mi, unreal.MaterialInstanceConstant):
                print('not an MI, left as is:', pkg)
                continue
            for name in MEL.get_texture_parameter_names(mi):
                if MEL.get_material_instance_texture_parameter_value(mi, name) == EAL.load_asset(drop):
                    MEL.set_material_instance_texture_parameter_value(mi, name, k)
                    print('repointed', pkg, name, '->', keep.rsplit('/', 1)[1])
            EAL.save_asset(str(pkg), only_if_is_dirty=False)
        left = list(referencers(drop))
        print('ORPHAN' if not left else 'STILL USED', drop, left)


BC4_FAMILIES = {  # master -> texture parameters whose maps go G8 -> BC4 (all their MIs must carry G8/BC4 maps there)
    '/Game/FoA/Materials/M_Surface': ('Roughness', 'AO'),          # converted 2026-11-09 15:18
    '/Game/FoA/Decals/Materials/M_Decal_Wear': ('Mask',),
    '/Game/FoA/Decals/Materials/M_Decal_Wear_Normal': ('Mask',),
    '/Game/FoA/Fireplace/Materials/M_Fireplace': ('RoughnessTex',),
}


def family_check():
    """Read-only, before any BC4 switch: for each family master, every MI under it and the compression of the texture
    each MI puts on the converted parameters. A family converts only if every one of them is G8 (or already BC4)."""
    MEL = unreal.MaterialEditingLibrary
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
        ['/Game/FoA/Materials', '/Game/FoA/Decals', '/Game/FoA/Fireplace', '/Game/FoA/Textures'], True)   # fresh editor: registry may lag
    ok_all, todo, blocked = True, {}, {}
    for master, params in BC4_FAMILIES.items():
        mats = [str(u) for u in referencers(master)]
        print('FAMILY', master, 'params', params, 'MIs', len(mats))
        for u in mats:
            mi = EAL.load_asset(u)
            if not isinstance(mi, unreal.MaterialInstanceConstant):
                continue
            for p in params:
                t = MEL.get_material_instance_texture_parameter_value(mi, p)
                c = t.get_editor_property('compression_settings') if t else None
                good = c in (unreal.TextureCompressionSettings.TC_GRAYSCALE, unreal.TextureCompressionSettings.TC_ALPHA)
                ok_all &= good
                print('   ', u.rsplit('/', 1)[1], p, t.get_name() if t else None, str(c).split('.')[-1], 'ok' if good else 'BLOCKS')
                if t and c == unreal.TextureCompressionSettings.TC_GRAYSCALE:
                    todo.setdefault(master, set()).add(t.get_path_name().split('.')[0])
                if not good:
                    blocked.setdefault(master, []).append(f'{u} {p} {t.get_name() if t else None} {c}')
    import json
    json.dump({'todo': {k: sorted(v) for k, v in todo.items()}, 'blocked': blocked},
              open('P:/FoA/Saved/WorldShots/bc4_families.json', 'w'), indent=1)
    print('ALL FAMILIES CONVERTIBLE' if ok_all else 'SOME FAMILY BLOCKED', '-> Saved/WorldShots/bc4_families.json')


def bc4():
    """Switch the G8 maps of the checked families to TC_Alpha (BC4, linear). The masters' sampler types are changed to
    Alpha through Hayba material_set_node in the same pass (MaterialTexture.ush: Alpha and LinearGrayscale both read .rrrr,
    so shading is identical). FOA_TEX_LIST = comma list of texture paths."""
    for p in [x for x in os.environ.get('FOA_TEX_LIST', '').split(',') if x]:
        t = EAL.load_asset(p)
        before = str(t.get_editor_property('compression_settings')).split('.')[-1]
        t.set_editor_property('srgb', False)
        t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_ALPHA)
        EAL.save_asset(p, only_if_is_dirty=False)
        print(p.rsplit('/', 1)[1], before, '-> TC_ALPHA (BC4)')


{'cap': cap, 'probe': probe, 'dedupe': dedupe, 'family_check': family_check, 'bc4': bc4}[os.environ.get('FOA_TEX', 'probe')]()
