"""Import one Lux3D splat-mesh glTF (P:/FoA-Assets/splatmesh, from Tools/Splats/ply_to_splatmesh.py) for Level 2's
interview set, set up like Tools/Splats/import_sand_vfx.py (Nanite off, full-precision UVs, no lightmap UVs or
recomputed normals, padded bounds). One mesh per run keeps the editor call short.

  $env:FOA_AREAS='asset:/Game/FoA/Level2/Journey/Sand'; python Tools/Unreal/ue_remote.py Tools/Unreal/level2/import_l2_sand.py FOA_SPLAT_MESH=SM_SandBriefcase

The meshes are Lux3D (Aholo) text-to-3D splats generated on 11-05 for the dream (docs/lux3d-bedroom-prompts.md):
Fear of adulthood (briefcase) 4726056, Unpaid Bills, Sand Crow. They form out of black sand when the interview opens
and crumble with his double at the end (BP_L2StopSet)."""
import os

import unreal

SRC = 'P:/FoA-Assets/splatmesh'
DST = '/Game/FoA/Level2/Journey/Sand'
PAD = {'SM_SandBriefcase': ((40, 40, 30), (40, 40, 10)), 'SM_SandBills': ((45, 45, 40), (45, 45, 10)),
       'SM_SandCrow': ((60, 60, 50), (60, 60, 10)), 'SM_SandCalendar': ((35, 35, 30), (35, 35, 10)),
       'SM_SandNecktie': ((35, 35, 30), (35, 35, 10)), 'SM_SandHand': ((40, 40, 40), (40, 40, 20))}
# Splat.x (radius scale) = 0.6 x the converter's radius_scale_hint, as MI_Sand_AlarmClock (2.6 for 4.91) and
# MI_Sand_Hourglass (6 for 8.48) do; one small child of MI_Sand_Hourglass per object.
RADIUS = {'SM_SandBriefcase': 3.6, 'SM_SandBills': 6.9, 'SM_SandCrow': 2.9, 'SM_SandCalendar': 4.3, 'SM_SandNecktie': 3.9,
          'SM_SandHand': 1.6}
PARENT = '/Game/FoA/VFX/Splats/Instances/MI_Sand_Hourglass'


def instance(name):
    mi_name = 'MI_' + name[3:]
    path = f'{DST}/{mi_name}'
    mel = unreal.MaterialEditingLibrary
    if EAL.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(mi_name, DST, unreal.MaterialInstanceConstant,
                                                                    unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, unreal.load_asset(PARENT))
    old = mel.get_material_instance_vector_parameter_value(mi, 'Splat')
    mel.set_material_instance_vector_parameter_value(mi, 'Splat', unreal.LinearColor(RADIUS[name], old.g, old.b, old.a))
    mel.update_material_instance(mi)
    EAL.save_asset(path, only_if_is_dirty=False)
    return mi
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def find(name):
    folder = f'{DST}/{name}'
    paths = EAL.list_assets(folder, recursive=True, include_folder=False) if EAL.does_directory_exist(folder) else []
    meshes = [p.split('.')[0] for p in paths if str(EAL.find_asset_data(p).asset_class_path.asset_name) == 'StaticMesh']
    assert len(meshes) <= 1, meshes
    return meshes[0] if meshes else None


def run(name):
    full = find(name)
    if not full:
        pipe = unreal.InterchangeGenericAssetsPipeline()  # no junk materials or textures: the mesh takes MI_Sand_Hourglass
        materials = pipe.get_editor_property('material_pipeline')
        materials.set_editor_property('import_materials', False)
        materials.get_editor_property('texture_pipeline').set_editor_property('import_textures', False)
        pipe.get_editor_property('mesh_pipeline').set_editor_property('build_nanite', False)
        overrides = unreal.InterchangePipelineStackOverride()
        overrides.add_pipeline(pipe)
        task = unreal.AssetImportTask()
        for k, v in (('filename', f'{SRC}/{name}.gltf'), ('destination_path', f'{DST}/{name}'), ('automated', True),
                     ('replace_existing', True), ('save', False), ('options', overrides)):
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        full = find(name)
        assert full, ('import failed', name, task.get_editor_property('imported_object_paths'))
    mesh = unreal.load_asset(full)
    ns = SMES.get_nanite_settings(mesh)
    ns.set_editor_property('enabled', False)
    SMES.set_nanite_settings(mesh, ns, True)
    bs = SMES.get_lod_build_settings(mesh, 0)
    for k, v in (('recompute_normals', False), ('recompute_tangents', False), ('generate_lightmap_u_vs', False),
                 ('use_full_precision_u_vs', True), ('distance_field_resolution_scale', 0.0), ('remove_degenerates', False)):
        bs.set_editor_property(k, v)
    SMES.set_lod_build_settings(mesh, 0, bs)
    pos, neg = PAD[name]
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(*pos))
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(*neg))
    mesh.set_material(0, instance(name))
    EAL.save_asset(full, only_if_is_dirty=False)
    junk = [p for p in EAL.list_assets(f'{DST}/{name}', True) if p.split('.')[0] != full]
    print(name, full, 'verts', mesh.get_num_vertices(0), 'tris', mesh.get_num_triangles(0), 'other assets', junk)


run(os.environ['FOA_SPLAT_MESH'])
