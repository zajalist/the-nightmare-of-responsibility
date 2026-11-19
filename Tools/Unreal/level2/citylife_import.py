"""City life lane: Lux3D imports into /Game/FoA/Level2/CityLife/<Name> (run through ue_remote, one short run per mode).
  $env:FOA_AREAS='/Game/FoA/Level2/CityLife'
  python Tools/Unreal/ue_remote.py Tools/Unreal/level2/citylife_import.py CL_MODE=static CL_ITEMS=briefcase:Briefcase:512,...
  ... CL_MODE=rename CL_ITEMS=briefcase:Briefcase,...        (its own run, after the import)
  ... CL_MODE=skel   CL_ITEMS=tpose/rig/commuter_in_suit_t_rig:Commuter:1024    (a Lux3D auto-rigged GLB)
  ... CL_MODE=anim   CL_ITEMS=Commuter:tpose/rig/commuter_in_suit_t_rig_anim/Walk_Formal_Loop.fbx,...  (onto SK_Lux3D_<Name>)
Paths are relative to P:/FoA-Assets/lux3d/citylife_20261118. Static meshes: Nanite off, three reduction LODs (100/50/20 %);
textures capped at the given size. Prints what it made (class, path, triangles, bounds)."""
import os

import unreal

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
SRC = 'P:/FoA-Assets/lux3d/citylife_20261118'
ROOT = '/Game/FoA/Level2/CityLife'
LOG = 'P:/FoA/Saved/QA/lanes/citylife_import.log'


