"""Read-only metadata/bind audit before integrating a newly proportioned body."""
import json,os
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
paths={
 'original_body':'/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh',
 'natural_teen_body':os.environ.get('FOA_BODY_SOURCE','/Game/FoA/Characters/Protagonist/Teen/Built_N/Body/MHC_Face_N_Body')}
out={}
for label,path in paths.items():
    mesh=unreal.load_asset(path);assert mesh,path
    component=unreal.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
    bones={}
    for i in range(component.get_num_bones()):
        name=str(component.get_bone_name(i));tr=component.get_ref_pose_transform(i)
        bones[name]=dict(parent=str(component.get_parent_bone(name)),translation=[tr.translation.x,tr.translation.y,tr.translation.z],
            rotation=[tr.rotation.x,tr.rotation.y,tr.rotation.z,tr.rotation.w],scale=[tr.scale3d.x,tr.scale3d.y,tr.scale3d.z])
    def pathof(v):return v.get_path_name() if v else None
    dna=[pathof(d.get_editor_property('dna_asset')) for d in mesh.get_editor_property('asset_user_data')
         if d.get_class().get_name()=='DNAAssetUserData']
    out[label]=dict(mesh=mesh.get_path_name(),skeleton=pathof(mesh.get_editor_property('skeleton')),
        physics=pathof(mesh.get_editor_property('physics_asset')),post_process=pathof(mesh.get_editor_property('post_process_anim_blueprint')),
        dna=dna,bone_count=len(bones),bones=bones)
old,new=(out[k]['bones'] for k in paths)
out['comparison']=dict(missing=sorted(set(old)-set(new)),extra=sorted(set(new)-set(old)),
    changed_parents=[n for n in old.keys()&new.keys() if old[n]['parent']!=new[n]['parent']],
    changed_ref_translations=[n for n in old.keys()&new.keys() if sum((a-b)**2 for a,b in zip(old[n]['translation'],new[n]['translation']))>.001**2])
dest=Path('P:/FoA/Saved/CharacterShots/natural_teen_rig.json');dest.write_text(json.dumps(out,indent=1))
print('New Body metadata read; no asset changes',str(dest),{k:{q:v for q,v in d.items() if q!='bones'} for k,d in out.items() if k!='comparison'})
