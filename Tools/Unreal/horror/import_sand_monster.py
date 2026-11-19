"""Import the jumpscare's black-sand shell, P:/FoA-Assets/splatmesh/SM_SandMonster.gltf (Tools/Splats/glb_to_sandsplats.py
of the Lux3D monster, 14k grains), into /Game/FoA/Gameplay/Jumpscare/Sand, set up for M_SplatMesh the way
Tools/Splats/import_sand_vfx.py does (Nanite off, no lightmap UVs, full-precision UVs, padded bounds).
  $env:FOA_AREAS='Gameplay'; python Tools/Unreal/ue_remote.py Tools/Unreal/horror/import_sand_monster.py"""
import unreal

EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
DST = '/Game/FoA/Gameplay/Jumpscare/Sand'
FULL = DST + '/SM_SandMonster/StaticMeshes/SM_SandMonster'


def main():
    if not EAL.does_asset_exist(FULL):
        t = unreal.AssetImportTask()
        for k, v in (('filename', 'P:/FoA-Assets/splatmesh/SM_SandMonster.gltf'), ('destination_path', DST), ('automated', True),
                     ('replace_existing', True), ('save', False)):
            t.set_editor_property(k, v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    for p in EAL.list_assets(DST, recursive=True, include_folder=False):
        print('asset', p)
    mesh = unreal.load_asset(FULL)
    ns = SMES.get_nanite_settings(mesh)
    ns.set_editor_property('enabled', False)
    SMES.set_nanite_settings(mesh, ns, True)
    bs = SMES.get_lod_build_settings(mesh, 0)
    for k, v in (('recompute_normals', False), ('recompute_tangents', False), ('generate_lightmap_u_vs', False),
                 ('use_full_precision_u_vs', True), ('distance_field_resolution_scale', 0.0), ('remove_degenerates', False)):
        bs.set_editor_property(k, v)
    SMES.set_lod_build_settings(mesh, 0, bs)
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(40, 40, 30))  # grains shed and fall
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(40, 40, 80))
    EAL.save_asset(FULL, only_if_is_dirty=False)
    print('SM_SandMonster verts', mesh.get_num_vertices(0), 'uv', SMES.get_num_uv_channels(mesh, 0))


main()
