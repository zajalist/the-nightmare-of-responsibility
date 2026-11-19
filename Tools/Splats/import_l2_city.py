"""Level 2 Toronto (Queen St, 600 m corridor) into /Game/FoA/Level2/City, in short runs (world lane):
  $env:FOA_AREAS='/Game/FoA/Level2'; python Tools/Unreal/ue_remote.py Tools/Splats/import_l2_city.py FOA_CITY=ground
  $env:FOA_AREAS='/Game/FoA/Level2'; python Tools/Unreal/ue_remote.py Tools/Splats/import_l2_city.py FOA_CITY=meshes FOA_CITY_FROM=0 FOA_CITY_N=40
ground: ground_intensity_4096.png -> T_City_Ground (sRGB, grey intensity) and MI-free M_City_Ground (unlit texture)
meshes: manifest.json meshes[FROM:FROM+N] -> City/Meshes/<name>, M_SplatCity_Lean, Nanite off, full-precision UVs,
        no lightmap UVs, no recomputed normals, degenerates kept (each quad is nudged; see ply_to_splatmesh.py)."""
import json
import os
import time
from pathlib import Path

import unreal

SRC = 'P:/FoA-Assets/level2/toronto/processed/queen_600m'
DST = '/Game/FoA/Level2/City'
EAL = unreal.EditorAssetLibrary
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
MAT = '/Game/FoA/Level2/M_SplatCity_Lean'


def tasks(files, dest, parallel=False):
    out = []
    for f in files:
        t = unreal.AssetImportTask()
        if parallel:
            t.set_editor_property('async_', True)
        exact_dest=f'{dest}/{Path(f).stem}/StaticMeshes'
        for k, v in (('filename', f), ('destination_path', exact_dest), ('automated', True), ('replace_existing', True), ('save', False)):
            t.set_editor_property(k, v)
        pipeline=unreal.InterchangeGenericAssetsPipeline()
        material=pipeline.get_editor_property('material_pipeline');material.set_editor_property('import_materials',False)
        material.get_editor_property('texture_pipeline').set_editor_property('import_textures',False)
        # UE5.9 defaults to building Nanite and a distance field before post-import settings.
        # World splat quads use neither; avoid building and immediately discarding both.
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
        out.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(out)
    if parallel:
        results = [t.get_objects() for t in out]
        assert all(len(objects)==1 and isinstance(objects[0],unreal.StaticMesh) for objects in results)


def meshes():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None,'PIE running'
    dense=Path(SRC).with_name('queen_600m_dense')
    source=dense if (dense/'manifest.json').exists() else Path(SRC)
    m = json.loads((source/'manifest.json').read_text())['meshes']
    if source==dense:
        old=json.load(open(f'{SRC}/manifest.json'))['meshes']
        assert [(e['name'],e['actor_location_cm']) for e in m]==[(e['name'],e['actor_location_cm']) for e in old]
    lo = int(os.environ.get('FOA_CITY_FROM', '0'))
    part = m[lo:lo + int(os.environ.get('FOA_CITY_N', '4'))]
    for e in part:
        asset=unreal.load_asset(f"{DST}/Meshes/{e['name']}/StaticMeshes/{e['name']}")
        if asset:unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(asset)
    tasks([str(source/e['gltf']) for e in part], f'{DST}/Meshes')
    mat, done = unreal.load_asset(MAT), 0
    for e in part:
        path = f"{DST}/Meshes/{e['name']}/StaticMeshes/{e['name']}"
        sm = unreal.load_asset(path)
        assert sm,e['name']
        ns = SMES.get_nanite_settings(sm)
        if ns.get_editor_property('enabled'):
            ns.set_editor_property('enabled', False)
            SMES.set_nanite_settings(sm, ns, True)
        bs = SMES.get_lod_build_settings(sm, 0)
        changed=False
        for k, v in (('recompute_normals', False), ('recompute_tangents', False), ('generate_lightmap_u_vs', False),
                     ('use_full_precision_u_vs', True), ('distance_field_resolution_scale', 0.0), ('remove_degenerates', False)):
            if bs.get_editor_property(k)!=v:
                bs.set_editor_property(k, v);changed=True
        if changed:SMES.set_lod_build_settings(sm, 0, bs)
        # Facing WPO rotates baked horizontal quads beyond their imported thin-roof bounds.
        sm.set_editor_property('positive_bounds_extension',unreal.Vector(100,100,100))
        sm.set_editor_property('negative_bounds_extension',unreal.Vector(100,100,100))
        sm.set_material(0, mat)
        assert sm.get_num_triangles(0)==e['splats']*2,(e['name'],sm.get_num_triangles(0))
        assert EAL.save_loaded_asset(sm)
        done += 1
    print('CITY meshes', lo, '..', lo + len(part) - 1, 'imported', done, 'of', len(part))


