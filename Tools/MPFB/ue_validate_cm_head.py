"""Finish validation/save after asynchronous morph import without reimporting again."""
import json
from pathlib import Path
import unreal
mesh=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Head')
comp=unreal.SkeletalMeshComponent()
comp.set_skeletal_mesh_asset(mesh)
names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
refs=[comp.get_ref_pose_transform(i) for i in range(len(names))]
head=unreal.Transform()
bone='head'
while bone in names:
    head=unreal.MathLibrary.compose_transforms(head,refs[names.index(bone)])
    bone=str(comp.get_parent_bone(bone))
error=max(abs(v-1) for t in refs for v in (t.scale3d.x,t.scale3d.y,t.scale3d.z))
print('HEAD_CM_DIAGNOSTIC',names,head.translation,head.scale3d,len(mesh.morph_targets))
assert error<.001 and 160<head.translation.z<190 and len(mesh.morph_targets)==52,(error,head,len(mesh.morph_targets))
unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
report={'mesh':mesh.get_path_name(),'bones':len(refs),'maximum_reference_scale_error':error,'head_reference_z_cm':head.translation.z,
        'head_scale':[head.scale3d.x,head.scale3d.y,head.scale3d.z],'morphs':len(mesh.morph_targets),'material_slots':len(mesh.materials)}
Path('P:/FoA/Saved/CharacterShots/mpfb/SK_Teen_Head_cm.json').write_text(json.dumps(report,indent=2))
body=unreal.load_asset('/Game/FoA/Characters/Teen/Mesh/SK_Teen_Body')
print('TEEN_CM_HEAD_PASS',report,'body_physics',body.physics_asset.get_path_name() if body.physics_asset else None)
