"""Rig lane, editor (read only): the kneel clips' timelines for the hanger montages.
  FOA_AREAS=Characters python Tools/Unreal/ue_remote.py Tools/Unreal/rig/hanger_clip_probe.py
Per clip: length, and every 0.2 s the pelvis / hand_r / hand_l / head positions in component space (cm, actor forward
is +Y on the Mannequin mesh). AM_FoA_KneelScrewdriver: its segments and notifies.
-> Saved/RigShots/hanger_use/clips.json"""
import json
from pathlib import Path

import unreal

AL, AP = unreal.AnimationLibrary, unreal.AnimPoseExtensions
P = '/Game/FoA/Characters/Player'
out = {}
opts = unreal.AnimPoseEvaluationOptions()
for name in ('Anims/UAL/UAL_Fixing_Kneeling', 'Anims/Hands/AS_FoA_Kneel_Work', 'Anims/UAL/UAL_Crouch_Idle_Loop', 'Anims/UAL/UAL_Farm_Harvest'):
    seq = unreal.load_asset(f'{P}/{name}')
    n = AL.get_num_frames(seq)
    L = seq.get_play_length()
    rows = []
    t = 0.0
    while t <= L + 1e-3:
        f = min(n, int(round(t / L * n)))
        pose = AP.get_anim_pose_at_frame(seq, f, opts)
        rows.append([round(t, 2)] + [[round(v, 1) for v in AP.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation.to_tuple()]
                                     for b in ('pelvis', 'hand_r', 'hand_l', 'head')])
        t += 0.2
    out[name] = dict(length=round(L, 3), frames=n, rows=rows)
m = unreal.load_asset(P + '/Montages/AM_FoA_KneelScrewdriver')
out['AM_FoA_KneelScrewdriver'] = dict(
    length=m.get_play_length(),
    segments=[t.export_text()[:600] for t in m.get_editor_property('slot_anim_tracks')],
    notifies=[(str(e.get_editor_property('notify').get_class().get_name()) if e.get_editor_property('notify') else None,
               str(e.get_editor_property('notify').get_editor_property('notify_name')) if isinstance(e.get_editor_property('notify'), unreal.AnimNotify_PlayMontageNotify) else '',
               round(AL.get_anim_notify_event_trigger_time(e), 3)) for e in AL.get_animation_notify_events(m)],
    sections=[str(s) for s in m.get_editor_property('composite_sections')][:10] if hasattr(m, 'composite_sections') else None)
Path('P:/FoA/Saved/RigShots/hanger_use/clips.json').write_text(json.dumps(out, indent=1))
print('CLIPS', {k: v.get('length') for k, v in out.items()}, out['AM_FoA_KneelScrewdriver']['notifies'])