def ground():
    t = unreal.AssetImportTask()
    for k, v in (('filename', f'{SRC}/ground_intensity_4096.png'), ('destination_path', DST), ('destination_name', 'T_City_Ground'),
                 ('automated', True), ('replace_existing', True), ('save', False)):
        t.set_editor_property(k, v)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    tex = next((EAL.load_asset(p) for p in EAL.list_assets(DST, False, False) if p.rsplit('/', 1)[1].split('.')[0] in
                ('T_City_Ground', 'ground_intensity_4096')), None)
    assert tex, 'ground texture import failed'
    tex.set_editor_property('srgb', True)
    EAL.save_loaded_asset(tex)
    print('CITY ground', tex.get_path_name(), tex.blueprint_get_size_x())


def streamed():
    """Bounded import of the new dense city's real near/far splat meshes only."""
    import json
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    source=Path(SRC).with_name('queen_600m_streamed')
    manifest=json.loads((source/'manifest.json').read_text())
    assert manifest['complete'] and manifest['completed_cells']==144
    entries=manifest['meshes']+manifest['overview']
    start=int(os.environ.get('FOA_CITY_FROM','0'));count=int(os.environ.get('FOA_CITY_N','2'))
    assert 0<=start<len(entries) and 1<=count<=8
    selected=entries[start:start+count]
    began=time.monotonic()
    folder=Path('P:/FoA/Saved/Integration/city_streamed/import');folder.mkdir(parents=True,exist_ok=True)
    receipt=[]
    if os.environ.get('FOA_CITY_PARALLEL')=='1':
        missing=[str(source/e['gltf']) for e in selected if not EAL.does_asset_exist(e['asset_path'])]
        if missing:tasks(missing,DST+'/Dense/Meshes',parallel=True)
    for e in selected:
        # Each asset is independently saved/receipted. Stop before starting more
        # work after 40 seconds; one native import itself cannot be preempted.
        if receipt and time.monotonic()-began>=40.:break
        if not EAL.does_asset_exist(e['asset_path']):
            tasks([str(source/e['gltf'])],DST+'/Dense/Meshes')
        mesh=unreal.load_asset(e['asset_path']);assert mesh,e['asset_path']
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(mesh)
        ns=SMES.get_nanite_settings(mesh)
        if ns.get_editor_property('enabled'):
            ns.set_editor_property('enabled',False);SMES.set_nanite_settings(mesh,ns,True)
        bs=SMES.get_lod_build_settings(mesh,0);changed=False
        for key,value in (('recompute_normals',False),('recompute_tangents',False),('generate_lightmap_u_vs',False),
                          ('use_full_precision_u_vs',True),('distance_field_resolution_scale',0.),('remove_degenerates',False)):
            if bs.get_editor_property(key)!=value:bs.set_editor_property(key,value);changed=True
        if changed:SMES.set_lod_build_settings(mesh,0,bs)
        assert not SMES.get_nanite_settings(mesh).get_editor_property('enabled'),e['name']
        assert SMES.get_lod_build_settings(mesh,0).get_editor_property('use_full_precision_u_vs'),e['name']
        padding=50. if e['kind']=='ground' else float(e['radius_cm_max'])+50.
        for prop in ('positive_bounds_extension','negative_bounds_extension'):
            old=mesh.get_editor_property(prop)
            mesh.set_editor_property(prop,unreal.Vector(*[max(padding,v) for v in old.to_tuple()]))
        material=unreal.load_asset(e['material']);assert material,e['material']
        mesh.set_material(0,material)
        triangles=mesh.get_num_triangles(0)
        assert triangles==e['splats']*2,(e['name'],triangles,e['splats'])
        assert SMES.get_num_uv_channels(mesh,0)>=2,e['name']
        assert EAL.save_loaded_asset(mesh,False)
        disk=Path('P:/FoA/Content'+e['asset_path'][5:]+'.uasset')
        receipt.append(dict(path=e['asset_path'],splats=e['splats'],triangles=triangles,
                            index=start+len(receipt),kind=e['kind'],lod=e['lod'],bounds_padding_cm=padding,
                            full_precision_uvs=True,nanite=False,asset_bytes=disk.stat().st_size))
        (folder/f'{start:04}.json').write_text(json.dumps(receipt,indent=2))
    print('Dense city import next index',start+len(receipt),'of',len(entries),
          'elapsed seconds',round(time.monotonic()-began,2),json.dumps(receipt))


def unload_streamed():
    assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
    paths = json.loads(os.environ['FOA_CITY_UNLOAD'])
    assert 1 <= len(paths) <= 32
    packages = []
    for path in paths:
        assert path.startswith(DST + '/Dense/Meshes/')
        package = unreal.find_object(None, path)
        if package:
            assert package.get_name() == path and isinstance(package, unreal.Package), path
            packages.append(package)
    if packages:
        unloaded, error = unreal.EditorLoadingAndSavingUtils.unload_packages(packages)
        assert unloaded and not str(error).strip(), (len(packages), str(error))
    print('Dense import packages unloaded:', len(packages))


{'meshes': meshes, 'ground': ground, 'streamed':streamed, 'unload_streamed':unload_streamed}[os.environ['FOA_CITY']]()