def task(filename, dest, options=None):
    t = unreal.AssetImportTask()
    for k, v in (('filename', filename), ('destination_path', dest), ('automated', True), ('replace_existing', True),
                 ('save', False)):
        t.set_editor_property(k, v)
    if options:
        t.set_editor_property('options', options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    return list(t.get_editor_property('imported_object_paths') or [])


def lods(mesh):
    smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    ns = smes.get_nanite_settings(mesh)
    ns.set_editor_property('enabled', False)
    smes.set_nanite_settings(mesh, ns, True)
    steps = []
    for pct, screen in ((1.0, 1.0), (.5, .25), (.2, .08)):
        s = unreal.StaticMeshReductionSettings()
        s.set_editor_property('percent_triangles', pct)
        s.set_editor_property('screen_size', screen)
        steps.append(s)
    opts = unreal.StaticMeshReductionOptions()
    opts.set_editor_property('auto_compute_lod_screen_size', False)
    opts.set_editor_property('reduction_settings', steps)
    smes.set_lods_with_notification(mesh, opts, True)


def report(dest, cap):
    for path in EAL.list_assets(dest, recursive=True, include_folder=False):
        a = EAL.load_asset(path)
        line = f'{a.get_class().get_name()} {path.split(".")[0]}'
        if isinstance(a, unreal.StaticMesh):
            if a.get_num_lods() < 3:
                lods(a)
            b = a.get_bounds()
            line += (f' tris={[a.get_num_triangles(i) for i in range(a.get_num_lods())]} size=({2 * b.box_extent.x:.0f},'
                     f'{2 * b.box_extent.y:.0f},{2 * b.box_extent.z:.0f}) origin=({b.origin.x:.0f},{b.origin.y:.0f},{b.origin.z:.0f})')
        elif isinstance(a, unreal.SkeletalMesh):
            b = a.get_bounds()
            line += f' size=({2 * b.box_extent.x:.0f},{2 * b.box_extent.y:.0f},{2 * b.box_extent.z:.0f}) skeleton={a.skeleton.get_path_name()}'
        elif isinstance(a, unreal.Texture2D):
            a.set_editor_property('max_texture_size', cap)
            line += f' {a.blueprint_get_size_x()}x{a.blueprint_get_size_y()} cap={cap}'
        elif isinstance(a, unreal.MaterialInstance):
            line += f' parent={a.get_editor_property("parent").get_path_name()}'
        elif isinstance(a, unreal.AnimSequence):
            line += f' length={a.get_play_length():.2f}s skeleton={a.get_editor_property("skeleton").get_name()}'
        EAL.save_asset(path, only_if_is_dirty=False)
        print(line)
        with open(LOG, 'a', encoding='utf-8') as fh:  # ue_remote clips long output
            fh.write(line + '\n')


def rename(name):
    dest = f'{ROOT}/{name}'
    found = {}
    for p in EAL.list_assets(dest, recursive=True, include_folder=False):
        found.setdefault(EAL.load_asset(p).get_class().get_name(), []).append(p.split('.')[0])
    for mi_path in [p for p in found.get('MaterialInstanceConstant', []) if '/MI_Lux3D_' not in p and '/Fbx/' not in p][:1]:
        mi = EAL.load_asset(mi_path)
        for prm, suffix in (('BaseColorTexture', 'BaseColor'), ('MetallicRoughnessTexture', 'MetallicRoughness'),
                            ('NormalTexture', 'Normal')):
            t = MEL.get_material_instance_texture_parameter_value(mi, prm)
            # only our own imports: an unset slot reports the parent's default (Interchange's shared T_Generic_N)
            if t and t.get_path_name().startswith(dest + '/') and '/T_Lux3D_' not in t.get_path_name():
                print('rename', t.get_name(), EAL.rename_asset(t.get_path_name().split('.')[0], f'{dest}/T_Lux3D_{name}_{suffix}'))
        print('rename MI', EAL.rename_asset(mi_path, f'{dest}/MI_Lux3D_{name}'))
    for cls, prefix in (('StaticMesh', 'SM'), ('SkeletalMesh', 'SK'), ('Skeleton', 'SKEL'), ('PhysicsAsset', 'PHYS')):
        for p in [p for p in found.get(cls, []) if f'/{prefix}_Lux3D_' not in p and '/Fbx/' not in p][:1]:
            print('rename', cls, EAL.rename_asset(p, f'{dest}/{prefix}_Lux3D_{name}'))


def main():
    mode = os.environ['CL_MODE']
    for spec in os.environ['CL_ITEMS'].split(','):
        parts = spec.split(':')
        if mode == 'static':
            item, name, cap = parts
            dest = f'{ROOT}/{name}'
            if not EAL.list_assets(dest, recursive=True):
                task(f'{SRC}/{item}/textured.glb', dest)
            report(dest, int(cap))
        elif mode == 'skel':
            item, name, cap = parts
            dest = f'{ROOT}/{name}'
            glb = next(f for f in os.listdir(f'{SRC}/{item}') if f.lower().endswith('.glb'))
            if not EAL.list_assets(dest, recursive=True):
                task(f'{SRC}/{item}/{glb}', dest)
            report(dest, int(cap))
        elif mode == 'rename':
            rename(parts[1])
        elif mode == 'fbx':  # a whole retarget FBX (mesh, skeleton, clip): the clips bind to this skeleton, not the GLB's
            name, fbx = parts
            dest = f'{ROOT}/{name}/Fbx'
            if not EAL.list_assets(dest, recursive=True):
                task(f'{SRC}/{fbx}', dest)
            report(dest, 1024)
        elif mode == 'anim':
            name, fbx = parts
            dest = f'{ROOT}/{name}'
            sk = next(EAL.load_asset(p) for p in EAL.list_assets(dest, recursive=True, include_folder=False)
                      if isinstance(EAL.load_asset(p), unreal.SkeletalMesh) and ('/Fbx/' in p or '/SK_Lux3D_' in p))
            dest = sk.get_path_name().rsplit('/', 1)[0]
            ui = unreal.FbxImportUI()
            ui.set_editor_property('import_mesh', False)
            ui.set_editor_property('import_animations', True)
            ui.set_editor_property('import_materials', False)
            ui.set_editor_property('import_textures', False)
            ui.set_editor_property('skeleton', sk.skeleton)
            ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
            seq = ui.get_editor_property('anim_sequence_import_data')  # Lux3D clips are 30 fps; 24 fps refuses them
            seq.set_editor_property('use_default_sample_rate', False)
            seq.set_editor_property('custom_sample_rate', 30)
            seq.set_editor_property('snap_to_closest_frame_boundary', True)
            made = task(f'{SRC}/{fbx}', dest, ui)
            for p in made:
                a = EAL.load_asset(p)
                if isinstance(a, unreal.AnimSequence):
                    clip = os.path.splitext(os.path.basename(fbx))[0]
                    target = f'{dest}/A_Lux3D_{name}_{clip}'
                    if p.split('.')[0] != target:
                        EAL.save_asset(p, only_if_is_dirty=False)
                        print('imported', p, 'rename next run to', target)
            report(dest, 1024)


main()
