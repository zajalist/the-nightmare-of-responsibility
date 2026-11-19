"""Native readback only under a stopped-editor asset lease.
Default: the two dream meshes. To check a cold city, pass FOA_VERIFY_CITY_FROM and
FOA_VERIFY_CITY_N<=32; full-city cold loads exceed a short native call budget.
"""
import json
import os
from pathlib import Path
import unreal

assert os.environ.get('FOA_LEASE')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
out=Path('P:/FoA/Saved/Integration/splat_visual_20261112')
manifest=json.loads(Path('P:/FoA-Assets/level2/toronto/processed/queen_600m_dense/manifest.json').read_text())
start=int(os.environ.get('FOA_VERIFY_CITY_FROM','0'));size=int(os.environ.get('FOA_VERIFY_CITY_N','0'))
assert 0<=size<=32 and start>=0
city_rows=manifest['meshes'][start:start+size]
expected={f"/Game/FoA/Level2/City/Meshes/{row['name']}/StaticMeshes/{row['name']}":row['splats']*2
          for row in city_rows}
expected['/Game/FoA/Level2/Dream/SM_DreamA/StaticMeshes/SM_DreamA']=493688
expected['/Game/FoA/Level2/Dream/SM_DreamInterview/StaticMeshes/SM_DreamInterview']=json.loads(
    Path('P:/FoA-Assets/splatmesh/dream_interview/SM_DreamInterview.splatmesh.json').read_text())['splats']*2
rows=[]
subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for path,triangles in expected.items():
    mesh=unreal.load_asset(path)
    assert mesh and mesh.get_num_triangles(0)==triangles,path
    assert not subsystem.get_nanite_settings(mesh).get_editor_property('enabled'),path
    aniso=os.environ.get('FOA_VERIFY_ANISO')=='1' and '/Dream/' in path
    assert subsystem.get_num_uv_channels(mesh,0)==(5 if aniso else 2),path
    if aniso:assert mesh.get_material(0).get_name()=='M_SplatWorld_Aniso',path
    settings=subsystem.get_lod_build_settings(mesh,0)
    for key,value in [('use_full_precision_u_vs',True),('distance_field_resolution_scale',0.),
                      ('recompute_normals',False),('recompute_tangents',False),('remove_degenerates',False)]:
        assert settings.get_editor_property(key)==value,(path,key)
    rows.append(dict(path=path,triangles=triangles,vertices=mesh.get_num_vertices(0)))
dirty=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
owned=set(expected)|{'/Game/FoA/Level2/Dream/M_L2_PanoSky','/Game/FoA/Level2/M_SplatWorld_Aniso'}
assert not (set(dirty)&owned),sorted(set(dirty)&owned)
report=dict(meshes=len(rows),city_meshes=len(city_rows),city_triangles=sum(row['splats']*2 for row in city_rows),
            owned_dirty=[],pie=False,lean_build_settings=True,rows=rows,
            anti_aliasing_method=unreal.SystemLibrary.get_console_variable_int_value('r.AntiAliasingMethod'))
(out/(f'native_verified_city_{start}.json' if size else 'native_verified_dream.json')).write_text(json.dumps(report,indent=1))
print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
