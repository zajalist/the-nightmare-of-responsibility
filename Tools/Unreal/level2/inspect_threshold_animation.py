"""Read-only animation and sequence binding diagnostics."""
import json
from pathlib import Path
import unreal
rows=[]
for name in ('UAL_Walk_Formal_Loop','UAL_Idle_Loop'):
    clip=unreal.load_asset('/Game/FoA/Characters/Player/Anims/UAL/'+name)
    opts=unreal.AnimPoseEvaluationOptions();opts.evaluation_type=unreal.AnimDataEvalType.RAW
    poses=[]
    for t in (0,.25,.5,1):
        pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
        poses.append(str(unreal.AnimPoseExtensions.get_bone_pose(pose,'hand_r',unreal.AnimPoseSpaces.WORLD)))
    rows.append(dict(clip=name,skeleton=str(clip.get_editor_property('skeleton')),length=clip.get_play_length(),poses=poses))
for name in ('LS_DreamThreshold','LS_DreamThreshold_ReducedMotion'):
    seq=unreal.load_asset('/Game/FoA/Level2/Transition/'+name)
    for b in seq.get_bindings():
        rows.append(dict(sequence=name,binding=str(b.get_display_name()),parent=str(b.get_parent().get_display_name()) if b.get_parent().is_valid() else None,
            tracks=[dict(type=t.get_class().get_name()) for t in b.get_tracks()]))
Path('P:/FoA/Saved/Integration/story_continuity/animation.json').write_text(json.dumps(rows,indent=1))
print(json.dumps(rows))

