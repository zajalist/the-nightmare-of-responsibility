"""Read matching Teen body and sock bind bones for offline surface clearance."""
import json
from pathlib import Path
import unreal
out={}
for label in ('Body','Socks'):
    path='/Game/FoA/Characters/Teen/Mesh/SK_Teen_'+label
    mesh=unreal.load_asset(path);assert mesh,path
    comp=unreal.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
    bones={}
    for i in range(comp.get_num_bones()):
        name=str(comp.get_bone_name(i));t=comp.get_ref_pose_transform(i)
        bones[name]=dict(parent=str(comp.get_parent_bone(name)),translation=t.translation.to_tuple(),rotation=t.rotation.to_tuple(),scale=t.scale3d.to_tuple())
    out[label]=dict(mesh=path,bones=bones)
Path('P:/FoA/Saved/WakeUp/teen_foot_reference.json').write_text(json.dumps(out,indent=2))
print('Teen foot reference bones', {k:len(v['bones']) for k,v in out.items()})
