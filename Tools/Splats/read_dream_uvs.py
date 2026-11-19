"""Read actual imported mesh UVs/positions; no asset mutations."""
import json,os
from pathlib import Path
import unreal
assert os.environ.get('FOA_LEASE')
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
rows=[]
for name in ('SM_DreamA','SM_DreamInterview'):
    mesh=unreal.load_asset(f'/Game/FoA/Level2/Dream/{name}/StaticMeshes/{name}')
    description=mesh.get_static_mesh_description(0)
    samples=[]
    for i in (0,1,2,3,4,5,600,3000,6000,12000):
        key=unreal.VertexInstanceID();key.set_editor_property('id_value',i)
        vertex=description.get_vertex_instance_vertex(key)
        samples.append(dict(id=i,position=list(description.get_vertex_position(vertex).to_tuple()),
            uvs=[list(description.get_vertex_instance_uv(key,j).to_tuple()) for j in range(5)]))
    build=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
    rows.append(dict(name=name,build_scale=list(build.get_editor_property('build_scale3d').to_tuple()),samples=samples))
Path('P:/FoA/Saved/Integration/splat_visual_20261112/imported_uvs.json').write_text(json.dumps(rows,indent=1))
print(json.dumps(rows))
