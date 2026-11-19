"""Phone-only finger keys. Preserve every other authored phone-hold bone and the sleep assets."""
import json
from pathlib import Path
import unreal
A=unreal.AnimPoseExtensions;L=unreal.AnimPoseSpaces.LOCAL
path='/Game/FoA/Characters/Player/Anims/AS_FoA_PhoneHold'
seq=unreal.load_asset(path);key=unreal.load_asset('/Game/FoA/Characters/Player/Anims/Hands/AS_FoA_Grip_Key_R')
fit=json.loads(Path('P:/FoA/Saved/UIShots/phone_grip_fit.json').read_text())
options=unreal.AnimPoseEvaluationOptions();before=A.get_anim_pose_at_frame(seq,0,options);grip=A.get_anim_pose_at_frame(key,0,options)
names=[str(n) for n in A.get_bone_names(before)]
fingers=[n for n in names if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
unchanged={n:A.get_bone_pose(before,n,L).export_text() for n in names if n not in fingers}
unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(seq)
ctrl=seq.get_editor_property('controller');count=unreal.AnimationLibrary.get_num_frames(seq)+1
support={'middle':(40,45,27),'ring':(45,50,30),'pinky':(50,55,33)}
ref=A.get_reference_pose(seq.get_editor_property('skeleton'))
ctrl.open_bracket('Fit phone corner grip',False)
for n in fingers:
    t=A.get_bone_pose(grip,n,L)
    if n=='index_02_r':
        ref=A.get_reference_pose(seq.get_editor_property('skeleton'));q=A.get_bone_pose(ref,n,L).rotation
        curl=unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0,0,1),-fit['index_02_curl_deg']).quaternion()
        t.rotation=unreal.MathLibrary.multiply_quat_quat(q,curl)
    digit=n.split('_')[0]
    if digit in support and n.split('_')[1] in ('01','02','03'):
        q=A.get_bone_pose(ref,n,L).rotation;curl=support[digit][int(n.split('_')[1])-1]
        delta=unreal.MathLibrary.rotator_from_axis_and_angle(unreal.Vector(0,0,1),-curl).quaternion()
        t.rotation=unreal.MathLibrary.multiply_quat_quat(q,delta)
    ctrl.set_bone_track_keys(n,[t.translation]*count,[t.rotation]*count,[t.scale3d]*count,False)
ctrl.close_bracket(False)
after=A.get_anim_pose_at_frame(seq,0,options)
assert all(A.get_bone_pose(after,n,L).export_text()==text for n,text in unchanged.items()),'Non-finger phone pose changed'
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
Path('P:/FoA/Saved/UIShots/phone_finger_preservation.json').write_text(json.dumps(dict(changed=fingers,preserved_bones=len(unchanged),frames=count,index_02_curl=fit['index_02_curl_deg']),indent=1))
print('Phone grip saved; non-finger bones preserved',len(unchanged))
