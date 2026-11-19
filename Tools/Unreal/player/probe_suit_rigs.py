"""Read loaded skeletal assets through unregistered components; no world actors or Creator sessions."""
import json
import unreal

paths={
    "original_body":"/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh",
    "suited_body":"/Game/FoA/Characters/Player/Clothing/SK_FoA_Body_Suited",
    "suit":"/Game/FoA/Characters/Player/Clothing/SK_FoA_Suit",
    "teen_head":"/Game/FoA/Characters/Protagonist/Teen/Built/MHC_Teen_Head",
}
result={}
for name,path in paths.items():
    mesh=unreal.load_asset(path)
    component=unreal.SkeletalMeshComponent()
    component.set_skeletal_mesh_asset(mesh)
    bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
    dna=[d.get_editor_property("dna_asset") for d in mesh.get_editor_property("asset_user_data")
         if d.get_class().get_name()=="DNAAssetUserData"]
    result[name]={"mesh":path,"bones":bones,"bone_count":len(bones),
        "skeleton":mesh.get_editor_property("skeleton").get_path_name(),
        "physics":str(mesh.get_editor_property("physics_asset")),
        "post_process":str(mesh.get_editor_property("post_process_anim_blueprint")),
        "dna":[d.get_path_name() if d else None for d in dna]}
old=set(result['original_body']['bones'])
for name in ('suited_body','suit'):
    result[name]['missing_original_bones']=sorted(old-set(result[name]['bones']))
    result[name]['extra_bones']=sorted(set(result[name]['bones'])-old)
with open('P:/FoA/Saved/CharacterShots/suit_rigs.json','w') as file:json.dump(result,file,indent=2)
print('SUIT RIGS', {name:{k:v for k,v in data.items() if k!='bones'} for name,data in result.items()})
