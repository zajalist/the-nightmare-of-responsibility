"""Read authored clip poses and retarget op settings; no asset/actor changes."""
import json
from pathlib import Path
import unreal
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
rtg=unreal.load_asset('/Game/FoA/Characters/Player/Retarget/RTG_Mannequin_to_MetaHuman')
r=unreal.IKRetargeterController.get_controller(rtg)
out=dict(ops=[str(r.get_op_name(i)) for i in range(r.get_num_retarget_ops())],
    methods=[s for s in dir(r) if 'op' in s.lower() or 'profile' in s.lower()],clips={})
out['data']=[]
out['wake_sections']=[]
ls=unreal.load_asset('/Game/FoA/Cinematics/LS_WakeUp')
for b in ls.get_bindings():
    for tr in b.get_tracks():
        if isinstance(tr,unreal.MovieSceneSkeletalAnimationTrack):
            for sec in tr.get_sections():
                out['wake_sections'].append(dict(binding=str(b.get_display_name()),start=sec.get_start_frame(),end=sec.get_end_frame(),params=sec.get_editor_property('params').export_text()))
for i in range(r.get_num_retarget_ops()):
    op=r.get_op_controller(i)
    out['data'].append(dict(name=str(r.get_op_name(i)),settings=op.get_settings().export_text(),enabled=r.get_retarget_op_enabled(i)))
for label,path in (('lie','/Game/FoA/Cinematics/WakeUp/AS_FoA_Wake_Lying'),
                   ('walk','/Game/FoA/Characters/Player/Anims/Loco/AS_FoA_Walk_Brisk')):
    seq=unreal.load_asset(path); assert seq,path
    options=unreal.AnimPoseEvaluationOptions(); options.set_editor_property('extract_root_motion',False)
    out['clips'][label]=dict(options=options.export_text(),length=seq.get_play_length(),samples={})
    for at in (0.0,1.0,2.0,6.0):
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(seq,min(at,seq.get_play_length()),options)
        out['clips'][label]['samples'][str(at)]={}
        for bone in ('root','pelvis','head','foot_l','foot_r'):
            t=unreal.AnimPoseExtensions.get_bone_pose(pose,bone,unreal.AnimPoseSpaces.WORLD)
            out['clips'][label]['samples'][str(at)][bone]=dict(location=[t.translation.x,t.translation.y,t.translation.z],rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])
Path('P:/FoA/Saved/CharacterShots/retarget_sleep_read.json').write_text(json.dumps(out,indent=1))
print('READ ONLY raw lying/walk bones and retarget ops saved')
