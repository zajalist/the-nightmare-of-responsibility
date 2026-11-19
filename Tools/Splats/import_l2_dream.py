"""Level 2 Dream A (Aholo world 3FO4K4V8OF4C) into /Game/FoA/Level2/Dream, one asset per run (world lane):
  $env:FOA_AREAS='/Game/FoA/Level2'; python Tools/Unreal/ue_remote.py Tools/Splats/import_l2_dream.py FOA_L2_STEP=tex
  $env:FOA_AREAS='/Game/FoA/Level2'; python Tools/Unreal/ue_remote.py Tools/Splats/import_l2_dream.py FOA_L2_STEP=mesh
tex : P:/FoA-Assets/level2/aholo/dream_a/pano.jpg -> T_DreamA_Pano (sRGB, no mips: an equirect wraps at u = 0/1)
mesh: prepare_dream_density.py staged full-source glTF (246844 lean splats) -> same SM_DreamA asset. Same build setup as
      import_sand_vfx.py (Nanite off, no lightmap UVs, full-precision UVs, no recomputed normals, degenerates kept), and
      bounds padded by the largest splat radius (57 cm) because the quads are expanded in the vertex shader."""
import os
import json
import math
from pathlib import Path

import unreal

DST = '/Game/FoA/Level2/Dream'
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def find(name, cls):
    for p in EAL.list_assets(DST, recursive=True, include_folder=False):
        if p.rsplit('/', 1)[1].split('.')[0] == name:
            a = EAL.load_asset(p)
            if isinstance(a, cls):
                return a
    return None


def task(filename, dest, name=None):
    if filename.lower().endswith('.gltf'):dest=f'{dest}/{Path(filename).stem}/StaticMeshes'
    t = unreal.AssetImportTask()
    for k, v in (('filename', filename), ('destination_path', dest), ('automated', True), ('replace_existing', True), ('save', False)):
        t.set_editor_property(k, v)
    if name:
        t.set_editor_property('destination_name', name)
    if filename.lower().endswith('.gltf'):
        pipeline=unreal.InterchangeGenericAssetsPipeline()
        material=pipeline.get_editor_property('material_pipeline')
        material.set_editor_property('import_materials',False)
        material.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
        mesh_pipeline=pipeline.get_editor_property('mesh_pipeline')
        mesh_pipeline.set_editor_property('build_nanite',False)
        mesh_pipeline.set_editor_property('distance_field_resolution_scale',0.)
        common=pipeline.get_editor_property('common_meshes_properties')
        for key,value in [('recompute_normals',False),('recompute_tangents',False),
                          ('use_full_precision_u_vs',True),('remove_degenerates',False)]:
            common.set_editor_property(key,value)
        overrides=unreal.InterchangePipelineStackOverride()
        overrides.add_pipeline(pipeline)
        t.set_editor_property('options',overrides)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])


def tex():
    task('P:/FoA-Assets/level2/aholo/dream_a/pano.jpg', DST, 'T_DreamA_Pano')
    t = find('T_DreamA_Pano', unreal.Texture2D)
    assert t, 'pano import failed'
    t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    t.set_editor_property('srgb', True)
    t.set_editor_property('address_x', unreal.TextureAddress.TA_WRAP)
    t.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    EAL.save_loaded_asset(t)
    print('L2 tex', t.get_path_name(), t.blueprint_get_size_x(), 'x', t.blueprint_get_size_y())


def mesh():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'PIE running'
    interview=os.environ.get('FOA_L2_STEP')=='interview'
    name='SM_DreamInterview' if interview else 'SM_DreamA'
    source=Path('P:/FoA-Assets/splatmesh/dream_interview/SM_DreamInterview.gltf' if interview else 'P:/FoA-Assets/splatmesh/dream_dense/SM_DreamA.gltf')
    assert source.exists(),'Run offline prepare_dream_density.py first'
    side=json.loads(source.with_suffix('.splatmesh.json').read_text())
    material=unreal.load_asset('/Game/FoA/Level2/M_SplatWorld_Aniso' if side.get('covariance') else '/Game/FoA/Level2/M_SplatWorld_Lean')
    assert material,'Build Dream ellipse material before importing covariance meshes'
    if not interview:
        baseline=json.loads(Path('P:/FoA-Assets/splatmesh/SM_DreamA.splatmesh.json').read_text())
        assert side['offset_m']==baseline['offset_m'] and side['splats']==side['candidates']
    path=f'{DST}/{name}/StaticMeshes/{name}'
    old=unreal.load_asset(path)
    if old:unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(old)
    task(str(source), DST)
    m = unreal.load_asset(path)
    assert m, 'mesh import failed'
    ns = SMES.get_nanite_settings(m)
    if ns.get_editor_property('enabled'):
        ns.set_editor_property('enabled', False)
        SMES.set_nanite_settings(m, ns, True)
    bs = SMES.get_lod_build_settings(m, 0)
    changed=False
    for k, v in (('recompute_normals', False), ('recompute_tangents', False), ('generate_lightmap_u_vs', False),
                 ('use_full_precision_u_vs', True), ('distance_field_resolution_scale', 0.0), ('remove_degenerates', False)):
        if bs.get_editor_property(k)!=v:
            bs.set_editor_property(k, v);changed=True
    if changed:SMES.set_lod_build_settings(m, 0, bs)
    # Perspective Jacobian can enlarge off-axis ellipses; keep their true source support visible.
    padding=max(60,math.ceil(side['support_radius_cm_max']*2)) if side.get('covariance') else max(60,math.ceil(side['radius_cm']['max']*1.04))
    m.set_editor_property('positive_bounds_extension', unreal.Vector(padding,padding,padding))
    m.set_editor_property('negative_bounds_extension', unreal.Vector(padding,padding,padding))
    m.set_material(0, material)
    assert m.get_num_triangles(0)==side['splats']*2
    assert SMES.get_num_uv_channels(m,0)==(5 if side.get('covariance') else 2)
    assert EAL.save_loaded_asset(m)
    bb = m.get_bounding_box()
    print('L2 mesh', m.get_path_name(), 'verts', m.get_num_vertices(0), 'tris', m.get_num_triangles(0),
          'uv', SMES.get_num_uv_channels(m, 0), 'bounds', bb.min, bb.max)


{'tex': tex, 'mesh': mesh, 'interview':mesh}[os.environ['FOA_L2_STEP']]()
