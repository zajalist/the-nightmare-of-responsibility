"""dreamroom lane: import one Lux3D splat mesh (P:/FoA-Assets/splatmesh/<name>.gltf, made by Tools/Splats/ply_to_splatmesh.py)
into /Game/FoA/Level2/Dream/Fears with the M_SplatMesh setup of Tools/Splats/import_sand_vfx.py (Nanite off, no lightmap UVs,
full-precision UVs, no recomputed normals, bounds padded for the rise and crumble), and create or update its material
instance. One mesh per run keeps each editor call short.
  FOA_AREAS=/Game/FoA/Level2/Dream python Tools/Unreal/ue_remote.py Tools/Unreal/level2/dream_fears_import.py FOA_FEAR=SM_DreamHand
Sources (Lux3D G1-Turbo splats, P:/FoA-Assets/lux3d): sand_hand 4725644, fear_of_adulthood_briefcase 4726056, sand_crow 4726206,
sand_hourglass 4726151 (24k of 1.5M here; the VFX lane's SM_SandHourglass keeps its 8k).
"""
import json
import os

import unreal

SRC = 'P:/FoA-Assets/splatmesh'
DST = '/Game/FoA/Level2/Dream/Fears'
PARENT = '/Game/FoA/VFX/Splats/Instances/MI_Sand_AlarmClock'  # static mode (3): formed until SandEvent crumbles it
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MEL = unreal.MaterialEditingLibrary
# mesh: material instance, radius scale (about 0.7 x the converter's hint), rim light (world: just behind EXIT, high)
FEARS = {'SM_DreamHand': 'MI_DreamFear_Hand', 'SM_DreamBriefcase': 'MI_DreamFear_Briefcase', 'SM_DreamCrow': 'MI_DreamFear_Crow',
         'SM_DreamHourglass': 'MI_DreamFear_Hourglass', 'fear_of_adulthood_clock': 'MI_DreamFear_Clock'}
INSTANCE_ONLY = ('fear_of_adulthood_clock',)  # the VFX lane's import: only its dream instance here
# Silhouettes were checked black on white first (front for clock, hand, hourglass, briefcase; side for the crow);
# the bills, the wall calendar and the sand door read as blobs or plain slabs and are not used.
SPLAT_FACTOR = 0.45  # x the converter's radius hint: smaller grains keep the silhouettes crisp at 3-5x object scale
EXIT_LIGHT = (20000.0, -79560.0, 260.0, 22.0)  # rim intensity: edges glow so black reads on the darker Dream A grade
PAD = ((40, 40, 30), (40, 40, 20))  # cm, mesh-local: grains rise from and fall onto the floor around the object


def mesh_path(name):
    p = f'{DST}/{name}/{name}/StaticMeshes/{name}'
    return p if EAL.does_asset_exist(p) else None


def instance(name, mi_name, side):
    path = f'{DST}/{mi_name}'
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        mi_name, DST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, unreal.load_asset(PARENT))
    height = round(side['bounds_m']['max'][1] * 100.0, 1)  # glTF y is up: the object's height in cm (centre-ray normals)
    MEL.set_material_instance_vector_parameter_value(mi, 'Tune', unreal.LinearColor(0.0, 0.0, height, 0.0))
    MEL.set_material_instance_vector_parameter_value(mi, 'Splat', unreal.LinearColor(round(side['radius_scale_hint'] * SPLAT_FACTOR, 2), 0.9, 1.0, 0.9))
    MEL.set_material_instance_vector_parameter_value(mi, 'Light', unreal.LinearColor(*EXIT_LIGHT))
    MEL.update_material_instance(mi)
    EAL.save_asset(path, only_if_is_dirty=False)
    return path, height


def run(name):
    if name in INSTANCE_ONLY or os.environ.get('FOA_MI_ONLY') == '1':  # FOA_MI_ONLY: retune the instance, leave the mesh
        side = json.load(open(f'{SRC}/{name}.splatmesh.json', encoding='utf-8'))
        print('FEAR', name, *instance(name, FEARS[name], side))
        return
    full = mesh_path(name)
    if not full or os.environ.get('FOA_REIMPORT') == '1':  # reimport replaces the mesh in place (denser conversion)
        task = unreal.AssetImportTask()
        for k, v in (('filename', f'{SRC}/{name}.gltf'), ('destination_path', f'{DST}/{name}'), ('automated', True),
                     ('replace_existing', True), ('save', False)):
            task.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        full = mesh_path(name)
        assert full, 'IMPORT FAILED ' + name
    mesh = unreal.load_asset(full)
    ns = SMES.get_nanite_settings(mesh)
    ns.set_editor_property('enabled', False)
    SMES.set_nanite_settings(mesh, ns, True)
    bs = SMES.get_lod_build_settings(mesh, 0)
    for k, v in (('recompute_normals', False), ('recompute_tangents', False), ('generate_lightmap_u_vs', False),
                 ('use_full_precision_u_vs', True), ('distance_field_resolution_scale', 0.0), ('remove_degenerates', False)):
        bs.set_editor_property(k, v)
    SMES.set_lod_build_settings(mesh, 0, bs)
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(*PAD[0]))
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(*PAD[1]))
    side = json.load(open(f'{SRC}/{name}.splatmesh.json', encoding='utf-8'))
    mi, height = instance(name, FEARS[name], side)
    mesh.set_material(0, unreal.load_asset(mi))
    EAL.save_asset(full, only_if_is_dirty=False)
    print('FEAR', name, full, 'verts', mesh.get_num_vertices(0), 'uv', SMES.get_num_uv_channels(mesh, 0), mi, 'height', height)


run(os.environ['FOA_FEAR'])  # in a function: no asset wrappers left in the editor's shared globals
