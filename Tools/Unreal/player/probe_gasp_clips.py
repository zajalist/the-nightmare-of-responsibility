"""Read-only: root travel, speed and yaw of every AS_GASP_* clip (what the locomotion tuning matches).
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/player/probe_gasp_clips.py
Writes Saved/AnimShots/gasp_clips.json."""
import json
import math
import unreal
AL, AP, EAL = unreal.AnimationLibrary, unreal.AnimPoseExtensions, unreal.EditorAssetLibrary
CS = unreal.AnimPoseSpaces.WORLD
out = {}
for path in EAL.list_assets('/Game/FoA/Characters/Player/Anims/GASP', recursive=False):
    seq = unreal.load_asset(path.split('.')[0])
    if not isinstance(seq, unreal.AnimSequence):
        continue
    n, L = AL.get_num_frames(seq), seq.get_play_length()
    o = unreal.AnimPoseEvaluationOptions(); o.set_editor_property('extract_root_motion', False)
    roots = [AP.get_bone_pose(AP.get_anim_pose_at_frame(seq, f, o), 'root', CS) for f in range(0, n + 1)]
    pos = [r.translation for r in roots]
    yaw = [r.rotation.rotator().yaw for r in roots]
    d = sum(((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 for a, b in zip(pos, pos[1:]))
    sp = [((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 / (L / n) for a, b in zip(pos, pos[1:])]
    dy = (yaw[-1] - yaw[0] + 540) % 360 - 180
    out[seq.get_name()] = dict(len=round(L, 2), frames=n, travel=round(d, 1), net=[round(pos[-1].x - pos[0].x, 1), round(pos[-1].y - pos[0].y, 1)],
                               yaw=round(dy, 1), vmax=round(max(sp) if sp else 0, 1), vend=round(sum(sp[-5:]) / 5 if len(sp) > 5 else 0, 1),
                               rm=seq.get_editor_property('enable_root_motion'),
                               curves=[str(c) for c in AL.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)][:6])
open('P:/FoA/Saved/AnimShots/gasp_clips.json', 'w').write(json.dumps(out, indent=1))
print('GASP clips', len(out))
