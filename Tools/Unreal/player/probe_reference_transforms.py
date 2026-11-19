"""Read actual SkeletalMesh local reference transforms without world actors or Creator sessions."""
import json,os
from pathlib import Path
import unreal
folder='/Game/FoA/Characters/Player/Clothing/'
paths={'original_body':'/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Body/SKM_MHC_Protagonist_BodyMesh',
 'original_face':'/Game/FoA/Characters/Protagonist/Built/MHC_Protagonist/Face/SKM_MHC_Protagonist_FaceMesh',
 'teen_head':'/Game/FoA/Characters/Protagonist/Teen/Built/MHC_Teen_Head',
 **{n:folder+'SK_FoA_'+n for n in ('Suit','Body_Suited','Shirt','Trousers','Tie','Socks','Boots_Worn')}}
report={}
for label,path in paths.items():
 mesh=unreal.load_asset(path);assert mesh,path
 component=unreal.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
 bones={}
 for i in range(component.get_num_bones()):
  name=str(component.get_bone_name(i));t=component.get_ref_pose_transform(i)
  bones[name]={'parent':str(component.get_parent_bone(name)), 'translation':[t.translation.x,t.translation.y,t.translation.z],
    'scale':[t.scale3d.x,t.scale3d.y,t.scale3d.z],'rotation':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]}
 report[label]={'mesh':path,'bone_count':len(bones),'bones':bones}
 print('REF',label,len(bones),{n:bones[n] for n in ('root','head','FACIAL_C_FacialRoot','FACIAL_C_ForeheadSkin','FACIAL_C_Chin3')if n in bones})
Path('P:/FoA/Saved/CharacterShots/ref_pose_'+os.environ.get('FOA_REF_TAG','before')+'.json').write_text(json.dumps(report,indent=2))
print('PASS actual skeletal asset ref transforms recorded without actors')
