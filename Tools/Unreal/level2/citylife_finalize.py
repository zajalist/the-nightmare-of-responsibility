"""City life lane: finish the auto-rigged characters and drop import leftovers (ue_remote, one mode per run).
  CL_MODE=mat     the FBX walker meshes (the retarget FBX: mesh + skeleton + clip) wear the Lux3D glTF material (MI_Lux3D_<Name>)
  CL_MODE=junk    list leftovers and their referencers: the GLB-imported SK/SKEL/PHYS (the clips need the FBX skeleton),
                  the FBX's placeholder Phong MI and 32 px texture, and each import's unused third texture
  CL_MODE=delete  delete the junk list (FOA_EXCLUSIVE=1): only assets whose registry referencers are all in the list
  CL_MODE=rename  FBX assets to SK_/SKEL_/PHYS_/A_Lux3D_<Name>[_<Clip>] next to the material
Names: CL_NAMES=Commuter,Faceless. Statics: CL_STATIC=Briefcase,OfficeChair,..."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
ROOT = '/Game/FoA/Level2/CityLife'
LOG = 'P:/FoA/Saved/QA/lanes/citylife_import.log'


def say(line):
    print(line)
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


def assets(folder):
    return [p.split('.')[0] for p in EAL.list_assets(folder, recursive=True, include_folder=False)]


def refs(pkg):
    return [str(r) for r in (AR.get_referencers(pkg, unreal.AssetRegistryDependencyOptions()) or [])]


def junk():
    out = []
    for name in [n for n in os.environ.get('CL_NAMES', '').split(',') if n]:
        fbx_mesh = any(isinstance(EAL.load_asset(p), unreal.SkeletalMesh) for p in assets(f'{ROOT}/{name}/Fbx'))
        if fbx_mesh:  # before the rename only: then <k>_Lux3D_<Name> is still the GLB import, not the walker
            out += [f'{ROOT}/{name}/{k}_Lux3D_{name}' for k in ('SK', 'SKEL', 'PHYS')
                    if EAL.does_asset_exist(f'{ROOT}/{name}/{k}_Lux3D_{name}')]
        out += [p for p in assets(f'{ROOT}/{name}/Fbx') if isinstance(EAL.load_asset(p), (unreal.MaterialInstance, unreal.Texture2D))]
        out += [p for p in assets(f'{ROOT}/{name}') if '/Textures/' in p]
    for name in [n for n in os.environ.get('CL_STATIC', '').split(',') if n]:
        out += [p for p in assets(f'{ROOT}/{name}') if '/Textures/' in p]
    return out


def main():
    mode = os.environ['CL_MODE']
    names = [n for n in os.environ.get('CL_NAMES', '').split(',') if n]
    if mode == 'mat':
        for name in names:
            mi = EAL.load_asset(f'{ROOT}/{name}/MI_Lux3D_{name}')
            for p in assets(f'{ROOT}/{name}'):
                sk = EAL.load_asset(p)
                if isinstance(sk, unreal.SkeletalMesh):
                    mats = list(sk.get_editor_property('materials'))  # elements are copies: write them back by index
                    for i, m in enumerate(mats):
                        m.set_editor_property('material_interface', mi)
                        mats[i] = m
                    sk.set_editor_property('materials', mats)
                    EAL.save_loaded_asset(sk)
                    now = [m.get_editor_property('material_interface').get_name() for m in sk.get_editor_property('materials')]
                    say(f'mat {p} slots={now}')
    elif mode == 'redirectors':  # FOA_EXCLUSIVE=1: point referencers at the renamed assets, then the redirectors go
        reds = [EAL.load_asset(p) for p in assets(ROOT) if isinstance(EAL.load_asset(p), unreal.ObjectRedirector)]
        say(f'redirectors {len(reds)}')
        if reds:
            unreal.AssetToolsHelpers.get_asset_tools().fixup_referencers(reds)
        say(f'redirectors left {sum(1 for p in assets(ROOT) if isinstance(EAL.load_asset(p), unreal.ObjectRedirector))}')
    elif mode in ('junk', 'delete'):
        doomed = junk()
        for p in doomed:
            outside = [r for r in refs(p) if r not in doomed]
            if mode == 'junk' or outside:
                say(f'{mode} {p} referencers_outside={outside}')
            else:
                unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(EAL.load_asset(p))
                say(f'delete {p} {EAL.delete_asset(p)}')
    elif mode == 'rename':
        for name in names:
            for p in assets(f'{ROOT}/{name}/Fbx'):
                a = EAL.load_asset(p)
                base = p.rsplit('/', 1)[1]
                base = base[:-5] if base.endswith('_Anim') else base  # a whole-FBX import names its clip <file>_Anim
                if isinstance(a, unreal.AnimSequence):
                    dst = f'{ROOT}/{name}/A_Lux3D_{name}_{base}'
                elif isinstance(a, unreal.SkeletalMesh):
                    dst = f'{ROOT}/{name}/SK_Lux3D_{name}'
                elif isinstance(a, unreal.Skeleton):
                    dst = f'{ROOT}/{name}/SKEL_Lux3D_{name}'
                elif isinstance(a, unreal.PhysicsAsset):
                    dst = f'{ROOT}/{name}/PHYS_Lux3D_{name}'
                else:
                    continue
                say(f'rename {p} -> {dst} {EAL.rename_asset(p, dst)}')


main()
